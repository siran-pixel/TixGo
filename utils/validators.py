import re
from typing import Tuple, Optional, Dict, Any


def validate_email(email: str) -> bool:
    """Validates email format using regex standard."""
    if not email or not isinstance(email, str):
        return False
    pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    return bool(re.match(pattern, email.strip()))


def validate_password(password: str) -> Tuple[bool, Optional[str]]:
    """Validates that password meets minimum security requirements."""
    if not password or len(password) < 6:
        return False, "Password must be at least 6 characters long."
    if not re.search(r"[A-Za-z]", password):
        return False, "Password must contain at least one letter."
    if not re.search(r"[0-9]", password):
        return False, "Password must contain at least one number."
    return True, None


def validate_phone(phone: str) -> bool:
    """Validates phone number format: must be exactly 10 digits."""
    if not phone or not isinstance(phone, str):
        return False
    cleaned = re.sub(r"[\s\-\(\)\+]", "", phone)
    return len(cleaned) == 10 and cleaned.isdigit()


def validate_attendee_data(attendee: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """Validates an attendee entry."""
    name = attendee.get("full_name", "").strip()
    if not name or len(name) < 2:
        return False, "Attendee name must be at least 2 characters."

    try:
        age = int(attendee.get("age", 0))
        if age < 1 or age > 120:
            return False, "Attendee age must be between 1 and 120."
    except (ValueError, TypeError):
        return False, "Attendee age must be a valid number."

    phone = str(attendee.get("phone", "")).strip()
    if not validate_phone(phone):
        return False, "Attendee must provide a valid 10-digit phone number."

    city = attendee.get("city", "").strip()
    if not city or len(city) < 2:
        return False, "Attendee city is required."

    return True, None


def validate_event_rules(event_type: str, total_seats: int, price: Optional[float] = None) -> Tuple[bool, Optional[str]]:
    """Enforces domain business rules for specific event types."""
    event_type = event_type.capitalize()
    
    if event_type == "Cricket":
        if total_seats > 50000:
            return False, "Cricket stadium capacity cannot exceed 50,000 seats."
    elif event_type == "Concert":
        if total_seats != 1050:
            pass
    elif event_type == "General":
        if price is not None and price > 1000.0:
            return False, "General show ticket price cannot exceed ₹1000."

    return True, None
