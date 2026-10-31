"""Terminal interface for testing and controlled batch preparation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image

from podbot.api_limits import get_daily_limit, set_daily_limit
from podbot.audit import audit_image, make_color_preview
from podbot.importer import import_design
from podbot.mockups import create_shirt_mockup
from podbot.pipeline import create_draft
from podbot.processing import ProcessOptions, process_stored_design
from podbot.provider_catalog import CATALOG, MODELS, get_spec, make_provider
from podbot.publishing import approve_listing, confirm_rights, mark_uploaded
from podbot.rehash import rehash_designs
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
    create.add_argument("--provider", choices=list(MODELS), default="cloudflare")
    create.add_argument("--paid-ok", action="store_true",
                        help="Authorize one potentially billed image generation")
    create.add_argument("--gemini-size", choices=["1K", "2K", "4K"], default="2K")
    create.add_argument("--flat-prompt", action="store_true", help="Append flat white background guidance")
    create.add_argument("--seo", choices=["local", "gemini"], default="local")
    import_cmd = commands.add_parser("import", help="Import a local design without image API")
    import_cmd.add_argument("--file", type=Path, required=True)
    import_cmd.add_argument("--niche", required=True)
    import_cmd.add_argument("--keywords", default="")
    api_cap = commands.add_parser("api-limit", help="View or change daily paid API request cap")
    api_cap.add_argument("--set", type=int)
    commands.add_parser("models", help="List image providers; no credentials exposed")
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
    process.add_argument("--bg", action="store_true", help="Use rembg Python optional extra")
    process.add_argument("--flat-bg", action="store_true", help="Remove a flat background with Pillow")
    process.add_argument("--esrgan", type=Path)
    rehash = commands.add_parser("rehash", help="Migrate legacy fingerprints from source.png")
    rehash.add_argument("--dry-run", action="store_true")
    check = commands.add_parser("audit", help="Run detailed local QC checks")
    check.add_argument("--id", required=True)
    check.add_argument("--platform", choices=["redbubble", "teepublic"], required=True)
    preview = commands.add_parser("colors", help="Export four-color fabric preview")
    preview.add_argument("--id", required=True)
    args = parser.parse_args()
    if args.command == "create":
        spec = get_spec(args.provider)
        if (spec.paid or args.seo == "gemini") and not args.paid_ok:
            parser.error("Potentially billed API call; pass --paid-ok after checking pricing.")
        provider = make_provider(
            args.provider, allow_paid=args.paid_ok,
            gemini_size=args.gemini_size,
        )
        record = create_draft(
            args.prompt, args.niche, args.keywords, provider, seo_mode=args.seo,
            flat_background_prompt=args.flat_prompt,
        )
        print(json.dumps(record, indent=2, ensure_ascii=False))
    elif args.command == "import":
        result = import_design(args.file, args.niche, args.keywords)
        print(json.dumps({"id": result["id"], "path": result["print_file"]}))
    elif args.command == "api-limit":
        if args.set is not None:
            set_daily_limit(args.set)
        print(f"Daily potential-billing calls per provider: {get_daily_limit()}")
    elif args.command == "rehash":
        print(json.dumps(rehash_designs(dry_run=args.dry_run), indent=2))
    elif args.command == "models":
        for spec in CATALOG:
            print(f"{spec.id}: {spec.label} [{spec.env_key}] — {spec.hint}")
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
            remove_background=bool(args.rembg) or args.bg, rembg_binary=args.rembg,
            flat_background=args.flat_bg,
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
