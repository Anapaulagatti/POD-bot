"""Regression tests for Pillow-only print cutout edge quality."""

import pytest
from PIL import Image, ImageDraw

from podbot.flat_background import _decontaminate_edges, remove_flat_background


def _near_white_fringe_share(image: Image.Image) -> float:
    pixels = image.convert("RGBA").tobytes()
    partial = [
        pixels[offset:offset + 3]
        for offset in range(0, len(pixels), 4)
        if 0 < pixels[offset + 3] < 255
    ]
    assert partial, "Regression image should contain partially transparent edge pixels."
    pale = sum(min(rgb) >= 220 for rgb in partial)
    return pale / len(partial)


@pytest.mark.parametrize("antialias", [False, True])
def test_flat_background_does_not_leave_white_fringe_on_blue_circle(antialias):
    scale = 4 if antialias else 1
    image = Image.new("RGB", (240 * scale, 240 * scale), "white")
    ImageDraw.Draw(image).ellipse(
        (44 * scale, 42 * scale, 196 * scale, 198 * scale), fill=(16, 42, 102)
    )
    if antialias:
        image = image.resize((240, 240), Image.Resampling.LANCZOS)

    result = remove_flat_background(image)

    assert result.getpixel((0, 0))[3] == 0
    assert result.getpixel((120, 120)) == (16, 42, 102, 255)
    assert _near_white_fringe_share(result) < 0.15


def test_flat_background_handles_off_white_background():
    image = Image.new("RGB", (200, 200), (251, 248, 243))
    ImageDraw.Draw(image).ellipse((40, 44, 160, 156), fill=(24, 42, 94))

    result = remove_flat_background(image)

    assert result.getpixel((0, 0))[3] == 0
    assert result.getpixel((100, 100)) == (24, 42, 94, 255)
    assert _near_white_fringe_share(result) < 0.15


def test_white_island_inside_dark_outline_is_preserved():
    image = Image.new("RGB", (200, 200), "white")
    draw = ImageDraw.Draw(image)
    draw.ellipse((50, 50, 150, 150), fill="black")
    draw.ellipse((60, 60, 140, 140), fill="white")

    result = remove_flat_background(image)

    assert result.getpixel((0, 0))[3] == 0
    assert result.getpixel((100, 100)) == (255, 255, 255, 255)


def test_alpha_unmixing_uses_estimated_background_color():
    pixel = Image.new("RGBA", (1, 1), (150, 160, 180, 128))
    mask = Image.new("L", (1, 1), 128)

    _decontaminate_edges(pixel, mask, (255, 255, 255))

    assert pixel.getpixel((0, 0)) == (45, 65, 105, 128)
