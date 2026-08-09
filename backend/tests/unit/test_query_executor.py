import pytest
import aiosqlite
from app.services.chat.query_executor import execute_intent
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
        """)
        await conn.commit()
        yield conn


async def seed(db, records):
    repo = EmailDecisionRepository(db)
    for r in records:
        await repo.insert_decision(r)


# ── Count queries ─────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_count_enterprise_rfp(db):
    await seed(db, [
        {"email_id": "em_01", "thread_id": "th_01", "decision": "task_created", "category": "enterprise_rfp", "assignee_id": "u_aarti"},
        {"email_id": "em_02", "thread_id": "th_02", "decision": "task_created", "category": "enterprise_rfp", "assignee_id": "u_aarti"},
        {"email_id": "em_03", "thread_id": "th_03", "decision": "task_created", "category": "marketing", "assignee_id": "u_meera"},
    ])
    intent = {"intent_type": "count", "filters": {"category": "enterprise_rfp"},
              "group_by": None, "sub_intent": None, "sum_field": None,
              "include_fields": [], "limit": None, "aggregation": "count"}
    result = await execute_intent(intent, db)
    assert result["result"] == 2
    assert "enterprise_rfp" in str(result["supporting_data"])


# ── Zero count — must return 0 not hallucinate ────────────────────────────────
@pytest.mark.asyncio
async def test_gst_refund_zero(db):
    await seed(db, [
        {"email_id": "em_inv", "thread_id": "th_inv", "decision": "task_created",
         "category": "finance", "assignee_id": "u_divya",
         "raw_subject": "Invoice INV-2026-0331"},
    ])
    intent = {"intent_type": "zero_check", "filters": {}, "group_by": None,
              "sub_intent": "gst_refund_count", "sum_field": None,
              "include_fields": [], "limit": None, "aggregation": "count"}
    result = await execute_intent(intent, db)
    assert result["result"] == 0
    assert result["supporting_data"]["gst_refund_count"] == 0


# ── Sum deal value ────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_sum_deal_value(db):
    await seed(db, [
        {"email_id": "em_v1", "thread_id": "th_v1", "decision": "task_created",
         "category": "enterprise_rfp", "deal_value_inr": 2_500_000},
        {"email_id": "em_v2", "thread_id": "th_v2", "decision": "task_created",
         "category": "enterprise_rfp", "deal_value_inr": 3_200_000},
        {"email_id": "em_v3", "thread_id": "th_v3", "decision": "task_created",
         "category": "enterprise_rfp", "deal_value_inr": None},
    ])
    intent = {"intent_type": "sum", "filters": {"category": "enterprise_rfp"},
              "sum_field": "deal_value_inr", "group_by": None, "sub_intent": None,
              "include_fields": [], "limit": None, "aggregation": "sum"}
    result = await execute_intent(intent, db)
    sd = result["supporting_data"]
    assert sd["total_deal_value_inr"] == 5_700_000
    assert sd["records_with_value"] == 2
    assert sd["records_without_value"] == 1


# ── Triage with reasons ───────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_triage_with_reasons(db):
    await seed(db, [
        {"email_id": "em_t1", "thread_id": "th_t1", "decision": "task_created",
         "assignee_id": "u_triage", "category": "triage", "task_id": "tsk_t1",
         "confidence": 0.42, "routing_reason": "Two conflicting asks",
         "company_name": "Halcyon Retail"},
    ])
    intent = {"intent_type": "list", "filters": {"assignee_id": "u_triage"},
              "sub_intent": "triage_with_reasons", "group_by": None,
              "sum_field": None, "include_fields": [], "limit": None, "aggregation": "list"}
    result = await execute_intent(intent, db)
    sd = result["supporting_data"]
    assert sd["triage_count"] == 1
    assert "tsk_t1" in sd["triage_task_ids"]
    assert result["result"][0]["routing_reason"] == "Two conflicting asks"


# ── Compound filter: high priority + low confidence ───────────────────────────
@pytest.mark.asyncio
async def test_compound_high_priority_low_confidence(db):
    await seed(db, [
        {"email_id": "em_c1", "thread_id": "th_c1", "decision": "task_created",
         "priority": "high", "confidence": 0.38, "task_id": "tsk_c1",
         "category": "triage", "assignee_id": "u_triage"},
        {"email_id": "em_c2", "thread_id": "th_c2", "decision": "task_created",
         "priority": "high", "confidence": 0.92, "task_id": "tsk_c2",
         "category": "enterprise_rfp", "assignee_id": "u_aarti"},
        {"email_id": "em_c3", "thread_id": "th_c3", "decision": "task_created",
         "priority": "medium", "confidence": 0.40, "task_id": "tsk_c3",
         "category": "marketing", "assignee_id": "u_meera"},
    ])
    intent = {"intent_type": "compound_filter",
              "filters": {"priority": "high", "confidence_lt": 0.65},
              "sub_intent": None, "group_by": None, "sum_field": None,
              "include_fields": [], "limit": None, "aggregation": "list"}
    result = await execute_intent(intent, db)
    sd = result["supporting_data"]
    assert sd["count"] == 1
    assert sd["matches"][0]["task_id"] == "tsk_c1"
    assert sd["matches"][0]["confidence"] == 0.38


# ── Out of scope ──────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_out_of_scope_returns_no_data(db):
    intent = {"intent_type": "out_of_scope", "filters": {},
              "sub_intent": None, "group_by": None, "sum_field": None,
              "include_fields": [], "limit": None, "aggregation": None,
              "out_of_scope_reason": "Cannot send emails"}
    result = await execute_intent(intent, db)
    assert result["out_of_scope"] is True
    assert result["supporting_data"] == {}
    assert result["result"] is None


# ── Spurious rate ─────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_spurious_rate_zero(db):
    await seed(db, [
        {"email_id": "em_s1", "thread_id": "th_s1", "decision": "task_created",
         "category": "enterprise_rfp", "assignee_id": "u_aarti"},
        {"email_id": "em_s2", "thread_id": "th_s2", "decision": "skipped",
         "skipped_reason": "ooo"},
    ])
    intent = {"intent_type": "rate", "filters": {}, "sub_intent": "spurious_rate",
              "group_by": None, "sum_field": None,
              "include_fields": [], "limit": None, "aggregation": "rate"}
    result = await execute_intent(intent, db)
    sd = result["supporting_data"]
    assert sd["spurious_count"] == 0
    assert sd["spurious_rate"] == 0.0


# ── Threads updated multiple times ────────────────────────────────────────────
@pytest.mark.asyncio
async def test_threads_multi_updated(db):
    await db.execute(
        "INSERT INTO thread_updates (thread_id,email_id,task_id,action) VALUES (?,?,?,?)",
        ("th_m1", "em_orig", "tsk_m1", "created"),
    )
    await db.execute(
        "INSERT INTO thread_updates (thread_id,email_id,task_id,action) VALUES (?,?,?,?)",
        ("th_m1", "em_rep1", "tsk_m1", "updated"),
    )
    await db.execute(
        "INSERT INTO thread_updates (thread_id,email_id,task_id,action) VALUES (?,?,?,?)",
        ("th_m1", "em_rep2", "tsk_m1", "updated"),
    )
    await db.commit()

    intent = {"intent_type": "list", "filters": {}, "sub_intent": "threads_multi_updated",
              "group_by": None, "sum_field": None,
              "include_fields": [], "limit": None, "aggregation": "list"}
    result = await execute_intent(intent, db)
    sd = result["supporting_data"]
    assert "th_m1" in sd["threads_updated_multiple_times"]
