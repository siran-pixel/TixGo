from models import db, Event, Seat


def test_admin_login(client):
    """Test admin authentication."""
    response = client.post(
        "/admin/login",
        json={
            "email": "admin1234@gmail.com",
            "password": "admin@1234",
        },
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True


def test_admin_dashboard_unauthorized(client):
    """Test unauthorized access to admin dashboard redirects to admin login."""
    response = client.get("/admin/dashboard")
    assert response.status_code == 302
    assert "/admin/login" in response.headers["Location"]


def test_admin_dashboard_authorized(admin_client):
    """Test authorized admin dashboard view."""
    response = admin_client.get("/admin/dashboard")
    assert response.status_code == 200
    assert b"Dashboard Overview" in response.data


def test_admin_add_event_and_seat_generation(admin_client, app):
    """Test admin adding an event and automatic seat provisioning."""
    response = admin_client.post(
        "/admin/events/add",
        data={
            "name": "Rock Fest 2026",
            "description": "Epic rock concert with live bands.",
            "event_type": "Concert",
            "banner_image": "/static/images/event_concert.jpg",
            "venue": "Grand Arena",
            "city": "Bengaluru",
            "event_date": "2026-09-15",
            "event_time": "19:00",
            "total_seats": "1050",
            "price": "2000",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200

    with app.app_context():
        event = Event.query.filter_by(name="Rock Fest 2026").first()
        assert event is not None
        assert event.total_seats == 1050
        assert event.seats.count() == 1050


def test_admin_seat_management_view(admin_client):
    """Test authorized admin can access the Seat Management interface."""
    response = admin_client.get("/admin/seats?event_id=1")
    assert response.status_code == 200
    assert b"Seat Management" in response.data
    assert b"Lock for Resource Persons" in response.data


def test_admin_lock_and_unlock_seats_for_resource_persons(admin_client, app):
    """Test admin successfully locks and unlocks seats for VIP/Resource Persons."""
    # 1. Admin locks seat 1 and 2 for 'Chief Guest'
    res_lock = admin_client.post(
        "/admin/api/events/1/seats/lock",
        json={
            "seat_ids": [1, 2],
            "reason": "Chief Guest",
        },
    )
    assert res_lock.status_code == 200
    data_lock = res_lock.get_json()
    assert data_lock["success"] is True
    assert "Chief Guest" in data_lock["message"]

    with app.app_context():
        seat1 = db.session.get(Seat, 1)
        seat2 = db.session.get(Seat, 2)
        assert seat1.status == "ADMIN_LOCKED"
        assert seat1.admin_reserve_reason == "Chief Guest"
        assert seat2.status == "ADMIN_LOCKED"
        assert seat2.admin_reserve_reason == "Chief Guest"

    # 2. Public API reflects ADMIN_LOCKED
    res_public = admin_client.get("/api/events/1/seats")
    assert res_public.status_code == 200
    public_seats = {s["id"]: s for s in res_public.get_json()["seats"]}
    assert public_seats[1]["status"] == "ADMIN_LOCKED"
    assert public_seats[1]["admin_reserve_reason"] == "Chief Guest"

    # 3. Admin unlocks seat 1 and 2 back to AVAILABLE
    res_unlock = admin_client.post(
        "/admin/api/events/1/seats/unlock",
        json={"seat_ids": [1, 2]},
    )
    assert res_unlock.status_code == 200
    data_unlock = res_unlock.get_json()
    assert data_unlock["success"] is True

    with app.app_context():
        seat1 = db.session.get(Seat, 1)
        seat2 = db.session.get(Seat, 2)
        assert seat1.status == "AVAILABLE"
        assert seat1.admin_reserve_reason is None
        assert seat2.status == "AVAILABLE"
        assert seat2.admin_reserve_reason is None


def test_user_cannot_lock_admin_reserved_seat(admin_client, auth_client):
    """Test regular users cannot lock or select an admin-reserved seat."""
    # 1. Admin locks seat 3 for 'Resource Person'
    res_admin = admin_client.post(
        "/admin/api/events/1/seats/lock",
        json={"seat_ids": [3], "reason": "Resource Person"},
    )
    assert res_admin.status_code == 200

    # 2. Regular user tries to lock seat 3 -> Must be rejected with 409
    res_user = auth_client.post(
        "/api/seats/lock",
        json={"event_id": 1, "seat_ids": [3]},
    )
    assert res_user.status_code == 409
    data_user = res_user.get_json()
    assert data_user["success"] is False
    assert "reserved by the admin" in data_user["message"]

    # 3. Clean up by unlocking
    admin_client.post("/admin/api/events/1/seats/unlock", json={"seat_ids": [3]})


def test_unauthorized_user_cannot_lock_admin_seats(client):
    """Test unauthenticated/non-admin user is rejected from admin seat lock endpoint."""
    response = client.post(
        "/admin/api/events/1/seats/lock",
        json={"seat_ids": [1], "reason": "Hacker"},
    )
    assert response.status_code == 403

