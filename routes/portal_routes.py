import json
from datetime import datetime, date
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from models import (
    db,
    User,
    Hospital,
    WardBed,
    Facility,
    Doctor,
    EmergencyEvent,
    Appointment,
    QueueToken,
    VisitNote,
    MedicationReminder,
)
from core.queue_engine import (
    calculate_queue_position,
    estimate_queue_wait_minutes,
    update_doctor_average_consultation,
)

portal_bp = Blueprint("portal", __name__, url_prefix="/portal")


def get_current_portal_context():
    """Helper to retrieve active logged-in doctor or admin, or default mock staff for demo."""
    user = None
    if "user_id" in session:
        user = db.session.get(User, session["user_id"])

    doctor = None
    hospital = None

    if user and user.role == "doctor":
        doctor = Doctor.query.filter_by(user_id=user.id).first()
        if doctor:
            hospital = doctor.hospital
    elif user and user.role == "admin":
        # Link admin to first hospital or user-associated hospital
        hospital = Hospital.query.filter(Hospital.slug.in_([user.app_id.replace("admin_", ""), "aiims-delhi"])).first()

    # Fallbacks for seamless hackathon judge demo
    if not doctor:
        doctor = Doctor.query.first()
    if not hospital:
        hospital = doctor.hospital if doctor else Hospital.query.first()

    return user, doctor, hospital


@portal_bp.route("/")
def dashboard():
    """Main landing portal redirecting to active context."""
    user, doctor, hospital = get_current_portal_context()
    hospitals = Hospital.query.all()
    recent_events = EmergencyEvent.query.order_by(EmergencyEvent.created_at.desc()).limit(10).all()
    active_tokens = QueueToken.query.filter_by(status="waiting").count()

    return render_template(
        "portal/dashboard.html",
        user=user,
        doctor=doctor,
        hospital=hospital,
        hospitals=hospitals,
        recent_events=recent_events,
        active_tokens=active_tokens,
    )


# -------------------------------------------------------------
# 1. EMERGENCY DEPARTMENT (ED) PRE-ALERT LIVE BOARD
# -------------------------------------------------------------
@portal_bp.route("/doctor/er")
def doctor_er_board():
    """
    Emergency Room incoming pre-alert command board.
    Shows incoming ambulances with live ETA countdown, triage category, and photo.
    """
    user, doctor, hospital = get_current_portal_context()
    
    # Active pre-alerts: status in ['initiated', 'triage_completed', 'pre_alert_sent', 'accepted']
    active_pre_alerts = (
        EmergencyEvent.query.filter(
            EmergencyEvent.status.in_(["pre_alert_sent", "accepted", "triage_completed"])
        )
        .order_by(EmergencyEvent.created_at.desc())
        .all()
    )

    return render_template(
        "portal/doctor_er.html",
        user=user,
        doctor=doctor,
        hospital=hospital,
        pre_alerts=active_pre_alerts,
    )


@portal_bp.route("/doctor/er/<int:event_id>/action", methods=["POST"])
def er_pre_alert_action(event_id):
    """Accept incoming emergency pre-alert or redirect."""
    event = db.session.get(EmergencyEvent, event_id)
    if not event:
        flash("Emergency event not found.", "danger")
        return redirect(url_for("portal.doctor_er_board"))

    action = request.form.get("action", "accept")
    reason = request.form.get("reason", "").strip()

    if action == "accept":
        event.status = "accepted"
        flash(f"Pre-Alert Accepted! Critical care team notified and bed prepared for {event.patient.full_name if event.patient else 'Patient'}.", "success")
    elif action == "redirect":
        event.status = "redirected"
        event.cancellation_reason = reason or "Redirected by ED Doctor to specialized burn/trauma center"
        # Release held bed
        if event.selected_hospital_id:
            bed = WardBed.query.filter_by(hospital_id=event.selected_hospital_id, ward_type="ICU").first()
            if bed and bed.reserved_beds > 0:
                bed.reserved_beds -= 1
        flash(f"Patient redirected: {event.cancellation_reason}", "warning")

    event.updated_at = datetime.utcnow()
    db.session.commit()
    return redirect(url_for("portal.doctor_er_board"))


# -------------------------------------------------------------
# 2. OUTPATIENT CLINIC QUEUE CONTROLLER & PRESCRIPTIONS
# -------------------------------------------------------------
@portal_bp.route("/doctor/clinic")
def doctor_clinic():
    """
    Doctor's outpatient consultation queue with Call Next, Mark Done,
    and digital prescription notes creator.
    """
    user, doctor, hospital = get_current_portal_context()
    
    # Doctor's queue tokens
    tokens = (
        QueueToken.query.filter_by(doctor_id=doctor.id)
        .order_by(QueueToken.token_number.asc())
        .all()
    )

    current_consultation = next((t for t in tokens if t.status in ["called", "in_consultation"]), None)
    waiting_tokens = [t for t in tokens if t.status == "waiting"]
    completed_tokens = [t for t in tokens if t.status == "done"]

    return render_template(
        "portal/doctor_clinic.html",
        user=user,
        doctor=doctor,
        hospital=hospital,
        tokens=tokens,
        current_consultation=current_consultation,
        waiting_tokens=waiting_tokens,
        completed_tokens=completed_tokens,
    )


@portal_bp.route("/doctor/clinic/call-next", methods=["POST"])
def doctor_call_next():
    """Calls next patient in queue, updating current_token_number."""
    user, doctor, hospital = get_current_portal_context()

    # Find first waiting token
    next_token = (
        QueueToken.query.filter_by(doctor_id=doctor.id, status="waiting")
        .order_by(QueueToken.token_number.asc())
        .first()
    )

    if next_token:
        next_token.status = "in_consultation"
        next_token.consultation_start_time = datetime.utcnow()
        doctor.current_token_number = next_token.token_number
        db.session.commit()
        flash(f"Now Calling Token #{next_token.token_number}: {next_token.patient.full_name}", "success")
    else:
        flash("No waiting patients in queue.", "info")

    return redirect(url_for("portal.doctor_clinic"))


@portal_bp.route("/doctor/clinic/mark-done/<int:token_id>", methods=["POST"])
def doctor_mark_done(token_id):
    """
    Marks patient consultation complete, saves visit notes & prescription,
    recalculates doctor's average consultation duration, and auto-generates patient reminders.
    """
    token = db.session.get(QueueToken, token_id)
    if not token:
        flash("Token not found.", "danger")
        return redirect(url_for("portal.doctor_clinic"))

    doctor = token.doctor
    token.status = "done"
    token.consultation_end_time = datetime.utcnow()

    # Calculate actual consultation duration
    duration_mins = 12.0
    if token.consultation_start_time:
        delta = (token.consultation_end_time - token.consultation_start_time).total_seconds() / 60.0
        duration_mins = max(3.0, delta)

    # Recalculate dynamic average consultation time
    completed_count = QueueToken.query.filter_by(doctor_id=doctor.id, status="done").count()
    new_avg = update_doctor_average_consultation(
        current_avg=doctor.hospital.avg_consultation_time,
        completed_consultations_count=completed_count,
        actual_duration_minutes=duration_mins,
    )
    doctor.hospital.avg_consultation_time = new_avg

    # Save Visit Note & Digital Prescription
    diagnosis = request.form.get("diagnosis", "General Checkup").strip()
    clinical_notes = request.form.get("clinical_notes", "").strip()
    next_date_str = request.form.get("next_checkup_date")
    next_date = datetime.strptime(next_date_str, "%Y-%m-%d").date() if next_date_str else None

    visit_note = VisitNote(
        appointment_id=token.appointment_id,
        doctor_id=doctor.id,
        patient_id=token.patient_id,
        diagnosis=diagnosis,
        clinical_notes=clinical_notes,
        next_checkup_date=next_date,
    )
    db.session.add(visit_note)
    db.session.flush()

    # Auto-create Medication Reminder if prescribed
    med_name = request.form.get("med_name", "").strip()
    if med_name:
        med_dose = request.form.get("med_dose", "1 tablet").strip()
        med_freq = request.form.get("med_freq", "Daily").strip()
        med_slot = request.form.get("med_slot", "Morning").strip()
        med_instr = request.form.get("med_instr", "After meal").strip()

        reminder = MedicationReminder(
            patient_id=token.patient_id,
            visit_note_id=visit_note.id,
            medicine_name=med_name,
            dosage=med_dose,
            frequency=med_freq,
            time_slot=med_slot,
            instructions=med_instr,
            is_active=True,
        )
        db.session.add(reminder)

    db.session.commit()
    flash(f"Consultation complete for Token #{token.token_number}! Average OPD consultation updated to {new_avg} mins.", "success")
    return redirect(url_for("portal.doctor_clinic"))


# -------------------------------------------------------------
# 3. ADMIN COMMAND CENTER (BED MANAGEMENT & CROWD CONTROLLER)
# -------------------------------------------------------------
@portal_bp.route("/admin/beds")
def admin_bed_management():
    """
    Real-time Bed Management & Crowd Controller.
    KEY HACKATHON DEMO: Adjusting beds or crowd here alters hospital rankings live!
    """
    user, doctor, hospital = get_current_portal_context()
    all_hospitals = Hospital.query.all()

    return render_template(
        "portal/admin_beds.html",
        user=user,
        hospital=hospital,
        all_hospitals=all_hospitals,
    )


@portal_bp.route("/admin/analytics")
def admin_analytics():
    """Hospital operational analytics and emergency volume dashboard."""
    user, doctor, hospital = get_current_portal_context()
    
    total_emergencies = EmergencyEvent.query.count()
    cardiac_emergencies = EmergencyEvent.query.filter_by(triage_category="Cardiac").count()
    trauma_emergencies = EmergencyEvent.query.filter_by(triage_category="Trauma").count()
    completed_consultations = QueueToken.query.filter_by(status="done").count()
    waiting_tokens = QueueToken.query.filter_by(status="waiting").count()

    return render_template(
        "portal/admin_analytics.html",
        user=user,
        hospital=hospital,
        total_emergencies=total_emergencies,
        cardiac_emergencies=cardiac_emergencies,
        trauma_emergencies=trauma_emergencies,
        completed_consultations=completed_consultations,
        waiting_tokens=waiting_tokens,
    )
