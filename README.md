# PODBot Studio 4.1.0 (Giao diện tiếng Việt)

**Local-first Windows Print-On-Demand studio:** generate original AI design drafts, prepare transparent-canvas PNG files, create SEO metadata, review drafts for Redbubble and TeePublic, then upload manually. Written in Python, designed to become a single `PODBot.exe`.

> Status: **Initial working source-code scaffold, not a completed auto-publisher**. No live platform uploader is implemented. AI calls require a valid account/token and depend on provider limits. No free unlimited image API is promised.

## What works

- CustomTkinter desktop GUI mặc định bằng tiếng Việt, có thanh điều hướng, trang tổng quan, Studio tạo ảnh, thư viện và trang xu hướng.
- 14 user-selectable image models across Cloudflare, Hugging Face, Google Gemini, OpenAI, Replicate, fal.ai and Stability AI; see [Model marketplace](docs/PROVIDER_MARKETPLACE_V4.md).
- Deterministic offline SEO or optional Gemini REST SEO (depending on availability/quota).
- Generate one design per click with explicit rights and paid-API confirmation; import your own PNG/JPEG/WebP without AI fees.
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

## Added in MVP 0.2

- Project-scoped ECC Python/TDD skills (license and installation caveats in [ECC integration](docs/ECC_INTEGRATION.md)). They enhance the developer workflow, not EXE runtime.
- Google Trends public RSS research by country, with source and approximate volume (not a product-opportunity guarantee). Brands/celebrities shown in RSS are **not** automatically safe to sell.
- TeePublic all-products 5000 × 5500 transparent-canvas preset, per-platform image preflight warnings, and illustrative local T-shirt mockup preview.
- The command line adds `podbot trends --country US`, `podbot preflight --id ID --platform teepublic`, and `podbot mockup --id ID`.
- Desktop GUI adds a Trend Research tab, Preflight and T-shirt mockup buttons. User approval is still required for marketplace publishing.

See [marketplace design requirements](docs/MARKETPLACE_REQUIREMENTS.md). These checks are advisory; the original AI resolution and actual visible artwork dimensions matter, and no resizing creates genuine high-resolution detail.

## Professional print prep / supervised publishing (0.3)

- **Process PNG**: preserve the original, crop to alpha bounds, 7% safe margin, 5000×5500 canvas and 300-DPI file metadata. Optional **external** `rembg` with `isnet-general-use` and `Real-ESRGAN-ncnn-vulkan` x4. Neither tool nor its model weights are bundled in `PODBot.exe`. Tool selection can execute a third-party program and, for rembg, download model weights after user confirmation. Check commercial weight licensing, installer integrity and GPU compatibility.
- **QC**: hard fails for opaque rectangular artwork, edge-touching pixels, missing/inadequate canvas or TeePublic artwork footprint; warnings for coverage, palette and shirt contrast. Heuristics can reject genuine rectangular art and cannot guarantee print quality. Background remover is **optional**, not automatically available on a clean EXE install.
- **Preview 4 colors**: white, dark, navy, gray. DHash fingerprint stored as duplicate-analysis groundwork. Editable local blocklist at `~/Documents/PODBot/blocklist.txt`. Empty by default and not an authoritative trademark index.
- **Human publishing gate**: explicit commercial rights confirmation → QC pass → `approved` → approved-only CSV/manual upload → explicit `uploaded` confirmation. No unsupervised logins, browser injections, CAPTCHA automation, or official marketplace write API implementation.
- Editing metadata/reprocessing resets prior approvals, and output is retained locally. Full audit and docs: [PUBLISHING_POLICY](docs/PUBLISHING_POLICY.md) and [PROJECT_ROADMAP](docs/PROJECT_ROADMAP.md).

### Local tools

The base EXE provides transparent crop/canvas, preflight and preview. For additional AI processing, separately install a **verified official** rembg CLI or Real-ESRGAN-ncnn-vulkan binary and explicitly choose its executable in **Publishing Queue → Process PNG**. Tool execution can consume RAM/VRAM and disk space. No cloud AI background removal is silently used. On Windows, the separate rembg tool might be the `rembg.exe` entrypoint produced by `pip install "rembg[cpu,cli]"` on a supported Python version. First use may download model weights. Verify the chosen model license before commercial production.

### Controlled CLI

```powershell
podbot rights --id DESIGN_ID --confirm
podbot process --id DESIGN_ID --rembg C:\\tools\\rembg.exe --esrgan C:\\tools\\realesrgan-ncnn-vulkan.exe
podbot audit --id DESIGN_ID --platform teepublic
podbot colors --id DESIGN_ID
podbot approve --id DESIGN_ID --platform redbubble
podbot export --platform redbubble --out approved.csv
podbot uploaded --id DESIGN_ID --platform redbubble --confirm
```

**A successful Windows build is not a print proof or a signed/fully smoke-tested desktop release.**

## New in version 4.0.0: Model Marketplace and local import

Choose from 14 image models in the AI Design + SEO tab. Enter only the key for your chosen provider in API Settings, and review the explicit potentially billable API confirmation. No silent paid fallback or retries. On the CLI, use --paid-ok per image request, or run "podbot models" to see available models and required environment variable names.

Bring your own designs from local PNG/JPEG/WebP with the new Import button, or use "podbot import --file PATH --niche NATURE" from terminal. Local file importing skips the paid image-generation API. It still runs existing SEO, PNG preparation, copyright confirmation and marketplace QC. Each asset remains a draft until reviewed.

The current code has mocked vendor API tests and a GitHub-hosted Windows build. It has **not** been tested with your paid Gemini/OpenAI/Replicate/fal/Stability credentials and is not a signed installer. The provider model/API contract and credit balance must be validated through your own provider dashboard.

**Research and strategy:** [15 inspected repositories with licenses and priorities](docs/REPOSITORY_RESEARCH_V4.md), [4.x roadmap](docs/ROADMAP_V4.md). The old release roadmap remains archived for context.

The Redbubble/TeePublic workflow still requires human review and upload. No login automation, CAPTCHA handling or unattended bulk posting is included.
