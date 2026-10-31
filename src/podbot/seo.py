"""Honest, editable SEO drafts. Gemini is opt-in; rules work offline."""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass


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


def gemini_seo(niche: str, keywords: str, prompt: str, api_key: str = "") -> SEOMetadata:
    key = api_key or os.environ.get("GEMINI_API_KEY", "")
    if not key:
        raise ValueError("GEMINI_API_KEY is required for AI SEO.")
    model = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash-lite")
    if not re.fullmatch(r"[\w.\-]+", model):
        raise ValueError("Invalid Gemini model identifier.")
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
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            result = json.load(response)
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"Gemini SEO API returned HTTP {exc.code}.") from exc
    try:
        content = result["candidates"][0]["content"]["parts"][0]["text"]
        data = json.loads(content)
        return normalize_metadata(data["title"], data["description"], data["tags"])
    except (KeyError, IndexError, ValueError, TypeError) as exc:
        raise RuntimeError("Gemini returned invalid SEO metadata.") from exc
