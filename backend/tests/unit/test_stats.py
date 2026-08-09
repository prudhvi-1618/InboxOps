import pytest
import aiosqlite
from app.api.routes.stats import get_stats
from app.infrastructure.database.repository import EmailDecisionRepository


@pytest.fixture
async def db():
    async with aiosqlite.connect(":memory:") as conn:
        conn.row_factory = aiosqlite.Row
        await conn.executescript("""
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
            CREATE TABLE IF NOT EXISTS runs (
                run_id TEXT PRIMARY KEY, started_at TEXT NOT NULL,
                finished_at TEXT, email_count INTEGER DEFAULT 0,
                created INTEGER DEFAULT 0, updated INTEGER DEFAULT 0,
                skipped INTEGER DEFAULT 0, errors INTEGER DEFAULT 0
            );
        """)
        await conn.commit()
        yield conn


async def seed(db, records: list[dict]):
    repo = EmailDecisionRepository(db)
    for r in records:
        await repo.insert_decision(r)


@pytest.mark.asyncio
async def test_stats_all_zeros_on_empty_db(db):
    result = await get_stats(db)
    assert result["totals"]["processed"] == 0
    assert result["totals"]["created"] == 0
    assert result["gst_refund_count"] == 0
    assert result["spurious_rate"]["rate"] == 0.0
    assert result["triage_items"] == []


@pytest.mark.asyncio
async def test_stats_category_breakdown(db):
    await seed(db, [
        {"email_id": "em_01", "thread_id": "th_01", "decision": "task_created",
         "category": "enterprise_rfp", "assignee_id": "u_aarti",
         "confidence": 0.91, "deal_value_inr": 2_500_000},
        {"email_id": "em_02", "thread_id": "th_02", "decision": "task_created",
         "category": "enterprise_rfp", "assignee_id": "u_aarti",
         "confidence": 0.85, "deal_value_inr": None},
        {"email_id": "em_03", "thread_id": "th_03", "decision": "task_created",
         "category": "marketing", "assignee_id": "u_meera",
         "confidence": 0.88},
        {"email_id": "em_04", "thread_id": "th_04", "decision": "skipped",
         "skipped_reason": "spam", "spam_lookalike_category": "marketing"},
    ])

    result = await get_stats(db)

    categories = {r["category"]: r["count"] for r in result["by_category"]}
    assert categories.get("enterprise_rfp") == 2
    assert categories.get("marketing") == 1

    skip_reasons = {r["skipped_reason"]: r["count"] for r in result["skip_reasons"]}
    assert skip_reasons.get("spam") == 1


@pytest.mark.asyncio
async def test_stats_deal_value_sum(db):
    await seed(db, [
        {"email_id": "em_v1", "thread_id": "th_v1", "decision": "task_created",
         "category": "enterprise_rfp", "assignee_id": "u_aarti",
         "deal_value_inr": 2_500_000},
        {"email_id": "em_v2", "thread_id": "th_v2", "decision": "task_created",
         "category": "enterprise_rfp", "assignee_id": "u_aarti",
         "deal_value_inr": 3_200_000},
        {"email_id": "em_v3", "thread_id": "th_v3", "decision": "task_created",
         "category": "enterprise_rfp", "assignee_id": "u_aarti",
         "deal_value_inr": None},  # no stated value
    ])

    result = await get_stats(db)
    dv = result["total_deal_value"]
    assert dv["sum_inr"] == 5_700_000
    assert dv["rfp_count_with_value"] == 2
    assert dv["rfp_count_without_value"] == 1


@pytest.mark.asyncio
async def test_stats_triage_items_have_reasons(db):
    await seed(db, [
        {"email_id": "em_t1", "thread_id": "th_t1", "decision": "task_created",
         "assignee_id": "u_triage", "category": "triage",
         "confidence": 0.42,
         "routing_reason": "Two conflicting asks: RFP and webinar",
         "company_name": "Halcyon Retail"},
    ])

    result = await get_stats(db)
    assert len(result["triage_items"]) == 1
    assert result["triage_items"][0]["routing_reason"] == "Two conflicting asks: RFP and webinar"
    assert result["triage_items"][0]["company_name"] == "Halcyon Retail"


@pytest.mark.asyncio
async def test_stats_gst_refund_is_zero(db):
    """Deliberate zero trap — must return 0, not hallucinate."""
    await seed(db, [
        {"email_id": "em_inv", "thread_id": "th_inv", "decision": "task_created",
         "category": "finance", "assignee_id": "u_divya",
         "raw_subject": "Invoice INV-2026-0331"},
    ])
    result = await get_stats(db)
    assert result["gst_refund_count"] == 0


@pytest.mark.asyncio
async def test_stats_spurious_rate_zero_for_clean_system(db):
    await seed(db, [
        {"email_id": "em_c1", "thread_id": "th_c1", "decision": "task_created",
         "category": "enterprise_rfp", "assignee_id": "u_aarti"},
        {"email_id": "em_s1", "thread_id": "th_s1", "decision": "skipped",
         "skipped_reason": "ooo"},
    ])
    result = await get_stats(db)
    assert result["spurious_rate"]["spurious_count"] == 0
    assert result["spurious_rate"]["rate"] == 0.0


@pytest.mark.asyncio
async def test_stats_threads_updated_multiple_times(db):
    await seed(db, [
        {"email_id": "em_orig", "thread_id": "th_multi", "decision": "task_created",
         "task_id": "tsk_multi", "assignee_id": "u_aarti"},
    ])
    await db.execute(
        "INSERT INTO thread_updates (thread_id, email_id, task_id, action) VALUES (?,?,?,?)",
        ("th_multi", "em_orig", "tsk_multi", "created"),
    )
    await db.execute(
        "INSERT INTO thread_updates (thread_id, email_id, task_id, action) VALUES (?,?,?,?)",
        ("th_multi", "em_reply1", "tsk_multi", "updated"),
    )
    await db.execute(
        "INSERT INTO thread_updates (thread_id, email_id, task_id, action) VALUES (?,?,?,?)",
        ("th_multi", "em_reply2", "tsk_multi", "updated"),
    )
    await db.commit()

    result = await get_stats(db)
    multi = result["threads_updated_multiple_times"]
    assert len(multi) == 1
    assert multi[0]["thread_id"] == "th_multi"
    assert multi[0]["update_count"] == 3
