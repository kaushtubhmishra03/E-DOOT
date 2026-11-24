import uuid
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from models import db


class User(db.Model):
    """Core user table for Patients, Doctors, and Administrators."""
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    phone = db.Column(db.String(20), unique=True, nullable=False, index=True)
    app_id = db.Column(db.String(50), unique=True, nullable=False, index=True)  # User's chosen ID, e.g. rahul101
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), nullable=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default="patient", nullable=False)  # 'patient', 'doctor', 'admin'
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    patient_profile = db.relationship("PatientProfile", backref="user", uselist=False, cascade="all, delete-orphan")
    emergency_settings = db.relationship("EmergencySummarySettings", backref="user", uselist=False, cascade="all, delete-orphan")

    def set_password(self, password: str) -> None:
        """Hash and store the user's password."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """Verify the password against stored hash."""
        return check_password_hash(self.password_hash, password)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "phone": self.phone,
            "app_id": self.app_id,
            "full_name": self.full_name,
            "email": self.email,
            "role": self.role,
        }


class PatientProfile(db.Model):
    """Detailed medical and emergency profile for a patient."""
    __tablename__ = "patient_profiles"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, unique=True)
    
    # Public & Clinical Data
    blood_group = db.Column(db.String(10), default="Unknown")  # e.g., O+, B+, AB-
    age = db.Column(db.Integer, nullable=True)
    gender = db.Column(db.String(20), default="Unspecified")
    address = db.Column(db.String(255), nullable=True)
    
    # Comma-separated or text entries
    allergies = db.Column(db.Text, default="")  # e.g., "Penicillin, Peanuts"
    chronic_conditions = db.Column(db.Text, default="")  # e.g., "Asthma, Type 2 Diabetes"
    current_medications = db.Column(db.Text, default="")  # e.g., "Metformin 500mg, Salbutamol"
    
    # ICE (In Case of Emergency) Contact
    emergency_contact_name = db.Column(db.String(120), nullable=True)
    emergency_contact_phone = db.Column(db.String(20), nullable=True)
    emergency_contact_relation = db.Column(db.String(50), default="Family")

    # Secure unguessable token for emergency lockscreen QR scan
    qr_uuid = db.Column(db.String(64), unique=True, nullable=False, default=lambda: uuid.uuid4().hex)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "blood_group": self.blood_group,
            "age": self.age,
            "gender": self.gender,
            "address": self.address,
            "allergies": self.allergies,
            "chronic_conditions": self.chronic_conditions,
            "current_medications": self.current_medications,
            "emergency_contact_name": self.emergency_contact_name,
            "emergency_contact_phone": self.emergency_contact_phone,
            "emergency_contact_relation": self.emergency_contact_relation,
            "qr_uuid": self.qr_uuid,
        }


class EmergencySummarySettings(db.Model):
    """User privacy preferences dictating what is shown on unauthenticated QR scan."""
    __tablename__ = "emergency_summary_settings"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, unique=True)

    show_full_name = db.Column(db.Boolean, default=True)
    show_blood_group = db.Column(db.Boolean, default=True)
    show_allergies = db.Column(db.Boolean, default=True)
    show_conditions = db.Column(db.Boolean, default=True)
    show_medications = db.Column(db.Boolean, default=True)
    show_emergency_contact = db.Column(db.Boolean, default=True)
    show_address = db.Column(db.Boolean, default=False)  # Hidden by default for privacy
