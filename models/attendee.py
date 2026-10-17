from models import db


class Attendee(db.Model):
    __tablename__ = "attendees"

    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey("bookings.id", ondelete="CASCADE"), nullable=False, index=True)
    seat_id = db.Column(db.Integer, db.ForeignKey("seats.id", ondelete="RESTRICT"), nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    city = db.Column(db.String(100), nullable=False)

    # Relationships
    ticket = db.relationship("Ticket", backref="attendee", uselist=False, lazy=True, cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "booking_id": self.booking_id,
            "seat_id": self.seat_id,
            "seat_number": self.seat.seat_number if self.seat else None,
            "section": self.seat.section if self.seat else None,
            "category": self.seat.category if self.seat else None,
            "price": float(self.seat.price) if self.seat else 0.0,
            "full_name": self.full_name,
            "age": self.age,
            "phone": self.phone,
            "city": self.city,
            "ticket_number": self.ticket.ticket_number if self.ticket else None,
        }

    def __repr__(self):
        return f"<Attendee {self.full_name} - Seat {self.seat_id}>"
