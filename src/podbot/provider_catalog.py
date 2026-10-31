"""Opt-in image model catalog with official REST adapters. No model fallback or key storage.

Limits: API schemas/quotas/prices can change. Credentials only in memory or environment.
All paid calls require explicit UI/CLI confirmation before factory invocation.
"""

from __future__ import annotations

import base64
import io
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any

from PIL import Image

from podbot.providers import CloudflareFluxProvider, HuggingFaceProvider

MAX_IMAGE_BYTES = 30 * 1024 * 1024
MAX_JSON_BYTES = 2 * 1024 * 1024


@dataclass(frozen=True)
class ModelSpec:
    id: str
    label: str
    vendor: str
    model: str
    env_key: str
    paid: bool
    hint: str


CATALOG = (
    ModelSpec("cloudflare", "Cloudflare · FLUX.1 Schnell (quota)", "cloudflare",
              "@cf/black-forest-labs/flux-1-schnell", "CLOUDFLARE_API_TOKEN", False,
              "Allowance and eligibility depend on Cloudflare account."),
    ModelSpec("huggingface", "Hugging Face · FLUX Schnell (credits)", "huggingface",
              "black-forest-labs/FLUX.1-schnell", "HF_TOKEN", False,
              "Free credits are limited; usage beyond credits may cost money."),
    ModelSpec("gemini-flash-lite", "Gemini · 3.1 Flash Lite Image (paid)", "gemini",
              "gemini-3.1-flash-lite-image", "GEMINI_API_KEY", True,
              "Fast, native 1K image output; token billed."),
    ModelSpec("gemini-flash", "Gemini · 3.1 Flash Image (paid)", "gemini",
              "gemini-3.1-flash-image", "GEMINI_API_KEY", True,
              "Supports 1K/2K/4K with eligible paid account."),
    ModelSpec("gemini-pro", "Gemini · 3 Pro Image (paid)", "gemini",
              "gemini-3-pro-image", "GEMINI_API_KEY", True,
              "High-quality 1K/2K/4K generation, token billed."),
    ModelSpec("openai-flare", "OpenAI · GPT Image 2.5 Flare (paid)", "openai",
              "gpt-image-2.5-flare", "OPENAI_API_KEY", True,
              "Transparent PNG generation; OpenAI image API billing."),
    ModelSpec("openai-sunburst", "OpenAI · GPT Image 2.5 Sunburst (paid)", "openai",
              "gpt-image-2.5-sunburst", "OPENAI_API_KEY", True,
              "High fidelity transparent PNG; OpenAI image API billing."),
    ModelSpec("replicate-schnell", "Replicate · FLUX.1 Schnell (paid)", "replicate",
              "black-forest-labs/flux-schnell", "REPLICATE_API_TOKEN", True,
              "Image billed per successful output."),
    ModelSpec("replicate-dev", "Replicate · FLUX.1 Dev (paid)", "replicate",
              "black-forest-labs/flux-dev", "REPLICATE_API_TOKEN", True,
              "Billed hosted image generation."),
    ModelSpec("fal-turbo", "fal.ai · FLUX.2 Turbo (paid)", "fal",
              "fal-ai/flux-2/turbo", "FAL_KEY", True,
              "Billed by output size; official fal synchronous REST endpoint."),
    ModelSpec("fal-z-image", "fal.ai · Z-Image Turbo (paid)", "fal",
              "fal-ai/z-image/turbo", "FAL_KEY", True,
              "Billed hosted image generation, quality and availability vary."),
    ModelSpec("stability-core", "Stability AI · Stable Image Core (paid)", "stability",
              "core", "STABILITY_API_KEY", True, "Credit-billed text-to-image."),
    ModelSpec("stability-ultra", "Stability AI · Stable Image Ultra (paid)", "stability",
              "ultra", "STABILITY_API_KEY", True, "Premium credit-billed text-to-image."),
)
MODELS = {item.id: item for item in CATALOG}
LABELS = {item.label: item.id for item in CATALOG}


def _check_image(payload: bytes) -> Image.Image:
    if not payload or len(payload) > MAX_IMAGE_BYTES:
        raise RuntimeError("Image was empty or exceeded safety limit.")
    try:
        with Image.open(io.BytesIO(payload)) as original:
            original.verify()
        with Image.open(io.BytesIO(payload)) as original:
            if original.width * original.height > 64_000_000:
                raise RuntimeError("Image pixel count is above safe limit.")
            original.load()
            return original.copy()
    except (OSError, ValueError) as exc:
        raise RuntimeError("API returned invalid image data.") from exc


def _decode(data: str) -> Image.Image:
    try:
        encoded = data.split(",", 1)[-1] if data.startswith("data:image/") else data
        if len(encoded) > MAX_IMAGE_BYTES * 2:
            raise RuntimeError("Image response exceeded size limit.")
        return _check_image(base64.b64decode(encoded, validate=True))
    except (ValueError, base64.binascii.Error) as exc:
        raise RuntimeError("API returned malformed base64 image data.") from exc


def _call(url: str, body: dict | None, headers: dict[str, str],
          timeout: int = 180) -> dict[str, Any]:
    data = None if body is None else json.dumps(body).encode("utf-8")
    request = urllib.request.Request(
        url, data=data, method="GET" if data is None else "POST",
        headers={"Content-Type": "application/json", **headers},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read(MAX_JSON_BYTES + 1)
    except urllib.error.HTTPError as exc:
        # Do not echo upstream bodies: they can contain prompts or account data.
        raise RuntimeError(f"Provider HTTP {exc.code}. Check key, credits, model and quota.") from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise RuntimeError("Image provider network request failed.") from exc
    if len(raw) > MAX_JSON_BYTES:
        raise RuntimeError("Provider response exceeded maximum JSON size.")
    try:
        result = json.loads(raw)
        if not isinstance(result, dict):
            raise ValueError("not an object")
        return result
    except (ValueError, UnicodeError) as exc:
        raise RuntimeError("Provider returned malformed JSON.") from exc


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        raise RuntimeError("Image download redirected; manual source inspection required.")


def _download(url: str, vendor: str) -> Image.Image:
    parsed = urllib.parse.urlsplit(url)
    permitted = {
        "replicate": {"replicate.delivery", "pbxt.replicate.delivery"},
        "fal": {"fal.media", "v3.fal.media", "v3b.fal.media", "storage.googleapis.com"},
    }
    host = (parsed.hostname or "").lower()
    if (parsed.scheme != "https" or parsed.username or parsed.password
            or parsed.port not in (None, 443) or host not in permitted[vendor]):
        raise RuntimeError("Untrusted provider image host was rejected.")
    opener = urllib.request.build_opener(_NoRedirect())
    try:
        with opener.open(urllib.request.Request(url), timeout=60) as response:
            raw = response.read(MAX_IMAGE_BYTES + 1)
    except (urllib.error.URLError, TimeoutError) as exc:
        raise RuntimeError("Could not download provider image.") from exc
    return _check_image(raw)


@dataclass
class GeminiImage:
    model: str
    key: str
    size: str = "2K"
    name: str = "gemini-image"

    def generate(self, prompt: str) -> Image.Image:
        if not self.key:
            raise ValueError("Gemini API key is required.")
        allowed = {"gemini-3.1-flash-lite-image", "gemini-3.1-flash-image",
                   "gemini-3-pro-image"}
        if self.model not in allowed:
            raise ValueError("Gemini image model is not supported.")
        if self.size not in {"1K", "2K", "4K"}:
            raise ValueError("Invalid Gemini image size.")
        if self.model.endswith("flash-lite-image") and self.size != "1K":
            raise ValueError("Gemini Flash Lite supports 1K output.")
        body = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "responseModalities": ["IMAGE"],
                "imageConfig": {"aspectRatio": "4:5", "imageSize": self.size},
            },
        }
        result = _call(
            f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent",
            body, {"x-goog-api-key": self.key},
        )
        for candidate in result.get("candidates", []):
            for part in candidate.get("content", {}).get("parts", []):
                inline = part.get("inlineData") or part.get("inline_data") or {}
                if inline.get("data") and inline.get("mimeType", inline.get("mime_type", "image/png")).startswith("image/"):
                    return _decode(inline["data"])
        raise RuntimeError("Gemini did not return an image; verify model and prompt.")


@dataclass
class OpenAIImage:
    model: str
    key: str
    name: str = "openai-image"

    def generate(self, prompt: str) -> Image.Image:
        if not self.key:
            raise ValueError("OpenAI API key is required.")
        if self.model not in {"gpt-image-2.5-flare", "gpt-image-2.5-sunburst"}:
            raise ValueError("Unsupported OpenAI image model.")
        result = _call("https://api.openai.com/v1/images/generations", {
            "model": self.model, "prompt": prompt, "n": 1,
            "size": "1024x1536", "quality": "high",
            "background": "transparent", "output_format": "png",
        }, {"Authorization": f"Bearer {self.key}"})
        images = result.get("data") or []
        if not images or "b64_json" not in images[0]:
            raise RuntimeError("OpenAI did not return image bytes.")
        return _decode(images[0]["b64_json"])


@dataclass
class ReplicateImage:
    model: str
    key: str
    name: str = "replicate-image"

    def generate(self, prompt: str) -> Image.Image:
        if not self.key:
            raise ValueError("Replicate API token is required.")
        if self.model not in {"black-forest-labs/flux-schnell", "black-forest-labs/flux-dev"}:
            raise ValueError("Unsupported Replicate official model.")
        result = _call(
            f"https://api.replicate.com/v1/models/{self.model}/predictions",
            {"input": {"prompt": prompt, "aspect_ratio": "4:5",
                       "output_format": "png", "num_outputs": 1}},
            {"Authorization": f"Bearer {self.key}", "Prefer": "wait=60"},
            timeout=75,
        )
        for _ in range(15):
            status = result.get("status")
            if status == "succeeded":
                outputs = result.get("output") or []
                if not outputs:
                    raise RuntimeError("Replicate returned an empty output.")
                url = outputs[0] if isinstance(outputs, list) else outputs
                if not isinstance(url, str):
                    raise RuntimeError("Replicate output is not a URL.")
                return _download(url, "replicate")
            if status in {"failed", "canceled"}:
                raise RuntimeError("Replicate prediction failed or was cancelled.")
            prediction_id = result.get("id", "")
            if not re.fullmatch(r"[A-Za-z0-9_-]{8,100}", prediction_id):
                raise RuntimeError("Replicate returned an invalid prediction ID.")
            time.sleep(2)
            result = _call(
                f"https://api.replicate.com/v1/predictions/{prediction_id}",
                None, {"Authorization": f"Bearer {self.key}"}, timeout=30,
            )
        raise RuntimeError("Replicate prediction still pending; verify job in your dashboard.")


@dataclass
class FalImage:
    model: str
    key: str
    name: str = "fal-image"

    def generate(self, prompt: str) -> Image.Image:
        if not self.key:
            raise ValueError("fal.ai API key is required.")
        if self.model not in {"fal-ai/flux-2/turbo", "fal-ai/z-image/turbo"}:
            raise ValueError("Unsupported fal.ai image model.")
        result = _call(f"https://fal.run/{self.model}", {
            "prompt": prompt, "image_size": "portrait_4_3",
            "output_format": "png", "num_images": 1,
        }, {"Authorization": f"Key {self.key}"}, timeout=210)
        outputs = result.get("images") or []
        if not outputs:
            raise RuntimeError("fal.ai returned no images.")
        url = outputs[0].get("url", "")
        if url.startswith("data:image/"):
            return _decode(url)
        return _download(url, "fal")


@dataclass
class StabilityImage:
    model: str
    key: str
    name: str = "stability-image"

    def generate(self, prompt: str) -> Image.Image:
        if not self.key:
            raise ValueError("Stability API key is required.")
        if self.model not in {"core", "ultra"}:
            raise ValueError("Unsupported Stability image model.")
        boundary = "podbotmultipartboundary2026"
        params = {"prompt": prompt, "output_format": "png", "aspect_ratio": "4:5"}
        data = b"".join(
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"{key}\"\r\n\r\n{value}\r\n".encode()
            for key, value in params.items()
        ) + f"--{boundary}--\r\n".encode()
        request = urllib.request.Request(
            f"https://api.stability.ai/v2beta/stable-image/generate/{self.model}",
            data=data, method="POST",
            headers={
                "Authorization": f"Bearer {self.key}",
                "Accept": "image/*",
                "Content-Type": f"multipart/form-data; boundary={boundary}",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=180) as response:
                raw = response.read(MAX_IMAGE_BYTES + 1)
        except urllib.error.HTTPError as exc:
            raise RuntimeError(f"Stability HTTP {exc.code}. Verify credits/parameters.") from exc
        except (urllib.error.URLError, TimeoutError) as exc:
            raise RuntimeError("Stability connection failed.") from exc
        return _check_image(raw)


def get_spec(selection: str) -> ModelSpec:
    if selection not in MODELS:
        raise ValueError("Unknown model identifier; use models list.")
    return MODELS[selection]


def make_provider(
    selection: str, credentials: dict[str, str] | None = None, *,
    allow_paid: bool = False, gemini_size: str = "2K",
):
    spec = get_spec(selection)
    if spec.paid and not allow_paid:
        raise PermissionError("Paid model requires explicit consent before sending request.")
    creds = credentials or {}
    key = creds.get(spec.env_key, "").strip() or os.environ.get(spec.env_key, "").strip()
    if spec.vendor == "cloudflare":
        account = creds.get("CLOUDFLARE_ACCOUNT_ID", "") or os.environ.get("CLOUDFLARE_ACCOUNT_ID", "")
        if not account or not key:
            raise ValueError("Cloudflare Account ID/token are required.")
        provider = CloudflareFluxProvider(account_id=account, token=key)
    elif spec.vendor == "huggingface":
        if not key:
            raise ValueError("HF_TOKEN is required.")
        provider = HuggingFaceProvider(token=key)
    elif spec.vendor == "gemini":
        provider = GeminiImage(spec.model, key, size="1K" if selection == "gemini-flash-lite" else gemini_size)
    elif spec.vendor == "openai":
        provider = OpenAIImage(spec.model, key)
    elif spec.vendor == "replicate":
        provider = ReplicateImage(spec.model, key)
    elif spec.vendor == "fal":
        provider = FalImage(spec.model, key)
    elif spec.vendor == "stability":
        provider = StabilityImage(spec.model, key)
    else:
        raise ValueError("No adapter available for this model.")
    if not key:
        raise ValueError(f"Missing {spec.env_key}; enter it in Settings or environment.")
    provider.name = f"{spec.vendor}:{spec.model}"
    return provider
