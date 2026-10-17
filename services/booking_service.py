import secrets
from typing import List, Dict, Any, Tuple, Optional
from models import db, utcnow, User, Event, Seat, SeatLock, Booking, Attendee, Payment, Ticket
from config import Config
from services.seat_lock_service import clean_expired_locks
from services.payment_service import process_simulated_payment
from services.email_service import send_booking_confirmation
from utils.qr_generator import generate_ticket_qr
from utils.validators import validate_attendee_data


def generate_booking_reference() -> str:
    """Generates unique booking reference e.g. BK-20260821-A9F3."""
    date_part = utcnow().strftime("%Y%m%d")
    random_hex = secrets.token_hex(3).upper()
    return f"BK-{date_part}-{random_hex}"


def generate_ticket_number() -> str:
    """Generates unique ticket number e.g. TKT-2026-894125."""
    year = utcnow().strftime("%Y")
    random_num = secrets.randbelow(900000) + 100000
    return f"TKT-{year}-{random_num}"


def calculate_pricing(seats: List[Seat]) -> Dict[str, float]:
    """Calculates subtotal, convenience fee, tax and total amount server-side."""
    subtotal = float(sum(seat.price for seat in seats))
    convenience_fee = round(subtotal * (Config.CONVENIENCE_FEE_PERCENTAGE / 100.0), 2)
    # GST / Tax calculation (18% on convenience fee)
    tax = round(convenience_fee * (Config.TAX_PERCENTAGE / 100.0), 2)
    total_amount = round(subtotal + convenience_fee + tax, 2)

    return {
        "subtotal": subtotal,
        "convenience_fee": convenience_fee,
        "tax": tax,
        "total_amount": total_amount,
    }


def execute_booking_transaction(
    user_id: int,
    event_id: int,
    session_token: str,
    attendees_data: List[Dict[str, Any]],
    payment_method: str,
    payment_details: Optional[Dict[str, Any]] = None
) -> Tuple[bool, str, Optional[Booking]]:
    """
    Executes an atomic database transaction for booking tickets:
    1. Verifies lock ownership & validity
    2. Calculates total cost from DB prices
    3. Simulates payment gateway
    4. Creates Booking, Attendees, Payment, Tickets, QR Codes
    5. Updates Seat statuses to BOOKED
    6. Sends email confirmation
    """
    if payment_details is None:
        payment_details = {}

    clean_expired_locks()
    now = utcnow()

    # 1. Validation of inputs
    if not attendees_data:
        return False, "No attendee details provided.", None

    if len(attendees_data) > Config.MAX_SEATS_PER_BOOKING:
        return False, f"Cannot book more than {Config.MAX_SEATS_PER_BOOKING} tickets per transaction.", None

    user = db.session.get(User, user_id)
    if not user:
        return False, "User account not found.", None

    event = db.session.get(Event, event_id)
    if not event or event.status != "ACTIVE":
        return False, "Event is not available for booking.", None

    seat_ids = [att.get("seat_id") for att in attendees_data]
    if len(seat_ids) != len(set(seat_ids)):
        return False, "Duplicate seats detected in attendee form.", None

    # Validate each attendee's information
    for att in attendees_data:
        is_valid, msg = validate_attendee_data(att)
        if not is_valid:
            return False, f"Attendee validation failed: {msg}", None

    # 2. Verify all seat locks
    seats = Seat.query.filter(Seat.id.in_(seat_ids), Seat.event_id == event_id).all()
    if len(seats) != len(seat_ids):
        return False, "Invalid seat selection for this event.", None

    for seat in seats:
        if seat.status == "BOOKED":
            return False, f"Seat {seat.seat_number} is already booked.", None

        if seat.status == "ADMIN_LOCKED":
            reason_txt = f" ({seat.admin_reserve_reason})" if seat.admin_reserve_reason else ""
            return False, f"Seat {seat.seat_number} is reserved by the admin{reason_txt} and cannot be booked.", None

        lock = SeatLock.query.filter_by(seat_id=seat.id).first()
        if not lock or lock.session_token != session_token or lock.is_expired:
            return False, f"Your lock for seat {seat.seat_number} has expired or is invalid. Please reselect seats.", None

    # 3. Calculate authoritative pricing from DB
    pricing = calculate_pricing(seats)
    total_amount = pricing["total_amount"]

    # 4. Simulate Payment Gateway
    pay_success, pay_msg, pay_info = process_simulated_payment(total_amount, payment_method, payment_details)
    if not pay_success:
        return False, f"Payment failed: {pay_msg}", None

    # 5. Database Transaction (Atomic)
    try:
        booking_ref = generate_booking_reference()
        
        booking = Booking(
            booking_reference=booking_ref,
            user_id=user.id,
            event_id=event.id,
            total_tickets=len(seats),
            subtotal=pricing["subtotal"],
            convenience_fee=pricing["convenience_fee"],
            tax=pricing["tax"],
            total_amount=pricing["total_amount"],
            booking_status="CONFIRMED",
            created_at=now,
        )
        db.session.add(booking)
        db.session.flush()  # Populates booking.id

        # Create Payment record
        payment = Payment(
            booking_id=booking.id,
            transaction_id=pay_info["transaction_id"],
            payment_method=payment_method.upper(),
            amount=pricing["total_amount"],
            payment_status="SUCCESS",
            paid_at=now,
        )
        db.session.add(payment)

        # Map seat_id to Seat object
        seat_map = {s.id: s for s in seats}

        # Create Attendees & Tickets
        for att in attendees_data:
            seat_id = att["seat_id"]
            seat = seat_map[seat_id]

            attendee = Attendee(
                booking_id=booking.id,
                seat_id=seat_id,
                full_name=att["full_name"].strip(),
                age=int(att["age"]),
                phone=str(att["phone"]).strip(),
                city=att["city"].strip(),
            )
            db.session.add(attendee)
            db.session.flush()  # Populates attendee.id

            # Generate Ticket & QR
            ticket_num = generate_ticket_number()
            qr_url = generate_ticket_qr(ticket_num)

            ticket = Ticket(
                booking_id=booking.id,
                attendee_id=attendee.id,
                seat_id=seat_id,
                ticket_number=ticket_num,
                qr_code_path=qr_url,
                ticket_status="ACTIVE",
                created_at=now,
            )
            db.session.add(ticket)

            # Mark seat as BOOKED
            seat.status = "BOOKED"

            # Remove Seat Lock
            lock = SeatLock.query.filter_by(seat_id=seat_id).first()
            if lock:
                db.session.delete(lock)

        db.session.commit()

        # 6. Send asynchronous/sync confirmation email
        try:
            send_booking_confirmation(booking)
        except Exception:
            pass  # Non-blocking for client response

        return True, "Booking confirmed successfully!", booking

    except Exception as e:
        db.session.rollback()
        return False, f"Transaction error: {str(e)}", None
