import io
import zipfile
import csv
from datetime import datetime, date, timedelta
import pytest
from models import db, User, Admin, Event, EventSection, Seat, Booking, Attendee, Payment, Ticket
from services.export_service import (
    generate_date_wise_booking_csv,
    generate_section_wise_organizer_csv,
    generate_all_sections_zip,
    sanitize_csv_cell,
)


@pytest.fixture
def populated_booking_data(app):
    """Creates a sample event with dynamic sections, bookings, attendees, and payments."""
    with app.app_context():
        # Setup Event with sections
        event = Event(
            name="Coldplay World Tour 2026",
            description="Live concert event.",
            event_type="Concert",
            venue="DY Patil Stadium",
            city="Mumbai",
            event_date=date(2026, 11, 20),
            event_time=datetime.strptime("19:00", "%H:%M").time(),
            total_seats=100,
            status="ACTIVE"
        )
        db.session.add(event)
        db.session.commit()

        # Create VIP section
        vip_sec = EventSection(
            event_id=event.id,
            name="VIP Lounge",
            section_type="Section",
            price=5000.0,
            total_seats=10,
            display_order=1
        )
        db.session.add(vip_sec)
        db.session.commit()

        # Create Seats
        seat_vip1 = Seat(event_id=event.id, seat_number="VIP-1", section="VIP Lounge", category="VIP", price=5000.0, status="BOOKED", section_id=vip_sec.id, row_label="A", seat_index=1)
        seat_vip2 = Seat(event_id=event.id, seat_number="VIP-2", section="VIP Lounge", category="VIP", price=5000.0, status="BOOKED", section_id=vip_sec.id, row_label="A", seat_index=2)
        seat_std = Seat(event_id=event.id, seat_number="STD-1", section="Standard", category="Standard", price=1000.0, status="BOOKED", row_label="B", seat_index=1)
        db.session.add_all([seat_vip1, seat_vip2, seat_std])
        db.session.commit()

        # Fetch test user
        user = User.query.filter_by(email="john@example.com").first()

        # Create Booking 1: 2 VIP tickets (Multi-ticket booking)
        # Subtotal: 10000, Conv fee (5%): 500, Tax (18% of 500): 90, Total: 10590
        b1 = Booking(
            booking_reference="BK-TEST-MULTI-01",
            user_id=user.id,
            event_id=event.id,
            total_tickets=2,
            subtotal=10000.0,
            convenience_fee=500.0,
            tax=90.0,
            total_amount=10590.0,
            booking_status="CONFIRMED",
            created_at=datetime(2026, 10, 14, 10, 30, 0)
        )
        db.session.add(b1)
        db.session.commit()

        # Attendee 1 with formula injection test in name
        att1 = Attendee(booking_id=b1.id, seat_id=seat_vip1.id, full_name="=1+1 Danger Name", age=25, phone="9876543210", city="Mumbai")
        att2 = Attendee(booking_id=b1.id, seat_id=seat_vip2.id, full_name="Alice Smith", age=26, phone="9876543211", city="Mumbai")
        db.session.add_all([att1, att2])
        db.session.flush()

        # Payment for b1 (SUCCESS)
        p1 = Payment(booking_id=b1.id, transaction_id="TXN-MULTI-01", payment_method="UPI", amount=10590.0, payment_status="SUCCESS")
        t1 = Ticket(booking_id=b1.id, attendee_id=att1.id, seat_id=seat_vip1.id, ticket_number="TKT-VIP-01", qr_code_path="/qr/tkt1.png", ticket_status="ACTIVE")
        t2 = Ticket(booking_id=b1.id, attendee_id=att2.id, seat_id=seat_vip2.id, ticket_number="TKT-VIP-02", qr_code_path="/qr/tkt2.png", ticket_status="ACTIVE")
        db.session.add_all([p1, t1, t2])
        db.session.commit()

        # Create Booking 2: 1 Standard ticket on a different day
        b2 = Booking(
            booking_reference="BK-TEST-SINGLE-02",
            user_id=user.id,
            event_id=event.id,
            total_tickets=1,
            subtotal=1000.0,
            convenience_fee=50.0,
            tax=9.0,
            total_amount=1059.0,
            booking_status="CONFIRMED",
            created_at=datetime(2026, 10, 15, 14, 0, 0)
        )
        db.session.add(b2)
        db.session.commit()

        att3 = Attendee(booking_id=b2.id, seat_id=seat_std.id, full_name="Bob Runner", age=30, phone="9876543212", city="Pune")
        db.session.add(att3)
        db.session.flush()

        p2 = Payment(booking_id=b2.id, transaction_id="TXN-SINGLE-02", payment_method="CREDIT_CARD", amount=1059.0, payment_status="SUCCESS")
        t3 = Ticket(booking_id=b2.id, attendee_id=att3.id, seat_id=seat_std.id, ticket_number="TKT-STD-01", qr_code_path="/qr/tkt3.png", ticket_status="ACTIVE")
        db.session.add_all([p2, t3])
        db.session.commit()

        return {
            "event_id": event.id,
            "b1_id": b1.id,
            "b2_id": b2.id,
            "b1_ref": b1.booking_reference,
            "b2_ref": b2.booking_reference,
        }


def test_sanitize_csv_cell():
    """Verify formula injection characters are prepended with single quote."""
    assert sanitize_csv_cell("=SUM(A1:A10)") == "'=SUM(A1:A10)"
    assert sanitize_csv_cell("+cmd|' /C calc'!A0") == "'+cmd|' /C calc'!A0"
    assert sanitize_csv_cell("-123") == "'-123"
    assert sanitize_csv_cell("@alert(1)") == "'@alert(1)"
    assert sanitize_csv_cell("Normal Text") == "Normal Text"
    assert sanitize_csv_cell(None) == ""


def test_date_wise_booking_csv_generation(app, populated_booking_data):
    """Test Date-Wise Booking Report CSV generation with 29 columns and daily summary."""
    with app.app_context():
        # Query specifically for 2026-10-14 (Booking 1)
        stream, filename = generate_date_wise_booking_csv(booking_date="2026-10-14")
        assert filename == "daily_bookings_2026-10-14.csv"
        
        content = stream.getvalue().decode("utf-8-sig")
        reader = csv.reader(io.StringIO(content))
        rows = list(reader)

        # Row 0: Headers
        headers = rows[0]
        assert len(headers) == 29
        assert headers[0] == "Booking ID"
        assert headers[1] == "Booking Date"
        assert headers[11] == "Section or Stand Name"
        assert headers[14] == "Number of Tickets"
        assert headers[18] == "Convenience Fee"
        assert headers[22] == "Total Payable Amount"
        assert headers[28] == "Booking Status"

        # Check Booking 1 tickets (there should be 2 attendee rows)
        assert rows[1][0] == "BK-TEST-MULTI-01"
        assert rows[2][0] == "BK-TEST-MULTI-01"

        # Check multi-ticket fee distribution: 500 fee divided across 2 tickets = 250.00 each
        assert rows[1][18] == "250.00"
        assert rows[2][18] == "250.00"
        # Tax 90 divided across 2 tickets = 45.00 each
        assert rows[1][21] == "45.00"
        assert rows[2][21] == "45.00"

        # Check Formula Injection mitigation on attendee 1
        assert rows[1][7].startswith("'=")

        # Check Daily Final Summary rows at bottom
        summary_found = False
        for row in rows:
            if row and "DAILY FINAL SUMMARY" in row[0]:
                summary_found = True
            if row and row[0] == "Total Tickets Booked":
                assert row[1] == "2"
            if row and row[0] == "Total Bookings":
                assert row[1] == "1"

        assert summary_found is True


def test_date_wise_booking_csv_range_filter(app, populated_booking_data):
    """Test date range filter capturing both bookings across days."""
    with app.app_context():
        stream, filename = generate_date_wise_booking_csv(
            start_date="2026-10-14",
            end_date="2026-10-15"
        )
        assert filename == "daily_bookings_2026-10-14_to_2026-10-15.csv"

        content = stream.getvalue().decode("utf-8-sig")
        assert "BK-TEST-MULTI-01" in content
        assert "BK-TEST-SINGLE-02" in content
        assert "Total Tickets Booked,3" in content


def test_organizer_section_wise_csv(app, populated_booking_data):
    """Test organizer section-wise CSV export and privacy constraints."""
    with app.app_context():
        event_id = populated_booking_data["event_id"]
        stream, filename = generate_section_wise_organizer_csv(
            event_id=event_id,
            section_name="VIP Lounge"
        )
        assert filename == "VIP_Lounge_Users.csv"

        content = stream.getvalue().decode("utf-8-sig")
        reader = csv.reader(io.StringIO(content))
        rows = list(reader)

        headers = rows[0]
        assert len(headers) == 23
        assert "Booking ID" in headers
        assert "Section or Stand Name" in headers
        assert "Ticket Number" in headers
        assert "Total Payable Amount" in headers

        # Ensure no sensitive credentials leaked
        assert "password" not in content.lower()
        assert "password_hash" not in content.lower()
        assert "token" not in content.lower()

        # Check summary at bottom
        assert "Total Section Tickets Booked,2" in content
        assert "Total Section Base Amount,10000.00" in content


def test_organizer_all_sections_zip(app, populated_booking_data):
    """Test All Sections ZIP archive generation."""
    with app.app_context():
        event_id = populated_booking_data["event_id"]
        stream, zip_filename = generate_all_sections_zip(event_id=event_id)
        assert zip_filename.endswith(".zip")
        assert "Coldplay" in zip_filename or "DY" in zip_filename or "All_Sections" in zip_filename

        # Verify ZIP contains valid CSV files
        with zipfile.ZipFile(stream, "r") as zf:
            names = zf.namelist()
            assert len(names) >= 1
            for name in names:
                assert name.endswith(".csv")
                csv_bytes = zf.read(name)
                assert b"Booking ID" in csv_bytes


def test_event_date_management_routes(admin_client, app):
    """Test Event Date Management web views and November 2026 API updates."""
    with app.app_context():
        # Test GET page
        res = admin_client.get("/admin/events/date-management")
        assert res.status_code == 200
        assert b"Event Date Management" in res.data
        assert b"November 2026" in res.data

        # Test single date update to valid November 2026 date
        update_res = admin_client.post("/admin/events/date-management/update-single", json={
            "event_id": 1,
            "new_date": "2026-11-22",
            "new_time": "18:00"
        })
        assert update_res.status_code == 200
        data = update_res.get_json()
        assert data["success"] is True
        assert data["new_date"] == "2026-11-22"

        # Verify database record updated in-place
        event = db.session.get(Event, 1)
        assert event.event_date == date(2026, 11, 22)
        assert event.event_time == datetime.strptime("18:00", "%H:%M").time()

        # Test single date update rejected if NOT in November 2026
        bad_res = admin_client.post("/admin/events/date-management/update-single", json={
            "event_id": 1,
            "new_date": "2026-12-05",
            "new_time": "18:00"
        })
        assert bad_res.status_code == 400
        bad_data = bad_res.get_json()
        assert bad_data["success"] is False
        assert "Date must be in November 2026" in bad_data["message"]

        # Test Bulk sync to November 2026
        sync_res = admin_client.post("/admin/events/date-management/sync-all-november", json={})
        assert sync_res.status_code == 200
        sync_data = sync_res.get_json()
        assert sync_data["success"] is True
        assert sync_data["updated_count"] >= 1
