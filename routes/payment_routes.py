import secrets
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from models import db, Event, Seat
from utils.security import login_required, get_current_user
from services.seat_lock_service import get_session_active_locks, clean_expired_locks
from services.booking_service import calculate_pricing, execute_booking_transaction

payment_bp = Blueprint("payment", __name__)


@payment_bp.route("/booking/payment")
@login_required
def payment_view():
    """Renders simulated multi-method payment gateway interface."""
    session_token = session.get("session_token", "")
    pending = session.get("pending_booking")

    if not pending or not pending.get("attendees"):
        flash("No pending booking found. Please select your seats.", "warning")
        return redirect(url_for("events.landing_page"))

    clean_expired_locks()
    active_locks = get_session_active_locks(session_token, event_id=pending["event_id"])
    active_seat_ids = {l["id"] for l in active_locks}

    attendees = pending["attendees"]
    for att in attendees:
        if att["seat_id"] not in active_seat_ids:
            flash("Your seat lock has expired before payment. Please reselect your seats.", "danger")
            session.pop("pending_booking", None)
            return redirect(url_for("seats.seat_selection_view", event_id=pending["event_id"]))

    event = db.session.get(Event, pending["event_id"])
    if not event:
        flash("Event not found.", "danger")
        return redirect(url_for("events.landing_page"))
    seats = Seat.query.filter(Seat.id.in_([a["seat_id"] for a in attendees])).all()
    pricing = calculate_pricing(seats)

    temp_order_id = f"ORD-{secrets.token_hex(4).upper()}"

    return render_template(
        "payment.html",
        event=event,
        attendees=attendees,
        pricing=pricing,
        order_id=temp_order_id,
        seconds_remaining=active_locks[0]["seconds_remaining"] if active_locks else 0
    )


@payment_bp.route("/api/payment/process", methods=["POST"])
@login_required
def api_process_payment():
    """
    Executes atomic booking transaction upon simulated payment confirmation.
    Recalculates authoritative DB pricing and verifies server-side locks.
    """
    user = get_current_user()
    session_token = session.get("session_token", "")
    pending = session.get("pending_booking")

    if not pending or not pending.get("attendees"):
        return jsonify({"success": False, "message": "No active booking session found."}), 400

    data = request.get_json() or {}
    payment_method = data.get("payment_method", "UPI").upper()
    payment_details = data.get("payment_details", {})

    success, message, booking = execute_booking_transaction(
        user_id=user.id,
        event_id=pending["event_id"],
        session_token=session_token,
        attendees_data=pending["attendees"],
        payment_method=payment_method,
        payment_details=payment_details
    )

    if not success:
        return jsonify({"success": False, "message": message}), 400

    # Clear pending booking from session
    session.pop("pending_booking", None)

    return jsonify({
        "success": True,
        "message": message,
        "booking_reference": booking.booking_reference,
        "redirect_url": url_for("tickets.view_ticket", booking_reference=booking.booking_reference)
    })
