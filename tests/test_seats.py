from datetime import datetime, timedelta
from models import db, utcnow, Seat, SeatLock
from services.seat_lock_service import clean_expired_locks


def test_get_event_seats(client):
    """Test retrieving seat map layout for cricket stadium event."""
    response = client.get("/api/events/1/seats")
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert data["total_seats"] == 2500

    # Verify Lower Stand (150 seats @ ₹2000 per stand) and Upper Stand (100 seats @ ₹1350 per stand)
    lower_seats = [s for s in data["seats"] if s["category"] == "Lower Stand"]
    upper_seats = [s for s in data["seats"] if s["category"] == "Upper Stand"]

    assert len(lower_seats) == 1500  # 10 stands * 150 seats
    assert len(upper_seats) == 1000  # 10 stands * 100 seats
    assert all(s["price"] == 2000.0 for s in lower_seats)
    assert all(s["price"] == 1350.0 for s in upper_seats)


def test_seat_lock_success(auth_client):
    """Test locking 2 available seats."""
    response = auth_client.post(
        "/api/seats/lock",
        json={"event_id": 1, "seat_ids": [1, 2]},
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert data["data"]["total_seats"] == 2
    assert data["data"]["seconds_remaining"] == 300


def test_max_tickets_limit_enforced(auth_client):
    """Test error when attempting to lock 11 seats (limit is 10)."""
    seat_ids = list(range(1, 12))  # 11 seats
    response = auth_client.post(
        "/api/seats/lock",
        json={"event_id": 1, "seat_ids": seat_ids},
    )
    assert response.status_code == 409
    data = response.get_json()
    assert data["success"] is False
    assert "Maximum 10 tickets" in data["message"]


def test_seat_lock_conflict(auth_client, client):
    """Test that User B cannot lock a seat already locked by User A."""
    # User A locks seat 5
    res1 = auth_client.post("/api/seats/lock", json={"event_id": 1, "seat_ids": [5]})
    assert res1.status_code == 200

    # User B (different session) tries to lock seat 5
    with client.session_transaction() as sess:
        sess["session_token"] = "different-session-token-999"

    res2 = client.post("/api/seats/lock", json={"event_id": 1, "seat_ids": [5]})
    assert res2.status_code == 409
    data = res2.get_json()
    assert data["success"] is False
    assert "currently locked by another user" in data["message"]


def test_expired_lock_auto_cleanup(app):
    """Test that expired locks are automatically cleared and seats restored to AVAILABLE."""
    with app.app_context():
        seat = db.session.get(Seat, 10)
        seat.status = "LOCKED"

        # Add expired lock (expired 10 seconds ago)
        expired_lock = SeatLock(
            seat_id=10,
            session_token="old-token",
            locked_at=utcnow() - timedelta(minutes=6),
            expires_at=utcnow() - timedelta(seconds=10),
        )
        db.session.add(expired_lock)
        db.session.commit()

        # Run cleanup
        cleaned = clean_expired_locks()
        assert cleaned >= 1

        # Check seat status
        seat_after = db.session.get(Seat, 10)
        assert seat_after.status == "AVAILABLE"


def test_deselect_and_reselect_seat_at_max_limit(auth_client, app):
    """
    Test selecting 10 seats, deselecting 1 seat, and selecting a new replacement seat.
    Ensures deselected seat is freed and replacement seat locks successfully.
    """
    # 1. Lock 10 seats (seats 1 to 10)
    initial_seats = list(range(1, 11))
    res1 = auth_client.post(
        "/api/seats/lock",
        json={"event_id": 1, "seat_ids": initial_seats},
    )
    assert res1.status_code == 200
    assert res1.get_json()["data"]["total_seats"] == 10

    # 2. Deselect seat 10 explicitly
    res_release = auth_client.post(
        "/api/seats/release",
        json={"seat_ids": [10]},
    )
    assert res_release.status_code == 200

    # Verify seat 10 is AVAILABLE again
    with app.app_context():
        seat10 = db.session.get(Seat, 10)
        assert seat10.status == "AVAILABLE"

    # 3. Select a new replacement seat (seat 11) alongside seats 1 to 9
    new_seats = list(range(1, 10)) + [11]  # 10 seats total
    res2 = auth_client.post(
        "/api/seats/lock",
        json={"event_id": 1, "seat_ids": new_seats},
    )
    assert res2.status_code == 200
    assert res2.get_json()["data"]["total_seats"] == 10

    # Verify seat 11 is now LOCKED and seat 10 is still AVAILABLE
    with app.app_context():
        seat11 = db.session.get(Seat, 11)
        assert seat11.status == "LOCKED"
        seat10 = db.session.get(Seat, 10)
        assert seat10.status == "AVAILABLE"
