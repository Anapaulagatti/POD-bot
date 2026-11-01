# PODBot ProMax, security and release audit

Audit date: 2026-11-01. Target baseline: `main` commit `006e9f3a`; fix branch: `audit/promax-network-release-hardening`. This is a code and CI audit, not a penetration test, paid-provider integration test, Authenticode verification or proof of marketplace licensing.

## Executive summary

- **High, fixed in PR #9:** Authenticated API calls in `provider_catalog._call`, Stability, Cloudflare **and Gemini SEO (`seo.py`)** used redirect-following `urllib.request.urlopen`. A redirect could forward sensitive headers. These routes now share a restricted HTTPS transport that rejects redirects and validates an exact host allowlist before connecting. Gemini SEO was found during follow-up adversarial review; it is explicitly regression-tested.
- **High, fixed in PR #9:** Tagged Release built onedir and onefile without running the same native EXE/GUI smoke checks as pull-request CI. This risks a published non-starting ZIP or EXE even when unit tests pass. The release workflow now checks onedir smoke + GUI, and onefile smoke, before packaging and publication.
- **Medium, already controlled:** Paid image API attempts are reserved atomically in SQLite, after local Gemini argument validation. Remote HTTP 400 and timeout attempts are *not* refunded to avoid silent repeated expenses. `paid-api-manual` is only manually dispatched with a typed consent value. The daily attempt count is not a USD charge limit.
- **Medium, already controlled:** Model discovery is a read-only operation and does not prove billing, image entitlement, available credits or transparent image output. Invalid/unknown model options remain unverified until an explicitly approved live probe.
- **Medium, already controlled:** Image approvals recheck current blocklist and use SHA256-bound cached OCR text; missing OCR engine results in a warning and manual review, not commercial-rights clearance.
- **Manual gate, outstanding:** Tesseract is still an external dependency; optional RapidOCR packaging was not yet verified. An actual suite of licensed POD design fixtures, dark-shirt preview and calibrated flat-background tolerance is still needed.
- **Manual gate, outstanding:** Public Windows release is not Authenticode signed. Checksums alone do not provide software publisher identity.
- **Hardening backlog:** GitHub Actions references use mutable version tags (`actions/checkout@v4`, `setup-python@v5`, `softprops/action-gh-release@v2`). Evaluate and pin audited action commit SHAs in a separate reviewed supply-chain change; do not guess hashes.

## Security regression gates added

1. Reject wrong-scheme, deceptive subdomain, credentials-in-URL, non-standard port and fragment in authenticated API URLs before networking.
2. Refuse to forward an Authorization header through HTTP 3xx; never silently retry a billable generation request.
3. Verify OpenAI/Cloudflare/Stability/**Gemini SEO** route token-bearing requests via the approved transport. An AST-based source gate prevents reintroduction of raw `urllib.request.urlopen` outside reviewed, unauthenticated public Trends RSS.
4. Verify release workflow checks both native binary formats before any public GitHub release action, and paid-provider workflow retains user opt-in.

## Explicit third-party and discovery boundaries

- **Hugging Face inference remains outside this transport:** `HuggingFaceProvider` uses the separately maintained `huggingface_hub.InferenceClient`. Its redirects, endpoints and auth-header behavior have **not** been security-tested in this audit. Avoid claiming it is covered; perform a separate pinned-version audit before treating it as hardened.
- **Model discovery uses its own no-redirect handler:** `model_discovery._get_json` uses a request-only GET opener with `_NoRedirect`, and its model and identity URLs are fixed by the app. It is not yet consolidated into `auth_transport`; any consolidation must account for the separate `huggingface.co` identity URL and must preserve strict redirect refusal.
- **Static scan coverage:** `tests/test_seo_secure_transport.py` inspects Python syntax for direct `urllib.request.urlopen` outside `trends.py`. This catches a known easy-to-miss regression, but is not a general taint-analysis engine. Other HTTP libraries and aliasing require explicit source review.

## Verified skill sources and how we used them

| Skill source | Specific relevant practice | Integration choice |
| --- | --- | --- |
| [obra/superpowers](https://github.com/obra/superpowers) | `systematic-debugging`, `verification-before-completion` | Reproduce a bug, add regression tests, verify evidence before claiming success |
| [trailofbits/skills](https://github.com/trailofbits/skills) | `insecure-defaults`, `sharp-edges`, `supply-chain-risk-auditor` | Trace credentials, network redirects, supply-chain and release risks |
| [mattpocock/skills](https://github.com/mattpocock/skills) | `diagnosing-bugs`, `improve-codebase-architecture`, `tdd` | Prioritize reproducible regressions and clear module boundaries |

Two project-specific, auditable skill instructions live under `.claude/skills/promax-secure-provider-audit` and `.claude/skills/promax-release-verification`. Upstream install statistics are not used as a trust signal, and no arbitrary third-party scripts were executed or embedded in the Windows binary.

## Final verification evidence

- PR: https://github.com/Anapaulagatti/POD-bot/pull/9
- CI: see the latest GitHub Actions run for this PR. Do not call this branch ready to merge until all stages (Ruff, pytest, dependency audit, PyInstaller, EXE/GUI smoke) pass.
- Release-tag workflow with both artifact formats is not exercised by pull-request CI. Its order and smoke requirements are checked by the new regression test. Full tag release still requires a version bump and deliberate release decision.
- No real provider credentials were used during this audit. No paid generation or claims of `background: transparent` entitlement were made.

## Acceptance checklist

- [ ] Windows PR CI green on the exact PR head SHA
- [ ] Peer review of the authenticated transport allowlist, no-redirect policy and coverage
- [ ] Operator runs one consented provider integration test with configured GitHub Secret, then examines actual RGBA output (not mock data)
- [ ] Curated real POD fixture set tested on dark and light fabrics
- [ ] Certificate, signature and publisher chain verified before presenting release as signed/trusted
