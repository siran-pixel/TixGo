from services.payment_service import process_simulated_payment
from services.booking_service import calculate_pricing
from models import Seat


def test_payment_service_methods():
    """Test simulated gateway across payment methods."""
    # Test valid UPI
    ok, msg, data = process_simulated_payment(500.0, "UPI", {"upi_id": "test@okaxis"})
    assert ok is True
    assert data["status"] == "SUCCESS"
    assert data["transaction_id"].startswith("TXN-")

    # Test valid Credit Card
    ok, msg, data = process_simulated_payment(1200.0, "CREDIT_CARD", {"card_number": "4532890123456789"})
    assert ok is True

    # Test invalid payment method
    ok, msg, data = process_simulated_payment(500.0, "BITCOIN", {})
    assert ok is False


def test_pricing_calculation(app):
    """Test server-side price calculation integrity."""
    with app.app_context():
        # Cinema Balcony seat (₹250) + Standard seat (₹200)
        s1 = Seat(event_id=1, seat_number="A1", price=250.0, status="AVAILABLE")
        s2 = Seat(event_id=1, seat_number="E1", price=200.0, status="AVAILABLE")

        pricing = calculate_pricing([s1, s2])
        assert pricing["subtotal"] == 450.0
        assert pricing["convenience_fee"] == 22.50  # 5% of 450
        assert pricing["tax"] == 4.05               # 18% of 22.50
        assert pricing["total_amount"] == 476.55
