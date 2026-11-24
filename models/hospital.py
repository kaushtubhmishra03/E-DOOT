from datetime import datetime
from models import db


class Hospital(db.Model):
    """Healthcare facility with capacity, location, and operational stats."""
    __tablename__ = "hospitals"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    slug = db.Column(db.String(100), unique=True, nullable=False)
    address = db.Column(db.String(255), nullable=False)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    emergency_helpline = db.Column(db.String(20), default="108")
    
    # Live operational status
    crowd_level = db.Column(db.String(20), default="Moderate")  # 'Low', 'Moderate', 'Critical'
    avg_consultation_time = db.Column(db.Integer, default=12)  # In minutes
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    beds = db.relationship("WardBed", backref="hospital", cascade="all, delete-orphan", lazy="joined")
    facilities = db.relationship("Facility", backref="hospital", cascade="all, delete-orphan", lazy="joined")
    doctors = db.relationship("Doctor", backref="hospital", cascade="all, delete-orphan")

    def get_bed_count(self, ward_type: str) -> int:
        """Return available beds for a given ward type (ICU, Trauma, General)."""
        for bed in self.beds:
            if bed.ward_type.upper() == ward_type.upper():
                return max(0, bed.available_beds - bed.reserved_beds)
        return 0

    def supports_category(self, category: str) -> bool:
        """Check if hospital has clinical facility/specialty for the given triage category."""
        if category == "Unknown":
            return True
        for f in self.facilities:
            if f.category.lower() == category.lower():
                return True
        return False

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "slug": self.slug,
            "address": self.address,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "phone": self.phone,
            "emergency_helpline": self.emergency_helpline,
            "crowd_level": self.crowd_level,
            "avg_consultation_time": self.avg_consultation_time,
            "beds": {b.ward_type: {"total": b.total_beds, "available": b.available_beds, "reserved": b.reserved_beds} for b in self.beds},
            "facilities": [f.category for f in self.facilities],
        }


class WardBed(db.Model):
    """Bed allocation per ward type."""
    __tablename__ = "ward_beds"

    id = db.Column(db.Integer, primary_key=True)
    hospital_id = db.Column(db.Integer, db.ForeignKey("hospitals.id"), nullable=False)
    ward_type = db.Column(db.String(30), nullable=False)  # 'ICU', 'Trauma', 'General'
    total_beds = db.Column(db.Integer, default=10, nullable=False)
    available_beds = db.Column(db.Integer, default=5, nullable=False)
    reserved_beds = db.Column(db.Integer, default=0, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Facility(db.Model):
    """Hospital clinical specialties and high-acuity equipment."""
    __tablename__ = "facilities"

    id = db.Column(db.Integer, primary_key=True)
    hospital_id = db.Column(db.Integer, db.ForeignKey("hospitals.id"), nullable=False)
    category = db.Column(db.String(50), nullable=False)  # 'Cardiac', 'Stroke', 'Trauma', 'Breathing', 'Burns'
    has_cath_lab = db.Column(db.Boolean, default=False)
    has_ct_mri = db.Column(db.Boolean, default=True)
    has_burn_unit = db.Column(db.Boolean, default=False)
    has_trauma_center = db.Column(db.Boolean, default=False)
    notes = db.Column(db.String(255), nullable=True)


class Doctor(db.Model):
    """Doctor profile associated with a hospital."""
    __tablename__ = "doctors"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    hospital_id = db.Column(db.Integer, db.ForeignKey("hospitals.id"), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    specialization = db.Column(db.String(100), nullable=False)  # e.g., 'Cardiology', 'General Medicine'
    cabin_number = db.Column(db.String(20), default="Room 101")
    is_on_duty = db.Column(db.Boolean, default=True)
    current_token_number = db.Column(db.Integer, default=0)
