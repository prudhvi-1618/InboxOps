from app.graph.state import EmailProcessingState
from app.domain.policies.priority import compute_priority
from app.core.logging import get_logger

logger = get_logger(__name__)


def priority_node(state: EmailProcessingState) -> dict:
    """
    Refines priority based on 72-hour deadline calculation and overdue conditions.
    """
    gemini_result = state.get("gemini_result") or {}
    email = state.get("email") or {}
    category = state.get("category") or gemini_result.get("category", "triage")
    due_date = state.get("due_date") or gemini_result.get("due_date")
    routing_reason = state.get("routing_reason") or gemini_result.get("routing_reason", "")
    current_priority = state.get("priority") or gemini_result.get("priority", "medium")

    priority = compute_priority(
        current_priority,
        due_date,
        email.get("received_at", ""),
        category,
        routing_reason,
    )
    return {"priority": priority}
