"""Free API Radar tests: public metadata, TTL, scoped keys and no silent billing."""

from __future__ import annotations

import base64
import io
import json
import urllib.request

import pytest
from PIL import Image

from podbot import free_api_radar, model_discovery, provider_catalog
from podbot.auth_transport import NoCredentialRedirect, open_authenticated


OFFERS = [
    {"id": "tongyi-mai/z-image-turbo", "name": "Z Image Turbo",
     "paid_only": False, "output_modalities": ["image"],
     "supported_endpoints": ["/v1/images/generations"]},
    {"id": "openai/gpt-image-2", "paid_only": True,
     "supported_endpoints": ["/v1/images/generations"]},
    {"id": "community/unknown-free", "paid_only": False,
     "output_modalities": ["text"]},
    {"id": "mystery/unverified", "output_modalities": ["image"]},
]


def test_catalog_does_not_mistake_quest_credits_for_zero_dollars():
    result = free_api_radar.parse_image_offers(OFFERS)
    assert len(result) == 4
    allowed = [model for model in result if model.image_adapter]
    assert [item.model_id for item in allowed] == ["tongyi-mai/z-image-turbo"]
    assert "NOT a zero-cost" in allowed[0].warning
    assert any(model.access == "paid-only" for model in result)
    assert any(model.access == "unknown" for model in result)
    assert not free_api_radar.parse_image_offers(
        [{"id": "x/unknown", "supported_endpoints": ["/v1/images/generations"]}]
    )[0].image_adapter


def test_public_catalog_refresh_is_cached_and_never_sends_credentials(monkeypatch):
    requests = []

    class Response:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
        def read(self, size):
            return json.dumps(OFFERS).encode("utf-8")

    def fake_open(request, *, timeout):
        requests.append((request, timeout))
        return Response()

    monkeypatch.setattr(free_api_radar, "_CACHE", None)
    monkeypatch.setattr(free_api_radar, "open_authenticated", fake_open)
    first = free_api_radar.refresh_public_catalog(now=1000)
    second = free_api_radar.refresh_public_catalog(now=1100)
    third = free_api_radar.refresh_public_catalog(now=1000 + free_api_radar.REFRESH_SECONDS + 1)
    assert first is second
    assert first is not third
    assert len(requests) == 2
    for request, timeout in requests:
        assert request.get_method() == "GET"
        assert request.full_url == free_api_radar.CATALOG_URL
        assert not request.has_header("Authorization")
        assert timeout == 12


def test_public_catalog_rejects_redirect_or_truncated_body(monkeypatch):
    from podbot import auth_transport
    real = auth_transport.open_authenticated
    with pytest.raises(ValueError, match="unapproved"):
        real(urllib.request.Request("https://gen.pollinations.ai.evil.test/models"),
             timeout=1)
    with pytest.raises(RuntimeError, match="protect API credentials"):
        NoCredentialRedirect().redirect_request(
            urllib.request.Request("https://gen.pollinations.ai/image/models"),
            None, 302, "redirect", {},
            "https://third-party.test/collect",
        )
    class Oversized:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
        def read(self, size):
            return b"x" * size
    monkeypatch.setattr(free_api_radar, "open_authenticated",
                        lambda *args, **kwargs: Oversized())
    monkeypatch.setattr(free_api_radar, "_CACHE", None)
    with pytest.raises(RuntimeError, match="size limit"):
        free_api_radar.refresh_public_catalog(force=True)


def test_pollinations_key_probe_is_read_only_before_model_selection(monkeypatch):
    calls = []
    def identity(url, headers):
        calls.append((url, headers))
        return {"id": "key-123", "permissions": ["image"]}
    monkeypatch.setattr(model_discovery, "_get_json", identity)
    snapshot = free_api_radar.CatalogSnapshot(
        free_api_radar.parse_image_offers(OFFERS), fetched_at=300.0
    )
    monkeypatch.setattr(model_discovery, "refresh_public_catalog", lambda: snapshot)
    result = model_discovery.discover_models(
        "pollinations", {"POLLINATIONS_API_KEY": "sk_secret-123"}
    )
    assert result.verified
    assert sum(m.compatible for m in result.models) == 1
    assert calls == [("https://gen.pollinations.ai/account/key",
                      {"Authorization": "Bearer sk_secret-123"})]
    assert "secret-123" not in repr(result)
    assert "MAY SPEND Pollen" in result.message


def test_registration_and_provider_require_explicit_spend_consent(monkeypatch):
    snapshot = free_api_radar.CatalogSnapshot(
        free_api_radar.parse_image_offers(OFFERS), 100
    )
    candidates = [
        model_discovery.DiscoveredModel(o.model_id, o.name, o.image_adapter, o.warning)
        for o in snapshot.offers
    ]
    models = provider_catalog.set_discovered_models("pollinations", candidates)
    try:
        assert len(models) == 1
        assert models[0].paid is True
        with pytest.raises(PermissionError):
            provider_catalog.make_provider(models[0].id, {"POLLINATIONS_API_KEY": "sk_example"})
        provider = provider_catalog.make_provider(
            models[0].id, {"POLLINATIONS_API_KEY": "sk_example"}, allow_paid=True
        )
        assert isinstance(provider, provider_catalog.MeteredImageProvider)
        with pytest.raises(ValueError, match="secret key"):
            provider_catalog.PollinationsImage(models[0].model, "pk_public").validate_request()
    finally:
        provider_catalog.set_discovered_models("pollinations", [])


def test_pollinations_image_post_uses_only_one_bounded_api_call(monkeypatch):
    original = Image.new("RGBA", (12, 16), (12, 40, 80, 230))
    stream = io.BytesIO()
    original.save(stream, "PNG")
    encoded = base64.b64encode(stream.getvalue()).decode()
    requests = []
    def fake_call(url, body, headers, timeout=180):
        requests.append((url, body, headers, timeout))
        return {"data": [{"b64_json": encoded}]}
    monkeypatch.setattr(provider_catalog, "_call", fake_call)
    image = provider_catalog.PollinationsImage(
        "tongyi-mai/z-image-turbo", "sk_test-only"
    ).generate("an original mountain badge")
    assert image.size == (12, 16)
    assert len(requests) == 1
    url, body, headers, timeout = requests[0]
    assert url == "https://gen.pollinations.ai/v1/images/generations"
    assert "sk_test-only" not in url and "sk_test-only" not in json.dumps(body)
    assert headers == {"Authorization": "Bearer sk_test-only"}
    assert body["n"] == 1 and body["response_format"] == "b64_json"
    assert timeout == 120


def test_pollinations_unknown_image_format_never_retries(monkeypatch):
    calls = []
    def wrong_response(*args, **kwargs):
        calls.append(1)
        return {"data": [{"url": "https://untrusted.test/img.png"}]}
    monkeypatch.setattr(provider_catalog, "_call", wrong_response)
    with pytest.raises(RuntimeError, match="no retry"):
        provider_catalog.PollinationsImage(
            "tongyi-mai/z-image-turbo", "sk_test-only"
        ).generate("plant")
    assert calls == [1]
