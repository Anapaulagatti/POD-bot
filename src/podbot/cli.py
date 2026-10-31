"""Terminal interface for testing and controlled batch preparation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image

from podbot.mockups import create_shirt_mockup
from podbot.pipeline import create_draft
from podbot.quality import assess_design
from podbot.trends import read_trends
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
    trends = commands.add_parser("trends", help="Public, attributed Google Trends RSS")
    trends.add_argument("--country", default="US")
    trends.add_argument("--limit", type=int, default=10)
    preflight = commands.add_parser("preflight", help="Inspect print quality warnings")
    preflight.add_argument("--id", required=True)
    preflight.add_argument("--platform", choices=["redbubble", "teepublic"], required=True)
    mockup = commands.add_parser("mockup", help="Create local T-shirt preview")
    mockup.add_argument("--id", required=True)
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
    elif args.command == "trends":
        for trend in read_trends(args.country, args.limit):
            print(json.dumps(trend.__dict__, ensure_ascii=False))
    elif args.command in {"preflight", "mockup"}:
        item = next((record for record in list_designs() if record["id"] == args.id), None)
        if not item:
            parser.error("Design ID not found.")
        if args.command == "preflight":
            print(json.dumps(assess_design(item, args.platform).to_dict(), indent=2))
        else:
            source = Path(item["print_file"])
            target = source.parent / "mockup-shirt.png"
            with Image.open(source) as image:
                create_shirt_mockup(image, target)
            print(f"Preview created: {target}")
    elif args.command == "review":
        updated = update_state(args.id, args.platform, args.state)
        print(updated["platform_status"])


if __name__ == "__main__":
    main()
