"""Crack diagnostics: prompt, demo data and runner."""
from __future__ import annotations

from .ai_client import AIClient, AIResult
from .schemas import CrackReport

SYSTEM = (
    "You are a structural engineer doing a preliminary visual assessment of a concrete or "
    "masonry surface from a photograph. Be cautious, state uncertainty, and respond with valid JSON only."
)

PROMPT = """Assess the crack or defect visible in this photo of a concrete or wall surface.

Classify defect_type as exactly one of: Hairline, Settlement, Structural Shear,
Thermal Expansion, Spalling. Estimate the maximum crack width in millimetres from visual
cues (state your best estimate even if uncertain). Give likely root causes and practical
engineering repairs (for example epoxy injection, structural re-grouting, polymer-modified
mortar patching, crack stitching). If the image shows no clear defect, say so in summary,
use Hairline with a low severity_score and urgency Monitor.

Return ONLY a JSON object with exactly this shape:
{
  "defect_type": "Hairline" | "Settlement" | "Structural Shear" | "Thermal Expansion" | "Spalling",
  "estimated_width_mm": <number>,
  "severity_score": <integer 0-100, higher is more severe>,
  "urgency": "Monitor" | "Repair Soon" | "Urgent" | "Immediate",
  "root_causes": ["<cause>", ...],
  "recommended_repairs": ["<repair>", ...],
  "monitoring_advice": "<how to monitor, e.g. crack gauges, dated photos>",
  "summary": "<2-3 sentence overview>"
}"""


def demo_report() -> CrackReport:
    """Return fixed, realistic sample data used in demo/fallback mode."""
    return CrackReport(
        defect_type="Settlement",
        estimated_width_mm=2.5,
        severity_score=58,
        urgency="Repair Soon",
        root_causes=[
            "Differential foundation settlement under one corner",
            "Poor drainage softening the soil near the footing",
            "Insufficient reinforcement cover at the affected panel",
        ],
        recommended_repairs=[
            "Epoxy injection to seal and bond the crack after settlement stabilises",
            "Structural re-grouting of voids behind the affected section",
            "Improve surface drainage away from the foundation",
        ],
        monitoring_advice=(
            "Fix tell-tale crack gauges and photograph the crack monthly. Re-assess if the width grows "
            "by more than 0.5 mm."
        ),
        summary=(
            "A diagonal crack consistent with minor differential settlement. Not an immediate collapse "
            "risk, but it needs a site inspection and repair. Sample data (demo mode)."
        ),
        source="demo",
    )


def run_crack_analysis(client: AIClient, image_bytes: bytes) -> AIResult:
    """Run the crack diagnosis on a prepared JPEG image."""
    return client.generate_structured(PROMPT, image_bytes, CrackReport, demo_report, system=SYSTEM)
