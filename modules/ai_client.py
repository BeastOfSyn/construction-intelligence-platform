"""Gemini wrapper with strict JSON handling, one retry, and graceful demo fallback.

The app never shows a raw traceback: every failure path ends in a demo/fallback
result plus a short, human-readable warning.
"""
from __future__ import annotations

import io
import json
import os
import re
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Sequence, Tuple, Type, TypeVar, Union

from PIL import Image, ImageOps
from pydantic import BaseModel, ValidationError

from . import config as C

Part = Union[str, bytes]
Turn = Tuple[str, List[Part]]  # (role "user"|"model", parts)
T = TypeVar("T", bound=BaseModel)


class ImageError(ValueError):
    """Raised when an uploaded image is empty, oversized, corrupt or unsupported."""


@dataclass
class AIResult:
    """A validated report plus any user-facing warnings."""

    report: BaseModel
    warnings: List[str] = field(default_factory=list)


@dataclass
class ChatResult:
    """A chat reply, where it came from, and any warnings."""

    text: str
    source: str
    warnings: List[str] = field(default_factory=list)


# ---------------------------------------------------------------- helpers
def prepare_image(data: bytes) -> bytes:
    """Validate an image and return a Gemini-friendly JPEG.

    The image is checked with Pillow, converted to RGB (transparency flattened onto
    white), auto-rotated from EXIF, and resized so the longest side is at most
    ``MAX_IMAGE_SIDE`` pixels.

    Raises:
        ImageError: for empty, oversized, corrupt or non JPEG/PNG files.
    """
    if not data:
        raise ImageError("The uploaded file is empty.")
    if len(data) > C.MAX_UPLOAD_BYTES:
        raise ImageError(f"Image is larger than the {C.MAX_UPLOAD_MB} MB limit.")
    try:
        img = Image.open(io.BytesIO(data))
        img.load()
    except (OSError, ValueError, Image.DecompressionBombError) as exc:
        raise ImageError("Could not read this file as an image. Try another JPG or PNG.") from exc
    if img.format not in ("JPEG", "PNG"):
        raise ImageError("Unsupported image format. Please upload a JPG or PNG.")
    img = ImageOps.exif_transpose(img)
    if img.mode in ("RGBA", "LA", "P"):
        rgba = img.convert("RGBA")
        background = Image.new("RGB", rgba.size, (255, 255, 255))
        background.paste(rgba, mask=rgba.split()[-1])
        img = background
    else:
        img = img.convert("RGB")
    img.thumbnail((C.MAX_IMAGE_SIDE, C.MAX_IMAGE_SIDE))
    out = io.BytesIO()
    img.save(out, format="JPEG", quality=88)
    return out.getvalue()


_FENCE = re.compile(r"^```(?:json|JSON)?\s*|\s*```$", re.MULTILINE)


def extract_json(text: str) -> dict:
    """Parse a JSON object from model text, tolerating code fences and chatter.

    Raises:
        ValueError: if no valid JSON object can be found.
    """
    if not text or not text.strip():
        raise ValueError("Empty model response")
    cleaned = _FENCE.sub("", text.strip()).strip()
    try:
        value = json.loads(cleaned)
    except json.JSONDecodeError:
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start == -1 or end <= start:
            raise ValueError("No JSON object found in model response") from None
        try:
            value = json.loads(cleaned[start : end + 1])
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON in model response: {exc.msg}") from exc
    if not isinstance(value, dict):
        raise ValueError("Model response JSON is not an object")
    return value


def _secret(name: str) -> Optional[str]:
    """Read a value from st.secrets, then the environment; never raises."""
    try:
        import streamlit as st

        value = st.secrets.get(name)
        if value:
            return str(value).strip()
    except Exception:  # noqa: BLE001 - secrets file may not exist
        pass
    env = os.environ.get(name, "").strip()
    return env or None


def resolve_api_key(sidebar_key: Optional[str]) -> Optional[str]:
    """Return the API key by priority: sidebar > st.secrets > environment."""
    if sidebar_key and sidebar_key.strip():
        return sidebar_key.strip()
    return _secret("GEMINI_API_KEY")


def resolve_model() -> str:
    """Return the configured Gemini model name."""
    return _secret("GEMINI_MODEL") or C.DEFAULT_MODEL


def friendly_error(exc: BaseException) -> str:
    """Map an exception to a short message that never leaks keys or tracebacks."""
    text = str(exc).lower()
    if any(k in text for k in ("api key", "api_key", "permission_denied", "401", "403", "unauthenticated")):
        return "The Gemini API key was rejected. Check the key and try again."
    if any(k in text for k in ("429", "quota", "resource_exhausted", "rate limit")):
        return "Gemini quota or rate limit reached. Wait a moment and retry."
    if any(k in text for k in ("404", "not found", "model")):
        return "The configured Gemini model was not found. Set GEMINI_MODEL to a model listed in Google AI Studio."
    if any(k in text for k in ("timeout", "timed out", "connection", "network", "dns")):
        return "Could not reach Gemini (network problem or timeout)."
    if "safety" in text or "blocked" in text:
        return "Gemini blocked this request for safety reasons."
    return "The AI request failed."


_RETRY_TEMPLATE = (
    "Your previous reply could not be parsed or did not match the required JSON schema "
    "({error}).\nReturn ONLY the corrected JSON object, with no markdown and no commentary.\n\n"
    "Previous reply:\n{previous}\n\nOriginal task:\n{prompt}"
)


class AIClient:
    """Thin wrapper around Gemini that falls back to demo data when needed."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None) -> None:
        self.api_key = (api_key or "").strip() or None
        self.model = model or C.DEFAULT_MODEL

    @property
    def is_live(self) -> bool:
        """True when an API key is available."""
        return self.api_key is not None

    # ---- the only method that touches the network (mocked in tests) -----
    def _call_model(self, turns: Sequence[Turn], system: Optional[str], json_mode: bool) -> str:
        """Send ``turns`` to Gemini and return the response text."""
        from google import genai
        from google.genai import types

        client = genai.Client(
            api_key=self.api_key,
            http_options=types.HttpOptions(timeout=C.REQUEST_TIMEOUT_S * 1000),
        )
        contents = []
        for role, parts in turns:
            built = []
            for part in parts:
                if isinstance(part, bytes):
                    built.append(types.Part.from_bytes(data=part, mime_type="image/jpeg"))
                else:
                    built.append(types.Part.from_text(text=part))
            contents.append(types.Content(role=role, parts=built))
        config = types.GenerateContentConfig(
            system_instruction=system,
            response_mime_type="application/json" if json_mode else None,
            temperature=0.2 if json_mode else 0.5,
        )
        response = client.models.generate_content(model=self.model, contents=contents, config=config)
        text = getattr(response, "text", None)
        if not text:
            raise RuntimeError("Gemini returned an empty or blocked response")
        return text

    # ---- structured (JSON) generation -----------------------------------
    def generate_structured(
        self,
        prompt: str,
        image_bytes: Optional[bytes],
        model_cls: Type[T],
        demo_factory: Callable[[], T],
        system: Optional[str] = None,
    ) -> AIResult:
        """Run a structured request and return a validated report.

        Order of fallbacks: Gemini -> one JSON-fix retry -> demo data flagged
        ``source="fallback"``. Without an API key, demo data is returned directly.
        """
        if not self.is_live:
            demo = demo_factory()
            return AIResult(demo.model_copy(update={"source": "demo"}), [C.DEMO_NOTICE])

        parts: List[Part] = [prompt]
        if image_bytes:
            parts = [image_bytes, prompt]
        warnings: List[str] = []
        raw = ""
        try:
            raw = self._call_model([("user", parts)], system, True)
            return AIResult(self._validate(raw, model_cls), warnings)
        except (ValueError, ValidationError) as first_error:
            retry_prompt = _RETRY_TEMPLATE.format(
                error=str(first_error).splitlines()[0][:200], previous=raw[:4000], prompt=prompt
            )
            retry_parts: List[Part] = [image_bytes, retry_prompt] if image_bytes else [retry_prompt]
            try:
                raw = self._call_model([("user", retry_parts)], system, True)
                return AIResult(self._validate(raw, model_cls), warnings)
            except (ValueError, ValidationError):
                warnings.append("The AI returned malformed output twice; showing sample data instead.")
            except Exception as exc:  # noqa: BLE001
                warnings.append(f"{friendly_error(exc)} Showing sample data instead.")
        except Exception as exc:  # noqa: BLE001 - network/auth/quota/etc.
            warnings.append(f"{friendly_error(exc)} Showing sample data instead.")

        fallback = demo_factory().model_copy(update={"source": "fallback"})
        return AIResult(fallback, warnings)

    @staticmethod
    def _validate(raw: str, model_cls: Type[T]) -> T:
        """Parse and validate ``raw`` into ``model_cls`` with source='gemini'."""
        data: Dict = extract_json(raw)
        data.pop("source", None)
        report = model_cls.model_validate(data)
        return report.model_copy(update={"source": "gemini"})

    # ---- chat -------------------------------------------------------------
    def chat(
        self,
        history: Sequence[Dict[str, str]],
        message: str,
        system_prompt: str,
        demo_reply: Callable[[str], str],
    ) -> ChatResult:
        """Answer ``message`` using the last turns of ``history`` as context."""
        if not self.is_live:
            return ChatResult(demo_reply(message), "demo", [])
        recent = list(history)[-C.CHAT_HISTORY_TURNS * 2 :]
        turns: List[Turn] = []
        for item in recent:
            role = "model" if item.get("role") == "assistant" else "user"
            content = str(item.get("content", "")).strip()
            if content:
                turns.append((role, [content]))
        turns.append(("user", [message]))
        try:
            text = self._call_model(turns, system_prompt, False)
            return ChatResult(text.strip(), "gemini", [])
        except Exception as exc:  # noqa: BLE001
            return ChatResult(
                demo_reply(message), "fallback", [f"{friendly_error(exc)} Showing a sample answer instead."]
            )
