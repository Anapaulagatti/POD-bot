"""Pillow-only conservative flat-background cutout for POD illustrations.

Flood-fills only edge-connected pixels close to a uniform corner color.
This is NOT semantic background removal: inspect letters, white art and halos.
"""

from __future__ import annotations

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageOps


def remove_flat_background(
    image: Image.Image, *, tolerance: int = 25, feather: float = 0.65,
    scan_max: int = 768,
) -> Image.Image:
    """Return cutout, fail closed on gradients, existing alpha or ambiguous edges."""
    if not 4 <= tolerance <= 65:
        raise ValueError("Tolerance must be between 4 and 65.")
    if not 0 <= feather <= 2:
        raise ValueError("Feather radius must be between 0 and 2.")
    if not 128 <= scan_max <= 1024:
        raise ValueError("Scan size must be between 128 and 1024.")
    if min(image.size) < 16 or image.width * image.height > 50_000_000:
        raise ValueError("Image dimensions are not suitable for flat cutout.")
    rgba = ImageOps.exif_transpose(image).convert("RGBA")
    if rgba.getchannel("A").getextrema()[0] < 255:
        raise ValueError("This image already has transparency; keep its original alpha.")
    small = ImageOps.contain(rgba.convert("RGB"), (scan_max, scan_max))
    w, h = small.size
    corners = [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)]
    colors = [small.getpixel(point) for point in corners]
    base = tuple(round(sum(rgb[channel] for rgb in colors) / 4) for channel in range(3))
    distance = lambda rgb: max(abs(rgb[channel] - base[channel]) for channel in range(3))
    if any(distance(rgb) > max(12, tolerance // 2) for rgb in colors):
        raise ValueError("Corner colors vary: not a uniform flat background.")
    edge_points = (
        [(x, 0) for x in range(w)] + [(x, h - 1) for x in range(w)]
        + [(0, y) for y in range(h)] + [(w - 1, y) for y in range(h)]
    )
    edge_near = sum(distance(small.getpixel(point)) <= tolerance for point in edge_points)
    if edge_near / len(edge_points) < 0.85:
        raise ValueError("Edges are not predominantly the same color; manual review needed.")
    difference = ImageChops.difference(small, Image.new("RGB", (w, h), base))
    r, g, b = difference.split()
    maximum = ImageChops.lighter(ImageChops.lighter(r, g), b)
    candidates = maximum.point(lambda value: 255 if value <= tolerance else 0)
    # 255 = candidate background; 128 = connected flood-filled region.
    for point in corners:
        if candidates.getpixel(point) == 255:
            ImageDraw.floodfill(candidates, point, 128, thresh=0)
    matte = candidates.point(lambda value: 255 if value == 128 else 0)
    removed_fraction = matte.histogram()[255] / (w * h)
    if not 0.08 <= removed_fraction <= 0.92:
        raise ValueError("Detected background covers an unsafe area; no changes applied.")
    if feather:
        matte = matte.filter(ImageFilter.GaussianBlur(feather))
    matte = matte.resize(rgba.size, Image.Resampling.BILINEAR)
    alpha = ImageChops.subtract(rgba.getchannel("A"), matte)
    if not alpha.getbbox():
        raise ValueError("The cutout would remove all artwork.")
    rgba.putalpha(alpha)
    return rgba
