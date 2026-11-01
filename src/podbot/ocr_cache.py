"""Content-addressed OCR cache stored in the design manifest, never a key store."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path

from PIL import Image

from podbot.image_review import OCRReport, scan_ocr

OCR_CACHE_VERSION = 1
MAX_OCR_TEXT = 4000


def image_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def cached_image_ocr(entry: dict, image: Image.Image, path: Path) -> tuple[OCRReport, bool]:
    """Reuse OCR only when the exact print-file bytes match a prior scan.

    Returns (report, cache_updated). No secrets and no calls to paid services.
    """
    checksum = image_sha256(path)
    cached = entry.get("ocr_cache")
    if (isinstance(cached, dict) and cached.get("version") == OCR_CACHE_VERSION
            and cached.get("sha256") == checksum
            and isinstance(cached.get("available"), bool)
            and isinstance(cached.get("text"), str)
            and isinstance(cached.get("note"), str)
            and len(cached["text"]) <= MAX_OCR_TEXT
            and cached["available"]):
        return OCRReport(cached["available"], cached["text"], cached["note"]), False
    result = scan_ocr(image)
    if result.available:
        entry["ocr_cache"] = {
            "version": OCR_CACHE_VERSION,
            "sha256": checksum,
            "available": True,
            "text": result.text[:MAX_OCR_TEXT],
            "note": result.note[:240],
            "scanned_at": datetime.now(UTC).isoformat(),
        }
        return result, True
    # Do not persist a missing/failed OCR result: retry when the engine is installed.
    return result, False
