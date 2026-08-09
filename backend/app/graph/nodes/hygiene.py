from app.graph.state import EmailProcessingState
from app.domain.policies.hygiene import check_hygiene
from app.models.email import InboundEmail
from app.core.logging import get_logger

logger = get_logger(__name__)


def hygiene_node(state: EmailProcessingState) -> dict:
    """
    Runs regex-based hygiene checks before any LLM call.
    If the email is OOO / newsletter / spam — mark skip=True immediately.
    """
    email = InboundEmail(**state["email"])
    result = check_hygiene(email)

    if result:
        logger.info(f"[hygiene] SKIP {email.email_id} reason={result['skipped_reason']}")
        return {
            "skip": True,
            "skipped_reason": result["skipped_reason"],
            "spam_lookalike_category": result.get("spam_lookalike_category"),
            "decision": "skipped",
        }

    return {"skip": False, "skipped_reason": None, "spam_lookalike_category": None}
