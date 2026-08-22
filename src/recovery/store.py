"""Durable state for the recovery system — SQLite, stdlib only.

Turns the engine from an in-memory demo into a system that *remembers*: cases,
the bandit's learned posteriors, and scheduled retry/nudge jobs all survive a
restart. The learning loop ("Measure feeds back ↺") is only real if the learning
is persisted — that's what this does.
"""

from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime
from pathlib import Path

_SCHEMA = """
CREATE TABLE IF NOT EXISTS cases (
    id           TEXT PRIMARY KEY,
    status       TEXT,
    recovered    INTEGER,
    reason       TEXT,
    klass        TEXT,
    amount_paise INTEGER,
    created_at   TEXT,
    payload      TEXT
);
CREATE TABLE IF NOT EXISTS bandit (
    context TEXT,
    arm     TEXT,
    alpha   REAL,
    beta    REAL,
    PRIMARY KEY (context, arm)
);
CREATE TABLE IF NOT EXISTS jobs (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id    TEXT,
    action     TEXT,
    channel    TEXT,
    run_at     TEXT,
    status     TEXT DEFAULT 'pending',
    created_at TEXT,
    result     TEXT
);
CREATE INDEX IF NOT EXISTS idx_jobs_due ON jobs(status, run_at);
"""


class RecoveryStore:
    def __init__(self, db_path: str | Path) -> None:
        self.path = str(db_path)
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._db = sqlite3.connect(self.path, check_same_thread=False)
        self._db.row_factory = sqlite3.Row
        self._db.executescript(_SCHEMA)
        self._db.commit()

    # -- cases --------------------------------------------------------------- #
    def save_case(self, record: dict) -> None:
        with self._lock:
            self._db.execute(
                "INSERT OR REPLACE INTO cases "
                "(id, status, recovered, reason, klass, amount_paise, created_at, payload) "
                "VALUES (?,?,?,?,?,?,?,?)",
                (
                    record["id"],
                    record.get("status"),
                    int(bool(record.get("recovered"))),
                    record.get("reason"),
                    record.get("class"),
                    int(record.get("amount_paise") or 0),
                    record.get("occurred_at") or datetime.utcnow().isoformat(),
                    json.dumps(record),
                ),
            )
            self._db.commit()

    def list_cases(self, limit: int = 50, offset: int = 0) -> list[dict]:
        cur = self._db.execute(
            "SELECT payload FROM cases ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (limit, offset),
        )
        return [json.loads(r["payload"]) for r in cur.fetchall()]

    def count_cases(self) -> int:
        return self._db.execute("SELECT COUNT(*) AS n FROM cases").fetchone()["n"]

    # -- bandit posteriors --------------------------------------------------- #
    def save_bandit(self, ab: dict[tuple[str, str], list[float]]) -> None:
        with self._lock:
            self._db.executemany(
                "INSERT OR REPLACE INTO bandit (context, arm, alpha, beta) VALUES (?,?,?,?)",
                [(ctx, arm, float(a), float(b)) for (ctx, arm), (a, b) in ab.items()],
            )
            self._db.commit()

    def load_bandit(self) -> dict[tuple[str, str], list[float]]:
        cur = self._db.execute("SELECT context, arm, alpha, beta FROM bandit")
        return {(r["context"], r["arm"]): [r["alpha"], r["beta"]] for r in cur.fetchall()}

    # -- scheduled jobs ------------------------------------------------------ #
    def enqueue_job(self, case_id: str, action: str, channel: str, run_at: datetime) -> int:
        with self._lock:
            cur = self._db.execute(
                "INSERT INTO jobs (case_id, action, channel, run_at, status, created_at) "
                "VALUES (?,?,?,?, 'pending', ?)",
                (case_id, action, channel, run_at.isoformat(), datetime.utcnow().isoformat()),
            )
            self._db.commit()
            return int(cur.lastrowid)

    def due_jobs(self, now: datetime) -> list[dict]:
        cur = self._db.execute(
            "SELECT * FROM jobs WHERE status = 'pending' AND run_at <= ? ORDER BY run_at",
            (now.isoformat(),),
        )
        return [dict(r) for r in cur.fetchall()]

    def mark_job(self, job_id: int, status: str, result: str | None = None) -> None:
        with self._lock:
            self._db.execute(
                "UPDATE jobs SET status = ?, result = ? WHERE id = ?", (status, result, job_id)
            )
            self._db.commit()

    def pending_job_count(self) -> int:
        return self._db.execute(
            "SELECT COUNT(*) AS n FROM jobs WHERE status = 'pending'"
        ).fetchone()["n"]

    def close(self) -> None:
        self._db.close()
