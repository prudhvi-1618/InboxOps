import pytest
import aiosqlite
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.ingestion import process_batch, _process_single_email
from app.models.result import IngestResult


@pytest.fixture
async def db():
    async with aiosqlite.connect(":memory:") as conn:
        conn.row_factory = aiosqlite.Row
        await conn.execute("PRAGMA foreign_keys=ON")
        await conn.executescript("""
            CREATE TABLE IF NOT EXISTS runs (
                run_id TEXT PRIMARY KEY, started_at TEXT NOT NULL,
                finished_at TEXT, email_count INTEGER DEFAULT 0,
                created INTEGER DEFAULT 0, updated INTEGER DEFAULT 0,
                skipped INTEGER DEFAULT 0, errors INTEGER DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS email_decisions (
                email_id TEXT PRIMARY KEY, thread_id TEXT NOT NULL,
                run_id TEXT, decision TEXT NOT NULL,
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
                task_id TEXT NOT NULL, action TEXT NOT NULL,
                updated_at TEXT NOT NULL DEFAULT (datetime('now'))
            );
        """)
        await conn.commit()
        yield conn


def make_email(email_id: str, thread_id: str, is_reply=False, message_index=0) -> dict:
    return {
        "email_id": email_id,
        "thread_id": thread_id,
        "subject": "Test RFP",
        "body": "Budget Rs. 25 lakhs. Deadline 12th August 2026.",
        "from_name": "Test Sender",
        "from_email": "test@test.com",
        "received_at": "2026-08-01T09:00:00+05:30",
        "is_reply": is_reply,
        "message_index": message_index,
    }


def mock_graph_result(decision="task_created", task_id="tsk_mock") -> dict:
    return {
        "decision": decision,
        "task_id": task_id,
        "assignee_id": "u_aarti",
        "category": "enterprise_rfp",
        "priority": "medium",
        "confidence": 0.91,
        "skipped_reason": None,
        "spam_lookalike_category": None,
        "deal_value_inr": 2_500_000,
        "company_name": "Test Co",
        "due_date": "2026-08-12",
        "routing_reason": "Enterprise RFP above threshold",
        "needs_update": False,
        "existing_task_id": None,
        "skip": False,
        "gemini_result": None,
        "gemini_error": None,
        "title": "RFP Test",
        "description": "Test description",
        "email": make_email("em_001", "th_001"),
        "candidate_id": "test@example.com",
        "run_id": "run_test",
        "already_processed": False,
        "error_message": None,
    }


# ── Test: summary counts are correct ─────────────────────────────────────────
@pytest.mark.asyncio
async def test_process_batch_returns_correct_counts(db):
    emails = [
        make_email("em_001", "th_001"),
        make_email("em_002", "th_002"),
        make_email("em_003", "th_003"),
    ]

    with patch(
        "app.services.ingestion.email_graph.ainvoke",
        new=AsyncMock(return_value=mock_graph_result()),
    ):
        result = await process_batch(emails, "test@example.com", db)

    assert result.processed == 3
    assert result.tasks_created == 3
    assert result.tasks_updated == 0
    assert result.skipped == 0
    assert result.errors == []


# ── Test: Run 2 idempotency — same batch twice, count unchanged ───────────────
@pytest.mark.asyncio
async def test_run2_idempotency(db):
    emails = [make_email("em_idem_01", "th_idem_01")]

    with patch(
        "app.services.ingestion.email_graph.ainvoke",
        new=AsyncMock(return_value=mock_graph_result(task_id="tsk_idem")),
    ):
        result1 = await process_batch(emails, "test@example.com", db)

    # Second run — same emails
    with patch(
        "app.services.ingestion.email_graph.ainvoke",
        new=AsyncMock(return_value=mock_graph_result(task_id="tsk_idem")),
    ) as mock_graph:
        result2 = await process_batch(emails, "test@example.com", db)
        # Graph must NOT be called for duplicate emails
        mock_graph.assert_not_called()

    assert result1.tasks_created == 1
    assert result2.tasks_created == 0
    assert result2.skipped == 1
    assert result2.processed == 1


# ── Test: thread reply → task_updated counted correctly ───────────────────────
@pytest.mark.asyncio
async def test_thread_reply_counted_as_updated(db):
    original = make_email("em_orig", "th_orig")
    reply = make_email("em_reply", "th_orig", is_reply=True, message_index=1)

    # First: original email
    with patch(
        "app.services.ingestion.email_graph.ainvoke",
        new=AsyncMock(return_value=mock_graph_result(
            decision="task_created", task_id="tsk_orig"
        )),
    ):
        r1 = await process_batch([original], "test@example.com", db)

    assert r1.tasks_created == 1

    # Second: reply on same thread
    updated_state = mock_graph_result(decision="task_updated", task_id="tsk_orig")
    updated_state["needs_update"] = True
    updated_state["existing_task_id"] = "tsk_orig"

    with patch(
        "app.services.ingestion.email_graph.ainvoke",
        new=AsyncMock(return_value=updated_state),
    ):
        r2 = await process_batch([reply], "test@example.com", db)

    assert r2.tasks_updated == 1
    assert r2.tasks_created == 0


# ── Test: error in one email does not crash batch ────────────────────────────
@pytest.mark.asyncio
async def test_one_error_does_not_crash_batch(db):
    emails = [
        make_email("em_good", "th_good"),
        make_email("em_bad", "th_bad"),
    ]

    call_count = 0

    async def mock_invoke(state):
        nonlocal call_count
        call_count += 1
        if state["email"]["email_id"] == "em_bad":
            raise Exception("Simulated Gemini failure")
        return mock_graph_result(task_id="tsk_good")

    with patch("app.services.ingestion.email_graph.ainvoke", side_effect=mock_invoke):
        result = await process_batch(emails, "test@example.com", db)

    assert result.processed == 2
    assert result.tasks_created == 1
    assert len(result.errors) == 1


# ── Test: skipped emails counted in result ────────────────────────────────────
@pytest.mark.asyncio
async def test_skipped_ooo_counted(db):
    email = make_email("em_ooo", "th_ooo")
    email["subject"] = "Out of Office"
    email["body"] = "I am out of office until 14th August."

    # Hygiene node fires before graph — graph returns skip decision
    skip_state = mock_graph_result()
    skip_state["decision"] = "skipped"
    skip_state["skipped_reason"] = "ooo"
    skip_state["task_id"] = None
    skip_state["assignee_id"] = None

    with patch(
        "app.services.ingestion.email_graph.ainvoke",
        new=AsyncMock(return_value=skip_state),
    ):
        result = await process_batch([email], "test@example.com", db)

    assert result.skipped == 1
    assert result.tasks_created == 0


# ── Test: IngestResult fields and types ──────────────────────────────────────
def test_ingest_result_default_shape():
    r = IngestResult()
    assert r.processed == 0
    assert r.tasks_created == 0
    assert r.tasks_updated == 0
    assert r.skipped == 0
    assert r.errors == []
    assert isinstance(r.errors, list)


def test_ingest_result_serialization():
    r = IngestResult(processed=60, tasks_created=41, tasks_updated=7, skipped=12)
    d = r.model_dump()
    assert d == {
        "processed": 60,
        "tasks_created": 41,
        "tasks_updated": 7,
        "skipped": 12,
        "errors": [],
    }
