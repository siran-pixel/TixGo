from models import db, utcnow


class Ticket(db.Model):
    __tablename__ = "tickets"

    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey("bookings.id", ondelete="CASCADE"), nullable=False, index=True)
    attendee_id = db.Column(db.Integer, db.ForeignKey("attendees.id", ondelete="CASCADE"), nullable=False)
    seat_id = db.Column(db.Integer, db.ForeignKey("seats.id", ondelete="RESTRICT"), nullable=False)
    ticket_number = db.Column(db.String(50), unique=True, nullable=False, index=True)
    qr_code_path = db.Column(db.String(255), nullable=False)
    ticket_status = db.Column(db.String(50), nullable=False, default="ACTIVE")  # ACTIVE, USED, CANCELLED
    created_at = db.Column(db.DateTime, default=utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "ticket_number": self.ticket_number,
            "booking_id": self.booking_id,
            "booking_reference": self.booking.booking_reference if self.booking else None,
            "event_name": self.booking.event.name if self.booking and self.booking.event else None,
            "venue": self.booking.event.venue if self.booking and self.booking.event else None,
            "city": self.booking.event.city if self.booking and self.booking.event else None,
            "event_date": self.booking.event.event_date.strftime("%Y-%m-%d") if self.booking and self.booking.event else None,
            "event_time": self.booking.event.event_time.strftime("%H:%M") if self.booking and self.booking.event else None,
            "seat_number": self.seat.seat_number if self.seat else None,
            "section": self.seat.section if self.seat else None,
            "category": self.seat.category if self.seat else None,
            "price": float(self.seat.price) if self.seat else 0.0,
            "attendee_name": self.attendee.full_name if self.attendee else None,
            "attendee_age": self.attendee.age if self.attendee else None,
            "attendee_phone": self.attendee.phone if self.attendee else None,
            "attendee_city": self.attendee.city if self.attendee else None,
            "qr_code_path": self.qr_code_path,
            "ticket_status": self.ticket_status,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else None,
        }

    def __repr__(self):
        return f"<Ticket {self.ticket_number} ({self.ticket_status})>"
