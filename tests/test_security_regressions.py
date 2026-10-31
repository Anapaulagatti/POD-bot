"""Security regressions: API response caps, rembg opt-in, no API key disclosure."""

import io
import json
import sys
import types

import pytest
from PIL import Image

from podbot.http_utils import CLOUDFLARE_JSON_LIMIT, read_limited_json
from podbot.processing import ProcessOptions, process_image
from podbot.provider_catalog import OpenAIImage


def test_bounded_json_does_not_read_unlimited_bytes():
    class Response:
        def __init__(self, contents):
            self.value = contents
            self.read_size = None

        def read(self, amount):
            self.read_size = amount
            return self.value[:amount]

    response = Response(json.dumps({"ok": True}).encode())
    assert read_limited_json(response, 100) == {"ok": True}
    assert response.read_size == 101
    oversized = Response(b"{" + b"x" * 200)
    with pytest.raises(RuntimeError, match="size limit"):
        read_limited_json(oversized, 100)
    assert oversized.read_size == 101
    with pytest.raises(TypeError):
        read_limited_json(Response(b"[1,2,3]"), 100)


def test_cloudflare_json_limit_has_bounded_ceiling():
    assert 2 * 1024 * 1024 <= CLOUDFLARE_JSON_LIMIT <= 32 * 1024 * 1024


def test_rembg_python_optional_backend_does_not_need_exe(monkeypatch, tmp_path):
    class FakeModule(types.ModuleType):
        def new_session(self, model):
            assert model == "isnet-general-use"
            return object()

        def remove(self, image, session):
            result = Image.new("RGBA", image.size, (0, 0, 0, 0))
            result.paste((255, 255, 255, 255), (12, 12, 45, 45))
            return result

    monkeypatch.setitem(sys.modules, "rembg", FakeModule("rembg"))
    target = tmp_path / "result.png"
    metadata = process_image(
        Image.new("RGB", (80, 80), "white"),
        target,
        ProcessOptions(remove_background=True, target_size=(250, 280)),
    )
    assert "rembg-python:isnet-general-use" in metadata["steps"]
    with Image.open(target) as output:
        assert output.getpixel((0, 0))[3] == 0


def test_openai_http_400_is_explicit_without_retry(monkeypatch):
    calls = []

    def failing(*args, **kwargs):
        calls.append(1)
        raise RuntimeError("Provider HTTP 400. Check key, credits, model and quota.")

    monkeypatch.setattr("podbot.provider_catalog._call", failing)
    with pytest.raises(RuntimeError, match="transparent PNG"):
        OpenAIImage("gpt-image-2.5-flare", "redacted").generate("Original floral art")
    assert len(calls) == 1
