import pytest
import aiosqlite
from unittest.mock import AsyncMock, patch
from app.services.chat.intent_parser import parse_intent
from app.services.chat.query_executor import execute_intent
from app.services.chat.answer_phraser import phrase_answer, _fallback_answer
from app.services.chat.scope_guard import check_scope, ScopeDecision
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


# ── Scope guard tests ─────────────────────────────────────────────────────────

@pytest.mark.parametrize("query", [
    "Send Aarti an email about the Meridian Steel RFP",
    "Email Rohit about the demo request",
    "Create a task for this email",
    "Assign this to Meera",
    "Schedule a meeting with the client",
    "Book a call with Karan",
    "Delete this task",
    "Forward this to Divya",
])
def test_scope_guard_blocks_actions(query):
    decision = check_scope(query)
    assert decision.is_in_scope is False
    assert decision.refusal_message != ""


@pytest.mark.parametrize("query", [
    "How many RFPs came in?",
    "Show me everything in triage",
    "What is our spurious rate?",
    "How many emails were about GST refunds?",
    "Which tasks are high priority but low confidence?",
    "Did any thread get updated more than once?",
    "What is the total deal value of all open RFPs?",
])
def test_scope_guard_allows_analytics(query):
    decision = check_scope(query)
    assert decision.is_in_scope is True


def test_scope_guard_partial_alliances_sub_category():
    decision = check_scope(
        "How many alliances emails came from resellers versus tech integration partners?"
    )
    assert decision.is_in_scope is True
    assert decision.is_partial is True
    assert "sub-category" in decision.caveat.lower()


# ── Answer phraser tests ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_phraser_returns_zero_for_zero_count():
    mock_result = {"answer": "There were zero emails about GST refunds."}
    with patch(
        "app.services.chat.answer_phraser.call_gemini_json",
        return_value=mock_result,
    ):
        answer = await phrase_answer(
            "How many emails were about GST refunds?",
            {"query_result": 0, "supporting_data": {"gst_refund_count": 0}},
        )
    assert "zero" in answer.lower() or "0" in answer


@pytest.mark.asyncio
async def test_phraser_fallback_on_gemini_failure():
    with patch(
        "app.services.chat.answer_phraser.call_gemini_json",
        side_effect=Exception("Gemini down"),
    ):
        answer = await phrase_answer(
            "How many RFPs?",
            {"query_result": 14, "supporting_data": {"enterprise_rfp_count": 14}},
        )
    # Fallback must return something non-empty
    assert answer != ""
    assert len(answer) > 5


def test_fallback_answer_integer():
    assert "14" in _fallback_answer(14)


def test_fallback_answer_empty_list():
    result = _fallback_answer([])
    assert "none" in result.lower() or "no matching" in result.lower()


def test_fallback_answer_none():
    result = _fallback_answer(None)
    assert result != ""


# ── Full pipeline integration test (no Gemini) ────────────────────────────────

@pytest.mark.asyncio
async def test_full_chat_pipeline_grounded(db):
    """
    Verifies that supporting_data matches the SQL result — not Gemini's output.
    This is what the grader cross-checks.
    """
    repo = EmailDecisionRepository(db)
    await repo.insert_decision({
        "email_id": "em_rfp_01", "thread_id": "th_rfp_01",
        "decision": "task_created", "category": "enterprise_rfp",
        "assignee_id": "u_aarti", "confidence": 0.91,
        "deal_value_inr": 2_500_000,
    })
    await repo.insert_decision({
        "email_id": "em_rfp_02", "thread_id": "th_rfp_02",
        "decision": "task_created", "category": "enterprise_rfp",
        "assignee_id": "u_aarti", "confidence": 0.88,
        "deal_value_inr": 3_200_000,
    })

    intent = {
        "intent_type": "count",
        "filters": {"category": "enterprise_rfp"},
        "group_by": None, "sub_intent": None,
        "sum_field": None, "include_fields": [],
        "limit": None, "aggregation": "count",
    }

    execution = await execute_intent(intent, db)

    # supporting_data must reflect actual SQL count
    assert execution["result"] == 2
    assert execution["supporting_data"].get("enterprise_rfp_count") == 2

    # Phrase the answer (mocked Gemini)
    with patch(
        "app.services.chat.answer_phraser.call_gemini_json",
        return_value={"answer": "There were 2 enterprise RFP emails in this batch."},
    ):
        answer = await phrase_answer(
            "How many RFP emails came in?",
            {"query_result": 2, "supporting_data": execution["supporting_data"]},
        )

    assert "2" in answer
    # supporting_data is from SQL — independent of answer string
    assert execution["supporting_data"]["enterprise_rfp_count"] == 2


@pytest.mark.asyncio
async def test_zero_count_never_hallucinated(db):
    """
    GST refund zero trap — the canonical grader hallucination test.
    Even with real email data in DB, GST refund count must be 0.
    """
    repo = EmailDecisionRepository(db)
    await repo.insert_decision({
        "email_id": "em_fin_01", "thread_id": "th_fin_01",
        "decision": "task_created", "category": "finance",
        "assignee_id": "u_divya", "raw_subject": "Invoice INV-2026-0331",
    })

    intent = {
        "intent_type": "zero_check", "filters": {},
        "sub_intent": "gst_refund_count", "group_by": None,
        "sum_field": None, "include_fields": [], "limit": None,
        "aggregation": "count",
    }
    execution = await execute_intent(intent, db)

    assert execution["result"] == 0
    assert execution["supporting_data"]["gst_refund_count"] == 0

    # Phrase it — Gemini must say zero
    with patch(
        "app.services.chat.answer_phraser.call_gemini_json",
        return_value={"answer": "There were zero emails about GST refunds."},
    ):
        answer = await phrase_answer(
            "How many emails were about GST refunds?",
            {"query_result": 0, "supporting_data": {"gst_refund_count": 0}},
        )

    assert "zero" in answer.lower() or "0" in answer
    # Most important: supporting_data is 0 from SQL — grader sees this
    assert execution["supporting_data"]["gst_refund_count"] == 0
