"""Terminal interface for testing and controlled batch preparation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image

from podbot.audit import audit_image, find_blocked_terms, get_blocklist, make_color_preview
from podbot.mockups import create_shirt_mockup
from podbot.pipeline import create_draft
from podbot.processing import ProcessOptions, process_stored_design
from podbot.publishing import approve_listing, confirm_rights, mark_uploaded
from podbot.providers import CloudflareFluxProvider, HuggingFaceProvider
from podbot.quality import assess_design
from podbot.storage import export_csv, list_designs, update_state
from podbot.trends import read_trends


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
    rights = commands.add_parser("rights", help="Record explicit commercial rights review")
    rights.add_argument("--id", required=True)
    rights.add_argument("--confirm", action="store_true")
    approve = commands.add_parser("approve", help="Approve only when QC and rights pass")
    approve.add_argument("--id", required=True)
    approve.add_argument("--platform", choices=["redbubble", "teepublic"], required=True)
    uploaded = commands.add_parser("uploaded", help="Record manual marketplace upload")
    uploaded.add_argument("--id", required=True)
    uploaded.add_argument("--platform", choices=["redbubble", "teepublic"], required=True)
    uploaded.add_argument("--confirm", action="store_true")
    process = commands.add_parser("process", help="Rebuild cropped transparent canvas")
    process.add_argument("--id", required=True)
    process.add_argument("--rembg", type=Path)
    process.add_argument("--esrgan", type=Path)
    check = commands.add_parser("audit", help="Run detailed local QC checks")
    check.add_argument("--id", required=True)
    check.add_argument("--platform", choices=["redbubble", "teepublic"], required=True)
    preview = commands.add_parser("colors", help="Export four-color fabric preview")
    preview.add_argument("--id", required=True)
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
    elif args.command == "rights":
        if not args.confirm:
            parser.error("Use --confirm only after personally checking commercial rights.")
        print(confirm_rights(args.id)["rights_confirmed_at"])
    elif args.command == "approve":
        print(json.dumps(approve_listing(args.id, args.platform)["approval_evidence"][args.platform]))
    elif args.command == "uploaded":
        if not args.confirm:
            parser.error("--confirm requires you to have actually uploaded this design.")
        print(mark_uploaded(args.id, args.platform, confirmed=True)["platform_status"])
    elif args.command == "process":
        options = ProcessOptions(
            remove_background=bool(args.rembg), rembg_binary=args.rembg,
            upscale=bool(args.esrgan), esrgan_binary=args.esrgan,
        )
        print(json.dumps(process_stored_design(args.id, options)["processing"], indent=2))
    elif args.command in {"audit", "colors"}:
        entry = next((r for r in list_designs() if r["id"] == args.id), None)
        if entry is None:
            parser.error("Design ID not found.")
        with Image.open(entry["print_file"]) as image:
            if args.command == "audit":
                print(json.dumps([c.to_dict() for c in audit_image(image, args.platform)],
                                 indent=2))
            else:
                path = Path(entry["print_file"]).parent / "preview-4-colors.png"
                make_color_preview(image, path)
                print(path)
    elif args.command == "review":
        updated = update_state(args.id, args.platform, args.state)
        print(updated["platform_status"])


if __name__ == "__main__":
    main()
