"""Pillow-only conservative flat-background cutout for POD illustrations.

Flood-fills only edge-connected pixels close to a uniform corner color.
This is NOT semantic background removal: inspect letters, white art and halos.
"""

from __future__ import annotations

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageMath, ImageOps


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
    def distance(rgb: tuple[int, int, int]) -> int:
        return max(abs(rgb[channel] - base[channel]) for channel in range(3))
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
    # Flood all four borders, including multiple edge-connected components.
    # Bound component count to prevent pathological patterns from taking too long.
    regions = 0
    for point in edge_points:
        if candidates.getpixel(point) == 255:
            regions += 1
            if regions > 32:
                raise ValueError("Too many separate edge areas for safe flat cutout.")
            ImageDraw.floodfill(candidates, point, 128, thresh=0)
    matte = candidates.point(lambda value: 255 if value == 128 else 0)
    removed_fraction = matte.histogram()[255] / (w * h)
    if not 0.08 <= removed_fraction <= 0.92:
        raise ValueError("Detected background covers an unsafe area; no changes applied.")
    hard_foreground = ImageOps.invert(matte)
    soft_foreground = hard_foreground
    if feather:
        soft_foreground = ImageChops.darker(
            hard_foreground, hard_foreground.filter(ImageFilter.GaussianBlur(feather))
        )
    # Never turn pixels classified as background into a translucent white halo.
    hard_full = hard_foreground.resize(rgba.size, Image.Resampling.NEAREST)
    soft_full = soft_foreground.resize(rgba.size, Image.Resampling.BILINEAR)
    alpha = ImageChops.darker(hard_full, soft_full)
    if not alpha.getbbox():
        raise ValueError("The cutout would remove all artwork.")
    rgba.putalpha(alpha)
    _decontaminate_edges(rgba, alpha, base)
    return rgba


def _decontaminate_edges(
    rgba: Image.Image, alpha: Image.Image, background: tuple[int, int, int]
) -> None:
    """Reverse background mixing on antialiased edges in bounded image tiles.

    For 0 < alpha < 255, C = (I - (1 - alpha) * B) / alpha.
    Fully transparent and opaque areas need no adjustment.
    """
    for y in range(0, rgba.height, 1024):
        for x in range(0, rgba.width, 1024):
            box = (x, y, min(x + 1024, rgba.width), min(y + 1024, rgba.height))
            mask = alpha.crop(box)
            low, high = mask.getextrema()
            if high == 0 or low == 255:
                continue
            safe_mask = mask.point(lambda value: max(value, 1))
            channels = rgba.crop(box).convert("RGB").split()
            corrected = []
            for source, color in zip(channels, background):
                channel = ImageMath.lambda_eval(
                    lambda p, background_color=color: (
                        p["source"] * 255 - (255 - p["alpha"]) * background_color
                    ) / p["alpha"],
                    source=source, alpha=safe_mask,
                ).convert("L")
                corrected.append(channel)
            rgba.paste(Image.merge("RGBA", (*corrected, mask)), (x, y))
