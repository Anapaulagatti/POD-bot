"""Pillow-only cutout, prompt transparency, migration and rembg caching."""

import json
import sys
import types

import pytest
from PIL import Image, ImageDraw

from podbot.audit import fingerprint
from podbot.flat_background import remove_flat_background
from podbot.pipeline import create_draft
from podbot.processing import (
    ProcessOptions,
    _rembg_session,
    process_image,
    process_stored_design,
)
from podbot.prompting import FLAT_BACKGROUND_SUFFIX, prepare_image_prompt
from podbot.rehash import rehash_designs
from podbot.storage import list_designs, save_manifest


def test_pillow_flat_cutout_keeps_white_lettering_on_dark_background():
    image = Image.new("RGB", (180, 200), "#102336")
    draw = ImageDraw.Draw(image)
    draw.rectangle((55, 50, 125, 155), fill="white")
    result = remove_flat_background(image)
    assert result.mode == "RGBA"
    assert result.getpixel((0, 0))[3] == 0
    assert result.getpixel((90, 105))[3] >= 245
    assert result.size == image.size
    assert image.getpixel((0, 0)) == (16, 35, 54)


def test_flat_cutout_preserves_opaque_illustration_and_rejects_gradient():
    img = Image.new("RGB", (120, 140), "white")
    ImageDraw.Draw(img).ellipse((20, 25, 100, 115), fill=(215, 60, 30))
    output = remove_flat_background(img, feather=0)
    assert output.getpixel((0, 0))[3] == 0
    assert output.getpixel((60, 60))[3] == 255
    assert output.getchannel("A").getbbox()

    gradient = Image.new("RGB", (128, 128))
    for x in range(128):
        for y in range(128):
            gradient.putpixel((x, y), (x * 2, y * 2, 100))
    with pytest.raises(ValueError, match="Corner colors"):
        remove_flat_background(gradient)


def test_flat_cutout_refuses_already_transparent_and_ambiguous_blank():
    alpha = Image.new("RGBA", (120, 120), (255, 255, 255, 0))
    with pytest.raises(ValueError, match="already has transparency"):
        remove_flat_background(alpha)
    with pytest.raises(ValueError, match="unsafe area"):
        remove_flat_background(Image.new("RGB", (120, 120), "white"))


def test_cutout_requires_explicit_mode_and_prepares_print(tmp_path):
    image = Image.new("RGB", (160, 160), "white")
    ImageDraw.Draw(image).rectangle((40, 45, 125, 130), fill="navy")
    dest = tmp_path / "print.png"
    info = process_image(image, dest, ProcessOptions(
        flat_background=True, target_size=(240, 260)
    ))
    assert "pillow-edge-flood-v1" in info["steps"]
    with Image.open(dest) as result:
        assert result.getpixel((0, 0))[3] == 0
    with pytest.raises(ValueError, match="either Pillow"):
        process_image(image, tmp_path / "invalid.png",
                      ProcessOptions(flat_background=True, remove_background=True))


def test_flat_prompt_is_opt_in_and_does_not_change_original_seo(tmp_path):
    original = "Unique alpine flower for a print"

    class Provider:
        name = "stub"

        def __init__(self):
            self.received = None

        def generate(self, prompt):
            self.received = prompt
            image = Image.new("RGBA", (160, 160), (0, 0, 0, 0))
            ImageDraw.Draw(image).ellipse((40, 35, 120, 125), fill="purple")
            return image

    provider = Provider()
    entry = create_draft(
        original, "nature", "flowers", provider, root=tmp_path,
        flat_background_prompt=True,
    )
    assert FLAT_BACKGROUND_SUFFIX in provider.received
    assert entry["prompt"] == original
    assert entry["prompt_sent"] == provider.received
    assert entry["flat_background_prompt"]
    assert prepare_image_prompt(original) == original
    with pytest.raises(ValueError, match="too long"):
        prepare_image_prompt("a" * 2040, flat_background=True)


def test_rehash_legacy_uses_local_source_and_does_not_reset_review(tmp_path):
    from podbot.pipeline import create_draft

    class Provider:
        name = "stub"

        def generate(self, prompt):
            image = Image.new("RGBA", (100, 100), (0, 0, 0, 0))
            ImageDraw.Draw(image).rectangle((18, 20, 78, 82), fill="white")
            return image

    entry = create_draft("One original white print", "white", "minimal",
                         Provider(), root=tmp_path)
    manifest = tmp_path / entry["id"] / "manifest.json"
    original = json.loads(manifest.read_text(encoding="utf-8"))
    original["fingerprint"] = "0" * 16
    original["fingerprint_algorithm"] = "v1"
    original["platform_status"]["redbubble"] = "approved"
    original["approval_evidence"] = {"redbubble": {"manual": True}}
    save_manifest(manifest.parent, original)
    assert rehash_designs(tmp_path, dry_run=True)["updated"] == 1
    assert json.loads(manifest.read_text())["fingerprint"] == "0" * 16
    assert rehash_designs(tmp_path)["updated"] == 1
    updated = list_designs(tmp_path)[0]
    with Image.open(manifest.parent / "source.png") as source:
        assert updated["fingerprint"] == fingerprint(source)
    assert updated["platform_status"]["redbubble"] == "approved"
    assert updated["approval_evidence"] == original["approval_evidence"]
    assert rehash_designs(tmp_path)["skipped"] == 1


def test_rehash_ignores_unsafe_manifest_directory(tmp_path):
    invalid = tmp_path / "unsafe"
    invalid.mkdir()
    (invalid / "manifest.json").write_text('{"id":"unsafe","fingerprint":"0000000000000000"}')
    assert rehash_designs(tmp_path)["scanned"] == 0


def test_rembg_model_session_cached_between_images(monkeypatch, tmp_path):
    calls = []

    class FakeModule(types.ModuleType):
        def new_session(self, model):
            calls.append(model)
            return object()

        def remove(self, image, session):
            result = Image.new("RGBA", image.size, (0, 0, 0, 0))
            result.paste((0, 0, 0, 255), (12, 12, 48, 48))
            return result

    fake = FakeModule("rembg")
    monkeypatch.setitem(sys.modules, "rembg", fake)
    _rembg_session.cache_clear()
    try:
        for index in range(2):
            process_image(
                Image.new("RGB", (70, 70), "white"), tmp_path / f"bg{index}.png",
                ProcessOptions(remove_background=True, target_size=(160, 170)),
            )
        assert calls == ["isnet-general-use"]
    finally:
        _rembg_session.cache_clear()
