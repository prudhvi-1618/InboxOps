from typing import Optional


VALID_ASSIGNEES = {"u_aarti", "u_rohit", "u_meera", "u_karan", "u_divya", "u_triage"}
VALID_CATEGORIES = {"enterprise_rfp", "smb_enquiry", "marketing", "alliances", "finance", "triage"}


def validate_routing(assignee_id: Optional[str], category: Optional[str]) -> tuple[str, str]:
    """
    Ensures assignee_id and category are valid enums.
    Falls back to triage if Gemini returned something invalid.
    """
    if assignee_id not in VALID_ASSIGNEES:
        assignee_id = "u_triage"
    if category not in VALID_CATEGORIES:
        category = "triage"
    # Keep assignee/category consistent
    if assignee_id == "u_triage" and category != "triage":
        category = "triage"
    return assignee_id, category
