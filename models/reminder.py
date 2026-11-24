from datetime import datetime, date
from models import db


class MedicationReminder(db.Model):
    """Daily medication and therapy regimen for a patient."""
    __tablename__ = "medication_reminders"

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    visit_note_id = db.Column(db.Integer, db.ForeignKey("visit_notes.id"), nullable=True)
    
    medicine_name = db.Column(db.String(150), nullable=False)
    dosage = db.Column(db.String(50), default="1 tablet")
    frequency = db.Column(db.String(50), default="Daily")  # 'Daily', 'Twice daily', 'Thrice daily', 'Weekly'
    time_slot = db.Column(db.String(50), default="Morning")  # 'Morning', 'Afternoon', 'Night'
    instructions = db.Column(db.String(150), default="After meal")
    
    consecutive_missed = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    patient = db.relationship("User", backref="reminders")
    visit_note = db.relationship("VisitNote", backref="reminders")
    adherence_logs = db.relationship("AdherenceLog", backref="reminder", cascade="all, delete-orphan")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "medicine_name": self.medicine_name,
            "dosage": self.dosage,
            "frequency": self.frequency,
            "time_slot": self.time_slot,
            "instructions": self.instructions,
            "consecutive_missed": self.consecutive_missed,
            "is_active": self.is_active,
        }


class AdherenceLog(db.Model):
    """Log of taken vs missed doses."""
    __tablename__ = "adherence_logs"

    id = db.Column(db.Integer, primary_key=True)
    reminder_id = db.Column(db.Integer, db.ForeignKey("medication_reminders.id"), nullable=False)
    scheduled_date = db.Column(db.Date, default=date.today)
    time_slot = db.Column(db.String(50), default="Morning")
    status = db.Column(db.String(20), nullable=False)  # 'taken', 'missed'
    logged_at = db.Column(db.DateTime, default=datetime.utcnow)
