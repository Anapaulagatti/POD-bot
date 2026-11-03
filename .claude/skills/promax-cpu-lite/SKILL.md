---
name: promax-cpu-lite
description: Maintain the low-memory, low-dependency Windows PODBot workflow, deterministic structured prompts and optional CPU vectorization.
---

# ProMax Lite skills for PODBot

1. **Performance budget first.** Never add Torch, CUDA, onnxruntime, large ML wheels or checkpoint weights to `requirements/windows.in` or the standard EXE without explicit approval and clean-Windows measurement. Keep costly providers and nonlocal tools strictly opt-in.
2. **Prompt determinism.** Validate versioned recipe schema, enforce at most six HEX colors, preserve original user content, and hash the recipe and actual sent prompt in the manifest. Editing the prompt must not falsely retain structured provenance.
3. **Paywall boundary.** Check incompatible background instructions and malformed palettes before `gemini_seo` or `provider.generate`. Never silently fall back to paid AI or repeatedly retry failed inference.
4. **Memory-aware image tooling.** Default to conservative Pillow cutouts and four-color fabric previews. Optional VTracer takes an explicit trusted path, caps pixel dimensions and process timeout, uses `shell=False` and validates SVG for active/external content.
5. **Originals and approvals.** Exported SVGs are review-only. Do not replace the source/print PNG or approvals without explicit confirmation. OCR and commercial-rights review remain separate.
6. **Security and supply chain.** Check binary and model provenance and exact checkpoint license, including training-data concerns. No silent download, executable installation or new dependency at app startup.
7. **Verification.** Add fast mocked tests for valid/invalid recipes, review-state preservation, SVG injection rejection and XML size bounds. Release only with green native Windows CI.
