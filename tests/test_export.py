import io
import pandas as pd
from services.export_service import export_to_csv_stream, export_to_excel_stream


def test_export_csv_empty(app):
    """Test CSV export stream generation when no bookings exist."""
    with app.app_context():
        stream = export_to_csv_stream()
        assert isinstance(stream, io.BytesIO)
        content = stream.getvalue().decode("utf-8-sig")
        assert "Booking ID" in content
        assert "Attendee Name" in content
        assert "Seat Number" in content


def test_export_excel_empty(app):
    """Test Excel export stream generation with openpyxl."""
    with app.app_context():
        stream = export_to_excel_stream()
        assert isinstance(stream, io.BytesIO)
        # Read back using pandas to verify valid Excel binary
        df = pd.read_excel(stream)
        assert "Booking ID" in df.columns
        assert "Ticket ID" in df.columns
        assert "Payment Amount" in df.columns
