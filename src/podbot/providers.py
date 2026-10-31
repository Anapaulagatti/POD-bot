"""Interchangeable image generation providers. No paid fallback or credential storage."""

from __future__ import annotations

import base64
import io
import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Protocol

from PIL import Image


class ImageProvider(Protocol):
    name: str

    def generate(self, prompt: str) -> Image.Image: ...


@dataclass
class CloudflareFluxProvider:
    account_id: str = ""
    token: str = ""
    steps: int = 4
    name: str = "cloudflare-flux-1-schnell"

    def generate(self, prompt: str) -> Image.Image:
        account = self.account_id or os.environ.get("CLOUDFLARE_ACCOUNT_ID", "")
        token = self.token or os.environ.get("CLOUDFLARE_API_TOKEN", "")
        if not account or not token:
            raise ValueError("Cloudflare Account ID and API Token are required.")
        if not account.replace("-", "").isalnum():
            raise ValueError("Invalid Cloudflare Account ID.")
        if not 1 <= self.steps <= 8:
            raise ValueError("Cloudflare FLUX steps must be between 1 and 8.")
        url = (
            f"https://api.cloudflare.com/client/v4/accounts/{account}/ai/run/"
            "@cf/black-forest-labs/flux-1-schnell"
        )
        payload = json.dumps({"prompt": prompt[:2048], "steps": self.steps}).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=payload,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                result = json.load(response)
        except urllib.error.HTTPError as exc:
            raise RuntimeError(f"Cloudflare API returned HTTP {exc.code}.") from exc
        if result.get("success") is False:
            raise RuntimeError("Cloudflare rejected the generation request. Check quota/token.")
        encoded = (result.get("result") or {}).get("image")
        if not encoded:
            raise RuntimeError("Cloudflare returned no image.")
        try:
            binary = base64.b64decode(encoded, validate=True)
            image = Image.open(io.BytesIO(binary))
            image.load()
            return image
        except (ValueError, OSError) as exc:
            raise RuntimeError("Cloudflare returned an unreadable image.") from exc


@dataclass
class HuggingFaceProvider:
    token: str = ""
    model: str = "black-forest-labs/FLUX.1-schnell"
    name: str = "huggingface-inference"

    def generate(self, prompt: str) -> Image.Image:
        token = self.token or os.environ.get("HF_TOKEN", "")
        if not token:
            raise ValueError("HF_TOKEN is required.")
        try:
            from huggingface_hub import InferenceClient
        except ImportError as exc:
            raise RuntimeError('Install optional package: pip install -e ".[hf]"') from exc
        client = InferenceClient(api_key=token)
        image = client.text_to_image(prompt=prompt, model=self.model)
        image.load()
        return image
