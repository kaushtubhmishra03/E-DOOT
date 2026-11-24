import re
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from models import db, User, PatientProfile, EmergencySummarySettings

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    """Sign up with Phone number and custom App ID (Zero Aadhaar)."""
    if request.method == "POST":
        phone = request.form.get("phone", "").strip()
        app_id = request.form.get("app_id", "").strip().lower()
        full_name = request.form.get("full_name", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")
        role = request.form.get("role", "patient")

        # Basic validations
        if not phone or not app_id or not full_name or not password:
            flash("All required fields must be completed.", "danger")
            return render_template("auth/register.html", phone=phone, app_id=app_id, full_name=full_name)

        if not re.match(r"^[a-zA-Z0-9_-]{3,30}$", app_id):
            flash("App ID must be 3-30 alphanumeric characters (letters, numbers, hyphens, underscores).", "danger")
            return render_template("auth/register.html", phone=phone, app_id=app_id, full_name=full_name)

        if len(password) < 6:
            flash("Password must be at least 6 characters long.", "danger")
            return render_template("auth/register.html", phone=phone, app_id=app_id, full_name=full_name)

        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return render_template("auth/register.html", phone=phone, app_id=app_id, full_name=full_name)

        # Check existing user
        if User.query.filter_by(phone=phone).first():
            flash("An account with this phone number already exists. Please log in.", "warning")
            return redirect(url_for("auth.login"))

        if User.query.filter_by(app_id=app_id).first():
            flash("This App ID is already taken. Please choose another unique ID.", "warning")
            return render_template("auth/register.html", phone=phone, app_id="", full_name=full_name)

        # Create user
        new_user = User(
            phone=phone,
            app_id=app_id,
            full_name=full_name,
            role=role if role in ["patient", "doctor", "admin"] else "patient",
        )
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.flush()

        # If patient, create profile and default privacy settings
        if new_user.role == "patient":
            profile = PatientProfile(user_id=new_user.id)
            settings = EmergencySummarySettings(user_id=new_user.id)
            db.session.add(profile)
            db.session.add(settings)

        db.session.commit()

        # Auto-login
        session["user_id"] = new_user.id
        session["user_role"] = new_user.role
        session["user_name"] = new_user.full_name
        session["app_id"] = new_user.app_id

        flash(f"Welcome to E-Doot, {new_user.full_name}! Please configure your emergency profile.", "success")
        return redirect(url_for("app_routes.profile") if new_user.role == "patient" else url_for("portal.dashboard"))

    return render_template("auth/register.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """Log in via Phone Number or App ID."""
    if request.method == "POST":
        identifier = request.form.get("identifier", "").strip().lower()
        password = request.form.get("password", "")

        user = User.query.filter((User.phone == identifier) | (User.app_id == identifier)).first()
        if user and user.check_password(password):
            session["user_id"] = user.id
            session["user_role"] = user.role
            session["user_name"] = user.full_name
            session["app_id"] = user.app_id

            flash(f"Welcome back, {user.full_name}!", "success")
            if user.role in ["doctor", "admin"]:
                return redirect(url_for("portal.dashboard"))
            return redirect(url_for("app_routes.index"))
        else:
            flash("Invalid credentials. Please verify your phone/App ID and password.", "danger")

    return render_template("auth/login.html")


@auth_bp.route("/logout")
def logout():
    """Clear session and log user out."""
    session.clear()
    flash("You have been signed out safely.", "info")
    return redirect(url_for("main.index"))
