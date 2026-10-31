# PODBot Studio 4.x: ranked delivery roadmap

## Shipped in 4.0.0 (code, Windows CI pending confirmation)
- 14 image model choices across 7 service ecosystems: Cloudflare, Hugging Face, Google Gemini, OpenAI, Replicate, fal.ai, Stability AI.
- Paid-model opt-in confirmation on desktop and explicit CLI --paid-ok, one generation per user action and NO hidden provider fallback.
- In-memory keys / environment variables, provider allowlists and bounded CDN downloads; no API keys in manifests.
- Local PNG/JPEG/WebP import that requires zero image API credits; preserve original image, draft SEO and human publishing approval workflow.
- Pure mock-based paid HTTP integration tests, not paid end-to-end credentials or a signed desktop app.

## Priority 4.1: Security, costs and reliability
- Per-provider spending ceiling, daily request limit, transaction/usage receipts, no silent paid retry.
- Optional Windows Credential Manager (Python keyring) for consent-based secret remembrance. Default does not remember keys.
- SQLite job queue with restart-safety and cancellation; terminal-state checks for Replicate and fal queues.
- Show current provider cost-policy URLs and clearly estimate image dimensions before calling the API.

## Priority 4.2: Print studio excellence
- VTracer vectorization for flat-color designs; OCR via RapidOCR for invented lettering and brand names.
- Calibrated alpha halo cleanup, connected-component speck detection and posterization for clean screen printing.
- Product-specific printable area, stroke width, bleed, color contrast, and real print sample testing.
- Side-by-side original/enhanced comparison, 4-color apparel preview and provenance record.

## Priority 4.3: Optional local GPUs
- ComfyUI localhost API, queue and workflow templates; separate ComfyUI/model downloads.
- GPU/VRAM checks, hash pinning and verification of each model's commercial license.
- No GPL source bundling and no Python/PyTorch training runtime inside the single-file PODBot.exe.

## Priority 4.4: Multi-store operations
- Gallery sorting, duplicate grouping, sales CSV reporting, country-specific seasonality and sourced trends.
- Official draft API integrations ONLY for platforms that support authorized integration.
- Redbubble and TeePublic remain manual review/upload workflows unless policy clearly permits official integrations.

## Release gates
- Pytest and Ruff on Windows, clean PyInstaller build, output artifact and security fixtures.
- Manual end-to-end tests with user's own API credentials (billable) and 4 representative image types.
- Test on supported Windows machines and independent malware scanning before any binary is advertised as production-safe.
