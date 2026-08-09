from app.domain.services.date_parser import hours_until_deadline
from typing import Optional


def compute_priority(
    gemini_priority: str,
    due_date: Optional[str],
    received_at: str,
    category: str,
    routing_reason: str = "",
) -> str:
    """
    Final priority after Gemini's suggestion.
    Enforces the 72-hour rule and overdue invoice rule deterministically.
    """
    if due_date:
        hours = hours_until_deadline(due_date, received_at)
        if hours is not None and 0 <= hours <= 72:
            return "high"

    # Overdue invoice — Gemini should catch this but we enforce it too
    if category == "finance" and "overdue" in routing_reason.lower():
        return "high"

    # Trust Gemini for everything else
    if gemini_priority in ("high", "medium", "low"):
        return gemini_priority

    return "medium"
