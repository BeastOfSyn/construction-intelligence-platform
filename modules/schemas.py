"""Pydantic JSON contracts for AI results."""
from __future__ import annotations

from typing import Any, List, Literal

from pydantic import BaseModel, Field, field_validator

Severity = Literal["Low", "Medium", "High", "Critical"]
SafetyStatus = Literal["Compliant", "Needs Improvement", "Non-Compliant", "Critical"]
DefectType = Literal["Hairline", "Settlement", "Structural Shear", "Thermal Expansion", "Spalling"]
Urgency = Literal["Monitor", "Repair Soon", "Urgent", "Immediate"]

_SEVERITIES = ("Low", "Medium", "High", "Critical")
_STATUSES = ("Compliant", "Needs Improvement", "Non-Compliant", "Critical")
_DEFECTS = ("Hairline", "Settlement", "Structural Shear", "Thermal Expansion", "Spalling")
_URGENCIES = ("Monitor", "Repair Soon", "Urgent", "Immediate")


def _match(value: Any, options: tuple) -> Any:
    """Case/whitespace-insensitive match of ``value`` to one of ``options``.

    Unknown values are returned unchanged so Pydantic raises a clear error.
    """
    if isinstance(value, str):
        key = value.strip().lower().replace("_", " ").replace("-", " ")
        for option in options:
            if option.lower().replace("-", " ") == key:
                return option
    return value


class PPEItem(BaseModel):
    """One PPE checklist entry."""

    item: str
    detected: bool
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    note: str = ""


class Hazard(BaseModel):
    """One identified site hazard."""

    hazard: str
    severity: Severity
    remedy: str

    @field_validator("severity", mode="before")
    @classmethod
    def _norm_severity(cls, v: Any) -> Any:
        return _match(v, _SEVERITIES)


class SafetyReport(BaseModel):
    """Structured PPE / site-safety audit result."""

    safety_score: int = Field(ge=0, le=100)
    overall_status: SafetyStatus
    ppe_detection: List[PPEItem]
    hazards: List[Hazard]
    summary: str = ""
    source: str = "gemini"

    @field_validator("overall_status", mode="before")
    @classmethod
    def _norm_status(cls, v: Any) -> Any:
        return _match(v, _STATUSES)

    @field_validator("safety_score", mode="before")
    @classmethod
    def _round_score(cls, v: Any) -> Any:
        if isinstance(v, float):
            return int(round(v))
        return v


class CrackReport(BaseModel):
    """Structured crack / structural-integrity diagnosis."""

    defect_type: DefectType
    estimated_width_mm: float = Field(ge=0.0, le=500.0)
    severity_score: int = Field(ge=0, le=100)
    urgency: Urgency
    root_causes: List[str]
    recommended_repairs: List[str]
    monitoring_advice: str = ""
    summary: str = ""
    source: str = "gemini"

    @field_validator("defect_type", mode="before")
    @classmethod
    def _norm_defect(cls, v: Any) -> Any:
        return _match(v, _DEFECTS)

    @field_validator("urgency", mode="before")
    @classmethod
    def _norm_urgency(cls, v: Any) -> Any:
        return _match(v, _URGENCIES)

    @field_validator("severity_score", mode="before")
    @classmethod
    def _round_score(cls, v: Any) -> Any:
        if isinstance(v, float):
            return int(round(v))
        return v


def safety_metrics(report: SafetyReport) -> dict:
    """Return headline counts for a safety report."""
    missing = sum(1 for p in report.ppe_detection if not p.detected)
    return {"hazards": len(report.hazards), "ppe_missing": missing}


def to_json(model: BaseModel) -> str:
    """Serialize a model to pretty JSON for download."""
    return model.model_dump_json(indent=2)
