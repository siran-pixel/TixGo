from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

def utcnow() -> datetime:
    """Returns naive UTC datetime object for cross-database compatibility."""
    return datetime.now(timezone.utc).replace(tzinfo=None)

# Import models so they register with SQLAlchemy
from models.user import User
from models.admin import Admin
from models.otp_verification import OTPVerification
from models.event import Event
from models.event_section import EventSection
from models.seat import Seat
from models.seat_lock import SeatLock
from models.booking import Booking
from models.attendee import Attendee
from models.payment import Payment
from models.ticket import Ticket

__all__ = [
    "db",
    "utcnow",
    "User",
    "Admin",
    "OTPVerification",
    "Event",
    "EventSection",
    "Seat",
    "SeatLock",
    "Booking",
    "Attendee",
    "Payment",
    "Ticket",
]
