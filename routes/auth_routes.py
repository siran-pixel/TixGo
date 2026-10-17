from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from models import db, User
from config import Config
from utils.security import set_user_session, clear_user_session, get_current_user
from utils.validators import validate_email, validate_password, validate_phone

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/signup", methods=["GET", "POST"])
def signup():
    """Direct user registration without OTP verification."""
    if session.get("user_id"):
        return redirect(url_for("events.landing_page"))

    if request.method == "POST":
        data = request.get_json() if request.is_json else request.form
        full_name = data.get("full_name", "").strip()
        email = data.get("email", "").strip().lower()
        password = data.get("password", "")
        confirm_password = data.get("confirm_password", "")
        phone = data.get("phone", "").strip()

        # Validation
        if not full_name or len(full_name) < 2:
            msg = "Please enter your full name (minimum 2 characters)."
            if request.is_json:
                return jsonify({"success": False, "message": msg}), 400
            flash(msg, "danger")
            return render_template("signup.html"), 400

        if not validate_email(email):
            msg = "Please enter a valid email address."
            if request.is_json:
                return jsonify({"success": False, "message": msg}), 400
            flash(msg, "danger")
            return render_template("signup.html"), 400

        is_pw_valid, pw_err = validate_password(password)
        if not is_pw_valid:
            if request.is_json:
                return jsonify({"success": False, "message": pw_err}), 400
            flash(pw_err, "danger")
            return render_template("signup.html"), 400

        if password != confirm_password:
            msg = "Passwords do not match."
            if request.is_json:
                return jsonify({"success": False, "message": msg}), 400
            flash(msg, "danger")
            return render_template("signup.html"), 400

        if not validate_phone(phone):
            msg = "Please enter a valid 10-15 digit phone number."
            if request.is_json:
                return jsonify({"success": False, "message": msg}), 400
            flash(msg, "danger")
            return render_template("signup.html"), 400

        # Check duplicate email
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            msg = "An account with this email already exists. Please log in."
            if request.is_json:
                return jsonify({"success": False, "message": msg}), 409
            flash(msg, "warning")
            return redirect(url_for("auth.login", email=email))

        # Create verified user directly
        user = User(
            full_name=full_name,
            email=email,
            phone=phone,
            is_verified=True
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        # Automatically log the user in
        set_user_session(user)
        flash(f"Account created successfully! Welcome to ShowSpot, {user.full_name}.", "success")

        if request.is_json:
            return jsonify({
                "success": True,
                "message": "Account created successfully.",
                "redirect_url": url_for("events.landing_page")
            })
        return redirect(url_for("events.landing_page"))

    return render_template("signup.html")


@auth_bp.route("/verify-otp", methods=["GET", "POST"])
def verify_otp():
    """Redirect to home as OTP verification is removed."""
    flash("OTP verification is not required. You can log in directly.", "info")
    return redirect(url_for("events.landing_page"))


@auth_bp.route("/api/auth/resend-otp", methods=["POST"])
def resend_otp():
    """No-op response since OTP verification is disabled."""
    return jsonify({
        "success": True,
        "message": "OTP verification is disabled. You can log in directly."
    })


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """Direct user login view and verification."""
    if session.get("user_id"):
        return redirect(url_for("events.landing_page"))

    if request.method == "POST":
        data = request.get_json() if request.is_json else request.form
        email = data.get("email", "").strip().lower()
        password = data.get("password", "")

        if not email or not password:
            msg = "Please provide both email and password."
            if request.is_json:
                return jsonify({"success": False, "message": msg}), 400
            flash(msg, "danger")
            return render_template("login.html", email=email), 400

        user = User.query.filter_by(email=email).first()
        if not user or not user.check_password(password):
            msg = "Invalid email or password. Please check your credentials."
            if request.is_json:
                return jsonify({"success": False, "message": msg}), 401
            flash(msg, "danger")
            return render_template("login.html", email=email), 401

        # Ensure user is active/verified
        if not user.is_verified:
            user.is_verified = True
            db.session.commit()

        set_user_session(user)
        next_url = request.args.get("next") or url_for("events.landing_page")
        flash(f"Welcome back, {user.full_name}!", "success")

        if request.is_json:
            return jsonify({"success": True, "message": "Login successful.", "redirect_url": next_url})
        return redirect(next_url)

    email_prefill = request.args.get("email", "").strip().lower()
    return render_template("login.html", email=email_prefill)


@auth_bp.route("/logout")
def logout():
    """Logs out regular user."""
    clear_user_session()
    flash("You have been logged out.", "info")
    return redirect(url_for("events.landing_page"))


@auth_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    """Direct password recovery request."""
    if request.method == "POST":
        data = request.get_json() if request.is_json else request.form
        email = data.get("email", "").strip().lower()

        if not email:
            msg = "Please enter your registered email."
            if request.is_json:
                return jsonify({"success": False, "message": msg}), 400
            flash(msg, "danger")
            return render_template("forgot_password.html"), 400

        user = User.query.filter_by(email=email).first()
        if not user:
            msg = "No account found with that email address. Please sign up."
            if request.is_json:
                return jsonify({"success": False, "message": msg}), 404
            flash(msg, "danger")
            return render_template("forgot_password.html", email=email), 404

        session["reset_email"] = email
        flash(f"Account found for {email}. Please enter your new password below.", "info")
        if request.is_json:
            return jsonify({"success": True, "message": "Proceed to password reset.", "redirect_url": url_for("auth.reset_password", email=email)})
        return redirect(url_for("auth.reset_password", email=email))

    return render_template("forgot_password.html")


@auth_bp.route("/reset-password", methods=["GET", "POST"])
def reset_password():
    """Sets new password directly."""
    email = request.args.get("email", "").strip().lower() or session.get("reset_email", "")

    if not email:
        flash("Please enter your email to reset your password.", "warning")
        return redirect(url_for("auth.forgot_password"))

    if request.method == "POST":
        data = request.get_json() if request.is_json else request.form
        new_password = data.get("password", "")
        confirm_password = data.get("confirm_password", "")

        is_pw_valid, pw_err = validate_password(new_password)
        if not is_pw_valid:
            if request.is_json:
                return jsonify({"success": False, "message": pw_err}), 400
            flash(pw_err, "danger")
            return render_template("reset_password.html", email=email), 400

        if new_password != confirm_password:
            msg = "Passwords do not match."
            if request.is_json:
                return jsonify({"success": False, "message": msg}), 400
            flash(msg, "danger")
            return render_template("reset_password.html", email=email), 400

        user = User.query.filter_by(email=email).first()
        if not user:
            flash("User not found.", "danger")
            return redirect(url_for("auth.signup"))

        user.set_password(new_password)
        user.is_verified = True
        db.session.commit()
        session.pop("reset_email", None)

        flash("Password updated successfully! Please log in with your new password.", "success")
        if request.is_json:
            return jsonify({"success": True, "message": "Password updated.", "redirect_url": url_for("auth.login", email=email)})
        return redirect(url_for("auth.login", email=email))

    return render_template("reset_password.html", email=email)
