$ErrorActionPreference = 'Stop'
python -m pip install --require-hashes -r requirements/windows-py312.lock.txt
python -m pip install --no-deps -e .
python -m pip check
python -m pytest -q
python -m ruff check src tests
python -m PyInstaller --noconfirm --clean --onefile --windowed --name PODBot --paths src --collect-all customtkinter --collect-submodules keyring.backends --collect-submodules huggingface_hub src/podbot/app.py
Write-Host "Build ready: dist/PODBot.exe"
