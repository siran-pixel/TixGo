from models import db, utcnow


class Payment(db.Model):
    __tablename__ = "payments"

    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey("bookings.id", ondelete="CASCADE"), nullable=False, index=True)
    transaction_id = db.Column(db.String(100), unique=True, nullable=False, index=True)
    payment_method = db.Column(db.String(50), nullable=False)  # UPI, CREDIT_CARD, DEBIT_CARD, NET_BANKING
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    payment_status = db.Column(db.String(50), nullable=False, default="SUCCESS")  # SUCCESS, FAILED, PENDING, REFUNDED
    paid_at = db.Column(db.DateTime, default=utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "booking_id": self.booking_id,
            "transaction_id": self.transaction_id,
            "payment_method": self.payment_method,
            "amount": float(self.amount),
            "payment_status": self.payment_status,
            "paid_at": self.paid_at.strftime("%Y-%m-%d %H:%M:%S") if self.paid_at else None,
        }

    def __repr__(self):
        return f"<Payment {self.transaction_id} ({self.payment_status})>"
