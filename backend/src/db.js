// src/db.js
import Database from 'better-sqlite3';
import { mkdirSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const dataDir = join(__dirname, '..', 'data');
mkdirSync(dataDir, { recursive: true });

const db = new Database(join(dataDir, 'inbox_router.db'));

// WAL mode for concurrent reads during long ingest batches
db.pragma('journal_mode = WAL');
db.pragma('foreign_keys = ON');

db.exec(`
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
    email_id               TEXT PRIMARY KEY,
    thread_id              TEXT NOT NULL,
    run_id                 TEXT,
    decision               TEXT NOT NULL CHECK(decision IN ('task_created','task_updated','skipped','error')),
    category               TEXT,
    assignee_id            TEXT,
    task_id                TEXT,
    priority               TEXT,
    confidence             REAL,
    skipped_reason         TEXT,
    spam_lookalike_category TEXT,
    deal_value_inr         INTEGER,
    company_name           TEXT,
    due_date               TEXT,
    routing_reason         TEXT,
    raw_subject            TEXT,
    raw_from_email         TEXT,
    raw_from_name          TEXT,
    received_at            TEXT,
    processed_at           TEXT NOT NULL DEFAULT (datetime('now')),
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

  CREATE INDEX IF NOT EXISTS idx_email_decisions_thread
    ON email_decisions(thread_id);

  CREATE INDEX IF NOT EXISTS idx_email_decisions_decision
    ON email_decisions(decision);

  CREATE INDEX IF NOT EXISTS idx_email_decisions_category
    ON email_decisions(category);

  CREATE INDEX IF NOT EXISTS idx_thread_updates_thread
    ON thread_updates(thread_id);
`);

export default db;
