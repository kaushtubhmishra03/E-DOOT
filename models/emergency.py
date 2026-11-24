import uuid
from datetime import datetime
from models import db


class EmergencyEvent(db.Model):
    """Tracks an active or past emergency dispatch workflow."""
    __tablename__ = "emergency_events"

    id = db.Column(db.Integer, primary_key=True)
    event_token = db.Column(db.String(64), unique=True, nullable=False, default=lambda: uuid.uuid4().hex)
    patient_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    
    # Helper info
    helper_name = db.Column(db.String(100), default="Good Samaritan")
    helper_phone = db.Column(db.String(20), nullable=True)
    helper_lat = db.Column(db.Float, nullable=True)
    helper_lng = db.Column(db.Float, nullable=True)

    # Triage and Clinical
    triage_category = db.Column(db.String(50), default="Unknown")  # Cardiac, Stroke, Trauma, Breathing, Burns, Unknown
    triage_answers_json = db.Column(db.Text, default="{}")
    photo_filename = db.Column(db.String(255), nullable=True)

    # Dispatch & Routing
    selected_hospital_id = db.Column(db.Integer, db.ForeignKey("hospitals.id"), nullable=True)
    eta_minutes = db.Column(db.Integer, default=15)
    
    # Status lifecycle
    status = db.Column(db.String(30), default="initiated")
    # 'initiated', 'triage_completed', 'pre_alert_sent', 'accepted', 'redirected', 'cancelled', 'completed'
    cancellation_reason = db.Column(db.String(255), nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship
    hospital = db.relationship("Hospital", backref="emergency_events")
    patient = db.relationship("User", backref="emergency_events")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "event_token": self.event_token,
            "patient_id": self.patient_id,
            "patient_name": self.patient.full_name if self.patient else "Unidentified Patient",
            "helper_name": self.helper_name,
            "helper_phone": self.helper_phone,
            "helper_lat": self.helper_lat,
            "helper_lng": self.helper_lng,
            "triage_category": self.triage_category,
            "photo_filename": self.photo_filename,
            "selected_hospital_id": self.selected_hospital_id,
            "hospital_name": self.hospital.name if self.hospital else None,
            "eta_minutes": self.eta_minutes,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class AccessAuditLog(db.Model):
    """Immutable audit trail of emergency summary card accesses."""
    __tablename__ = "access_audit_logs"

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    accessed_at = db.Column(db.DateTime, default=datetime.utcnow)
    ip_address = db.Column(db.String(50), default="Unknown")
    user_agent = db.Column(db.String(255), default="Unknown")
    access_type = db.Column(db.String(50), default="emergency_qr_scan")  # 'emergency_qr_scan', 'web_view', 'sos_trigger'
    location_lat = db.Column(db.Float, nullable=True)
    location_lng = db.Column(db.Float, nullable=True)
    helper_note = db.Column(db.String(255), nullable=True)

    patient = db.relationship("User", backref="access_logs")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "accessed_at": self.accessed_at.strftime("%Y-%m-%d %H:%M:%S"),
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "access_type": self.access_type,
            "location": f"{self.location_lat:.4f}, {self.location_lng:.4f}" if self.location_lat and self.location_lng else "Location unshared",
        }
