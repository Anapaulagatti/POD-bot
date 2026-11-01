---
name: promax-release-verification
description: Verify reproducible, secure Windows EXE releases with tests, audits, native smoke checks, artifacts and explicit manual gates.
---

# PODBot ProMax: release verification

Adapted as project-specific instructions from obra/superpowers verification-before-completion, Trail of Bits supply-chain-risk-auditor, and mattpocock/skills diagnosing-bugs.

1. Establish one exact commit SHA and Windows CPython 3.12 environment before claiming results. Run `ruff`, `pytest`, `pip check`, `pip-audit`, then PyInstaller.
2. Never regenerate package versions during a tagged release; install the committed Windows SHA256 lock with `--require-hashes`.
3. Treat onedir and onefile as two independent binaries: smoke-test `--smoke-test` for BOTH. Also launch onedir GUI and check it stays alive before archiving it. A tag must not publish without these checks.
4. Preserve least privilege in GitHub Actions (read-only except the release job that needs contents:write). Do not provide secrets to PR builds. Do not auto-run the paid API workflow.
5. A signed executable requires an operator-owned Authenticode certificate and certificate management; code checksum and successful PyInstaller build are not equivalent to signing.
6. Collect concrete CI run URLs, number of tests passed, artifact size and available checks. If a check has not run, report it as pending.
7. Audit dependency updates for origin, maintenance, transitive behavior and licensing, not only number of stars or trending installs. Never execute unknown SKILL.md shell scripts blindly.

## References
- https://github.com/obra/superpowers
- https://github.com/trailofbits/skills
- https://github.com/mattpocock/skills
