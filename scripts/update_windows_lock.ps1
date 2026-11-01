# Run only on native Windows with Python 3.12, then review and commit the diff.
$ErrorActionPreference = 'Stop'
$PSNativeCommandUseErrorActionPreference = $true

$python = python -c "import sys;print('.'.join(map(str,sys.version_info[:2])))"
if ($python -ne '3.12') { throw "This project pins Windows CPython 3.12 only." }
python -m pip install "pip-tools>=7,<8"
python -m piptools compile --allow-unsafe --generate-hashes --no-emit-index-url --no-emit-trusted-host -o requirements/windows-py312.lock.txt requirements/windows.in
Write-Host "Lock refreshed. Review diff; run tests and pip-audit before committing."
