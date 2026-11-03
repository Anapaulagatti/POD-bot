"""Gemini free-tier text discovery and deliberate text-only calls, no real credentials."""

import io
import json
import urllib.error

import pytest
from PIL import Image

from podbot import model_discovery, pipeline, seo
from podbot.model_discovery import GEMINI_FREE_TEXT_CANDIDATES, _gemini_text_models
from podbot.seo import SEOMetadata


MODELS = [
    {"name": "models/gemini-3.5-flash-lite", "displayName": "Gemini 3.5 Lite",
     "supportedGenerationMethods": ["generateContent"]},
    {"name": "models/gemini-3.1-flash-lite",
     "supportedGenerationMethods": ["generateContent"]},
    {"name": "models/gemini-2.5-flash-lite",
     "supportedGenerationMethods": ["generateContent"]},
    {"name": "models/gemini-3.1-flash-image",
     "supportedGenerationMethods": ["generateContent"]},
    {"name": "models/gemini-2.5-flash-tts",
     "supportedGenerationMethods": ["generateContent"]},
    {"name": "models/gemini-3.5-flash-lite", "supportedGenerationMethods": ["countTokens"]},
    {"name": "models/gemini-3.5-pro", "supportedGenerationMethods": ["countTokens"]},
]


def test_free_tier_text_models_are_listed_separately_not_as_image_models():
    text = _gemini_text_models(MODELS)
    assert {"gemini-2.5-flash-lite", "gemini-3.1-flash-lite",
            "gemini-3.5-flash-lite"} <= {x.id for x in text}
    assert all(x.id in GEMINI_FREE_TEXT_CANDIDATES for x in text)
    assert not any("image" in x.id or "tts" in x.id for x in text)
    images = model_discovery._clean_models(MODELS, "gemini")
    assert next(x for x in images if x.id == "gemini-3.5-flash-lite").compatible is False
    assert next(x for x in images if x.id == "gemini-3.1-flash-image").compatible is True


def test_gemini_key_listing_returns_text_and_image_separately(monkeypatch):
    seen = []

    def fake_get(url, headers):
        seen.append((url, headers))
        return {"models": MODELS}
    monkeypatch.setattr(model_discovery, "_get_json", fake_get)
    found = model_discovery.discover_models("gemini", {"GEMINI_API_KEY": "not-real"})
    assert found.verified is True
    assert any(item.id == "gemini-3.1-flash-lite" for item in found.seo_models)
    assert any(item.id == "gemini-3.1-flash-image" and item.compatible for item in found.models)
    assert "does NOT guarantee" in found.message
    assert len(seen) == 1
    assert seen[0][1]["x-goog-api-key"] == "not-real"
    assert "not-real" not in seen[0][0]


class Response:
    def __init__(self, obj):
        self.data = json.dumps(obj).encode("utf-8")
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False
    def read(self, n=-1):
        return self.data[:n]


def test_gemini_seo_uses_selected_flash_lite_instead_of_image_model(monkeypatch):
    requests = []
    reservations = []
    def fake_open(request, *, timeout):
        requests.append(request)
        assert timeout == 90
        return Response({"candidates": [{"content": {"parts": [{
            "text": json.dumps({"title": "Mountain Badge",
                                "description": "An original nature badge.",
                                "tags": ["mountains", "nature"]})
        }]}}]})
    monkeypatch.setattr(seo, "open_authenticated", fake_open)
    monkeypatch.setattr(seo, "reserve_paid_request", lambda vendor: reservations.append(vendor))
    result = seo.gemini_seo(
        "mountain", "nature", "original badge", "not-real",
        model="gemini-3.1-flash-lite",
    )
    assert result.title == "Mountain Badge"
    assert len(requests) == 1
    assert "/gemini-3.1-flash-lite:generateContent" in requests[0].full_url
    assert requests[0].get_header("X-goog-api-key") == "not-real"
    assert "not-real" not in requests[0].full_url
    assert reservations == ["gemini"]


def test_gemini_text_refine_only_one_call_and_no_image_output(monkeypatch):
    seen = []
    reservations = []

    def fake_open(request, *, timeout):
        seen.append((request, timeout))
        return Response({"candidates": [{"content": {"parts": [
            {"text": "Original minimalist mountain badge; solid chroma magenta background."}
        ]}}]})
    monkeypatch.setattr(seo, "open_authenticated", fake_open)
    monkeypatch.setattr(seo, "reserve_paid_request", lambda vendor: reservations.append(vendor))
    result = seo.gemini_refine_prompt(
        "Original gray mountain crest on magenta background", "not-real",
        model="gemini-3.5-flash-lite",
    )
    assert "mountain" in result
    assert len(seen) == 1
    request, timeout = seen[0]
    assert timeout == 90
    assert request.get_method() == "POST"
    assert request.full_url.endswith("/gemini-3.5-flash-lite:generateContent")
    data = json.loads(request.data)
    assert "responseModalities" not in json.dumps(data)
    assert "imageConfig" not in json.dumps(data)
    assert reservations == ["gemini"]


@pytest.mark.parametrize("model", ["../bad", "gemini-3-pro-image", ""])
def test_invalid_text_model_or_missing_key_rejected_without_metering(monkeypatch, model):
    called = []
    monkeypatch.setattr(seo, "reserve_paid_request", lambda *_: called.append(1))
    monkeypatch.setattr(seo, "open_authenticated", lambda *_a, **_kw: pytest.fail("API call"))
    with pytest.raises(ValueError):
        seo.gemini_refine_prompt(
            "Original botanical mountain print", "", model=model,
        )
    assert not called


def test_text_project_permission_error_is_actionable_and_has_no_retry(monkeypatch):
    calls = []
    monkeypatch.setattr(seo, "reserve_paid_request", lambda *_: None)
    def fail(*args, **kwargs):
        calls.append(1)
        raise urllib.error.HTTPError(
            "https://generativelanguage.googleapis.com", 403, "Forbidden", {}, io.BytesIO()
        )
    monkeypatch.setattr(seo, "open_authenticated", fail)
    with pytest.raises(RuntimeError, match="Free Tier unavailable"):
        seo.gemini_refine_prompt(
            "An original simple nature illustration", "not-real",
            model="gemini-3.5-flash-lite",
        )
    assert calls == [1]


def test_gemini_text_seo_model_is_recorded_in_manifest(monkeypatch, tmp_path):
    monkeypatch.setattr(pipeline, "PRINT_SIZE", (320, 380))
    seen = []

    def fake_seo(niche, keywords, prompt, key, *, model):
        seen.append(model)
        return SEOMetadata("Art Design", "Original vintage nature artwork.", ["nature"])

    class ImageProvider:
        name = "offline-test-image"
        def generate(self, prompt):
            return Image.new("RGBA", (90, 110), (50, 100, 150, 255))

    monkeypatch.setattr(pipeline, "gemini_seo", fake_seo)
    entry = pipeline.create_draft(
        "an original botanical badge", "outdoors", "nature", ImageProvider(),
        seo_mode="gemini", gemini_key="fake", root=tmp_path,
        gemini_seo_model="gemini-3.1-flash-lite",
    )
    assert seen == ["gemini-3.1-flash-lite"]
    assert entry["gemini_seo_model"] == "gemini-3.1-flash-lite"
    assert json.loads((tmp_path / entry["id"] / "manifest.json").read_text())[
        "gemini_seo_model"
    ] == "gemini-3.1-flash-lite"
