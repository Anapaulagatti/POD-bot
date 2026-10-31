"""Tests use in-memory fake HTTP responses, never call billed providers."""

import base64
import io
import urllib.error
from pathlib import Path
import pytest
from PIL import Image

from podbot import provider_catalog as catalog


def png64() -> str:
    memory = io.BytesIO()
    Image.new("RGBA", (32, 48), (50, 100, 200, 0)).save(memory, "PNG")
    return base64.b64encode(memory.getvalue()).decode()


def test_all_image_choices_have_distinct_model_ids_and_cost_flags():
    assert len(catalog.CATALOG) >= 12
    assert len(catalog.MODELS) == len(catalog.CATALOG)
    assert len({entry.label for entry in catalog.CATALOG}) == len(catalog.CATALOG)
    assert catalog.get_spec("gemini-pro").model == "gemini-3-pro-image"
    assert catalog.get_spec("openai-flare").paid
    assert not catalog.get_spec("cloudflare").paid


def test_paid_provider_fails_closed_without_consent(monkeypatch):
    calls = []
    monkeypatch.setattr(catalog, "_call", lambda *args, **kwargs: calls.append(args))
    with pytest.raises(PermissionError, match="explicit consent"):
        catalog.make_provider("openai-flare", {"OPENAI_API_KEY": "fake"})
    with pytest.raises(ValueError, match="Missing"):
        catalog.make_provider("openai-flare", {}, allow_paid=True)
    assert not calls


def test_gemini_image_contract_and_resolution(monkeypatch):
    requests = []

    def fake_request(url, body, headers, timeout=180):
        requests.append((url, body, headers))
        return {"candidates": [{"content": {"parts": [
            {"text": "extra description"},
            {"inlineData": {"mimeType": "image/png", "data": png64()}},
        ]}}]}

    monkeypatch.setattr(catalog, "_call", fake_request)
    provider = catalog.make_provider("gemini-pro", {"GEMINI_API_KEY": "test-secret"},
                                     allow_paid=True, gemini_size="4K")
    image = provider.generate("original botanical art")
    assert image.size == (32, 48)
    url, body, headers = requests[0]
    assert url.endswith("/gemini-3-pro-image:generateContent")
    assert body["generationConfig"]["responseModalities"] == ["IMAGE"]
    assert body["generationConfig"]["imageConfig"]["imageSize"] == "4K"
    assert headers["x-goog-api-key"] == "test-secret"
    assert "test-secret" not in str(body)


def test_gemini_lite_cannot_be_forced_to_4k(monkeypatch):
    monkeypatch.setattr(catalog, "_call", lambda *args, **kwargs: {})
    provider = catalog.make_provider("gemini-flash-lite", {"GEMINI_API_KEY": "fake"},
                                     allow_paid=True, gemini_size="4K")
    assert provider.size == "1K"


def test_openai_transparent_png_parameters(monkeypatch):
    requests = []

    def fake_request(url, body, headers, timeout=180):
        requests.append((url, body, headers))
        return {"data": [{"b64_json": png64()}]}

    monkeypatch.setattr(catalog, "_call", fake_request)
    image = catalog.make_provider("openai-flare", {"OPENAI_API_KEY": "fake"},
                                  allow_paid=True).generate("a flower")
    assert image.mode == "RGBA"
    url, body, headers = requests[0]
    assert url == "https://api.openai.com/v1/images/generations"
    assert body["model"] == "gpt-image-2.5-flare"
    assert body["background"] == "transparent"
    assert body["output_format"] == "png"
    assert headers["Authorization"] == "Bearer fake"


def test_replicate_official_model_prediction_contract(monkeypatch):
    requests = []

    def fake_request(url, body, headers, timeout=180):
        requests.append((url, body, headers))
        return {"status": "succeeded", "output": [
            "https://replicate.delivery/pbxt/test/output.png"
        ]}

    def fake_download(url, vendor):
        assert vendor == "replicate"
        assert "replicate.delivery" in url
        return Image.new("RGB", (24, 24))

    monkeypatch.setattr(catalog, "_call", fake_request)
    monkeypatch.setattr(catalog, "_download", fake_download)
    image = catalog.make_provider("replicate-schnell",
                                  {"REPLICATE_API_TOKEN": "fake"}, allow_paid=True).generate("art")
    assert image.width == 24
    assert "/v1/models/black-forest-labs/flux-schnell/predictions" in requests[0][0]


def test_fal_flux_2_turbo_contract(monkeypatch):
    records = []

    def fake_request(url, body, headers, timeout=180):
        records.append((url, body, headers))
        return {"images": [{"url": "https://storage.googleapis.com/falserverless/abc.png"}]}

    monkeypatch.setattr(catalog, "_call", fake_request)
    monkeypatch.setattr(catalog, "_download", lambda url, vendor: Image.new("RGBA", (40, 40)))
    image = catalog.make_provider("fal-turbo", {"FAL_KEY": "fake"},
                                  allow_paid=True).generate("art")
    assert image.width == 40
    assert records[0][0] == "https://fal.run/fal-ai/flux-2/turbo"
    assert records[0][2]["Authorization"] == "Key fake"
    assert records[0][1]["num_images"] == 1


def test_stability_contract_is_multipart_without_key_in_body(monkeypatch):
    requests = []
    data = base64.b64decode(png64())

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self, n=-1):
            return data

    def fake_open(request, timeout):
        requests.append(request)
        return FakeResponse()

    monkeypatch.setattr(catalog.urllib.request, "urlopen", fake_open)
    provider = catalog.make_provider("stability-core", {"STABILITY_API_KEY": "fake"},
                                     allow_paid=True)
    assert provider.generate("art").size == (32, 48)
    request = requests[0]
    assert request.full_url.endswith("stable-image/generate/core")
    assert b'name="prompt"' in request.data
    assert b"fake" not in request.data
    assert request.get_header("Authorization") == "Bearer fake"


def test_untrusted_image_urls_are_rejected_before_network(monkeypatch):
    monkeypatch.setattr(catalog.urllib.request, "build_opener",
                        lambda *args: pytest.fail("unexpected external fetch"))
    for url in ("http://replicate.delivery/real.png",
                "https://127.0.0.1/private.png",
                "https://replicate.delivery.evil.test/one.png",
                "https://user:pass@replicate.delivery/x.png"):
        with pytest.raises(RuntimeError, match="Untrusted"):
            catalog._download(url, "replicate")


def test_openai_http_error_does_not_leak_credentials(monkeypatch):
    def fail(*args, **kwargs):
        raise urllib.error.HTTPError(
            "https://api.openai.com", 402, "fake-secret sensitive",
            {}, None
        )

    monkeypatch.setattr(catalog.urllib.request, "urlopen", fail)
    with pytest.raises(RuntimeError) as caught:
        catalog.make_provider("openai-sunburst",
                              {"OPENAI_API_KEY": "fake-secret"}, allow_paid=True).generate("test")
    assert "fake-secret" not in str(caught.value)


def test_image_response_rejects_oversized_or_invalid_bytes():
    with pytest.raises(RuntimeError):
        catalog._check_image(b"not an image")
    with pytest.raises(RuntimeError):
        catalog._check_image(b"Z" * (catalog.MAX_IMAGE_BYTES + 1))


def test_model_catalog_does_not_include_retired_image_endpoints():
    for spec in catalog.CATALOG:
        assert not any(old in spec.model for old in (
            "dall-e-", "gpt-image-1", "-preview",
        ))



def test_local_import_does_not_call_image_api(tmp_path, monkeypatch):
    from podbot.importer import import_design
    monkeypatch.setenv("PODBOT_DATA_DIR", str(tmp_path))
    source = tmp_path / "my-art.png"
    Image.new("RGBA", (90, 100), (0, 90, 170, 240)).save(source)
    entry = import_design(source, "original abstract", "blue, nature", root=tmp_path / "designs")
    assert entry["ai_generated"] is False
    assert entry["model_id"] == "local-import"
    assert entry["platform_status"]["redbubble"] == "draft"
    assert Path(entry["source_file"]).is_file()


def test_bad_local_file_rejected_before_creating_design(tmp_path):
    from podbot.importer import import_design
    fake = tmp_path / "malware.exe"
    fake.write_bytes(b"not an image")
    with pytest.raises(ValueError, match="Only PNG"):
        import_design(fake, "flowers", root=tmp_path / "designs")
    assert not (tmp_path / "designs").exists()
