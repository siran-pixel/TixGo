from datetime import datetime, date, time, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, send_file
from models import db, utcnow, Admin, Event, EventSection, Booking, User, Seat, Attendee, Payment, Ticket
from utils.security import admin_required, set_admin_session, clear_admin_session, get_current_admin
from utils.validators import validate_email, validate_event_rules
from services.seat_generator_service import (
    generate_seats_for_event,
    provision_dynamic_layout,
    get_default_sections_for_event_type,
)
from services.seat_lock_service import admin_lock_seats, admin_unlock_seats
from services.export_service import (
    export_to_csv_stream,
    export_to_excel_stream,
    generate_date_wise_booking_csv,
    generate_section_wise_organizer_csv,
    generate_all_sections_zip,
)
from config import Config

admin_bp = Blueprint("admin", __name__)


@admin_bp.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    """Separate dedicated admin login portal."""
    if session.get("admin_id"):
        return redirect(url_for("admin.admin_dashboard"))

    if request.method == "POST":
        data = request.get_json() if request.is_json else request.form
        email = data.get("email", "").strip().lower()
        password = data.get("password", "")

        if not email or not password:
            msg = "Please enter admin email and password."
            if request.is_json:
                return jsonify({"success": False, "message": msg}), 400
            flash(msg, "danger")
            return render_template("admin/login.html"), 400

        # Check in DB first
        admin = Admin.query.filter_by(email=email).first()
        
        # If admin doesn't exist in DB, verify with Config/env development credentials
        if not admin and email == Config.ADMIN_EMAIL.lower() and password == Config.ADMIN_PASSWORD:
            admin = Admin(email=Config.ADMIN_EMAIL, is_active=True)
            admin.set_password(Config.ADMIN_PASSWORD)
            db.session.add(admin)
            db.session.commit()

        if admin and admin.check_password(password) and admin.is_active:
            set_admin_session(admin)
            flash("Admin login successful.", "success")
            if request.is_json:
                return jsonify({"success": True, "redirect_url": url_for("admin.admin_dashboard")})
            return redirect(url_for("admin.admin_dashboard"))

        msg = "Invalid admin credentials."
        if request.is_json:
            return jsonify({"success": False, "message": msg}), 401
        flash(msg, "danger")
        return render_template("admin/login.html"), 401

    return render_template("admin/login.html")


@admin_bp.route("/admin/logout")
def admin_logout():
    """Logs out admin user."""
    clear_admin_session()
    flash("Admin logged out successfully.", "info")
    return redirect(url_for("admin.admin_login"))


@admin_bp.route("/admin/dashboard")
@admin_required
def admin_dashboard():
    """Central metrics dashboard for administrative monitoring."""
    total_events = Event.query.count()
    total_users = User.query.count()
    total_bookings = Booking.query.count()
    
    # Calculate tickets sold and total revenue
    tickets_sold = Ticket.query.count()
    total_revenue = db.session.query(db.func.sum(Booking.total_amount))\
        .filter(Booking.booking_status == "CONFIRMED").scalar() or 0.0

    today = date.today()
    upcoming_events_count = Event.query.filter(Event.event_date >= today, Event.status == "ACTIVE").count()

    recent_bookings = Booking.query.order_by(Booking.created_at.desc()).limit(8).all()
    upcoming_events = Event.query.filter(Event.event_date >= today, Event.status == "ACTIVE")\
        .order_by(Event.event_date.asc()).limit(5).all()

    return render_template(
        "admin/dashboard.html",
        total_events=total_events,
        total_users=total_users,
        total_bookings=total_bookings,
        tickets_sold=tickets_sold,
        total_revenue=float(total_revenue),
        upcoming_events_count=upcoming_events_count,
        recent_bookings=recent_bookings,
        upcoming_events=upcoming_events,
    )


@admin_bp.route("/admin/events")
@admin_required
def admin_events():
    """Event management catalog view."""
    events = Event.query.order_by(Event.event_date.desc()).all()
    return render_template("admin/events.html", events=events)


@admin_bp.route("/admin/events/add", methods=["GET", "POST"])
@admin_required
def admin_add_event():
    """Adds a new event and automatically provisions its seating layout."""
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        event_type = request.form.get("event_type", "Cinema").strip()
        banner_image = request.form.get("banner_image", "").strip() or "/static/images/event_cinema.jpg"
        venue = request.form.get("venue", "").strip()
        city = request.form.get("city", "").strip()
        event_date_str = request.form.get("event_date", "")
        event_time_str = request.form.get("event_time", "")
        
        try:
            total_seats = int(request.form.get("total_seats", 300))
            price = float(request.form.get("price", 500.0))
        except (ValueError, TypeError):
            flash("Invalid capacity or price value.", "danger")
            return render_template("admin/add_event.html")

        # Validate event rules
        is_valid, err_msg = validate_event_rules(event_type, total_seats, price)
        if not is_valid:
            flash(err_msg, "danger")
            return render_template("admin/add_event.html")

        try:
            event_date = datetime.strptime(event_date_str, "%Y-%m-%d").date()
            event_time = datetime.strptime(event_time_str, "%H:%M").time()
        except ValueError:
            flash("Invalid date or time format.", "danger")
            return render_template("admin/add_event.html")

        new_event = Event(
            name=name,
            description=description,
            event_type=event_type,
            banner_image=banner_image,
            venue=venue,
            city=city,
            event_date=event_date,
            event_time=event_time,
            total_seats=0,  # Will be updated by seat generator
            status="ACTIVE",
        )
        db.session.add(new_event)
        db.session.commit()

        action = request.form.get("action", "save")
        if action == "configure_layout":
            flash(f"Event '{name}' created! Please configure its dynamic seating layout below.", "info")
            return redirect(url_for("admin.admin_event_layout_designer", event_id=new_event.id))

        # Automatically provision default preset seats
        seat_count = generate_seats_for_event(
            event=new_event,
            custom_price=price,
            custom_capacity=total_seats
        )

        flash(f"Event '{name}' created successfully with {seat_count} seats generated!", "success")
        return redirect(url_for("admin.admin_events"))

    return render_template("admin/add_event.html")


@admin_bp.route("/admin/events/<int:event_id>/edit", methods=["GET", "POST"])
@admin_required
def admin_edit_event(event_id: int):
    """Edits event metadata and status."""
    event = db.session.get(Event, event_id)
    if not event:
        flash("Event not found.", "danger")
        return redirect(url_for("admin.admin_events"))

    if request.method == "POST":
        event.name = request.form.get("name", event.name).strip()
        event.description = request.form.get("description", event.description).strip()
        event.venue = request.form.get("venue", event.venue).strip()
        event.city = request.form.get("city", event.city).strip()
        event.banner_image = request.form.get("banner_image", event.banner_image).strip()
        event.status = request.form.get("status", event.status).strip()

        date_str = request.form.get("event_date")
        time_str = request.form.get("event_time")
        if date_str:
            try:
                event.event_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError:
                pass
        if time_str:
            try:
                event.event_time = datetime.strptime(time_str, "%H:%M").time()
            except ValueError:
                pass

        db.session.commit()
        flash(f"Event '{event.name}' updated successfully.", "success")
        return redirect(url_for("admin.admin_events"))

    return render_template("admin/edit_event.html", event=event)


@admin_bp.route("/admin/events/<int:event_id>/delete", methods=["POST"])
@admin_required
def admin_delete_event(event_id: int):
    """Cancels or removes an event."""
    event = db.session.get(Event, event_id)
    if not event:
        flash("Event not found.", "danger")
        return redirect(url_for("admin.admin_events"))

    if event.bookings:
        # If event has bookings, soft-cancel to preserve historical records
        event.status = "CANCELLED"
        db.session.commit()
        flash(f"Event '{event.name}' has active bookings, so its status was changed to CANCELLED.", "warning")
    else:
        db.session.delete(event)
        db.session.commit()
        flash(f"Event '{event.name}' removed successfully.", "success")

    return redirect(url_for("admin.admin_events"))


@admin_bp.route("/admin/bookings")
@admin_required
def admin_bookings():
    """All system bookings with attendee details."""
    search = request.args.get("search", "").strip()
    status_filter = request.args.get("status", "").strip()

    query = Booking.query.join(User).join(Event)

    if search:
        query = query.filter(
            (Booking.booking_reference.ilike(f"%{search}%")) |
            (User.full_name.ilike(f"%{search}%")) |
            (User.email.ilike(f"%{search}%")) |
            (Event.name.ilike(f"%{search}%"))
        )

    if status_filter:
        query = query.filter(Booking.booking_status == status_filter)

    bookings = query.order_by(Booking.created_at.desc()).all()
    return render_template("admin/bookings.html", bookings=bookings, search_query=search, status_filter=status_filter)


@admin_bp.route("/admin/users")
@admin_required
def admin_users():
    """Registered users directory."""
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template("admin/users.html", users=users)


@admin_bp.route("/admin/revenue")
@admin_required
def admin_revenue():
    """Revenue analysis and financial breakdown."""
    today = date.today()
    today_start = datetime.combine(today, time.min)
    today_end = datetime.combine(today + timedelta(days=1), time.min)
    month_start = datetime.combine(today.replace(day=1), time.min)
    
    total_revenue = db.session.query(db.func.sum(Booking.total_amount))\
        .filter(Booking.booking_status == "CONFIRMED").scalar() or 0.0

    today_revenue = db.session.query(db.func.sum(Booking.total_amount))\
        .filter(Booking.booking_status == "CONFIRMED", Booking.created_at >= today_start, Booking.created_at < today_end).scalar() or 0.0

    monthly_revenue = db.session.query(db.func.sum(Booking.total_amount))\
        .filter(Booking.booking_status == "CONFIRMED", Booking.created_at >= month_start).scalar() or 0.0

    tickets_sold = Ticket.query.count()
    tickets_available = Seat.query.filter_by(status="AVAILABLE").count()
    cancellations = Booking.query.filter_by(booking_status="CANCELLED").count()

    # Revenue by event type
    revenue_by_type = db.session.query(
        Event.event_type,
        db.func.sum(Booking.total_amount).label("total_rev"),
        db.func.count(Booking.id).label("booking_count")
    ).join(Booking, Booking.event_id == Event.id)\
     .filter(Booking.booking_status == "CONFIRMED")\
     .group_by(Event.event_type).all()

    type_stats = [{"type": row.event_type, "revenue": float(row.total_rev or 0), "bookings": row.booking_count} for row in revenue_by_type]

    return render_template(
        "admin/revenue.html",
        total_revenue=float(total_revenue),
        today_revenue=float(today_revenue),
        monthly_revenue=float(monthly_revenue),
        tickets_sold=tickets_sold,
        tickets_available=tickets_available,
        cancellations=cancellations,
        type_stats=type_stats,
    )


@admin_bp.route("/admin/reports")
@admin_required
def admin_reports():
    """Export and reporting page."""
    events = Event.query.order_by(Event.name.asc()).all()
    return render_template("admin/reports.html", events=events)


@admin_bp.route("/api/admin/export/csv")
@admin_required
def api_export_csv():
    """Downloads CSV report of bookings."""
    event_id = request.args.get("event_id", type=int)
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")

    stream = export_to_csv_stream(event_id, start_date, end_date)
    filename = f"showspot_bookings_{utcnow().strftime('%Y%m%d_%H%M%S')}.csv"

    return send_file(
        stream,
        mimetype="text/csv",
        as_attachment=True,
        download_name=filename,
    )


@admin_bp.route("/api/admin/export/excel")
@admin_required
def api_export_excel():
    """Downloads Excel XLSX report of bookings."""
    event_id = request.args.get("event_id", type=int)
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")

    stream = export_to_excel_stream(event_id, start_date, end_date)
    filename = f"showspot_bookings_{utcnow().strftime('%Y%m%d_%H%M%S')}.xlsx"

    return send_file(
        stream,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name=filename,
    )


# =========================================================================
# Date-Wise Booking Reports (Feature 1)
# =========================================================================

@admin_bp.route("/admin/reports/date-wise")
@admin_required
def admin_date_wise_reports():
    """Date-Wise Booking Reports interface with date and status filters."""
    events = Event.query.order_by(Event.name.asc()).all()
    today_str = date.today().strftime("%Y-%m-%d")
    return render_template(
        "admin/date_wise_reports.html",
        events=events,
        today_str=today_str,
    )


@admin_bp.route("/admin/reports/date-wise/download")
@admin_required
def admin_download_date_wise_csv():
    """Streams the 29-column Date-Wise Booking CSV report with daily financial summary."""
    event_id = request.args.get("event_id", type=int)
    booking_date = request.args.get("booking_date")
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    payment_status = request.args.get("payment_status")
    booking_status = request.args.get("booking_status")

    stream, filename = generate_date_wise_booking_csv(
        booking_date=booking_date,
        start_date=start_date,
        end_date=end_date,
        event_id=event_id,
        payment_status=payment_status,
        booking_status=booking_status,
    )

    return send_file(
        stream,
        mimetype="text/csv",
        as_attachment=True,
        download_name=filename,
    )


# =========================================================================
# Organizer Reports - Section-Wise CSV Export (Feature 2)
# =========================================================================

@admin_bp.route("/admin/reports/organizer")
@admin_required
def admin_organizer_reports():
    """Section-Wise Organizer Reports interface with dynamic section picker."""
    events = Event.query.order_by(Event.name.asc()).all()
    return render_template("admin/organizer_reports.html", events=events)


@admin_bp.route("/admin/api/events/<int:event_id>/sections")
@admin_required
def api_event_sections(event_id: int):
    """API returning all configured sections/stands for the selected event."""
    event = db.session.get(Event, event_id)
    if not event:
        return jsonify({"success": False, "message": "Event not found."}), 404

    sections = []
    # If custom sections exist in EventSection
    for sec in event.sections:
        sections.append({
            "id": sec.id,
            "name": sec.name,
            "section_type": sec.section_type,
            "price": float(sec.price),
            "total_seats": sec.total_seats,
        })

    # If no custom sections, query distinct seat sections
    if not sections:
        distinct = db.session.query(Seat.section).filter(Seat.event_id == event_id).distinct().all()
        for d in distinct:
            if d[0]:
                count = Seat.query.filter_by(event_id=event_id, section=d[0]).count()
                sample_seat = Seat.query.filter_by(event_id=event_id, section=d[0]).first()
                price = float(sample_seat.price) if sample_seat else 0.0
                sections.append({
                    "id": None,
                    "name": d[0],
                    "section_type": "Section",
                    "price": price,
                    "total_seats": count,
                })

    return jsonify({"success": True, "event_name": event.name, "sections": sections})


@admin_bp.route("/admin/reports/organizer/download")
@admin_required
def admin_download_organizer_section_csv():
    """Streams a section-wise CSV report safe for external event organizers."""
    event_id = request.args.get("event_id", type=int)
    section_name = request.args.get("section")
    include_unconfirmed = request.args.get("include_unconfirmed", "false").lower() == "true"

    if not event_id or not section_name:
        flash("Please select both an event and a section.", "warning")
        return redirect(url_for("admin.admin_organizer_reports"))

    try:
        stream, filename = generate_section_wise_organizer_csv(
            event_id=event_id,
            section_name=section_name,
            include_unconfirmed=include_unconfirmed,
        )
        return send_file(
            stream,
            mimetype="text/csv",
            as_attachment=True,
            download_name=filename,
        )
    except Exception as exc:
        flash(f"Error generating section report: {str(exc)}", "danger")
        return redirect(url_for("admin.admin_organizer_reports"))


@admin_bp.route("/admin/reports/organizer/download-all")
@admin_required
def admin_download_organizer_all_zip():
    """Streams a ZIP archive containing individual CSV reports for each section in the event."""
    event_id = request.args.get("event_id", type=int)
    include_unconfirmed = request.args.get("include_unconfirmed", "false").lower() == "true"

    if not event_id:
        flash("Please select an event to download section reports.", "warning")
        return redirect(url_for("admin.admin_organizer_reports"))

    try:
        stream, filename = generate_all_sections_zip(
            event_id=event_id,
            include_unconfirmed=include_unconfirmed,
        )
        return send_file(
            stream,
            mimetype="application/zip",
            as_attachment=True,
            download_name=filename,
        )
    except Exception as exc:
        flash(f"Error generating all-sections zip: {str(exc)}", "danger")
        return redirect(url_for("admin.admin_organizer_reports"))


# =========================================================================
# Event Date Management - November 2026 (Feature 3)
# =========================================================================

@admin_bp.route("/admin/events/date-management", methods=["GET"])
@admin_required
def admin_event_date_management():
    """View and manage event schedules with November 2026 validation."""
    events = Event.query.order_by(Event.event_date.asc(), Event.id.asc()).all()
    return render_template("admin/event_date_management.html", events=events)


@admin_bp.route("/admin/events/date-management/update-single", methods=["POST"])
@admin_required
def api_update_event_date_single():
    """Updates an individual event's date in November 2026, preserving bookings and layout."""
    data = request.get_json() if request.is_json else request.form
    event_id = data.get("event_id")
    new_date_str = data.get("new_date")
    new_time_str = data.get("new_time")

    if not event_id or not new_date_str:
        msg = "Event ID and new date are required."
        if request.is_json:
            return jsonify({"success": False, "message": msg}), 400
        flash(msg, "danger")
        return redirect(url_for("admin.admin_event_date_management"))

    event = db.session.get(Event, int(event_id))
    if not event:
        msg = "Event not found."
        if request.is_json:
            return jsonify({"success": False, "message": msg}), 404
        flash(msg, "danger")
        return redirect(url_for("admin.admin_event_date_management"))

    try:
        parsed_date = datetime.strptime(new_date_str.strip(), "%Y-%m-%d").date()
    except ValueError:
        msg = "Invalid date format. Expected YYYY-MM-DD."
        if request.is_json:
            return jsonify({"success": False, "message": msg}), 400
        flash(msg, "danger")
        return redirect(url_for("admin.admin_event_date_management"))

    # Validate November 2026
    if parsed_date.year != 2026 or parsed_date.month != 11:
        msg = f"Date must be in November 2026 (2026-11-01 to 2026-11-30). Received: {new_date_str}."
        if request.is_json:
            return jsonify({"success": False, "message": msg}), 400
        flash(msg, "danger")
        return redirect(url_for("admin.admin_event_date_management"))

    event.event_date = parsed_date
    if new_time_str:
        try:
            event.event_time = datetime.strptime(new_time_str.strip(), "%H:%M").time()
        except ValueError:
            pass

    db.session.commit()
    msg = f"Event '{event.name}' successfully rescheduled to {parsed_date.strftime('%B %d, %Y')}."
    if request.is_json:
        return jsonify({
            "success": True,
            "message": msg,
            "event_id": event.id,
            "new_date": parsed_date.strftime("%Y-%m-%d"),
        })
    flash(msg, "success")
    return redirect(url_for("admin.admin_event_date_management"))


@admin_bp.route("/admin/events/date-management/sync-all-november", methods=["POST"])
@admin_required
def api_sync_all_events_november():
    """Syncs/updates all events to dates across November 2026 without altering layouts or bookings."""
    events = Event.query.order_by(Event.id.asc()).all()
    if not events:
        msg = "No events found to update."
        if request.is_json:
            return jsonify({"success": False, "message": msg}), 400
        flash(msg, "warning")
        return redirect(url_for("admin.admin_event_date_management"))

    day_step = max(1, 28 // max(1, len(events)))
    updated_count = 0
    for idx, evt in enumerate(events):
        day = min(28, 1 + (idx * day_step))
        evt.event_date = date(2026, 11, day)
        updated_count += 1

    db.session.commit()
    msg = f"Successfully updated all {updated_count} events to November 2026."
    if request.is_json:
        return jsonify({"success": True, "message": msg, "updated_count": updated_count})
    flash(msg, "success")
    return redirect(url_for("admin.admin_event_date_management"))


@admin_bp.route("/admin/seats")
@admin_required
def admin_seats():
    """Admin interactive Seat Management view for locking/unlocking seats."""
    events = Event.query.order_by(Event.event_date.asc()).all()
    selected_event_id = request.args.get("event_id", type=int)

    selected_event = None
    if selected_event_id:
        selected_event = db.session.get(Event, selected_event_id)
    if not selected_event and events:
        selected_event = events[0]

    stats = {
        "total": 0,
        "available": 0,
        "booked": 0,
        "admin_locked": 0,
    }
    if selected_event:
        stats["total"] = selected_event.seats.count()
        stats["available"] = selected_event.seats.filter_by(status="AVAILABLE").count()
        stats["booked"] = selected_event.seats.filter_by(status="BOOKED").count()
        stats["admin_locked"] = selected_event.seats.filter_by(status="ADMIN_LOCKED").count()

    return render_template(
        "admin/seats.html",
        events=events,
        selected_event=selected_event,
        stats=stats,
    )


@admin_bp.route("/admin/events/<int:event_id>/seats")
@admin_required
def admin_event_seats(event_id: int):
    """Direct shortcut route to lock/unlock seats for a specific event."""
    return redirect(url_for("admin.admin_seats", event_id=event_id))


@admin_bp.route("/admin/api/events/<int:event_id>/seats/lock", methods=["POST"])
@admin_required
def api_admin_lock_seats(event_id: int):
    """API endpoint for admin to lock selected seats for resource persons/guests."""
    data = request.get_json() or {}
    seat_ids = data.get("seat_ids", [])
    reason = data.get("reason", "Resource Person")

    success, message, res_data = admin_lock_seats(
        event_id=event_id,
        seat_ids=seat_ids,
        reason=reason
    )
    return jsonify({
        "success": success,
        "message": message,
        "data": res_data,
    }), (200 if success else 400)


@admin_bp.route("/admin/api/events/<int:event_id>/seats/unlock", methods=["POST"])
@admin_required
def api_admin_unlock_seats(event_id: int):
    """API endpoint for admin to unlock previously locked seats back to AVAILABLE."""
    data = request.get_json() or {}
    seat_ids = data.get("seat_ids", [])

    success, message, res_data = admin_unlock_seats(
        event_id=event_id,
        seat_ids=seat_ids
    )
    return jsonify({
        "success": success,
        "message": message,
        "data": res_data,
    }), (200 if success else 400)


# =========================================================================
# Dynamic Seat Layout & Pricing Management Routes
# =========================================================================

@admin_bp.route("/admin/seat-layouts")
@admin_required
def admin_seat_layouts():
    """Seat Layout Management Catalog: list events with layout statistics and actions."""
    events = Event.query.order_by(Event.event_date.desc()).all()
    return render_template("admin/seat_layouts.html", events=events)


@admin_bp.route("/admin/events/<int:event_id>/layout", methods=["GET", "POST"])
@admin_required
def admin_event_layout_designer(event_id: int):
    """Interactive Dynamic Section, Stand, Row, and Pricing Layout Designer."""
    event = db.session.get(Event, event_id)
    if not event:
        flash("Event not found.", "danger")
        return redirect(url_for("admin.admin_events"))

    if request.method == "POST":
        import json
        data = request.get_json() if request.is_json else None
        if not data and request.form:
            sections_json = request.form.get("sections_json")
            if sections_json:
                try:
                    data = {"sections": json.loads(sections_json)}
                except ValueError:
                    data = None

        if not data or "sections" not in data:
            if request.is_json:
                return jsonify({"success": False, "message": "Invalid layout configuration data."}), 400
            flash("Invalid layout configuration submitted.", "danger")
            return redirect(url_for("admin.admin_event_layout_designer", event_id=event_id))

        sections_config = data.get("sections", [])
        publish = data.get("publish", False) or (request.form.get("action") == "publish")

        success, message, seat_count = provision_dynamic_layout(event, sections_config)
        if success:
            if publish:
                event.status = "ACTIVE"
                db.session.commit()
                message += " Event is now ACTIVE and published for users."

            if request.is_json:
                return jsonify({
                    "success": True,
                    "message": message,
                    "seat_count": seat_count,
                    "total_seats": event.total_seats,
                    "sections_count": len(event.sections),
                })
            flash(message, "success")
            return redirect(url_for("admin.admin_seat_layouts"))
        else:
            if request.is_json:
                return jsonify({"success": False, "message": message}), 400
            flash(message, "danger")
            return redirect(url_for("admin.admin_event_layout_designer", event_id=event_id))

    # GET request: prepare existing or default sections
    existing_sections = [s.to_dict() for s in event.sections]
    if not existing_sections:
        existing_sections = get_default_sections_for_event_type(event.event_type)

    has_bookings = Seat.query.filter_by(event_id=event.id, status="BOOKED").count() > 0

    return render_template(
        "admin/layout_designer.html",
        event=event,
        initial_sections=existing_sections,
        has_bookings=has_bookings,
    )


@admin_bp.route("/admin/api/events/<int:event_id>/layout/preview", methods=["POST"])
@admin_required
def api_preview_layout(event_id: int):
    """Calculates live summary and previews seat layout without modifying the database."""
    event = db.session.get(Event, event_id)
    if not event:
        return jsonify({"success": False, "message": "Event not found."}), 404

    data = request.get_json() or {}
    sections = data.get("sections", [])
    if not sections:
        return jsonify({"success": False, "message": "No sections provided for preview."}), 400

    total_seats = 0
    total_revenue_potential = 0.0
    section_summaries = []
    min_p = float("inf")
    max_p = 0.0

    for idx, sec in enumerate(sections):
        name = sec.get("name", f"Section {idx+1}")
        price = float(sec.get("price", 0.0))
        color = sec.get("color", "#6366f1")
        rows = sec.get("rows", [])
        sec_seats = sum(int(r.get("seat_count", 0)) for r in rows)
        sec_rev = sec_seats * price

        total_seats += sec_seats
        total_revenue_potential += sec_rev
        if price < min_p: min_p = price
        if price > max_p: max_p = price

        section_summaries.append({
            "name": name,
            "section_type": sec.get("section_type", "Section"),
            "price": price,
            "color": color,
            "rows_count": len(rows),
            "total_seats": sec_seats,
            "potential_revenue": sec_rev,
        })

    return jsonify({
        "success": True,
        "total_seats": total_seats,
        "total_sections": len(sections),
        "min_price": min_p if min_p != float("inf") else 0,
        "max_price": max_p,
        "potential_revenue": total_revenue_potential,
        "sections": section_summaries,
    })
