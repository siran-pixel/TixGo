from werkzeug.security import generate_password_hash, check_password_hash
from models import db, utcnow


class OTPVerification(db.Model):
    __tablename__ = "otp_verifications"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    email = db.Column(db.String(150), nullable=False, index=True)
    otp_hash = db.Column(db.String(255), nullable=False)
    purpose = db.Column(db.String(50), nullable=False, default="SIGNUP")  # 'SIGNUP', 'PASSWORD_RESET'
    expires_at = db.Column(db.DateTime, nullable=False)
    attempts = db.Column(db.Integer, default=0, nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow)

    def set_otp(self, otp_code: str):
        self.otp_hash = generate_password_hash(str(otp_code))

    def check_otp(self, otp_code: str) -> bool:
        return check_password_hash(self.otp_hash, str(otp_code))

    @property
    def is_expired(self) -> bool:
        return utcnow() > self.expires_at

    def __repr__(self):
        return f"<OTPVerification {self.email} ({self.purpose})>"
