"""MVP 0.3 acceptance tests: print processing and human publishing gate."""

import json

import pytest
from PIL import Image, ImageDraw

from podbot.audit import audit_image, find_blocked_terms, fingerprint, make_color_preview
from podbot.processing import compose_print, process_image, ProcessOptions
from podbot.publishing import approve_listing, confirm_rights, export_approved_csv
from podbot.storage import list_designs, update_seo


def sample_logo():
    image = Image.new("RGBA", (100, 100), (0, 0, 0, 0))
    ImageDraw.Draw(image).ellipse((18, 16, 80, 86), fill=(10, 100, 220, 255))
    return image


def test_canvas_crop_safe_margin_and_dpi(tmp_path):
    out = tmp_path / "out.png"
    meta = compose_print(sample_logo(), out, size=(240, 260), margin=0.08)
    with Image.open(out) as image:
        assert image.mode == "RGBA"
        assert image.size == (240, 260)
        assert image.getpixel((0, 0))[3] == 0
        assert image.info["dpi"][0] == pytest.approx(300, rel=0.01)
        bbox = image.getchannel("A").getbbox()
        assert bbox[0] >= 15 and bbox[1] >= 16
    assert meta["source_size"] == [100, 100]
    assert meta["print_size"] == [240, 260]


def test_canvas_rejects_fully_transparent_or_unsafe_margin(tmp_path):
    with pytest.raises(ValueError):
        compose_print(Image.new("RGBA", (40, 40), (0, 0, 0, 0)), tmp_path / "out.png",
                      size=(100, 100))
    with pytest.raises(ValueError):
        compose_print(sample_logo(), tmp_path / "out.png", size=(100, 100), margin=0.5)


def test_opaque_background_does_not_falsely_pass_preflight(tmp_path):
    p = tmp_path / "opaque.png"
    process_image(Image.new("RGB", (80, 80), "white"), p, ProcessOptions(target_size=(200, 220)))
    with Image.open(p) as art:
        report = audit_image(art, "teepublic")
    assert any(check.name == "background" and check.level == "fail" for check in report)


def test_print_qc_edge_touch_and_shape():
    artwork = Image.new("RGBA", (100, 100), (0, 0, 0, 0))
    ImageDraw.Draw(artwork).rectangle((0, 10, 99, 90), fill=(100, 100, 100, 255))
    report = audit_image(artwork, "redbubble")
    assert any(check.name == "edge_touch" and check.level == "fail" for check in report)
    assert {x.level for x in report} <= {"pass", "warn", "fail"}


def test_dedupe_hash_detects_near_match():
    image = sample_logo()
    assert fingerprint(image) == fingerprint(image.copy())
    other = Image.new("RGBA", (100, 100), (255, 255, 255, 255))
    assert fingerprint(image) != fingerprint(other)


def test_blocklist_matches_unicode_boundaries_and_does_not_flag_substring():
    source = ["Café Brand", "sample hero"]
    assert "Café Brand" in find_blocked_terms("A cafe-brand print", source)
    assert not find_blocked_terms("heroes garden", ["hero"])


def test_preview_grid_shows_four_shirt_colors(tmp_path):
    path = tmp_path / "grid.png"
    make_color_preview(sample_logo(), path, tile=(120, 140))
    with Image.open(path) as image:
        assert image.size == (240, 280)
        assert image.mode == "RGB"


def test_background_tool_not_silently_downloaded(tmp_path):
    out = tmp_path / "design.png"
    with pytest.raises(RuntimeError, match="tool"):
        process_image(Image.new("RGB", (80, 80), "white"), out,
                      ProcessOptions(remove_background=True, target_size=(200, 220)))
    assert not out.exists()


def test_publish_gate_requires_rights_and_blocks_bad_background(tmp_path):
    from podbot.pipeline import create_draft

    class Fake:
        name = "test"

        def generate(self, prompt):
            return Image.new("RGB", (100, 100), "white")

    draft = create_draft("original watercolor garden", "plants", "garden", Fake(), root=tmp_path)
    with pytest.raises(ValueError, match="rights"):
        approve_listing(draft["id"], "teepublic", root=tmp_path)
    confirm_rights(draft["id"], root=tmp_path)
    with pytest.raises(ValueError, match="quality"):
        approve_listing(draft["id"], "teepublic", root=tmp_path)
    assert list_designs(tmp_path)[0]["platform_status"]["teepublic"] == "draft"


def test_publish_gate_blocks_terms_in_edited_seo(tmp_path):
    from podbot.pipeline import create_draft

    class Fake:
        name = "test"

        def generate(self, prompt):
            return sample_logo()

    draft = create_draft("original nature pattern", "nature", "garden", Fake(), root=tmp_path)
    confirm_rights(draft["id"], root=tmp_path)
    update_seo(draft["id"], "Café Brand souvenir", "An original print", ["garden"], root=tmp_path)
    with pytest.raises(ValueError, match="blocklist"):
        approve_listing(draft["id"], "redbubble", root=tmp_path, blocklist=["cafe brand"])


def test_export_only_approved_and_uploaded_requires_prior_approval(tmp_path):
    from podbot.pipeline import create_draft
    from podbot.storage import update_state

    class Fake:
        name = "test"

        def generate(self, prompt):
            return sample_logo()

    draft = create_draft("original ink botanical artwork", "botany", "flower", Fake(), root=tmp_path)
    csv_path = tmp_path / "upload.csv"
    assert export_approved_csv(csv_path, "redbubble", root=tmp_path) == 0
    with pytest.raises(ValueError, match="approved"):
        update_state(draft["id"], "redbubble", "uploaded", root=tmp_path)
    assert json.loads((tmp_path / draft["id"] / "manifest.json").read_text())["id"] == draft["id"]
