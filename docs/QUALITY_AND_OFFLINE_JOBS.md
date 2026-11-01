# PODBot Windows, image-quality and offline jobs operating guide

## Packaging and release

- Supported build host: Windows latest, CPython 3.12. Build on Windows, not Linux.
- Push and pull request CI: unit tests, compile, Ruff, onedir executable with a bundled offline smoke probe, native GUI start test and portable ZIP artifact.
- Manual workflow_dispatch: the above plus onefile, its offline smoke probe and artifact.
- Version-tag release: onefile + onedir, prerelease, SHA256 list. Never tag a failing commit.
- Windows lock is generated using `piptools compile --generate-hashes` on an actual Windows CPython 3.12 runner and committed as `requirements/windows-py312.lock.txt`. CI and release install from that exact file using hash verification.
- Dependency updates require a fresh Windows lock, test suite, `pip-audit`, inspection of the lock diff and a new release tag. Do not silently regenerate dependency resolution while publishing.
- When `pip-audit` flags an advisory: inspect the package, upstream resolution, whether the vulnerable function is used, and the real advisory. Fix/pin to a patched dependency and regenerate the lock. For an independently confirmed false positive, record advisory ID, evidence and expiry in a reviewed exception. Do not globally disable auditing.
- A ZIP without Authenticode is a developer preview, not signed or notarized. A successful headless smoke probe + a short GUI survival test does not prove the GUI renders correctly on every Windows version, DPI or antivirus.

## Image-quality acceptance checks

- Inspect transparent output on **white, charcoal and navy** fabric. Keep the original source; do not claim a large resized PNG recovers missing fine detail.
- Pillow flat-background removal only handles uniform/near-uniform border colors. It deliberately refuses gradients, already-transparent inputs and unsafe masks.
- Alpha decontamination is performed against an estimated border color. Halo scanning is **advisory**: legitimate white lettering/white strokes can trigger false positives.
- OCR requires a separately installed `tesseract` executable, accessible via PATH or `PODBOT_TESSERACT_PATH`. The program neither silently downloads a model nor bundles OCR trained data. To read Vietnamese, install `vie` language data and select it from the Python API.
- OCR is a transcription aid, **not** a copyright/trademark clearance service. The user must verify every letter and commercial right.
- Real-image fixture matrix to review manually: transparent white lettering on a dark motif, dark-blue antialiased circle on white, opaque pale ivory background, cast shadows, hand-drawn ink outlines, gradient background refusal, and high-resolution 5000 × 5500 export. The tests currently include reproducible synthetic proxies; no private buyer artwork has been supplied or approved for use as an automated fixture.

## Durable task behavior

- The SQLite database `jobs.sqlite3` is kept in the local PODBot data directory.
- Only offline `inspect` and `reprocess` tasks can be serialized. No provider API call, credential or prompt is stored in the queue. Billing requests remain interactive and are never retried without a separate explicit user confirmation.
- The desktop resumes waiting/interrupted offline tasks after restart. A running task may be retried after a crash, so the service is **at least once**, not exactly once; a new image file may be created on recovery.
- Cancel operates only while the task is **pending**. There is no force-cancel for a running image operation (which might corrupt a partially written image or database). Failed tasks may be retried manually while under the configured attempt limit.
- Errors in the queue database are intentionally generic to avoid storing secrets or sensitive image/provider content.

## Paid-provider contract check

Unit tests use mocked HTTP, so a green CI run does not validate credentials, billing eligibility or provider response fields. To perform **one** real billable test, on a machine you control:

```powershell
$env:PODBOT_PAID_CALLS_PER_DAY = "1"
$env:PODBOT_LIVE_TEST_APPROVED = "YES_I_ACCEPT_POTENTIAL_CHARGES"
# Set OPENAI_API_KEY securely in the environment; never commit it.
python scripts/live_paid_probe.py --provider openai-flare --live
```

Without `--live`, the script is dry run and makes no network call. Live probing uses one generation attempt, produces `paid-live-probe.png` locally and will fail if an OpenAI response unexpectedly lacks transparency. Check current provider pricing and documentation before spending credits. A timeout may still have incurred charges. Never paste a secret into public GitHub logs.
