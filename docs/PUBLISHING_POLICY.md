# POD publishing safeguards and platform references

Verified October 31, 2026. All URLs are primary publisher documentation. Policies may change; verify again before listing.

## TeePublic

- [Designing for Specific Product Dimensions](https://teepublic.zendesk.com/hc/en-us/articles/4409831531031-Designing-for-Specific-Product-Dimensions): transparent PNG; minimum design **1500 × 1995 actual pixels**, excluding transparent border. The recommendation for enabling all products is **5000 × 5500** canvas. Guidance states **150 DPI** at print scale; 300 DPI PNG metadata alone does not create pixel detail.
- [Daily upload limits](https://teepublic.zendesk.com/hc/en-us/articles/115013698727-Is-there-a-limit-to-how-many-designs-I-can-upload): Pending and Apprentice accounts 25 uploads per rolling 24 h; Artisan 50. This application does NOT automate upload or assume user category.
- [Account categories](https://teepublic.zendesk.com/hc/en-us/articles/14297563940375-What-are-Account-Categories): mass-produced and automation-heavy work can affect discoverability; design quality matters.
- [Terms](https://www.teepublic.com/terms): artists warrant rights to use/reproduce/sell art. The local blocklist is only a preventive hint and does not verify legal ownership.

## Redbubble

- [User Agreement](https://www.redbubble.com/agreement): seller responsible for IP rights and compliance. The platform can remove or suspend work. Image rules differ by product, so a 5000 × 5500 canvas is not sufficient for ALL Redbubble products.
- [Image dimensions guide](https://help.redbubble.com/hc/en-us/articles/202270679-Dimensions-Formats) (link may redirect or temporarily fail): review current product-specific requirements in the uploader.

## Protected local workflow

1. Generate one original art draft using chosen provider or import file manually in a future release.
2. Process from ORIGINAL source (preserved) into separate PNG, use optional locally installed background removal/upscaler if desired. Check model weight license before using commercially.
3. Run automatic audit: canvas size, transparent bounds, edge proximity, visible art dimensions, coverage, color and contrast. A `fail` blocks approval. This is heuristic, not a guarantee; rectangular opaque art is conservatively flagged as requiring cutout.
4. Review prompt/title/tags/description against a user-maintained blocklist and confirm commercial rights explicitly. Any mutation of SEO or source processing returns approved states to draft.
5. Approve per platform. Export only **approved** items. Open official marketplace webpage manually and review exact placement, colors, original detail, legal metadata and disclosures.
6. After personally uploading and checking seller dashboard, explicitly mark uploaded locally. No login credentials or cookies stored, no CAPTCHA or anti-bot circumvention.

## AI processing caveats

- [rembg](https://github.com/danielgatis/rembg) program MIT, but individual model weight licensing may differ. Do not use weights without verified commercial-use rights. New isnet/birefnet models normally use color decontamination instead of aggressive alpha matting by default. The first local run may download weights and take CPU/GPU memory.
- [Real-ESRGAN-ncnn-vulkan](https://github.com/xinntao/Real-ESRGAN-ncnn-vulkan): downloadable official executable, Vulkan-capable graphics needed. The tool is not bundled. Upscaling may improve perceived texture but cannot guarantee native detail, exact color or print durability.
- 300-DPI file metadata, Alpha/edge inspection and generic mockup previews do not constitute a commercial print test.

## Pending items

OCR scanning, connected-component speck removal, actual halo estimation, true photoreal shirt mockups, image-based automated background removal without separate install, SQLite jobs, and authorized publisher API adapters are NOT implemented in 0.3.
