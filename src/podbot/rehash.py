"""Migrate legacy advisory fingerprints without modifying images or approvals."""

from __future__ import annotations

import json
import re
from pathlib import Path

from PIL import Image, UnidentifiedImageError

from podbot.audit import fingerprint
from podbot.settings import designs_directory
from podbot.storage import save_manifest


def rehash_designs(root: Path | None = None, *, dry_run: bool = False) -> dict[str, int]:
    """Rehash v1 manifests using their immutable source.png; leave v2 unchanged."""
    folder = root if root is not None else designs_directory()
    result = {"scanned": 0, "updated": 0, "skipped": 0, "missing": 0, "failed": 0}
    if not folder.exists():
        return result
    for manifest in sorted(folder.glob("*/manifest.json")):
        if not re.fullmatch(r"[0-9a-f]{32}", manifest.parent.name):
            continue
        result["scanned"] += 1
        try:
            entry = json.loads(manifest.read_text(encoding="utf-8"))
            if entry.get("id") != manifest.parent.name:
                result["failed"] += 1
                continue
            if re.fullmatch(r"v2:[a-f0-9]{32}", str(entry.get("fingerprint", ""))):
                result["skipped"] += 1
                continue
            # Local folder is canonical; never follow an arbitrary path from a JSON manifest.
            source = manifest.parent / "source.png"
            if not source.is_file():
                result["missing"] += 1
                continue
            with Image.open(source) as image:
                if image.width * image.height > 50_000_000:
                    raise ValueError("Original image exceeds the safe pixel limit.")
                value = fingerprint(image)
            if not dry_run:
                entry["fingerprint"] = value
                entry["fingerprint_algorithm"] = "v2:luminance-gray+alpha"
                save_manifest(manifest.parent, entry)
            result["updated"] += 1
        except (OSError, ValueError, TypeError, UnidentifiedImageError):
            result["failed"] += 1
    return result
