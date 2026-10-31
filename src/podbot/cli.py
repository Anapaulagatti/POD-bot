"""Terminal interface for testing and controlled batch preparation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from podbot.pipeline import create_draft
from podbot.providers import CloudflareFluxProvider, HuggingFaceProvider
from podbot.storage import export_csv, list_designs, update_state


def main() -> None:
    parser = argparse.ArgumentParser(description="PODBot local-first CLI")
    commands = parser.add_subparsers(dest="command", required=True)
    create = commands.add_parser("create", help="Generate one design draft")
    create.add_argument("--prompt", required=True)
    create.add_argument("--niche", required=True)
    create.add_argument("--keywords", default="")
    create.add_argument("--provider", choices=["cloudflare", "huggingface"], default="cloudflare")
    create.add_argument("--seo", choices=["local", "gemini"], default="local")
    commands.add_parser("list", help="Display saved draft status")
    csv = commands.add_parser("export", help="Generate manual-upload CSV")
    csv.add_argument("--platform", required=True, choices=["redbubble", "teepublic"])
    csv.add_argument("--out", required=True, type=Path)
    review = commands.add_parser("review", help="Record a manual review / upload result")
    review.add_argument("--id", required=True)
    review.add_argument("--platform", choices=["redbubble", "teepublic"], required=True)
    review.add_argument("--state", choices=["draft", "approved", "uploaded"], required=True)
    args = parser.parse_args()
    if args.command == "create":
        provider = (
            CloudflareFluxProvider() if args.provider == "cloudflare" else HuggingFaceProvider()
        )
        record = create_draft(
            args.prompt, args.niche, args.keywords, provider, seo_mode=args.seo
        )
        print(json.dumps(record, indent=2, ensure_ascii=False))
    elif args.command == "list":
        for item in list_designs():
            print(f"{item['id']} {item['seo']['title']} {item['platform_status']}")
    elif args.command == "export":
        count = export_csv(args.out, args.platform)
        print(f"Exported {count} records to {args.out}")
    elif args.command == "review":
        updated = update_state(args.id, args.platform, args.state)
        print(updated["platform_status"])


if __name__ == "__main__":
    main()
