"""No paid network calls: OCR cache, Trends filters and per-key model discovery."""

from __future__ import annotations

import json
import urllib.error

import pytest
from PIL import Image

from podbot import model_discovery, provider_catalog
from podbot.image_review import OCRReport
from podbot.publishing import export_approved_csv, validate_listing
from podbot.storage import save_manifest
from podbot.trends import keyword_suggestions


def test_ocr_cache_reuses_exact_file_and_rescans_change(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr("podbot.publishing.audit_image", lambda image, platform: [])
    monkeypatch.setattr(
        "podbot.ocr_cache.scan_ocr",
        lambda image: (calls.append(1) or OCRReport(True, "Acme", "confirmed locally")),
    )
    path = tmp_path / "print.png"
    Image.new("RGBA", (30, 30), (20, 50, 90, 220)).save(path)
    entry = {
        "id": "b" * 32, "print_file": str(path),
        "rights_confirmed_at": "yes",
        "seo": {"title": "local", "description": "art", "tags": ["blue"]},
    }
    validate_listing(entry, "redbubble", blocklist=[], cache_dir=tmp_path)
    assert len(calls) == 1
    assert entry["ocr_cache"]["version"] == 1
    assert entry["ocr_cache"]["sha256"] in json.loads(
        (tmp_path / "manifest.json").read_text()
    )["ocr_cache"]["sha256"]
    validate_listing(entry, "redbubble", blocklist=[], cache_dir=tmp_path)
    assert len(calls) == 1
    # Changing the blocklist must still reject the cached OCR text.
    with pytest.raises(ValueError, match="ocr_text"):
        validate_listing(entry, "redbubble", blocklist=["acme"], cache_dir=tmp_path)
    assert len(calls) == 1
    Image.new("RGBA", (30, 30), (20, 50, 90, 221)).save(path)
    validate_listing(entry, "redbubble", blocklist=[], cache_dir=tmp_path)
    assert len(calls) == 2


def test_csv_export_uses_existing_transcript_without_new_ocr(monkeypatch, tmp_path):
    count = []
    monkeypatch.setattr("podbot.publishing.audit_image", lambda image, platform: [])
    monkeypatch.setattr(
        "podbot.ocr_cache.scan_ocr",
        lambda image: (count.append(1) or OCRReport(True, "original flowers", "ok")),
    )
    for index in range(3):
        design_id = f"{index + 1:032x}"
        folder = tmp_path / design_id
        folder.mkdir()
        image_path = folder / "print.png"
        Image.new("RGBA", (40, 40), (12, 12, index, 255)).save(image_path)
        save_manifest(folder, {
            "id": design_id, "print_file": str(image_path), "rights_confirmed_at": "yes",
            "platform_status": {"redbubble": "approved"},
            "seo": {"title": "original", "description": "floral", "tags": ["flower"]},
        })
    assert export_approved_csv(tmp_path / "first.csv", "redbubble", root=tmp_path) == 3
    assert len(count) == 3
    assert export_approved_csv(tmp_path / "second.csv", "redbubble", root=tmp_path) == 3
    assert len(count) == 3


def test_missing_ocr_is_not_negative_cached(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr("podbot.publishing.audit_image", lambda image, platform: [])
    monkeypatch.setattr(
        "podbot.ocr_cache.scan_ocr",
        lambda image: (calls.append(1) or OCRReport(False, "", "engine missing")),
    )
    path = tmp_path / "print.png"
    Image.new("RGBA", (20, 20), (0, 0, 0, 0)).save(path)
    record = {"print_file": str(path), "rights_confirmed_at": "yes", "seo": {}}
    for _ in range(2):
        checks = validate_listing(record, "teepublic", blocklist=[])
        assert any(c["name"] == "ocr_text" and c["level"] == "warn" for c in checks)
    assert len(calls) == 2


@pytest.mark.parametrize("phrase", [
    "tour dates for", "for a mountain", "a mountain", "mountain to",
    "of a flower", "design in", "in the sky", "tour for",
])
def test_keyword_suggestions_reject_function_words_on_edges(phrase):
    phrases = keyword_suggestions("mountain tour dates", (phrase + " today",))
    assert phrase not in phrases


def test_keyword_suggestions_include_useful_exact_phrase():
    terms = keyword_suggestions("mountain tour dates", ("Best mountain tour dates for 2027",))
    assert "mountain tour dates" in terms
    assert all(phrase.split()[0].casefold() not in {"a", "for", "to", "of", "in"}
               for phrase in terms)
    assert all(phrase.split()[-1].casefold() not in {"a", "for", "to", "of", "in"}
               for phrase in terms)


def test_openai_list_check_no_paid_post_or_keys_in_url(monkeypatch):
    captured = []

    def fake_get(url, headers):
        captured.append((url, headers))
        return {"data": [
            {"id": "gpt-image-3-alpha", "owned_by": "openai"},
            {"id": "gpt-6", "owned_by": "openai"},
        ]}

    monkeypatch.setattr(model_discovery, "_get_json", fake_get)
    result = model_discovery.discover_models(
        "openai", {"OPENAI_API_KEY": "very-secret-token"}
    )
    assert result.verified
    assert len(result.models) == 2
    assert any(m.id == "gpt-image-3-alpha" and m.compatible for m in result.models)
    assert any(m.id == "gpt-6" and not m.compatible for m in result.models)
    assert "very-secret-token" not in repr(result)
    assert captured == [("https://api.openai.com/v1/models",
                         {"Authorization": "Bearer very-secret-token"})]


def test_gemini_list_pages_and_new_image_models(monkeypatch):
    urls = []

    def fake_get(url, headers):
        urls.append(url)
        assert headers["x-goog-api-key"] == "secret"
        if "pageToken" not in url:
            return {"models": [
                {"name": "models/gemini-3.8-image-pro",
                 "supportedGenerationMethods": ["generateContent"]},
                {"name": "models/gemini-3.8-text",
                 "supportedGenerationMethods": ["generateContent"]},
            ], "nextPageToken": "abc"}
        return {"models": [{"name": "models/nano-banana-4",
                            "supportedGenerationMethods": ["generateContent"]}]}

    monkeypatch.setattr(model_discovery, "_get_json", fake_get)
    result = model_discovery.discover_models("gemini", {"GEMINI_API_KEY": "secret"})
    assert len(urls) == 2
    assert len([m for m in result.models if m.compatible]) == 2
    specs = provider_catalog.set_discovered_models("gemini", result.models)
    try:
        assert len(specs) == 2
        assert provider_catalog.get_spec("discovered:gemini:gemini-3.8-image-pro").model == (
            "gemini-3.8-image-pro"
        )
        with pytest.raises(PermissionError):
            provider_catalog.make_provider("discovered:gemini:gemini-3.8-image-pro",
                                           {"GEMINI_API_KEY": "secret"})
    finally:
        provider_catalog.set_discovered_models("gemini", [])


def test_unverified_fal_model_list_does_not_claim_valid_key():
    result = model_discovery.discover_models("fal", {"FAL_KEY": "some-value"})
    assert not result.verified
    assert result.models == ()


def test_model_probe_refuses_network_or_invalid_key_without_leaking(monkeypatch):
    def fake_get(url, headers):
        raise urllib.error.URLError("Authorization: Bearer secret")

    monkeypatch.setattr(model_discovery, "_get_json", fake_get)
    with pytest.raises(urllib.error.URLError):
        model_discovery.discover_models("openai", {"OPENAI_API_KEY": "secret"})
    with pytest.raises(ValueError, match="Missing"):
        model_discovery.discover_models("gemini", {})
