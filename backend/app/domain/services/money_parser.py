import re
from typing import Optional

# Multipliers
_LAKH = 100_000
_CRORE = 10_000_000


def parse_inr(text: str) -> Optional[int]:
    """
    Extracts the FIRST Indian currency amount from free text.
    Returns integer rupees or None if nothing unambiguous found.

    Handles:
      - crore / crores / cr / C
      - lakh / lakhs / lac / lacs / L
      - plain numbers with ₹ / Rs. / INR prefix
      - comma-formatted numbers (1,00,000 or 6,50,000)
      - decimal multipliers (1.2 cr, 2.5 lakhs)

    Does NOT guess. Returns None if ambiguous.
    """
    if not text:
        return None

    text_lower = text.lower()

    # ── Pattern 1: X crore(s) / X cr / X C ──────────────────────────────────
    m = re.search(
        r"(?:rs\.?\s*|inr\s*|₹\s*)?"
        r"([\d]+(?:\.[\d]+)?)"
        r"\s*(?:crores?|cr\.?)\b",
        text_lower,
    )
    if m:
        return _to_int(m.group(1), _CRORE)

    # ── Pattern 2: X lakh(s) / X lac(s) / X L ───────────────────────────────
    m = re.search(
        r"(?:rs\.?\s*|inr\s*|₹\s*)?"
        r"([\d]+(?:\.[\d]+)?)"
        r"\s*(?:lakhs?|lacs?|l\b)",
        text_lower,
    )
    if m:
        return _to_int(m.group(1), _LAKH)

    # ── Pattern 3: ₹ / Rs. / INR followed by plain number ───────────────────
    m = re.search(
        r"(?:rs\.?\s*|inr\s*|₹\s*)"
        r"([\d, ]+(?:\.[\d]+)?)\b",
        text_lower,
    )
    if m:
        raw = m.group(1).replace(",", "").replace(" ", "")
        return _to_int(raw, 1)

    # ── Pattern 4: Comma-formatted Indian / Western numbers (e.g. 6,50,000 or 1,00,000) ──
    m = re.search(
        r"\b(\d{1,3}(?:,\d{2})*,\d{3}(?:\.\d+)?)\b",
        text_lower,
    )
    if m:
        raw = m.group(1).replace(",", "").replace(" ", "")
        return _to_int(raw, 1)

    return None


def _to_int(value_str: str, multiplier: float) -> Optional[int]:
    try:
        return int(round(float(value_str) * multiplier))
    except (ValueError, TypeError):
        return None
