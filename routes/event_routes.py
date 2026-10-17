from datetime import datetime
from flask import Blueprint, render_template, request, jsonify, abort
from models import db, Event

event_bp = Blueprint("events", __name__)


@event_bp.route("/")
def landing_page():
    """Homepage with hero banner, category filters, and featured event cards."""
    category = request.args.get("category", "All").strip()
    search = request.args.get("search", "").strip()

    query = Event.query.filter(Event.status == "ACTIVE")

    if category and category.lower() != "all":
        query = query.filter(Event.event_type.ilike(category))

    if search:
        query = query.filter(
            (Event.name.ilike(f"%{search}%")) |
            (Event.city.ilike(f"%{search}%")) |
            (Event.venue.ilike(f"%{search}%")) |
            (Event.event_type.ilike(f"%{search}%"))
        )

    events = query.order_by(Event.event_date.asc(), Event.event_time.asc()).all()
    
    categories = [
        {"name": "All", "icon": "fa-layer-group"},
        {"name": "Cricket", "icon": "fa-baseball-bat-ball"},
        {"name": "Concert", "icon": "fa-music"},
        {"name": "General", "icon": "fa-ticket"},
    ]

    return render_template(
        "index.html",
        events=events,
        categories=categories,
        selected_category=category,
        search_query=search,
    )


@event_bp.route("/events")
def events_catalog():
    """Redirects or renders event catalog."""
    return landing_page()


@event_bp.route("/events/<int:event_id>")
def event_details(event_id: int):
    """Detailed event overview page."""
    event = db.session.get(Event, event_id)
    if not event:
        abort(404)
    return render_template("event_details.html", event=event)


# REST API endpoints
@event_bp.route("/api/events", methods=["GET"])
def api_events_list():
    """Returns list of active events with optional category and search filters."""
    category = request.args.get("category", "").strip()
    search = request.args.get("search", "").strip()

    query = Event.query.filter(Event.status == "ACTIVE")

    if category and category.lower() != "all":
        query = query.filter(Event.event_type.ilike(category))

    if search:
        query = query.filter(
            (Event.name.ilike(f"%{search}%")) |
            (Event.city.ilike(f"%{search}%")) |
            (Event.venue.ilike(f"%{search}%"))
        )

    events = query.order_by(Event.event_date.asc()).all()
    return jsonify({"success": True, "count": len(events), "events": [e.to_dict() for e in events]})


@event_bp.route("/api/events/<int:event_id>", methods=["GET"])
def api_event_detail(event_id: int):
    """Returns individual event JSON details."""
    event = db.session.get(Event, event_id)
    if not event:
        return jsonify({"success": False, "message": "Event not found."}), 404
    return jsonify({"success": True, "event": event.to_dict()})
