"""Read-only Pollinations image catalog with bounded memory and refresh cadence.

"Quest eligible" is NOT free: calls may spend Pollen credits. No credentials
are required or sent to this public listing, and no code is downloaded/executed.
"""

from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass

from podbot.auth_transport import open_authenticated

CATALOG_URL = "https://gen.pollinations.ai/image/models?source=official"
MAX_CATALOG_BYTES = 2 * 1024 * 1024
REFRESH_SECONDS = 6 * 60 * 60
MODEL_ID_PATTERN = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9_./:-]{2,140}\Z")


@dataclass(frozen=True)
class ImageOffer:
    model_id: str
    name: str
    access: str  # quest-eligible, paid-only, unknown
    image_adapter: bool
    warning: str


@dataclass(frozen=True)
class CatalogSnapshot:
    offers: tuple[ImageOffer, ...]
    fetched_at: float
    source: str = CATALOG_URL


_CACHE: CatalogSnapshot | None = None


def parse_image_offers(payload: list | dict) -> tuple[ImageOffer, ...]:
    if isinstance(payload, dict):
        data = payload.get("models", payload.get("data", payload.get("result")))
    else:
        data = payload
    if not isinstance(data, list):
        raise TypeError("Pollinations model listing shape is not recognized.")
    found: dict[str, ImageOffer] = {}
    for entry in data[:500]:
        if not isinstance(entry, dict):
            continue
        model = entry.get("id") or entry.get("model")
        if not isinstance(model, str) or not MODEL_ID_PATTERN.fullmatch(model):
            continue
        is_paid_only = entry.get("paid_only", entry.get("paidOnly"))
        access = ("paid-only" if is_paid_only is True
                  else "quest-eligible" if is_paid_only is False else "unknown")
        endpoints = entry.get("supported_endpoints", [])
        output = entry.get("output_modalities", [])
        if not isinstance(endpoints, list):
            endpoints = []
        if not isinstance(output, list):
            output = []
        supports_images = any(
            isinstance(item, str) and "images/generations" in item.casefold()
            for item in endpoints
        ) or "image" in output
        # A model ID alone is not proof of ability to use the POST image route.
        eligible = access == "quest-eligible" and supports_images
        display = str(entry.get("name") or entry.get("title") or model)[:100]
        found[model] = ImageOffer(
            model_id=model, name=display, access=access, image_adapter=eligible,
            warning=("Can use earned Quest Pollen; this is NOT a zero-cost model."
                     if eligible else
                     "Unavailable for free-credit testing or adapter unverified."),
        )
    return tuple(sorted(
        found.values(), key=lambda o: (not o.image_adapter, o.access, o.model_id)
    ))


def refresh_public_catalog(*, force: bool = False, now: float | None = None) -> CatalogSnapshot:
    """No network until invoked by the user/Settings UI; 6-hour in-memory TTL."""
    global _CACHE
    current = time.time() if now is None else now
    if (_CACHE is not None and not force
            and 0 <= current - _CACHE.fetched_at < REFRESH_SECONDS):
        return _CACHE
    request = urllib.request.Request(
        CATALOG_URL, headers={
            "Accept": "application/json", "User-Agent": "PODBotStudio/1.0",
        }, method="GET",
    )
    try:
        with open_authenticated(request, timeout=12) as response:
            data = response.read(MAX_CATALOG_BYTES + 1)
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"Pollinations catalog rejected GET (HTTP {exc.code}).") from None
    except (urllib.error.URLError, TimeoutError, OSError):
        raise RuntimeError("Pollinations public catalog is not reachable.") from None
    if len(data) > MAX_CATALOG_BYTES:
        raise RuntimeError("Pollinations catalog exceeded the size limit.")
    try:
        payload = json.loads(data)
    except (ValueError, UnicodeError):
        raise RuntimeError("Pollinations returned invalid catalog JSON.") from None
    offers = parse_image_offers(payload)
    _CACHE = CatalogSnapshot(offers, current)
    return _CACHE
