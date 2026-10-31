# PODBot contributor instructions

Project-local instructions inspired by ECC development practices; not a declaration that the full ECC plugin has been installed.

- Use Python >=3.11, Pytest tests, Ruff and Windows PyInstaller CI.
- Implement changes with focused RED/GREEN tests, then review security, portability and resource usage.
- Never store user API keys in source, logs or unencrypted manifests. Never bypass marketplace authentication, CAPTCHA or platform restrictions.
- Avoid third-party code copies without a checked license; cite sources and provenance in docs.
- Treat AI designs as drafts requiring IP checks and print-quality verification; never claim a resized picture gained original detail.
- Redbubble and TeePublic uploading stays human-approved until an authorized workflow has been demonstrated.
- Build gate: `python -m pytest -q`, `python -m ruff check src tests`, then Windows PyInstaller build and binary smoke test.

ECC project skill source and license: [docs/ECC_INTEGRATION.md](docs/ECC_INTEGRATION.md).
