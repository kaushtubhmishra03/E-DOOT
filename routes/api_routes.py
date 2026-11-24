from datetime import datetime
from flask import Blueprint, request, jsonify, session
from models import db, Hospital, WardBed, Doctor, EmergencyEvent, QueueToken, Appointment, VisitNote
from core.ranking import rank_hospitals_for_emergency
from core.triage import evaluate_triage

api_bp = Blueprint("api_bp", __name__, url_prefix="/api")


@api_bp.route("/hospitals/live-rankings")
def get_live_rankings():
    """
    Real-time hospital rankings polling endpoint.
    Used by the helper interface to live-update rankings when an admin adjusts beds or crowd.
    """
    helper_lat = float(request.args.get("lat", 28.5800))
    helper_lng = float(request.args.get("lng", 77.2200))
    category = request.args.get("category", "Cardiac")
    required_bed_type = request.args.get("bed_type", "ICU")

    all_hospitals = Hospital.query.filter_by(is_active=True).all()
    ranked = rank_hospitals_for_emergency(
        hospitals=all_hospitals,
        helper_lat=helper_lat,
        helper_lng=helper_lng,
        category=category,
        required_bed_type=required_bed_type,
        limit=3,
    )

    clean_results = []
    for h in ranked:
        clean_results.append({
            "rank": h["rank"],
            "hospital_id": h["hospital_id"],
            "name": h["name"],
            "distance_km": h["distance_km"],
            "travel_time_mins": int(h["travel_time_mins"]),
            "free_beds": h["free_beds"],
            "ward_type": h["ward_type"],
            "crowd_level": h["crowd_level"],
            "score": h["score"],
            "plain_reason": h["plain_reason"],
        })

    return jsonify({
        "status": "success",
        "timestamp": datetime.utcnow().isoformat(),
        "category": category,
        "required_bed_type": required_bed_type,
        "rankings": clean_results,
    })


@api_bp.route("/admin/hospital/<int:hospital_id>/update-bed", methods=["POST"])
def admin_update_bed(hospital_id):
    """Update ward bed count (Available / Total). Modifying this alters rankings live!"""
    hospital = db.session.get(Hospital, hospital_id)
    if not hospital:
        return jsonify({"status": "error", "message": "Hospital not found"}), 404

    data = request.get_json(silent=True) or request.form
    ward_type = data.get("ward_type", "ICU").upper()
    delta = int(data.get("delta", 0))
    new_avail = data.get("available_beds")

    bed = WardBed.query.filter_by(hospital_id=hospital.id, ward_type=ward_type).first()
    if not bed:
        bed = WardBed(hospital_id=hospital.id, ward_type=ward_type, total_beds=10, available_beds=5, reserved_beds=0)
        db.session.add(bed)

    if new_avail is not None:
        bed.available_beds = max(0, int(new_avail))
    elif delta != 0:
        bed.available_beds = max(0, bed.available_beds + delta)

    db.session.commit()
    return jsonify({
        "status": "success",
        "hospital_id": hospital.id,
        "ward_type": ward_type,
        "available_beds": bed.available_beds,
        "reserved_beds": bed.reserved_beds,
        "effective_free": max(0, bed.available_beds - bed.reserved_beds),
    })


@api_bp.route("/admin/hospital/<int:hospital_id>/update-crowd", methods=["POST"])
def admin_update_crowd(hospital_id):
    """Update hospital crowd level ('Low', 'Moderate', 'Critical'). Alters rankings live!"""
    hospital = db.session.get(Hospital, hospital_id)
    if not hospital:
        return jsonify({"status": "error", "message": "Hospital not found"}), 404

    data = request.get_json(silent=True) or request.form
    crowd_level = data.get("crowd_level", "Moderate").capitalize()
    if crowd_level not in ["Low", "Moderate", "Critical"]:
        return jsonify({"status": "error", "message": "Invalid crowd level"}), 400

    hospital.crowd_level = crowd_level
    db.session.commit()
    return jsonify({
        "status": "success",
        "hospital_id": hospital.id,
        "crowd_level": hospital.crowd_level,
    })


@api_bp.route("/doctor/event/<int:event_id>/status", methods=["POST"])
def doctor_update_emergency_status(event_id):
    """Doctor accepts pre-alert or redirects to another facility."""
    event = db.session.get(EmergencyEvent, event_id)
    if not event:
        return jsonify({"status": "error", "message": "Event not found"}), 404

    data = request.get_json(silent=True) or request.form
    action = data.get("action", "accept")  # 'accept' or 'redirect'
    reason = data.get("reason", "").strip()

    if action == "accept":
        event.status = "accepted"
    elif action == "redirect":
        event.status = "redirected"
        event.cancellation_reason = reason or "Redirected to specialized center by ER Doctor"
        # Release held bed
        if event.selected_hospital_id:
            answers = evaluate_triage({})
            bed = WardBed.query.filter_by(hospital_id=event.selected_hospital_id, ward_type="ICU").first()
            if bed and bed.reserved_beds > 0:
                bed.reserved_beds -= 1

    event.updated_at = datetime.utcnow()
    db.session.commit()

    return jsonify({
        "status": "success",
        "event_id": event.id,
        "new_status": event.status,
    })
