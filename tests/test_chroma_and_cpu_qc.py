"""CPU-lite chroma prompts, model alpha labels and preconversion QC tests."""

import hashlib

import pytest
from PIL import Image, ImageDraw

from podbot.audit import audit_image, fingerprint
from podbot.image_review import OCRReport, inspect_halo, review_ocr
from podbot.pipeline import create_draft
from podbot.prompt_recipe import PromptRecipe, build_prompt
from podbot.provider_catalog import CATALOG


class Stub:
    name = "no-api"

    def __init__(self, image):
        self.image = image
        self.calls = []

    def generate(self, prompt):
        self.calls.append(prompt)
        return self.image.copy()


def chroma_design(color=(255, 0, 255)):
    image = Image.new("RGB", (200, 220), color)
    ImageDraw.Draw(image).ellipse((46, 42, 154, 175), fill=(22, 44, 72))
    return image


@pytest.mark.parametrize("background,color", [
    ("chroma-magenta", (255, 0, 255)),
    ("chroma-green", (0, 255, 0)),
])
def test_chroma_prompt_and_pillow_auto_cutout(background, color, tmp_path, monkeypatch):
    from podbot import pipeline
    monkeypatch.setattr(pipeline, "PRINT_SIZE", (440, 480))
    recipe = PromptRecipe(subject="Original navy mountain badge", background=background)
    provider = Stub(chroma_design(color))
    prompt = build_prompt(recipe)
    entry = create_draft(
        prompt, "nature", "mountain", provider, root=tmp_path,
        prompt_recipe=recipe.to_manifest(),
    )
    assert provider.calls == [prompt]
    assert "#FF00FF" in prompt if background == "chroma-magenta" else "#00FF00" in prompt
    assert entry["auto_cutout"] == "success"
    assert entry["source_has_alpha"] is False
    assert "pillow-edge-flood-v1" in entry["processing"]["steps"]
    assert entry["prompt_sent_sha256"] == hashlib.sha256(prompt.encode()).hexdigest()
    with Image.open(entry["source_file"]) as source:
        assert source.getpixel((0, 0)) == color
    with Image.open(entry["print_file"]) as result:
        assert result.getpixel((0, 0))[3] == 0
        assert result.getchannel("A").getextrema()[1] == 255
    assert entry["platform_status"]["redbubble"] == "draft"


@pytest.mark.parametrize("palette,background", [
    (["#FF00FF"], "chroma-magenta"),
    (["#FA00FC"], "chroma-magenta"),
    (["#00FF00"], "chroma-green"),
    (["#00E900"], "chroma-green"),
])
def test_chroma_key_cannot_overlap_art_palette(palette, background):
    with pytest.raises(ValueError, match="too similar"):
        build_prompt(PromptRecipe(subject="Original geometric badge",
                                  colors=tuple(palette), background=background))


def test_chroma_failure_stays_draft_and_keeps_source(tmp_path, monkeypatch):
    from podbot import pipeline
    monkeypatch.setattr(pipeline, "PRINT_SIZE", (440, 480))
    recipe = PromptRecipe(subject="Original detailed mountain design")
    image = Image.new("RGB", (160, 180))
    for y in range(image.height):
        for x in range(image.width):
            image.putpixel((x, y), (x, y, 100))
    entry = create_draft(build_prompt(recipe), "nature", "mountain", Stub(image),
                         root=tmp_path, prompt_recipe=recipe.to_manifest())
    assert entry["auto_cutout"] == "needs_manual_review"
    assert "refused" in entry["quality_warning"]
    assert entry["platform_status"]["redbubble"] == "draft"
    with Image.open(entry["source_file"]) as original:
        assert original.mode == "RGB"


def test_models_do_not_misclaim_verified_alpha():
    configured = [m for m in CATALOG if m.alpha_capability == "requested-unverified"]
    assert {m.vendor for m in configured} == {"openai"}
    assert all(m.alpha_capability in {"unknown", "requested-unverified"} for m in CATALOG)
    assert all(m.alpha_capability == "unknown" for m in CATALOG if m.vendor != "openai")


def test_ocr_warns_about_misspelled_user_original_words():
    report = OCRReport(True, "MOUTAIN LAND", "ok")
    checks = review_ocr(report, [], prompt="Original lettering", expected_text="MOUNTAIN LAND")
    assert any(c.name == "ocr_expected_text" and c.level == "warn" for c in checks)
    checks = review_ocr(OCRReport(True, "MOUNTAIN LAND", "ok"), [],
                        expected_text="Mountain Land")
    assert not any(c.name == "ocr_expected_text" for c in checks)


def test_large_rgb_analysis_reduces_before_rgba_conversion(monkeypatch):
    image = Image.new("RGB", (1700, 1900), (30, 60, 100))
    original = Image.Image.convert
    expensive_rgba = []

    def spy(self, mode=None, *args, **kwargs):
        if self.width > 1000 and self.height > 1000 and mode == "RGBA":
            expensive_rgba.append(self.size)
        return original(self, mode, *args, **kwargs)

    monkeypatch.setattr(Image.Image, "convert", spy)
    assert fingerprint(image).startswith("v2:")
    assert any(c.name == "canvas" for c in audit_image(image, "redbubble"))
    assert inspect_halo(image).partial_pixels == 0
    assert not expensive_rgba
