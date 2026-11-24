from core.triage import evaluate_triage, get_first_aid_guidance, TriageCategory


def test_triage_cardiac_mapping():
    """Verify chest pain triggers Cardiac category and requires ICU bed."""
    answers = {
        "is_conscious": "conscious",
        "has_chest_pain": "yes",
        "has_stroke_signs": "no",
        "has_severe_trauma": "no",
        "has_breathing_issue": "no",
        "has_burns": "no",
    }
    result = evaluate_triage(answers)
    assert result["category"] == TriageCategory.CARDIAC
    assert result["acuity"] == "Critical"
    assert result["required_bed"] == "ICU"
    assert "Cath Lab" in result["primary_facility"]


def test_triage_stroke_mapping():
    """Verify neurological stroke symptoms map to Stroke category."""
    answers = {
        "is_conscious": "conscious",
        "has_chest_pain": "no",
        "has_stroke_signs": "yes",
        "has_severe_trauma": "no",
        "has_breathing_issue": "no",
        "has_burns": "no",
    }
    result = evaluate_triage(answers)
    assert result["category"] == TriageCategory.STROKE
    assert result["acuity"] == "Critical"
    assert result["required_bed"] == "ICU"


def test_triage_trauma_mapping():
    """Verify severe bleeding and fracture map to Trauma category and Trauma bed."""
    answers = {
        "is_conscious": "conscious",
        "has_chest_pain": "no",
        "has_stroke_signs": "no",
        "has_severe_trauma": "yes",
        "has_breathing_issue": "no",
        "has_burns": "no",
    }
    result = evaluate_triage(answers)
    assert result["category"] == TriageCategory.TRAUMA
    assert result["required_bed"] == "Trauma"


def test_triage_breathing_mapping():
    """Verify acute respiratory distress maps to Breathing category."""
    answers = {
        "is_conscious": "conscious",
        "has_chest_pain": "no",
        "has_stroke_signs": "no",
        "has_severe_trauma": "no",
        "has_breathing_issue": "yes",
        "has_burns": "no",
    }
    result = evaluate_triage(answers)
    assert result["category"] == TriageCategory.BREATHING
    assert result["required_bed"] == "ICU"


def test_triage_burns_mapping():
    """Verify burn injuries map to Burns category."""
    answers = {
        "is_conscious": "conscious",
        "has_chest_pain": "no",
        "has_stroke_signs": "no",
        "has_severe_trauma": "no",
        "has_breathing_issue": "no",
        "has_burns": "yes",
    }
    result = evaluate_triage(answers)
    assert result["category"] == TriageCategory.BURNS
    assert result["required_bed"] == "Trauma"


def test_triage_unknown_fallback():
    """Verify general symptoms fallback to Unknown with non-empty guidance."""
    answers = {
        "is_conscious": "conscious",
        "has_chest_pain": "no",
        "has_stroke_signs": "no",
        "has_severe_trauma": "no",
        "has_breathing_issue": "no",
        "has_burns": "no",
    }
    result = evaluate_triage(answers)
    assert result["category"] == TriageCategory.UNKNOWN
    assert result["disclaimer"] != ""


def test_first_aid_guidance_cpr_metronome():
    """Verify cardiac guidance includes CPR metronome trigger."""
    guidance = get_first_aid_guidance(TriageCategory.CARDIAC, language="en")
    assert guidance["has_cpr_metronome"] is True
    assert len(guidance["steps"]) > 0

    stroke_guidance = get_first_aid_guidance(TriageCategory.STROKE, language="en")
    assert stroke_guidance["has_cpr_metronome"] is False
