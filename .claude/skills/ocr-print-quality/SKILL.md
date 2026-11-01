---
name: ocr-print-quality
description: Correctly read text on transparent POD images, evaluate on contrasting fabrics and enforce local blocklist checks during marketplace approval.
---

# OCR Print Quality and Commercial Text Gate

1. Render the RGBA artwork over **white** before OCR. If transparency exists, also render on dark background to catch white text. Never call plain `convert("RGB")` on transparent art expecting white corners.
2. Keep OCR entirely offline and opt in. The base Windows package currently uses separately installed Tesseract if available, with bounded subprocess execution, explicit language, no shell and no automatic model downloads.
3. Reuse `find_blocked_terms` and local blocklist for recognized OCR text at the actual `validate_listing` gate, not only in an informational preflight. Exact matches must fail approval; OCR unavailable should warn and require manual attention, not imply cleared status.
4. Warn if OCR finds lettering despite the design prompt asking for 'no text'. OCR is probabilistic: human review can still find invisible or misread text. Never assert automatic trademark clearance.
5. Synthetic fixture matrix: transparent black glyph on clear background, white lettering, closed white islands, anti-aliasing, off-white matte, and two-tone motifs. Assert what pixels the OCR engine actually receives.
6. If implementing bundled OCR, evaluate [RapidAI/RapidOCR](https://github.com/RapidAI/RapidOCR) (modern `rapidocr` with `onnxruntime`). The older `rapidocr_onnxruntime` package family is being retired. Benchmark RAM/EXE size, license/model provenance and Windows DLL loading before adding to the default installer; prefer optional extras until verified.
7. Do not silently alter approved artwork. Any reprocessing from an offline queue invalidates marketplace approval only after the GUI clearly confirms the consequences.
