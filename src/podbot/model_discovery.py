"""Opt-in, read-only provider key check and live model catalog discovery.

Never makes inference requests, sends keys in URLs, caches credentials to disk,
follows redirects, or claims a listed model has verified billing/generation access.
"""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass

from podbot.free_api_radar import refresh_public_catalog, verify_quest_only_key

MAX_DISCOVERY_JSON = 1024 * 1024
MODEL_ID = re.compile(r"@?[A-Za-z0-9][A-Za-z0-9_./:-]{1,150}\Z")
PROVIDER_KEYS = {
    "openai": "OPENAI_API_KEY",
    "gemini": "GEMINI_API_KEY",
    "replicate": "REPLICATE_API_TOKEN",
    "cloudflare": "CLOUDFLARE_API_TOKEN",
    "huggingface": "HF_TOKEN",
    "stability": "STABILITY_API_KEY",
    "fal": "FAL_KEY",
    "pollinations": "POLLINATIONS_API_KEY",
}


@dataclass(frozen=True)
class DiscoveredModel:
    id: str
    name: str
    compatible: bool
    note: str


@dataclass(frozen=True)
class DiscoveryResult:
    provider: str
    verified: bool
    models: tuple[DiscoveredModel, ...]
    message: str


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        raise RuntimeError("Provider redirected the credential check; request stopped.")


def _get_json(url: str, headers: dict[str, str]) -> dict:
    """One bounded GET to an app-owned endpoint with no redirect or retry."""
    request = urllib.request.Request(
        url, method="GET",
        headers={"Accept": "application/json", "User-Agent": "PODBotStudio/1.0", **headers},
    )
    opener = urllib.request.build_opener(_NoRedirect())
    try:
        with opener.open(request, timeout=12) as response:
            raw = response.read(MAX_DISCOVERY_JSON + 1)
    except urllib.error.HTTPError as exc:
        # Never include upstream response bodies or Authorization headers.
        raise RuntimeError(f"Model listing rejected (HTTP {exc.code}).") from None
    except (urllib.error.URLError, TimeoutError, OSError):
        raise RuntimeError("Model listing network request failed.") from None
    if len(raw) > MAX_DISCOVERY_JSON:
        raise RuntimeError("Provider model listing exceeded the response limit.")
    try:
        payload = json.loads(raw)
    except (ValueError, UnicodeError):
        raise RuntimeError("Provider returned malformed model JSON.") from None
    if not isinstance(payload, dict):
        raise TypeError("Model response is not an object.")
    return payload


def _clean_models(items: list[dict], vendor: str) -> tuple[DiscoveredModel, ...]:
    discovered: dict[str, DiscoveredModel] = {}
    for item in items[:300]:
        if not isinstance(item, dict):
            continue
        name = item.get("id") if vendor == "openai" else item.get("name")
        if vendor == "gemini" and isinstance(name, str):
            name = name.removeprefix("models/")
        if vendor == "replicate":
            owner, model = item.get("owner"), item.get("name")
            name = f"{owner}/{model}" if isinstance(owner, str) and isinstance(model, str) else ""
        if vendor == "cloudflare":
            name = item.get("name") or item.get("id")
        if not isinstance(name, str) or not MODEL_ID.fullmatch(name):
            continue
        image_candidate = (
            vendor == "openai" and name.startswith("gpt-image-")
            or vendor == "gemini" and (
                "image" in name.casefold() or "banana" in name.casefold()
            ) and "generateContent" in item.get("supportedGenerationMethods", [])
        )
        if vendor == "replicate":
            # Existing official-model adapter supports these exact schemas only.
            image_candidate = name in {
                "black-forest-labs/flux-schnell", "black-forest-labs/flux-dev"
            }
        if vendor == "cloudflare":
            image_candidate = name == "@cf/black-forest-labs/flux-1-schnell"
        discovered[name] = DiscoveredModel(
            id=name, name=str(item.get("displayName") or name)[:130],
            compatible=bool(image_candidate),
            note=("Compatible image API route, not yet billed-tested"
                  if image_candidate else "Listed only; image adapter not verified"),
        )
    return tuple(sorted(discovered.values(), key=lambda m: (not m.compatible, m.id))[:120])


def discover_models(provider: str, credentials: dict[str, str]) -> DiscoveryResult:
    """Verify selected key through list/identity, then show listed models, never infer."""
    if provider not in PROVIDER_KEYS:
        raise ValueError("Unknown provider.")
    key = credentials.get(PROVIDER_KEYS[provider], "").strip()
    if not key:
        raise ValueError("Missing provider API key.")
    if provider == "fal":
        return DiscoveryResult(
            provider, False, (),
            "fal: No verified free credential-specific model-list endpoint configured. "
            "Key and entitlement not yet verified; choose a documented preset manually.",
        )
    if provider == "gemini":
        headers = {"x-goog-api-key": key}
        items = []
        page_token = ""
        for _ in range(3):  # Explicit cap, never an unbounded crawl.
            query = "?pageSize=100"
            if page_token:
                query += "&pageToken=" + urllib.parse.quote(page_token, safe="")
            data = _get_json(
                "https://generativelanguage.googleapis.com/v1beta/models" + query, headers
            )
            chunk = data.get("models", [])
            if not isinstance(chunk, list):
                raise TypeError("Invalid Gemini model listing.")
            items.extend(chunk)
            page_token = data.get("nextPageToken") or ""
            if not page_token or not isinstance(page_token, str) or len(page_token) > 300:
                break
        models = _clean_models(items, provider)
    elif provider == "openai":
        data = _get_json("https://api.openai.com/v1/models",
                         {"Authorization": f"Bearer {key}"})
        if not isinstance(data.get("data"), list):
            raise RuntimeError("Invalid OpenAI model listing.")
        models = _clean_models(data["data"], provider)
    elif provider == "replicate":
        data = _get_json("https://api.replicate.com/v1/models",
                         {"Authorization": f"Bearer {key}"})
        if not isinstance(data.get("results"), list):
            raise RuntimeError("Invalid Replicate model listing.")
        models = _clean_models(data["results"], provider)
    elif provider == "cloudflare":
        account = credentials.get("CLOUDFLARE_ACCOUNT_ID", "").strip()
        if not re.fullmatch(r"[a-fA-F0-9]{32}", account):
            raise ValueError("Cloudflare requires a valid 32-character account ID.")
        data = _get_json(
            f"https://api.cloudflare.com/client/v4/accounts/{account}/ai/models/search",
            {"Authorization": f"Bearer {key}"},
        )
        if data.get("success") is not True or not isinstance(data.get("result"), list):
            raise RuntimeError("Cloudflare model listing was rejected.")
        models = _clean_models(data["result"], provider)
    elif provider == "pollinations":
        # Pollinations uses an API key, even when the model can spend free
        # Quest credits. A read-only account-key endpoint verifies only the key.
        verify_quest_only_key(key)
        snapshot = refresh_public_catalog()
        models = tuple(
            DiscoveredModel(
                offer.model_id, offer.name, offer.image_adapter,
                offer.warning,
            )
            for offer in snapshot.offers
        )
    elif provider == "huggingface":
        data = _get_json("https://huggingface.co/api/whoami-v2",
                         {"Authorization": f"Bearer {key}"})
        if not isinstance(data.get("name"), str):
            raise RuntimeError("Hugging Face token identity could not be checked.")
        models = ()
    else:  # Stability: account identity, not a catalog for v2beta image generation.
        data = _get_json("https://api.stability.ai/v1/user/account",
                         {"Authorization": f"Bearer {key}"})
        if not (isinstance(data.get("email"), str) or isinstance(data.get("id"), str)):
            raise RuntimeError("Stability identity could not be checked.")
        models = ()
    compatible = sum(model.compatible for model in models)
    message = (
        f"Key passed a read-only list/identity request; {len(models)} models listed, "
        f"{compatible} image-model candidates supported by current adapter. "
        "A successful listing does NOT confirm credits, image generation, or transparency."
    )
    if provider == "pollinations":
        message += (
            " Quest eligible models MAY SPEND Pollen credits; not guaranteed free. "
            "Set a zero-paid budget on your key in the provider dashboard."
        )
    return DiscoveryResult(provider, True, models, message)
