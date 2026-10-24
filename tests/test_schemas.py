"""Tests for the Pydantic JSON contracts."""
import json

import pytest
from pydantic import ValidationError

from modules import cracks, safety
from modules.schemas import CrackReport, SafetyReport, safety_metrics, to_json


def _safety_payload(**over):
    data = {
        "safety_score": 70,
        "overall_status": "Needs Improvement",
        "ppe_detection": [{"item": "Safety helmet", "detected": True, "confidence": 0.9, "note": "ok"}],
        "hazards": [{"hazard": "Open edge", "severity": "High", "remedy": "Install guardrails"}],
        "summary": "s",
    }
    data.update(over)
    return data


def _crack_payload(**over):
    data = {
        "defect_type": "Hairline",
        "estimated_width_mm": 0.3,
        "severity_score": 20,
        "urgency": "Monitor",
        "root_causes": ["Shrinkage"],
        "recommended_repairs": ["Seal with flexible sealant"],
    }
    data.update(over)
    return data


def test_valid_safety_report():
    report = SafetyReport.model_validate(_safety_payload())
    assert report.safety_score == 70
    assert report.source == "gemini"


def test_safety_enum_case_normalised():
    report = SafetyReport.model_validate(
        _safety_payload(
            overall_status="needs improvement",
            hazards=[{"hazard": "x", "severity": "critical", "remedy": "y"}],
        )
    )
    assert report.overall_status == "Needs Improvement"
    assert report.hazards[0].severity == "Critical"


def test_safety_float_score_rounded():
    assert SafetyReport.model_validate(_safety_payload(safety_score=71.6)).safety_score == 72


@pytest.mark.parametrize("score", [-1, 101])
def test_safety_score_range(score):
    with pytest.raises(ValidationError):
        SafetyReport.model_validate(_safety_payload(safety_score=score))


@pytest.mark.parametrize(
    "bad",
    [
        {"overall_status": "Fine"},
        {"hazards": [{"hazard": "x", "severity": "Extreme", "remedy": "y"}]},
        {"ppe_detection": [{"item": "h", "detected": True, "confidence": 1.5, "note": ""}]},
    ],
)
def test_safety_invalid_values(bad):
    with pytest.raises(ValidationError):
        SafetyReport.model_validate(_safety_payload(**bad))


def test_safety_missing_required_field():
    payload = _safety_payload()
    payload.pop("hazards")
    with pytest.raises(ValidationError):
        SafetyReport.model_validate(payload)


def test_valid_crack_report_and_normalisation():
    report = CrackReport.model_validate(_crack_payload(defect_type="structural shear", urgency="repair soon"))
    assert report.defect_type == "Structural Shear"
    assert report.urgency == "Repair Soon"


@pytest.mark.parametrize(
    "bad",
    [
        {"defect_type": "Earthquake"},
        {"urgency": "Whenever"},
        {"severity_score": 101},
        {"estimated_width_mm": -1},
    ],
)
def test_crack_invalid_values(bad):
    with pytest.raises(ValidationError):
        CrackReport.model_validate(_crack_payload(**bad))


def test_demo_reports_are_valid_and_round_trip():
    for report in (safety.demo_report(), cracks.demo_report()):
        again = type(report).model_validate(json.loads(to_json(report)))
        assert again == report
        assert report.source == "demo"


def test_safety_metrics_counts():
    metrics = safety_metrics(safety.demo_report())
    assert metrics == {"hazards": 3, "ppe_missing": 2}
