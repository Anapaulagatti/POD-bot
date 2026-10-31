# Marketplace requirements, sources and release gates (October 31, 2026)

## Redbubble

Official help: https://help.redbubble.com/hc/en-us/articles/202270679-Dimensions-Formats

Redbubble accepts JPEG and PNG. PNG is required where transparent regions should remain transparent. Product requirements differ: apparel 2400 x 3200 px, graphic T-shirt 3873 x 4814 px, stickers up to 2800 x 2800 px, and larger home-goods/wall-art products require independent resolutions/aspect ratios. Redbubble indicates an image over 300 MB or 13500 x 13500 pixels may be rejected. The generated 5000 x 5500 canvas is NOT sufficient to unlock all Redbubble product categories.

## TeePublic

Official design guide: https://teepublic.zendesk.com/hc/en-us/articles/4409831531031-Designing-for-Specific-Product-Dimensions

TeePublic uploader guidance: a high-resolution transparent PNG at 150dpi, minimum artwork of at least 1500 x 1995 px **excluding transparent margins**. To enable all products the guidance states **5000 x 5500 px**. The 5000 x 5500 canvas is therefore the shared default draft output; actual artwork must also be adequately detailed.

Official upload guide: https://teepublic.zendesk.com/hc/en-us/articles/115013698607-How-do-I-upload-a-design

## Honest preflight

- PNG canvas: exact file dimensions, separate from visible artwork bounds.
- Transparency: actual alpha extrema, not just RGBA mode or transparent outer canvas.
- Native source: image generator may output ~1024px; scaling into a 5000px PNG does not restore detail. Automated checker warns whenever upscaled beyond 1.5x.
- Mockup previews are generic locally rendered garment drawings, not official marketplace product mockups.
- The user still needs IP, brand, licensed-character, title/tag, color, product-specific size and print-proof review.
- No claim of availability, ranking, approval or performance is guaranteed; marketplace requirements can change.

## Research source

Google Trends RSS: https://trends.google.com/trending/rss?geo=US

RSS is an indicator of general search interest, not a ready-to-sell POD keyword catalog or evidence of commercial rights. Do not auto-generate merch based solely on a trend. Feed may change or rate-limit access. This app does not hide request identity, use proxies or retry against rate limits.

## Third-party inspiration

Review workflow and license provenance in [REFERENCE_REPOS.md](REFERENCE_REPOS.md). No third-party uploader code was copied, and no unapproved browser publishing is included.
