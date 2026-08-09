import pytest
from app.domain.policies.hygiene import check_hygiene
from app.models.email import InboundEmail


def make_email(subject="", body="") -> InboundEmail:
    return InboundEmail(
        email_id="em_test",
        thread_id="th_test",
        subject=subject,
        body=body,
        from_name="Test",
        from_email="test@test.com",
        received_at="2026-08-08T10:00:00+05:30",
    )


# ── OOO ──────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("subject,body", [
    ("Out of Office", "I will be back on Monday."),
    ("Auto-Reply: Away", "I am currently out of the office."),
    ("", "I am away until 14th August with limited access to email."),
    ("OOO until Aug 20", "For urgent matters contact raghav@northbridge.in"),
    ("", "On vacation, will be back from 15th August."),
])
def test_ooo_detected(subject, body):
    result = check_hygiene(make_email(subject, body))
    assert result is not None
    assert result["skipped_reason"] == "ooo"


# ── Newsletter ────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("subject,body", [
    ("B2B Growth Weekly", "In this edition: why PLG is stalling. [Unsubscribe]"),
    ("Issue #212", "Top stories this week in SaaS. Manage your subscription."),
    ("", "You are receiving this because you subscribed. View in browser."),
])
def test_newsletter_detected(subject, body):
    result = check_hygiene(make_email(subject, body))
    assert result is not None
    assert result["skipped_reason"] == "newsletter"


# ── Spam ─────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("subject,body,expected_lookalike", [
    (
        "Quick question",
        "Hi, I noticed your website isn't ranking on page 1. We've helped 200+ SaaS companies 3x their organic traffic. Free audit attached — interested in a quick 15 min call?",
        "marketing",   # mentions content/pr-adjacent words
    ),
    (
        "Partnership opportunity",
        "We specialize in helping B2B companies double their leads. Would love to connect. No obligation.",
        None,
    ),
    (
        "Content collaboration",
        "We do content marketing, PR outreach, and webinar promotion for SaaS companies. Risk-free trial.",
        "marketing",
    ),
])
def test_spam_detected(subject, body, expected_lookalike):
    result = check_hygiene(make_email(subject, body))
    assert result is not None
    assert result["skipped_reason"] == "spam"
    assert result["spam_lookalike_category"] == expected_lookalike


# ── Legitimate emails — must NOT be skipped ───────────────────────────────────
@pytest.mark.parametrize("subject,body", [
    ("RFP - Enterprise DMS", "Meridian Steel invites proposals. Budget Rs. 25 lakhs."),
    ("Quick demo request", "Hi, we're a 30-person startup. Can we get a demo next week?"),
    ("Sponsorship - India SaaS Summit", "We need confirmation by tomorrow EOD."),
    ("Invoice INV-2026-0331", "Please process payment. 12 days overdue."),
    ("Reseller partnership", "We'd like to explore reselling your platform in MEA."),
    ("Bhai product chahiye", "Budget approx 1.2 cr. Board review 20th ko hai."),
])
def test_legitimate_not_skipped(subject, body):
    result = check_hygiene(make_email(subject, body))
    assert result is None, f"Legitimate email incorrectly skipped: subject='{subject}'"
