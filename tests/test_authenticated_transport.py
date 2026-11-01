"""Authenticated requests never forward provider keys through redirects."""

import base64
import io
import json
import urllib.error
import urllib.request

import pytest
from PIL import Image

from podbot import provider_catalog as catalog
from podbot import providers
from podbot.auth_transport import NoCredentialRedirect, open_authenticated


class FakeResponse:
    def __init__(self, data):
        self.data = data

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self, limit=None):
        return self.data if limit is None else self.data[:limit]


def test_authenticated_transport_rejects_untrusted_destinations(monkeypatch):
    monkeypatch.setattr(
        urllib.request, "build_opener",
        lambda *_: pytest.fail("untrusted URL must not reach the network"),
    )
    for url in (
        "http://api.openai.com/v1/models",
        "https://api.openai.com.evil.test/v1/models",
        "https://attacker.test/steal",
        "https://user:password@api.openai.com/v1/models",
        "https://api.openai.com:8443/v1/models",
        "https://api.openai.com/v1/models#fragment",
    ):
        with pytest.raises(ValueError, match="unapproved"):
            open_authenticated(
                urllib.request.Request(url, headers={"Authorization": "Bearer secret"}),
                timeout=2,
            )


def test_authenticated_redirect_cannot_reuse_credentials():
    handler = NoCredentialRedirect()
    request = urllib.request.Request(
        "https://api.openai.com/v1/models",
        headers={"Authorization": "Bearer secret"},
    )
    with pytest.raises(RuntimeError, match="protect API credentials"):
        handler.redirect_request(
            request, None, 307, "Redirect", request.headers,
            "https://attacker.test/collect",
        )


def test_openai_post_uses_no_redirect_opener_and_keeps_key_in_header(monkeypatch):
    seen = []

    class FakeOpener:
        def open(self, request, timeout):
            seen.append((request, timeout))
            return FakeResponse(b'{"ok": true}')

    def create_opener(handler):
        assert isinstance(handler, NoCredentialRedirect)
        return FakeOpener()

    monkeypatch.setattr(urllib.request, "build_opener", create_opener)
    payload = catalog._call(
        "https://api.openai.com/v1/images/generations",
        {"model": "example"}, {"Authorization": "Bearer secret"},
    )
    assert payload == {"ok": True}
    request, timeout = seen[0]
    assert timeout == 180
    assert request.get_header("Authorization") == "Bearer secret"
    assert "secret" not in request.full_url


def test_cloudflare_generation_uses_secure_opener(monkeypatch):
    image = Image.new("RGB", (8, 8), "blue")
    stream = io.BytesIO()
    image.save(stream, "PNG")
    image_json = json.dumps({
        "success": True, "result": {"image": base64.b64encode(stream.getvalue()).decode()}
    }).encode()
    visited = []

    def fake_open(request, *, timeout):
        visited.append(request)
        return FakeResponse(image_json)

    monkeypatch.setattr(providers, "open_authenticated", fake_open)
    monkeypatch.setattr(
        urllib.request, "urlopen",
        lambda *_args, **_kwargs: pytest.fail("insecure urlopen must not be used"),
    )
    result = providers.CloudflareFluxProvider("a" * 32, "my-secret").generate("leaf")
    assert result.size == (8, 8)
    assert visited[0].get_header("Authorization") == "Bearer my-secret"


def test_stability_generation_uses_secure_opener(monkeypatch):
    source = Image.new("RGBA", (8, 8))
    memory = io.BytesIO()
    source.save(memory, "PNG")
    seen = []

    def fake_open(request, *, timeout):
        seen.append(request)
        return FakeResponse(memory.getvalue())

    monkeypatch.setattr(catalog, "open_authenticated", fake_open)
    assert catalog.StabilityImage("core", "secret").generate("flower").size == (8, 8)
    assert seen[0].get_header("Authorization") == "Bearer secret"
