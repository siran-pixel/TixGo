import secrets
from typing import Dict, Any, Tuple
from models import utcnow


def process_simulated_payment(
    amount: float,
    payment_method: str,
    payment_data: Dict[str, Any]
) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Simulates a secure payment gateway transaction.
    Validates payment details based on method and generates a unique transaction ID.
    """
    if amount <= 0:
        return False, "Invalid payment amount.", {}

    payment_method = payment_method.upper().strip()
    if payment_method not in ("UPI", "CREDIT_CARD", "DEBIT_CARD", "NET_BANKING"):
        return False, "Unsupported payment method.", {}

    # Basic format checks
    if payment_method == "UPI":
        upi_id = payment_data.get("upi_id", "").strip()
        if upi_id and "@" not in upi_id:
            return False, "Invalid UPI ID format (e.g. user@okaxis).", {}

    elif payment_method in ("CREDIT_CARD", "DEBIT_CARD"):
        card_number = payment_data.get("card_number", "").replace(" ", "").strip()
        if card_number and len(card_number) < 12:
            return False, "Invalid card number.", {}

    # Generate realistic gateway transaction ID
    timestamp = utcnow().strftime("%Y%m%d%H%M%S")
    txn_id = f"TXN-{timestamp}-{secrets.token_hex(4).upper()}"

    return True, "Payment processed successfully.", {
        "transaction_id": txn_id,
        "amount": amount,
        "payment_method": payment_method,
        "status": "SUCCESS",
        "paid_at": utcnow().isoformat(),
    }
