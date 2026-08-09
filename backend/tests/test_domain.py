import pytest
from app.domain.services.money_parser import parse_inr
from app.domain.services.date_parser import parse_due_date, hours_until_deadline
from app.domain.policies.hygiene import check_hygiene
from app.domain.policies.priority import compute_priority
from app.domain.policies.routing import validate_routing
from app.models.email import InboundEmail


def test_parse_inr():
    assert parse_inr("The budget is 25 lakh INR") == 2500000
    assert parse_inr("Deal size is around 1.2 cr") == 12000000
    assert parse_inr("₹10,00,000 for this project") == 1000000
    assert parse_inr("Budget: 5 Lakhs") == 500000
    assert parse_inr("No money mentioned") is None


def test_parse_due_date():
    received = "2026-08-10T10:00:00Z"
    # tomorrow
    assert parse_due_date("Please reply by tomorrow EOD", received) == "2026-08-11"
    # explicit date DD-MM-YYYY
    assert parse_due_date("Submit by 15-08-2026", received) == "2026-08-15"
    # ISO date
    assert parse_due_date("Deadline is 2026-08-20", received) == "2026-08-20"


def test_hours_until_deadline():
    received = "2026-08-10T10:00:00Z"
    due = "2026-08-11"
    hours = hours_until_deadline(due, received)
    assert hours is not None
    assert 0 < hours <= 72


def test_check_hygiene():
    ooo_email = InboundEmail(
        email_id="e1",
        thread_id="t1",
        from_name="Alice",
        from_email="alice@corp.com",
        subject="Out of office",
        body="I am away on leave until next Monday.",
        received_at="2026-08-10T10:00:00Z",
    )
    result = check_hygiene(ooo_email)
    assert result is not None
    assert result["skipped_reason"] == "ooo"

    spam_email = InboundEmail(
        email_id="e2",
        thread_id="t2",
        from_name="Spammer",
        from_email="spammer@agency.com",
        subject="Rank on page 1",
        body="We offer SEO services and free audit. Quick 15 min call?",
        received_at="2026-08-10T10:00:00Z",
    )
    result2 = check_hygiene(spam_email)
    assert result2 is not None
    assert result2["skipped_reason"] == "spam"


def test_compute_priority():
    # within 72 hours
    priority = compute_priority("low", "2026-08-11", "2026-08-10T10:00:00Z", "smb_enquiry")
    assert priority == "high"

    # normal
    priority2 = compute_priority("medium", None, "2026-08-10T10:00:00Z", "smb_enquiry")
    assert priority2 == "medium"


def test_validate_routing():
    assignee, cat = validate_routing("u_aarti", "enterprise_rfp")
    assert assignee == "u_aarti"
    assert cat == "enterprise_rfp"

    assignee_invalid, cat_invalid = validate_routing("unknown", "invalid")
    assert assignee_invalid == "u_triage"
    assert cat_invalid == "triage"
