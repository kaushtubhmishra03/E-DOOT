"""
Seed script for E-Doot database.
Populates 8 realistic hospitals in Delhi/NCR, clinical facilities, bed capacities,
doctors, and 3 diverse mock patient profiles with fixed deterministic QR tokens for testing.
"""

from app import create_app
from models import (
    db,
    User,
    PatientProfile,
    EmergencySummarySettings,
    Hospital,
    WardBed,
    Facility,
    Doctor,
    MedicationReminder,
)


def seed_database():
    app = create_app()
    with app.app_context():
        print("Resetting and creating fresh database tables...")
        db.drop_all()
        db.create_all()

        print("Seeding 8 mock hospitals in Delhi/NCR...")
        hospitals_data = [
            {
                "name": "AIIMS New Delhi (Apex Trauma Center)",
                "slug": "aiims-delhi",
                "address": "Sri Aurobindo Marg, Ansari Nagar, New Delhi",
                "latitude": 28.5672,
                "longitude": 77.2100,
                "phone": "+91-11-26588500",
                "emergency_helpline": "108",
                "crowd_level": "Critical",
                "avg_consultation_time": 10,
                "beds": {"ICU": (16, 3), "Trauma": (25, 4), "General": (120, 15)},
                "specialties": [
                    ("Cardiac", True, True, False, True),
                    ("Stroke", False, True, False, True),
                    ("Trauma", False, True, False, True),
                    ("Breathing", False, True, False, True),
                    ("Burns", False, True, True, True),
                ],
            },
            {
                "name": "Safdarjung Hospital & VMMC",
                "slug": "safdarjung-delhi",
                "address": "Ring Road, Opposite AIIMS, New Delhi",
                "latitude": 28.5700,
                "longitude": 77.2070,
                "phone": "+91-11-26165060",
                "emergency_helpline": "108",
                "crowd_level": "Moderate",
                "avg_consultation_time": 12,
                "beds": {"ICU": (14, 5), "Trauma": (20, 7), "General": (100, 22)},
                "specialties": [
                    ("Trauma", False, True, False, True),
                    ("Burns", False, True, True, True),
                    ("Breathing", False, True, False, False),
                    ("Stroke", False, True, False, False),
                ],
            },
            {
                "name": "Fortis Escorts Heart Institute",
                "slug": "fortis-okhla",
                "address": "Okhla Road, Sukhdev Vihar, New Delhi",
                "latitude": 28.5604,
                "longitude": 77.2831,
                "phone": "+91-11-47135000",
                "emergency_helpline": "+91-11-47135555",
                "crowd_level": "Low",
                "avg_consultation_time": 15,
                "beds": {"ICU": (18, 9), "Trauma": (6, 3), "General": (70, 24)},
                "specialties": [
                    ("Cardiac", True, True, False, False),
                    ("Stroke", False, True, False, False),
                    ("Breathing", False, True, False, False),
                ],
            },
            {
                "name": "Max Super Speciality Hospital (Saket)",
                "slug": "max-saket",
                "address": "1, 2 Press Enclave Marg, Saket, New Delhi",
                "latitude": 28.5273,
                "longitude": 77.2155,
                "phone": "+91-11-26515050",
                "emergency_helpline": "+91-11-26515555",
                "crowd_level": "Low",
                "avg_consultation_time": 14,
                "beds": {"ICU": (12, 6), "Trauma": (10, 5), "General": (85, 28)},
                "specialties": [
                    ("Cardiac", True, True, False, False),
                    ("Stroke", False, True, False, True),
                    ("Trauma", False, True, False, True),
                    ("Breathing", False, True, False, False),
                ],
            },
            {
                "name": "Indraprastha Apollo Hospitals",
                "slug": "apollo-sarita-vihar",
                "address": "Delhi-Mathura Road, Sarita Vihar, New Delhi",
                "latitude": 28.5398,
                "longitude": 77.2842,
                "phone": "+91-11-26925858",
                "emergency_helpline": "1066",
                "crowd_level": "Moderate",
                "avg_consultation_time": 15,
                "beds": {"ICU": (20, 8), "Trauma": (12, 5), "General": (95, 30)},
                "specialties": [
                    ("Cardiac", True, True, False, True),
                    ("Stroke", False, True, False, True),
                    ("Trauma", False, True, False, True),
                    ("Breathing", False, True, False, True),
                    ("Burns", False, True, True, False),
                ],
            },
            {
                "name": "Dr. Ram Manohar Lohia Hospital",
                "slug": "rml-delhi",
                "address": "Baba Kharak Singh Marg, Connaught Place, New Delhi",
                "latitude": 28.6253,
                "longitude": 77.2001,
                "phone": "+91-11-23365525",
                "emergency_helpline": "108",
                "crowd_level": "Critical",
                "avg_consultation_time": 10,
                "beds": {"ICU": (12, 2), "Trauma": (15, 3), "General": (90, 10)},
                "specialties": [
                    ("Trauma", False, True, False, True),
                    ("Stroke", False, True, False, True),
                    ("Breathing", False, True, False, False),
                ],
            },
            {
                "name": "Sir Ganga Ram Hospital",
                "slug": "ganga-ram-delhi",
                "address": "Sir Ganga Ram Hospital Marg, Rajinder Nagar, New Delhi",
                "latitude": 28.6385,
                "longitude": 77.1895,
                "phone": "+91-11-25750000",
                "emergency_helpline": "+91-11-42251000",
                "crowd_level": "Moderate",
                "avg_consultation_time": 12,
                "beds": {"ICU": (16, 7), "Trauma": (8, 4), "General": (80, 22)},
                "specialties": [
                    ("Cardiac", True, True, False, False),
                    ("Stroke", False, True, False, True),
                    ("Breathing", False, True, False, False),
                ],
            },
            {
                "name": "BLK-Max Super Speciality Hospital",
                "slug": "blk-max-delhi",
                "address": "Pusa Road, Karol Bagh, New Delhi",
                "latitude": 28.6441,
                "longitude": 77.1798,
                "phone": "+91-11-30403040",
                "emergency_helpline": "+91-11-30403000",
                "crowd_level": "Low",
                "avg_consultation_time": 14,
                "beds": {"ICU": (12, 5), "Trauma": (8, 4), "General": (65, 19)},
                "specialties": [
                    ("Cardiac", True, True, False, False),
                    ("Trauma", False, True, False, True),
                    ("Breathing", False, True, False, False),
                    ("Stroke", False, True, False, True),
                ],
            },
        ]

        hospitals_map = {}
        for h_data in hospitals_data:
            h = Hospital(
                name=h_data["name"],
                slug=h_data["slug"],
                address=h_data["address"],
                latitude=h_data["latitude"],
                longitude=h_data["longitude"],
                phone=h_data["phone"],
                emergency_helpline=h_data["emergency_helpline"],
                crowd_level=h_data["crowd_level"],
                avg_consultation_time=h_data["avg_consultation_time"],
            )
            db.session.add(h)
            db.session.flush()
            hospitals_map[h.slug] = h

            # Add beds
            for ward_type, (total, avail) in h_data["beds"].items():
                bed = WardBed(
                    hospital_id=h.id,
                    ward_type=ward_type,
                    total_beds=total,
                    available_beds=avail,
                    reserved_beds=0,
                )
                db.session.add(bed)

            # Add facilities
            for spec, cath, ct, burns, trauma in h_data["specialties"]:
                fac = Facility(
                    hospital_id=h.id,
                    category=spec,
                    has_cath_lab=cath,
                    has_ct_mri=ct,
                    has_burn_unit=burns,
                    has_trauma_center=trauma,
                )
                db.session.add(fac)

        print("Seeding doctors and administrators...")
        # Doctor 1: AIIMS
        doc_user_1 = User(
            phone="9800112233",
            app_id="drverma",
            full_name="Dr. Anita Verma",
            email="dr.verma@aiims.edu",
            role="doctor",
        )
        doc_user_1.set_password("password123")
        db.session.add(doc_user_1)
        db.session.flush()

        doc_1 = Doctor(
            user_id=doc_user_1.id,
            hospital_id=hospitals_map["aiims-delhi"].id,
            name="Dr. Anita Verma",
            specialization="Emergency & Trauma Specialist",
            cabin_number="Room 104 - Trauma Bay",
            is_on_duty=True,
            current_token_number=3,
        )
        db.session.add(doc_1)

        # Doctor 2: Fortis Cardiology
        doc_user_2 = User(
            phone="9800112244",
            app_id="drgupta",
            full_name="Dr. Rajesh Gupta",
            email="dr.gupta@fortis.com",
            role="doctor",
        )
        doc_user_2.set_password("password123")
        db.session.add(doc_user_2)
        db.session.flush()

        doc_2 = Doctor(
            user_id=doc_user_2.id,
            hospital_id=hospitals_map["fortis-okhla"].id,
            name="Dr. Rajesh Gupta",
            specialization="Chief Interventional Cardiologist",
            cabin_number="Cath Lab Suite 2",
            is_on_duty=True,
            current_token_number=2,
        )
        db.session.add(doc_2)

        # Hospital Admins
        admin_aiims = User(
            phone="9900000001",
            app_id="admin_aiims",
            full_name="AIIMS Operations Desk",
            email="admin@aiims.edu",
            role="admin",
        )
        admin_aiims.set_password("password123")
        db.session.add(admin_aiims)

        admin_fortis = User(
            phone="9900000002",
            app_id="admin_fortis",
            full_name="Fortis Desk Admin",
            email="admin@fortis.com",
            role="admin",
        )
        admin_fortis.set_password("password123")
        db.session.add(admin_fortis)

        print("Seeding 3 mock patients with deterministic emergency QR tokens...")
        patients_data = [
            {
                "phone": "9876543210",
                "app_id": "rahul101",
                "name": "Rahul Sharma",
                "email": "rahul.sharma@example.com",
                "blood_group": "O+",
                "age": 34,
                "gender": "Male",
                "address": "Sector 45, Noida / South Extension, New Delhi",
                "allergies": "Penicillin, Shellfish",
                "conditions": "Moderate Asthma (Dust/Pollen trigger)",
                "medications": "Salbutamol Inhaler 100mcg (SOS), Montelukast 10mg",
                "ice_name": "Priya Sharma (Wife)",
                "ice_phone": "+91-9876543299",
                "ice_rel": "Spouse",
                "qr_uuid": "rahul-qr-demo-token-101",
                "reminders": [
                    ("Montelukast 10mg", "1 tablet", "Daily", "Night", "Take before sleep"),
                    ("Asthma Inhaler Check", "2 puffs", "Daily", "Morning", "Rinse mouth after inhalation"),
                ],
            },
            {
                "phone": "9811223344",
                "app_id": "sunita202",
                "name": "Sunita Patel",
                "email": "sunita.patel@example.com",
                "blood_group": "B+",
                "age": 58,
                "gender": "Female",
                "address": "Block C, Greater Kailash 1, New Delhi",
                "allergies": "Aspirin, Sulfa antibiotics",
                "conditions": "Type 2 Diabetes, Hypertension, Post-Angioplasty Stent (2022)",
                "medications": "Metformin 500mg, Atorvastatin 20mg, Telmisartan 40mg",
                "ice_name": "Amit Patel (Son)",
                "ice_phone": "+91-9811223300",
                "ice_rel": "Son",
                "qr_uuid": "sunita-qr-demo-token-202",
                "reminders": [
                    ("Metformin 500mg", "1 tablet", "Twice daily", "Morning", "With breakfast"),
                    ("Telmisartan 40mg", "1 tablet", "Daily", "Morning", "After breakfast"),
                    ("Atorvastatin 20mg", "1 tablet", "Daily", "Night", "At bedtime"),
                ],
            },
            {
                "phone": "9988776655",
                "app_id": "vikram303",
                "name": "Vikram Malhotra",
                "email": "vikram.malhotra@example.com",
                "blood_group": "AB-",
                "age": 26,
                "gender": "Male",
                "address": "DLF Phase 2, Gurugram, NCR",
                "allergies": "No known drug allergies (NKDA)",
                "conditions": "None (Active marathon runner)",
                "medications": "Multivitamin Complex",
                "ice_name": "Rohan Malhotra (Brother)",
                "ice_phone": "+91-9988776600",
                "ice_rel": "Brother",
                "qr_uuid": "vikram-qr-demo-token-303",
                "reminders": [
                    ("Daily Multivitamin", "1 capsule", "Daily", "Morning", "With water after meal"),
                ],
            },
        ]

        for p in patients_data:
            u = User(
                phone=p["phone"],
                app_id=p["app_id"],
                full_name=p["name"],
                email=p["email"],
                role="patient",
            )
            u.set_password("password123")
            db.session.add(u)
            db.session.flush()

            profile = PatientProfile(
                user_id=u.id,
                blood_group=p["blood_group"],
                age=p["age"],
                gender=p["gender"],
                address=p["address"],
                allergies=p["allergies"],
                chronic_conditions=p["conditions"],
                current_medications=p["medications"],
                emergency_contact_name=p["ice_name"],
                emergency_contact_phone=p["ice_phone"],
                emergency_contact_relation=p["ice_rel"],
                qr_uuid=p["qr_uuid"],
            )
            db.session.add(profile)

            settings = EmergencySummarySettings(
                user_id=u.id,
                show_full_name=True,
                show_blood_group=True,
                show_allergies=True,
                show_conditions=True,
                show_medications=True,
                show_emergency_contact=True,
                show_address=False,
            )
            db.session.add(settings)

            for med_name, dose, freq, slot, instr in p["reminders"]:
                rem = MedicationReminder(
                    patient_id=u.id,
                    medicine_name=med_name,
                    dosage=dose,
                    frequency=freq,
                    time_slot=slot,
                    instructions=instr,
                    is_active=True,
                )
                db.session.add(rem)

        db.session.commit()
        print("Database seeded successfully with 8 hospitals, 4 clinical staff, and 3 patients!")


if __name__ == "__main__":
    seed_database()
