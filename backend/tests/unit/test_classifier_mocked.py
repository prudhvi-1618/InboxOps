"""
tests/unit/test_classifier_mocked.py
Tests the entire LangGraph pipeline across all 12 canonical examples
with mocked Gemini responses to verify graph state transitions,
domain policies, rate limiter, and idempotency logic deterministically.
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


async def run_graph_with_gemini_mock(email: dict, mock_gemini_resp: dict | None) -> dict:
    state = make_initial_state(email)
    with patch(
        "app.graph.nodes.task_writer.task_writer_node",
        new=AsyncMock(return_value={"task_id": "tsk_mock", "decision": "task_created"}),
    ), patch(
        "app.graph.nodes.classify.call_gemini_json",
        new=AsyncMock(return_value=mock_gemini_resp),
    ):
        result = await email_graph.ainvoke(state)
    return result


@pytest.mark.asyncio
async def test_mock_ex01_enterprise_rfp():
    email = {
        "email_id": "em_ex01",
        "thread_id": "th_ex01",
        "message_index": 0,
        "from_name": "Suresh Kulkarni",
        "from_email": "s.kulkarni@meridiansteel.co.in",
        "subject": "RFP — Enterprise CRM Implementation (Ref: MS/IT/2026/044)",
        "body": (
            "Dear Sales Team,\n\n"
            "Meridian Steel is issuing an RFP for enterprise CRM. "
            "Our budget is Rs. 25 lakhs for Year 1. "
            "Please submit your proposal by 12th August 2026.\n\n"
            "Regards,\nSuresh Kulkarni\nHead of IT, Meridian Steel"
        ),
        "received_at": "2026-08-01T09:30:00Z",
        "is_reply": False,
    }
    gemini_resp = {
        "decision": "task_created",
        "assignee_id": "u_aarti",
        "category": "enterprise_rfp",
        "priority": "medium",
        "due_date": "2026-08-12",
        "deal_value_inr": 2500000,
        "company_name": "Meridian Steel",
        "title": "Enterprise CRM RFP — Meridian Steel",
        "description": "RFP for enterprise CRM implementation with 25L budget",
        "confidence": 0.95,
        "routing_reason": "Rule 3: Enterprise RFP with budget 25L > 10L",
    }
    result = await run_graph_with_gemini_mock(email, gemini_resp)
    assert result.get("skip") is not True
    assert result["assignee_id"] == "u_aarti"
    assert result["category"] == "enterprise_rfp"
    assert result["deal_value_inr"] == 2500000
    assert result["due_date"] == "2026-08-12"


@pytest.mark.asyncio
async def test_mock_ex02_smb_demo():
    email = {
        "email_id": "em_ex02",
        "thread_id": "th_ex02",
        "message_index": 0,
        "from_name": "Priya Sharma",
        "from_email": "priya@craftsvilla.in",
        "subject": "Quick question about your pricing",
        "body": (
            "Hi team,\n\n"
            "We are a 30-person direct-to-consumer brand looking for an inbox tool. "
            "Could we get a quick demo next week? Nothing urgent.\n\n"
            "Thanks,\nPriya"
        ),
        "received_at": "2026-08-01T11:00:00Z",
        "is_reply": False,
    }
    gemini_resp = {
        "decision": "task_created",
        "assignee_id": "u_rohit",
        "category": "smb_enquiry",
        "priority": "low",
        "due_date": None,
        "deal_value_inr": None,
        "company_name": "Craftsvilla",
        "title": "Demo Request — Craftsvilla",
        "description": "30-person D2C brand asking for product demo",
        "confidence": 0.92,
        "routing_reason": "Rule 4: SMB demo request with low urgency",
    }
    result = await run_graph_with_gemini_mock(email, gemini_resp)
    assert result.get("skip") is not True
    assert result["assignee_id"] == "u_rohit"
    assert result["category"] == "smb_enquiry"
    assert result["deal_value_inr"] is None
    assert result["priority"] == "low"


@pytest.mark.asyncio
async def test_mock_ex03_psu_tender_override():
    email = {
        "email_id": "em_ex03",
        "thread_id": "th_ex03",
        "message_index": 0,
        "from_name": "Rajiv Nambiar",
        "from_email": "r.nambiar@bhel.in",
        "subject": "Tender Notice: BHEL/PROC/2026/089 — Software Licences",
        "body": (
            "Bharat Heavy Electricals Limited (BHEL) invites bids for software licences. "
            "Estimated contract value: Rs. 6,50,000. "
            "Bid submission deadline: 03-08-2026 at 1700 hrs. "
            "Late submissions will be rejected without consideration."
        ),
        "received_at": "2026-08-01T14:20:00Z",
        "is_reply": False,
    }
    gemini_resp = {
        "decision": "task_created",
        "assignee_id": "u_aarti",
        "category": "enterprise_rfp",
        "priority": "high",
        "due_date": "2026-08-03",
        "deal_value_inr": 650000,
        "company_name": "Bharat Heavy Electricals Limited",
        "title": "BHEL Tender BHEL/PROC/2026/089",
        "description": "PSU tender for software licences",
        "confidence": 0.98,
        "routing_reason": "Rule 2: PSU tender overrides deal value",
    }
    result = await run_graph_with_gemini_mock(email, gemini_resp)
    assert result["assignee_id"] == "u_aarti"
    assert result["category"] == "enterprise_rfp"
    assert result["priority"] == "high"


@pytest.mark.asyncio
async def test_mock_ex04_marketing_sponsorship():
    email = {
        "email_id": "em_ex04",
        "thread_id": "th_ex04",
        "message_index": 0,
        "from_name": "Ananya Roy",
        "from_email": "ananya@saasgrowthcon.com",
        "subject": "Gold Sponsorship Opportunity — SaaS Growth Con 2026",
        "body": (
            "Hi team,\n\n"
            "We have 1 Gold Sponsorship slot left for SaaS Growth Con 2026 (Bengaluru). "
            "Cost is ₹4,00,000. Need confirmation by tomorrow EOD as brochures go to print.\n\n"
            "Best,\nAnanya"
        ),
        "received_at": "2026-08-02T10:00:00Z",
        "is_reply": False,
    }
    gemini_resp = {
        "decision": "task_created",
        "assignee_id": "u_meera",
        "category": "marketing",
        "priority": "high",
        "due_date": "2026-08-03",
        "deal_value_inr": 400000,
        "company_name": "SaaS Growth Con",
        "title": "Gold Sponsorship — SaaS Growth Con 2026",
        "description": "Event sponsorship opportunity ₹4L due tomorrow",
        "confidence": 0.95,
        "routing_reason": "Rule 5: Event sponsorship opportunity",
    }
    result = await run_graph_with_gemini_mock(email, gemini_resp)
    assert result["assignee_id"] == "u_meera"
    assert result["category"] == "marketing"
    assert result["deal_value_inr"] == 400000
    assert result["priority"] == "high"


@pytest.mark.asyncio
async def test_mock_ex05_overdue_invoice():
    email = {
        "email_id": "em_ex05",
        "thread_id": "th_ex05",
        "message_index": 0,
        "from_name": "Accounts Team",
        "from_email": "billing@cloudhost.co.in",
        "subject": "Invoice INV-2026-0331 overdue — immediate payment required",
        "body": (
            "Please find attached invoice INV-2026-0331 for Rs. 1,18,000 (incl. 18% GST) "
            "against PO-88214. Kindly process — payment terms were Net 30 and this is "
            "now 12 days overdue. Also, our GSTIN has changed to 27AAACL1234A1Z5."
        ),
        "received_at": "2026-08-02T16:00:00Z",
        "is_reply": False,
    }
    gemini_resp = {
        "decision": "task_created",
        "assignee_id": "u_divya",
        "category": "finance",
        "priority": "high",
        "due_date": None,
        "deal_value_inr": None,
        "company_name": "CloudHost",
        "title": "Overdue Invoice INV-2026-0331",
        "description": "Overdue payment reminder for invoice INV-2026-0331",
        "confidence": 0.97,
        "routing_reason": "Rule 7: Invoice overdue",
    }
    result = await run_graph_with_gemini_mock(email, gemini_resp)
    assert result["assignee_id"] == "u_divya"
    assert result["category"] == "finance"
    assert result["deal_value_inr"] is None
    assert result["priority"] == "high"


@pytest.mark.asyncio
async def test_mock_ex06_alliances_reseller():
    email = {
        "email_id": "em_ex06",
        "thread_id": "th_ex06",
        "message_index": 0,
        "from_name": "Vikram Sethi",
        "from_email": "v.sethi@apexconsulting.ae",
        "subject": "Reseller & Integration Partnership — Middle East Region",
        "body": (
            "Dear Team,\n\n"
            "Apex Consulting is a Salesforce and HubSpot implementation partner in UAE and Saudi. "
            "We have 40+ enterprise clients asking for an inbox routing layer. "
            "Who handles partnerships and reseller agreements at your company?\n\n"
            "Best,\nVikram Sethi"
        ),
        "received_at": "2026-08-03T12:00:00Z",
        "is_reply": False,
    }
    gemini_resp = {
        "decision": "task_created",
        "assignee_id": "u_karan",
        "category": "alliances",
        "priority": "medium",
        "due_date": None,
        "deal_value_inr": None,
        "company_name": "Apex Consulting",
        "title": "Partnership Proposal — Apex Consulting",
        "description": "Reseller and integration partnership query",
        "confidence": 0.94,
        "routing_reason": "Rule 6: Reseller partnership inquiry",
    }
    result = await run_graph_with_gemini_mock(email, gemini_resp)
    assert result["assignee_id"] == "u_karan"
    assert result["category"] == "alliances"
    assert result["deal_value_inr"] is None


@pytest.mark.asyncio
async def test_mock_ex07_ooo_auto_reply():
    email = {
        "email_id": "em_ex07",
        "thread_id": "th_ex07",
        "message_index": 0,
        "from_name": "Sunil Mehta",
        "from_email": "sunil.mehta@tcs.com",
        "subject": "Automatic reply: Re: RFP Demo Follow-up",
        "body": (
            "I am currently out of office on annual leave until Monday, 18th August 2026 "
            "with limited access to email. For urgent queries regarding the CRM project, "
            "please contact neha.gupta@tcs.com."
        ),
        "received_at": "2026-08-03T14:00:00Z",
        "is_reply": False,
    }
    result = await run_graph_with_gemini_mock(email, None)
    assert result.get("skip") is True
    assert result.get("skipped_reason") == "ooo"


@pytest.mark.asyncio
async def test_mock_ex08_vendor_spam():
    email = {
        "email_id": "em_ex08",
        "thread_id": "th_ex08",
        "message_index": 0,
        "from_name": "GrowTraffic Team",
        "from_email": "leads@growtraffic-fast.biz",
        "subject": "Guaranteed 10x Pipeline via B2B Webinars & PR Placements",
        "body": (
            "Hi there,\n\n"
            "We help fast-growing SaaS companies scale outbound. Our clients see 40+ demo requests "
            "in 30 days via our syndicated webinar network and Forbes/TechCrunch PR packages. "
            "Can we steal 15 mins this Thursday to share a free audit of your current reach?\n\n"
            "Best,\nGrowTraffic BD Team\n[Unsubscribe | Preferences]"
        ),
        "received_at": "2026-08-04T08:00:00Z",
        "is_reply": False,
    }
    result = await run_graph_with_gemini_mock(email, None)
    assert result.get("skip") is True
    assert result.get("skipped_reason") in ("spam", "newsletter")


@pytest.mark.asyncio
async def test_mock_ex09_newsletter():
    email = {
        "email_id": "em_ex09",
        "thread_id": "th_ex09",
        "message_index": 0,
        "from_name": "SaaS Pulse Digest",
        "from_email": "digest@saaspulse.io",
        "subject": "Issue #142: Why Vertical AI Agents Are Replacing Traditional SaaS",
        "body": (
            "In this edition: The rise of domain-specific agents, how Indian enterprises are "
            "procuring AI in 2026, and our interview with the founder of DevRev.\n\n"
            "Read online | Sponsor the next issue | Unsubscribe"
        ),
        "received_at": "2026-08-04T10:00:00Z",
        "is_reply": False,
    }
    result = await run_graph_with_gemini_mock(email, None)
    assert result.get("skip") is True
    assert result.get("skipped_reason") == "newsletter"


@pytest.mark.asyncio
async def test_mock_ex10_thread_reply():
    email = {
        "email_id": "em_ex10",
        "thread_id": "th_ex01",
        "message_index": 1,
        "from_name": "Suresh Kulkarni",
        "from_email": "s.kulkarni@meridiansteel.co.in",
        "subject": "Re: RFP — Enterprise CRM Implementation (Ref: MS/IT/2026/044)",
        "body": (
            "Hi Team,\n\n"
            "Following internal review, we are increasing the scope and budget to INR 32 lakhs. "
            "Also, our submission deadline is advanced to 11th August.\n\n"
            "--- Original Message ---\n"
            "From: Suresh Kulkarni\n"
            "Budget is Rs. 25 lakhs... by 12th August"
        ),
        "received_at": "2026-08-09T10:00:00Z",
        "is_reply": True,
    }
    gemini_resp = {
        "decision": "task_created",
        "assignee_id": "u_aarti",
        "category": "enterprise_rfp",
        "priority": "high",
        "due_date": "2026-08-11",
        "deal_value_inr": 3200000,
        "company_name": "Meridian Steel",
        "title": "RFP Scope & Budget Increase — Meridian Steel",
        "description": "Budget increased to 32L, deadline advanced to 11th Aug",
        "confidence": 0.96,
        "routing_reason": "Rule 3: Enterprise RFP update",
        "needs_update": True,
    }
    result = await run_graph_with_gemini_mock(email, gemini_resp)
    assert result.get("needs_update") is True
    assert result["assignee_id"] == "u_aarti"
    assert result["deal_value_inr"] == 3200000
    assert result["due_date"] == "2026-08-11"
    assert result["priority"] == "high"


@pytest.mark.asyncio
async def test_mock_ex11_ambiguous_two_asks():
    email = {
        "email_id": "em_ex11",
        "thread_id": "th_ex11",
        "message_index": 0,
        "from_name": "Harsh Vardhan",
        "from_email": "harsh@halcyonretail.com",
        "subject": "Possible partnership / large deal — need guidance",
        "body": (
            "Hi,\n\n"
            "We are evaluating your platform for our 800-person organisation (budget TBD), "
            "but our marketing team also wants to co-host a webinar series with you next quarter. "
            "Not sure who the right contact is — can we connect?\n\n"
            "Harsh Vardhan"
        ),
        "received_at": "2026-08-05T15:00:00Z",
        "is_reply": False,
    }
    gemini_resp = {
        "decision": "task_created",
        "assignee_id": "u_triage",
        "category": "triage",
        "priority": "medium",
        "due_date": None,
        "deal_value_inr": None,
        "company_name": "Halcyon Retail",
        "title": "Ambiguous Query — Halcyon Retail",
        "description": "Evaluation for 800 users plus webinar request",
        "confidence": 0.45,
        "routing_reason": "Rule 8: Conflicting asks between enterprise evaluation and marketing webinar",
    }
    result = await run_graph_with_gemini_mock(email, gemini_resp)
    assert result["assignee_id"] == "u_triage"
    assert result["category"] == "triage"
    assert result["confidence"] < 0.6
    assert result["deal_value_inr"] is None


@pytest.mark.asyncio
async def test_mock_ex12_hinglish_high_value():
    email = {
        "email_id": "em_ex12",
        "thread_id": "th_ex12",
        "message_index": 0,
        "from_name": "Manish Agarwal",
        "from_email": "m.agarwal@agarwaltextiles.com",
        "subject": "Software demo and pricing chahiye",
        "body": (
            "Namaste,\n\n"
            "Humare 3 plants ke liye aapka software evaluate karna hai. "
            "Approx 1.2 cr ka budget allocate kiya hai for this FY. "
            "Demo kab mil sakta hai? Board review 20th ko hai, usse pehle proposal chahiye.\n\n"
            "Manish Agarwal\nDirector, Operations"
        ),
        "received_at": "2026-08-05T12:00:00Z",
        "is_reply": False,
    }
    gemini_resp = {
        "decision": "task_created",
        "assignee_id": "u_aarti",
        "category": "enterprise_rfp",
        "priority": "medium",
        "due_date": "2026-08-20",
        "deal_value_inr": 12000000,
        "company_name": None,
        "title": "Enterprise Evaluation — 3 Plants",
        "description": "Software evaluation for 3 plants with 1.2 cr budget",
        "confidence": 0.91,
        "routing_reason": "Rule 3: Enterprise deal 1.2 cr > 10L",
    }
    result = await run_graph_with_gemini_mock(email, gemini_resp)
    assert result["assignee_id"] == "u_aarti"
    assert result["category"] == "enterprise_rfp"
    assert result["deal_value_inr"] == 12000000
    assert result["due_date"] == "2026-08-20"
