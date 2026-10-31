import json
from pathlib import Path

import pytest
from PIL import Image, ImageDraw

from podbot.pipeline import create_draft, prepare_print_image
from podbot.seo import local_seo, normalize_metadata
from podbot.storage import export_csv, list_designs, update_state


class StubProvider:
    name = "stub-test"

    def generate(self, prompt: str):
        image = Image.new("RGBA", (180, 180), (0, 0, 0, 0))
        ImageDraw.Draw(image).ellipse((30, 15, 150, 164), fill=(255, 70, 10, 255))
        return image


def test_seo_normalizes_and_deduplicates():
    data = normalize_metadata(" Example  Art ", "  An example ", ["Art", "art", "hiking"])
    assert data.tags == ["art", "hiking"]
    assert data.title == "Example Art"


def test_offline_seo_is_not_fake_trend_data():
    seo = local_seo("nature", "mountains, sunrise", "a sunrise over peaks")
    assert "Mountains" in seo.title
    assert "mountains" in seo.tags
    assert not any("trending" in t for t in seo.tags)


def test_print_canvas_preserves_alpha(tmp_path):
    path = tmp_path / "print.png"
    assert prepare_print_image(Image.new("RGBA", (20, 30), (50, 80, 90, 255)), path, (100, 120)) is False
    with Image.open(path) as image:
        assert image.size == (100, 120)
        assert image.getpixel((0, 0))[3] == 0


def test_pipeline_local_queue_and_export(tmp_path):
    record = create_draft("a minimalist mountain print", "outdoors", "mountain, sunrise", StubProvider(), root=tmp_path)
    assert record["platform_status"]["teepublic"] == "draft"
    assert Path(record["print_file"]).exists()
    manifest = json.loads((tmp_path / record["id"] / "manifest.json").read_text())
    assert manifest["seo"]["title"]
    assert len(list_designs(tmp_path)) == 1
    from podbot.publishing import confirm_rights

    confirm_rights(record["id"], root=tmp_path)
    update_state(record["id"], "redbubble", "approved", root=tmp_path)
    assert list_designs(tmp_path)[0]["platform_status"]["redbubble"] == "approved"
    csv_path = tmp_path / "export.csv"
    assert export_csv(csv_path, "redbubble", root=tmp_path) == 1
    assert "approved" in csv_path.read_text(encoding="utf-8-sig")


def test_invalid_review_rejected(tmp_path):
    with pytest.raises(ValueError):
        update_state("../outside", "redbubble", "uploaded", root=tmp_path)
    with pytest.raises(ValueError):
        update_state("0" * 32, "unapproved-platform", "uploaded", root=tmp_path)


def test_short_prompt_rejected_without_provider_call(tmp_path):
    with pytest.raises(ValueError):
        create_draft("bad", "art", "", StubProvider(), root=tmp_path)
    assert not list(tmp_path.iterdir())
