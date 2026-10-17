from models import db, utcnow


class Booking(db.Model):
    __tablename__ = "bookings"

    id = db.Column(db.Integer, primary_key=True)
    booking_reference = db.Column(db.String(50), unique=True, nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    event_id = db.Column(db.Integer, db.ForeignKey("events.id", ondelete="RESTRICT"), nullable=False, index=True)
    total_tickets = db.Column(db.Integer, nullable=False)
    subtotal = db.Column(db.Numeric(10, 2), nullable=False)
    convenience_fee = db.Column(db.Numeric(10, 2), nullable=False, default=0.0)
    tax = db.Column(db.Numeric(10, 2), nullable=False, default=0.0)
    total_amount = db.Column(db.Numeric(10, 2), nullable=False)
    booking_status = db.Column(db.String(50), nullable=False, default="CONFIRMED")  # CONFIRMED, CANCELLED, PENDING
    created_at = db.Column(db.DateTime, default=utcnow)

    # Relationships
    attendees = db.relationship("Attendee", backref="booking", lazy=True, cascade="all, delete-orphan")
    payment = db.relationship("Payment", backref="booking", uselist=False, lazy=True, cascade="all, delete-orphan")
    tickets = db.relationship("Ticket", backref="booking", lazy=True, cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "booking_reference": self.booking_reference,
            "user_id": self.user_id,
            "user_name": self.user.full_name if self.user else None,
            "user_email": self.user.email if self.user else None,
            "event_id": self.event_id,
            "event_name": self.event.name if self.event else None,
            "event_date": self.event.event_date.strftime("%Y-%m-%d") if self.event and self.event.event_date else None,
            "event_time": self.event.event_time.strftime("%H:%M") if self.event and self.event.event_time else None,
            "venue": self.event.venue if self.event else None,
            "city": self.event.city if self.event else None,
            "total_tickets": self.total_tickets,
            "subtotal": float(self.subtotal),
            "convenience_fee": float(self.convenience_fee),
            "tax": float(self.tax),
            "total_amount": float(self.total_amount),
            "booking_status": self.booking_status,
            "payment_status": self.payment.payment_status if self.payment else "PENDING",
            "payment_method": self.payment.payment_method if self.payment else "N/A",
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else None,
        }

    def __repr__(self):
        return f"<Booking {self.booking_reference} - {self.booking_status}>"
