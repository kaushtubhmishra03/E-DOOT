import pytest
from core.ranking import (
    haversine_distance,
    estimate_travel_time,
    get_crowd_penalty,
    rank_hospitals_for_emergency,
)


class MockHospital:
    """Lightweight test fixture mimicking Hospital model."""
    def __init__(self, id, name, lat, lng, crowd_level, beds_dict, specialties):
        self.id = id
        self.name = name
        self.slug = name.lower().replace(" ", "-")
        self.address = f"Address of {name}"
        self.latitude = lat
        self.longitude = lng
        self.phone = "108"
        self.emergency_helpline = "108"
        self.crowd_level = crowd_level
        self.beds = beds_dict  # ward_type -> free_count
        self.specialties = specialties
        self.facilities = [MockFacility(s) for s in specialties]

    def get_bed_count(self, ward_type: str) -> int:
        return self.beds.get(ward_type, 0)

    def supports_category(self, category: str) -> bool:
        if category == "Unknown":
            return True
        return category.lower() in [s.lower() for s in self.specialties]


class MockFacility:
    def __init__(self, category):
        self.category = category
        self.has_cath_lab = category.lower() == "cardiac"
        self.has_burn_unit = category.lower() == "burns"
        self.has_trauma_center = category.lower() == "trauma"
        self.has_ct_mri = True


def test_haversine_and_travel_time():
    """Verify distance computation between Connaught Place and AIIMS New Delhi (~7 km)."""
    # Connaught Place: 28.6315, 77.2167; AIIMS: 28.5672, 77.2100
    dist = haversine_distance(28.6315, 77.2167, 28.5672, 77.2100)
    assert 6.0 <= dist <= 8.5
    travel_time = estimate_travel_time(dist)
    assert travel_time >= 5.0


def test_crowd_penalties():
    """Verify standard penalty mappings."""
    assert get_crowd_penalty("Critical") == 35.0
    assert get_crowd_penalty("Moderate") == 15.0
    assert get_crowd_penalty("Low") == 0.0


def test_ranking_algorithm_and_formula():
    """
    Test scenario:
    Hospital A: Closer (2 km), but Critical crowd and 0 ICU beds.
    Hospital B: Slightly further (5 km), Low crowd, 5 free ICU beds, Cath Lab.
    Hospital B must be ranked #1 for a Cardiac emergency!
    """
    h_a = MockHospital(
        id=1,
        name="Hospital A",
        lat=28.5800,
        lng=77.2200,
        crowd_level="Critical",
        beds_dict={"ICU": 0},
        specialties=["Cardiac"],
    )
    h_b = MockHospital(
        id=2,
        name="Hospital B",
        lat=28.5400,
        lng=77.2300,
        crowd_level="Low",
        beds_dict={"ICU": 5},
        specialties=["Cardiac"],
    )

    helper_lat = 28.5850
    helper_lng = 77.2210

    ranked = rank_hospitals_for_emergency(
        hospitals=[h_a, h_b],
        helper_lat=helper_lat,
        helper_lng=helper_lng,
        category="Cardiac",
        required_bed_type="ICU",
        limit=2,
    )

    assert len(ranked) == 2
    # Hospital B must be rank #1 because it has available ICU beds
    assert ranked[0]["hospital_id"] == 2
    assert ranked[0]["rank"] == 1
    assert ranked[0]["has_relevant_bed"] is True
    assert "Cath Lab" in ranked[0]["plain_reason"]
