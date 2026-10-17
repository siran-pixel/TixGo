import pytest
from datetime import date, datetime, timedelta
from app import create_app
from models import db, User, Admin, Event, Seat
from services.seat_generator_service import generate_seats_for_event


@pytest.fixture
def app():
    """Create and configure a testing application instance."""
    app = create_app("testing")

    with app.app_context():
        db.create_all()

        # Create test admin
        admin = Admin(email="admin1234@gmail.com", is_active=True)
        admin.set_password("admin@1234")
        db.session.add(admin)

        # Create verified test user
        user = User(
            full_name="John Doe",
            email="john@example.com",
            phone="9876543210",
            is_verified=True
        )
        user.set_password("Password123")
        db.session.add(user)

        # Create unverified test user
        unverified = User(
            full_name="Jane Unverified",
            email="jane@example.com",
            phone="9876543211",
            is_verified=False
        )
        unverified.set_password("Password123")
        db.session.add(unverified)

        # Create test Cricket Event
        event_cricket = Event(
            id=1,
            name="IPL Grand Final: CSK vs MI",
            description="Championship cricket match at Chepauk Stadium.",
            event_type="Cricket",
            banner_image="/static/images/event_cricket.jpg",
            venue="MA Chidambaram Stadium (Chepauk)",
            city="Chennai",
            event_date=date.today() + timedelta(days=2),
            event_time=datetime.strptime("19:30", "%H:%M").time(),
            total_seats=2500,
            status="ACTIVE"
        )
        db.session.add(event_cricket)
        db.session.commit()

        # Generate seats for the cricket event
        generate_seats_for_event(event_cricket)

        yield app

        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()


@pytest.fixture
def auth_client(client, app):
    """A client with an active authenticated user session."""
    with client.session_transaction() as sess:
        sess["user_id"] = 1
        sess["user_email"] = "john@example.com"
        sess["user_name"] = "John Doe"
        sess["session_token"] = "test-session-token-12345"
    return client


@pytest.fixture
def admin_client(client, app):
    """A client with an active admin session."""
    with client.session_transaction() as sess:
        sess["admin_id"] = 1
        sess["admin_email"] = "admin1234@gmail.com"
    return client
