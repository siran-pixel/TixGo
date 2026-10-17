import os
from pathlib import Path
from dotenv import load_dotenv

# Base directory of the project
BASE_DIR = Path(__file__).resolve().parent

# Load environment variables
load_dotenv(BASE_DIR / ".env")


class Config:
    """Base Application Configuration"""
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-showspot-2026-supersecure")
    
    # Database
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'event_ticket_booking.db'}")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_recycle": 280,
        "pool_pre_ping": True,
    }

    # Admin Credentials
    ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin1234@gmail.com")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin@1234")

    # Mail Configuration
    MAIL_SERVER = os.getenv("MAIL_SERVER", "smtp.gmail.com")
    MAIL_PORT = int(os.getenv("MAIL_PORT", 587))
    MAIL_USE_TLS = os.getenv("MAIL_USE_TLS", "True").lower() in ("true", "1", "t")
    MAIL_USE_SSL = os.getenv("MAIL_USE_SSL", "False").lower() in ("true", "1", "t")
    MAIL_USERNAME = os.getenv("MAIL_USERNAME", "")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD", "")
    MAIL_DEFAULT_SENDER = os.getenv("MAIL_DEFAULT_SENDER", "ShowSpot Tickets <noreply@showspot.com>")

    # Application Paths
    STATIC_FOLDER = BASE_DIR / "static"
    QR_FOLDER = STATIC_FOLDER / "qr"
    EXPORT_FOLDER = BASE_DIR / "exports"
    IMAGE_FOLDER = STATIC_FOLDER / "images"

    # Business Rules
    MAX_SEATS_PER_BOOKING = int(os.getenv("MAX_SEATS_PER_BOOKING", 10))
    SEAT_LOCK_DURATION_SECONDS = int(os.getenv("SEAT_LOCK_DURATION_SECONDS", 300))  # 5 minutes
    OTP_EXPIRY_SECONDS = int(os.getenv("OTP_EXPIRY_SECONDS", 300))                  # 5 minutes
    OTP_MAX_ATTEMPTS = 5
    CONVENIENCE_FEE_PERCENTAGE = float(os.getenv("CONVENIENCE_FEE_PERCENTAGE", 5.0))
    TAX_PERCENTAGE = float(os.getenv("TAX_PERCENTAGE", 18.0))

    # Session & Security
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    PERMANENT_SESSION_LIFETIME = 86400  # 24 hours


class DevelopmentConfig(Config):
    DEBUG = True


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False
    SEAT_LOCK_DURATION_SECONDS = 300
    OTP_EXPIRY_SECONDS = 300


class ProductionConfig(Config):
    DEBUG = False
    SESSION_COOKIE_SECURE = True


config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
