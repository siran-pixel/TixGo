from models import db, Booking, Seat, Ticket


def test_full_booking_flow(auth_client, app):
    """Test end-to-end booking flow from locking seats to ticket creation."""
    # 1. Lock Seats 1 and 2
    lock_res = auth_client.post(
        "/api/seats/lock",
        json={"event_id": 1, "seat_ids": [1, 2]},
    )
    assert lock_res.status_code == 200

    # 2. Submit Attendee Details
    attendees_payload = {
        "attendees": [
            {"seat_id": 1, "full_name": "John Doe", "age": "30", "phone": "9876543210", "city": "Coimbatore"},
            {"seat_id": 2, "full_name": "Jane Smith", "age": "28", "phone": "9876543211", "city": "Coimbatore"},
        ]
    }
    att_res = auth_client.post("/booking/attendees?event_id=1", json=attendees_payload)
    assert att_res.status_code == 200

    # 3. Process Payment
    pay_res = auth_client.post(
        "/api/payment/process",
        json={
            "payment_method": "UPI",
            "payment_details": {"upi_id": "john@okaxis"},
        },
    )
    assert pay_res.status_code == 200
    pay_data = pay_res.get_json()
    assert pay_data["success"] is True
    booking_ref = pay_data["booking_reference"]
    assert booking_ref.startswith("BK-")

    # 4. Verify Database State
    with app.app_context():
        booking = Booking.query.filter_by(booking_reference=booking_ref).first()
        assert booking is not None
        assert booking.total_tickets == 2
        assert len(booking.attendees) == 2
        assert len(booking.tickets) == 2

        # Seats must be marked BOOKED
        s1 = db.session.get(Seat, 1)
        s2 = db.session.get(Seat, 2)
        assert s1.status == "BOOKED"
        assert s2.status == "BOOKED"

        # Tickets must have QR paths
        for t in booking.tickets:
            assert t.ticket_number.startswith("TKT-")
            assert "/static/qr/" in t.qr_code_path

    # 5. Access Consolidated Tickets Page
    ticket_page_res = auth_client.get(f"/tickets/{booking_ref}")
    assert ticket_page_res.status_code == 200
    assert bytes(booking_ref, "utf-8") in ticket_page_res.data
    assert b"John Doe" in ticket_page_res.data
    assert b"Jane Smith" in ticket_page_res.data
