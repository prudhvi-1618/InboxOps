import sqlite3
import aiosqlite
import os
from pathlib import Path
from app.core.logging import get_logger

logger = get_logger(__name__)

DB_PATH = Path(__file__).parent.parent.parent.parent / "data" / "inbox_router.db"


def get_db_path() -> Path:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return DB_PATH


def run_migrations() -> None:
    """
    Run synchronously once at startup.
    All CREATE TABLE IF NOT EXISTS — safe to re-run.
    """
    db_path = get_db_path()
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS runs (
            run_id       TEXT PRIMARY KEY,
            started_at   TEXT NOT NULL,
            finished_at  TEXT,
            email_count  INTEGER DEFAULT 0,
            created      INTEGER DEFAULT 0,
            updated      INTEGER DEFAULT 0,
            skipped      INTEGER DEFAULT 0,
            errors       INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS email_decisions (
            email_id                TEXT PRIMARY KEY,
            thread_id               TEXT NOT NULL,
            run_id                  TEXT,
            decision                TEXT NOT NULL
                CHECK(decision IN ('task_created','task_updated','skipped','error')),
            category                TEXT,
            assignee_id             TEXT,
            task_id                 TEXT,
            priority                TEXT,
            confidence              REAL,
            skipped_reason          TEXT,
            spam_lookalike_category TEXT,
            deal_value_inr          INTEGER,
            company_name            TEXT,
            due_date                TEXT,
            routing_reason          TEXT,
            raw_subject             TEXT,
            raw_from_email          TEXT,
            raw_from_name           TEXT,
            received_at             TEXT,
            processed_at            TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY(run_id) REFERENCES runs(run_id)
        );

        CREATE TABLE IF NOT EXISTS thread_updates (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            thread_id   TEXT NOT NULL,
            email_id    TEXT NOT NULL,
            task_id     TEXT NOT NULL,
            action      TEXT NOT NULL CHECK(action IN ('created','updated')),
            updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS tasks (
            task_id         TEXT PRIMARY KEY,
            candidate_id    TEXT NOT NULL,
            source_email_id TEXT NOT NULL,
            thread_id       TEXT NOT NULL,
            title           TEXT NOT NULL,
            description     TEXT,
            assignee_id     TEXT NOT NULL,
            category        TEXT NOT NULL,
            priority        TEXT NOT NULL,
            due_date        TEXT,
            deal_value_inr  INTEGER,
            company_name    TEXT,
            confidence      REAL NOT NULL DEFAULT 0.5,
            created_at      TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at      TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_ed_thread
            ON email_decisions(thread_id);
        CREATE INDEX IF NOT EXISTS idx_ed_decision
            ON email_decisions(decision);
        CREATE INDEX IF NOT EXISTS idx_ed_category
            ON email_decisions(category);
        CREATE INDEX IF NOT EXISTS idx_ed_run
            ON email_decisions(run_id);
        CREATE INDEX IF NOT EXISTS idx_tu_thread
            ON thread_updates(thread_id);
        CREATE INDEX IF NOT EXISTS idx_tasks_candidate
            ON tasks(candidate_id);
        CREATE INDEX IF NOT EXISTS idx_tasks_thread
            ON tasks(thread_id);
        CREATE INDEX IF NOT EXISTS idx_tasks_assignee
            ON tasks(assignee_id);
        CREATE INDEX IF NOT EXISTS idx_tasks_category
            ON tasks(category);
    """)
    conn.commit()
    conn.close()
    logger.info(f"Database ready at {db_path}")


async def get_db() -> aiosqlite.Connection:
    """FastAPI dependency — yields one async connection per request."""
    db_path = get_db_path()
    async with aiosqlite.connect(str(db_path)) as conn:
        conn.row_factory = aiosqlite.Row
        await conn.execute("PRAGMA journal_mode=WAL")
        await conn.execute("PRAGMA foreign_keys=ON")
        yield conn


async def init_db() -> None:
    """Async database initializer."""
    run_migrations()
