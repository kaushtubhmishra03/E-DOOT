import pytest
import json
from app import create_app
from config import TestingConfig
from models import db, User, PatientProfile, EmergencySummarySettings, Hospital, WardBed, Facility, EmergencyEvent
from core.notifications import SIMULATED_SMS_STORE


@pytest.fixture
def test_setup():
    app = create_app(TestingConfig)
    with app.test_client() as client:
        with app.app_context():
            db.create_all()

            # Create test patient
            user = User(phone="9988112233", app_id="test_patient", full_name="Aarav Verma", role="patient")
            user.set_password("pass123")
            db.session.add(user)
            db.session.flush()

            profile = PatientProfile(
                user_id=user.id,
                blood_group="O+",
                allergies="Penicillin",
                chronic_conditions="Asthma",
                emergency_contact_name="Neha Verma",
                emergency_contact_phone="9988112299",
                qr_uuid="test-qr-dispatch-token",
            )
            db.session.add(profile)
            settings = EmergencySummarySettings(user_id=user.id)
            db.session.add(settings)

            # Create test hospital with beds
            hosp = Hospital(
                name="Metro Heart Hospital",
                slug="metro-heart",
                address="Ring Road, New Delhi",
                latitude=28.5600,
                longitude=77.2200,
                phone="108",
                emergency_helpline="108",
                crowd_level="Low",
            )
            db.session.add(hosp)
            db.session.flush()

            bed = WardBed(
                hospital_id=hosp.id,
                ward_type="ICU",
                total_beds=10,
                available_beds=5,
                reserved_beds=0,
            )
            db.session.add(bed)

            fac = Facility(
                hospital_id=hosp.id,
                category="Cardiac",
                has_cath_lab=True,
                has_ct_mri=True,
            )
            db.session.add(fac)

            db.session.commit()

            yield client, user, hosp

            db.drop_all()


def test_emergency_workflow_triage_dispatch_and_bed_hold(test_setup):
    """
    Integration test:
    1. Helper submits triage form (Chest pain = yes) -> creates EmergencyEvent
    2. Ranking page displays top hospitals
    3. Helper dispatches to hospital -> 1 ICU bed is held (reserved_beds=1)
    4. Family SMS is sent (without private clinical symptoms!)
    5. Helper cancels alert -> held bed is released back (reserved_beds=0)
    """
    client, user, hosp = test_setup

    # 1. Submit Triage
    triage_data = {
        "is_conscious": "conscious",
        "has_chest_pain": "yes",
        "has_stroke_signs": "no",
        "has_severe_trauma": "no",
        "has_breathing_issue": "no",
        "has_burns": "no",
        "helper_phone": "9876543210",
        "helper_lat": "28.5700",
        "helper_lng": "77.2100",
    }
    resp = client.post("/app/emergency/test-qr-dispatch-token/submit-triage", data=triage_data, follow_redirects=False)
    assert resp.status_code == 302
    assert "/ranking" in resp.headers["Location"]

    event = EmergencyEvent.query.filter_by(patient_id=user.id).first()
    assert event is not None
    assert event.triage_category == "Cardiac"

    # 2. View Ranking
    rank_resp = client.get(f"/app/emergency/event/{event.event_token}/ranking")
    assert rank_resp.status_code == 200
    rank_html = rank_resp.data.decode("utf-8")
    assert "Metro Heart Hospital" in rank_html
    assert "Cardiac Emergency" in rank_html

    # Check initial beds before dispatch
    bed = WardBed.query.filter_by(hospital_id=hosp.id, ward_type="ICU").first()
    assert bed.reserved_beds == 0

    # 3. Dispatch to Hospital
    dispatch_resp = client.post(
        f"/app/emergency/event/{event.event_token}/dispatch",
        data={"hospital_id": hosp.id, "eta_minutes": 12},
        follow_redirects=False,
    )
    assert dispatch_resp.status_code == 302
    assert "/tracking" in dispatch_resp.headers["Location"]

    # Verify Bed Hold (Proposal 3)
    db.session.refresh(bed)
    assert bed.reserved_beds == 1  # 1 bed held!
    db.session.refresh(event)
    assert event.status == "pre_alert_sent"
    assert event.selected_hospital_id == hosp.id

    # 4. Verify Family SMS Dispatch
    # Privacy rule check: SMS must NOT expose symptoms or "Cardiac / Chest pain"
    recent_sms = SIMULATED_SMS_STORE[0]
    assert "Metro Heart Hospital" in recent_sms["body"]
    assert "Aarav Verma" in recent_sms["body"]
    assert "Chest Pain" not in recent_sms["body"]
    assert "Cardiac" not in recent_sms["body"]

    # 5. Cancel Emergency (False alarm safety window)
    cancel_resp = client.post(
        f"/app/emergency/event/{event.event_token}/cancel",
        data={"reason": "False alarm testing"},
        follow_redirects=True,
    )
    assert cancel_resp.status_code == 200
    db.session.refresh(bed)
    assert bed.reserved_beds == 0  # Held bed released back to pool!
    db.session.refresh(event)
    assert event.status == "cancelled"
