from datetime import date
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from models import db, Event, Seat, SeatLock, Booking
from utils.security import login_required, get_current_user
from utils.validators import validate_attendee_data
from services.seat_lock_service import get_session_active_locks, clean_expired_locks
from services.booking_service import calculate_pricing
from config import Config

booking_bp = Blueprint("booking", __name__)


@booking_bp.route("/booking/attendees", methods=["GET", "POST"])
@login_required
def attendee_details():
    """Collects individual attendee details for each locked seat."""
    session_token = session.get("session_token", "")
    event_id = request.args.get("event_id", type=int)

    clean_expired_locks()
    active_locks = get_session_active_locks(session_token, event_id=event_id)

    if not active_locks:
        flash("You do not have any active seat locks. Please select seats to continue.", "warning")
        return redirect(url_for("events.landing_page") if not event_id else url_for("seats.seat_selection_view", event_id=event_id))

    event = db.session.get(Event, active_locks[0]["event_id"])
    if not event:
        flash("Event not found.", "danger")
        return redirect(url_for("events.landing_page"))

    if request.method == "POST":
        data = request.get_json() if request.is_json else request.form
        attendees = []

        # Parse attendee inputs
        for idx, seat in enumerate(active_locks):
            if request.is_json:
                att_list = data.get("attendees", [])
                att_item = att_list[idx] if idx < len(att_list) else {}
                name = att_item.get("full_name", "")
                age = att_item.get("age", "")
                phone = att_item.get("phone", "")
                city = att_item.get("city", "")
            else:
                name = data.get(f"attendee_name_{seat['id']}", "")
                age = data.get(f"attendee_age_{seat['id']}", "")
                phone = data.get(f"attendee_phone_{seat['id']}", "")
                city = data.get(f"attendee_city_{seat['id']}", "")

            att_record = {
                "seat_id": seat["id"],
                "seat_number": seat["seat_number"],
                "section": seat["section"],
                "category": seat["category"],
                "price": seat["price"],
                "full_name": str(name).strip(),
                "age": age,
                "phone": str(phone).strip(),
                "city": str(city).strip(),
            }

            is_valid, err_msg = validate_attendee_data(att_record)
            if not is_valid:
                msg = f"Error for Seat {seat['seat_number']}: {err_msg}"
                if request.is_json:
                    return jsonify({"success": False, "message": msg}), 400
                flash(msg, "danger")
                return render_template("attendee_details.html", event=event, seats=active_locks, form_data=data)

            attendees.append(att_record)

        session["pending_booking"] = {
            "event_id": event.id,
            "attendees": attendees,
        }

        if request.is_json:
            return jsonify({"success": True, "redirect_url": url_for("booking.booking_review")})
        return redirect(url_for("booking.booking_review"))

    return render_template("attendee_details.html", event=event, seats=active_locks)


@booking_bp.route("/booking/review")
@login_required
def booking_review():
    """Displays consolidated booking review with pricing breakdown before payment."""
    session_token = session.get("session_token", "")
    pending = session.get("pending_booking")

    if not pending or not pending.get("attendees"):
        flash("No active booking in progress. Please select seats.", "warning")
        return redirect(url_for("events.landing_page"))

    clean_expired_locks()
    active_locks = get_session_active_locks(session_token, event_id=pending["event_id"])
    active_seat_ids = {l["id"] for l in active_locks}

    # Verify that all pending attendee seats are still locked
    attendees = pending["attendees"]
    for att in attendees:
        if att["seat_id"] not in active_seat_ids:
            flash("Your seat lock has expired. Please select your seats again.", "danger")
            session.pop("pending_booking", None)
            return redirect(url_for("seats.seat_selection_view", event_id=pending["event_id"]))

    event = db.session.get(Event, pending["event_id"])
    if not event:
        flash("Event not found.", "danger")
        return redirect(url_for("events.landing_page"))

    seats = Seat.query.filter(Seat.id.in_([a["seat_id"] for a in attendees])).all()
    pricing = calculate_pricing(seats)

    return render_template(
        "booking_review.html",
        event=event,
        attendees=attendees,
        pricing=pricing,
        seconds_remaining=active_locks[0]["seconds_remaining"] if active_locks else 0
    )


@booking_bp.route("/my-bookings")
@login_required
def my_bookings():
    """User bookings history divided into upcoming and past events."""
    user = get_current_user()
    today_date = date.today()

    all_bookings = Booking.query.filter_by(user_id=user.id)\
        .join(Event, Booking.event_id == Event.id)\
        .order_by(Booking.created_at.desc()).all()

    upcoming_bookings = [b for b in all_bookings if b.event and b.event.event_date >= today_date]
    past_bookings = [b for b in all_bookings if b.event and b.event.event_date < today_date]

    return render_template(
        "my_bookings.html",
        upcoming_bookings=upcoming_bookings,
        past_bookings=past_bookings,
    )


@booking_bp.route("/api/user/bookings", methods=["GET"])
@login_required
def api_user_bookings():
    """Returns JSON list of bookings for current user."""
    user = get_current_user()
    bookings = Booking.query.filter_by(user_id=user.id).order_by(Booking.created_at.desc()).all()
    return jsonify({"success": True, "bookings": [b.to_dict() for b in bookings]})
