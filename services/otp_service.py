import secrets
from datetime import timedelta
from typing import Tuple, Optional, Dict
from models import db, utcnow, OTPVerification, User
from config import Config

# In-memory store of recent OTPs for demo inspection / instant autofill
_latest_otps: Dict[str, str] = {}


def generate_otp_code() -> str:
    """Generates a cryptographically secure 6-digit numeric OTP."""
    return f"{secrets.randbelow(900000) + 100000}"


def get_latest_otp_code(email: str, purpose: str = "SIGNUP") -> Optional[str]:
    """Retrieves the latest generated raw OTP for an email and purpose (useful for local development)."""
    return _latest_otps.get(f"{email.strip().lower()}:{purpose.strip().upper()}")


def create_otp_record(email: str, purpose: str = "SIGNUP", user_id: Optional[int] = None) -> Tuple[str, OTPVerification]:
    """
    Creates or updates an OTP verification record for the given email and purpose.
    Returns (raw_otp_code, otp_record).
    """
    email = email.strip().lower()
    purpose = purpose.strip().upper()
    raw_otp = generate_otp_code()
    expires_at = utcnow() + timedelta(seconds=Config.OTP_EXPIRY_SECONDS)

    # Invalidate any existing active OTPs for the same email and purpose
    existing_otps = OTPVerification.query.filter_by(email=email, purpose=purpose).all()
    for otp in existing_otps:
        db.session.delete(otp)

    otp_record = OTPVerification(
        user_id=user_id,
        email=email,
        purpose=purpose,
        expires_at=expires_at,
        attempts=0,
    )
    otp_record.set_otp(raw_otp)

    db.session.add(otp_record)
    db.session.commit()

    # Cache for demo/dev retrieval
    _latest_otps[f"{email}:{purpose}"] = raw_otp

    return raw_otp, otp_record


def verify_otp_code(email: str, otp_code: str, purpose: str = "SIGNUP") -> Tuple[bool, str]:
    """
    Verifies the provided OTP code against the latest active record.
    Returns (is_valid, message).
    """
    email = email.strip().lower()
    purpose = purpose.strip().upper()
    clean_otp = str(otp_code).strip()

    if not clean_otp or len(clean_otp) != 6 or not clean_otp.isdigit():
        return False, "Please enter a valid 6-digit numeric OTP."

    otp_record = OTPVerification.query.filter_by(email=email, purpose=purpose)\
        .order_by(OTPVerification.created_at.desc()).first()

    if not otp_record:
        return False, "No active OTP request found for this email. Please request a new OTP."

    if otp_record.is_expired:
        return False, "OTP has expired. Please request a new code."

    if otp_record.attempts >= Config.OTP_MAX_ATTEMPTS:
        return False, "Maximum verification attempts exceeded. Please request a new OTP."

    otp_record.attempts += 1
    db.session.commit()

    if not otp_record.check_otp(clean_otp):
        remaining = Config.OTP_MAX_ATTEMPTS - otp_record.attempts
        return False, f"Invalid OTP code. {remaining} attempt(s) remaining."

    # Valid OTP: delete record and clear cache after successful verification
    db.session.delete(otp_record)
    db.session.commit()
    _latest_otps.pop(f"{email}:{purpose}", None)

    return True, "OTP verified successfully."
