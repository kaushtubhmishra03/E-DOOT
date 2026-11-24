from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

from models.user import User, PatientProfile, EmergencySummarySettings
from models.hospital import Hospital, WardBed, Facility, Doctor
from models.emergency import EmergencyEvent, AccessAuditLog
from models.appointment import Appointment, QueueToken, VisitNote
from models.reminder import MedicationReminder, AdherenceLog

__all__ = [
    "db",
    "User",
    "PatientProfile",
    "EmergencySummarySettings",
    "Hospital",
    "WardBed",
    "Facility",
    "Doctor",
    "EmergencyEvent",
    "AccessAuditLog",
    "Appointment",
    "QueueToken",
    "VisitNote",
    "MedicationReminder",
    "AdherenceLog",
]
