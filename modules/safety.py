"""PPE / site-safety audit: prompt, demo data and runner."""
from __future__ import annotations

from .ai_client import AIClient, AIResult
from .schemas import Hazard, PPEItem, SafetyReport

SYSTEM = (
    "You are a construction site safety officer reviewing a site photograph. "
    "Be conservative, specific and honest about what is not visible. "
    "Respond with valid JSON only."
)

PROMPT = """Audit this construction site photo for worker PPE compliance and site hazards.

Check these PPE items for every visible worker: Safety helmet, High-vis vest,
Steel-toe boots, Safety harness (when working at height), Gloves, Eye protection.
Reference OSHA 29 CFR 1926 and Indian standards (IS 456 for concrete works,
IS 3764 for excavation safety, IS 7969 for safety in construction). If an item cannot
be judged from the photo, set detected=false, a low confidence, and say so in note.

Return ONLY a JSON object with exactly this shape:
{
  "safety_score": <integer 0-100, higher is safer>,
  "overall_status": "Compliant" | "Needs Improvement" | "Non-Compliant" | "Critical",
  "ppe_detection": [
    {"item": "<PPE name>", "detected": <true|false>, "confidence": <0.0-1.0>, "note": "<short>"}
  ],
  "hazards": [
    {"hazard": "<description>", "severity": "Low"|"Medium"|"High"|"Critical", "remedy": "<corrective action>"}
  ],
  "summary": "<2-3 sentence overview>"
}
Include all six PPE items in ppe_detection. List every identifiable hazard."""


def demo_report() -> SafetyReport:
    """Return fixed, realistic sample data used in demo/fallback mode."""
    return SafetyReport(
        safety_score=68,
        overall_status="Needs Improvement",
        ppe_detection=[
            PPEItem(item="Safety helmet", detected=True, confidence=0.93, note="Worn by all visible workers."),
            PPEItem(item="High-vis vest", detected=True, confidence=0.88, note="Visible on most workers."),
            PPEItem(item="Steel-toe boots", detected=True, confidence=0.71, note="Footwear appears protective."),
            PPEItem(item="Safety harness", detected=False, confidence=0.82, note="No harness while working near an edge."),
            PPEItem(item="Gloves", detected=True, confidence=0.64, note="Gloves seen on two workers."),
            PPEItem(item="Eye protection", detected=False, confidence=0.58, note="No goggles visible during cutting."),
        ],
        hazards=[
            Hazard(
                hazard="Worker near an unprotected edge without fall arrest",
                severity="High",
                remedy="Install edge protection and require a harness anchored to a rated point.",
            ),
            Hazard(
                hazard="Loose materials stacked near walkway",
                severity="Medium",
                remedy="Relocate and stack materials on stable ground away from access routes.",
            ),
            Hazard(
                hazard="Trailing cables across the work area",
                severity="Low",
                remedy="Route cables overhead or use protective covers to remove trip hazards.",
            ),
        ],
        summary=(
            "Head and body protection is mostly in place, but fall protection and eye protection are "
            "missing. Address the edge hazard before work continues. Sample data (demo mode)."
        ),
        source="demo",
    )


def run_ppe_audit(client: AIClient, image_bytes: bytes) -> AIResult:
    """Run the PPE audit on a prepared JPEG image."""
    return client.generate_structured(PROMPT, image_bytes, SafetyReport, demo_report, system=SYSTEM)
