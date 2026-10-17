import logging
from typing import Optional, Dict, Any, List
from flask import render_template_string
from flask_mail import Mail, Message
from config import Config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("EmailService")

mail = Mail()

# In-memory store for recent mock emails (useful for demo/testing without live SMTP)
_mock_email_inbox: List[Dict[str, Any]] = []


def get_latest_mock_email(email: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Retrieves the latest dispatched email, optionally filtered by recipient."""
    if not _mock_email_inbox:
        return None
    if email:
        filtered = [m for m in reversed(_mock_email_inbox) if m.get("recipient") == email.lower()]
        return filtered[0] if filtered else None
    return _mock_email_inbox[-1]


def send_email(subject: str, recipient: str, html_body: str, text_body: Optional[str] = None) -> bool:
    """Dispatches email via Flask-Mail with robust fallback to console logging."""
    recipient = recipient.strip().lower()

    # Record mock email for testing/demo inspection
    _mock_email_inbox.append({
        "subject": subject,
        "recipient": recipient,
        "html": html_body,
        "text": text_body or subject,
    })

    # Keep inbox bounded
    if len(_mock_email_inbox) > 50:
        _mock_email_inbox.pop(0)

    # Check if SMTP credentials are configured
    if not Config.MAIL_USERNAME or not Config.MAIL_PASSWORD:
        logger.info(f"\n{'='*60}\n[LOCAL MOCK EMAIL DISPATCHED]\nTo: {recipient}\nSubject: {subject}\n{text_body or html_body}\n{'='*60}\n")
        return True

    try:
        msg = Message(
            subject=subject,
            recipients=[recipient],
            html=html_body,
            body=text_body or subject,
            sender=Config.MAIL_DEFAULT_SENDER,
        )
        mail.send(msg)
        logger.info(f"Email successfully sent via SMTP to {recipient}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email via SMTP to {recipient}: {e}. Dispatched to local console fallback.")
        return False


def send_signup_otp(email: str, full_name: str, otp_code: str) -> bool:
    """Sends OTP verification email for new user registration."""
    subject = "Verify Your ShowSpot Account - OTP Code"
    html_body = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e0e0e0; border-radius: 8px;">
        <div style="text-align: center; margin-bottom: 20px;">
            <h1 style="color: #E50914; margin: 0;">ShowSpot</h1>
            <p style="color: #666; margin-top: 5px;">Your Entertainment Destination</p>
        </div>
        <h2 style="color: #1F1F1F;">Welcome to ShowSpot, {full_name}!</h2>
        <p style="color: #444; font-size: 15px; line-height: 1.5;">
            Thank you for creating an account. Please use the 6-digit verification code below to verify your email address.
        </p>
        <div style="text-align: center; margin: 30px 0;">
            <span style="display: inline-block; font-size: 32px; font-weight: bold; letter-spacing: 6px; color: #E50914; background: #f8f9fa; padding: 15px 30px; border-radius: 8px; border: 1px dashed #E50914;">
                {otp_code}
            </span>
        </div>
        <p style="color: #777; font-size: 13px;">
            This OTP will expire in <strong>5 minutes</strong>. If you did not request this registration, please ignore this email.
        </p>
        <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
        <p style="color: #999; font-size: 12px; text-align: center;">
            &copy; 2026 ShowSpot Ticket Booking System. All rights reserved.
        </p>
    </div>
    """
    text_body = f"Welcome to ShowSpot! Your OTP verification code is: {otp_code}. It expires in 5 minutes."
    return send_email(subject, email, html_body, text_body)


def send_password_reset_otp(email: str, otp_code: str) -> bool:
    """Sends OTP code for password recovery."""
    subject = "Reset Your ShowSpot Password - OTP Code"
    html_body = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e0e0e0; border-radius: 8px;">
        <div style="text-align: center; margin-bottom: 20px;">
            <h1 style="color: #E50914; margin: 0;">ShowSpot</h1>
            <p style="color: #666; margin-top: 5px;">Password Recovery</p>
        </div>
        <h2 style="color: #1F1F1F;">Password Reset Request</h2>
        <p style="color: #444; font-size: 15px; line-height: 1.5;">
            We received a request to reset your password. Use the OTP code below to proceed with setting a new password.
        </p>
        <div style="text-align: center; margin: 30px 0;">
            <span style="display: inline-block; font-size: 32px; font-weight: bold; letter-spacing: 6px; color: #E50914; background: #f8f9fa; padding: 15px 30px; border-radius: 8px; border: 1px dashed #E50914;">
                {otp_code}
            </span>
        </div>
        <p style="color: #777; font-size: 13px;">
            This OTP code is valid for <strong>5 minutes</strong>. If you did not make this request, your account is still secure.
        </p>
        <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
        <p style="color: #999; font-size: 12px; text-align: center;">
            &copy; 2026 ShowSpot Ticket Booking System. All rights reserved.
        </p>
    </div>
    """
    text_body = f"ShowSpot Password Reset OTP: {otp_code}. Valid for 5 minutes."
    return send_email(subject, email, html_body, text_body)


def send_booking_confirmation(booking) -> bool:
    """Sends a booking confirmation email with ticket summary."""
    user = booking.user
    event = booking.event
    subject = f"Booking Confirmed! - {event.name} ({booking.booking_reference})"

    seats_list = ", ".join([att.seat.seat_number for att in booking.attendees if att.seat])

    html_body = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e0e0e0; border-radius: 8px;">
        <div style="text-align: center; margin-bottom: 20px;">
            <h1 style="color: #E50914; margin: 0;">ShowSpot</h1>
            <p style="color: #28a745; font-weight: bold; font-size: 16px;">Booking Confirmed! &check;</p>
        </div>
        <p style="font-size: 15px; color: #333;">Hi {user.full_name},</p>
        <p style="color: #555;">Your tickets for <strong>{event.name}</strong> have been successfully confirmed!</p>
        
        <table style="width: 100%; border-collapse: collapse; margin: 20px 0; font-size: 14px;">
            <tr style="background: #f8f9fa; border-bottom: 1px solid #eee;">
                <td style="padding: 10px; font-weight: bold; color: #555;">Booking Reference</td>
                <td style="padding: 10px; color: #1F1F1F;">{booking.booking_reference}</td>
            </tr>
            <tr style="border-bottom: 1px solid #eee;">
                <td style="padding: 10px; font-weight: bold; color: #555;">Event</td>
                <td style="padding: 10px; color: #1F1F1F;">{event.name}</td>
            </tr>
            <tr style="background: #f8f9fa; border-bottom: 1px solid #eee;">
                <td style="padding: 10px; font-weight: bold; color: #555;">Venue & City</td>
                <td style="padding: 10px; color: #1F1F1F;">{event.venue}, {event.city}</td>
            </tr>
            <tr style="border-bottom: 1px solid #eee;">
                <td style="padding: 10px; font-weight: bold; color: #555;">Date & Time</td>
                <td style="padding: 10px; color: #1F1F1F;">{event.event_date.strftime('%d %b %Y')} at {event.event_time.strftime('%I:%M %p')}</td>
            </tr>
            <tr style="background: #f8f9fa; border-bottom: 1px solid #eee;">
                <td style="padding: 10px; font-weight: bold; color: #555;">Seats Booked</td>
                <td style="padding: 10px; font-weight: bold; color: #E50914;">{seats_list} ({booking.total_tickets} Tickets)</td>
            </tr>
            <tr style="border-bottom: 1px solid #eee;">
                <td style="padding: 10px; font-weight: bold; color: #555;">Total Amount Paid</td>
                <td style="padding: 10px; font-weight: bold; color: #28a745;">₹{booking.total_amount:,.2f}</td>
            </tr>
        </table>
        
        <p style="color: #666; font-size: 13px;">
            You can view, print, or download your digital QR tickets anytime under <strong>My Bookings</strong> on ShowSpot.
        </p>
        <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
        <p style="color: #999; font-size: 12px; text-align: center;">
            &copy; 2026 ShowSpot Ticket Booking System. All rights reserved.
        </p>
    </div>
    """
    text_body = f"Your booking {booking.booking_reference} for {event.name} ({seats_list}) is confirmed! Total: ₹{booking.total_amount}."
    return send_email(subject, user.email, html_body, text_body)
