import os
from datetime import datetime, date, timedelta
from pathlib import Path
from flask import Flask, render_template, session, jsonify
from config import Config, config_by_name
from models import db, User, Admin, Event, Seat
from services.email_service import mail
from services.seat_generator_service import generate_seats_for_event
from utils.security import get_current_user, get_current_admin


def create_app(config_name: str = "default") -> Flask:
    """Application factory for ShowSpot Event Ticket Booking Platform."""
    app = Flask(__name__)
    app.config.from_object(config_by_name.get(config_name, Config))

    # Ensure required directories exist
    Config.QR_FOLDER.mkdir(parents=True, exist_ok=True)
    Config.EXPORT_FOLDER.mkdir(parents=True, exist_ok=True)
    Config.IMAGE_FOLDER.mkdir(parents=True, exist_ok=True)

    # Initialize extensions
    db.init_app(app)
    mail.init_app(app)

    # Register Blueprints
    from routes.auth_routes import auth_bp
    from routes.event_routes import event_bp
    from routes.seat_routes import seat_bp
    from routes.booking_routes import booking_bp
    from routes.payment_routes import payment_bp
    from routes.ticket_routes import ticket_bp
    from routes.admin_routes import admin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(event_bp)
    app.register_blueprint(seat_bp)
    app.register_blueprint(booking_bp)
    app.register_blueprint(payment_bp)
    app.register_blueprint(ticket_bp)
    app.register_blueprint(admin_bp)

    # Context processors for templates
    @app.context_processor
    def inject_globals():
        return {
            "current_user": get_current_user(),
            "current_admin": get_current_admin(),
            "now_year": date.today().year,
            "today_date": date.today(),
        }

    # Error handlers
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template("base.html", error_title="404 - Page Not Found", error_message="The page or resource you are looking for does not exist."), 404

    @app.errorhandler(403)
    def forbidden_error(error):
        return render_template("base.html", error_title="403 - Access Forbidden", error_message="You do not have permission to view this resource."), 403

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template("base.html", error_title="500 - Internal Server Error", error_message="An unexpected server error occurred. Please try again shortly."), 500

    return app


def initialize_database_and_seed(app: Flask):
    """Initializes database tables and provisions initial seed data if empty."""
    with app.app_context():
        db.create_all()

        # 1. Ensure Default Admin exists
        admin = Admin.query.filter_by(email=Config.ADMIN_EMAIL.lower()).first()
        if not admin:
            admin = Admin(email=Config.ADMIN_EMAIL, is_active=True)
            admin.set_password(Config.ADMIN_PASSWORD)
            db.session.add(admin)
            db.session.commit()
            print(f"[INIT] Created default admin account: {Config.ADMIN_EMAIL}")

        # 2. Check and Seed Sample Events
        if Event.query.count() == 0:
            sample_events = [
                Event(
                    name="IPL Grand Final: Chennai Super Kings vs Mumbai Indians",
                    description="Witness high-voltage cricket action as the two legendary rivals battle for the coveted championship trophy under blazing floodlights at Chepauk!",
                    event_type="Cricket",
                    banner_image="/static/images/event_cricket.jpg",
                    venue="MA Chidambaram Stadium (Chepauk)",
                    city="Chennai",
                    event_date=date.today() + timedelta(days=2),
                    event_time=datetime.strptime("19:30", "%H:%M").time(),
                    total_seats=2500,
                    status="ACTIVE",
                ),
                Event(
                    name="India vs Australia - T20 International Series Decider",
                    description="Experience world-class international cricket drama as Team India takes on the Aussies in a thrilling high-stakes blockbuster clash.",
                    event_type="Cricket",
                    banner_image="/static/images/event_cricket.jpg",
                    venue="Wankhede Stadium",
                    city="Mumbai",
                    event_date=date.today() + timedelta(days=5),
                    event_time=datetime.strptime("19:00", "%H:%M").time(),
                    total_seats=2500,
                    status="ACTIVE",
                ),
                Event(
                    name="A.R. Rahman Live in Concert - Symphony of Lights",
                    description="An enchanting evening of timeless melodies, electrifying stage performances, and iconic musical scores with live orchestra.",
                    event_type="Concert",
                    banner_image="/static/images/event_concert.jpg",
                    venue="YMCA Grounds",
                    city="Bengaluru",
                    event_date=date.today() + timedelta(days=8),
                    event_time=datetime.strptime("19:00", "%H:%M").time(),
                    total_seats=1050,
                    status="ACTIVE",
                ),
                Event(
                    name="Standup Comedy Night with Zakir & Friends",
                    description="Get ready for non-stop laughter, relatable jokes, and witty storytelling with India's finest stand-up comedians.",
                    event_type="General",
                    banner_image="/static/images/event_comedy.jpg",
                    venue="Music Academy Hall",
                    city="Mumbai",
                    event_date=date.today() + timedelta(days=3),
                    event_time=datetime.strptime("20:00", "%H:%M").time(),
                    total_seats=200,
                    status="ACTIVE",
                ),
            ]

            for ev in sample_events:
                db.session.add(ev)
            db.session.commit()

            # Provision seating for each sample event
            for ev in Event.query.all():
                if ev.seats.count() == 0:
                    generate_seats_for_event(ev, custom_price=800.0 if ev.event_type == "General" else 500.0, custom_capacity=ev.total_seats)

            print("[INIT] Successfully seeded 4 standard sample events with full seat maps.")


app = create_app(os.getenv("FLASK_ENV", "default"))

if __name__ == "__main__":
    initialize_database_and_seed(app)
    print("=========================================================")
    print("ShowSpot Event Ticket Booking Platform running at:")
    print("User Portal:  http://127.0.0.1:5000")
    print(f"Admin Portal: http://127.0.0.1:5000/admin/login ({Config.ADMIN_EMAIL})")
    print("=========================================================")
    app.run(host="127.0.0.1", port=5000, debug=True)
