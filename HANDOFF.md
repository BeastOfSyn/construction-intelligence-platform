# HANDOFF — Multimodal Construction Intelligence Platform

Use this file to resume/finish the project in ANY place (new Claude chat, Antigravity,
Cursor, Codespaces, plain VS Code). It contains the full spec, a progress tracker,
and exact commands. Update the tracker as you go.

---------------------------------------------------------------------------
## 0. TL;DR RESUME STEPS

1. Open this folder (`mcip/`) in your tool of choice.
2. Read section 2 (Progress Tracker). Anything unchecked = not done.
3. Paste this to the AI agent:
   > Read HANDOFF.md fully. Finish every unchecked item in the Progress Tracker,
   > following the Spec in section 3 exactly. Do not ask me questions. When done,
   > run the commands in section 5 until everything passes, then tick the tracker.
4. Verify with section 5 commands.
5. Deploy with section 6.

---------------------------------------------------------------------------
## 1. PROJECT

Name: Multimodal Construction Intelligence Platform (Skill Wallet Capstone Project 1)
Stack: Python 3.9+, Streamlit, Google Gemini (google-genai SDK), Pillow, Pydantic v2,
requests, pytest. No database. No runtime file writes. One-click deploy on
Streamlit Community Cloud.

Works in two modes:
- DEMO MODE (no API key): canned realistic JSON. Image pixels are NOT analysed.
- LIVE MODE (Gemini key): real multimodal analysis + chatbot.

---------------------------------------------------------------------------
## 2. PROGRESS TRACKER (tick when done)

- [x] HANDOFF.md written
- [x] modules/config.py
- [x] modules/schemas.py
- [x] modules/valuation.py
- [x] modules/weather.py
- [x] modules/ai_client.py
- [x] modules/safety.py
- [x] modules/cracks.py
- [x] modules/chat.py
- [x] modules/render3d.py
- [x] app.py (sidebar + 4 tabs + CSS)
- [x] tests/test_valuation.py
- [x] tests/test_schemas.py
- [x] tests/test_ai_client.py
- [x] tests/test_app_smoke.py
- [x] requirements.txt pinned
- [x] .streamlit/config.toml + secrets.toml.example
- [x] .gitignore
- [x] README.md
- [x] pytest -q all green
- [x] streamlit boots headless without errors
- [x] zip built and sent to user

---------------------------------------------------------------------------
## 3. FULL SPEC (source of truth)

### File structure
```
app.py
modules/__init__.py
modules/config.py        constants, rate tables, weather alerts, disclaimers
modules/ai_client.py     Gemini wrapper, JSON parsing, retries, demo fallback
modules/schemas.py       Pydantic models (JSON contracts)
modules/safety.py        PPE audit logic + demo data
modules/cracks.py        crack diagnostics logic + demo data
modules/valuation.py     budget, capex, valuation, materials, milestones, INR format
modules/weather.py       weather alerts
modules/chat.py          multi-turn assistant + demo replies
modules/render3d.py      Pollinations prompt builder + URL
tests/ (4 files)
requirements.txt  .streamlit/config.toml  .streamlit/secrets.toml.example
.gitignore  README.md  pytest.ini
```

### AI client rules
- Official `google-genai` SDK. Model from env/secrets GEMINI_MODEL, default
  `gemini-2.5-flash`. Never hardcode keys.
- Key priority: sidebar input > st.secrets["GEMINI_API_KEY"] > env GEMINI_API_KEY.
  None -> DEMO MODE.
- Images: validate with Pillow, convert RGB, longest side <= 1600px, re-encode JPEG.
- Ask for JSON only (`response_mime_type="application/json"`). Strip code fences,
  json.loads, validate with Pydantic. On failure retry ONCE with a "fix your JSON"
  prompt; if still failing -> demo response flagged `source: "fallback"` + st.warning.
- Every API call in try/except. App NEVER shows a raw traceback.
- Every result carries `source`: "gemini" | "demo" | "fallback"; UI shows a badge.
- Demo mode must say: "Demo mode does not analyze image pixels."

### Sidebar
Title + description; password input for Gemini key + status pill (Live AI / Demo Mode);
architecture overview (expander); feature navigation list; safety disclaimer.

### Tab 1 — Site Safety & PPE Audit
Uploader jpg/jpeg/png <= 8 MB, preview, "Run PPE Audit" button.
Audit helmet, high-vis vest, steel-toe boots, safety harness, gloves, eye protection
vs OSHA + IS 456 / IS 3764 / IS 7969.
SafetyReport JSON:
```
{ "safety_score": int 0-100,
  "overall_status": "Compliant"|"Needs Improvement"|"Non-Compliant"|"Critical",
  "ppe_detection": [{"item": str, "detected": bool, "confidence": 0-1, "note": str}],
  "hazards": [{"hazard": str, "severity": "Low"|"Medium"|"High"|"Critical", "remedy": str}],
  "summary": str, "source": str }
```
Render: metric cards (score, status, #hazards, #PPE missing), status pill, PPE table,
hazard table with severity badges, summary, JSON download button.

### Tab 2 — Crack Diagnostics
CrackReport JSON:
```
{ "defect_type": "Hairline"|"Settlement"|"Structural Shear"|"Thermal Expansion"|"Spalling",
  "estimated_width_mm": float, "severity_score": int 0-100,
  "urgency": "Monitor"|"Repair Soon"|"Urgent"|"Immediate",
  "root_causes": [str], "recommended_repairs": [str],
  "monitoring_advice": str, "summary": str, "source": str }
```
Metric cards, st.progress severity gauge, urgency pill, lists, JSON download, caution
"Photo-based estimate only; consult a licensed structural engineer."

### Tab 3 — Planning & Valuation (pure Python, deterministic)
Inputs: structure type, built-up sqft (200-500000), tier (1/2/3), completion %,
finish (Basic/Standard/Premium).
```
base_rate = {"Residential Apartment":1800,"Independent House/Villa":2200,"Commercial":2600,"Industrial":2000}
tier_cost = {"Tier 1":1.25,"Tier 2":1.0,"Tier 3":0.85}
finish    = {"Basic":0.9,"Standard":1.0,"Premium":1.3}
market    = {"Tier 1":9500,"Tier 2":5500,"Tier 3":3200}
struct_mkt= {"Residential Apartment":1.0,"Independent House/Villa":1.15,"Commercial":1.3,"Industrial":0.8}
total_budget = sqft*base_rate*tier_cost*finish
capex        = total_budget*completion/100
market_full  = sqft*market*struct_mkt
valuation    = market_full*(0.30+0.70*completion/100)
cement_bags  = sqft*0.40 ; steel_kg = sqft*4.0 ; remaining = total*(1-completion/100)
```
Milestones: Foundation 0-15, Plinth 15-30, Superstructure 30-60, Finishing 60-85,
Handover 85-100 (start inclusive, end exclusive; 100 => Handover complete).
format_inr: < 1 Cr => "₹X.XX Lakhs"; >= 1 Cr => "₹X.XX Crores"
(rounding to 100.00 Lakhs must roll up to Crores).
3D render: Pollinations URL
`https://image.pollinations.ai/prompt/{encoded}?width=1024&height=768&nologo=true`,
editable prompt, button, graceful failure.
Note rates are illustrative, not a quotation.

### Tab 4 — Weather + Assistant
Radio: High Wind / Heavy Rain / Extreme Heat / Normal with severity-coloured alert
boxes and 4-6 actions each (crane suspension, electrical hazard mitigation, concrete
curing protocol, etc.). Multi-turn chatbot (st.chat_message/st.chat_input, history in
session_state, last 10 turns as context, Clear chat button). Demo mode keyword replies.

### UI
Wide layout, custom CSS (cards, pills, badges, gradient header), light+dark safe.
Badge colours: Low green, Medium amber, High orange, Critical red.
Escape all model text with html.escape before injecting into HTML.

### Quality
Type hints + docstrings, no TODOs, session_state for results, handle: no file, wrong
type, oversize, corrupt image, empty chat, API errors, invalid numbers.

---------------------------------------------------------------------------
## 4. IF YOU ARE A NEW AGENT TAKING OVER

1. `ls -R` the project; compare against the file structure above.
2. For each unchecked item in section 2 build it per spec.
3. Do not rewrite finished modules unless tests fail.
4. Keep `source` field + demo/fallback behaviour intact.

---------------------------------------------------------------------------
## 5. VERIFY

```bash
python -m venv .venv
# Windows: .\.venv\Scripts\Activate.ps1      Linux/Mac: source .venv/bin/activate
pip install -r requirements.txt
pytest -q
streamlit run app.py
```
Manual: demo mode works with no key; paste a real key in sidebar to test live mode.

---------------------------------------------------------------------------
## 6. DEPLOY (Streamlit Community Cloud)

1. `git init && git add . && git commit -m "init"` and push to a NEW GitHub repo.
   Make sure `.env` and `.streamlit/secrets.toml` are NOT committed.
2. https://share.streamlit.io -> New app -> pick repo/branch, main file `app.py`.
3. Advanced settings -> Secrets:
   ```
   GEMINI_API_KEY = "your-key"
   GEMINI_MODEL = "gemini-2.5-flash"
   ```
4. Deploy. If model 404s, set GEMINI_MODEL to a model listed in Google AI Studio.
5. Screenshot every tab for submission.

---------------------------------------------------------------------------
## 7. VERIFIED STATE
- All 22 checklist items done. `pytest -q`: 90 passed. Streamlit boots headless (health 200).
- Tested on Python 3.13. Pinned deps need Python >= 3.11 (streamlit 1.66.1, pillow 13.0.0).
- NOT tested with a real Gemini key (no key in the build environment). The request-building
  code is tested against the real SDK types with a fake client; do one live run yourself.

---------------------------------------------------------------------------
## 8. KNOWN RISKS
- Gemini may return malformed JSON -> retry + fallback implemented.
- Pollinations can be slow/down -> handled gracefully.
- Model names change over time -> configurable via GEMINI_MODEL.
