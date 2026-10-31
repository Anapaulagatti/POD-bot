"""Bounded decoding for authenticated JSON API responses."""

from __future__ import annotations

import json

DEFAULT_JSON_LIMIT = 2 * 1024 * 1024
CLOUDFLARE_JSON_LIMIT = 32 * 1024 * 1024


def read_limited_json(response, max_bytes: int = DEFAULT_JSON_LIMIT) -> dict:
    """Do not stream unbounded upstream JSON or echo sensitive response bodies."""
    if not 0 < max_bytes <= 32 * 1024 * 1024:
        raise ValueError("Invalid response size limit.")
    raw = response.read(max_bytes + 1)
    if len(raw) > max_bytes:
        raise RuntimeError("Provider JSON response exceeds the configured size limit.")
    try:
        data = json.loads(raw)
    except (ValueError, UnicodeError) as exc:
        raise RuntimeError("Provider returned malformed JSON.") from exc
    if not isinstance(data, dict):
        raise RuntimeError("Provider JSON response must be an object.")
    return data
