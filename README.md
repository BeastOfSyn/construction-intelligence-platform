# Multimodal Construction Intelligence Platform

*Skill Wallet Capstone, Project 1: Generative AI | Real Estate Decision Support*

A Streamlit decision-support app that audits site-photo PPE compliance, classifies concrete
cracks with severity scores, estimates construction cost and property value in INR, and gives
weather-aware daily protocols plus a construction-engineering chatbot.

> **Safety notice:** educational tool only. It is not a certified engineering, structural-safety,
> estimating or valuation system. AI output can be wrong and must be verified by a qualified
> professional. **Demo mode does not analyze image pixels.**

## Features

| Tab | What it does |
|---|---|
| **1. Site Safety & PPE Audit** | Upload a site photo (JPG/PNG, max 8 MB). Gemini checks helmet, high-vis vest, steel-toe boots, harness, gloves and eye protection against OSHA and IS 456 / IS 3764 / IS 7969, returns a 0-100 safety score, status, PPE checklist and hazards with severity and remedies. Metric cards, status pills, downloadable JSON. |
| **2. Crack Diagnostics** | Upload a concrete/wall photo. Classifies Hairline / Settlement / Structural Shear / Thermal Expansion / Spalling, estimates width (mm), severity, root causes, repairs (epoxy injection, structural re-grouting...) and urgency. |
| **3. Planning & Valuation** | Structure type, built-up sq ft, Tier 1/2/3 city, finish level and completion slider give total budget, capex incurred, current asset valuation (INR Lakhs/Crores), cement and steel needs, milestone progress, and a Pollinations AI concept render. |
| **4. Site Assistant & Weather** | Weather selector (High Wind, Heavy Rain, Extreme Heat, Normal) with dynamic safety alerts, and a multi-turn engineering chatbot. |

**Two modes:** *Demo mode* (no API key) returns realistic sample data so every tab works offline.
*Live mode* (Gemini key in sidebar or secrets) analyzes real images and powers the chatbot. If the
AI errors or returns bad JSON twice, the app falls back to sample data and says so, with a result
badge showing the source (`gemini`, `demo` or `fallback`).

## Architecture

```
Streamlit UI (app.py)
 |- Tab 1 Safety     -> modules/safety.py --\
 |- Tab 2 Cracks     -> modules/cracks.py ---+-> modules/ai_client.py -> Gemini (multimodal)
 |- Tab 4 Assistant  -> modules/chat.py  --/    (demo / fallback data if no key or on error)
 |- Tab 3 Valuation  -> modules/valuation.py   (pure Python, deterministic)
 |                   -> modules/render3d.py -> Pollinations AI
 '- Tab 4 Weather    -> modules/weather.py     (static advisories)
All AI output is validated with Pydantic JSON contracts (modules/schemas.py).
```

No database and no runtime file writes, so it deploys in one click.

## Skill Wallet epic coverage

| Epic | Where |
|---|---|
| Pre-requisites, Epic 1: Requirements & environment | `requirements.txt`, `.streamlit/`, `.gitignore`, this README |
| Epic 2: PPE safety vision & crack diagnostics | `modules/safety.py`, `modules/cracks.py`, tabs 1-2 |
| Epic 3: Project planning & real estate valuation | `modules/valuation.py`, `modules/render3d.py`, tab 3 |
| Epic 4: Multimodal AI & JSON contracts | `modules/ai_client.py`, `modules/schemas.py` |
| Epic 5: Site chatbot & weather advisory | `modules/chat.py`, `modules/weather.py`, tab 4 |
| Epic 6: Interface, testing, cloud deployment | `app.py`, `tests/`, Streamlit Cloud steps below |

## Run locally

Requires **Python 3.11 or newer** (the pinned versions need it; tested on 3.13).

**Windows (PowerShell)**
```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1      # if blocked: Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
pip install -r requirements.txt
streamlit run app.py
```

**macOS / Linux**
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Open the URL Streamlit prints (usually http://localhost:8501). It starts in demo mode.

### Enable live Gemini mode
1. Create a free key in [Google AI Studio](https://aistudio.google.com/).
2. Either paste it in the sidebar, or copy `.streamlit/secrets.toml.example` to
   `.streamlit/secrets.toml` and fill in `GEMINI_API_KEY` (never commit that file).
3. Optional: set `GEMINI_MODEL` (default `gemini-2.5-flash`). If you get a "model not found"
   message, use a model name currently listed in AI Studio.

Key priority: sidebar > `st.secrets` > `GEMINI_API_KEY` environment variable.

## Deploy on Streamlit Community Cloud

1. Push this folder to a new GitHub repo (check `git status`: no `.env` or `secrets.toml`).
2. Go to [share.streamlit.io](https://share.streamlit.io), click **New app**, choose the repo,
   branch `main`, main file `app.py`.
3. **Advanced settings:** pick **Python 3.11, 3.12 or 3.13**, and paste into *Secrets*:
   ```toml
   GEMINI_API_KEY = "your-key"
   GEMINI_MODEL = "gemini-2.5-flash"
   ```
4. Deploy, then open the app and check all four tabs. Without the secret it runs in demo mode.

## Tests

```bash
pytest -q
```
Covers valuation formulas, INR formatting edge cases, milestone boundaries, weather alerts, JSON
schemas, Gemini JSON parsing/retry/fallback (mocked), image validation, chat, Pollinations
fetching, and an end-to-end Streamlit smoke test (`streamlit.testing.v1.AppTest`) in demo mode.

## JSON contracts

`SafetyReport`
```json
{
  "safety_score": 68,
  "overall_status": "Needs Improvement",
  "ppe_detection": [{"item": "Safety helmet", "detected": true, "confidence": 0.93, "note": "Worn by all visible workers."}],
  "hazards": [{"hazard": "Worker near an unprotected edge", "severity": "High", "remedy": "Install edge protection and use a harness."}],
  "summary": "...",
  "source": "gemini"
}
```

`CrackReport`
```json
{
  "defect_type": "Settlement",
  "estimated_width_mm": 2.5,
  "severity_score": 58,
  "urgency": "Repair Soon",
  "root_causes": ["Differential foundation settlement"],
  "recommended_repairs": ["Epoxy injection", "Structural re-grouting"],
  "monitoring_advice": "...",
  "summary": "...",
  "source": "gemini"
}
```

## Valuation formulas

```
total_budget  = sqft x base_rate x tier_multiplier x finish_multiplier
capex         = total_budget x completion%
valuation     = sqft x market_rate x structure_multiplier x (0.30 + 0.70 x completion%)
cement_bags   = sqft x 0.40        steel_kg = sqft x 4.0
```
All rates live in `modules/config.py` and are illustrative.

## Assumptions

- Python 3.11+ (pinned dependency versions require it).
- Rates and thumb rules (cement, steel, market rates) are illustrative, not quotations or appraisals.
- Weather is chosen by the user; live weather is not fetched.
- Pollinations is a free third-party service and can be slow or unavailable; the app degrades gracefully.
- Uploaded images are sent to Google Gemini only in live mode; avoid uploading confidential site imagery.

## Limitations

- Photo-based crack width and PPE detection are estimates and can miss or misjudge items.
- No user accounts, persistent storage or audit log.
- Not a substitute for site engineers, certified inspections or approved project documents.
