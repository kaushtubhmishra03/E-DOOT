import pytest
from datetime import date
from app import create_app
from config import TestingConfig
from models import (
    db,
    User,
    PatientProfile,
    Hospital,
    Doctor,
    Appointment,
    QueueToken,
    MedicationReminder,
    AdherenceLog,
    VisitNote,
)
from core.notifications import SIMULATED_SMS_STORE


@pytest.fixture
def daily_test_client():
    app = create_app(TestingConfig)
    with app.test_client() as client:
        with app.app_context():
            db.create_all()

            # Create patient
            patient = User(phone="9876500001", app_id="daily_patient", full_name="Karan Oberoi", role="patient")
            patient.set_password("pass123")
            db.session.add(patient)
            db.session.flush()

            profile = PatientProfile(
                user_id=patient.id,
                blood_group="B+",
                emergency_contact_name="Anjali Oberoi",
                emergency_contact_phone="+91-9876500099",
                qr_uuid="karan-daily-token",
            )
            db.session.add(profile)

            # Create Hospital & Doctor
            hosp = Hospital(
                name="Fortis Escorts",
                slug="fortis-escorts",
                address="Okhla, New Delhi",
                latitude=28.5604,
                longitude=77.2831,
                phone="108",
                crowd_level="Low",
                avg_consultation_time=12,
            )
            db.session.add(hosp)
            db.session.flush()

            doc_user = User(phone="9876500002", app_id="dr_karan", full_name="Dr. Rajesh Gupta", role="doctor")
            doc_user.set_password("pass123")
            db.session.add(doc_user)
            db.session.flush()

            doctor = Doctor(
                user_id=doc_user.id,
                hospital_id=hosp.id,
                name="Dr. Rajesh Gupta",
                specialization="Cardiologist",
                cabin_number="Room 204",
                is_on_duty=True,
                current_token_number=1,
            )
            db.session.add(doctor)

            # Add existing medication reminder
            reminder = MedicationReminder(
                patient_id=patient.id,
                medicine_name="Atorvastatin 20mg",
                dosage="1 tablet",
                frequency="Daily",
                time_slot="Night",
                consecutive_missed=0,
                is_active=True,
            )
            db.session.add(reminder)

            db.session.commit()

            # Log in as patient
            with client.session_transaction() as sess:
                sess["user_id"] = patient.id
                sess["user_role"] = "patient"
                sess["user_name"] = patient.full_name
                sess["app_id"] = patient.app_id

            yield client, patient, doctor, hosp, reminder

            db.drop_all()


def test_appointment_booking_and_token_issuance(daily_test_client):
    """Verify patient can book an appointment and receives a live queue token."""
    client, patient, doctor, hosp, reminder = daily_test_client

    # Book appointment
    book_resp = client.post("/app/appointments/book", data={
        "doctor_id": doctor.id,
        "scheduled_date": date.today().isoformat(),
        "scheduled_slot": "10:30 AM",
        "symptoms": "Occasional palpitations after exertion",
    }, follow_redirects=False)

    assert book_resp.status_code == 302
    assert "/app/queue" in book_resp.headers["Location"]

    # Verify Appointment & Queue Token created
    appt = Appointment.query.filter_by(patient_id=patient.id).first()
    assert appt is not None
    assert appt.doctor_id == doctor.id
    assert appt.queue_token is not None
    # Token number should be > doctor's current serving token
    assert appt.queue_token.token_number > doctor.current_token_number
    assert appt.queue_token.status == "waiting"


def test_live_queue_tracker_view(daily_test_client):
    """Verify live queue page calculates people ahead, wait time, and distance advisory."""
    client, patient, doctor, hosp, reminder = daily_test_client

    # Book appointment first to get token
    client.post("/app/appointments/book", data={
        "doctor_id": doctor.id,
        "scheduled_date": date.today().isoformat(),
        "scheduled_slot": "11:00 AM",
    })

    # Access Live Queue tracker
    queue_resp = client.get("/app/queue")
    assert queue_resp.status_code == 200
    html = queue_resp.data.decode("utf-8")
    assert "Live Clinic Queue" in html
    assert doctor.name in html
    assert "Predicted Turn Time" in html


def test_medication_adherence_and_family_missed_dose_alert(daily_test_client):
    """
    Test medication adherence logging:
    1. Miss dose 1 -> consecutive_missed = 1
    2. Miss dose 2 -> consecutive_missed = 2
    3. Miss dose 3 -> consecutive_missed = 3 -> Triggers family SMS alert!
    4. Log taken -> resets consecutive_missed = 0
    """
    client, patient, doctor, hosp, reminder = daily_test_client

    # Miss dose 1
    client.post(f"/app/reminders/{reminder.id}/log", data={"action": "missed"}, follow_redirects=True)
    db.session.refresh(reminder)
    assert reminder.consecutive_missed == 1

    # Miss dose 2
    client.post(f"/app/reminders/{reminder.id}/log", data={"action": "missed"}, follow_redirects=True)
    db.session.refresh(reminder)
    assert reminder.consecutive_missed == 2

    # Miss dose 3 (Should trigger family SMS!)
    client.post(f"/app/reminders/{reminder.id}/log", data={"action": "missed"}, follow_redirects=True)
    db.session.refresh(reminder)
    assert reminder.consecutive_missed == 3

    # Check simulated SMS store for family adherence alert
    recent_sms = SIMULATED_SMS_STORE[0]
    assert "Karan Oberoi" in recent_sms["body"]
    assert "missed 3 consecutive doses of Atorvastatin 20mg" in recent_sms["body"]
    assert "+91-9876500099" in recent_sms["to"]

    # Log Taken -> Should reset consecutive_missed to 0
    client.post(f"/app/reminders/{reminder.id}/log", data={"action": "taken"}, follow_redirects=True)
    db.session.refresh(reminder)
    assert reminder.consecutive_missed == 0


def test_visit_history_timeline(daily_test_client):
    """Verify medical history timeline displays past notes and prescriptions."""
    client, patient, doctor, hosp, reminder = daily_test_client

    # Create a completed visit note
    note = VisitNote(
        doctor_id=doctor.id,
        patient_id=patient.id,
        diagnosis="Coronary Artery Disease Review",
        clinical_notes="Stent patent. Normal ECG. Continue statin therapy.",
        next_checkup_date=date(2026, 12, 15),
    )
    db.session.add(note)
    db.session.commit()

    resp = client.get("/app/history")
    assert resp.status_code == 200
    html = resp.data.decode("utf-8")
    assert "Coronary Artery Disease Review" in html
    assert "Stent patent" in html
    assert doctor.name in html
