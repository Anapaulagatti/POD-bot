"""Honest, editable SEO drafts. Gemini is opt-in; rules work offline."""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass

from podbot.api_limits import reserve_paid_request
from podbot.auth_transport import open_authenticated
from podbot.http_utils import read_limited_json


@dataclass
class SEOMetadata:
    title: str
    description: str
    tags: list[str]

    def to_dict(self) -> dict:
        return asdict(self)


def _clean_phrase(value: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s-]", " ", value, flags=re.UNICODE)).strip()


def _words_from_csv(text: str) -> list[str]:
    return [_clean_phrase(t) for t in text.split(",") if _clean_phrase(t)]


def normalize_metadata(title: str, description: str, tags: list[str]) -> SEOMetadata:
    title = re.sub(r"\s+", " ", title).strip()[:80]
    description = re.sub(r"\s+", " ", description).strip()[:700]
    seen: set[str] = set()
    cleaned: list[str] = []
    for tag in tags:
        tag = _clean_phrase(str(tag)).lower()[:40]
        if tag and tag not in seen:
            cleaned.append(tag)
            seen.add(tag)
        if len(cleaned) == 15:
            break
    if not title or not description or not cleaned:
        raise ValueError("SEO metadata must contain title, description and tags.")
    return SEOMetadata(title=title, description=description, tags=cleaned)


def local_seo(niche: str, keywords: str, prompt: str) -> SEOMetadata:
    """Deterministic offline fallback, never claims true keyword traffic data."""
    niche = _clean_phrase(niche) or "Original art"
    phrases = _words_from_csv(keywords)
    subject = phrases[0] if phrases else niche
    title = f"{subject.title()} | {niche.title()} Art"
    description = (
        f"An original {niche.lower()} inspired design featuring {subject.lower()}. "
        "Made for fans of expressive everyday art and thoughtful gifts. "
        "Review product placement, image quality and wording before publishing."
    )
    derived = [niche, subject, *phrases, "original art", "graphic design", "gift idea", "artwork"]
    derived.extend(_words_from_csv(prompt[:240].replace(" ", ",", 0)))
    return normalize_metadata(title, description, derived)


def _validate_gemini_text_model(model: str) -> str:
    if not isinstance(model, str) or not re.fullmatch(
        r"gemini-[a-zA-Z0-9._-]{3,100}", model
    ):
        raise ValueError("Invalid Gemini text model identifier.")
    if any(part in model.casefold() for part in (
        "image", "banana", "tts", "audio", "live",
        "embedding", "video", "robotics", "computer",
    )):
        raise ValueError("Use a Gemini text model, not an image/audio model.")
    return model


def gemini_seo(
    niche: str, keywords: str, prompt: str, api_key: str = "",
    *, model: str | None = None,
) -> SEOMetadata:
    key = api_key or os.environ.get("GEMINI_API_KEY", "")
    if not key:
        raise ValueError("GEMINI_API_KEY is required for AI SEO.")
    model = model or os.environ.get("GEMINI_MODEL", "gemini-3.5-flash-lite")
    model = _validate_gemini_text_model(model)
    instructions = (
        "You create accurate English product listing drafts for ORIGINAL print-on-demand art. "
        "Return ONLY a JSON object with string title, string description, and list of 10-15 "
        "short distinct relevant tags. Avoid false claims, brand/trademark references, "
        "copyrighted characters, unverified trend statistics and keyword stuffing. "
        "Title 80 chars max; description under 700 chars. "
        f"Niche: {niche[:120]}. Keywords: {keywords[:300]}. Design: {prompt[:800]}."
    )
    body = json.dumps({"contents": [{"parts": [{"text": instructions}]}],
                       "generationConfig": {"responseMimeType": "application/json"}}).encode()
    request = urllib.request.Request(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        data=body,
        headers={"x-goog-api-key": key, "Content-Type": "application/json"},
        method="POST",
    )
    reserve_paid_request("gemini")
    try:
        with open_authenticated(request, timeout=90) as response:
            result = read_limited_json(response)
    except urllib.error.HTTPError as exc:
        if exc.code == 403:
            raise RuntimeError(
                "Gemini SEO HTTP 403: project restricted or Free Tier unavailable. "
                "Check AI Studio project; models.list success does not grant inference."
            ) from None
        if exc.code == 429:
            raise RuntimeError(
                "Gemini SEO HTTP 429: quota or rate limit reached for this model. "
                "Check AI Studio Rate Limits; no automatic retry."
            ) from None
        raise RuntimeError(f"Gemini SEO API returned HTTP {exc.code}.") from None
    try:
        content = result["candidates"][0]["content"]["parts"][0]["text"]
        data = json.loads(content)
        return normalize_metadata(data["title"], data["description"], data["tags"])
    except (KeyError, IndexError, ValueError, TypeError) as exc:
        raise RuntimeError("Gemini returned invalid SEO metadata.") from exc


def gemini_refine_prompt(prompt: str, api_key: str, *, model: str) -> str:
    """Explicit, potentially billable text-only prompt rewrite. No retries or images."""
    if not api_key.strip():
        raise ValueError("GEMINI_API_KEY is required for Gemini prompt editing.")
    model = _validate_gemini_text_model(model)
    if not 8 <= len(prompt.strip()) <= 3500:
        raise ValueError("Prompt must be between 8 and 3500 characters.")
    instructions = (
        "Rewrite this original print-on-demand design prompt as concise English "
        "instructions suitable for a text-to-image model. Preserve subject, "
        "original words, style, exact colors, requested background and layout. "
        "Do not add trademarks, brand names, characters, extra text, shadows, "
        "fake checkerboard transparency or gradients. Prioritize crisp print "
        "silhouettes. Return one revised prompt only, under 1200 characters. "
        "Do not generate an image. Source:\n" + prompt.strip()
    )
    request = urllib.request.Request(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        data=json.dumps({
            "contents": [{"parts": [{"text": instructions}]}],
            "generationConfig": {"maxOutputTokens": 550},
        }).encode("utf-8"),
        method="POST",
        headers={"x-goog-api-key": api_key, "Content-Type": "application/json"},
    )
    # A project can be in the paid tier even for a model with a Free Tier listing.
    reserve_paid_request("gemini")
    try:
        with open_authenticated(request, timeout=90) as response:
            result = read_limited_json(response)
    except urllib.error.HTTPError as exc:
        if exc.code == 403:
            raise RuntimeError(
                "Gemini HTTP 403: key/project may be restricted or Free Tier "
                "unavailable. Check AI Studio project status; listing is not access."
            ) from None
        if exc.code == 429:
            raise RuntimeError(
                "Gemini HTTP 429: request or daily quota exhausted. "
                "Check AI Studio Rate Limits. No automatic retry."
            ) from None
        raise RuntimeError(
            f"Gemini prompt request HTTP {exc.code}. Check model and project."
        ) from None
    try:
        parts = result["candidates"][0]["content"]["parts"]
        revised = "\n".join(
            part["text"] for part in parts if isinstance(part.get("text"), str)
        ).strip()
    except (ValueError, TypeError, KeyError, IndexError) as exc:
        raise RuntimeError("Gemini returned no usable text prompt.") from exc
    if not 8 <= len(revised) <= 1600:
        raise RuntimeError("Gemini text prompt is empty or too long; not applied.")
    return revised
