---
name: windows-packaging
description: Verify a reproducible Windows CPython 3.12 PyInstaller one-dir/one-file application, including native startup probes.
---

# Windows packaging for PODBot

1. Use the committed `requirements/windows-py312.lock.txt`; never resolve dependencies in a release job.
2. Install `pip install --require-hashes -r requirements/windows-py312.lock.txt`, `pip install --no-deps --no-build-isolation -e .`, then `pip check`.
3. Run tests, Ruff and dependency audit BEFORE PyInstaller.
4. PR/push builds only onedir, smoke-probe `PODBot.exe --smoke-test`, then a short GUI launch and terminate. A tag or explicit manual build may additionally create onefile.
5. Pack customtkinter assets, keyring backends and Hugging Face modules. Check the generated EXE exists and is not unexpectedly tiny.
6. Release with a SHA256SUMS manifest. If Windows GUI smoke fails, inspect PyInstaller warning files and logs; do not publish. A real-user Windows/DPI/antivirus test remains mandatory before declaring stable.
7. Do not bundle proprietary model weights, secrets or third-party executables without license review.
