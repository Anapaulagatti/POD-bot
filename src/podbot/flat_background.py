"""Pillow-only conservative flat-background cutout for POD illustrations.

Flood-fills only edge-connected pixels close to a uniform corner color.
This is NOT semantic background removal: inspect letters, white art and halos.
"""

from __future__ import annotations

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageMath, ImageOps


def remove_flat_background(
    image: Image.Image, *, tolerance: int = 25, feather: float = 0.65,
    scan_max: int = 768,
    chroma_key: tuple[int, int, int] | None = None,
) -> Image.Image:
    """Return cutout, fail closed on gradients, existing alpha or ambiguous edges."""
    if not 4 <= tolerance <= 65:
        raise ValueError("Tolerance must be between 4 and 65.")
    if not 0 <= feather <= 2:
        raise ValueError("Feather radius must be between 0 and 2.")
    if not 128 <= scan_max <= 1024:
        raise ValueError("Scan size must be between 128 and 1024.")
    if chroma_key is not None and (
        not isinstance(chroma_key, tuple) or len(chroma_key) != 3
        or any(type(value) is not int or not 0 <= value <= 255 for value in chroma_key)
    ):
        raise ValueError("Chroma key must be an RGB tuple of bytes.")
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
    if chroma_key is not None:
        # The builder knows the intended key. Uniform darkened corners can agree
        # with each other while differing sharply from that color (vignette).
        if any(max(abs(rgb[i] - chroma_key[i]) for i in range(3)) > tolerance + 15
               for rgb in colors):
            raise ValueError(
                "Chroma corner colors diverge from the selected key (possible vignette)."
            )
        # Check two inset perimeter rings as well, not just four corners.
        # A model-produced vignette can otherwise leave opaque colored bands.
        points = []
        for fraction in (0.03, 0.08):
            xx = min(w - 1, max(0, round((w - 1) * fraction)))
            yy = min(h - 1, max(0, round((h - 1) * fraction)))
            for index in range(24):
                x = round(index * (w - 1) / 23)
                y = round(index * (h - 1) / 23)
                points.extend(((x, yy), (x, h - 1 - yy),
                               (xx, y), (w - 1 - xx, y)))
        matches = sum(
            max(abs(small.getpixel(point)[i] - chroma_key[i])
                for i in range(3)) <= tolerance + 15 for point in points
        )
        if matches / len(points) < 0.92:
            raise ValueError(
                "Chroma background varies across inset edges (possible vignette); "
                "manual review required."
            )
        base = chroma_key

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
    if chroma_key is not None:
        # The matte was inferred from color differences, so it is not a
        # trustworthy physical coverage fraction for algebraic decontamination.
        # Trim the outermost pixel, then borrow clean RGB from opaque interior.
        alpha = alpha.filter(ImageFilter.MinFilter(3))
        if not alpha.getbbox():
            raise ValueError("Chroma refinement removed all visible artwork.")
        rgba.putalpha(alpha)
        _fill_chroma_fringe_from_core(rgba, alpha)
    else:
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


def _fill_chroma_fringe_from_core(rgba: Image.Image, alpha: Image.Image) -> None:
    """Repair a narrow chroma fringe from opaque interior colors, in small tiles.

    The color model is a weighted blur of an eroded opaque core, NOT an
    inversion of the estimated matte. No distant pixels are inpainted.
    """
    tile_size = 512
    padding = 12
    for top in range(0, rgba.height, tile_size):
        for left in range(0, rgba.width, tile_size):
            right = min(left + tile_size, rgba.width)
            bottom = min(top + tile_size, rgba.height)
            extended = (
                max(0, left - padding), max(0, top - padding),
                min(rgba.width, right + padding), min(rgba.height, bottom + padding),
            )
            tile_alpha = alpha.crop(extended)
            opaque = tile_alpha.point(lambda value: 255 if value >= 245 else 0)
            core = opaque.filter(ImageFilter.MinFilter(5))
            if not core.getbbox():
                continue  # No reliable interior color: do not invent one.
            near_edge = ImageOps.invert(
                tile_alpha.point(lambda value: 255 if value >= 250 else 0)
            ).filter(ImageFilter.MaxFilter(9))
            if not near_edge.getbbox():
                continue
            # Only alter RGB where artwork is visible, never an untouched core.
            visible = tile_alpha.point(lambda value: 255 if value > 0 else 0)
            near_edge = ImageChops.multiply(near_edge, visible)
            weights = core.filter(ImageFilter.GaussianBlur(2.3))
            safe = weights.point(lambda value: max(1, value))
            red, green, blue = rgba.crop(extended).convert("RGB").split()
            repaired = []
            for channel in (red, green, blue):
                weighted = ImageChops.multiply(channel, core)
                blurred = weighted.filter(ImageFilter.GaussianBlur(2.3))
                estimated = ImageMath.lambda_eval(
                    lambda p: (p["color"] * 255) / p["weight"],
                    color=blurred, weight=safe,
                ).convert("L")
                repaired.append(Image.composite(estimated, channel, near_edge))
            adjusted = Image.merge("RGBA", (*repaired, tile_alpha))
            crop = (
                left - extended[0], top - extended[1],
                right - extended[0], bottom - extended[1],
            )
            rgba.paste(adjusted.crop(crop), (left, top))
