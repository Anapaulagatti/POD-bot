"""Regression tests for OCR approval and sourced Trends keyword suggestions."""

from __future__ import annotations

import subprocess

import pytest
from PIL import Image, ImageDraw

from podbot.image_review import OCRReport, review_ocr, scan_ocr
from podbot.publishing import validate_listing
from podbot.trends import parse_trends


def test_transparent_dark_text_composited_on_white_for_ocr(monkeypatch):
    samples = []

    def fake_run(args, **kwargs):
        with Image.open(args[1]) as captured:
            samples.append((captured.getpixel((0, 0)), captured.getpixel((65, 65))))
        return subprocess.CompletedProcess(args, 0, b"original artwork\n", b"")

    monkeypatch.setattr("podbot.image_review.shutil.which", lambda _: "/fake/tesseract")
    monkeypatch.setattr("podbot.image_review.subprocess.run", fake_run)
    art = Image.new("RGBA", (130, 130), (0, 0, 0, 0))
    ImageDraw.Draw(art).rectangle((50, 50, 80, 80), fill=(10, 10, 10, 255))
    report = scan_ocr(art)
    assert report.available
    assert "original artwork" in report.text
    assert samples[0] == ((255, 255, 255), (10, 10, 10))
    assert len(samples) == 2
    assert samples[1][0] == (0, 0, 0)


def test_ocr_blocks_brands_and_warns_unrequested_text():
    checks = review_ocr(OCRReport(True, "Acme Logo", "review"),
                        ["acme"], prompt="original mountain art no text")
    assert any(c.name == "ocr_text" and c.level == "fail" for c in checks)
    checks = review_ocr(OCRReport(True, "hello sunshine", "review"), [],
                        prompt="minimal flower design no text")
    assert any(c.name == "ocr_unexpected_text" and c.level == "warn" for c in checks)
    unavailable = review_ocr(OCRReport(False, "", "not installed"), [])
    assert any(c.name == "ocr_text" and c.level == "warn" for c in unavailable)


def test_approve_path_checks_blocked_text_in_pixels(monkeypatch, tmp_path):
    png = tmp_path / "art.png"
    Image.new("RGBA", (100, 100), (0, 0, 0, 0)).save(png)
    monkeypatch.setattr("podbot.publishing.audit_image", lambda *args: [])
    monkeypatch.setattr("podbot.ocr_cache.scan_ocr",
                        lambda image: OCRReport(True, "ACME Brand", "ok"))
    entry = {
        "print_file": str(png),
        "rights_confirmed_at": "2026-10-31",
        "seo": {"title": "original art", "description": "floral", "tags": []},
        "prompt": "abstract floral pattern",
    }
    with pytest.raises(ValueError, match="ocr_text"):
        validate_listing(entry, "redbubble", blocklist=["acme"])


def test_ocr_does_not_break_approval_when_optional_engine_missing(monkeypatch, tmp_path):
    png = tmp_path / "art.png"
    Image.new("RGBA", (100, 100), (0, 0, 0, 0)).save(png)
    monkeypatch.setattr("podbot.publishing.audit_image", lambda *args: [])
    monkeypatch.setattr("podbot.ocr_cache.scan_ocr",
                        lambda image: OCRReport(False, "", "Tesseract missing"))
    entry = {
        "print_file": str(png), "rights_confirmed_at": "confirmed",
        "seo": {"title": "floral", "description": "art", "tags": []}
    }
    checks = validate_listing(entry, "redbubble", blocklist=[])
    assert any(c["name"] == "ocr_text" and c["level"] == "warn" for c in checks)


def test_trends_extracts_sourced_keyword_suggestions_and_news():
    rss = """<?xml version="1.0"?>
    <rss xmlns:ht="https://trends.google.com/trending/rss"><channel><item>
      <title>flower garden ideas</title><ht:approx_traffic>2000+</ht:approx_traffic>
      <ht:news_item><ht:news_item_title>Small flower garden ideas for patios</ht:news_item_title>
      <ht:news_item_snippet>Plan colorful backyard beds</ht:news_item_snippet></ht:news_item>
    </item></channel></rss>"""
    trend = parse_trends(rss)[0]
    assert "flower garden ideas" in trend.keywords
    assert "garden ideas" in trend.keywords
    assert len(trend.news_titles) == 1
    assert "patios" in trend.news_titles[0].lower()
    assert len(trend.keywords) <= 10
    assert trend.keyword_source == "RSS topic + news headline phrases (suggestions, not Google related queries)"


def test_trends_avoids_short_garbage_and_deduplicates():
    rss = """<rss><channel><item><title>A &amp; B</title></item></channel></rss>"""
    trend = parse_trends(rss)[0]
    assert len(set(trend.keywords)) == len(trend.keywords)
    assert all(len(keyword.strip()) > 2 for keyword in trend.keywords)
