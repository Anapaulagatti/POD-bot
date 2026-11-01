"""Visual chroma-edge regressions: neutral artwork must not have key-colored rims."""

from __future__ import annotations

import math

import pytest
from PIL import Image, ImageDraw

from podbot.flat_background import remove_flat_background
from podbot.pipeline import create_draft
from podbot.prompt_recipe import PromptRecipe, build_prompt


def _disc(key: tuple[int, int, int], *, size: int = 224) -> Image.Image:
    # Render at 4x for physically plausible blended RGB antialiasing.
    image = Image.new("RGB", (size * 4, size * 4), key)
    ImageDraw.Draw(image).ellipse((44 * 4, 40 * 4, 177 * 4, 182 * 4),
                                  fill=(111, 111, 111))
    return image.resize((size, size), Image.Resampling.LANCZOS)


def _edge_contamination(image: Image.Image) -> tuple[int, float]:
    pixels = image.convert("RGBA").get_flattened_data()
    # Use partially transparent pixels containing actual artwork.
    fringe = [(r, g, b) for r, g, b, a in pixels if 10 < a < 250]
    if not fringe:
        return 0, 0.0
    contaminated = sum(max(rgb) - min(rgb) > 28 for rgb in fringe)
    return len(fringe), contaminated / len(fringe)


@pytest.mark.parametrize("key", [(255, 0, 255), (0, 255, 0)])
def test_neutral_disc_chroma_fringe_has_less_than_five_percent_spill(key):
    source = _disc(key)
    cutout = remove_flat_background(source, chroma_key=key)
    pixels, share = _edge_contamination(cutout)
    assert pixels > 30
    assert share < .05
    assert cutout.getpixel((0, 0))[3] == 0
    center = cutout.getpixel((110, 110))
    assert center[3] == 255
    assert max(center[:3]) - min(center[:3]) < 2
    # Fringe is also neutral when composited on black, white and navy fabrics.
    for shirt in ((0, 0, 0), (255, 255, 255), (24, 39, 69)):
        composite = Image.new("RGBA", cutout.size, (*shirt, 255))
        composite.alpha_composite(cutout)
        assert composite.getpixel((0, 0))[:3] == shirt


@pytest.mark.parametrize("key", [(255, 0, 255), (0, 255, 0)])
def test_chroma_small_noise_still_preserves_clean_art(key):
    img = _disc(key)
    # +-9 on the key background only, with no tampering of artwork.
    for y in range(img.height):
        for x in range(img.width):
            p = img.getpixel((x, y))
            if max(abs(p[i] - key[i]) for i in range(3)) < 2:
                delta = (x + y) % 19 - 9
                img.putpixel((x, y), tuple(max(0, min(255, c + delta)) for c in p))
    cutout = remove_flat_background(img, chroma_key=key)
    pixels, share = _edge_contamination(cutout)
    assert pixels > 10
    assert share < .07


@pytest.mark.parametrize("key", [(255, 0, 255), (0, 255, 0)])
def test_uniform_dark_corner_vignette_is_rejected(key):
    img = _disc(key)
    w, h = img.size
    for y in range(h):
        for x in range(w):
            # Darken the corners by up to 40%, while keeping all four
            # corners equally tinted. The old four-corner test accepts this.
            distance = math.hypot(x - w / 2, y - h / 2)
            attenuation = 1 - .4 * min(1, distance / (math.hypot(w, h) / 2))
            rgb = img.getpixel((x, y))
            img.putpixel((x, y), tuple(round(channel * attenuation) for channel in rgb))
    with pytest.raises(ValueError, match="vignette|Chroma background"):
        remove_flat_background(img, chroma_key=key)


def test_white_inner_art_is_not_erased_by_magenta_edge_cleanup():
    image = Image.new("RGB", (210, 210), (255, 0, 255))
    d = ImageDraw.Draw(image)
    d.ellipse((30, 30, 180, 180), fill=(20, 20, 20))
    d.ellipse((75, 75, 135, 135), fill=(255, 255, 255))
    output = remove_flat_background(image, chroma_key=(255, 0, 255))
    assert output.getpixel((105, 105)) == (255, 255, 255, 255)
    assert output.getpixel((0, 0))[3] == 0


def test_pipeline_refuses_bad_vignette_without_approving(tmp_path, monkeypatch):
    from podbot import pipeline

    monkeypatch.setattr(pipeline, "PRINT_SIZE", (360, 420))
    img = _disc((255, 0, 255))
    img.putpixel((0, 0), (110, 0, 110))
    class Provider:
        name = "offline-fixture"
        def generate(self, prompt):
            return img.copy()
    recipe = PromptRecipe(subject="Original geometric neutral gray disc")
    record = create_draft(
        build_prompt(recipe), "geometric", "disc", Provider(),
        prompt_recipe=recipe.to_manifest(), root=tmp_path,
    )
    assert record["auto_cutout"] == "needs_manual_review"
    assert record["platform_status"]["redbubble"] == "draft"
    assert "vignette" in record["quality_warning"].casefold()
