---
name: release-security
description: Lock Python dependencies with hashes, audit Windows releases, protect secrets and produce verifiable signed-release readiness evidence.
---

# Secure PODBot release gate

1. Generate Windows Python 3.12 dependency lock with `pip-compile --allow-unsafe --generate-hashes` on a Windows runner; include wheel and setuptools.
2. Commit the resulting `requirements/windows-py312.lock.txt` after reviewing diff, and use `pip install --require-hashes`. Do not silently resolve a new lock inside tag release.
3. Fail on unit-test, Ruff, `pip check`, `pip-audit`, packaging or EXE smoke failures.
4. Investigate audit advisories against official sources, update vulnerable pins and hashes. Any false-positive exception requires a tracked explanation and expiry, never a blanket disable.
5. Build both onedir and onefile for tags, ship SHA256SUMS. Authenticode code signing and organization reputation checks are separate prerequisites for trusted public distribution.
6. Never log, commit, bundle or retry API keys, user prompts, tokens or provider error bodies. Live paid provider verification requires one explicit consent, one request, a 1/day attempt cap and manually configured credentials.
7. Preserve human review before POD marketplace posting.
