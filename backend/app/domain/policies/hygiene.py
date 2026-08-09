import re
from app.models.email import InboundEmail


# ── OOO signals ──────────────────────────────────────────────────────────────
_OOO_PATTERNS = [
    r"out\s+of\s+office",
    r"i\s+am\s+away",
    r"i'?m\s+currently\s+out",
    r"on\s+leave\s+until",
    r"will\s+be\s+back\s+(on|from)",
    r"auto[\s\-]?reply",
    r"automatic\s+reply",
    r"\booo\b",
    r"away\s+from\s+(the\s+)?office",
    r"limited\s+access\s+to\s+(my\s+)?email",
    r"on\s+vacation",
    r"currently\s+unavailable",
    r"i\s+will\s+be\s+out",
    r"on\s+annual\s+leave",
    r"public\s+holiday",
]

# ── Newsletter signals ────────────────────────────────────────────────────────
_NEWSLETTER_PATTERNS = [
    r"\[\s*unsubscribe\s*\]",
    r"unsubscribe\s+here",
    r"unsubscribe\s+from\s+this",
    r"issue\s+#\s*\d+",
    r"weekly\s+digest",
    r"\bnewsletter\b",
    r"you('?re|\s+are)\s+receiving\s+this\s+(because|email)",
    r"view\s+(in|this\s+email)\s+(browser|online)",
    r"email\s+preferences",
    r"in\s+this\s+edition[\s:]+",
    r"top\s+stories\s+(this\s+week|today)",
    r"manage\s+(your\s+)?subscription",
    r"sent\s+to\s+you\s+by",
    r"©\s*20\d\d\s+\w+.*all\s+rights\s+reserved",
]

# ── Spam / cold outreach signals ──────────────────────────────────────────────
_SPAM_PATTERNS = [
    r"we('?ve|\s+have)\s+helped\s+\d+\+?\s+(companies|brands|clients|saas)",
    r"\b3x\s+(your|their|our)\s+(organic|traffic|revenue|leads)",
    r"\bfree\s+audit\b",
    r"quick\s+15[\s\-]?min(ute)?\s+call",
    r"just\s+circling\s+back",
    r"following\s+up\s+on\s+my\s+(previous|last|earlier)\s+email",
    r"rank(ing)?\s+on\s+page\s+1",
    r"\bseo\s+(services?|agency|expert|specialist|strateg)",
    r"lead\s+gen(eration)?",
    r"we\s+noticed\s+your\s+(website|company|profile|brand)",
    r"i\s+(came\s+across|found|noticed)\s+your\s+(website|company|profile)",
    r"cold\s+email",
    r"double\s+your\s+(leads|revenue|traffic|conversions)",
    r"boost\s+your\s+(rankings|traffic|sales|revenue)",
    r"done-for-you\s+(content|marketing|seo)",
    r"we\s+speciali[sz]e\s+in\s+(helping|working\s+with)",
    r"interested\s+in\s+a\s+(quick\s+)?(demo|call|chat)\?",
    r"would\s+love\s+to\s+connect(\s+with\s+you)?",
    r"mutual\s+benefit",
    r"no\s+obligation",
    r"risk[\s\-]?free",
    r"100\s*%\s+guarantee",
    r"case\s+stud(y|ies)\s+from\s+(similar|top|leading)",
]

# ── Spam-lookalike category map ───────────────────────────────────────────────
# If spam email uses keywords from a real category, record which one it mimics
_LOOKALIKE_PATTERNS: list[tuple[str, str]] = [
    (r"webinar|sponsorship|content\s+market|pr\s+outreach|media\s+coverage|podcast|seo|organic\s+traffic|rank(ing)?\s+on\s+page", "marketing"),
    (r"resell|channel\s+partner|technology\s+integration|api\s+partner|white[\s\-]?label", "alliances"),
    (r"\brfp\b|\btender\b|\bproposal\b|\bbid\b", "enterprise_rfp"),
    (r"invoice|billing|payment|gst|vendor", "finance"),
]


def _match_any(patterns: list[str], text: str) -> bool:
    return any(re.search(p, text, re.IGNORECASE) for p in patterns)


def _detect_lookalike(text: str) -> str | None:
    for pattern, category in _LOOKALIKE_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return category
    return None


def check_hygiene(email: InboundEmail) -> dict | None:
    """
    Runs pure-regex hygiene checks BEFORE any Gemini call.
    Returns a skip dict if the email should be skipped, else None.

    Returned dict shape:
      { "skipped_reason": "ooo"|"newsletter"|"spam", "spam_lookalike_category": str|None }

    Priority order: OOO → Newsletter → Spam
    A skip here means NO Gemini call, NO task, NO triage entry.
    """
    subject = email.subject or ""
    body = email.body or ""
    combined = f"{subject} {body}"

    # ── OOO — check subject first (fastest signal) ───────────────────────────
    subject_lower = subject.lower()
    if any(kw in subject_lower for kw in (
        "out of office", "auto-reply", "automatic reply", "ooo", "on leave", "away from office"
    )):
        return {"skipped_reason": "ooo", "spam_lookalike_category": None}

    if _match_any(_OOO_PATTERNS, combined):
        return {"skipped_reason": "ooo", "spam_lookalike_category": None}

    # ── Newsletter ────────────────────────────────────────────────────────────
    if _match_any(_NEWSLETTER_PATTERNS, combined):
        return {"skipped_reason": "newsletter", "spam_lookalike_category": None}

    # ── Spam / cold outreach ──────────────────────────────────────────────────
    if _match_any(_SPAM_PATTERNS, combined):
        lookalike = _detect_lookalike(combined)
        return {"skipped_reason": "spam", "spam_lookalike_category": lookalike}

    return None
