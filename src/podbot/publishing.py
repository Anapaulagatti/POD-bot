"""Supervised Redbubble / TeePublic publishing. No login bot, no auto-post."""

from __future__ import annotations

import csv
import json
import re
from datetime import UTC, datetime
from pathlib import Path

from PIL import Image

from podbot.audit import audit_image, find_blocked_terms, get_blocklist, near_duplicates
from podbot.image_review import review_ocr
from podbot.ocr_cache import cached_image_ocr
from podbot.settings import designs_directory
from podbot.storage import list_designs, save_manifest

VALID_PLATFORMS = {"redbubble", "teepublic"}
POLICY_URLS = {
    "redbubble": "https://www.redbubble.com/agreement",
    "teepublic": "https://teepublic.zendesk.com/hc/en-us/articles/"
                 "4409831531031-Designing-for-Specific-Product-Dimensions",
}


def _load(design_id: str, root: Path | None) -> tuple[Path, dict]:
    if not re.fullmatch(r"[0-9a-f]{32}", design_id):
        raise ValueError("Invalid design ID.")
    file = (root or designs_directory()) / design_id / "manifest.json"
    entry = json.loads(file.read_text(encoding="utf-8"))
    if entry.get("id") != design_id:
        raise ValueError("Manifest ID mismatch.")
    return file, entry


def confirm_rights(design_id: str, *, root: Path | None = None) -> dict:
    """Call only after explicit human affirmation; records timestamp on the manifest."""
    file, entry = _load(design_id, root)
    entry["rights_confirmed_at"] = datetime.now(UTC).isoformat()
    # A rights change invalidates prior platform approval.
    entry["platform_status"] = {"redbubble": "draft", "teepublic": "draft"}
    save_manifest(file.parent, entry)
    return entry


def validate_listing(entry: dict, platform: str, *, blocklist: list[str] | None = None,
                     cache_dir: Path | None = None) -> list[dict]:
    if platform not in VALID_PLATFORMS:
        raise ValueError("Unknown marketplace.")
    if not entry.get("rights_confirmed_at"):
        raise ValueError("Confirm rights before approval.")
    listing = entry.get("seo", {})
    combined = " ".join([
        entry.get("prompt", ""), listing.get("title", ""),
        listing.get("description", ""), *listing.get("tags", []),
    ])
    terms = get_blocklist() if blocklist is None else blocklist
    blocked = find_blocked_terms(combined, terms)
    if blocked:
        raise ValueError(f"blocklist requires review: {', '.join(blocked[:5])}")
    source = Path(entry["print_file"])
    if not source.exists():
        raise ValueError("Print image is missing.")
    with Image.open(source) as image:
        checks = audit_image(image, platform)
        report, changed = cached_image_ocr(entry, image, source)
        if changed and cache_dir is not None:
            # Persist a content-hash-bound transcript even when approval subsequently fails.
            save_manifest(cache_dir, entry)
        checks.extend(review_ocr(report, terms, prompt=entry.get("prompt", "")))
    failures = [c for c in checks if c.level == "fail"]
    if failures:
        raise ValueError("Print quality fail: " + "; ".join(c.name for c in failures))
    return [x.to_dict() for x in checks]


def approve_listing(design_id: str, platform: str, *, root: Path | None = None,
                    blocklist: list[str] | None = None) -> dict:
    file, entry = _load(design_id, root)
    checks = validate_listing(entry, platform, blocklist=blocklist, cache_dir=file.parent)
    duplicates = near_duplicates(entry, list_designs(root))
    if duplicates:
        checks.append({
            "name": "similar_designs", "level": "warn",
            "value": ", ".join(duplicates[:5]),
            "message": "Possible near-duplicate detected locally. Review originality.",
        })
    entry.setdefault("platform_status", {})[platform] = "approved"
    entry.setdefault("approval_evidence", {})[platform] = {
        "timestamp": datetime.now(UTC).isoformat(),
        "checks": checks,
        "rights_confirmed_at": entry["rights_confirmed_at"],
    }
    save_manifest(file.parent, entry)
    return entry


def mark_uploaded(design_id: str, platform: str, *, confirmed: bool = False,
                  root: Path | None = None) -> dict:
    """User verifies the design on marketplace after manual browser upload."""
    if not confirmed:
        raise ValueError("Manual upload confirmation is required.")
    file, entry = _load(design_id, root)
    if platform not in VALID_PLATFORMS:
        raise ValueError("Unknown marketplace.")
    if entry.get("platform_status", {}).get(platform) != "approved":
        raise ValueError("Design must be approved before marking uploaded.")
    # Recheck because design or metadata may have changed since approval.
    validate_listing(entry, platform, cache_dir=file.parent)
    entry["platform_status"][platform] = "uploaded"
    entry.setdefault("upload_confirmed_at", {})[platform] = datetime.now(UTC).isoformat()
    save_manifest(file.parent, entry)
    return entry


def export_approved_csv(target: Path, platform: str, *,
                        root: Path | None = None) -> int:
    if platform not in VALID_PLATFORMS:
        raise ValueError("Unknown marketplace.")
    records = []
    for entry in list_designs(root):
        if entry.get("platform_status", {}).get(platform) != "approved":
            continue
        # Fail closed: an invalid approved record must not be exported silently.
        # The cache is persisted in its existing manifest, not in the export file.
        record_id = entry.get("id", "")
        if not re.fullmatch(r"[0-9a-f]{32}", record_id):
            raise ValueError("Invalid design ID in export.")
        folder = (root or designs_directory()) / record_id
        validate_listing(entry, platform, cache_dir=folder)
        seo = entry["seo"]
        records.append({
            "id": entry["id"], "title": seo["title"], "description": seo["description"],
            "tags": ", ".join(seo["tags"]), "file": entry["print_file"],
            "platform": platform, "status": "approved",
        })
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=[
            "id", "title", "description", "tags", "file", "platform", "status",
        ])
        writer.writeheader()
        writer.writerows(records)
    return len(records)
