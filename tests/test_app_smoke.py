"""Smoke tests: load the whole Streamlit app in demo mode and poke the main controls."""
from pathlib import Path

import pytest
import requests
from streamlit.testing.v1 import AppTest

from modules import render3d

APP = str(Path(__file__).resolve().parents[1] / "app.py")


@pytest.fixture()
def app(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    return AppTest.from_file(APP, default_timeout=60).run()


def test_app_loads_with_four_tabs(app):
    assert not app.exception
    assert len(app.tabs) == 4
    assert any(("Demo Mode" in m.value) or ("Live AI" in m.value) for m in app.sidebar.markdown)


def test_run_audit_without_upload_warns(app):
    app.button(key="safety_run").click().run()
    assert not app.exception
    assert any("upload" in w.value.lower() for w in app.warning)


def test_crack_without_upload_warns(app):
    app.button(key="crack_run").click().run()
    assert not app.exception
    assert any("upload" in w.value.lower() for w in app.warning)


def test_valuation_inputs_update_without_error(app):
    app.slider(key="val_completion").set_value(100).run()
    assert not app.exception
    app.selectbox(key="val_tier").set_value("Tier 1").run()
    assert not app.exception
    app.selectbox(key="val_structure").set_value("Commercial").run()
    assert not app.exception
    app.number_input(key="val_sqft").set_value(5000).run()
    assert not app.exception


def test_weather_selection_changes_alert(app):
    app.radio(key="weather_choice").set_value("High Wind").run()
    assert not app.exception
    assert any("crane" in e.value.lower() for e in app.error)
    app.radio(key="weather_choice").set_value("Normal").run()
    assert any("normal conditions" in s.value.lower() for s in app.success)


def test_chat_round_trip_in_demo_mode(app):
    app.chat_input[0].set_value("How long should I cure concrete?").run()
    assert not app.exception
    assert len(app.chat_message) == 2
    app.button(key="chat_clear").click().run()
    assert len(app.chat_message) == 0


def test_render_failure_is_friendly(app, monkeypatch):
    def boom(*a, **k):
        raise requests.ConnectionError("offline")

    monkeypatch.setattr(render3d.requests, "get", boom)
    app.button(key="render_btn").click().run()
    assert not app.exception
    assert any("unavailable" in e.value.lower() for e in app.error)
