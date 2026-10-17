from typing import Optional, Dict, Any
from models import db, Booking, Ticket, Attendee


def get_consolidated_booking_details(booking_identifier: str) -> Optional[Dict[str, Any]]:
    """
    Retrieves full consolidated ticket details for a given booking reference or numeric ID.
    Enables single-page viewing of all attendees and individual QR codes.
    """
    if str(booking_identifier).isdigit():
        booking = db.session.get(Booking, int(booking_identifier))
    else:
        booking = Booking.query.filter_by(booking_reference=str(booking_identifier).strip()).first()

    if not booking:
        return None

    tickets_list = []
    for att in booking.attendees:
        ticket = att.ticket
        seat = att.seat
        tickets_list.append({
            "ticket_id": ticket.id if ticket else None,
            "ticket_number": ticket.ticket_number if ticket else None,
            "ticket_status": ticket.ticket_status if ticket else "ACTIVE",
            "qr_code_path": ticket.qr_code_path if ticket else None,
            "attendee_name": att.full_name,
            "attendee_age": att.age,
            "attendee_phone": att.phone,
            "attendee_city": att.city,
            "seat_number": seat.seat_number if seat else "N/A",
            "section": seat.section if seat else "General",
            "category": seat.category if seat else "General",
            "price": float(seat.price) if seat else 0.0,
        })

    return {
        "booking_id": booking.id,
        "booking_reference": booking.booking_reference,
        "booking_status": booking.booking_status,
        "created_at": booking.created_at.strftime("%d %b %Y, %I:%M %p") if booking.created_at else None,
        "user_id": booking.user_id,
        "user_name": booking.user.full_name if booking.user else None,
        "user_email": booking.user.email if booking.user else None,
        "user_phone": booking.user.phone if booking.user else None,
        "event_id": booking.event_id,
        "event_name": booking.event.name if booking.event else None,
        "event_type": booking.event.event_type if booking.event else None,
        "banner_image": booking.event.banner_image if booking.event else None,
        "venue": booking.event.venue if booking.event else None,
        "city": booking.event.city if booking.event else None,
        "event_date": booking.event.event_date.strftime("%A, %d %B %Y") if booking.event and booking.event.event_date else None,
        "event_time": booking.event.event_time.strftime("%I:%M %p") if booking.event and booking.event.event_time else None,
        "total_tickets": booking.total_tickets,
        "subtotal": float(booking.subtotal),
        "convenience_fee": float(booking.convenience_fee),
        "tax": float(booking.tax),
        "total_amount": float(booking.total_amount),
        "payment_method": booking.payment.payment_method if booking.payment else "N/A",
        "transaction_id": booking.payment.transaction_id if booking.payment else "N/A",
        "payment_status": booking.payment.payment_status if booking.payment else "PENDING",
        "tickets": tickets_list,
    }
