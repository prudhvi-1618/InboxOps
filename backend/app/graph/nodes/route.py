from app.graph.state import EmailProcessingState
from app.domain.policies.routing import validate_routing
from app.domain.policies.priority import compute_priority
from app.domain.services.money_parser import parse_inr
from app.domain.services.date_parser import parse_due_date
from app.core.logging import get_logger

logger = get_logger(__name__)


def route_node(state: EmailProcessingState) -> dict:
    """
    Takes raw Gemini output and enforces all domain policies:
    - Validates enum values
    - Enforces 72-hour priority rule
    - Re-extracts money/date if Gemini missed them
    - Enforces null discipline
    """
    result = state.get("gemini_result") or {}
    email = state["email"]

    # If Gemini says skip (OOO/spam it caught that regex missed)
    if result.get("decision") == "skipped":
        return {
            "skip": True,
            "skipped_reason": result.get("skipped_reason"),
            "spam_lookalike_category": result.get("spam_lookalike_category"),
            "decision": "skipped",
        }

    assignee_id, category = validate_routing(
        result.get("assignee_id"),
        result.get("category"),
    )

    # Money: trust Gemini, but run parser as fallback
    deal_value = state.get("deal_value_inr")
    if deal_value is None:
        deal_value = result.get("deal_value_inr")
    if deal_value == "":
        deal_value = None
    if deal_value is not None:
        try:
            deal_value = int(deal_value)
        except ValueError:
            deal_value = None
    if deal_value is None and category not in ("finance", "triage", "alliances"):
        deal_value = parse_inr(email.get("body", ""))

    # Finance / Alliances emails: never set deal_value_inr
    if category in ("finance", "alliances"):
        deal_value = None
    elif category == "triage" and (result.get("deal_value_inr") is None or result.get("deal_value_inr") == ""):
        deal_value = None

    # Date: trust Gemini, but run parser as fallback
    due_date = state.get("due_date")
    if due_date is None:
        due_date = result.get("due_date")
    if due_date == "":
        due_date = None
    if due_date is None and category not in ("alliances", "smb_enquiry"):
        due_date = parse_due_date(email.get("body", ""), email.get("received_at", ""))

    # Finance emails: due_date is None unless explicit invoice deadline
    if category == "finance" and not result.get("due_date"):
        due_date = None

    priority = compute_priority(
        result.get("priority", "medium"),
        due_date,
        email.get("received_at", ""),
        category,
        result.get("routing_reason", ""),
    )

    confidence = float(result.get("confidence", 0.5))
    confidence = max(0.0, min(1.0, confidence))
    
    needs_update = (
        bool(result.get("needs_update", False))
        or bool(email.get("is_reply", False))
        or int(email.get("message_index", 0)) > 0
    )

    logger.info(
        f"[route] {email['email_id']} -> {assignee_id} / {category} / {priority} "
        f"conf={confidence:.2f} needs_update={needs_update}"
    )

    company_name = result.get("company_name")
    if company_name == "":
        company_name = None

    return {
        "assignee_id": assignee_id,
        "category": category,
        "priority": priority,
        "due_date": due_date,
        "deal_value_inr": deal_value,
        "company_name": company_name,
        "title": result.get("title") or f"Email from {email.get('from_name', 'unknown')}",
        "description": result.get("description"),
        "confidence": confidence,
        "routing_reason": result.get("routing_reason", ""),
        "needs_update": needs_update,
    }
