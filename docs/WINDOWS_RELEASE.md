# Windows Release & integrity checklist

## Tag-based GitHub release

The **Release Windows Preview** workflow triggers only on tags matching `v*`. It checks the tag matches the PEP 440 package version and is reachable from `main`, then resolves dependencies on a clean Windows Python 3.12 runner, runs `pip-audit`, tests and Ruff before packaging.

The workflow produces:
- `PODBot-vX-windows-onedir.zip`: portable folder build, preferred if antivirus dislikes onefile extraction
- `PODBot-vX-windows-onefile.exe`: existing portable single-file format
- `requirements-windows-py312.lock.txt`: **resolved version snapshot** for this release (includes transitive packages, generated on the runner, NOT a committed hash-pinned lockfile)
- `SHA256SUMS.txt`: SHA256 for those artifacts

Publishing uses `softprops/action-gh-release@v2` with `contents: write` and marks the release a prerelease. Failures in dependency audit, tests, lint or build prevent publishing. See [GitHub action documentation](https://github.com/softprops/action-gh-release) and [pip-audit](https://github.com/pypa/pip-audit).

A workflow existing on main is not proof that a release exists. A release is published **only when an eligible tag is pushed and its workflow completes**. Tags must not be created just to bypass review.

### Verify SHA256 on Windows

```powershell
Get-FileHash .\PODBot-v1.0.0rc3-windows-onefile.exe -Algorithm SHA256
```

Compare with the matching line in `SHA256SUMS.txt` on the GitHub Release page. A checksum detects accidental changes, **not a guarantee of trustworthy authorship**: signing and installer verification remain separate work.

### Security scope

This is a developer preview. Build dependency snapshot is resolved anew at tag time, meaning an older release cannot automatically be reproduced later without reinstalling that snapshot. The current main branch CI still builds onefile artifacts. Authenticode code signing, installer, genuine Windows startup visual tests, commercial-art OCR, and third-party GPU model packaging remain open milestones.

### Proposed first release

`v1.0.0rc3` only after the GitHub Windows PR checks have passed and the code changes are merged into main. Do not present a tag or binary as published until GitHub confirms the release run succeeded.
