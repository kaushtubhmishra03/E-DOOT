import math
from functools import wraps
from datetime import datetime, date
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from models import (
    db,
    User,
    PatientProfile,
    EmergencySummarySettings,
    AccessAuditLog,
    Hospital,
    Doctor,
    Appointment,
    QueueToken,
    VisitNote,
    MedicationReminder,
    AdherenceLog,
)
from core.qr_generator import (
    generate_qr_code_data_url,
    build_emergency_qr_payload,
    format_offline_medical_card,
)
from core.queue_engine import (
    calculate_queue_position,
    estimate_queue_wait_minutes,
    evaluate_leave_now_advisory,
)
from core.ranking import haversine_distance, estimate_travel_time
from core.notifications import notifier

app_routes_bp = Blueprint("app_routes", __name__, url_prefix="/app")


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("Please sign in to access your personal healthcare hub.", "warning")
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated_function


# -------------------------------------------------------------
# 1. PATIENT DASHBOARD & PROFILE
# -------------------------------------------------------------
@app_routes_bp.route("/")
@login_required
def index():
    """Patient personal dashboard."""
    user = db.session.get(User, session["user_id"])
    if not user or not user.patient_profile:
        flash("Profile not found. Please log in again.", "danger")
        return redirect(url_for("auth.login"))

    # Active appointments and queue tokens
    active_token = QueueToken.query.filter(
        QueueToken.patient_id == user.id,
        QueueToken.status.in_(["waiting", "called", "in_consultation"]),
    ).first()

    # Active reminders
    reminders = MedicationReminder.query.filter_by(patient_id=user.id, is_active=True).all()

    # Access audit logs count
    unreviewed_scans = AccessAuditLog.query.filter_by(patient_id=user.id).count()

    return render_template(
        "app/index.html",
        user=user,
        profile=user.patient_profile,
        active_token=active_token,
        reminders=reminders,
        unreviewed_scans=unreviewed_scans,
    )


@app_routes_bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    """View and update patient medical info & emergency privacy toggles."""
    user = db.session.get(User, session["user_id"])
    profile = user.patient_profile
    settings = user.emergency_settings

    if request.method == "POST":
        profile.blood_group = request.form.get("blood_group", "").strip().upper()
        profile.age = int(request.form.get("age")) if request.form.get("age") else None
        profile.gender = request.form.get("gender", "Unspecified")
        profile.address = request.form.get("address", "").strip()
        profile.allergies = request.form.get("allergies", "").strip()
        profile.chronic_conditions = request.form.get("chronic_conditions", "").strip()
        profile.current_medications = request.form.get("current_medications", "").strip()
        profile.emergency_contact_name = request.form.get("emergency_contact_name", "").strip()
        profile.emergency_contact_phone = request.form.get("emergency_contact_phone", "").strip()
        profile.emergency_contact_relation = request.form.get("emergency_contact_relation", "Family").strip()

        # Update privacy settings toggles
        settings.show_full_name = "show_full_name" in request.form
        settings.show_blood_group = "show_blood_group" in request.form
        settings.show_allergies = "show_allergies" in request.form
        settings.show_conditions = "show_conditions" in request.form
        settings.show_medications = "show_medications" in request.form
        settings.show_emergency_contact = "show_emergency_contact" in request.form
        settings.show_address = "show_address" in request.form

        db.session.commit()
        flash("Medical profile and emergency privacy settings updated successfully!", "success")
        return redirect(url_for("app_routes.profile"))

    return render_template("app/profile.html", user=user, profile=profile, settings=settings)


@app_routes_bp.route("/qr")
@login_required
def qr_card():
    """Generate and display user's Emergency QR code and physical ID card preview."""
    user = db.session.get(User, session["user_id"])
    profile = user.patient_profile
    settings = user.emergency_settings

    base_url = request.host_url.rstrip("/")
    emergency_url = build_emergency_qr_payload(base_url, profile.qr_uuid)
    qr_data_url = generate_qr_code_data_url(emergency_url, box_size=8, border=2)

    offline_text = format_offline_medical_card(
        full_name=user.full_name if settings.show_full_name else "Protected Patient",
        blood_group=profile.blood_group if settings.show_blood_group else "Protected",
        allergies=profile.allergies if settings.show_allergies else "Protected",
        conditions=profile.chronic_conditions if settings.show_conditions else "Protected",
        emergency_contact=f"{profile.emergency_contact_name} ({profile.emergency_contact_phone})" if settings.show_emergency_contact else "Protected",
        web_url=emergency_url,
    )

    return render_template(
        "app/qr_card.html",
        user=user,
        profile=profile,
        emergency_url=emergency_url,
        qr_data_url=qr_data_url,
        offline_text=offline_text,
    )


@app_routes_bp.route("/lockscreen")
@login_required
def lockscreen_preview():
    """Simulated phone lockscreen wallpaper featuring the Emergency QR card."""
    user = db.session.get(User, session["user_id"])
    profile = user.patient_profile
    base_url = request.host_url.rstrip("/")
    emergency_url = build_emergency_qr_payload(base_url, profile.qr_uuid)
    qr_data_url = generate_qr_code_data_url(emergency_url, box_size=6, border=1)

    return render_template(
        "app/lockscreen_qr.html",
        user=user,
        profile=profile,
        emergency_url=emergency_url,
        qr_data_url=qr_data_url,
    )


@app_routes_bp.route("/audit-log")
@login_required
def audit_log():
    """View immutable access logs of who viewed the patient's emergency card."""
    user = db.session.get(User, session["user_id"])
    logs = AccessAuditLog.query.filter_by(patient_id=user.id).order_by(AccessAuditLog.accessed_at.desc()).all()
    return render_template("app/audit_log.html", user=user, logs=logs)


# -------------------------------------------------------------
# 2. DOCTOR SEARCH & APPOINTMENT BOOKING
# -------------------------------------------------------------
@app_routes_bp.route("/appointments")
@login_required
def appointments_index():
    """View upcoming and past appointments, and find doctors."""
    user = db.session.get(User, session["user_id"])
    doctors = Doctor.query.filter_by(is_on_duty=True).all()
    hospitals = Hospital.query.all()
    my_appointments = (
        Appointment.query.filter_by(patient_id=user.id)
        .order_by(Appointment.scheduled_date.desc(), Appointment.created_at.desc())
        .all()
    )

    return render_template(
        "app/appointments.html",
        user=user,
        doctors=doctors,
        hospitals=hospitals,
        appointments=my_appointments,
    )


@app_routes_bp.route("/appointments/book", methods=["GET", "POST"])
@login_required
def book_appointment():
    """Book outpatient consultation and receive live queue token."""
    user = db.session.get(User, session["user_id"])
    doctors = Doctor.query.filter_by(is_on_duty=True).all()

    if request.method == "POST":
        doctor_id = int(request.form.get("doctor_id"))
        doctor = db.session.get(Doctor, doctor_id)
        if not doctor:
            flash("Selected physician not found.", "danger")
            return redirect(url_for("app_routes.appointments_index"))

        date_str = request.form.get("scheduled_date")
        sched_date = datetime.strptime(date_str, "%Y-%m-%d").date() if date_str else date.today()
        sched_slot = request.form.get("scheduled_slot", "10:00 AM")
        symptoms = request.form.get("symptoms", "").strip()

        # Create appointment record
        appt = Appointment(
            patient_id=user.id,
            doctor_id=doctor.id,
            hospital_id=doctor.hospital_id,
            scheduled_date=sched_date,
            scheduled_slot=sched_slot,
            symptoms=symptoms,
            status="in_queue",
        )
        db.session.add(appt)
        db.session.flush()

        # Determine next token number for this doctor on this day
        latest_token = (
            QueueToken.query.filter_by(doctor_id=doctor.id)
            .order_by(QueueToken.token_number.desc())
            .first()
        )
        next_token_num = (latest_token.token_number + 1) if latest_token else (doctor.current_token_number + 1)

        token = QueueToken(
            appointment_id=appt.id,
            hospital_id=doctor.hospital_id,
            doctor_id=doctor.id,
            patient_id=user.id,
            token_number=next_token_num,
            status="waiting",
        )
        db.session.add(token)
        db.session.commit()

        flash(f"Appointment confirmed with {doctor.name}! Your live queue token is #{token.token_number}.", "success")
        return redirect(url_for("app_routes.live_queue"))

    return render_template("app/appointment_book.html", user=user, doctors=doctors)


# -------------------------------------------------------------
# 3. LIVE QUEUE TRACKER & "LEAVE NOW" ADVISORY
# -------------------------------------------------------------
@app_routes_bp.route("/queue")
@login_required
def live_queue():
    """
    Live Outpatient Queue Tracker.
    Displays Token #, People Ahead, Estimated Wait Time, and distance-aware 'Leave Now' alert.
    """
    user = db.session.get(User, session["user_id"])
    active_token = QueueToken.query.filter(
        QueueToken.patient_id == user.id,
        QueueToken.status.in_(["waiting", "called", "in_consultation"]),
    ).first()

    if not active_token:
        return render_template("app/live_queue_empty.html", user=user)

    doctor = active_token.doctor
    hospital = active_token.hospital

    # All waiting tokens for this doctor
    all_doctor_tokens = (
        QueueToken.query.filter_by(doctor_id=doctor.id)
        .order_by(QueueToken.token_number.asc())
        .all()
    )

    people_ahead = calculate_queue_position(
        tokens=all_doctor_tokens,
        current_token_number=doctor.current_token_number,
        target_token_number=active_token.token_number,
    )

    predicted_wait_mins = estimate_queue_wait_minutes(
        people_ahead=people_ahead,
        avg_consultation_minutes=hospital.avg_consultation_time,
    )

    # Simulated patient location (default ~6 km from hospital -> approx 14 mins transit)
    patient_lat = 28.5800
    patient_lng = 77.2200
    dist_km = haversine_distance(patient_lat, patient_lng, hospital.latitude, hospital.longitude)
    travel_time_mins = int(round(estimate_travel_time(dist_km)))

    leave_now_advisory = evaluate_leave_now_advisory(
        predicted_wait_mins=predicted_wait_mins,
        travel_time_mins=travel_time_mins,
        buffer_mins=10,
    )

    return render_template(
        "app/live_queue.html",
        user=user,
        token=active_token,
        doctor=doctor,
        hospital=hospital,
        people_ahead=people_ahead,
        predicted_wait_mins=predicted_wait_mins,
        travel_time_mins=travel_time_mins,
        dist_km=dist_km,
        advisory=leave_now_advisory,
    )


# -------------------------------------------------------------
# 4. VISIT HISTORY & PRESCRIPTION TIMELINE
# -------------------------------------------------------------
@app_routes_bp.route("/history")
@login_required
def visit_history():
    """Chronological timeline of past consultations, doctor notes, and prescriptions."""
    user = db.session.get(User, session["user_id"])
    visit_notes = (
        VisitNote.query.filter_by(patient_id=user.id)
        .order_by(VisitNote.created_at.desc())
        .all()
    )

    return render_template(
        "app/visit_history.html",
        user=user,
        visit_notes=visit_notes,
    )


# -------------------------------------------------------------
# 5. DAILY MEDICATION & THERAPY REMINDERS
# -------------------------------------------------------------
@app_routes_bp.route("/reminders")
@login_required
def reminders():
    """Daily medication and therapy regimen adherence checklist."""
    user = db.session.get(User, session["user_id"])
    active_reminders = MedicationReminder.query.filter_by(patient_id=user.id, is_active=True).all()
    
    # Recent adherence logs for today
    today_logs = AdherenceLog.query.join(MedicationReminder).filter(
        MedicationReminder.patient_id == user.id,
        AdherenceLog.scheduled_date == date.today(),
    ).all()
    logged_map = {log.reminder_id: log.status for log in today_logs}

    return render_template(
        "app/reminders.html",
        user=user,
        reminders=active_reminders,
        logged_map=logged_map,
    )


@app_routes_bp.route("/reminders/<int:reminder_id>/log", methods=["POST"])
@login_required
def log_reminder(reminder_id):
    """
    Log Taken / Missed for a medication dose.
    If missed 3+ times in a row, automatically dispatches family SMS alert!
    """
    user = db.session.get(User, session["user_id"])
    reminder = db.session.get(MedicationReminder, reminder_id)
    if not reminder or reminder.patient_id != user.id:
        return jsonify({"status": "error", "message": "Reminder not found"}), 404

    action = request.form.get("action", "taken")  # 'taken' or 'missed'

    # Create log entry
    log_entry = AdherenceLog(
        reminder_id=reminder.id,
        scheduled_date=date.today(),
        time_slot=reminder.time_slot,
        status=action,
        logged_at=datetime.utcnow(),
    )
    db.session.add(log_entry)

    family_notified = False
    if action == "taken":
        reminder.consecutive_missed = 0
        flash(f"Dose logged: {reminder.medicine_name} taken!", "success")
    elif action == "missed":
        reminder.consecutive_missed += 1
        flash(f"Dose missed for {reminder.medicine_name}.", "warning")

        # Family Alert Trigger on 3+ consecutive missed doses
        if reminder.consecutive_missed >= 3:
            profile = user.patient_profile
            if profile and profile.emergency_contact_phone:
                notifier.send_adherence_missed_dose_alert(
                    to_phone=profile.emergency_contact_phone,
                    patient_name=user.full_name,
                    medicine_name=reminder.medicine_name,
                    missed_count=reminder.consecutive_missed,
                )
                family_notified = True
                flash(
                    f"⚠️ {reminder.consecutive_missed} consecutive doses missed! An alert SMS was dispatched to family contact ({profile.emergency_contact_phone}).",
                    "danger",
                )

    db.session.commit()
    return redirect(url_for("app_routes.reminders"))


@app_routes_bp.route("/reminders/add", methods=["POST"])
@login_required
def add_custom_reminder():
    """Patient adds a custom medicine/exercise reminder."""
    user = db.session.get(User, session["user_id"])
    med_name = request.form.get("medicine_name", "").strip()
    dosage = request.form.get("dosage", "1 tablet").strip()
    freq = request.form.get("frequency", "Daily").strip()
    time_slot = request.form.get("time_slot", "Morning").strip()
    instructions = request.form.get("instructions", "After meals").strip()

    if med_name:
        new_rem = MedicationReminder(
            patient_id=user.id,
            medicine_name=med_name,
            dosage=dosage,
            frequency=freq,
            time_slot=time_slot,
            instructions=instructions,
            is_active=True,
        )
        db.session.add(new_rem)
        db.session.commit()
        flash(f"New reminder for {med_name} scheduled!", "success")

    return redirect(url_for("app_routes.reminders"))
