import secrets
from flask import Blueprint, render_template, request, jsonify, session
from models import db, utcnow, Event, Seat, SeatLock
from services.seat_lock_service import lock_seats, release_seats, clean_expired_locks, get_session_active_locks
from config import Config

seat_bp = Blueprint("seats", __name__)


def get_or_create_session_token() -> str:
    """Ensures a unique session token exists for the client."""
    if "session_token" not in session:
        session["session_token"] = secrets.token_hex(16)
    return session["session_token"]


@seat_bp.route("/events/<int:event_id>/seats")
def seat_selection_view(event_id: int):
    """Renders dynamic interactive seat map page for the event."""
    event = db.session.get(Event, event_id)
    if not event:
        return jsonify({"success": False, "message": "Event not found."}), 404
    session_token = get_or_create_session_token()
    clean_expired_locks()

    active_locks = get_session_active_locks(session_token, event_id=event.id)

    return render_template(
        "seat_selection.html",
        event=event,
        active_locks=active_locks,
        max_tickets=Config.MAX_SEATS_PER_BOOKING,
        lock_duration=Config.SEAT_LOCK_DURATION_SECONDS,
    )


@seat_bp.route("/api/events/<int:event_id>/seats", methods=["GET"])
def api_get_event_seats(event_id: int):
    """
    Returns seat layout structure for the event,
    differentiating seats locked by the current user vs others.
    """
    event = db.session.get(Event, event_id)
    if not event:
        return jsonify({"success": False, "message": "Event not found."}), 404

    session_token = get_or_create_session_token()
    clean_expired_locks()
    now = utcnow()

    # Query all seats for this event
    seats = Seat.query.filter_by(event_id=event_id).order_by(Seat.id.asc()).all()

    # Query all active locks for this event
    seat_locks = db.session.query(SeatLock).join(Seat, SeatLock.seat_id == Seat.id)\
        .filter(Seat.event_id == event_id, SeatLock.expires_at > now).all()

    lock_map = {l.seat_id: l for l in seat_locks}

    seats_data = []
    for s in seats:
        seat_status = s.status
        is_my_lock = False
        remaining = 0

        if s.status == "ADMIN_LOCKED":
            seat_status = "ADMIN_LOCKED"
        elif s.id in lock_map:
            lock = lock_map[s.id]
            if lock.session_token == session_token:
                is_my_lock = True
                seat_status = "SELECTED"
                remaining = max(0, int((lock.expires_at - now).total_seconds()))
            else:
                seat_status = "LOCKED"

        seats_data.append({
            "id": s.id,
            "seat_number": s.seat_number,
            "section": s.section,
            "category": s.category,
            "price": float(s.price),
            "status": seat_status,
            "is_my_lock": is_my_lock,
            "seconds_remaining": remaining,
            "admin_reserve_reason": s.admin_reserve_reason,
            "section_id": s.section_id,
            "row_label": s.row_label,
            "seat_index": s.seat_index,
        })

    sections_data = [sec.to_dict() for sec in event.sections]

    return jsonify({
        "success": True,
        "event_id": event_id,
        "event_type": event.event_type,
        "total_seats": len(seats_data),
        "sections": sections_data,
        "seats": seats_data,
    })


@seat_bp.route("/api/events/<int:event_id>/seat-status", methods=["GET"])
def api_poll_seat_status(event_id: int):
    """Real-time polling endpoint for frontend seat status synchronization."""
    session_token = get_or_create_session_token()
    clean_expired_locks()
    now = utcnow()

    seats = Seat.query.filter_by(event_id=event_id).all()
    locks = db.session.query(SeatLock).join(Seat, SeatLock.seat_id == Seat.id)\
        .filter(Seat.event_id == event_id, SeatLock.expires_at > now).all()

    lock_map = {l.seat_id: l for l in locks}

    status_map = {}
    reason_map = {}
    for s in seats:
        if s.status == "BOOKED":
            status_map[s.id] = "BOOKED"
        elif s.status == "ADMIN_LOCKED":
            status_map[s.id] = "ADMIN_LOCKED"
            if s.admin_reserve_reason:
                reason_map[s.id] = s.admin_reserve_reason
        elif s.id in lock_map:
            lock = lock_map[s.id]
            status_map[s.id] = "SELECTED" if lock.session_token == session_token else "LOCKED"
        else:
            status_map[s.id] = "AVAILABLE"

    return jsonify({
        "success": True,
        "event_id": event_id,
        "status_map": status_map,
        "reason_map": reason_map,
        "timestamp": now.isoformat(),
    })


@seat_bp.route("/api/seats/lock", methods=["POST"])
def api_lock_seats():
    """Acquires or refreshes 5-minute server-side lock on selected seats."""
    data = request.get_json() or {}
    event_id = data.get("event_id")
    seat_ids = data.get("seat_ids", [])

    if not event_id or not seat_ids:
        return jsonify({"success": False, "message": "Event ID and seat IDs are required."}), 400

    session_token = get_or_create_session_token()
    user_id = session.get("user_id")

    success, message, lock_info = lock_seats(
        event_id=int(event_id),
        seat_ids=[int(s) for s in seat_ids],
        session_token=session_token,
        user_id=user_id
    )

    status_code = 200 if success else 409
    return jsonify({
        "success": success,
        "message": message,
        "data": lock_info
    }), status_code


@seat_bp.route("/api/seats/release", methods=["POST"])
def api_release_seats():
    """Releases active seat locks."""
    data = request.get_json() or {}
    seat_ids = data.get("seat_ids")

    session_token = get_or_create_session_token()
    clean_seat_ids = [int(s) for s in seat_ids] if seat_ids else None

    success, message = release_seats(session_token, clean_seat_ids)
    return jsonify({"success": success, "message": message})
