"""Tests for the AI client: JSON parsing, retry, fallback, images, chat."""
import io

import pytest
from PIL import Image

from modules import chat, cracks, safety
from modules import config as C
from modules.ai_client import (
    AIClient,
    ImageError,
    extract_json,
    friendly_error,
    prepare_image,
    resolve_api_key,
)
from modules.schemas import SafetyReport

VALID_JSON = safety.demo_report().model_dump_json()


def _png(size=(40, 30), mode="RGBA", fmt="PNG") -> bytes:
    buf = io.BytesIO()
    Image.new(mode, size, (200, 10, 10, 128) if mode == "RGBA" else (200, 10, 10)).save(buf, format=fmt)
    return buf.getvalue()


class Scripted(AIClient):
    """AIClient whose network call returns/raises scripted values."""

    def __init__(self, *outcomes, **kw):
        super().__init__(api_key="test-key", **kw)
        self.outcomes = list(outcomes)
        self.calls = []

    def _call_model(self, turns, system, json_mode):
        self.calls.append((list(turns), system, json_mode))
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


# ------------------------------------------------------------ extract_json
def test_extract_json_plain_and_fenced():
    assert extract_json('{"a": 1}') == {"a": 1}
    assert extract_json('```json\n{"a": 1}\n```') == {"a": 1}
    assert extract_json('```\n{"a": 1}\n```') == {"a": 1}


def test_extract_json_with_surrounding_text():
    assert extract_json('Sure! Here you go: {"a": {"b": 2}} Hope that helps.') == {"a": {"b": 2}}


@pytest.mark.parametrize("bad", ["", "   ", "no json here", "{not valid}", "[1, 2, 3]"])
def test_extract_json_failures(bad):
    with pytest.raises(ValueError):
        extract_json(bad)


# ------------------------------------------------------------ prepare_image
def test_prepare_image_converts_rgba_to_jpeg():
    out = prepare_image(_png())
    img = Image.open(io.BytesIO(out))
    assert img.format == "JPEG" and img.mode == "RGB"


def test_prepare_image_downsizes_large_images():
    out = prepare_image(_png(size=(3200, 1200), mode="RGB"))
    assert max(Image.open(io.BytesIO(out)).size) <= C.MAX_IMAGE_SIDE


def test_prepare_image_rejects_bad_input(monkeypatch):
    with pytest.raises(ImageError):
        prepare_image(b"")
    with pytest.raises(ImageError):
        prepare_image(b"definitely not an image")
    with pytest.raises(ImageError):
        prepare_image(_png(mode="RGB", fmt="GIF"))
    monkeypatch.setattr(C, "MAX_UPLOAD_BYTES", 10)
    with pytest.raises(ImageError):
        prepare_image(_png())


# ------------------------------------------------------------ structured calls
def test_demo_mode_without_key():
    result = AIClient(None).generate_structured("p", b"img", SafetyReport, safety.demo_report)
    assert result.report.source == "demo"
    assert any("pixels" in w for w in result.warnings)


def test_live_success_marks_source_gemini():
    client = Scripted(VALID_JSON)
    result = client.generate_structured("p", b"img", SafetyReport, safety.demo_report, system="sys")
    assert result.report.source == "gemini"
    assert result.warnings == []
    turns, system, json_mode = client.calls[0]
    assert system == "sys" and json_mode is True
    assert turns[0][0] == "user" and isinstance(turns[0][1][0], bytes)


def test_live_accepts_fenced_json():
    result = Scripted(f"```json\n{VALID_JSON}\n```").generate_structured("p", None, SafetyReport, safety.demo_report)
    assert result.report.source == "gemini"


def test_retry_after_malformed_json():
    client = Scripted("not json at all", VALID_JSON)
    result = client.generate_structured("p", b"img", SafetyReport, safety.demo_report)
    assert result.report.source == "gemini"
    assert len(client.calls) == 2
    retry_text = client.calls[1][0][0][1][-1]
    assert "corrected JSON" in retry_text


def test_retry_after_schema_violation():
    bad = '{"safety_score": 500, "overall_status": "Compliant", "ppe_detection": [], "hazards": []}'
    result = Scripted(bad, VALID_JSON).generate_structured("p", None, SafetyReport, safety.demo_report)
    assert result.report.source == "gemini"


def test_fallback_after_two_bad_responses():
    client = Scripted("garbage", "still garbage")
    result = client.generate_structured("p", None, SafetyReport, safety.demo_report)
    assert result.report.source == "fallback"
    assert result.warnings and "sample data" in result.warnings[0]
    assert len(client.calls) == 2


def test_api_error_falls_back_without_leaking_secrets():
    client = Scripted(RuntimeError("401 PERMISSION_DENIED: API key sk-SECRET-123 invalid"))
    result = client.generate_structured("p", b"img", SafetyReport, safety.demo_report)
    assert result.report.source == "fallback"
    assert "sk-SECRET-123" not in " ".join(result.warnings)
    assert "key" in result.warnings[0].lower()
    assert len(client.calls) == 1


def test_error_on_retry_call_falls_back():
    client = Scripted("garbage", TimeoutError("timed out"))
    result = client.generate_structured("p", None, SafetyReport, safety.demo_report)
    assert result.report.source == "fallback"


def test_run_helpers_in_demo_mode():
    assert safety.run_ppe_audit(AIClient(None), b"x").report.source == "demo"
    assert cracks.run_crack_analysis(AIClient(None), b"x").report.source == "demo"


# ------------------------------------------------------------ chat
def test_chat_demo_mode_uses_keywords():
    result = chat.get_reply(AIClient(None), [], "How long should I cure concrete?")
    assert result.source == "demo"
    assert "IS 456" in result.text


def test_chat_default_reply():
    assert "demo mode" in chat.demo_reply("zzz unrelated").lower()


def test_chat_live_trims_history_and_maps_roles():
    history = []
    for i in range(30):
        history.append({"role": "user" if i % 2 == 0 else "assistant", "content": f"m{i}"})
    client = Scripted("Live answer")
    result = chat.get_reply(client, history, "next question")
    assert result.source == "gemini" and result.text == "Live answer"
    turns, system, json_mode = client.calls[0]
    assert json_mode is False and "construction" in system.lower()
    assert len(turns) == C.CHAT_HISTORY_TURNS * 2 + 1
    assert turns[-1] == ("user", ["next question"])
    assert {role for role, _ in turns} == {"user", "model"}


def test_chat_error_falls_back():
    result = chat.get_reply(Scripted(RuntimeError("429 quota exceeded")), [], "scaffolding tips")
    assert result.source == "fallback"
    assert "quota" in result.warnings[0].lower()


# ------------------------------------------------------------ keys / errors
def test_resolve_api_key_priority(monkeypatch):
    import os
    import modules.ai_client as ai_mod

    # 1. sidebar key wins over st.secrets and env
    monkeypatch.setattr(ai_mod, "_secret", lambda name: "secret-key")
    monkeypatch.setenv("GEMINI_API_KEY", "env-key")
    assert resolve_api_key("  sidebar-key ") == "sidebar-key"

    # 2. st.secrets wins over env
    assert resolve_api_key("") == "secret-key"

    # 3. env wins when st.secrets has no key
    monkeypatch.setattr(ai_mod, "_secret", lambda name: os.environ.get(name))
    assert resolve_api_key("") == "env-key"

    # 4. None when neither is provided
    monkeypatch.delenv("GEMINI_API_KEY")
    assert resolve_api_key(None) is None


@pytest.mark.parametrize(
    "message,fragment",
    [
        ("403 PERMISSION_DENIED", "key"),
        ("429 RESOURCE_EXHAUSTED", "quota"),
        ("404 models/x is not found", "model"),
        ("connection timed out", "network"),
        ("something weird", "failed"),
    ],
)
def test_friendly_error(message, fragment):
    assert fragment in friendly_error(RuntimeError(message)).lower()


# ------------------------------------------------------------ real request building
def test_call_model_builds_valid_sdk_request(monkeypatch):
    """Exercise the real _call_model with a fake genai.Client to validate SDK types."""
    from google import genai

    captured = {}

    class FakeModels:
        def generate_content(self, model, contents, config):
            captured.update(model=model, contents=contents, config=config)

            class Resp:
                text = '{"ok": true}'

            return Resp()

    class FakeClient:
        def __init__(self, api_key=None, http_options=None):
            captured["api_key"] = api_key
            captured["timeout"] = http_options.timeout
            self.models = FakeModels()

    monkeypatch.setattr(genai, "Client", FakeClient)
    client = AIClient(api_key="k", model="gemini-test")
    text = client._call_model([("user", [b"\xff\xd8jpeg", "describe"]), ("model", ["ok"])], "sys", True)
    assert text == '{"ok": true}'
    assert captured["model"] == "gemini-test" and captured["api_key"] == "k"
    assert captured["timeout"] == C.REQUEST_TIMEOUT_S * 1000
    assert captured["config"].response_mime_type == "application/json"
    assert captured["config"].system_instruction == "sys"
    first, second = captured["contents"]
    assert first.role == "user" and first.parts[0].inline_data.mime_type == "image/jpeg"
    assert first.parts[1].text == "describe" and second.role == "model"


def test_call_model_empty_response_raises(monkeypatch):
    from google import genai

    class FakeModels:
        def generate_content(self, **kw):
            class Resp:
                text = None

            return Resp()

    class FakeClient:
        def __init__(self, **kw):
            self.models = FakeModels()

    monkeypatch.setattr(genai, "Client", FakeClient)
    with pytest.raises(RuntimeError):
        AIClient(api_key="k")._call_model([("user", ["hi"])], None, False)
