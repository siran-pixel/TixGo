from datetime import timedelta
from typing import List, Dict, Any, Tuple, Optional
from models import db, utcnow, Seat, SeatLock
from config import Config


def clean_expired_locks():
    """
    Finds all expired seat locks, marks the associated seats as 'AVAILABLE',
    and removes the expired lock records.
    """
    now = utcnow()
    expired_locks = SeatLock.query.filter(SeatLock.expires_at <= now).all()

    if not expired_locks:
        return 0

    cleaned_count = 0
    for lock in expired_locks:
        seat = db.session.get(Seat, lock.seat_id)
        if seat and seat.status == "LOCKED":
            seat.status = "AVAILABLE"
        db.session.delete(lock)
        cleaned_count += 1

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()

    return cleaned_count


def lock_seats(
    event_id: int,
    seat_ids: List[int],
    session_token: str,
    user_id: Optional[int] = None
) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Locks specified seats for a session for 5 minutes.
    Enforces maximum 10 seats limit and server-side concurrency safety.
    """
    # 1. Clean any expired locks across the system
    clean_expired_locks()

    if not seat_ids:
        return False, "No seats selected to lock.", {}

    # Check total requested count
    if len(seat_ids) > Config.MAX_SEATS_PER_BOOKING:
        return False, f"Maximum {Config.MAX_SEATS_PER_BOOKING} tickets can be booked in one transaction.", {}

    # 2. Release any previous locks held by this session that are NOT in the active seat_ids list
    existing_session_locks = SeatLock.query.filter_by(session_token=session_token).all()
    for old_lock in existing_session_locks:
        if old_lock.seat_id not in seat_ids:
            old_seat = db.session.get(Seat, old_lock.seat_id)
            if old_seat and old_seat.status == "LOCKED":
                old_seat.status = "AVAILABLE"
            db.session.delete(old_lock)

    # 3. Query all targeted seats
    seats = Seat.query.filter(Seat.id.in_(seat_ids), Seat.event_id == event_id).all()
    if len(seats) != len(seat_ids):
        return False, "One or more selected seats could not be found for this event.", {}

    # 4. Verify each seat's availability
    now = utcnow()
    expires_at = now + timedelta(seconds=Config.SEAT_LOCK_DURATION_SECONDS)

    for seat in seats:
        if seat.status == "BOOKED":
            return False, f"Seat {seat.seat_number} is already booked.", {}

        if seat.status == "ADMIN_LOCKED":
            reason_txt = f" ({seat.admin_reserve_reason})" if seat.admin_reserve_reason else ""
            return False, f"Seat {seat.seat_number} is reserved by the admin{reason_txt} and cannot be selected.", {}

        if seat.status == "LOCKED":
            # Check if locked by the same session
            lock = SeatLock.query.filter_by(seat_id=seat.id).first()
            if lock and lock.session_token != session_token and not lock.is_expired:
                return False, f"Seat {seat.seat_number} is currently locked by another user.", {}

    # 5. Apply or refresh locks
    for seat in seats:
        seat.status = "LOCKED"
        lock = SeatLock.query.filter_by(seat_id=seat.id).first()
        if lock:
            lock.session_token = session_token
            lock.user_id = user_id
            lock.locked_at = now
            lock.expires_at = expires_at
        else:
            new_lock = SeatLock(
                seat_id=seat.id,
                user_id=user_id,
                session_token=session_token,
                locked_at=now,
                expires_at=expires_at,
            )
            db.session.add(new_lock)

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return False, f"Database locking error: {str(e)}", {}

    locked_seat_data = [s.to_dict() for s in seats]
    return True, "Seats successfully locked.", {
        "seats": locked_seat_data,
        "expires_at": expires_at.isoformat(),
        "seconds_remaining": Config.SEAT_LOCK_DURATION_SECONDS,
        "total_seats": len(seats),
    }


def release_seats(session_token: str, seat_ids: Optional[List[int]] = None) -> Tuple[bool, str]:
    """Releases active seat locks held by a session."""
    query = SeatLock.query.filter_by(session_token=session_token)
    if seat_ids:
        query = query.filter(SeatLock.seat_id.in_(seat_ids))

    locks = query.all()
    for lock in locks:
        seat = db.session.get(Seat, lock.seat_id)
        if seat and seat.status == "LOCKED":
            seat.status = "AVAILABLE"
        db.session.delete(lock)

    try:
        db.session.commit()
        return True, f"Released {len(locks)} seat lock(s)."
    except Exception as e:
        db.session.rollback()
        return False, f"Failed to release locks: {str(e)}"


def get_session_active_locks(session_token: str, event_id: Optional[int] = None) -> List[Dict[str, Any]]:
    """Retrieves list of active locked seats for the given session."""
    clean_expired_locks()
    now = utcnow()

    query = db.session.query(SeatLock, Seat).join(Seat, SeatLock.seat_id == Seat.id)\
        .filter(SeatLock.session_token == session_token, SeatLock.expires_at > now)

    if event_id:
        query = query.filter(Seat.event_id == event_id)

    results = []
    for lock, seat in query.all():
        data = seat.to_dict()
        data["expires_at"] = lock.expires_at.isoformat()
        data["seconds_remaining"] = max(0, int((lock.expires_at - now).total_seconds()))
        results.append(data)

    return results


def admin_lock_seats(
    event_id: int,
    seat_ids: List[int],
    reason: Optional[str] = "Resource Person"
) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Locks specified seats permanently for resource persons, VIPs, or guests by the admin.
    Releases any temporary session locks and prevents regular users from booking.
    Cannot lock already BOOKED seats.
    """
    if not seat_ids:
        return False, "No seats selected to lock.", {}

    reason_str = (reason or "Resource Person").strip()

    try:
        # 1. Query all targeted seats
        seats = Seat.query.filter(Seat.id.in_(seat_ids), Seat.event_id == event_id).all()
        if len(seats) != len(seat_ids):
            return False, "One or more selected seats could not be found for this event.", {}

        # 2. Check if any seat is already booked
        for seat in seats:
            if seat.status == "BOOKED":
                return False, f"Seat {seat.seat_number} is already booked by a customer and cannot be locked.", {}

        # 3. Clean and remove any temporary user locks on these seats
        SeatLock.query.filter(SeatLock.seat_id.in_(seat_ids)).delete(synchronize_session=False)

        # 4. Mark seats as ADMIN_LOCKED with reason
        for seat in seats:
            seat.status = "ADMIN_LOCKED"
            seat.admin_reserve_reason = reason_str

        db.session.commit()
        return True, f"Successfully locked {len(seats)} seat(s) for '{reason_str}'.", {
            "locked_seats": [s.to_dict() for s in seats],
            "total_locked": len(seats),
        }
    except Exception as e:
        db.session.rollback()
        return False, f"Database error locking seats: {str(e)}", {}


def admin_unlock_seats(
    event_id: int,
    seat_ids: List[int]
) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Unlocks previously admin-locked seats and restores them to AVAILABLE.
    Only unlocks seats that are currently ADMIN_LOCKED (preserves BOOKED seats).
    """
    if not seat_ids:
        return False, "No seats selected to unlock.", {}

    try:
        seats = Seat.query.filter(Seat.id.in_(seat_ids), Seat.event_id == event_id).all()
        if not seats:
            return False, "No matching seats found.", {}

        unlocked_seats = []
        for seat in seats:
            if seat.status == "ADMIN_LOCKED":
                seat.status = "AVAILABLE"
                seat.admin_reserve_reason = None
                unlocked_seats.append(seat)

        if not unlocked_seats:
            return False, "None of the selected seats are currently locked by the administrator.", {}

        db.session.commit()
        return True, f"Successfully unlocked {len(unlocked_seats)} seat(s) to AVAILABLE.", {
            "unlocked_seats": [s.to_dict() for s in unlocked_seats],
            "total_unlocked": len(unlocked_seats),
        }
    except Exception as e:
        db.session.rollback()
        return False, f"Database error unlocking seats: {str(e)}", {}
