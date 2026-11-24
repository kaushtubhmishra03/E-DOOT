import pytest
from app import create_app
from config import TestingConfig
from models import (
    db,
    User,
    PatientProfile,
    Hospital,
    WardBed,
    Doctor,
    Appointment,
    QueueToken,
    EmergencyEvent,
    MedicationReminder,
    VisitNote,
)
from core.queue_engine import (
    calculate_queue_position,
    estimate_queue_wait_minutes,
    update_doctor_average_consultation,
    evaluate_leave_now_advisory,
)
from datetime import date, datetime


@pytest.fixture
def portal_test_client():
    app = create_app(TestingConfig)
    with app.test_client() as client:
        with app.app_context():
            db.create_all()

            # Create test patient
            patient = User(phone="9123456780", app_id="test_patient_3", full_name="Manish Tiwari", role="patient")
            patient.set_password("pass123")
            db.session.add(patient)
            db.session.flush()

            profile = PatientProfile(user_id=patient.id, blood_group="A+", qr_uuid="test-qr-portal-3")
            db.session.add(profile)

            # Create Hospital
            hosp = Hospital(
                name="AIIMS Delhi",
                slug="aiims-delhi",
                address="Ansari Nagar, New Delhi",
                latitude=28.5672,
                longitude=77.2100,
                phone="108",
                crowd_level="Critical",
                avg_consultation_time=10,
            )
            db.session.add(hosp)
            db.session.flush()

            # Add ICU and General beds
            bed_icu = WardBed(hospital_id=hosp.id, ward_type="ICU", total_beds=10, available_beds=2, reserved_beds=0)
            bed_gen = WardBed(hospital_id=hosp.id, ward_type="General", total_beds=50, available_beds=10, reserved_beds=0)
            db.session.add(bed_icu)
            db.session.add(bed_gen)

            # Create Doctor
            doc_user = User(phone="9123456781", app_id="dr_portal_test", full_name="Dr. Anita Verma", role="doctor")
            doc_user.set_password("pass123")
            db.session.add(doc_user)
            db.session.flush()

            doctor = Doctor(
                user_id=doc_user.id,
                hospital_id=hosp.id,
                name="Dr. Anita Verma",
                specialization="Trauma Specialist",
                cabin_number="Room 101",
                is_on_duty=True,
                current_token_number=1,
            )
            db.session.add(doctor)
            db.session.flush()

            # Create Appointment & Queue Token
            appt = Appointment(
                patient_id=patient.id,
                doctor_id=doctor.id,
                hospital_id=hosp.id,
                scheduled_date=date.today(),
            )
            db.session.add(appt)
            db.session.flush()

            token = QueueToken(
                appointment_id=appt.id,
                hospital_id=hosp.id,
                doctor_id=doctor.id,
                patient_id=patient.id,
                token_number=2,
                status="waiting",
            )
            db.session.add(token)
            db.session.commit()

            yield client, patient, doctor, hosp, token

            db.drop_all()


def test_queue_engine_calculations():
    """Verify queue position, wait estimate, and leave now advisory."""
    # Tokens 1 (serving), 2 (ahead), 3 (ahead), 4 (target)
    tokens = [
        QueueToken(token_number=2, status="waiting"),
        QueueToken(token_number=3, status="waiting"),
    ]
    people_ahead = calculate_queue_position(tokens, current_token_number=1, target_token_number=4)
    assert people_ahead == 2

    wait_mins = estimate_queue_wait_minutes(people_ahead=people_ahead, avg_consultation_minutes=15)
    assert wait_mins == 30

    # Leave now advisory when wait <= travel time + buffer
    advisory = evaluate_leave_now_advisory(predicted_wait_mins=25, travel_time_mins=20, buffer_mins=10)
    assert advisory["should_leave"] is True
    assert advisory["urgency"] == "soon"


def test_doctor_clinic_call_next_and_mark_done(portal_test_client):
    """Test doctor calling next waiting patient, documenting prescription, and completing visit."""
    client, patient, doctor, hosp, token = portal_test_client

    # Call Next Patient
    resp = client.post("/portal/doctor/clinic/call-next", follow_redirects=True)
    assert resp.status_code == 200

    db.session.refresh(token)
    assert token.status == "in_consultation"
    assert token.consultation_start_time is not None

    # Complete Consultation with Digital Prescription
    done_resp = client.post(
        f"/portal/doctor/clinic/mark-done/{token.id}",
        data={
            "diagnosis": "Acute Bronchospasm",
            "clinical_notes": "Chest wheezing cleared with nebulization. Prescribed bronchodilator.",
            "med_name": "Salbutamol 100mcg Inhaler",
            "med_dose": "2 puffs",
            "med_freq": "Daily",
            "med_slot": "Morning",
            "med_instr": "Rinse mouth after inhalation",
            "next_checkup_date": "2026-12-01",
        },
        follow_redirects=True,
    )
    assert done_resp.status_code == 200

    # Verify token is marked done
    db.session.refresh(token)
    assert token.status == "done"

    # Verify visit note was created
    note = VisitNote.query.filter_by(patient_id=patient.id).first()
    assert note is not None
    assert "Acute Bronchospasm" in note.diagnosis

    # Verify Medication Reminder was auto-created for patient!
    reminder = MedicationReminder.query.filter_by(patient_id=patient.id).first()
    assert reminder is not None
    assert reminder.medicine_name == "Salbutamol 100mcg Inhaler"
    assert reminder.is_active is True


def test_admin_live_bed_and_crowd_api(portal_test_client):
    """Test updating beds and crowd levels via admin API endpoints."""
    client, patient, doctor, hosp, token = portal_test_client

    # 1. Update ICU beds to 0 (Full)
    resp = client.post(
        f"/api/admin/hospital/{hosp.id}/update-bed",
        json={"ward_type": "ICU", "available_beds": 0},
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["effective_free"] == 0

    # 2. Update crowd to Low
    crowd_resp = client.post(
        f"/api/admin/hospital/{hosp.id}/update-crowd",
        json={"crowd_level": "Low"},
    )
    assert crowd_resp.status_code == 200
    assert crowd_resp.get_json()["crowd_level"] == "Low"


def test_doctor_er_accept_and_redirect(portal_test_client):
    """Test doctor accepting and redirecting ER pre-alerts."""
    client, patient, doctor, hosp, token = portal_test_client

    event = EmergencyEvent(
        event_token="test-er-token-123",
        patient_id=patient.id,
        triage_category="Cardiac",
        selected_hospital_id=hosp.id,
        status="pre_alert_sent",
    )
    db.session.add(event)
    db.session.commit()

    # Doctor accepts pre-alert
    accept_resp = client.post(
        f"/portal/doctor/er/{event.id}/action",
        data={"action": "accept"},
        follow_redirects=True,
    )
    assert accept_resp.status_code == 200
    db.session.refresh(event)
    assert event.status == "accepted"
