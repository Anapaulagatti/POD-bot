$ErrorActionPreference = 'Stop'
python -m pip install --upgrade pip
python -m pip install -e '.[hf,dev]'
python -m pytest -q
python -m ruff check src tests
python -m PyInstaller --noconfirm --clean --onefile --windowed --name PODBot --paths src --collect-all customtkinter --collect-submodules huggingface_hub src/podbot/app.py
Write-Host "Build ready: dist/PODBot.exe"
