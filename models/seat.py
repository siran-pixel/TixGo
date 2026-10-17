from datetime import datetime
from models import db


class Seat(db.Model):
    __tablename__ = "seats"

    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True)
    seat_number = db.Column(db.String(30), nullable=False)
    section = db.Column(db.String(50), nullable=False, default="Standard")
    category = db.Column(db.String(50), nullable=False, default="Standard")
    price = db.Column(db.Numeric(10, 2), nullable=False)
    status = db.Column(db.String(30), nullable=False, default="AVAILABLE", index=True)  # AVAILABLE, LOCKED, BOOKED, ADMIN_LOCKED
    admin_reserve_reason = db.Column(db.String(100), nullable=True)  # e.g. Resource Person, VIP, Chief Guest
    section_id = db.Column(db.Integer, db.ForeignKey("event_sections.id", ondelete="SET NULL"), nullable=True, index=True)
    row_label = db.Column(db.String(20), nullable=True)
    seat_index = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint("event_id", "seat_number", name="uk_event_seat"),
    )

    # Relationships
    locks = db.relationship("SeatLock", backref="seat", lazy=True, cascade="all, delete-orphan")
    attendees = db.relationship("Attendee", backref="seat", lazy=True)
    tickets = db.relationship("Ticket", backref="seat", lazy=True)
    section_obj = db.relationship("EventSection", backref="seats", lazy=True)

    def to_dict(self):
        return {
            "id": self.id,
            "event_id": self.event_id,
            "seat_number": self.seat_number,
            "section": self.section,
            "category": self.category,
            "price": float(self.price),
            "status": self.status,
            "admin_reserve_reason": self.admin_reserve_reason,
            "section_id": self.section_id,
            "row_label": self.row_label,
            "seat_index": self.seat_index,
        }

    def __repr__(self):
        return f"<Seat {self.seat_number} - Event {self.event_id} ({self.status})>"
