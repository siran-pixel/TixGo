from models import db, utcnow


class Event(db.Model):
    __tablename__ = "events"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    event_type = db.Column(db.String(50), nullable=False, default="Cinema")  # Cinema, Theater, Cricket, Concert, General
    banner_image = db.Column(db.String(255), nullable=True)
    venue = db.Column(db.String(200), nullable=False)
    city = db.Column(db.String(100), nullable=False)
    event_date = db.Column(db.Date, nullable=False)
    event_time = db.Column(db.Time, nullable=False)
    total_seats = db.Column(db.Integer, default=0, nullable=False)
    status = db.Column(db.String(50), default="ACTIVE", nullable=False)  # ACTIVE, CANCELLED, COMPLETED, DRAFT
    created_at = db.Column(db.DateTime, default=utcnow)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow)

    # Relationships
    seats = db.relationship("Seat", backref="event", lazy="dynamic", cascade="all, delete-orphan")
    bookings = db.relationship("Booking", backref="event", lazy=True)
    sections = db.relationship("EventSection", backref="event", cascade="all, delete-orphan", order_by="EventSection.display_order")

    @property
    def available_seats_count(self) -> int:
        from models.seat import Seat
        return self.seats.filter_by(status="AVAILABLE").count()

    @property
    def min_price(self) -> float:
        from models.seat import Seat
        first_seat = self.seats.order_by(Seat.price.asc()).first()
        return float(first_seat.price) if first_seat else 0.0

    @property
    def max_price(self) -> float:
        from models.seat import Seat
        last_seat = self.seats.order_by(Seat.price.desc()).first()
        return float(last_seat.price) if last_seat else 0.0

    @property
    def has_custom_sections(self) -> bool:
        return len(self.sections) > 0

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "event_type": self.event_type,
            "banner_image": self.banner_image,
            "venue": self.venue,
            "city": self.city,
            "event_date": self.event_date.strftime("%Y-%m-%d") if self.event_date else None,
            "event_time": self.event_time.strftime("%H:%M") if self.event_time else None,
            "total_seats": self.total_seats,
            "available_seats": self.available_seats_count,
            "min_price": self.min_price,
            "max_price": self.max_price,
            "has_custom_sections": self.has_custom_sections,
            "sections": [s.to_dict() for s in self.sections],
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f"<Event {self.name} ({self.event_type})>"
