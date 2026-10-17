from functools import wraps
from flask import session, redirect, url_for, flash, jsonify, request
from models import db
from models.user import User
from models.admin import Admin


def login_required(f):
    """Decorator to enforce regular user authentication."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("user_id"):
            if request.is_json or request.path.startswith("/api/"):
                return jsonify({"success": False, "message": "Authentication required. Please log in."}), 401
            flash("Please log in to continue.", "warning")
            return redirect(url_for("auth.login", next=request.url))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """Decorator to enforce admin authentication."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("admin_id"):
            if request.is_json or request.path.startswith("/api/"):
                return jsonify({"success": False, "message": "Admin authorization required."}), 403
            flash("Admin login required.", "danger")
            return redirect(url_for("admin.admin_login", next=request.url))
        return f(*args, **kwargs)
    return decorated_function


def set_user_session(user: User):
    """Stores user information in session."""
    session.permanent = True
    session["user_id"] = user.id
    session["user_email"] = user.email
    session["user_name"] = user.full_name


def clear_user_session():
    """Clears user-specific session data."""
    session.pop("user_id", None)
    session.pop("user_email", None)
    session.pop("user_name", None)


def set_admin_session(admin: Admin):
    """Stores admin information in session."""
    session.permanent = True
    session["admin_id"] = admin.id
    session["admin_email"] = admin.email


def clear_admin_session():
    """Clears admin-specific session data."""
    session.pop("admin_id", None)
    session.pop("admin_email", None)


def get_current_user():
    """Retrieves current logged-in user instance or None."""
    user_id = session.get("user_id")
    if user_id:
        return db.session.get(User, user_id)
    return None


def get_current_admin():
    """Retrieves current logged-in admin instance or None."""
    admin_id = session.get("admin_id")
    if admin_id:
        return db.session.get(Admin, admin_id)
    return None
