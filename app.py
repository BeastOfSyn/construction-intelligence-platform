"""Multimodal Construction Intelligence Platform - Streamlit entry point.

Run locally:  streamlit run app.py
Works with no API key (demo mode) or with a Google Gemini key (live mode).
"""
from __future__ import annotations

import html
import sys
from pathlib import Path
from typing import List, Optional, Sequence

sys.path.insert(0, str(Path(__file__).resolve().parent))

import streamlit as st  # noqa: E402

from modules import chat as chat_mod  # noqa: E402
from modules import config as C  # noqa: E402
from modules import cracks, render3d, safety, weather  # noqa: E402
from modules import valuation as V  # noqa: E402
from modules.ai_client import (  # noqa: E402
    AIClient,
    AIResult,
    ImageError,
    prepare_image,
    resolve_api_key,
    resolve_model,
)
from modules.schemas import CrackReport, SafetyReport, safety_metrics, to_json  # noqa: E402

st.set_page_config(page_title=C.APP_TITLE, page_icon="\U0001f3d7️", layout="wide")

CSS = """
<style>
.mcip-header{background:linear-gradient(135deg,#0f766e,#1d4ed8);color:#fff;padding:1.2rem 1.5rem;
  border-radius:14px;margin-bottom:1rem}
.mcip-title{font-size:1.7rem;font-weight:800;line-height:1.2;color:#fff}
.mcip-sub{margin-top:.3rem;opacity:.92;color:#fff}
.mcip-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:.8rem;margin:.6rem 0 1rem}
.mcip-card{border:1px solid rgba(128,128,128,.28);background:rgba(128,128,128,.08);border-radius:12px;
  padding:.8rem 1rem}
.mcip-label{font-size:.76rem;text-transform:uppercase;letter-spacing:.05em;opacity:.7}
.mcip-value{font-size:1.5rem;font-weight:700;line-height:1.3;margin-top:.15rem}
.mcip-subtext{font-size:.8rem;opacity:.7;margin-top:.1rem}
.mcip-pill{display:inline-block;padding:.12rem .7rem;border-radius:999px;color:#fff;font-weight:600;
  font-size:.85rem;white-space:nowrap}
.mcip-badge{display:inline-block;padding:.08rem .55rem;border-radius:6px;font-size:.75rem;font-weight:600;
  border:1px solid rgba(128,128,128,.4);opacity:.9}
.mcip-table{width:100%;border-collapse:collapse;margin:.4rem 0 1rem}
.mcip-table th,.mcip-table td{border-bottom:1px solid rgba(128,128,128,.25);padding:.5rem .6rem;
  text-align:left;vertical-align:top}
.mcip-table th{font-size:.76rem;text-transform:uppercase;letter-spacing:.04em;opacity:.7}
</style>
"""

ARCHITECTURE = """\
Streamlit UI (app.py)
 |- Tab 1 Safety     -> modules/safety.py --\\
 |- Tab 2 Cracks     -> modules/cracks.py ---+-> modules/ai_client.py -> Gemini (multimodal)
 |- Tab 4 Assistant  -> modules/chat.py  --/    (demo / fallback data if no key or on error)
 |- Tab 3 Valuation  -> modules/valuation.py   (pure Python, deterministic)
 |                   -> modules/render3d.py -> Pollinations AI
 '- Tab 4 Weather    -> modules/weather.py     (static advisories)
All AI output is validated with Pydantic JSON contracts (modules/schemas.py)."""


# ------------------------------------------------------------------ html helpers
def esc(value: object) -> str:
    """HTML-escape any value."""
    return html.escape(str(value))


def pill(text: str, color: str) -> str:
    """Return a colored pill."""
    return f'<span class="mcip-pill" style="background:{color}">{esc(text)}</span>'


def metric_card(label: str, value_html: str, sub: str = "") -> str:
    """Return one metric card; ``value_html`` must already be safe HTML."""
    sub_html = f'<div class="mcip-subtext">{esc(sub)}</div>' if sub else ""
    return (
        f'<div class="mcip-card"><div class="mcip-label">{esc(label)}</div>'
        f'<div class="mcip-value">{value_html}</div>{sub_html}</div>'
    )


def render_cards(cards: Sequence[str]) -> None:
    """Render a responsive grid of metric cards."""
    st.markdown(f'<div class="mcip-grid">{"".join(cards)}</div>', unsafe_allow_html=True)


def html_table(headers: Sequence[str], rows: Sequence[Sequence[str]]) -> None:
    """Render a table; each cell must already be safe HTML."""
    head = "".join(f"<th>{esc(h)}</th>" for h in headers)
    body = "".join("<tr>" + "".join(f"<td>{cell}</td>" for cell in row) + "</tr>" for row in rows)
    st.markdown(
        f'<table class="mcip-table"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>',
        unsafe_allow_html=True,
    )


def source_badge(source: str) -> str:
    """Return a small badge describing where a result came from."""
    labels = {"gemini": "Source: Gemini AI", "demo": "Source: demo data", "fallback": "Source: fallback sample data"}
    return f'<span class="mcip-badge">{esc(labels.get(source, source))}</span>'


def show_notices(result: AIResult) -> None:
    """Show demo notice or warnings for a result."""
    if result.report.source == "demo":
        st.info(C.DEMO_NOTICE)
    for warning in result.warnings:
        if result.report.source != "demo":
            st.warning(warning)


# ------------------------------------------------------------------ layout blocks
def render_header() -> None:
    """Render CSS and the gradient page header."""
    st.markdown(CSS, unsafe_allow_html=True)
    st.markdown(
        f'<div class="mcip-header"><div class="mcip-title">{esc(C.APP_TITLE)}</div>'
        f'<div class="mcip-sub">{esc(C.APP_SUBTITLE)}</div></div>',
        unsafe_allow_html=True,
    )


def render_sidebar() -> AIClient:
    """Render the sidebar and return a configured AI client."""
    with st.sidebar:
        st.markdown("### Control panel")
        key_input = st.text_input(
            "Google Gemini API key",
            type="password",
            key="gemini_api_key",
            placeholder="Paste key, or leave blank for demo mode",
            help="Your key stays in this browser session and is never stored by the app.",
        )
        client = AIClient(resolve_api_key(key_input), resolve_model())
        if client.is_live:
            st.markdown(pill("Live AI", "#16a34a"), unsafe_allow_html=True)
        else:
            st.markdown(pill("Demo Mode", "#d97706"), unsafe_allow_html=True)
            st.caption(C.DEMO_NOTICE)
        with st.expander("Architecture overview"):
            st.code(ARCHITECTURE, language="text")
        st.markdown(
            "**Features**\n"
            "1. Site Safety & PPE Audit\n"
            "2. Crack Diagnostics\n"
            "3. Planning & Real Estate Valuation\n"
            "4. Site Assistant & Weather Advisory"
        )
        st.caption(C.DISCLAIMER)
    return client


def prepare_upload(uploaded: Optional[object]) -> Optional[bytes]:
    """Validate an uploaded file; show a friendly error and return None on failure."""
    if uploaded is None:
        return None
    try:
        return prepare_image(uploaded.getvalue())  # type: ignore[attr-defined]
    except ImageError as exc:
        st.error(str(exc))
        return None


# --------------------------------------------------------------------- Tab 1
def render_safety_report(report: SafetyReport) -> None:
    """Render the PPE / safety audit results."""
    metrics = safety_metrics(report)
    status_color = C.STATUS_COLORS.get(report.overall_status, "#6b7280")
    render_cards(
        [
            metric_card("Safety score", f"{report.safety_score}/100"),
            metric_card("Overall status", pill(report.overall_status, status_color)),
            metric_card("Hazards identified", str(metrics["hazards"])),
            metric_card("PPE items missing", str(metrics["ppe_missing"])),
        ]
    )
    st.progress(report.safety_score / 100, text=f"Safety score {report.safety_score}/100")
    st.markdown(source_badge(report.source), unsafe_allow_html=True)

    st.markdown("##### PPE checklist")
    rows: List[List[str]] = []
    for item in report.ppe_detection:
        status = pill("Detected", "#16a34a") if item.detected else pill("Missing", "#dc2626")
        rows.append([esc(item.item), status, f"{item.confidence:.0%}", esc(item.note)])
    html_table(["Item", "Status", "Confidence", "Note"], rows)

    st.markdown("##### Identified hazards")
    if report.hazards:
        hazard_rows = [
            [esc(h.hazard), pill(h.severity, C.SEVERITY_COLORS.get(h.severity, "#6b7280")), esc(h.remedy)]
            for h in report.hazards
        ]
        html_table(["Hazard", "Severity", "Corrective remedy"], hazard_rows)
    else:
        st.success("No hazards identified in this image.")
    if report.summary:
        st.markdown("##### Summary")
        st.write(report.summary)
    st.download_button(
        "Download JSON report",
        data=to_json(report),
        file_name="safety_report.json",
        mime="application/json",
        key="safety_download",
    )


def render_safety_tab(client: AIClient) -> None:
    """Tab 1: site safety and PPE audit."""
    st.subheader("Site Safety & PPE Audit")
    st.caption("Upload a construction site photo to audit worker PPE and spot hazards (OSHA / IS 456 / IS 3764 / IS 7969).")
    uploaded = st.file_uploader(
        f"Site photo (JPG or PNG, max {C.MAX_UPLOAD_MB} MB)", type=C.ALLOWED_IMAGE_TYPES, key="safety_upload"
    )
    image = prepare_upload(uploaded)
    if uploaded is not None and image is not None:
        st.image(uploaded.getvalue(), caption=uploaded.name)
    if st.button("Run PPE Audit", type="primary", key="safety_run"):
        if image is None:
            st.warning("Please upload a valid site photo first.")
        else:
            with st.spinner("Auditing site photo..."):
                result = safety.run_ppe_audit(client, image)
            st.session_state["safety_result"] = {"result": result, "name": uploaded.name if uploaded else ""}
    saved = st.session_state.get("safety_result")
    if saved:
        st.divider()
        if saved["name"]:
            st.caption(f"Results for: {saved['name']}")
        show_notices(saved["result"])
        render_safety_report(saved["result"].report)


# --------------------------------------------------------------------- Tab 2
def render_crack_report(report: CrackReport) -> None:
    """Render the crack diagnostics results."""
    urgency_color = C.URGENCY_COLORS.get(report.urgency, "#6b7280")
    render_cards(
        [
            metric_card("Defect type", esc(report.defect_type)),
            metric_card("Estimated width", f"{report.estimated_width_mm:.1f} mm"),
            metric_card("Severity score", f"{report.severity_score}/100"),
            metric_card("Urgency", pill(report.urgency, urgency_color)),
        ]
    )
    st.progress(report.severity_score / 100, text=f"Severity {report.severity_score}/100")
    st.markdown(source_badge(report.source), unsafe_allow_html=True)
    left, right = st.columns(2)
    with left:
        st.markdown("##### Likely root causes")
        for cause in report.root_causes:
            st.markdown(f"- {cause}")
    with right:
        st.markdown("##### Recommended repairs")
        for repair in report.recommended_repairs:
            st.markdown(f"- {repair}")
    if report.monitoring_advice:
        st.markdown("##### Monitoring advice")
        st.write(report.monitoring_advice)
    if report.summary:
        st.markdown("##### Summary")
        st.write(report.summary)
    st.warning("Photo-based estimate only; consult a licensed structural engineer.")
    st.download_button(
        "Download JSON report",
        data=to_json(report),
        file_name="crack_report.json",
        mime="application/json",
        key="crack_download",
    )


def render_crack_tab(client: AIClient) -> None:
    """Tab 2: crack diagnostics and structural integrity."""
    st.subheader("Crack Diagnostics & Structural Integrity")
    st.caption("Upload a close-up of a concrete or wall surface to classify the defect and get repair guidance.")
    uploaded = st.file_uploader(
        f"Surface photo (JPG or PNG, max {C.MAX_UPLOAD_MB} MB)", type=C.ALLOWED_IMAGE_TYPES, key="crack_upload"
    )
    image = prepare_upload(uploaded)
    if uploaded is not None and image is not None:
        st.image(uploaded.getvalue(), caption=uploaded.name)
    if st.button("Diagnose Crack", type="primary", key="crack_run"):
        if image is None:
            st.warning("Please upload a valid surface photo first.")
        else:
            with st.spinner("Analyzing surface..."):
                result = cracks.run_crack_analysis(client, image)
            st.session_state["crack_result"] = {"result": result, "name": uploaded.name if uploaded else ""}
    saved = st.session_state.get("crack_result")
    if saved:
        st.divider()
        if saved["name"]:
            st.caption(f"Results for: {saved['name']}")
        show_notices(saved["result"])
        render_crack_report(saved["result"].report)


# --------------------------------------------------------------------- Tab 3
def render_render_section(structure: str, tier: str, finish: str) -> None:
    """Conceptual 3D render via Pollinations AI."""
    st.markdown("##### Conceptual 3D architectural render")
    default_prompt = render3d.build_prompt(structure, tier, finish)
    if st.session_state.get("_render_default") != default_prompt:
        st.session_state["_render_default"] = default_prompt
        st.session_state["render_prompt"] = default_prompt
    prompt = st.text_area("Render prompt (editable)", key="render_prompt", height=100)
    if st.button("Generate Concept Render", key="render_btn"):
        try:
            with st.spinner("Generating concept render (can take up to a minute)..."):
                st.session_state["render_bytes"] = render3d.fetch_render(prompt)
        except (ValueError, RuntimeError) as exc:
            st.session_state.pop("render_bytes", None)
            st.error(f"{exc} You can paste this link into a browser instead:")
            st.code(render3d.pollinations_url(prompt or default_prompt), language="text")
    if st.session_state.get("render_bytes"):
        st.image(st.session_state["render_bytes"], caption="AI concept render (illustrative only)")


def render_valuation_tab() -> None:
    """Tab 3: planning, costs and real estate valuation."""
    st.subheader("Planning & Real Estate Valuation")
    st.caption("Enter project details to estimate budget, spend to date, asset value and materials in INR.")
    col_a, col_b = st.columns(2)
    with col_a:
        structure = st.selectbox("Structure type", C.STRUCTURE_TYPES, key="val_structure")
        sqft = st.number_input(
            "Built-up area (sq ft)", min_value=C.MIN_SQFT, max_value=C.MAX_SQFT, value=1200, step=50, key="val_sqft"
        )
        finish = st.selectbox("Finish level", C.FINISH_LEVELS, index=1, key="val_finish")
    with col_b:
        tier = st.selectbox("Location tier", C.LOCATION_TIERS, index=1, key="val_tier")
        completion = st.slider("Completion (%)", 0, 100, 40, key="val_completion")
    try:
        result = V.compute_valuation(structure, float(sqft), tier, float(completion), finish)
    except ValueError as exc:
        st.error(str(exc))
        return
    render_cards(
        [
            metric_card("Total project budget", esc(V.format_inr(result.total_budget))),
            metric_card("Capex incurred", esc(V.format_inr(result.capex_incurred)), f"{result.completion:.0f}% of budget"),
            metric_card(
                "Current asset valuation",
                esc(V.format_inr(result.current_valuation)),
                f"At completion: {V.format_inr(result.market_value_full)}",
            ),
            metric_card(
                "Cement required",
                f"{result.cement_bags_total:,.0f} bags",
                f"{result.cement_bags_remaining:,.0f} bags remaining",
            ),
            metric_card(
                "Steel required",
                f"{result.steel_kg_total:,.0f} kg",
                f"{result.steel_kg_remaining:,.0f} kg remaining",
            ),
        ]
    )
    st.progress(result.completion / 100, text=f"{result.completion:.0f}% complete - current stage: {result.milestone}")
    status_colors = {"Done": "#16a34a", "In progress": "#d97706", "Pending": "#6b7280"}
    html_table(
        ["Milestone", "Range", "Status"],
        [
            [esc(row["Milestone"]), esc(row["Range"]), pill(row["Status"], status_colors[row["Status"]])]
            for row in V.milestone_table(result.completion)
        ],
    )
    st.caption(C.VALUATION_NOTE)
    st.divider()
    render_render_section(structure, tier, finish)


# --------------------------------------------------------------------- Tab 4
def _clear_chat() -> None:
    """Callback: reset the conversation."""
    st.session_state["chat_history"] = []
    st.session_state.pop("chat_notice", None)


def render_assistant_tab(client: AIClient) -> None:
    """Tab 4: weather advisory and construction assistant."""
    st.subheader("Daily Site Assistant & Weather Advisory")
    condition = st.radio("Today's weather condition", weather.list_conditions(), horizontal=True, key="weather_choice")
    alert = weather.get_alert(condition)
    body = f"**{alert['headline']}**\n\n" + "\n".join(f"- {a}" for a in alert["actions"])  # type: ignore[union-attr]
    {"error": st.error, "warning": st.warning, "success": st.success}[str(alert["level"])](body)

    st.divider()
    head_col, clear_col = st.columns([5, 1])
    head_col.markdown("##### Construction engineering assistant")
    clear_col.button("Clear chat", on_click=_clear_chat, key="chat_clear")
    if not client.is_live:
        st.caption("Demo mode: keyword-based sample answers. Add a Gemini key in the sidebar for full AI answers.")

    history = st.session_state.setdefault("chat_history", [])
    message = st.chat_input("Ask a construction engineering question...", key="chat_box")
    if message is not None:
        message = message.strip()
        if not message:
            st.warning("Please type a question first.")
        else:
            with st.spinner("Thinking..."):
                reply = chat_mod.get_reply(client, history, message)
            history.append({"role": "user", "content": message})
            history.append({"role": "assistant", "content": reply.text, "source": reply.source})
            st.session_state["chat_notice"] = reply.warnings
    for notice in st.session_state.get("chat_notice", []):
        st.warning(notice)
    for item in history:
        with st.chat_message(item["role"]):
            st.markdown(item["content"])
            if item["role"] == "assistant" and item.get("source") == "demo":
                st.caption("Demo answer")


# ----------------------------------------------------------------------- main
def main() -> None:
    """Assemble the page."""
    render_header()
    client = render_sidebar()
    tabs = st.tabs(
        ["Site Safety & PPE", "Crack Diagnostics", "Planning & Valuation", "Site Assistant & Weather"]
    )
    with tabs[0]:
        render_safety_tab(client)
    with tabs[1]:
        render_crack_tab(client)
    with tabs[2]:
        render_valuation_tab()
    with tabs[3]:
        render_assistant_tab(client)
    st.caption(C.DISCLAIMER)


main()
