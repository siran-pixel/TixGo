import json
import pytest
from datetime import date, datetime, timedelta
from models import db, Event, Seat, EventSection, Booking, Attendee, SeatLock
from services.seat_generator_service import provision_dynamic_layout, get_default_sections_for_event_type
from services.booking_service import execute_booking_transaction


def test_admin_seat_layouts_catalog_view(admin_client):
    """Test authorized admin can access the Seat Layout Management catalog."""
    response = admin_client.get("/admin/seat-layouts")
    assert response.status_code == 200
    assert b"Dynamic Seat Layout & Pricing Management" in response.data
    assert b"Event Seating Arrangements" in response.data


def test_admin_layout_designer_view(admin_client):
    """Test authorized admin can open the layout designer for an event."""
    response = admin_client.get("/admin/events/1/layout")
    assert response.status_code == 200
    assert b"Layout Designer" in response.data
    assert b"Live Seating Layout Preview" in response.data


def test_admin_layout_preview_api(admin_client):
    """Test AJAX preview calculation without modifying database."""
    preview_payload = {
        "sections": [
            {
                "name": "Elite",
                "section_type": "Section",
                "price": 2500.0,
                "color": "#a855f7",
                "rows": [
                    {"row_name": "A", "seat_count": 10},
                    {"row_name": "B", "seat_count": 10},
                    {"row_name": "C", "seat_count": 10},
                ],
            },
            {
                "name": "Platinum",
                "section_type": "Section",
                "price": 1500.0,
                "color": "#3b82f6",
                "rows": [
                    {"row_name": "A", "seat_count": 10},
                    {"row_name": "B", "seat_count": 15},
                ],
            },
        ]
    }
    response = admin_client.post(
        "/admin/api/events/1/layout/preview",
        json=preview_payload,
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert data["total_seats"] == 55  # (10+10+10) + (10+15)
    assert data["total_sections"] == 2
    assert data["min_price"] == 1500.0
    assert data["max_price"] == 2500.0
    # Potential revenue = (30 * 2500) + (25 * 1500) = 75000 + 37500 = 112500
    assert data["potential_revenue"] == 112500.0


def test_concert_dynamic_section_based_seating_generation(admin_client, app):
    """
    Test Concert Event: Admin creates custom sections (Elite, Platinum, Silver)
    with non-uniform rows and seats as specified in prompt.
    """
    with app.app_context():
        # Create a new concert event
        concert = Event(
            name="Coldplay World Tour 2026",
            description="Epic live stadium concert",
            event_type="Concert",
            banner_image="/static/images/event_concert.jpg",
            venue="Bhartiya Mall Grounds",
            city="Bengaluru",
            event_date=date.today() + timedelta(days=10),
            event_time=datetime.strptime("18:00", "%H:%M").time(),
            total_seats=0,
            status="DRAFT",
        )
        db.session.add(concert)
        db.session.commit()
        concert_id = concert.id

    # Configure Concert Sections via Admin API
    concert_sections = [
        {
            "name": "Elite",
            "section_type": "Section",
            "price": 2500.0,
            "color": "#a855f7",
            "description": "Front stage luxury seating",
            "rows": [
                {"row_name": "A", "seat_count": 10},
                {"row_name": "B", "seat_count": 10},
                {"row_name": "C", "seat_count": 10},
            ],
        },
        {
            "name": "Platinum",
            "section_type": "Section",
            "price": 1500.0,
            "color": "#3b82f6",
            "description": "Prime elevated view",
            "rows": [
                {"row_name": "A", "seat_count": 10},
                {"row_name": "B", "seat_count": 15},
                {"row_name": "C", "seat_count": 15},
                {"row_name": "D", "seat_count": 20},
            ],
        },
        {
            "name": "Silver",
            "section_type": "Section",
            "price": 800.0,
            "color": "#94a3b8",
            "description": "Acoustic amphitheater seating",
            "rows": [
                {"row_name": "A", "seat_count": 20},
                {"row_name": "B", "seat_count": 20},
                {"row_name": "C", "seat_count": 20},
                {"row_name": "D", "seat_count": 25},
                {"row_name": "E", "seat_count": 25},
            ],
        },
    ]

    response = admin_client.post(
        f"/admin/events/{concert_id}/layout",
        json={"sections": concert_sections, "publish": True},
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    # Elite: 30 + Platinum: 60 + Silver: 110 = 200 seats total
    assert data["seat_count"] == 200

    with app.app_context():
        ev = db.session.get(Event, concert_id)
        assert ev.total_seats == 200
        assert ev.status == "ACTIVE"
        assert len(ev.sections) == 3

        # Verify sections in database
        sec_names = [s.name for s in ev.sections]
        assert sec_names == ["Elite", "Platinum", "Silver"]

        elite_sec = next(s for s in ev.sections if s.name == "Elite")
        assert elite_sec.total_seats == 30
        assert float(elite_sec.price) == 2500.0

        # Verify all seat numbers are strictly unique across sections
        seat_numbers = [s.seat_number for s in ev.seats.all()]
        assert len(seat_numbers) == 200
        assert len(set(seat_numbers)) == 200

        # Verify seat row labels and prices
        sample_elite_a1 = ev.seats.filter_by(row_label="A", seat_index=1, section="Elite").first()
        assert sample_elite_a1 is not None
        assert float(sample_elite_a1.price) == 2500.0


def test_cricket_stand_based_seating_generation(admin_client, app):
    """
    Test Cricket Match: Admin creates custom stands (North Stand, South Stand, VIP Stand)
    with custom prices and row capacities.
    """
    with app.app_context():
        cricket = Event(
            name="India vs England T20 Clash",
            description="High voltage cricket clash",
            event_type="Cricket",
            banner_image="/static/images/event_cricket.jpg",
            venue="Eden Gardens Stadium",
            city="Kolkata",
            event_date=date.today() + timedelta(days=15),
            event_time=datetime.strptime("19:30", "%H:%M").time(),
            total_seats=0,
            status="DRAFT",
        )
        db.session.add(cricket)
        db.session.commit()
        cricket_id = cricket.id

    cricket_stands = [
        {
            "name": "North Stand",
            "section_type": "Stand",
            "price": 500.0,
            "color": "#2563eb",
            "rows": [
                {"row_name": "A", "seat_count": 50},
                {"row_name": "B", "seat_count": 50},
                {"row_name": "C", "seat_count": 60},
            ],
        },
        {
            "name": "South Stand",
            "section_type": "Stand",
            "price": 750.0,
            "color": "#0ea5e9",
            "rows": [
                {"row_name": "A", "seat_count": 40},
                {"row_name": "B", "seat_count": 50},
                {"row_name": "C", "seat_count": 50},
            ],
        },
        {
            "name": "VIP Stand",
            "section_type": "Stand",
            "price": 2000.0,
            "color": "#eab308",
            "rows": [
                {"row_name": "A", "seat_count": 20},
                {"row_name": "B", "seat_count": 20},
            ],
        },
    ]

    response = admin_client.post(
        f"/admin/events/{cricket_id}/layout",
        json={"sections": cricket_stands, "publish": True},
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    # North (160) + South (140) + VIP (40) = 340 seats total
    assert data["seat_count"] == 340

    with app.app_context():
        ev = db.session.get(Event, cricket_id)
        assert ev.total_seats == 340
        assert len(ev.sections) == 3


def test_cannot_overwrite_layout_when_bookings_exist(admin_client, auth_client, app):
    """
    Test Safety Rule: If customer bookings exist, admin cannot silently destroy or overwrite seats.
    """
    with app.app_context():
        # Find or create a seat in event 1 and mark as BOOKED
        seat = db.session.get(Seat, 10)
        seat.status = "BOOKED"
        db.session.commit()

    # Attempt to overwrite layout
    response = admin_client.post(
        "/admin/events/1/layout",
        json={
            "sections": [
                {
                    "name": "New Section",
                    "price": 1000.0,
                    "rows": [{"row_name": "A", "seat_count": 10}],
                }
            ]
        },
    )
    assert response.status_code == 400
    data = response.get_json()
    assert data["success"] is False
    assert "already has" in data["message"]
    assert "booked ticket" in data["message"]


def test_admin_locking_and_booking_on_dynamic_layout(admin_client, auth_client, app):
    """
    Test Admin Seat Locking integration with dynamic layouts:
    Admin locks a seat for 'Resource Person', verifying that users cannot select it,
    while another seat in the section can be selected and booked normally.
    """
    with app.app_context():
        event = Event(
            name="Zakir Comedy Fest 2026",
            description="Comedy special",
            event_type="General",
            banner_image="/static/images/event_cinema.jpg",
            venue="Town Hall",
            city="Delhi",
            event_date=date.today() + timedelta(days=5),
            event_time=datetime.strptime("20:00", "%H:%M").time(),
            total_seats=0,
            status="ACTIVE",
        )
        db.session.add(event)
        db.session.commit()
        event_id = event.id

        sections_cfg = [
            {
                "name": "Front VIP",
                "section_type": "Section",
                "price": 1000.0,
                "color": "#f97316",
                "rows": [
                    {"row_name": "A", "seat_count": 5},
                    {"row_name": "B", "seat_count": 5},
                ],
            }
        ]
        provision_dynamic_layout(event, sections_cfg)
        seats = Seat.query.filter_by(event_id=event_id).all()
        seat1_id = seats[0].id
        seat2_id = seats[1].id

    # 1. Admin locks seat1 for 'Resource Person'
    res_lock = admin_client.post(
        f"/admin/api/events/{event_id}/seats/lock",
        json={"seat_ids": [seat1_id], "reason": "Resource Person"},
    )
    assert res_lock.status_code == 200

    # 2. User tries to lock seat1 -> must fail with 409
    res_user_fail = auth_client.post(
        "/api/seats/lock",
        json={"event_id": event_id, "seat_ids": [seat1_id]},
    )
    assert res_user_fail.status_code == 409

    # 3. User locks seat2 -> succeeds
    res_user_ok = auth_client.post(
        "/api/seats/lock",
        json={"event_id": event_id, "seat_ids": [seat2_id]},
    )
    assert res_user_ok.status_code == 200

    # 4. Public API contains section details and correct statuses
    res_public = auth_client.get(f"/api/events/{event_id}/seats")
    assert res_public.status_code == 200
    pub_data = res_public.get_json()
    assert len(pub_data["sections"]) == 1
    assert pub_data["sections"][0]["name"] == "Front VIP"
    seats_map = {s["id"]: s for s in pub_data["seats"]}
    assert seats_map[seat1_id]["status"] == "ADMIN_LOCKED"
    assert seats_map[seat1_id]["admin_reserve_reason"] == "Resource Person"
    assert seats_map[seat2_id]["status"] == "SELECTED"
