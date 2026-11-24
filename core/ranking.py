"""
Resource-aware emergency hospital ranking algorithm.

Ranks candidate healthcare facilities using the deterministic formula:
    Score = 0.5 * travel_time + 0.3 * crowd_penalty + 0.2 * speciality_fit
    (Lower score is better).

Ensures emergency dispatch never sends a patient to a facility without
an active specialty service or available critical care bed.
"""

import math
from typing import List, Dict, Any, Tuple


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate great-circle distance between two GPS coordinates in kilometers.
    """
    R = 6371.0  # Earth's radius in kilometers
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2.0) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return round(R * c, 2)


def estimate_travel_time(distance_km: float) -> float:
    """
    Estimate transit time in minutes given distance in kilometers.
    Calibrated for Indian metropolitan emergency transit (approx 25-30 km/h
    accounting for signal congestion and ambulance sirens).
    Minimum floor of 5 minutes for dispatch readiness.
    """
    base_minutes = distance_km * 2.2
    return round(max(5.0, base_minutes), 1)


def get_crowd_penalty(crowd_level: str) -> float:
    """
    Convert qualitative crowd congestion into a standardized penalty metric.
    """
    level = (crowd_level or "").strip().lower()
    if level == "critical":
        return 35.0
    elif level == "moderate":
        return 15.0
    return 0.0  # 'Low' or unlisted


def calculate_speciality_fit(hospital: Any, category: str) -> Tuple[float, str]:
    """
    Evaluate specialty fit penalty and determine equipment matching description.
    Penalties:
      0.0: Premier dedicated facility for this specific acute crisis.
      10.0: Fully equipped tertiary multi-specialty.
      25.0: Basic secondary capability.
    """
    cat = category.strip().capitalize()
    has_category = hospital.supports_category(cat)

    if not has_category:
        return 35.0, "General Emergency Care Only (Specialty Unit Not Primary)"

    # Check high-acuity equipment flags
    for f in hospital.facilities:
        if f.category.lower() == cat.lower():
            if cat == "Cardiac" and f.has_cath_lab:
                return 0.0, "Dedicated 24/7 Primary Angioplasty Cath Lab & CCU"
            if cat == "Burns" and f.has_burn_unit:
                return 0.0, "Dedicated Tertiary Burns Resuscitation Unit"
            if cat == "Trauma" and f.has_trauma_center:
                return 0.0, "Apex Level 1 Comprehensive Trauma Bay & OR"
            if cat == "Stroke" and f.has_ct_mri:
                return 0.0, "Comprehensive Stroke Center with Immediate Neuro-CT"
            return 5.0, f"Full {cat} Specialty Unit Available"

    return 10.0, f"{cat} Capable Multi-Specialty Department"


def rank_hospitals_for_emergency(
    hospitals: List[Any],
    helper_lat: float,
    helper_lng: float,
    category: str,
    required_bed_type: str = "General",
    limit: int = 3
) -> List[Dict[str, Any]]:
    """
    Filter and rank hospitals using the deterministic scoring formula:
        Score = 0.5 * travel_time + 0.3 * crowd_penalty + 0.2 * speciality_fit
    
    Filters to hospitals that support the category and have at least 1 free relevant bed.
    Returns the top-ranked hospitals with detailed score breakdown and human-readable explanation.
    """
    candidates = []

    for h in hospitals:
        # Check bed availability for required ward
        free_beds = h.get_bed_count(required_bed_type)
        supports_cat = h.supports_category(category)

        # Calculate metrics
        dist_km = haversine_distance(helper_lat, helper_lng, h.latitude, h.longitude)
        travel_time = estimate_travel_time(dist_km)
        crowd_penalty = get_crowd_penalty(h.crowd_level)
        spec_penalty, spec_desc = calculate_speciality_fit(h, category)

        # Primary bed eligibility check
        has_relevant_bed = free_beds > 0

        # Calculate score (Lower is better)
        score = round((0.5 * travel_time) + (0.3 * crowd_penalty) + (0.2 * spec_penalty), 2)

        candidates.append({
            "hospital": h,
            "hospital_id": h.id,
            "name": h.name,
            "slug": h.slug,
            "address": h.address,
            "latitude": h.latitude,
            "longitude": h.longitude,
            "phone": h.phone,
            "emergency_helpline": h.emergency_helpline,
            "crowd_level": h.crowd_level,
            "distance_km": dist_km,
            "travel_time_mins": travel_time,
            "free_beds": free_beds,
            "ward_type": required_bed_type,
            "has_relevant_bed": has_relevant_bed,
            "supports_category": supports_cat,
            "speciality_desc": spec_desc,
            "score": score,
            "breakdown": {
                "travel_time": travel_time,
                "crowd_penalty": crowd_penalty,
                "speciality_penalty": spec_penalty,
            },
        })

    # Sort: Prioritize hospitals with available relevant beds, then by lowest score
    # Eligible hospitals (has bed + supports category) come first
    eligible = [c for c in candidates if c["has_relevant_bed"] and c["supports_category"]]
    ineligible = [c for c in candidates if not (c["has_relevant_bed"] and c["supports_category"])]

    eligible.sort(key=lambda x: x["score"])
    ineligible.sort(key=lambda x: x["score"])

    # Combine pool (eligible prioritized)
    ranked_pool = eligible + ineligible

    # Build human-readable rationale for top results
    for rank_idx, item in enumerate(ranked_pool[:limit], 1):
        reasons = []
        if item["has_relevant_bed"]:
            reasons.append(f"{item['free_beds']} available {item['ward_type']} beds")
        else:
            reasons.append(f"⚠️ {item['ward_type']} at capacity")

        reasons.append(item["speciality_desc"])
        reasons.append(f"Est. Transit: {int(item['travel_time_mins'])} mins ({item['distance_km']} km)")

        if item["crowd_level"] == "Low":
            reasons.append("Low ER congestion (Minimal intake wait)")
        elif item["crowd_level"] == "Critical":
            reasons.append("High ER crowd volume")

        item["rank"] = rank_idx
        item["plain_reason"] = " • ".join(reasons)

    return ranked_pool[:limit]
