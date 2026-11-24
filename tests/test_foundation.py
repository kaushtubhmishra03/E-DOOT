import pytest
from app import create_app
from config import TestingConfig
from models import db, User, PatientProfile, EmergencySummarySettings, AccessAuditLog
from core.qr_generator import generate_qr_code_data_url, format_offline_medical_card
from core.i18n import t
from core.gemini_service import gemini_assistant


@pytest.fixture
def client():
    app = create_app(TestingConfig)
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
            yield client
            db.drop_all()


def test_user_creation_and_auth(client):
    """Test user registration, password hashing, and login."""
    # Register a new patient
    resp = client.post("/auth/register", data={
        "full_name": "Test User",
        "phone": "9999888877",
        "app_id": "testuser1",
        "password": "secretpassword",
        "confirm_password": "secretpassword",
        "role": "patient",
    }, follow_redirects=True)
    assert resp.status_code == 200

    # Verify user exists in database
    user = User.query.filter_by(app_id="testuser1").first()
    assert user is not None
    assert user.check_password("secretpassword") is True
    assert user.check_password("wrongpassword") is False
    assert user.patient_profile is not None
    assert user.emergency_settings is not None


def test_qr_code_generation():
    """Verify QR code data URL and offline payload generator."""
    url = "http://localhost:5000/app/emergency/test-token"
    qr_data = generate_qr_code_data_url(url)
    assert qr_data.startswith("data:image/png;base64,")

    card_text = format_offline_medical_card(
        full_name="Rahul Sharma",
        blood_group="O+",
        allergies="Penicillin",
        conditions="Asthma",
        emergency_contact="Priya (9876543299)",
        web_url=url,
    )
    assert "E-DOOT EMERGENCY MEDICAL ID" in card_text
    assert "BLOOD GROUP: O+" in card_text


def test_unauthenticated_emergency_view_and_audit_log(client):
    """Verify helper can view summary without login and that an access log is generated."""
    # Create patient with fixed QR token
    user = User(phone="9111222333", app_id="aiduser", full_name="Aarav Gupta", role="patient")
    user.set_password("pass123")
    db.session.add(user)
    db.session.flush()

    profile = PatientProfile(
        user_id=user.id,
        blood_group="B+",
        allergies="Aspirin",
        chronic_conditions="Diabetes",
        qr_uuid="aarav-emergency-token",
    )
    db.session.add(profile)
    settings = EmergencySummarySettings(
        user_id=user.id,
        show_blood_group=True,
        show_allergies=True,
        show_conditions=False,  # Hidden by patient
    )
    db.session.add(settings)
    db.session.commit()

    # Unauthenticated scan of emergency card
    resp = client.get("/app/emergency/aarav-emergency-token")
    assert resp.status_code == 200
    html = resp.data.decode("utf-8")
    assert "B+" in html
    assert "Aspirin" in html
    # Hidden condition should not appear
    assert "Diabetes" not in html
    # Good Samaritan shield must be visible
    assert "Good Samaritan" in html

    # Verify access log was created
    log = AccessAuditLog.query.filter_by(patient_id=user.id).first()
    assert log is not None
    assert log.access_type == "emergency_qr_scan"


def test_multilingual_i18n():
    """Verify translations exist across English, Hindi, and Marathi."""
    en_val = t("emergency_sos", lang="en")
    hi_val = t("emergency_sos", lang="hi")
    mr_val = t("emergency_sos", lang="mr")

    assert en_val == "Emergency SOS"
    assert "आपातकालीन" in hi_val
    assert "आपत्कालीन" in mr_val


def test_gemini_emergency_red_flag_guardrail():
    """Verify the AI Assistant intercepts acute symptoms and warns the user."""
    result = gemini_assistant.answer_health_doubt("I have severe sudden chest pain and trouble breathing", language="en")
    assert result["is_emergency"] is True
    assert "CRITICAL EMERGENCY WARNING" in result["answer"]

    # Normal health question
    normal_result = gemini_assistant.answer_health_doubt("What is a normal blood pressure?", language="en")
    assert normal_result["is_emergency"] is False
    assert "Blood Pressure" in normal_result["answer"]
