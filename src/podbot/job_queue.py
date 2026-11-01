"""SQLite-backed local queue for offline, repeatable POD operations.

Only known offline tasks are serializable. Never persist API keys or callable objects.
Running jobs are recovered after crashes and requeued within their retry budget.
"""

from __future__ import annotations

import json
import re
import sqlite3
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from podbot.settings import data_directory

KINDS = frozenset({"reprocess", "inspect"})
STATES = frozenset({"pending", "running", "succeeded", "failed", "cancelled"})
ID_PATTERN = re.compile(r"[0-9a-f]{32}\Z")


@dataclass(frozen=True)
class Job:
    id: str
    kind: str
    payload: dict
    status: str
    attempts: int
    max_attempts: int
    error: str


class JobQueue:
    """Sequential, atomic queue; create one connection per operation."""

    def __init__(self, path: Path | None = None):
        self.path = Path(path) if path is not None else data_directory() / "jobs.sqlite3"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._db() as db:
            db.execute("""
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY, kind TEXT NOT NULL,
                    payload TEXT NOT NULL, status TEXT NOT NULL,
                    attempts INTEGER NOT NULL DEFAULT 0,
                    max_attempts INTEGER NOT NULL DEFAULT 3,
                    error TEXT NOT NULL DEFAULT '',
                    created REAL NOT NULL, updated REAL NOT NULL
                )
            """)
            db.execute("CREATE INDEX IF NOT EXISTS idx_jobs_ready ON jobs(status,created)")

    @contextmanager
    def _db(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        try:
            db.execute("PRAGMA busy_timeout=10000")
            with db:
                yield db
        finally:
            db.close()

    @staticmethod
    def _validated(kind: str, payload: dict) -> dict:
        if kind not in KINDS or not isinstance(payload, dict):
            raise ValueError("Only approved local offline job types are accepted.")
        design_id = payload.get("design_id")
        if not isinstance(design_id, str) or not ID_PATTERN.fullmatch(design_id):
            raise ValueError("Invalid design ID.")
        if kind == "inspect":
            if set(payload) != {"design_id", "platform"}:
                raise ValueError("Unsupported inspection fields.")
            if payload["platform"] not in ("teepublic", "redbubble"):
                raise ValueError("Invalid platform.")
        else:
            if set(payload) != {"design_id", "flat_background"}:
                raise ValueError("Unsupported processing fields.")
            if not isinstance(payload["flat_background"], bool):
                raise ValueError("flat_background must be boolean.")
        return payload

    @staticmethod
    def _job(row: sqlite3.Row) -> Job:
        return Job(
            row["id"], row["kind"], json.loads(row["payload"]),
            row["status"], row["attempts"], row["max_attempts"], row["error"]
        )

    def enqueue(self, kind: str, payload: dict, max_attempts: int = 3) -> Job:
        data = self._validated(kind, payload)
        if not 1 <= max_attempts <= 5:
            raise ValueError("Retry count must be in 1..5.")
        job_id, now = uuid.uuid4().hex, time.time()
        with self._db() as db:
            db.execute(
                """INSERT INTO jobs
                (id,kind,payload,status,attempts,max_attempts,error,created,updated)
                VALUES (?,?,?,'pending',0,?,'',?,?)""",
                (job_id, kind, json.dumps(data, sort_keys=True), max_attempts, now, now),
            )
            row = db.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
        return self._job(row)

    def list(self, limit: int = 100) -> list[Job]:
        if not 1 <= limit <= 1000:
            raise ValueError("Invalid limit.")
        with self._db() as db:
            rows = db.execute("SELECT * FROM jobs ORDER BY created DESC LIMIT ?", (limit,)).fetchall()
        return [self._job(row) for row in rows]

    def recover(self) -> int:
        """Interrupted tasks are resumed only if they still have attempts left."""
        with self._db() as db:
            db.execute("BEGIN IMMEDIATE")
            rows = db.execute("SELECT id, attempts, max_attempts FROM jobs WHERE status='running'").fetchall()
            for row in rows:
                status = "pending" if row["attempts"] < row["max_attempts"] else "failed"
                db.execute("UPDATE jobs SET status=?, updated=?, error=? WHERE id=?",
                           (status, time.time(), "Interrupted by previous shutdown", row["id"]))
            return len(rows)

    def claim(self) -> Job | None:
        with self._db() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT * FROM jobs WHERE status='pending' AND attempts<max_attempts "
                "ORDER BY created LIMIT 1"
            ).fetchone()
            if row is None:
                return None
            db.execute("UPDATE jobs SET status='running',attempts=attempts+1,updated=? "
                       "WHERE id=?", (time.time(), row["id"]))
            selected = db.execute("SELECT * FROM jobs WHERE id=?", (row["id"],)).fetchone()
            return self._job(selected)

    def finish(self, job_id: str, *, error: str | None = None) -> None:
        with self._db() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
            if row is None or row["status"] != "running":
                raise ValueError("Job is not running.")
            status = "failed" if error is not None else "succeeded"
            # Never persist exceptions, prompts, keys or remote response bodies.
            safe_error = "Task failed; inspect local logs without credentials." if error else ""
            db.execute("UPDATE jobs SET status=?,error=?,updated=? WHERE id=?",
                       (status, safe_error, time.time(), job_id))

    def cancel(self, job_id: str) -> bool:
        """Cancel waiting tasks. Running work requires a separate cooperative stop."""
        with self._db() as db:
            cursor = db.execute(
                "UPDATE jobs SET status='cancelled',updated=? WHERE id=? AND status='pending'",
                (time.time(), job_id)
            )
            return cursor.rowcount == 1

    def retry(self, job_id: str) -> bool:
        with self._db() as db:
            cursor = db.execute(
                "UPDATE jobs SET status='pending',error='',updated=? "
                "WHERE id=? AND status='failed' AND attempts<max_attempts",
                (time.time(), job_id)
            )
            return cursor.rowcount == 1
