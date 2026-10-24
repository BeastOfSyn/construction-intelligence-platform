"""Pollinations AI prompt builder and image fetcher for conceptual renders."""
from __future__ import annotations

from urllib.parse import quote

import requests

BASE_URL = "https://image.pollinations.ai/prompt/"
WIDTH, HEIGHT = 1024, 768

_STYLE = {
    "Residential Apartment": "modern multi-storey residential apartment building with balconies",
    "Independent House/Villa": "contemporary independent villa with landscaped garden",
    "Commercial": "modern commercial office building with glass facade",
    "Industrial": "clean industrial warehouse and factory building",
}
_FINISH = {
    "Basic": "simple plaster and paint finish",
    "Standard": "quality facade with tasteful detailing",
    "Premium": "premium materials, stone cladding and designer lighting",
}
_TIER = {
    "Tier 1": "in a large metropolitan Indian city",
    "Tier 2": "in a growing Indian city",
    "Tier 3": "in a small Indian town",
}


def build_prompt(structure: str, tier: str, finish: str) -> str:
    """Build a descriptive text-to-image prompt for an architectural concept render."""
    return (
        f"Conceptual 3D architectural rendering of a {_STYLE.get(structure, structure)}, "
        f"{_FINISH.get(finish, finish)}, {_TIER.get(tier, '')}, "
        "daylight, photorealistic, wide angle, high detail"
    ).replace(" ,", ",")


def pollinations_url(prompt: str) -> str:
    """Return the Pollinations URL for ``prompt``."""
    return f"{BASE_URL}{quote(prompt.strip(), safe='')}?width={WIDTH}&height={HEIGHT}&nologo=true"


def fetch_render(prompt: str, timeout: float = 60.0) -> bytes:
    """Download the rendered image bytes.

    Raises:
        ValueError: for an empty prompt.
        RuntimeError: if the service is unreachable, slow, or returns a non-image.
    """
    if not prompt or not prompt.strip():
        raise ValueError("Enter a prompt first.")
    try:
        response = requests.get(pollinations_url(prompt), timeout=timeout)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise RuntimeError("The image service is unavailable or timed out.") from exc
    if not response.headers.get("Content-Type", "").startswith("image/"):
        raise RuntimeError("The image service did not return an image.")
    return response.content
