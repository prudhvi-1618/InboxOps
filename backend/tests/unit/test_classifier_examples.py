"""
tests/unit/test_classifier_examples.py
The 12 canonical examples from the brief — ground truth test suite.
These tests call the full LangGraph graph — not just individual nodes.
Uses mocks to avoid live Gemini API calls.
"""
import pytest
from unittest.mock import AsyncMock, patch
from app.graph.workflow import email_graph
from app.graph.state import EmailProcessingState


def make_initial_state(email: dict) -> EmailProcessingState:
    return {
        "email": email,
        "candidate_id": "nirujogiprudhvi@gmail.com",
        "run_id": "test_run",
        "skip": False,
        "skipped_reason": None,
        "spam_lookalike_category": None,
        "already_processed": False,
        "existing_task_id": None,
        "needs_update": False,
        "gemini_result": None,
        "gemini_error": None,
        "assignee_id": None,
        "category": None,
        "priority": None,
        "due_date": None,
        "deal_value_inr": None,
        "company_name": None,
        "title": None,
        "description": None,
        "confidence": 0.5,
        "routing_reason": None,
        "task_id": None,
        "decision": None,
        "error_message": None,
    }


async def run_graph_no_write(email: dict, mock_resp: dict) -> dict:
    """Runs full graph but mocks task_writer and Gemini to avoid API calls."""
    state = make_initial_state(email)
    with patch(
        "app.graph.nodes.task_writer.post_new_task",
        new=AsyncMock(return_value={"task_id": "tsk_mock"}),
    ), patch(
        "app.graph.nodes.task_writer.patch_existing_task",
        new=AsyncMock(return_value={"task_id": "tsk_mock"}),
    ), patch(
        "app.graph.nodes.classify.call_gemini_json",
        new=AsyncMock(return_value=mock_resp),
    ):
        result = await email_graph.ainvoke(state)
    return result


# ── Example 1: Standard Enterprise RFP ───────────────────────────────────────
@pytest.mark.asyncio
async def test_ex01_enterprise_rfp():
    email = {
        "email_id": "em_ex01",
        "thread_id": "th_ex01",
        "message_index": 0,
        "from_name": "Suresh Kulkarni",
        "from_email": "s.kulkarni@meridiansteel.co.in",
        "subject": "RFP — Enterprise CRM Implementation (Ref: MS/IT/2026/044)",
        "body": "Budget is Rs. 25 lakhs for Year 1. Please submit your proposal by 12th August 2026.",
        "received_at": "2026-08-01T09:30:00Z",
        "is_reply": False,
    }
    mock_resp = {
        "assignee_id": "u_aarti",
        "category": "enterprise_rfp",
        "priority": "medium",
        "due_date": "2026-08-12",
        "deal_value_inr": 2500000,
        "confidence": 0.9,
        "decision": "task_created"
    }
    result = await run_graph_no_write(email, mock_resp)
    assert result.get("skip") is not True
    assert result["assignee_id"] == "u_aarti"
    assert result["category"] == "enterprise_rfp"
    assert result["deal_value_inr"] == 2500000
    assert result["due_date"] == "2026-08-12"
    assert result["priority"] in ("medium", "low")


# ── Example 2: SMB Demo Request ──────────────────────────────────────────────
@pytest.mark.asyncio
async def test_ex02_smb_demo():
    email = {
        "email_id": "em_ex02",
        "thread_id": "th_ex02",
        "message_index": 0,
        "from_name": "Priya Sharma",
        "from_email": "priya@craftsvilla.in",
        "subject": "Quick question about your pricing",
        "body": "Could we get a quick demo next week? Nothing urgent.",
        "received_at": "2026-08-01T11:00:00Z",
        "is_reply": False,
    }
    mock_resp = {
        "assignee_id": "u_rohit",
        "category": "smb_enquiry",
        "priority": "low",
        "deal_value_inr": None,
        "confidence": 0.8,
        "decision": "task_created"
    }
    result = await run_graph_no_write(email, mock_resp)
    assert result.get("skip") is not True
    assert result["assignee_id"] == "u_rohit"
    assert result["category"] == "smb_enquiry"
    assert result["deal_value_inr"] is None
    assert result["due_date"] is None
    assert result["priority"] == "low"


# ── Example 3: PSU Tender (Rule 2 overrides deal value) ──────────────────────
@pytest.mark.asyncio
async def test_ex03_psu_tender_override():
    email = {
        "email_id": "em_ex03",
        "thread_id": "th_ex03",
        "message_index": 0,
        "from_name": "Rajiv Nambiar",
        "from_email": "r.nambiar@bhel.in",
        "subject": "Tender Notice: BHEL/PROC/2026/089 — Software Licences",
        "body": "Estimated contract value: Rs. 6,50,000. Bid submission deadline: 03-08-2026 at 1700 hrs.",
        "received_at": "2026-08-01T14:20:00Z",
        "is_reply": False,
    }
    mock_resp = {
        "assignee_id": "u_aarti",
        "category": "enterprise_rfp",
        "priority": "high",
        "due_date": "2026-08-03",
        "deal_value_inr": 650000,
        "confidence": 0.9,
        "decision": "task_created"
    }
    result = await run_graph_no_write(email, mock_resp)
    assert result.get("skip") is not True
    assert result["assignee_id"] == "u_aarti", "PSU tender must go to Aarti regardless of value"
    assert result["category"] == "enterprise_rfp"
    assert result["deal_value_inr"] == 650000
    assert result["due_date"] == "2026-08-03"
    assert result["priority"] == "high", "<72h to deadline must be high priority"


# ── Example 4: Marketing Sponsorship ────────────────────────────────────────
@pytest.mark.asyncio
async def test_ex04_marketing_sponsorship():
    email = {
        "email_id": "em_ex04",
        "thread_id": "th_ex04",
        "message_index": 0,
        "from_name": "Ananya Roy",
        "from_email": "ananya@saasgrowthcon.com",
        "subject": "Gold Sponsorship Opportunity — SaaS Growth Con 2026",
        "body": "Cost is ₹4,00,000. Need confirmation by tomorrow EOD.",
        "received_at": "2026-08-02T10:00:00Z",
        "is_reply": False,
    }
    mock_resp = {
        "assignee_id": "u_meera",
        "category": "marketing",
        "priority": "high",
        "due_date": "2026-08-03",
        "deal_value_inr": 400000,
        "confidence": 0.9,
        "decision": "task_created"
    }
    result = await run_graph_no_write(email, mock_resp)
    assert result.get("skip") is not True
    assert result["assignee_id"] == "u_meera"
    assert result["category"] == "marketing"
    assert result["deal_value_inr"] == 400000
    assert result["due_date"] == "2026-08-03"
    assert result["priority"] == "high"


# ── Example 5: Overdue Invoice ───────────────────────────────────────────────
@pytest.mark.asyncio
async def test_ex05_overdue_invoice():
    email = {
        "email_id": "em_ex05",
        "thread_id": "th_ex05",
        "message_index": 0,
        "from_name": "Accounts Team",
        "from_email": "billing@cloudhost.co.in",
        "subject": "Invoice INV-2026-0331 overdue — immediate payment required",
        "body": "Please find attached invoice INV-2026-0331 for Rs. 1,18,000",
        "received_at": "2026-08-02T16:00:00Z",
        "is_reply": False,
    }
    mock_resp = {
        "assignee_id": "u_divya",
        "category": "finance",
        "priority": "high",
        "deal_value_inr": None,
        "confidence": 0.9,
        "decision": "task_created"
    }
    result = await run_graph_no_write(email, mock_resp)
    assert result.get("skip") is not True
    assert result["assignee_id"] == "u_divya"
    assert result["category"] == "finance"
    assert result["deal_value_inr"] is None, "Invoice amount is not a deal value"
    assert result["priority"] == "high"


# ── Example 6: Alliances Partnership ────────────────────────────────────────
@pytest.mark.asyncio
async def test_ex06_alliances_reseller():
    email = {
        "email_id": "em_ex06",
        "thread_id": "th_ex06",
        "message_index": 0,
        "from_name": "Vikram Sethi",
        "from_email": "v.sethi@apexconsulting.ae",
        "subject": "Reseller & Integration Partnership — Middle East Region",
        "body": "Who handles partnerships and reseller agreements at your company?",
        "received_at": "2026-08-03T12:00:00Z",
        "is_reply": False,
    }
    mock_resp = {
        "assignee_id": "u_karan",
        "category": "alliances",
        "priority": "medium",
        "deal_value_inr": None,
        "confidence": 0.9,
        "decision": "task_created"
    }
    result = await run_graph_no_write(email, mock_resp)
    assert result.get("skip") is not True
    assert result["assignee_id"] == "u_karan"
    assert result["category"] == "alliances"
    assert result["deal_value_inr"] is None
    assert result["due_date"] is None
    assert result["priority"] == "medium"


# ── Example 7: OOO Auto-Reply (Skip) ────────────────────────────────────────
@pytest.mark.asyncio
async def test_ex07_ooo_auto_reply():
    email = {
        "email_id": "em_ex07",
        "thread_id": "th_ex07",
        "message_index": 0,
        "from_name": "Sunil Mehta",
        "from_email": "sunil.mehta@tcs.com",
        "subject": "Automatic reply: Re: RFP Demo Follow-up",
        "body": "I am currently out of office on annual leave",
        "received_at": "2026-08-03T14:00:00Z",
        "is_reply": False,
    }
    mock_resp = {
        "decision": "skipped",
        "skipped_reason": "ooo",
        "confidence": 0.9
    }
    result = await run_graph_no_write(email, mock_resp)
    assert result.get("skip") is True
    assert result.get("skipped_reason") == "ooo"


# ── Example 8: Vendor Spam with Lookalike Words (Skip) ──────────────────────
@pytest.mark.asyncio
async def test_ex08_vendor_spam_lookalike():
    email = {
        "email_id": "em_ex08",
        "thread_id": "th_ex08",
        "message_index": 0,
        "from_name": "GrowTraffic Team",
        "from_email": "leads@growtraffic-fast.biz",
        "subject": "Guaranteed 10x Pipeline via B2B Webinars & PR Placements",
        "body": "Can we steal 15 mins this Thursday to share a free audit",
        "received_at": "2026-08-04T08:00:00Z",
        "is_reply": False,
    }
    mock_resp = {
        "decision": "skipped",
        "skipped_reason": "spam",
        "spam_lookalike_category": "marketing",
        "confidence": 0.9
    }
    result = await run_graph_no_write(email, mock_resp)
    assert result.get("skip") is True
    assert result.get("skipped_reason") in ("spam", "newsletter")


# ── Example 9: Newsletter (Skip) ─────────────────────────────────────────────
@pytest.mark.asyncio
async def test_ex09_newsletter():
    email = {
        "email_id": "em_ex09",
        "thread_id": "th_ex09",
        "message_index": 0,
        "from_name": "SaaS Pulse Digest",
        "from_email": "digest@saaspulse.io",
        "subject": "Issue #142: Why Vertical AI Agents Are Replacing Traditional SaaS",
        "body": "Read online | Sponsor the next issue | Unsubscribe",
        "received_at": "2026-08-04T10:00:00Z",
        "is_reply": False,
    }
    mock_resp = {
        "decision": "skipped",
        "skipped_reason": "newsletter",
        "confidence": 0.9
    }
    result = await run_graph_no_write(email, mock_resp)
    assert result.get("skip") is True
    assert result.get("skipped_reason") == "newsletter"


# ── Example 10: Thread Reply with Budget Increase ────────────────────────────
@pytest.mark.asyncio
async def test_ex10_thread_reply_budget_increase():
    email = {
        "email_id": "em_ex10",
        "thread_id": "th_ex01",
        "message_index": 1,
        "from_name": "Suresh Kulkarni",
        "from_email": "s.kulkarni@meridiansteel.co.in",
        "subject": "Re: RFP",
        "body": "Increasing the scope and budget to INR 32 lakhs.",
        "received_at": "2026-08-09T10:00:00Z",
        "is_reply": True,
    }
    mock_resp = {
        "assignee_id": "u_aarti",
        "category": "enterprise_rfp",
        "priority": "high",
        "due_date": "2026-08-11",
        "deal_value_inr": 3200000,
        "needs_update": True,
        "confidence": 0.9,
        "decision": "task_created"
    }
    result = await run_graph_no_write(email, mock_resp)
    assert result.get("skip") is not True
    assert result.get("needs_update") is True
    assert result["assignee_id"] == "u_aarti"
    assert result["category"] == "enterprise_rfp"
    assert result["deal_value_inr"] == 3200000
    assert result["due_date"] == "2026-08-11"
    assert result["priority"] == "high", "<72h to 11th Aug from Aug 9th must be high"


# ── Example 11: Ambiguous Email with Conflicting Asks ─────────────────────────
@pytest.mark.asyncio
async def test_ex11_ambiguous_two_asks():
    email = {
        "email_id": "em_ex11",
        "thread_id": "th_ex11",
        "message_index": 0,
        "from_name": "Harsh Vardhan",
        "from_email": "harsh@halcyonretail.com",
        "subject": "Possible partnership",
        "body": "Evaluating your platform (budget TBD), but marketing also wants webinar.",
        "received_at": "2026-08-05T15:00:00Z",
        "is_reply": False,
    }
    mock_resp = {
        "assignee_id": "u_triage",
        "category": "triage",
        "priority": "medium",
        "deal_value_inr": None,
        "confidence": 0.4,
        "decision": "task_created"
    }
    result = await run_graph_no_write(email, mock_resp)
    assert result.get("skip") is not True
    assert result["assignee_id"] == "u_triage"
    assert result["category"] == "triage"
    assert result["confidence"] < 0.6
    assert result["deal_value_inr"] is None


# ── Example 12: Hinglish High-Value Inbound ──────────────────────────────────
@pytest.mark.asyncio
async def test_ex12_hinglish_high_value():
    email = {
        "email_id": "em_ex12",
        "thread_id": "th_ex12",
        "message_index": 0,
        "from_name": "Manish Agarwal",
        "from_email": "m.agarwal@agarwaltextiles.com",
        "subject": "Software demo",
        "body": "Approx 1.2 cr ka budget allocate kiya hai for this FY. Demo kab mil sakta hai? Board review 20th ko hai",
        "received_at": "2026-08-05T12:00:00Z",
        "is_reply": False,
    }
    mock_resp = {
        "assignee_id": "u_aarti",
        "category": "enterprise_rfp",
        "priority": "medium",
        "due_date": "2026-08-20",
        "deal_value_inr": 12000000,
        "confidence": 0.9,
        "decision": "task_created"
    }
    result = await run_graph_no_write(email, mock_resp)
    assert result.get("skip") is not True
    assert result["assignee_id"] == "u_aarti", "₹1.2 cr (> ₹10L) must go to Aarti"
    assert result["category"] == "enterprise_rfp"
    assert result["deal_value_inr"] == 12000000
    assert result["due_date"] == "2026-08-20"
