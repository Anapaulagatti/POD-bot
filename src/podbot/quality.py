"""Compatibility facade around the single authoritative audit.py QC engine.

Do not store platform thresholds or maintain independent pass/fail checks here.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

from PIL import Image

from podbot.audit import MIN_CANVAS, audit_image

PROFILE_SIZES = MIN_CANVAS  # Deprecated alias; one shared source of truth.


@dataclass(frozen=True)
class QualityReport:
    platform: str
    canvas_size: tuple[int, int]
    artwork_size: tuple[int, int]
    has_transparency: bool
    issues: tuple[str, ...]
    ready: bool

    def to_dict(self) -> dict:
        return asdict(self)


def assess_image(
    image: Image.Image,
    source_size: tuple[int, int] | None = None,
    platform: str = "teepublic",
    opaque_source: bool | None = None,
) -> QualityReport:
    """Backwards compatible report projected only from audit_image results."""
    checks = audit_image(
        image, platform, source_size=source_size, opaque_source=bool(opaque_source)
    )
    alpha = image.convert("RGBA").getchannel("A")
    box = alpha.getbbox()
    art_size = (box[2] - box[0], box[3] - box[1]) if box else (0, 0)
    return QualityReport(
        platform=platform,
        canvas_size=image.size,
        artwork_size=art_size,
        has_transparency=alpha.getextrema()[0] < 255,
        issues=tuple(
            f"{check.name}: {check.message} ({check.value})"
            for check in checks if check.level != "pass"
        ),
        ready=all(check.level != "fail" for check in checks),
    )


def assess_design(record: dict, platform: str) -> QualityReport:
    path = Path(record["print_file"])
    if not path.is_file():
        raise FileNotFoundError(f"Missing local print asset: {path}")
    native = tuple(record.get("original_size", (0, 0)))
    with Image.open(path) as image:
        return assess_image(
            image, source_size=native, platform=platform,
            opaque_source=not record.get("source_has_alpha", False),
        )
