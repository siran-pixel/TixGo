from flask import Blueprint, render_template, abort, jsonify, request
from services.ticket_service import get_consolidated_booking_details

ticket_bp = Blueprint("tickets", __name__)


@ticket_bp.route("/tickets/<booking_reference>")
def view_ticket(booking_reference: str):
    """Renders consolidated multi-ticket page with QR codes for all booked attendees."""
    booking_details = get_consolidated_booking_details(booking_reference)
    if not booking_details:
        abort(404, description="Booking not found.")

    return render_template("ticket.html", booking=booking_details)


@ticket_bp.route("/tickets/<booking_reference>/download")
def download_ticket(booking_reference: str):
    """Renders standalone printable/saveable ticket format."""
    booking_details = get_consolidated_booking_details(booking_reference)
    if not booking_details:
        abort(404, description="Booking not found.")

    return render_template("ticket.html", booking=booking_details, is_print_view=True)


@ticket_bp.route("/api/tickets/<booking_reference>", methods=["GET"])
def api_get_ticket_details(booking_reference: str):
    """Returns JSON payload of consolidated booking and tickets."""
    booking_details = get_consolidated_booking_details(booking_reference)
    if not booking_details:
        return jsonify({"success": False, "message": "Booking not found."}), 404

    return jsonify({"success": True, "booking": booking_details})
