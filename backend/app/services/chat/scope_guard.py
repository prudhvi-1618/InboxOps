"""
Scope guard for the chat interface.
Determines whether a query is answerable from local DB data
or must be declined as out-of-scope.

Two layers:
  Layer 1 — Keyword pre-check (fast, no Gemini, catches obvious actions)
  Layer 2 — Intent-based check (after Gemini parsing, catches subtle cases)

Design principle:
  "I don't have that breakdown" is always better than a fabricated answer.
  Honest zero or honest refusal scores higher than confident hallucination.
"""

import re
from app.core.logging import get_logger

logger = get_logger(__name__)

# ── Layer 1: action keyword patterns ─────────────────────────────────────────
_ACTION_PATTERNS = [
    r"\bsend\b.*\bemail\b",
    r"\bemail\s+(aarti|rohit|meera|karan|divya|the\s+team)\b",
    r"\bcreate\s+(a\s+)?task\b",
    r"\bassign\s+(this\s+)?(to|task)\b",
    r"\bdelete\s+(this\s+)?task\b",
    r"\bforward\s+this\b",
    r"\breply\s+to\b",
    r"\bschedule\s+a\s+(meeting|call|demo)\b",
    r"\bbook\s+a\s+(call|meeting|slot)\b",
    r"\bupdate\s+the\s+task\b",
    r"\bmark\s+(this\s+)?as\s+(done|complete|resolved)\b",
    r"\bnotify\s+(aarti|rohit|meera|karan|divya)\b",
]

_COMPILED_ACTION = [re.compile(p, re.IGNORECASE) for p in _ACTION_PATTERNS]

# ── Layer 2: questions that sound analytical but cannot be answered ────────────
# These are answered with partial data + honest caveat
_PARTIAL_ANSWER_PATTERNS = [
    r"resellers?\s+(vs|versus)\s+tech(nology)?\s+(integration|partner)",
    r"sub.?categor",
    r"breakdown\s+within\s+alliances",
    r"which\s+type\s+of\s+(reseller|partner)",
]

_COMPILED_PARTIAL = [re.compile(p, re.IGNORECASE) for p in _PARTIAL_ANSWER_PATTERNS]


class ScopeDecision:
    """Result of scope check."""

    def __init__(
        self,
        is_in_scope: bool,
        is_partial: bool = False,
        refusal_message: str = "",
        caveat: str = "",
    ):
        self.is_in_scope = is_in_scope
        self.is_partial = is_partial          # True → answer with caveat
        self.refusal_message = refusal_message
        self.caveat = caveat


def check_scope(query: str) -> ScopeDecision:
    """
    Layer 1 + Layer 2 scope check.
    Returns ScopeDecision.

    is_in_scope=True  → proceed to intent parsing + SQL
    is_in_scope=False, is_partial=False → full refusal
    is_in_scope=True,  is_partial=True  → answer with caveat
    """
    q = query.strip()

    # ── Layer 1: action requests → full refusal ───────────────────────────────
    for pattern in _COMPILED_ACTION:
        if pattern.search(q):
            logger.info(f"[scope_guard] Action request blocked: '{q[:60]}'")
            return ScopeDecision(
                is_in_scope=False,
                refusal_message=(
                    "This interface answers questions about processed email data — "
                    "it does not send emails, create tasks, or take any actions. "
                    "Please ask a question about routing results, counts, or statistics."
                ),
            )

    # ── Layer 2: partial-answer queries ──────────────────────────────────────
    for pattern in _COMPILED_PARTIAL:
        if pattern.search(q):
            logger.info(f"[scope_guard] Partial-answer query: '{q[:60]}'")
            return ScopeDecision(
                is_in_scope=True,
                is_partial=True,
                caveat=(
                    "Note: I can only provide the top-level category count — "
                    "sub-category breakdowns (e.g. resellers vs tech integration) "
                    "are not stored in the routing data."
                ),
            )

    return ScopeDecision(is_in_scope=True)


def build_refusal_response(decision: ScopeDecision) -> dict:
    """
    Builds the full ChatResponse dict for a refused query.
    supporting_data is always {} for refusals.
    """
    return {
        "answer": decision.refusal_message,
        "supporting_data": {},
    }
