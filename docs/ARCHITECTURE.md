# Architecture & safety design

## Pipeline

`Tkinter GUI / CLI -> ImageProvider -> source.png -> print canvas -> metadata -> JSON manifest -> publishing review queue -> CSV/manual marketplace upload`.

- `providers.py`: Cloudflare FLUX.1-schnell REST and optional Hugging Face Inference Client. Fail closed; never silently switch to a paid model/provider. Provider network calls in GUI worker thread.
- `seo.py`: deterministic local SEO, optional opt-in Gemini API metadata; labels it a draft, not evidence of verified keyword traffic.
- `pipeline.py`: image creation, alpha detection, print-canvas export and content hash. Canvas upscaling alone does not improve physical print fidelity.
- `storage.py`: local manifests with atomic replace and explicit per-marketplace review states.
- `app.py`: desktop UI with no user account credentials; external upload pages are explicitly user-operated.
- `cli.py`: automation-ready one-design-at-a-time CLI and CSV export.

## Important missing capabilities

- Real background separation/masking, color management, DPI/print-quality validation and print-area variations per marketplace product.
- Live, correctly sourced trend signals; providers may require authentication and licensing.
- Production-grade platform integrations or authorized uploader automation. Check current terms, limits and UI behavior before implementing. Never bypass CAPTCHA, anti-bot detection, rate limits or access controls.
- Secure OS credential vault, encrypted backups, job cancellation, quotas, model progress and resumable failed requests.
- GPU-model weights and local ComfyUI server are **not bundled** into the EXE.

## Release integrity

Windows CI runs on clean GitHub-hosted Windows runner. PyInstaller produces a one-file .exe; it's an executable packaging tool, not an installer or code-signing certificate. Never distribute an unsigned, unscanned EXE as a verified production binary.

## Release 0.3

See [PUBLISHING_POLICY.md](PUBLISHING_POLICY.md). Optional external rembg and Real-ESRGAN, output provenance, QC failures that prevent approval, human ownership confirmation, approved-only CSV and manual upload confirmation. No marketplace passwords, CAPTCHA bypass or unattended publishing.
