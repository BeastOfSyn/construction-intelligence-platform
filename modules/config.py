"""Central configuration: constants, rate tables, weather alerts, disclaimers."""
from __future__ import annotations

from typing import Dict, List, Tuple

APP_TITLE = "Multimodal Construction Intelligence Platform"
APP_SUBTITLE = "Site safety, structural diagnostics, cost planning and valuation in one dashboard"

DISCLAIMER = (
    "Educational decision-support tool. It is NOT a certified engineering, "
    "structural-safety, estimating or valuation system. AI output can be wrong; "
    "a qualified professional must verify any real-world decision."
)
DEMO_NOTICE = "Demo mode does not analyze image pixels. Results shown are illustrative sample data."

# ---------------------------------------------------------------- AI / uploads
DEFAULT_MODEL = "gemini-3.5-flash"
MAX_UPLOAD_MB = 8
MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024
MAX_IMAGE_SIDE = 1600
ALLOWED_IMAGE_TYPES: List[str] = ["jpg", "jpeg", "png"]
CHAT_HISTORY_TURNS = 10
REQUEST_TIMEOUT_S = 60

# ------------------------------------------------------------------ valuation
STRUCTURE_TYPES: List[str] = [
    "Residential Apartment",
    "Independent House/Villa",
    "Commercial",
    "Industrial",
]
LOCATION_TIERS: List[str] = ["Tier 1", "Tier 2", "Tier 3"]
FINISH_LEVELS: List[str] = ["Basic", "Standard", "Premium"]

BASE_CONSTRUCTION_RATE: Dict[str, float] = {
    "Residential Apartment": 1800,
    "Independent House/Villa": 2200,
    "Commercial": 2600,
    "Industrial": 2000,
}
TIER_COST_MULTIPLIER: Dict[str, float] = {"Tier 1": 1.25, "Tier 2": 1.0, "Tier 3": 0.85}
FINISH_MULTIPLIER: Dict[str, float] = {"Basic": 0.9, "Standard": 1.0, "Premium": 1.3}
MARKET_RATE_PER_SQFT: Dict[str, float] = {"Tier 1": 9500, "Tier 2": 5500, "Tier 3": 3200}
STRUCTURE_MARKET_MULTIPLIER: Dict[str, float] = {
    "Residential Apartment": 1.0,
    "Independent House/Villa": 1.15,
    "Commercial": 1.3,
    "Industrial": 0.8,
}
# Value of the land/plot share at 0% completion, remainder accrues with progress.
LAND_VALUE_SHARE = 0.30
CEMENT_BAGS_PER_SQFT = 0.40
STEEL_KG_PER_SQFT = 4.0
MIN_SQFT = 200
MAX_SQFT = 500_000

# (name, start_inclusive, end_exclusive); the last stage ends at 100 inclusive.
MILESTONES: List[Tuple[str, int, int]] = [
    ("Foundation", 0, 15),
    ("Plinth", 15, 30),
    ("Superstructure", 30, 60),
    ("Finishing", 60, 85),
    ("Handover", 85, 100),
]

VALUATION_NOTE = (
    "Rates are illustrative thumb rules, not a quotation, bill of quantities or market appraisal."
)

# ------------------------------------------------------------------- severity
SEVERITY_LEVELS: List[str] = ["Low", "Medium", "High", "Critical"]
SEVERITY_COLORS: Dict[str, str] = {
    "Low": "#16a34a",
    "Medium": "#d97706",
    "High": "#ea580c",
    "Critical": "#dc2626",
}
STATUS_COLORS: Dict[str, str] = {
    "Compliant": "#16a34a",
    "Needs Improvement": "#d97706",
    "Non-Compliant": "#ea580c",
    "Critical": "#dc2626",
}
URGENCY_COLORS: Dict[str, str] = {
    "Monitor": "#16a34a",
    "Repair Soon": "#d97706",
    "Urgent": "#ea580c",
    "Immediate": "#dc2626",
}

# -------------------------------------------------------------------- weather
WEATHER_CONDITIONS: List[str] = ["High Wind", "Heavy Rain", "Extreme Heat", "Normal"]
WEATHER_ALERTS: Dict[str, Dict[str, object]] = {
    "High Wind": {
        "level": "error",
        "headline": "High wind alert: restrict lifting and work at height",
        "actions": [
            "Suspend crane and tower-crane operations once wind exceeds the manufacturer's limit.",
            "Secure scaffolding ties, sheeting, formwork panels and all loose materials.",
            "Stop work at height and on open edges; clear personnel from the swing radius.",
            "Lower or lock booms, hoists and material platforms; park mobile equipment.",
            "Re-inspect scaffolding and temporary works before work resumes.",
        ],
    },
    "Heavy Rain": {
        "level": "warning",
        "headline": "Heavy rain alert: electrical, excavation and curing risks",
        "actions": [
            "Isolate temporary electrical supply in wet areas; verify earth-leakage (RCD/GFCI) protection.",
            "Cover freshly placed concrete and protect curing surfaces from washout.",
            "Pump out excavations and inspect trench walls and shoring for collapse risk.",
            "Control slip hazards: clear mud, add walkways, and restrict ladder use.",
            "Postpone concrete pours, painting and external waterproofing until conditions improve.",
        ],
    },
    "Extreme Heat": {
        "level": "warning",
        "headline": "Extreme heat alert: heat-stress and concrete curing controls",
        "actions": [
            "Provide drinking water and shaded rest areas; enforce rest-break cycles.",
            "Shift heavy work to early morning or evening hours; avoid midday exposure.",
            "Concrete curing protocol: start wet curing early, use curing compound or wet burlap, and avoid hot-hour pours.",
            "Monitor workers for heat-stress symptoms and keep first aid on site.",
            "Check hot surfaces on metal, formwork and equipment before handling.",
        ],
    },
    "Normal": {
        "level": "success",
        "headline": "Normal conditions: continue standard site controls",
        "actions": [
            "Hold the daily toolbox talk and confirm the day's task risk assessment.",
            "Carry out routine PPE checks at the gate.",
            "Inspect scaffolding, ladders and lifting gear before use.",
            "Keep walkways, access routes and material stacks tidy.",
        ],
    },
}
