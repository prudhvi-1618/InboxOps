import pytest
import aiosqlite
import asyncio
from pathlib import Path
from app.infrastructure.database.connection import run_migrations, get_db_path
from app.infrastructure.database.repository import EmailDecisionRepository
from app.services.idempotency import check_and_resolve


@pytest.fixture
async def db():
    """In-memory SQLite for each test — fully isolated."""
    async with aiosqlite.connect(":memory:") as conn:
        conn.row_factory = aiosqlite.Row
        await conn.execute("PRAGMA foreign_keys=ON")
        await conn.executescript("""
            CREATE TABLE IF NOT EXISTS email_decisions (
                email_id TEXT PRIMARY KEY,
                thread_id TEXT NOT NULL,
                run_id TEXT,
                decision TEXT NOT NULL,
                category TEXT, assignee_id TEXT, task_id TEXT,
                priority TEXT, confidence REAL, skipped_reason TEXT,
                spam_lookalike_category TEXT, deal_value_inr INTEGER,
                company_name TEXT, due_date TEXT, routing_reason TEXT,
                raw_subject TEXT, raw_from_email TEXT, raw_from_name TEXT,
                received_at TEXT,
                processed_at TEXT NOT NULL DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS thread_updates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                thread_id TEXT NOT NULL, email_id TEXT NOT NULL,
                task_id TEXT NOT NULL,
                action TEXT NOT NULL, updated_at TEXT NOT NULL DEFAULT (datetime('now'))
            );
        """)
        await conn.commit()
        yield conn


@pytest.mark.asyncio
async def test_fresh_email_no_thread(db):
    """New email, no prior thread → Case 3."""
    result = await check_and_resolve("em_new", "th_new", False, 0, db)
    assert result["already_processed"] is False
    assert result["needs_update"] is False
    assert result["existing_task_id"] is None


@pytest.mark.asyncio
async def test_duplicate_email_skipped(db):
    """Same email_id posted twice → Case 1 on second call."""
    repo = EmailDecisionRepository(db)
    await repo.insert_decision({
        "email_id": "em_dup",
        "thread_id": "th_dup",
        "decision": "task_created",
        "task_id": "tsk_abc",
    })

    result = await check_and_resolve("em_dup", "th_dup", False, 0, db)
    assert result["already_processed"] is True
    assert result["existing_task_id"] == "tsk_abc"


@pytest.mark.asyncio
async def test_reply_on_known_thread(db):
    """is_reply=True + thread has task → Case 2, needs_update=True."""
    repo = EmailDecisionRepository(db)
    await repo.insert_decision({
        "email_id": "em_orig",
        "thread_id": "th_001",
        "decision": "task_created",
        "task_id": "tsk_xyz",
    })

    result = await check_and_resolve("em_reply", "th_001", True, 1, db)
    assert result["already_processed"] is False
    assert result["needs_update"] is True
    assert result["existing_task_id"] == "tsk_xyz"


@pytest.mark.asyncio
async def test_reply_on_unknown_thread_treated_as_fresh(db):
    """is_reply=True but original was spam (no task) → treat as fresh POST."""
    result = await check_and_resolve("em_reply_orphan", "th_orphan", True, 1, db)
    assert result["already_processed"] is False
    assert result["needs_update"] is False
    assert result["existing_task_id"] is None


@pytest.mark.asyncio
async def test_message_index_triggers_update(db):
    """message_index > 0 also triggers Case 2 even if is_reply=False."""
    repo = EmailDecisionRepository(db)
    await repo.insert_decision({
        "email_id": "em_first",
        "thread_id": "th_002",
        "decision": "task_created",
        "task_id": "tsk_qqq",
    })

    result = await check_and_resolve("em_second", "th_002", False, 1, db)
    assert result["needs_update"] is True
    assert result["existing_task_id"] == "tsk_qqq"


@pytest.mark.asyncio
async def test_idempotency_is_db_backed_not_memory(db):
    """
    Simulates Run 2: same email ingested in a new 'session'.
    The DB record persists — not an in-memory cache.
    """
    repo = EmailDecisionRepository(db)
    await repo.insert_decision({
        "email_id": "em_run1",
        "thread_id": "th_run1",
        "decision": "task_created",
        "task_id": "tsk_run1",
    })

    # Simulate second ingest call (new check_and_resolve call, same DB)
    result1 = await check_and_resolve("em_run1", "th_run1", False, 0, db)
    result2 = await check_and_resolve("em_run1", "th_run1", False, 0, db)

    assert result1["already_processed"] is True
    assert result2["already_processed"] is True
