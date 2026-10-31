"""Best-effort LOCAL limit for paid API attempts, not a USD billing cap.

Reserves requests in SQLite *before* network transmission. A timeout may have
already billed the request, so reservations are not refunded automatically.
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from podbot.settings import data_directory

DEFAULT_DAILY_CAP = 3
MAX_DAILY_CAP = 100


def _validate_limit(value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= MAX_DAILY_CAP:
        raise ValueError("Daily paid API call limit must be an integer between 0 and 100.")
    return value


def get_daily_limit() -> int:
    """Environment override is intentional and takes precedence over UI settings."""
    env = os.getenv("PODBOT_PAID_CALLS_PER_DAY")
    if env is not None:
        try:
            return _validate_limit(int(env))
        except (ValueError, TypeError) as exc:
            raise ValueError("Invalid PODBOT_PAID_CALLS_PER_DAY environment value.") from exc
    file = data_directory() / "api_call_limits.json"
    if not file.is_file():
        return DEFAULT_DAILY_CAP
    try:
        config = json.loads(file.read_text(encoding="utf-8"))
        return _validate_limit(config["daily_paid_calls_per_provider"])
    except (KeyError, ValueError, OSError, TypeError) as exc:
        raise RuntimeError("Invalid local paid-API limit configuration. Fail closed.") from exc


def set_daily_limit(value: int) -> Path:
    _validate_limit(value)
    folder = data_directory()
    folder.mkdir(parents=True, exist_ok=True)
    file = folder / "api_call_limits.json"
    fd, temp = tempfile.mkstemp(prefix=".api-limits-", suffix=".tmp", dir=folder)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as writer:
            json.dump({"daily_paid_calls_per_provider": value}, writer)
        os.replace(temp, file)
    finally:
        if os.path.exists(temp):
            os.remove(temp)
    return file


def reserve_paid_request(provider: str, *, day: str | None = None) -> int:
    """Reserve one potentially billed request with atomic SQLite transaction."""
    if not re.fullmatch(r"[a-z][a-z0-9_-]{1,40}", provider):
        raise ValueError("Invalid provider identifier.")
    limit = get_daily_limit()
    if limit == 0:
        raise PermissionError("Paid API calls are disabled by the local daily limit.")
    today = day or datetime.now(UTC).date().isoformat()
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", today):
        raise ValueError("Invalid reservation date.")
    folder = data_directory()
    folder.mkdir(parents=True, exist_ok=True)
    try:
        with sqlite3.connect(folder / "paid_api_attempts.sqlite3", timeout=10) as db:
            db.execute(
                "CREATE TABLE IF NOT EXISTS api_attempts ("
                "id INTEGER PRIMARY KEY, provider TEXT NOT NULL, day TEXT NOT NULL, "
                "created_at TEXT NOT NULL)"
            )
            db.execute("BEGIN IMMEDIATE")
            current = db.execute(
                "SELECT COUNT(*) FROM api_attempts WHERE provider = ? AND day = ?",
                (provider, today),
            ).fetchone()[0]
            if current >= limit:
                raise PermissionError(
                    f"Local daily attempt cap reached for {provider}: {limit} calls. "
                    "Adjust your cap after reviewing provider billing."
                )
            db.execute(
                "INSERT INTO api_attempts(provider, day, created_at) VALUES(?, ?, ?)",
                (provider, today, datetime.now(UTC).isoformat()),
            )
            return current + 1
    except sqlite3.Error as exc:
        raise RuntimeError("Cannot record paid request usage; blocked to avoid untracked billing.") from exc
