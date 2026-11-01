"""Advisory POD image inspection: edge halos, shirt previews and local OCR.

Neither pixel checks nor OCR constitute trademark clearance or print certification.
OCR requires a separately installed Tesseract executable; no models/downloads.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageOps

from podbot.audit import Check, find_blocked_terms


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
    sample = ImageOps.contain(image, (800, 800), Image.Resampling.LANCZOS).convert("RGBA")
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


def review_ocr(
    report: OCRReport, blocked_terms: list[str], *, prompt: str = ""
) -> list[Check]:
    """Advisory OCR + hard block only for recognized exact blocklist phrases."""
    if not report.available:
        return [Check(
            "ocr_text", "warn", "unavailable",
            "Offline OCR unavailable. Check all text in the artwork manually.",
        )]
    text = report.text.strip()
    blocked = find_blocked_terms(text, blocked_terms)
    if blocked:
        return [Check(
            "ocr_text", "fail", ", ".join(blocked[:5]),
            "OCR detected words on your local blocklist; review artwork before approval.",
        )]
    output = [Check(
        "ocr_text", "pass" if text else "warn",
        text[:140] if text else "nothing recognized",
        "OCR is imperfect; inspect all visible text and commercial rights manually.",
    )]
    if text and re.search(r"\b(no\s+(?:text|words|letters|typography|writing))\b",
                          prompt, re.IGNORECASE):
        output.append(Check(
            "ocr_unexpected_text", "warn", text[:140],
            "Words detected even though the prompt requested no text.",
        ))
    return output


def scan_ocr(
    image: Image.Image, *, executable: str | Path | None = None,
    language: str = "eng",
) -> OCRReport:
    """Run local Tesseract on white and dark composites, never on raw RGBA RGB bytes."""
    if language not in {"eng", "vie", "eng+vie"}:
        raise ValueError("Unsupported OCR language.")
    candidate = str(executable or os.environ.get("PODBOT_TESSERACT_PATH") or "tesseract")
    tool = shutil.which(candidate)
    if tool is None:
        return OCRReport(False, "", "Tesseract OCR is not installed or selected.")
    rgba = image.convert("RGBA")
    rgba.thumbnail((1800, 1800), Image.Resampling.LANCZOS)
    is_transparent = rgba.getchannel("A").getextrema()[0] < 255
    backgrounds = ((255, 255, 255), (0, 0, 0)) if is_transparent else ((255, 255, 255),)
    lines: list[str] = []
    seen: set[str] = set()
    succeeded = False
    with tempfile.TemporaryDirectory(prefix="podbot-ocr-") as temp:
        path = Path(temp) / "image.png"
        for rgb in backgrounds:
            canvas = Image.new("RGBA", rgba.size, (*rgb, 255))
            canvas.alpha_composite(rgba)
            canvas.convert("RGB").save(path)
            try:
                result = subprocess.run(
                    [tool, str(path), "stdout", "-l", language],
                    timeout=45, capture_output=True, check=False,
                    shell=False,
                )
            except (OSError, subprocess.TimeoutExpired):
                continue
            if result.returncode != 0:
                continue
            succeeded = True
            for line in result.stdout[:65536].decode("utf-8", errors="replace").splitlines():
                line = line.strip()
                signature = line.casefold()
                if line and signature not in seen:
                    lines.append(line)
                    seen.add(signature)
    if not succeeded:
        return OCRReport(False, "", "OCR engine or language data unavailable.")
    text = "\n".join(lines)[:4000]
    return OCRReport(True, text, "OCR is advisory; review text manually on light/dark fabric.")
