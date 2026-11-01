---
name: image-quality-assurance
description: Test alpha compositing, flat-background removal, OCR, halos and print-ready POD exports with reproducible images and manual visual review.
---

# POD image quality gates

1. Write a failing fixture test before each edge-processing change.
2. Protect originals. Flat-background removal is conservative, failing explicitly on gradient, nonuniform border, existing alpha and ambiguous coverage.
3. Test dark anti-aliased motif on white/ivory, white lettering on dark motif, white enclosed islands and cast shadows. Use both hard-edged and naturally anti-aliased art.
4. Inspect edge-halo shares on partial alpha, and composite the same final PNG over white, charcoal and navy. A low halo ratio is advisory, not an absolute guarantee.
5. Verify 5000x5500 PNG export, 300DPI metadata, crop margins and actual native resolution. Lanczos does not invent print detail.
6. Optional OCR must use explicitly available local Tesseract with a timeout, no shell, no automatic downloads. Transcriptions are advisory; inspect words manually.
7. Never auto-approve copyright, trademark or marketplace compliance solely because OCR/pixel checks pass.
