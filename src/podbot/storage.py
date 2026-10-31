"""Atomic manifest writes and a local review queue. No central server required."""

from __future__ import annotations

import csv
import json
import os
import tempfile
from pathlib import Path

from podbot.seo import normalize_metadata
from podbot.settings import designs_directory

ALLOWED_STATES = {"draft", "approved", "uploaded"}


def save_manifest(folder: Path, record: dict) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / "manifest.json"
    fd, temporary = tempfile.mkstemp(prefix=".manifest-", suffix=".tmp", dir=str(folder))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(record, handle, ensure_ascii=False, indent=2)
        os.replace(temporary, target)
    finally:
        if os.path.exists(temporary):
            os.remove(temporary)
    return target


def list_designs(root: Path | None = None) -> list[dict]:
    root = root or designs_directory()
    if not root.exists():
        return []
    results = []
    for file in root.glob("*/manifest.json"):
        try:
            record = json.loads(file.read_text(encoding="utf-8"))
            if record.get("id") == file.parent.name:
                results.append(record)
        except (json.JSONDecodeError, OSError):
            continue
    return sorted(results, key=lambda item: item.get("created_at", ""), reverse=True)


def update_state(design_id: str, platform: str, state: str, root: Path | None = None) -> dict:
    """A state transition never bypasses the human approval workflow."""
    if platform not in {"redbubble", "teepublic"}:
        raise ValueError("Unknown platform.")
    if state not in ALLOWED_STATES:
        raise ValueError("Unknown review state.")
    if not __import__("re").fullmatch(r"[0-9a-f]{32}", design_id):
        raise ValueError("Invalid design ID.")
    if state == "approved":
        from podbot.publishing import approve_listing

        return approve_listing(design_id, platform, root=root)
    if state == "uploaded":
        raise ValueError("Use mark_uploaded(..., confirmed=True) after manual upload.")
    file = (root or designs_directory()) / design_id / "manifest.json"
    record = json.loads(file.read_text(encoding="utf-8"))
    if record.get("id") != design_id:
        raise ValueError("Manifest ID mismatch.")
    record.setdefault("platform_status", {})[platform] = "draft"
    record.setdefault("approval_evidence", {}).pop(platform, None)
    save_manifest(file.parent, record)
    return record


def export_csv(target: Path, platform: str, root: Path | None = None) -> int:
    """Only safely approved designs are exported for manual marketplace upload."""
    from podbot.publishing import export_approved_csv

    return export_approved_csv(target, platform, root=root)


def update_seo(
    design_id: str,
    title: str,
    description: str,
    tags: list[str],
    root: Path | None = None,
) -> dict:
    """Apply explicitly reviewed SEO edits to the stored local manifest."""
    import re

    if not re.fullmatch(r"[0-9a-f]{32}", design_id):
        raise ValueError("Invalid design ID.")
    metadata = normalize_metadata(title, description, tags)
    folder = (root or designs_directory()) / design_id
    record = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    if record.get("id") != design_id:
        raise ValueError("Manifest ID mismatch.")
    record["seo"] = metadata.to_dict()
    # Metadata changes invalidate approvals; uploading requires a fresh review.
    for platform in ("redbubble", "teepublic"):
        if record.get("platform_status", {}).get(platform) == "approved":
            record["platform_status"][platform] = "draft"
        record.get("approval_evidence", {}).pop(platform, None)
    save_manifest(folder, record)
    return record
