# PODBot development roadmap (user-supplied specification)

Historical roadmap from v0.3. For the currently active v4.x roadmap, see [ROADMAP_V4.md](ROADMAP_V4.md). Implemented means code/tests exist, not proven marketplace success.

| Milestone | Status | Details |
|---|---|---|
| A. Image processing and QC | **Partial** | Cropping, safe margins, 300 DPI metadata, external opt-in rembg, external Real-ESRGAN, 4-color preview, alpha/dimensions/edge checks. TODO: automatic model installer/progress, halo cleanup, calibrated sharpness and speck tests. |
| B. IP safety and marketplace rules | **Partial** | User-editable normalized blocklist, dHash fingerprint, rights confirmation, per-platform QC gate. TODO: OCR, duplicate gallery warning, official per-product policies and false-positive tuning. |
| C. Background jobs/gallery | **Not built** | Persistent queue, cancellation, retry with backoff, quotas, thumbnail paging. |
| D. Storage/security/installer | **Not built** | SQLite migration, Windows Credential Manager, signed installer, release process. API keys currently in memory. |
| E. Trends/seasonality/sales | **Partial** | Public Google Trends RSS with attribution; TODO: history cache and sales CSV insights. |
| F. Local ComfyUI and approved provider APIs | **Not built** | ComfyUI support or provider draft uploads ONLY where official API + account authorization permit. Redbubble/TeePublic remain manual. |

## Recommended release criteria

1. Windows Pytest and Ruff must pass. No secret values committed.
2. GitHub-hosted Windows PyInstaller builds an unsigned standalone application; successful build alone is insufficient for production QA.
3. Manually test 4 sample image types: watercolor/opaque AI generation, transparent clip-art, text line-art, textured illustration. Examine cutout edges on light/dark fabric.
4. Validate user rights and platform-specific placement in an actual seller account without bulk automation.
5. Review licensing of every externally installed tool AND selected model weights before commercial distribution.

ECC Python/TDD rules are available under .claude/ but do not ship inside the Windows runtime.
