from models import db, utcnow


class SeatLock(db.Model):
    __tablename__ = "seat_locks"

    id = db.Column(db.Integer, primary_key=True)
    seat_id = db.Column(db.Integer, db.ForeignKey("seats.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    session_token = db.Column(db.String(100), nullable=False, index=True)
    locked_at = db.Column(db.DateTime, default=utcnow)
    expires_at = db.Column(db.DateTime, nullable=False, index=True)

    @property
    def is_expired(self) -> bool:
        return utcnow() > self.expires_at

    def to_dict(self):
        return {
            "id": self.id,
            "seat_id": self.seat_id,
            "session_token": self.session_token,
            "locked_at": self.locked_at.isoformat() if self.locked_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "seconds_remaining": max(0, int((self.expires_at - utcnow()).total_seconds())),
        }

    def __repr__(self):
        return f"<SeatLock Seat:{self.seat_id} Token:{self.session_token[:8]} Expires:{self.expires_at}>"
