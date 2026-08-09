from app.graph.state import EmailProcessingState
from app.domain.services.money_parser import parse_inr
from app.domain.services.date_parser import parse_due_date
from app.core.logging import get_logger

logger = get_logger(__name__)


def extract_node(state: EmailProcessingState) -> dict:
    """
    Extracts entities or fills in fallbacks for deal_value_inr and due_date using domain parsers.
    """
    email = state.get("email", {})
    gemini_result = state.get("gemini_result") or {}
    category = gemini_result.get("category") or state.get("category")

    deal_value = gemini_result.get("deal_value_inr")
    if deal_value is None and category not in ("finance", "triage", "alliances"):
        deal_value = parse_inr(email.get("body", ""))

    if category in ("finance", "alliances"):
        deal_value = None

    due_date = gemini_result.get("due_date")
    if due_date is None and category not in ("alliances", "smb_enquiry"):
        due_date = parse_due_date(email.get("body", ""), email.get("received_at", ""))

    return {
        "deal_value_inr": deal_value,
        "due_date": due_date,
    }
