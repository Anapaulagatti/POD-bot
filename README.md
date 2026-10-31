# PODBot Studio (MVP 0.1.0)

**Local-first Windows Print-On-Demand studio:** generate original AI design drafts, prepare transparent-canvas PNG files, create SEO metadata, review drafts for Redbubble and TeePublic, then upload manually. Written in Python, designed to become a single `PODBot.exe`.

> Status: **Initial working source-code scaffold, not a completed auto-publisher**. No live platform uploader is implemented. AI calls require a valid account/token and depend on provider limits. No free unlimited image API is promised.

## What works

- Native Tkinter desktop GUI with three tabs: AI Design + SEO, Publishing Queue, API Settings.
- Cloudflare Workers AI FLUX.1-schnell provider and optional Hugging Face provider.
- Deterministic offline SEO or optional Gemini REST SEO (depending on availability/quota).
- Generate one design per click, with a rights-confirmation prompt.
- Save source PNG and a 5000×5500 px PNG on a transparent canvas; retain metadata in a JSON manifest.
- Local review queue with platform-specific draft, approved and manually uploaded states.
- Export editable CSV metadata and open official upload pages in the user's browser.
- GitHub Actions Windows CI to run tests and build a downloadable single-file `.exe` artifact.

**Limits:** AI image generators often produce opaque backgrounds. Putting an opaque source on a transparent canvas **does not remove the source background**. Scaling does not add real print detail, even if the saved PNG is 5000×5500 px. The operator must inspect/edit the design and comply with marketplace size, transparency, intellectual-property, AI-content and upload policies. Draft tags are NOT backed by live trend data. No scraping, login automation, CAPTCHA bypass or unattended mass publishing is included.

## Run from source

Install **Python 3.11+** on Windows (with Tkinter). In PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[hf,dev]"
python -m podbot
```

Set Cloudflare Account ID/API token in the GUI (in-memory only), or use `CLOUDFLARE_ACCOUNT_ID` and `CLOUDFLARE_API_TOKEN` environment variables. For Hugging Face, use `HF_TOKEN`. For Gemini SEO, use `GEMINI_API_KEY` and optionally `GEMINI_MODEL` compatible with your plan. There is also an API-free offline SEO mode. Tokens are not stored by PODBot and should never be committed. Cloudflare may require billing/account setup even within free allocations.

## Command line

```powershell
podbot create --provider cloudflare --seo local --niche "mountains" --keywords "hiking,sunrise" --prompt "Original minimalist mountain silhouette, no text, no logos"
podbot list
podbot export --platform redbubble --out queue-redbubble.csv
podbot review --id YOUR_32_CHARACTER_DESIGN_ID --platform redbubble --state approved
```

## Build Windows EXE

On Windows with Python installed, run:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_windows.ps1
```

Output is `dist/PODBot.exe`. Alternatively, enable GitHub Actions, run **Validate and build Windows executable**, and download artifact **PODBot-windows-exe**. Build artifacts are separate from a released, tested application. Bundling dependencies increases EXE size. `PODBot.exe` itself does not bundle a local diffusion model or GPU drivers, so cloud generation still needs an internet connection.

## Storage and security

`~/Documents/PODBot/designs/<uuid>/` stores `source.png`, `print_5000x5500.png` and `manifest.json`. API keys remain in memory and are not saved; the original prompt and listing metadata are stored locally. Generated designs are not encrypted. No user password/cookie or social-login tokens are collected.

## Development roadmap

1. **MVP 0.1:** Stable local image pipeline, metadata, review queue and Windows build.
2. **MVP 0.2:** Local trend research with attribution, source allowlist, caching, deduplication, cost/quota budgeting and cross-platform SEO presets.
3. **MVP 0.3:** Background-removal tool, actual resolution/quality checks, printable vector/text compositions, mockup templates, local ComfyUI adapter.
4. **MVP 0.4:** Supervised browser workflow only if permitted by Redbubble/TeePublic terms and technical behavior, with per-product review, manual confirmation, bounded retry and explicit consent.
5. **MVP 1.0:** Windows code signing, installer/update strategy, secure encrypted credential store, release QA and backup/restore.

See [Architecture](docs/ARCHITECTURE.md), [Source Review](docs/REFERENCE_REPOS.md), and [Hướng dẫn GitHub / build EXE](docs/GITHUB_SETUP_VI.md).

## New in MVP 0.2 (experimental development branch)

- Project-scoped ECC Python/TDD skills (license and installation caveats in [ECC integration](docs/ECC_INTEGRATION.md)). They enhance the developer workflow, not EXE runtime.
- Google Trends public RSS research by country, with source and approximate volume (not a product-opportunity guarantee). Brands/celebrities shown in RSS are **not** automatically safe to sell.
- TeePublic all-products 5000 × 5500 transparent-canvas preset, per-platform image preflight warnings, and illustrative local T-shirt mockup preview.
- The command line adds `podbot trends --country US`, `podbot preflight --id ID --platform teepublic`, and `podbot mockup --id ID`.
- Desktop GUI adds a Trend Research tab, Preflight and T-shirt mockup buttons. User approval is still required for marketplace publishing.

See [marketplace design requirements](docs/MARKETPLACE_REQUIREMENTS.md). These checks are advisory; the original AI resolution and actual visible artwork dimensions matter, and no resizing creates genuine high-resolution detail.
