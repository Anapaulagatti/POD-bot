"""Atomic manifest writes and a local review queue. No central server required."""

from __future__ import annotations

import csv
import json
import os
import tempfile
from pathlib import Path

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
    if platform not in {"redbubble", "teepublic"}:
        raise ValueError("Unknown platform.")
    if state not in ALLOWED_STATES:
        raise ValueError("Unknown review state.")
    if not __import__("re").fullmatch(r"[0-9a-f]{32}", design_id):
        raise ValueError("Invalid design ID.")
    root = root or designs_directory()
    file = root / design_id / "manifest.json"
    record = json.loads(file.read_text(encoding="utf-8"))
    record.setdefault("platform_status", {})[platform] = state
    save_manifest(file.parent, record)
    return record


def export_csv(target: Path, platform: str, root: Path | None = None) -> int:
    if platform not in {"redbubble", "teepublic"}:
        raise ValueError("Unknown platform.")
    records = list_designs(root)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=[
            "id", "title", "description", "tags", "file", "status", "platform", "prompt"
        ])
        writer.writeheader()
        for entry in records:
            metadata = entry["seo"]
            writer.writerow({
                "id": entry["id"], "title": metadata["title"],
                "description": metadata["description"],
                "tags": ", ".join(metadata["tags"]), "file": entry["print_file"],
                "status": entry.get("platform_status", {}).get(platform, "draft"),
                "platform": platform, "prompt": entry["prompt"],
            })
    return len(records)
