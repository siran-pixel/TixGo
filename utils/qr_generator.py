import os
import qrcode
from pathlib import Path
from config import Config


def generate_ticket_qr(ticket_number: str) -> str:
    """
    Generates a high-quality QR code for a given ticket identifier.
    Saves the image file to static/qr/<ticket_number>.png
    Returns the relative web-accessible URL: /static/qr/<ticket_number>.png
    """
    qr_dir = Path(Config.QR_FOLDER)
    qr_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{ticket_number}.png"
    filepath = qr_dir / filename

    # Payload contains verified ticket token and verification URL
    qr_payload = f"SHOWSPOT-VERIFIED:{ticket_number}"

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=8,
        border=3,
    )
    qr.add_data(qr_payload)
    qr.make(fit=True)

    img = qr.make_image(fill_color="#1F1F1F", back_color="#FFFFFF")
    img.save(str(filepath))

    return f"/static/qr/{filename}"
