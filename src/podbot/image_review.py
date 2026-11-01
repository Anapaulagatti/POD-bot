"""Advisory POD image inspection: edge halos, shirt previews and local OCR.

Neither pixel checks nor OCR constitute trademark clearance or print certification.
OCR requires a separately installed Tesseract executable; no models/downloads.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageOps


@dataclass(frozen=True)
class HaloReport:
    partial_pixels: int
    bright_partial_pixels: int
    bright_share: float
    warning: bool


@dataclass(frozen=True)
class OCRReport:
    available: bool
    text: str
    note: str


def inspect_halo(image: Image.Image, *, threshold: float = 0.35) -> HaloReport:
    """Measure pale, partially transparent fringe as a review hint, not a verdict."""
    if not 0 <= threshold <= 1:
        raise ValueError("Invalid halo threshold.")
    sample = ImageOps.contain(image.convert("RGBA"), (800, 800))
    rgba = sample.tobytes()
    partial = bright = 0
    for i in range(0, len(rgba), 4):
        a = rgba[i + 3]
        if 8 <= a <= 247:
            partial += 1
            if min(rgba[i], rgba[i + 1], rgba[i + 2]) >= 220:
                bright += 1
    share = bright / partial if partial else 0.0
    # Too few sampled pixels provide no useful statistic.
    return HaloReport(partial, bright, share, partial >= 20 and share > threshold)


def create_fabric_preview(image: Image.Image, destination: Path) -> Path:
    """Preview the true alpha composited on light, dark and navy cloth colors."""
    thumb = ImageOps.contain(image.convert("RGBA"), (520, 520))
    swatches = ((255, 255, 255), (29, 29, 30), (24, 39, 69))
    canvas = Image.new("RGB", (thumb.width * 3, thumb.height))
    for index, rgb in enumerate(swatches):
        tile = Image.new("RGBA", thumb.size, (*rgb, 255))
        tile.alpha_composite(thumb)
        canvas.paste(tile.convert("RGB"), (index * thumb.width, 0))
    destination.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(destination, format="PNG")
    return destination


def scan_ocr(
    image: Image.Image, *, executable: str | Path | None = None,
    language: str = "eng",
) -> OCRReport:
    """Run offline OCR without shell, API keys or network; missing OCR is explicit."""
    if language not in {"eng", "vie", "eng+vie"}:
        raise ValueError("Unsupported OCR language.")
    candidate = str(executable or os.environ.get("PODBOT_TESSERACT_PATH") or "tesseract")
    tool = shutil.which(candidate)
    if tool is None:
        return OCRReport(False, "", "Tesseract OCR is not installed or selected.")
    image = ImageOps.contain(image.convert("RGB"), (1800, 1800))
    with tempfile.TemporaryDirectory(prefix="podbot-ocr-") as temp:
        path = Path(temp) / "image.png"
        image.save(path)
        try:
            result = subprocess.run(
                [tool, str(path), "stdout", "-l", language],
                timeout=45, capture_output=True, check=False,
                shell=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            return OCRReport(False, "", "Offline OCR could not complete.")
    if result.returncode != 0:
        return OCRReport(False, "", "OCR engine or language data unavailable.")
    text = result.stdout[:65536].decode("utf-8", errors="replace").strip()
    return OCRReport(True, text[:4000], "Review recognized text manually; OCR can be inaccurate.")
