"""Contract regressions: avoid paid Gemini parameter guesses and bad Trends pruning."""

import io

import pytest
from PIL import Image

from podbot import provider_catalog as catalog
from podbot.api_limits import get_daily_limit, set_daily_limit
from podbot.model_discovery import DiscoveredModel
from podbot.trends import keyword_suggestions


def _model(model: str, vendor: str = "gemini") -> DiscoveredModel:
    return DiscoveredModel(model, model, True, "Listed, not generated")


def _image_data() -> str:
    import base64

    data = io.BytesIO()
    Image.new("RGBA", (4, 6), (40, 70, 120, 255)).save(data, "PNG")
    return base64.b64encode(data.getvalue()).decode()


def test_unknown_gemini_has_no_guessed_image_size_or_ratio(monkeypatch):
    captured = []

    def stub(url, body, headers):
        captured.append(body)
        return {"candidates": [{"content": {"parts": [
            {"inlineData": {"mimeType": "image/png", "data": _image_data()}}
        ]}}]}

    monkeypatch.setattr(catalog, "_call", stub)
    image = catalog.GeminiImage("gemini-4.5-image", "test-key", size="4K").generate("leaf")
    assert image.size == (4, 6)
    assert captured[0]["generationConfig"] == {"responseModalities": ["IMAGE"]}
    assert "imageConfig" not in captured[0]["generationConfig"]


def test_known_gemini_retains_audited_image_size_contract(monkeypatch):
    params = []
    monkeypatch.setattr(catalog, "_call", lambda url, body, headers: (
        params.append(body) or {"candidates": [{"content": {"parts": [
            {"inlineData": {"mimeType": "image/png", "data": _image_data()}}
        ]}}]}
    ))
    catalog.GeminiImage("gemini-nano-banana-2.1", "key", size="2K").generate("a flower")
    assert params[0]["generationConfig"]["imageConfig"] == {
        "aspectRatio": "4:5", "imageSize": "2K"
    }


def test_gemini_bad_configuration_does_not_reserve_paid_attempt(monkeypatch, tmp_path):
    monkeypatch.setenv("PODBOT_DATA_DIR", str(tmp_path))
    monkeypatch.delenv("PODBOT_PAID_CALLS_PER_DAY", raising=False)
    set_daily_limit(1)
    assert get_daily_limit() == 1
    called = []
    monkeypatch.setattr(catalog, "_call", lambda *args, **kwargs: called.append(1))
    provider = catalog.MeteredImageProvider(
        catalog.GeminiImage("gemini-nano-banana-2.1", "key", size="8K"),
        "gemini", "gemini"
    )
    with pytest.raises(ValueError, match="Invalid Gemini image size"):
        provider.generate("test")
    assert not called
    from podbot.api_limits import reserve_paid_request
    assert reserve_paid_request("gemini") == 1


def test_gemini_http_400_explains_counted_attempt_without_retry(monkeypatch):
    calls = []

    def reject(*args, **kwargs):
        calls.append(1)
        raise RuntimeError("Provider HTTP 400. Check key and model.")

    monkeypatch.setattr(catalog, "_call", reject)
    with pytest.raises(RuntimeError, match="counted toward the daily safety"):
        catalog.GeminiImage("gemini-new-image", "key").generate("test")
    assert len(calls) == 1


def test_catalog_model_listed_only_once_and_reuses_known_adapter():
    before = len(catalog.LABELS)
    values = [
        _model("gpt-image-2.5-flare", "openai"),
        _model("gpt-image-2.5-flare", "openai"),
        _model("gpt-image-4-new", "openai"),
    ]
    found = catalog.set_discovered_models("openai", values)
    try:
        assert [spec.model for spec in found] == [
            "gpt-image-2.5-flare", "gpt-image-4-new"
        ]
        assert found[0].id == "openai-flare"
        assert len([label for label, ident in catalog.LABELS.items()
                    if catalog.get_spec(ident).model == "gpt-image-2.5-flare"]) == 1
        assert len(catalog.LABELS) == before + 1
    finally:
        catalog.set_discovered_models("openai", [])


def test_existing_replicate_and_cloudflare_presets_reused_if_discovered():
    for vendor, model, expected in [
        ("replicate", "black-forest-labs/flux-schnell", "replicate-schnell"),
        ("cloudflare", "@cf/black-forest-labs/flux-1-schnell", "cloudflare"),
    ]:
        try:
            found = catalog.set_discovered_models(vendor, [_model(model, vendor)])
            assert [spec.id for spec in found] == [expected]
        finally:
            catalog.set_discovered_models(vendor, [])


def test_new_york_marathon_not_turned_into_york_marathon():
    keywords = keyword_suggestions(
        "New York marathon",
        ("New York marathon runners prepare for race day",)
    )
    assert keywords[0] == "New York marathon"
    assert "New York" in keywords
    assert "York marathon" in keywords or "New York marathon" in keywords
    assert "for a mountain" not in keywords
