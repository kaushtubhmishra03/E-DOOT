"""
Queue wait-time prediction and dynamic consultation time learning engine.

Calculates:
1. People ahead in line for a specific doctor / clinic.
2. Estimated wait time = people_ahead * avg_consultation_time.
3. Recalculates average consultation duration when a doctor marks a patient done.
4. "Leave Now" advisory based on patient transit time vs queue wait.
"""

from datetime import datetime
from typing import Dict, Any, List, Optional


def calculate_queue_position(
    tokens: List[Any],
    current_token_number: int,
    target_token_number: int
) -> int:
    """
    Returns the count of patients ahead in line between current serving token
    and target patient's token among 'waiting' or 'called' tokens.
    """
    if target_token_number <= current_token_number:
        return 0

    people_ahead = 0
    for tok in tokens:
        t_num = getattr(tok, "token_number", tok if isinstance(tok, int) else 0)
        status = getattr(tok, "status", "waiting")
        if current_token_number < t_num < target_token_number and status in ["waiting", "called"]:
            people_ahead += 1

    return people_ahead


def estimate_queue_wait_minutes(
    people_ahead: int,
    avg_consultation_minutes: int = 12
) -> int:
    """
    Predicts wait time in minutes = people_ahead * avg_consultation_minutes.
    Floor of 0.
    """
    safe_avg = max(3, avg_consultation_minutes)
    return max(0, people_ahead * safe_avg)


def update_doctor_average_consultation(
    current_avg: int,
    completed_consultations_count: int,
    actual_duration_minutes: float
) -> int:
    """
    Updates doctor's average consultation duration using exponential/moving average.
    Clamps reasonable consultation bounds between 5 and 45 minutes.
    """
    clamped_actual = max(3.0, min(60.0, actual_duration_minutes))
    if completed_consultations_count <= 1:
        new_avg = clamped_actual
    else:
        # Smooth moving average (weight 0.7 historical, 0.3 latest)
        new_avg = (current_avg * 0.7) + (clamped_actual * 0.3)

    return int(round(max(5, min(45, new_avg))))


def evaluate_leave_now_advisory(
    predicted_wait_mins: int,
    travel_time_mins: int,
    buffer_mins: int = 10
) -> Dict[str, Any]:
    """
    Evaluates whether patient should leave home/office now.
    Triggered when: predicted_wait <= travel_time + buffer.
    """
    should_leave = predicted_wait_mins <= (travel_time_mins + buffer_mins)
    urgency = "immediate" if predicted_wait_mins <= travel_time_mins else ("soon" if should_leave else "relax")

    if urgency == "immediate":
        message = f"🚨 Leave immediately! Your appointment is estimated in {predicted_wait_mins} mins and transit takes {travel_time_mins} mins."
    elif urgency == "soon":
        message = f"🚗 Time to prepare and leave now. Estimated wait: {predicted_wait_mins} mins; transit: {travel_time_mins} mins."
    else:
        message = f"⏳ Plenty of time. Your estimated turn is in {predicted_wait_mins} mins."

    return {
        "should_leave": should_leave,
        "urgency": urgency,
        "message": message,
        "predicted_wait_mins": predicted_wait_mins,
        "travel_time_mins": travel_time_mins,
    }
