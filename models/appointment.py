from datetime import datetime
from models import db


class Appointment(db.Model):
    """Outpatient doctor consultation booking."""
    __tablename__ = "appointments"

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey("doctors.id"), nullable=False)
    hospital_id = db.Column(db.Integer, db.ForeignKey("hospitals.id"), nullable=False)
    
    scheduled_date = db.Column(db.Date, nullable=False)
    scheduled_slot = db.Column(db.String(20), default="10:00 AM")
    symptoms = db.Column(db.String(255), nullable=True)
    status = db.Column(db.String(20), default="booked")  # 'booked', 'in_queue', 'completed', 'cancelled'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    patient = db.relationship("User", backref="appointments")
    doctor = db.relationship("Doctor", backref="appointments")
    hospital = db.relationship("Hospital", backref="appointments")
    queue_token = db.relationship("QueueToken", backref="appointment", uselist=False, cascade="all, delete-orphan")
    visit_notes = db.relationship("VisitNote", backref="appointment", cascade="all, delete-orphan")


class QueueToken(db.Model):
    """Live queue token for outpatient clinic."""
    __tablename__ = "queue_tokens"

    id = db.Column(db.Integer, primary_key=True)
    appointment_id = db.Column(db.Integer, db.ForeignKey("appointments.id"), unique=True, nullable=False)
    hospital_id = db.Column(db.Integer, db.ForeignKey("hospitals.id"), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey("doctors.id"), nullable=False)
    patient_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    
    token_number = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), default="waiting")  # 'waiting', 'called', 'in_consultation', 'done', 'skipped'
    
    issued_at = db.Column(db.DateTime, default=datetime.utcnow)
    consultation_start_time = db.Column(db.DateTime, nullable=True)
    consultation_end_time = db.Column(db.DateTime, nullable=True)

    # Relationships
    patient = db.relationship("User", backref="queue_tokens")
    doctor = db.relationship("Doctor", backref="queue_tokens")
    hospital = db.relationship("Hospital", backref="queue_tokens")


class VisitNote(db.Model):
    """Clinical documentation and prescription summary recorded by a doctor."""
    __tablename__ = "visit_notes"

    id = db.Column(db.Integer, primary_key=True)
    appointment_id = db.Column(db.Integer, db.ForeignKey("appointments.id"), nullable=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey("doctors.id"), nullable=False)
    patient_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    
    diagnosis = db.Column(db.String(255), nullable=False)
    clinical_notes = db.Column(db.Text, nullable=True)
    next_checkup_date = db.Column(db.Date, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    doctor = db.relationship("Doctor", backref="visit_notes")
    patient = db.relationship("User", backref="visit_notes")
