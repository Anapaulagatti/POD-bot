"""Local settings and filesystem paths; never persist provider credentials."""

from __future__ import annotations

import os
from pathlib import Path


def data_directory() -> Path:
    overridden = os.environ.get("PODBOT_DATA_DIR")
    if overridden:
        return Path(overridden).expanduser().resolve()
    return Path.home() / "Documents" / "PODBot"


def designs_directory() -> Path:
    path = data_directory() / "designs"
    path.mkdir(parents=True, exist_ok=True)
    return path
