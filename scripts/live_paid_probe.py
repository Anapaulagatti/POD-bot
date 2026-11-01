"""One-shot billed provider verification; never run by normal CI.

Usage: python scripts/live_paid_probe.py --provider openai-flare
Dry-run is default. Live requires an explicit opt-in and configured secret.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider", default="openai-flare")
    parser.add_argument("--live", action="store_true")
    args = parser.parse_args()

    from podbot.provider_catalog import get_spec, make_provider

    spec = get_spec(args.provider)
    if not spec.paid:
        raise ValueError("Live probe is restricted to explicitly billable providers.")
    print(f"Provider contract: {spec.id}, key variable: {spec.env_key}")
    if not args.live:
        print("Dry-run only: no provider invocation, network call or billing.")
        return 0
    if os.environ.get("PODBOT_LIVE_TEST_APPROVED") != "YES_I_ACCEPT_POTENTIAL_CHARGES":
        raise PermissionError("Paid live API probe was not explicitly approved.")
    if os.environ.get("PODBOT_PAID_CALLS_PER_DAY") != "1":
        raise PermissionError("Set PODBOT_PAID_CALLS_PER_DAY=1 for one-shot verification.")
    key = os.environ.get(spec.env_key)
    if not key:
        raise ValueError(f"Required {spec.env_key} is missing.")
    # Do not log provider objects, request headers, keys, prompts or response body.
    provider = make_provider(spec.id, {spec.env_key: key}, allow_paid=True)
    art = provider.generate("Simple original dark blue leaf silhouette, no lettering")
    rgba = art.convert("RGBA")
    has_transparency = rgba.getchannel("A").getextrema()[0] < 255
    print(f"Valid image received: {rgba.width}x{rgba.height}, alpha={has_transparency}")
    if spec.vendor == "openai" and not has_transparency:
        raise RuntimeError("OpenAI response lacked transparent output; inspect API contract.")
    output = Path("paid-live-probe.png")
    rgba.save(output, format="PNG")
    print(f"Review generated artifact locally: {output} (do not auto-publish)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
