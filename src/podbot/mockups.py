"""Local generic t-shirt preview. Not an official marketplace product mockup."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageOps


def create_shirt_mockup(
    artwork: Image.Image,
    target: Path,
    size: tuple[int, int] = (720, 840),
) -> Path:
    """Composite artwork onto a drawn shirt; never alter the source asset."""
    w, h = size
    if w < 180 or h < 200:
        raise ValueError("Mockup canvas is too small.")
    preview = Image.new("RGB", size, (233, 236, 241))
    draw = ImageDraw.Draw(preview)
    # Flat-lay T-shirt with sleeves, collar and seam details.
    points = [
        (int(.32*w), int(.12*h)), (int(.40*w), int(.08*h)),
        (int(.60*w), int(.08*h)), (int(.68*w), int(.12*h)),
        (int(.91*w), int(.23*h)), (int(.79*w), int(.38*h)),
        (int(.71*w), int(.33*h)), (int(.71*w), int(.91*h)),
        (int(.29*w), int(.91*h)), (int(.29*w), int(.33*h)),
        (int(.21*w), int(.38*h)), (int(.09*w), int(.23*h)),
    ]
    draw.polygon(points, fill=(250, 250, 247), outline=(157, 165, 177), width=3)
    draw.ellipse((int(.42*w), int(.071*h), int(.58*w), int(.17*h)),
                 fill=(201, 207, 216), outline=(157, 165, 177), width=2)
    source = artwork.convert("RGBA")
    # Never enlarge tiny previews; use only for visualization, not product export.
    scaled = ImageOps.contain(source, (int(.34*w), int(.40*h)), Image.Resampling.LANCZOS)
    x = (w - scaled.width) // 2
    y = int(.36*h) - scaled.height // 2
    preview.paste(scaled, (x, y), mask=scaled.getchannel("A"))
    target.parent.mkdir(parents=True, exist_ok=True)
    preview.save(target, "PNG")
    return target
