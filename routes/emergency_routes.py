import os
import uuid
import json
from datetime import datetime
from werkzeug.utils import secure_filename
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, current_app
from models import (
    db,
    User,
    PatientProfile,
    EmergencySummarySettings,
    AccessAuditLog,
    Hospital,
    WardBed,
    EmergencyEvent,
)
from core.triage import evaluate_triage, get_first_aid_guidance, TRIAGE_QUESTIONS
from core.ranking import rank_hospitals_for_emergency
from core.notifications import notifier

emergency_bp = Blueprint("emergency_bp", __name__, url_prefix="/app/emergency")

UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@emergency_bp.route("/<qr_uuid>")
def view_emergency_summary(qr_uuid):
    """
    Public, unauthenticated emergency view for first responders and Good Samaritan helpers.
    Zero login friction. Displays only what the patient has authorized.
    Logs every access for privacy audits.
    """
    profile = PatientProfile.query.filter_by(qr_uuid=qr_uuid).first()
    if not profile:
        return render_template("app/emergency_not_found.html", qr_uuid=qr_uuid)

    user = profile.user
    settings = user.emergency_settings or EmergencySummarySettings(user_id=user.id)

    # Immutable access logging
    try:
        audit_entry = AccessAuditLog(
            patient_id=user.id,
            ip_address=request.headers.get("X-Forwarded-For", request.remote_addr or "127.0.0.1"),
            user_agent=request.headers.get("User-Agent", "Unknown Browser")[:250],
            access_type="emergency_qr_scan",
            accessed_at=datetime.utcnow(),
        )
        db.session.add(audit_entry)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"[Audit Log Error] Failed to record access log: {e}")

    summary = {
        "full_name": user.full_name if settings.show_full_name else "Verified Citizen",
        "blood_group": profile.blood_group if settings.show_blood_group else "Protected",
        "allergies": profile.allergies if settings.show_allergies else "Protected",
        "chronic_conditions": profile.chronic_conditions if settings.show_conditions else "Protected",
        "current_medications": profile.current_medications if settings.show_medications else "Protected",
        "emergency_contact_name": profile.emergency_contact_name if settings.show_emergency_contact else None,
        "emergency_contact_phone": profile.emergency_contact_phone if settings.show_emergency_contact else None,
        "emergency_contact_relation": profile.emergency_contact_relation if settings.show_emergency_contact else "Family",
        "address": profile.address if settings.show_address else None,
    }

    return render_template(
        "app/emergency_view.html",
        patient=user,
        profile=profile,
        summary=summary,
        qr_uuid=qr_uuid,
        settings=settings,
    )


@emergency_bp.route("/<qr_uuid>/log-location", methods=["POST"])
def log_helper_location(qr_uuid):
    """Optionally records helper's GPS coordinates into the latest access audit log."""
    data = request.get_json(silent=True) or {}
    lat = data.get("lat")
    lng = data.get("lng")

    profile = PatientProfile.query.filter_by(qr_uuid=qr_uuid).first()
    if profile and lat and lng:
        latest_log = (
            AccessAuditLog.query.filter_by(patient_id=profile.user_id)
            .order_by(AccessAuditLog.accessed_at.desc())
            .first()
        )
        if latest_log:
            latest_log.location_lat = float(lat)
            latest_log.location_lng = float(lng)
            db.session.commit()
            return jsonify({"status": "success", "message": "Location logged"})

    return jsonify({"status": "ignored"}), 200


@emergency_bp.route("/<qr_uuid>/sos", methods=["GET"])
def sos_triage_wizard(qr_uuid):
    """
    Interactive Emergency Triage Wizard.
    Guides bystander through 4-6 voice-prompted symptom questions with injury photo upload.
    """
    profile = PatientProfile.query.filter_by(qr_uuid=qr_uuid).first()
    if not profile:
        return render_template("app/emergency_not_found.html", qr_uuid=qr_uuid)

    user = profile.user
    return render_template(
        "app/sos_triage.html",
        qr_uuid=qr_uuid,
        profile=profile,
        patient=user,
        questions=TRIAGE_QUESTIONS,
    )


@emergency_bp.route("/<qr_uuid>/submit-triage", methods=["POST"])
def submit_triage(qr_uuid):
    """
    Processes bystander triage answers and uploaded photo,
    runs rules-based triage evaluation, and creates an EmergencyEvent record.
    """
    profile = PatientProfile.query.filter_by(qr_uuid=qr_uuid).first()
    patient_id = profile.user_id if profile else None

    # Helper GPS coordinates (default to Delhi Central coords for demo if not shared)
    helper_lat = float(request.form.get("helper_lat", 28.5800))
    helper_lng = float(request.form.get("helper_lng", 77.2200))
    helper_phone = request.form.get("helper_phone", "").strip()

    # Gather triage question answers from form
    answers = {}
    for q in TRIAGE_QUESTIONS:
        answers[q["key"]] = request.form.get(q["key"], q["default"])

    # Handle optional photo upload
    photo_filename = None
    if "injury_photo" in request.files:
        file = request.files["injury_photo"]
        if file and file.filename and allowed_file(file.filename):
            ext = file.filename.rsplit(".", 1)[1].lower()
            photo_filename = f"injury_{uuid.uuid4().hex[:10]}.{ext}"
            file.save(os.path.join(UPLOAD_FOLDER, photo_filename))

    # Evaluate deterministic triage
    patient_conditions = profile.chronic_conditions if profile else ""
    triage_result = evaluate_triage(answers, patient_conditions=patient_conditions)

    # Create EmergencyEvent record
    event = EmergencyEvent(
        event_token=uuid.uuid4().hex,
        patient_id=patient_id,
        helper_name="Good Samaritan Bystander",
        helper_phone=helper_phone or "Unshared",
        helper_lat=helper_lat,
        helper_lng=helper_lng,
        triage_category=triage_result["category"],
        triage_answers_json=json.dumps(answers),
        photo_filename=photo_filename,
        status="triage_completed",
    )
    db.session.add(event)
    db.session.commit()

    return redirect(url_for("emergency_bp.hospital_ranking_view", event_token=event.event_token))


@emergency_bp.route("/event/<event_token>/ranking")
def hospital_ranking_view(event_token):
    """
    Ranks hospitals based on:
    Score = 0.5 * travel_time + 0.3 * crowd_penalty + 0.2 * speciality_fit
    Displays top 3 facilities with plain-language rationale, interactive map, and first-aid guide.
    """
    event = EmergencyEvent.query.filter_by(event_token=event_token).first_or_404()
    patient = event.patient
    profile = patient.patient_profile if patient else None

    # Map triage category to required ward bed
    answers = json.loads(event.triage_answers_json or "{}")
    triage_result = evaluate_triage(answers, patient_conditions=profile.chronic_conditions if profile else "")
    required_bed_type = triage_result["required_bed"]

    # Retrieve all active network hospitals
    all_hospitals = Hospital.query.filter_by(is_active=True).all()

    # Helper location (fallback to central Delhi coordinates if unprovided)
    helper_lat = event.helper_lat or 28.5800
    helper_lng = event.helper_lng or 77.2200

    # Calculate ranking
    ranked_hospitals = rank_hospitals_for_emergency(
        hospitals=all_hospitals,
        helper_lat=helper_lat,
        helper_lng=helper_lng,
        category=event.triage_category,
        required_bed_type=required_bed_type,
        limit=3,
    )

    # First aid guidance for Golden Hour panel (Proposal 1)
    first_aid = get_first_aid_guidance(event.triage_category)

    return render_template(
        "app/hospital_ranking.html",
        event=event,
        patient=patient,
        profile=profile,
        triage_result=triage_result,
        ranked_hospitals=ranked_hospitals,
        all_hospitals=all_hospitals,
        first_aid=first_aid,
        helper_lat=helper_lat,
        helper_lng=helper_lng,
    )


@emergency_bp.route("/event/<event_token>/dispatch", methods=["POST"])
def dispatch_hospital(event_token):
    """
    Confirms chosen destination hospital, holds 1 critical bed (Proposal 3),
    dispatches real-time pre-alert to hospital portal, and sends family SMS alert.
    """
    event = EmergencyEvent.query.filter_by(event_token=event_token).first_or_404()
    hospital_id = int(request.form.get("hospital_id"))
    hospital = db.session.get(Hospital, hospital_id)
    if not hospital:
        flash("Selected hospital not found.", "danger")
        return redirect(url_for("emergency_bp.hospital_ranking_view", event_token=event_token))

    eta_minutes = int(request.form.get("eta_minutes", 15))

    # Update event state
    event.selected_hospital_id = hospital.id
    event.eta_minutes = eta_minutes
    event.status = "pre_alert_sent"
    event.updated_at = datetime.utcnow()

    # Bed Hold (Proposal 3): Reserve 1 relevant bed at destination hospital
    answers = json.loads(event.triage_answers_json or "{}")
    triage_result = evaluate_triage(answers)
    bed_type = triage_result["required_bed"]

    bed_record = WardBed.query.filter_by(hospital_id=hospital.id, ward_type=bed_type).first()
    if bed_record and bed_record.available_beds > bed_record.reserved_beds:
        bed_record.reserved_beds += 1

    db.session.commit()

    # Family SMS Notification
    patient = event.patient
    profile = patient.patient_profile if patient else None
    if profile and profile.emergency_contact_phone:
        base_url = request.host_url.rstrip("/")
        live_location_url = f"{base_url}/app/emergency/event/{event.event_token}/tracking"
        notifier.send_emergency_sms(
            to_phone=profile.emergency_contact_phone,
            patient_name=patient.full_name,
            hospital_name=hospital.name,
            helper_phone=event.helper_phone or "Good Samaritan",
            live_location_url=live_location_url,
        )

    return redirect(url_for("emergency_bp.active_emergency_tracking", event_token=event.event_token))


@emergency_bp.route("/event/<event_token>/tracking")
def active_emergency_tracking(event_token):
    """
    Active en-route tracking screen with:
    1. Golden Hour Survival Timer (60:00 countdown).
    2. Real-time pre-alert status & Bed Hold countdown.
    3. Category-specific first-aid action steps (with CPR metronome if Cardiac).
    4. 10-Second Cancel Button to prevent false alarms.
    """
    event = EmergencyEvent.query.filter_by(event_token=event_token).first_or_404()
    patient = event.patient
    profile = patient.patient_profile if patient else None
    hospital = event.hospital

    first_aid = get_first_aid_guidance(event.triage_category)

    return render_template(
        "app/emergency_tracking.html",
        event=event,
        patient=patient,
        profile=profile,
        hospital=hospital,
        first_aid=first_aid,
    )


@emergency_bp.route("/event/<event_token>/cancel", methods=["POST"])
def cancel_emergency(event_token):
    """
    Cancels emergency alert within false-alarm window,
    releases held hospital bed back to pool, and logs cancellation reason.
    """
    event = EmergencyEvent.query.filter_by(event_token=event_token).first_or_404()
    reason = request.form.get("reason", "Cancelled by bystander (False alarm)").strip()

    # Release held bed if applicable
    if event.selected_hospital_id:
        answers = json.loads(event.triage_answers_json or "{}")
        triage_result = evaluate_triage(answers)
        bed_type = triage_result["required_bed"]
        bed_record = WardBed.query.filter_by(
            hospital_id=event.selected_hospital_id, ward_type=bed_type
        ).first()
        if bed_record and bed_record.reserved_beds > 0:
            bed_record.reserved_beds -= 1

    event.status = "cancelled"
    event.cancellation_reason = reason
    event.updated_at = datetime.utcnow()
    db.session.commit()

    flash("Emergency dispatch cancelled. Held hospital beds have been released.", "info")
    if event.patient and event.patient.patient_profile:
        return redirect(
            url_for("emergency_bp.view_emergency_summary", qr_uuid=event.patient.patient_profile.qr_uuid)
        )
    return redirect(url_for("main.index"))
