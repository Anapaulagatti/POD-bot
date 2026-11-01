# PODBot ProMax Lite: CPU-first POD workflow

Goal: fast Windows startup and predictable memory use on entry-level machines. The default Python dependencies and Windows EXE **remain unchanged**: Pillow, CustomTkinter and keyring. No PyTorch, CUDA, ONNX, diffusion weights or model downloads are added.

## 1. Create a structured prompt, completely offline

Open **Tạo thiết kế → BỘ DỰNG PROMPT CÓ CẤU TRÚC · OFFLINE**. Enter a descriptive original subject, choose one of four print-oriented styles, one of three layouts, a palette of **1–6 #RRGGBB colors**, chroma magenta/green, flat white or explicitly requested transparent background, and whether to include original lettering. Default is **chroma-magenta** for models without a configured alpha request; OpenAI's image API adapter may request transparency, but a real API test is still required before trusting it. Click **Dựng prompt (0 phí API)**.

This only composes deterministic English instructions. It **does not** call any AI API, use GPU, or generate an image. Review the resulting editable prompt and copyright/trademark constraints before generating. If you edit the prompt manually, the app keeps the freeform text but no longer falsely attributes it to the builder. Background directions live in the builder: the flat-background legacy suffix is automatically disabled when building.

When a design is generated, `manifest.json` stores `prompt_recipe` (including schema version 1), `prompt_recipe_sha256`, the actual original `prompt`, `prompt_sent`, and `prompt_sent_sha256`. Older freeform prompts remain valid. A mismatched recipe or contradictory transparent-versus-white background instruction is rejected before SEO or image generation, preventing wasted API attempts.

The builder is a **prompt organizer**, not a guarantee that the provider will return transparent alpha, printable native resolution or error-free typography. The model selector labels alpha as **requested but unverified** for OpenAI and **unknown** for other models. Transparent prompts trigger a warning. Chroma prompts reject palettes containing colors close to the selected key.

## 2. Background removal without GPU

Keep **Pillow flat-color removal** as the built-in default for suitable almost-uniform backgrounds. Chroma and flat-white recipe designs are **automatically** passed through conservative Pillow cutout after their original PNG has been saved; if cutout fails, the image remains a draft with a visible warning instead of being falsely approved. The original is never overwritten. Green or magenta keys avoid erasing legitimate white art when their color does not overlap the artwork. It is conservative and refuses gradients and ambiguous opaque images; preserve the original and manually inspect edges on dark and light shirts. The existing separately installed rembg/BiRefNet remains optional. It can require large weights, significant RAM and may download model weights on first use. Do **not** silently install it in a standard EXE.

BiRefNet model cards may display MIT, but commercial-rights concerns exist around training data and particular checkpoints. Verify the exact **weight version and license** before commercial distribution. Do not bundle BRIA RMBG-2.0's non-commercial weights.

## 3. Optional VTracer CPU SVG review

For vector-like artwork (flat-color silhouettes and line art), install the **VTracer CLI from its publisher** separately. Select a design in the library and click **Xuất SVG (VTracer)**, then explicitly choose the trusted CLI executable. It runs at most 180 seconds, downsamples source PNG to fit 1600×1600 for low-memory machines, and constrains palette to at most 6 colors. The source is the **current processed print PNG containing actual alpha**, not the original image with its background. The CLI fails if that PNG is opaque, missing or outside the design folder. The SVG is scanned for active or external content and written as a **review-only** file inside the design folder.

The application never replaces the print PNG, invalidates or grants approval, or auto-posts SVGs to a store. Review visual fidelity, text, transparency and rights before using the vector result. VTracer CLI version **1.0 alpha** supports `--max-colors`; older CLIs may reject it. The desktop application does not download VTracer itself.

CLI example:

```powershell
podbot vectorize --id 0123456789abcdef0123456789abcdef --vtracer "C:\Tools\vtracer.exe" --max-colors 4
```

VTracer CLI is MIT licensed, but ensure the **artwork source** is independently licensed. VTracer's separate commercial desktop application and optional generative features may have different terms.

## 4. CPU memory improvements and lettering check

- `fingerprint`, `audit_image`, and `inspect_halo` now scale the source image down **before** converting to RGBA for their 128/512/800-pixel analyses. This avoids allocating another large RGBA analysis buffer for every print preview. Small differences near the hash/alpha threshold are possible; compare old library fingerprints and visually review near-duplicate results after upgrading.
- The image composer still allocates a full-size 5000×5500 print canvas and may briefly exceed a few hundred MB depending on source dimensions and Pillow internals. **No claim of verified peak RAM below 300 MB** is made. Actual RAM benchmarking on the intended weak Windows hardware is required.
- When a structured prompt includes user-original lettering, OCR compares the recognized text with the requested phrase and warns on a mismatch. OCR is advisory and must not auto-correct art; a human must proofread final lettering. Tesseract remains optional and separately installed.

## 5. Heavy tools deliberately excluded

| Candidate | Default EXE | Reason |
| --- | --- | --- |
| LayerDiffuse / ComfyUI | No | GPU, model weights and dedicated service requirements |
| BiRefNet/rembg | No | Optional installation only; weights and memory requirements |
| Spandrel / Real-ESRGAN | No | PyTorch/model weights, external tool already supported |
| RapidOCR | No | Additional runtime/model packaging not yet benchmarked |
| LAION aesthetic predictor / pyiqa | No | CLIP/Torch and unclear commercial-license contexts |
| PromptEnhancer 7B | No | Large memory/GPU footprint and unclear license |
| VTracer CLI | Optional user-selected executable | CPU-friendly, not silently bundled |

## Acceptance

- Run Ruff, all unit tests, pip-audit, Windows PyInstaller onedir and native GUI/EXE smoke from the new PR.
- Re-test prompt provenance with a fake provider before any network calls.
- Test external VTracer CLI against real, properly licensed line-art in a separate Windows session; synthetic tests mock subprocess.
- Do not claim genuine GPU or print quality validation without representative physical/POD artwork.
- When a model generates opaque backgrounds or fails alpha quality checks, do not auto-publish.
