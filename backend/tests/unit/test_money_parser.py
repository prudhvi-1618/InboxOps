import pytest
from app.domain.services.money_parser import parse_inr


@pytest.mark.parametrize("text,expected", [
    # Crore variants
    ("Budget approx 1.2 cr allocated hai", 12_000_000),
    ("Rs. 1 crore deal", 10_000_000),
    ("INR 2.5 crores", 25_000_000),
    ("budget is 1 Cr.", 10_000_000),
    # Lakh variants
    ("Rs. 25 lakhs", 2_500_000),
    ("indicative budget is Rs. 25 lakhs", 2_500_000),
    ("₹4,00,000", 400_000),
    ("6,50,000 estimated value", 650_000),
    ("Estimated value: Rs. 6,50,000", 650_000),
    ("10 lakh budget", 1_000_000),
    ("2.5 lakhs", 250_000),
    ("budget 5L", 500_000),
    # Plain with symbol
    ("invoice for Rs. 1,18,000", 118_000),
    ("₹ 32 lakhs", 3_200_000),
    # None cases
    ("no money mentioned here", None),
    ("call us ASAP", None),
    ("", None),
    (None, None),
])
def test_parse_inr(text, expected):
    assert parse_inr(text) == expected
