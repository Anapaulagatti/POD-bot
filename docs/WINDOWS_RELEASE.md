# Windows Release & integrity checklist

## Tag-based GitHub release

The **Release Windows Preview** workflow triggers only on tags matching `v*`. It checks the tag matches the PEP 440 package version and is reachable from `main`, then installs the committed hash-locked dependencies on a clean Windows Python 3.12 runner, runs `pip-audit`, tests and Ruff before packaging.

The workflow produces:
- `PODBot-vX-windows-onedir.zip`: portable folder build, preferred if antivirus dislikes onefile extraction
- `PODBot-vX-windows-onefile.exe`: existing portable single-file format
- `requirements-windows-py312.lock.txt`: **byte-for-byte copy of the committed hash-checked lock** in `requirements/windows-py312.lock.txt`
- `SHA256SUMS.txt`: SHA256 for those artifacts

Publishing uses `softprops/action-gh-release@v2` with `contents: write` and marks the release a prerelease. Failures in dependency audit, tests, lint or build prevent publishing. See [GitHub action documentation](https://github.com/softprops/action-gh-release) and [pip-audit](https://github.com/pypa/pip-audit).

A workflow existing on main is not proof that a release exists. A release is published **only when an eligible tag is pushed and its workflow completes**. Tags must not be created just to bypass review.

### Verify SHA256 on Windows

```powershell
Get-FileHash .\PODBot-v1.0.0rc3-windows-onefile.exe -Algorithm SHA256
```

Compare with the matching line in `SHA256SUMS.txt` on the GitHub Release page. A checksum detects accidental changes, **not a guarantee of trustworthy authorship**: signing and installer verification remain separate work.

### Security scope

This is a developer preview. The same Windows-CPython-3.12 lockfile is installed in CI and tagged releases. PR/push builds produce onedir; the onefile build is reserved for manual workflow runs or tags. CI performs a bundled offline smoke probe and a brief Windows GUI startup check, not a full GUI visual automation. Authenticode signing, installer, real-world image fixtures and optional external OCR/GPU binaries remain open verification steps. See [quality & offline job guide](QUALITY_AND_OFFLINE_JOBS.md).

### Proposed first release

`v1.0.0rc3` only after the GitHub Windows PR checks have passed and the code changes are merged into main. Do not present a tag or binary as published until GitHub confirms the release run succeeded.
