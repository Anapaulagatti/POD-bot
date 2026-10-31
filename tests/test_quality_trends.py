"""Acceptance tests for print preflight, real RSS trends and local mockups."""

import pytest
from PIL import Image

from podbot.mockups import create_shirt_mockup
from podbot.pipeline import prepare_print_image
from podbot.quality import assess_image
from podbot.trends import parse_trends, read_trends


RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss xmlns:ht="https://trends.google.com/trending/rss"><channel>
<item><title>flower garden</title><pubDate>Sat, 31 Oct 2026 09:00:00 GMT</pubDate>
<ht:approx_traffic>5000+</ht:approx_traffic></item>
<item><title>Local artist</title><pubDate>Sat, 31 Oct 2026 10:00:00 GMT</pubDate>
<ht:approx_traffic>200+</ht:approx_traffic></item>
</channel></rss>"""


def test_trends_parse_source_attribution():
    trends = parse_trends(RSS, country="US", limit=1)
    assert len(trends) == 1
    trend = trends[0]
    assert trend.title == "flower garden"
    assert trend.approx_traffic == "5000+"
    assert trend.country == "US"
    assert trend.source_url == "https://trends.google.com/trending/rss?geo=US"
    assert "Oct 2026" in trend.published


def test_trends_reject_unsafe_xml():
    xml = '<!DOCTYPE lol [<!ENTITY x "unsafe">]><rss><channel/></rss>'
    with pytest.raises(ValueError, match="DOCTYPE"):
        parse_trends(xml)


def test_trends_country_allowlist():
    with pytest.raises(ValueError):
        read_trends(country="US;https://evil.example/")


def test_trends_network_mock(monkeypatch):
    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def read(self, size=-1):
            return RSS.encode("utf-8")

    urls = []

    def fake_open(request, timeout):
        urls.append(request.full_url)
        assert timeout <= 15
        return Response()

    monkeypatch.setattr("podbot.trends.urllib.request.urlopen", fake_open)
    output = read_trends(country="GB", limit=2)
    assert len(output) == 2
    assert urls == ["https://trends.google.com/trending/rss?geo=GB"]


def test_opaque_rgba_is_not_counted_as_transparent(tmp_path):
    opaque = Image.new("RGBA", (25, 30), (80, 90, 100, 255))
    path = tmp_path / "opaque.png"
    assert prepare_print_image(opaque, path, (100, 110)) is False


def test_preflight_flags_low_native_resolution_and_opaque_art():
    img = Image.new("RGBA", (200, 200), (60, 60, 60, 255))
    report = assess_image(img, source_size=(50, 50), platform="teepublic")
    assert not report.ready
    assert any("5000" in issue for issue in report.issues)
    assert any("opaque" in issue.lower() for issue in report.issues)
    assert any("upscal" in issue.lower() for issue in report.issues)


def test_preflight_art_bbox_ignores_transparent_margins():
    img = Image.new("RGBA", (250, 250), (0, 0, 0, 0))
    img.paste((90, 10, 20, 255), (50, 50, 150, 180))
    report = assess_image(img, source_size=(250, 250), platform="redbubble")
    assert report.artwork_size == (100, 130)
    assert report.has_transparency is True
    assert report.platform == "redbubble"


def test_preflight_rejects_unknown_platform():
    with pytest.raises(ValueError):
        assess_image(Image.new("RGB", (20, 30)), platform="somewhere")


def test_mockup_is_rendered_locally_and_keeps_source_unchanged(tmp_path):
    design = Image.new("RGBA", (120, 120), (0, 0, 0, 0))
    design.paste((200, 60, 20, 255), (30, 20, 90, 100))
    first = design.tobytes()
    target = tmp_path / "shirt.png"
    result = create_shirt_mockup(design, target, size=(520, 620))
    assert result == target
    with Image.open(target) as image:
        assert image.size == (520, 620)
        assert image.mode == "RGB"
    assert design.tobytes() == first


def test_mockup_rejects_tiny_canvas(tmp_path):
    with pytest.raises(ValueError):
        create_shirt_mockup(Image.new("RGBA", (10, 10)), tmp_path / "t.png", size=(50, 60))
