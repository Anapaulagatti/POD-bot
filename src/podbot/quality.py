"""Conservative print-preflight checks against marketplace sizing guidance."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

from PIL import Image

# See docs/MARKETPLACE_REQUIREMENTS.md. These are indicative upload guides,
# not a promise that a design qualifies for all products.
PROFILE_SIZES = {
    "redbubble": (2400, 3200),
    "teepublic": (5000, 5500),
}


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
    """Inspect actual pixels, not EXIF DPI or reported file resolution."""
    if platform not in PROFILE_SIZES:
        raise ValueError("Unsupported marketplace.")
    if image.width == 0 or image.height == 0:
        raise ValueError("Empty image.")
    required = PROFILE_SIZES[platform]
    alpha = image.convert("RGBA").getchannel("A")
    extrema = alpha.getextrema()
    transparent = extrema[0] < 255
    box = alpha.getbbox()
    art_size = (box[2] - box[0], box[3] - box[1]) if box else (0, 0)
    issues: list[str] = []
    if image.width < required[0] or image.height < required[1]:
        if platform == "teepublic":
            issues.append("TeePublic all-product canvas requires 5000 x 5500 pixels.")
        else:
            issues.append("Redbubble apparel commonly requires 2400 x 3200 pixels.")
    if art_size == (0, 0):
        issues.append("No non-transparent artwork detected.")
    if platform == "teepublic" and (art_size[0] < 1500 or art_size[1] < 1995):
        issues.append("TeePublic artwork footprint is below 1500 x 1995 pixels.")
    if not transparent or opaque_source:
        issues.append("Opaque background/source detected; confirm suitability for apparel.")
    if source_size and (art_size[0] > source_size[0] * 1.5 or art_size[1] > source_size[1] * 1.5):
        issues.append(
            "Artwork was upscaled from the native AI source. Upscaling does not restore "
            "fine print detail; review at full size."
        )
    return QualityReport(platform, image.size, art_size, transparent, tuple(issues), not issues)


def assess_design(record: dict, platform: str) -> QualityReport:
    image_path = Path(record["print_file"])
    if not image_path.exists():
        raise FileNotFoundError(f"Missing local print asset: {image_path}")
    native = tuple(record.get("original_size", (0, 0)))
    with Image.open(image_path) as image:
        return assess_image(
            image,
            source_size=native,
            platform=platform,
            opaque_source=not record.get("source_has_alpha", False),
        )
