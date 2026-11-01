# PODBot engineering sources and next gates

## Verified repositories (2026-11-01)

| Repo | Why useful | Decision |
| --- | --- | --- |
| [flack0x/trendspyg](https://github.com/flack0x/trendspyg) | RSS, related queries from Explore, cache, agent-facing docs | Study for optional advanced Trends mode. Keep dependency-free RSS for portable EXE. Explore requires Chrome and is susceptible to 429 rate limits. |
| [RapidAI/RapidOCR](https://github.com/RapidAI/RapidOCR) | Offline OCR with ONNX Runtime, cross-platform | Candidate for optional OCR-enabled build after test on clean Windows. Prefer maintained `rapidocr` over retiring `rapidocr_onnxruntime` family. |
| [obra/superpowers](https://github.com/obra/superpowers) | TDD, systematic debugging, review and verification skills | Reference for writing repo-specific skill playbooks. Do not copy unreviewed executable scripts or entire repo into PODBot. |
| [anthropics/skills](https://github.com/anthropics/skills) | Agent Skills format and authoring templates | Reference for SKILL.md structure only. Not every skill here is open source. |
| [GeneralMills/pytrends](https://github.com/GeneralMills/pytrends) | Historical related searches examples | Archived in April 2025; not recommended as a new production dependency. |

## Delivery in PR #8

- OCR now renders transparent art over white; on transparencies, an additional dark preview is scanned. Deduplicated text participates in `review_ocr` checks.
- `validate_listing` and the offline inspect job both apply the same OCR policy; a recognized phrase from local blocklist yields a FAIL. Missing OCR gives a WARN and requires manual inspection. No OCR can promise copyright or trademark clearance.
- Google Trends RSS now supplies attributed topic + news-headline-derived keyword suggestions. The GUI can copy or prefill both, but does not generate merchandise automatically. **Derived keywords are not Google Related Queries** and do not have verified popularity scores.
- Queued reprocessing now confirms earlier Redbubble/TeePublic approved or uploaded statuses will revert to draft.
- Existing paid API probe still requires explicit user opt-in; none of the changes add background billable calls.

## Manual gates

- Run tests, Ruff, dependency audit, Windows onedir/onefile build and startup checks on every changed commit.
- Test OCR with real POD artworks of different colored text and language scripts; default Tesseract may be absent on consumer machines.
- Validate an optional `rapidocr` backend with real packaging measurements, including signed DLLs/model licenses and performance before including it in standard EXE.
- For verified Related Queries, separately test `trendspyg` Explore in a Chrome-enabled environment with strict rate limits, timeouts and timestamped cache. Do not pretend RSS contains those values.
- Never automatically greenlight selling designs containing recognized brand names, celebrities or other protected material.

## Follow-up: SHA-256 OCR caching and dynamic API model discovery

- OCR text now caches inside each design manifest with its print-file SHA-256. Approval, upload confirmation and CSV export reuse the transcript until image bytes change. Reprocessing clears the cache. Blocklist changes are still checked on every approval. Failed OCR attempts are never negative-cached.
- Trends keyword suggestions reject phrases with function words at either end. Trends with blocklist matches are visibly warned and their auto-prefill is disabled.
- Settings offers a read-only key check and model listing per selected provider. No generation call, billing, image prompts or automatic retry happens during a key check.
- OpenAI: GET /v1/models. Gemini: GET /v1beta/models, up to three pages. Replicate: first page of the public model catalog. Cloudflare: Workers AI model listing. Hugging Face and Stability: identity check only. fal: credential-specific nonbillable discovery not configured, clearly marked unverified.
- Only detected image models with an adapter-compatible request contract are offered to the generator. Others remain listed-only. Users can opt into a manual preset list with a warning.
- A successful key listing does not establish credits, quota, image-generation entitlement, transparency or supported parameters. A billable live probe still requires separate explicit consent.
- API keys are sent in headers over HTTPS, never in URLs, logs, manifests or saved discovered-model records. Session-only matching invalidates a model choice when its key is changed.