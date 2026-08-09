import pytest
from app.graph.nodes.preprocess import _strip_quoted_text


@pytest.mark.parametrize("body,expected_contains,expected_not_contains", [
    # Standard > quoting
    (
        "Correction — budget is now Rs. 32 lakhs.\n\n> Original message\n> Budget was Rs. 25 lakhs.",
        "Correction — budget is now Rs. 32 lakhs.",
        "Rs. 25 lakhs",
    ),
    # "On [date] wrote:" pattern
    (
        "Please see the updated deadline below.\n\nOn 1 Aug 2026 at 09:14, Suresh wrote:\n> Please find our RFP attached.",
        "Please see the updated deadline below.",
        "Please find our RFP",
    ),
    # Outlook "--- Original Message ---"
    (
        "Following up on this.\n\n--- Original Message ---\nFrom: someone@company.com\nSubject: RFP",
        "Following up on this.",
        "Original Message",
    ),
    # "From: X Sent: Y To: Z" forwarded block
    (
        "FYI — please action.\n\nFrom: vendor@abc.com Sent: Monday To: sales@company.com\nSubject: Invoice",
        "FYI — please action.",
        "vendor@abc.com",
    ),
    # Underscore separator
    (
        "Thanks for the quick response.\n\n_______________________________\nPrevious thread content here.",
        "Thanks for the quick response.",
        "Previous thread content",
    ),
    # No quoted text — full body preserved
    (
        "We'd like a demo for our 30-person team. No rush.",
        "We'd like a demo for our 30-person team. No rush.",
        None,
    ),
    # Empty body
    (
        "",
        "",
        None,
    ),
])
def test_strip_quoted_text(body, expected_contains, expected_not_contains):
    result = _strip_quoted_text(body)
    assert expected_contains in result
    if expected_not_contains:
        assert expected_not_contains not in result
