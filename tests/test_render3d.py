"""Tests for the Pollinations prompt builder and fetcher."""
import pytest
import requests

from modules import render3d


class FakeResponse:
    def __init__(self, content=b"img", content_type="image/jpeg", status=200):
        self.content = content
        self.headers = {"Content-Type": content_type}
        self._status = status

    def raise_for_status(self):
        if self._status >= 400:
            raise requests.HTTPError(str(self._status))


def test_prompt_mentions_inputs():
    prompt = render3d.build_prompt("Commercial", "Tier 1", "Premium")
    assert "commercial" in prompt.lower() and "metropolitan" in prompt and "premium" in prompt.lower()


def test_url_is_encoded_and_has_params():
    url = render3d.pollinations_url("a house & garden / modern")
    assert url.startswith("https://image.pollinations.ai/prompt/")
    assert " " not in url and "&" not in url.split("?")[0] and "/" not in url.split("prompt/")[1].split("?")[0]
    assert url.endswith("?width=1024&height=768&nologo=true")


def test_fetch_success(monkeypatch):
    monkeypatch.setattr(render3d.requests, "get", lambda *a, **k: FakeResponse(b"bytes"))
    assert render3d.fetch_render("a house") == b"bytes"


def test_fetch_errors(monkeypatch):
    with pytest.raises(ValueError):
        render3d.fetch_render("   ")
    monkeypatch.setattr(render3d.requests, "get", lambda *a, **k: FakeResponse(status=500))
    with pytest.raises(RuntimeError):
        render3d.fetch_render("a house")
    monkeypatch.setattr(render3d.requests, "get", lambda *a, **k: FakeResponse(content_type="text/html"))
    with pytest.raises(RuntimeError):
        render3d.fetch_render("a house")

    def timeout(*a, **k):
        raise requests.Timeout("slow")

    monkeypatch.setattr(render3d.requests, "get", timeout)
    with pytest.raises(RuntimeError):
        render3d.fetch_render("a house")
