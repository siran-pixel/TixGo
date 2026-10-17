import io
import csv
import zipfile
import re
from datetime import datetime, date, time
from pathlib import Path
from typing import Optional, Tuple, List, Dict, Any
import pandas as pd
from models import db, Booking, Attendee, Ticket, Seat, Event, User, Payment, EventSection
from config import Config


def build_booking_export_dataframe(
    event_id: Optional[int] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> pd.DataFrame:
    """Queries all booking rows with attendees and tickets and formats them for tabular export."""
    query = db.session.query(
        Booking.id.label("booking_id"),
        Booking.booking_reference.label("booking_ref"),
        User.full_name.label("user_name"),
        User.email.label("user_email"),
        Event.name.label("event_name"),
        Event.venue.label("venue"),
        Event.event_date.label("event_date"),
        Event.event_time.label("event_time"),
        Ticket.ticket_number.label("ticket_id"),
        Seat.seat_number.label("seat_number"),
        Seat.category.label("category"),
        Attendee.full_name.label("attendee_name"),
        Attendee.age.label("attendee_age"),
        Attendee.phone.label("attendee_phone"),
        Attendee.city.label("attendee_city"),
        Seat.price.label("ticket_price"),
        Booking.total_amount.label("payment_amount"),
        Payment.payment_status.label("payment_status"),
        Booking.booking_status.label("booking_status"),
        Booking.created_at.label("booking_date"),
    ).join(User, Booking.user_id == User.id)\
     .join(Event, Booking.event_id == Event.id)\
     .join(Attendee, Attendee.booking_id == Booking.id)\
     .join(Seat, Attendee.seat_id == Seat.id)\
     .outerjoin(Ticket, Ticket.attendee_id == Attendee.id)\
     .outerjoin(Payment, Payment.booking_id == Booking.id)

    if event_id:
        query = query.filter(Booking.event_id == event_id)

    if start_date:
        try:
            s_dt = datetime.strptime(start_date, "%Y-%m-%d")
            query = query.filter(Booking.created_at >= s_dt)
        except ValueError:
            pass

    if end_date:
        try:
            e_dt = datetime.strptime(end_date, "%Y-%m-%d")
            query = query.filter(Booking.created_at <= e_dt)
        except ValueError:
            pass

    results = query.order_by(Booking.created_at.desc()).all()

    data = []
    for row in results:
        data.append({
            "Booking ID": row.booking_ref,
            "User Name": row.user_name,
            "User Email": row.user_email,
            "Event": row.event_name,
            "Venue": row.venue,
            "Date": row.event_date.strftime("%Y-%m-%d") if row.event_date else "",
            "Time": row.event_time.strftime("%H:%M") if row.event_time else "",
            "Ticket ID": row.ticket_id or "N/A",
            "Seat Number": row.seat_number,
            "Category": row.category,
            "Attendee Name": row.attendee_name,
            "Age": row.attendee_age,
            "Phone": row.attendee_phone,
            "City": row.attendee_city,
            "Ticket Price": float(row.ticket_price) if row.ticket_price else 0.0,
            "Payment Amount": float(row.payment_amount) if row.payment_amount else 0.0,
            "Payment Status": row.payment_status or "SUCCESS",
            "Booking Status": row.booking_status,
            "Booking Date": row.booking_date.strftime("%Y-%m-%d %H:%M:%S") if row.booking_date else "",
        })

    if not data:
        # Create empty DataFrame with required columns
        columns = [
            "Booking ID", "User Name", "User Email", "Event", "Venue", "Date", "Time",
            "Ticket ID", "Seat Number", "Category", "Attendee Name", "Age", "Phone", "City",
            "Ticket Price", "Payment Amount", "Payment Status", "Booking Status", "Booking Date"
        ]
        return pd.DataFrame(columns=columns)

    return pd.DataFrame(data)


def export_to_csv_stream(event_id: Optional[int] = None, start_date: Optional[str] = None, end_date: Optional[str] = None) -> io.BytesIO:
    """Exports filtered bookings as a CSV file in an in-memory byte stream."""
    df = build_booking_export_dataframe(event_id, start_date, end_date)
    output = io.BytesIO()
    df.to_csv(output, index=False, encoding="utf-8-sig")
    output.seek(0)
    return output


def export_to_excel_stream(event_id: Optional[int] = None, start_date: Optional[str] = None, end_date: Optional[str] = None) -> io.BytesIO:
    """Exports filtered bookings as a styled Excel file in an in-memory byte stream."""
    df = build_booking_export_dataframe(event_id, start_date, end_date)
    output = io.BytesIO()
    
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Bookings")
        workbook = writer.book
        worksheet = writer.sheets["Bookings"]
        
        # Auto-adjust column widths
        for col in worksheet.columns:
            max_len = max(len(str(cell.value or "")) for cell in col)
            col_letter = col[0].column_letter
            worksheet.column_dimensions[col_letter].width = max(max_len + 3, 12)

    output.seek(0)
    return output


def sanitize_csv_cell(value: Any) -> Any:
    """Mitigates CSV formula injection by prepending a single quote if the value begins with unsafe characters."""
    if value is None:
        return ""
    val_str = str(value)
    if val_str and val_str[0] in ("=", "+", "-", "@", "\t", "\r"):
        return f"'{val_str}"
    return val_str


def sanitize_filename(name: str) -> str:
    """Sanitizes strings to create clean, filesystem-safe filenames."""
    if not name:
        return "file"
    cleaned = re.sub(r'[^a-zA-Z0-9_\-]', '_', name.strip())
    return re.sub(r'_+', '_', cleaned).strip('_')


def generate_date_wise_booking_csv(
    booking_date: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    event_id: Optional[int] = None,
    payment_status: Optional[str] = None,
    booking_status: Optional[str] = None,
) -> Tuple[io.BytesIO, str]:
    """
    Generates a Date-Wise Booking Report CSV with 29 comprehensive financial and booking columns,
    properly distributed fees for multi-ticket bookings, formula injection mitigation,
    and a Daily Final Summary block at the bottom.
    """
    query = Booking.query

    # Event filter
    if event_id:
        query = query.filter(Booking.event_id == event_id)

    # Date / Date Range filter (based on booking creation date)
    s_dt = None
    e_dt = None

    if start_date:
        try:
            s_dt = datetime.strptime(start_date, "%Y-%m-%d").replace(hour=0, minute=0, second=0, microsecond=0)
        except ValueError:
            pass
    if end_date:
        try:
            e_dt = datetime.strptime(end_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59, microsecond=999999)
        except ValueError:
            pass

    if not s_dt and not e_dt and booking_date:
        try:
            b_dt = datetime.strptime(booking_date, "%Y-%m-%d")
            s_dt = b_dt.replace(hour=0, minute=0, second=0, microsecond=0)
            e_dt = b_dt.replace(hour=23, minute=59, second=59, microsecond=999999)
        except ValueError:
            pass

    if s_dt:
        query = query.filter(Booking.created_at >= s_dt)
    if e_dt:
        query = query.filter(Booking.created_at <= e_dt)

    # Booking status filter
    if booking_status and booking_status.strip().upper() not in ("", "ALL"):
        query = query.filter(Booking.booking_status == booking_status.strip().upper())

    # Payment status filter
    if payment_status and payment_status.strip().upper() not in ("", "ALL"):
        query = query.join(Payment, Payment.booking_id == Booking.id).filter(Payment.payment_status == payment_status.strip().upper())

    bookings = query.order_by(Booking.created_at.desc()).all()

    # Determine filename
    if booking_date and not start_date and not end_date:
        filename = f"daily_bookings_{booking_date}.csv"
    elif start_date and end_date:
        filename = f"daily_bookings_{start_date}_to_{end_date}.csv"
    elif start_date:
        filename = f"daily_bookings_from_{start_date}.csv"
    elif end_date:
        filename = f"daily_bookings_until_{end_date}.csv"
    else:
        filename = f"daily_bookings_{datetime.now().strftime('%Y-%m-%d')}.csv"

    output = io.StringIO()
    writer = csv.writer(output, lineterminator="\r\n")

    # 29 specific column headers
    headers = [
        "Booking ID", "Booking Date", "Booking Time", "Event Name", "Event Category",
        "Event Date", "Event Venue", "User Name", "User ID", "Mobile Number",
        "Email Address", "Section or Stand Name", "Row Name", "Seat Number", "Number of Tickets",
        "Price Per Ticket", "Base Ticket Amount", "Discount Amount", "Convenience Fee", "Booking Fee",
        "Other Extra Charges", "Tax Amount", "Total Payable Amount", "Actual Amount Paid",
        "Pending Amount", "Payment Method", "Payment Transaction ID", "Payment Status", "Booking Status"
    ]
    writer.writerow(headers)

    # Financial and attendance aggregators for Daily Final Summary
    unique_user_ids = set()
    total_tickets_count = 0
    total_base_amount = 0.0
    total_extra_charges = 0.0
    total_discounts = 0.0
    total_payable_amount = 0.0
    total_actual_paid = 0.0
    total_pending_amount = 0.0
    total_refunds = 0.0

    for b in bookings:
        unique_user_ids.add(b.user_id)
        b_paid = 0.0
        pay_method = "N/A"
        pay_txn = "N/A"
        pay_status = "PENDING"

        if b.payment:
            pay_method = b.payment.payment_method or "N/A"
            pay_txn = b.payment.transaction_id or "N/A"
            pay_status = b.payment.payment_status or "PENDING"
            if pay_status == "SUCCESS":
                b_paid = float(b.payment.amount)
            elif pay_status == "REFUNDED":
                total_refunds += float(b.payment.amount)

        b_total = float(b.total_amount)
        b_pending = max(0.0, round(b_total - b_paid, 2))
        total_payable_amount += b_total
        total_actual_paid += b_paid
        total_pending_amount += b_pending
        total_extra_charges += float(b.convenience_fee + b.tax)

        attendees = b.attendees or []
        num_attendees = len(attendees)

        if num_attendees == 0:
            total_tickets_count += b.total_tickets
            subtotal = float(b.subtotal)
            total_base_amount += subtotal
            per_ticket = subtotal / max(1, b.total_tickets)

            rows_data = [
                sanitize_csv_cell(b.booking_reference),
                sanitize_csv_cell(b.created_at.strftime("%Y-%m-%d") if b.created_at else ""),
                sanitize_csv_cell(b.created_at.strftime("%H:%M:%S") if b.created_at else ""),
                sanitize_csv_cell(b.event.name if b.event else "N/A"),
                sanitize_csv_cell(b.event.event_type if b.event else "N/A"),
                sanitize_csv_cell(b.event.event_date.strftime("%Y-%m-%d") if b.event and b.event.event_date else ""),
                sanitize_csv_cell(b.event.venue if b.event else "N/A"),
                sanitize_csv_cell(b.user.full_name if b.user else "N/A"),
                sanitize_csv_cell(str(b.user_id)),
                sanitize_csv_cell(b.user.phone if b.user else ""),
                sanitize_csv_cell(b.user.email if b.user else ""),
                sanitize_csv_cell("Standard"),
                sanitize_csv_cell("N/A"),
                sanitize_csv_cell("General Admission"),
                b.total_tickets,
                f"{per_ticket:.2f}",
                f"{subtotal:.2f}",
                "0.00",
                f"{float(b.convenience_fee):.2f}",
                "0.00",
                "0.00",
                f"{float(b.tax):.2f}",
                f"{b_total:.2f}",
                f"{b_paid:.2f}",
                f"{b_pending:.2f}",
                sanitize_csv_cell(pay_method),
                sanitize_csv_cell(pay_txn),
                sanitize_csv_cell(pay_status),
                sanitize_csv_cell(b.booking_status),
            ]
            writer.writerow(rows_data)
        else:
            # Distribute fees across attendee tickets without multiplying charges
            for att in attendees:
                total_tickets_count += 1
                seat = att.seat
                seat_price = float(seat.price) if seat and seat.price else (float(b.subtotal) / num_attendees)
                total_base_amount += seat_price

                conv_fee_item = round(float(b.convenience_fee) / num_attendees, 2)
                tax_item = round(float(b.tax) / num_attendees, 2)
                item_payable = round(seat_price + conv_fee_item + tax_item, 2)
                item_paid = round(b_paid / num_attendees, 2) if b_paid > 0 else 0.0
                item_pending = max(0.0, round(item_payable - item_paid, 2))

                section_name = seat.section if seat and seat.section else "Standard"
                row_label = seat.row_label if seat and seat.row_label else "N/A"
                seat_no = seat.seat_number if seat and seat.seat_number else "N/A"

                rows_data = [
                    sanitize_csv_cell(b.booking_reference),
                    sanitize_csv_cell(b.created_at.strftime("%Y-%m-%d") if b.created_at else ""),
                    sanitize_csv_cell(b.created_at.strftime("%H:%M:%S") if b.created_at else ""),
                    sanitize_csv_cell(b.event.name if b.event else "N/A"),
                    sanitize_csv_cell(b.event.event_type if b.event else "N/A"),
                    sanitize_csv_cell(b.event.event_date.strftime("%Y-%m-%d") if b.event and b.event.event_date else ""),
                    sanitize_csv_cell(b.event.venue if b.event else "N/A"),
                    sanitize_csv_cell(att.full_name or (b.user.full_name if b.user else "N/A")),
                    sanitize_csv_cell(str(b.user_id)),
                    sanitize_csv_cell(att.phone or (b.user.phone if b.user else "")),
                    sanitize_csv_cell(b.user.email if b.user else ""),
                    sanitize_csv_cell(section_name),
                    sanitize_csv_cell(row_label),
                    sanitize_csv_cell(seat_no),
                    1,
                    f"{seat_price:.2f}",
                    f"{seat_price:.2f}",
                    "0.00",
                    f"{conv_fee_item:.2f}",
                    "0.00",
                    "0.00",
                    f"{tax_item:.2f}",
                    f"{item_payable:.2f}",
                    f"{item_paid:.2f}",
                    f"{item_pending:.2f}",
                    sanitize_csv_cell(pay_method),
                    sanitize_csv_cell(pay_txn),
                    sanitize_csv_cell(pay_status),
                    sanitize_csv_cell(b.booking_status),
                ]
                writer.writerow(rows_data)

    # Append Daily Final Summary
    writer.writerow([])
    writer.writerow(["==================== DAILY FINAL SUMMARY ===================="])
    writer.writerow(["Summary Metric", "Value"])
    writer.writerow(["Total Unique Users", len(unique_user_ids)])
    writer.writerow(["Total Bookings", len(bookings)])
    writer.writerow(["Total Tickets Booked", total_tickets_count])
    writer.writerow(["Total Base Ticket Amount", f"{total_base_amount:.2f}"])
    writer.writerow(["Total Extra Charges", f"{total_extra_charges:.2f}"])
    writer.writerow(["Total Discounts", f"{total_discounts:.2f}"])
    writer.writerow(["Total Payable Amount", f"{total_payable_amount:.2f}"])
    writer.writerow(["Total Actual Amount Paid", f"{total_actual_paid:.2f}"])
    writer.writerow(["Total Pending Amount", f"{total_pending_amount:.2f}"])
    writer.writerow(["Total Refunded Amount", f"{total_refunds:.2f}"])

    bytes_output = io.BytesIO(output.getvalue().encode("utf-8-sig"))
    bytes_output.seek(0)
    return bytes_output, filename


def generate_section_wise_organizer_csv(
    event_id: int,
    section_name: str,
    include_unconfirmed: bool = False
) -> Tuple[io.BytesIO, str]:
    """
    Generates an organizer-safe CSV report for a specific section or stand.
    Excludes sensitive customer authentication credentials, payment card tokens, or internal secrets.
    """
    event = db.session.get(Event, event_id)
    if not event:
        raise ValueError(f"Event ID {event_id} not found.")

    query = db.session.query(
        Booking, Attendee, Seat, Payment, Ticket
    ).join(Attendee, Attendee.booking_id == Booking.id)\
     .join(Seat, Attendee.seat_id == Seat.id)\
     .outerjoin(Payment, Payment.booking_id == Booking.id)\
     .outerjoin(Ticket, Ticket.attendee_id == Attendee.id)\
     .filter(Booking.event_id == event_id)\
     .filter(Seat.section == section_name)

    if not include_unconfirmed:
        query = query.filter(Booking.booking_status == "CONFIRMED")

    results = query.order_by(Seat.seat_number.asc()).all()

    output = io.StringIO()
    writer = csv.writer(output, lineterminator="\r\n")

    headers = [
        "Booking ID", "Booking Date", "Booking Time", "Event Name",
        "Section or Stand Name", "Row Name", "Seat Number",
        "Attendee Name", "Mobile Number", "Email Address", "City",
        "Ticket Number", "Price Per Ticket", "Base Ticket Amount",
        "Discount Amount", "Extra Charges", "Total Payable Amount",
        "Actual Amount Paid", "Pending Amount", "Payment Method",
        "Payment Status", "Booking Status", "Ticket Status"
    ]
    writer.writerow(headers)

    total_tickets = 0
    total_base_amount = 0.0
    unique_attendee_names = set()
    total_amount_paid = 0.0

    for booking, attendee, seat, payment, ticket in results:
        total_tickets += 1
        seat_price = float(seat.price) if seat.price else 0.0
        total_base_amount += seat_price
        unique_attendee_names.add(attendee.full_name)

        num_att = max(1, len(booking.attendees))
        extra_charges = round(float(booking.convenience_fee + booking.tax) / num_att, 2)
        item_payable = round(seat_price + extra_charges, 2)
        item_paid = round(float(payment.amount) / num_att, 2) if (payment and payment.payment_status == "SUCCESS") else 0.0
        item_pending = max(0.0, round(item_payable - item_paid, 2))
        total_amount_paid += item_paid

        row_data = [
            sanitize_csv_cell(booking.booking_reference),
            sanitize_csv_cell(booking.created_at.strftime("%Y-%m-%d") if booking.created_at else ""),
            sanitize_csv_cell(booking.created_at.strftime("%H:%M:%S") if booking.created_at else ""),
            sanitize_csv_cell(event.name),
            sanitize_csv_cell(seat.section),
            sanitize_csv_cell(seat.row_label or "N/A"),
            sanitize_csv_cell(seat.seat_number),
            sanitize_csv_cell(attendee.full_name),
            sanitize_csv_cell(attendee.phone or (booking.user.phone if booking.user else "")),
            sanitize_csv_cell(booking.user.email if booking.user else ""),
            sanitize_csv_cell(attendee.city or ""),
            sanitize_csv_cell(ticket.ticket_number if ticket else "N/A"),
            f"{seat_price:.2f}",
            f"{seat_price:.2f}",
            "0.00",
            f"{extra_charges:.2f}",
            f"{item_payable:.2f}",
            f"{item_paid:.2f}",
            f"{item_pending:.2f}",
            sanitize_csv_cell(payment.payment_method if payment else "N/A"),
            sanitize_csv_cell(payment.payment_status if payment else "PENDING"),
            sanitize_csv_cell(booking.booking_status),
            sanitize_csv_cell(ticket.ticket_status if ticket else "ACTIVE"),
        ]
        writer.writerow(row_data)

    writer.writerow([])
    writer.writerow([f"==================== SECTION SUMMARY: {section_name} ===================="])
    writer.writerow(["Summary Metric", "Value"])
    writer.writerow(["Total Section Tickets Booked", total_tickets])
    writer.writerow(["Total Section Base Amount", f"{total_base_amount:.2f}"])
    writer.writerow(["Total Unique Attendees", len(unique_attendee_names)])
    writer.writerow(["Total Section Amount Paid", f"{total_amount_paid:.2f}"])

    sec_slug = sanitize_filename(section_name)
    filename = f"{sec_slug}_Users.csv"

    bytes_output = io.BytesIO(output.getvalue().encode("utf-8-sig"))
    bytes_output.seek(0)
    return bytes_output, filename


def generate_all_sections_zip(
    event_id: int,
    include_unconfirmed: bool = False
) -> Tuple[io.BytesIO, str]:
    """Packages individual section CSV reports for an event into an in-memory ZIP archive."""
    event = db.session.get(Event, event_id)
    if not event:
        raise ValueError(f"Event ID {event_id} not found.")

    sections = [s.name for s in event.sections]
    if not sections:
        distinct_secs = db.session.query(Seat.section).filter(Seat.event_id == event_id).distinct().all()
        sections = [s[0] for s in distinct_secs if s[0]]

    if not sections:
        sections = ["Standard"]

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for sec_name in sections:
            csv_stream, csv_filename = generate_section_wise_organizer_csv(
                event_id=event_id,
                section_name=sec_name,
                include_unconfirmed=include_unconfirmed
            )
            zip_file.writestr(csv_filename, csv_stream.getvalue())

    zip_buffer.seek(0)
    event_slug = sanitize_filename(event.name)
    zip_filename = f"{event_slug}_All_Sections_Reports.zip"
    return zip_buffer, zip_filename
