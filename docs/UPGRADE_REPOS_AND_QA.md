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
