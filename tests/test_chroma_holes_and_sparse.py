"""Chroma holes and sparse artwork must survive the complete CPU pipeline."""

import pytest
from PIL import Image, ImageDraw

from podbot.flat_background import remove_flat_background
from podbot.pipeline import create_draft
from podbot.prompt_recipe import PromptRecipe, build_prompt


def ring_art(key: tuple[int, int, int]) -> Image.Image:
    image = Image.new("RGB", (240, 240), key)
    painter = ImageDraw.Draw(image)
    painter.ellipse((42, 40, 199, 200), fill=(105, 105, 105))
    painter.ellipse((55, 53, 186, 187), fill=key)  # Letter O counter
    return image


def badge_with_two_holes(key: tuple[int, int, int]) -> Image.Image:
    image = Image.new("RGB", (240, 240), key)
    brush = ImageDraw.Draw(image)
    brush.rounded_rectangle((55, 34, 174, 208), radius=34, fill=(38, 38, 48))
    brush.ellipse((79, 54, 151, 108), fill=key)
    brush.ellipse((79, 133, 151, 187), fill=key)  # Letter B counters
    return image


@pytest.mark.parametrize("key", [(255, 0, 255), (0, 255, 0)])
@pytest.mark.parametrize("make_art", [ring_art, badge_with_two_holes])
def test_all_enclosed_chroma_holes_are_transparent(key, make_art):
    original = make_art(key)
    output = remove_flat_background(original, chroma_key=key)
    assert output.getpixel((0, 0))[3] == 0
    assert output.getpixel((120, 81))[3] == 0
    assert output.getpixel((120, 160))[3] == 0
    stroke_x = 48 if make_art is ring_art else 60
    assert output.getpixel((stroke_x, 120))[3] > 190
    # A neutral opaque subject must not turn magenta or green around inner edges.
    for r, g, b, a in output.get_flattened_data():
        if a > 16 and 0 < r < 200 and 0 < g < 200 and 0 < b < 200:
            assert max(r, g, b) - min(r, g, b) <= 25 or make_art is badge_with_two_holes


@pytest.mark.parametrize("key", [(255, 0, 255), (0, 255, 0)])
def test_sparse_cross_is_not_rejected_as_unsafe_background(key):
    image = Image.new("RGB", (320, 320), key)
    draw = ImageDraw.Draw(image)
    draw.line((155, 50, 155, 270), fill=(24, 33, 43), width=8)
    draw.line((85, 135, 230, 135), fill=(24, 33, 43), width=8)
    output = remove_flat_background(image, chroma_key=key)
    assert output.getpixel((0, 0))[3] == 0
    assert output.getpixel((155, 135))[3] > 235
    assert output.getpixel((155, 90))[3] > 150
    assert output.getpixel((205, 135))[3] > 150


def test_global_chroma_holes_in_processed_print_pipeline(tmp_path, monkeypatch):
    from podbot import pipeline

    monkeypatch.setattr(pipeline, "PRINT_SIZE", (480, 480))
    image = ring_art((255, 0, 255))

    class Provider:
        name = "offline-fixture"

        def generate(self, prompt):
            return image.copy()

    recipe = PromptRecipe(subject="Original hollow geometric letter O")
    entry = create_draft(
        build_prompt(recipe), "lettering", "geometric", Provider(),
        root=tmp_path, prompt_recipe=recipe.to_manifest(),
    )
    assert entry["auto_cutout"] == "success"
    with Image.open(entry["print_file"]) as print_png:
        center = (print_png.width // 2, print_png.height // 2)
        assert print_png.getpixel(center)[3] == 0
        assert print_png.getchannel("A").getextrema() == (0, 255)
    with Image.open(entry["source_file"]) as source:
        assert source.getpixel((120, 120)) == (255, 0, 255)
    assert entry["platform_status"]["redbubble"] == "draft"


def test_generic_flat_white_keeps_enclosed_white_details():
    image = Image.new("RGB", (210, 210), "white")
    draw = ImageDraw.Draw(image)
    draw.ellipse((30, 30, 180, 180), fill="black")
    draw.ellipse((80, 80, 130, 130), fill="white")
    output = remove_flat_background(image)
    assert output.getpixel((105, 105))[3] == 255
    assert output.getpixel((0, 0))[3] == 0


def test_chroma_all_key_refuses_blank_canvas():
    image = Image.new("RGB", (210, 210), (255, 0, 255))
    with pytest.raises(ValueError, match="unsafe area"):
        remove_flat_background(image, chroma_key=(255, 0, 255))
