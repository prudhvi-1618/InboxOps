import re
from app.graph.state import EmailProcessingState
from app.core.logging import get_logger

logger = get_logger(__name__)

# Patterns that mark the START of a quoted/forwarded block.
# Everything from the first match onwards is stripped.
_QUOTE_BOUNDARY_PATTERNS = [
    # "--- Original Message ---" / "---- Forwarded Message ----"
    r"^-{2,}\s*(original|forwarded)\s+message\s*-{2,}",
    # "On Mon, 1 Aug 2026, Suresh wrote:"
    r"^on\s+.{5,80}wrote\s*:",
    # "From: X Sent: Y To: Z"
    r"^from\s*:.{1,80}sent\s*:.{1,80}to\s*:",
    # Lines starting with > (standard email quoting)
    r"^>",
    # Outlook-style separator
    r"^_{5,}",
    # "Begin forwarded message:"
    r"^begin\s+forwarded\s+message",
    # "Reply above this line"
    r"reply\s+above\s+this\s+line",
    # Date + "at" + time + "wrote" pattern
    r"^\d{1,2}\s+\w+\s+20\d\d\s+at\s+\d{1,2}:\d{2}",
]

_COMPILED = [re.compile(p, re.IGNORECASE | re.MULTILINE) for p in _QUOTE_BOUNDARY_PATTERNS]


def _strip_quoted_text(body: str) -> str:
    """
    Removes quoted/forwarded reply chains from an email body.
    Returns only the new content written by the current sender.
    Preserves blank lines within the new content.
    """
    if not body:
        return ""

    lines = body.splitlines()
    cutoff = len(lines)

    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue
        for pattern in _COMPILED:
            if pattern.match(stripped):
                cutoff = i
                break
        if cutoff < len(lines):
            break

    new_content = "\n".join(lines[:cutoff]).strip()
    return new_content


def preprocess_node(state: EmailProcessingState) -> dict:
    """
    LangGraph node — runs first in the pipeline.

    1. Strips quoted reply chains from email body
    2. Logs how much was trimmed (useful for debugging double-extraction bugs)
    3. Returns updated email dict with clean body

    This ensures Gemini never sees quoted text and cannot
    double-extract deal values or dates from old messages.
    """
    email = dict(state["email"])
    original_body = email.get("body", "") or ""
    clean_body = _strip_quoted_text(original_body)

    trimmed_chars = len(original_body) - len(clean_body)
    if trimmed_chars > 0:
        logger.debug(
            f"[preprocess] {email.get('email_id')} "
            f"stripped {trimmed_chars} chars of quoted text "
            f"({len(original_body)} → {len(clean_body)})"
        )

    email["body"] = clean_body
    return {"email": email}
