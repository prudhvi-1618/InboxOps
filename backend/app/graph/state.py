from typing import Optional, Any
from typing_extensions import TypedDict
from app.models.email import InboundEmail


class EmailProcessingState(TypedDict):
    # Input
    email: dict                         # raw InboundEmail dict
    candidate_id: str
    run_id: str

    # Hygiene stage
    skip: bool
    skipped_reason: Optional[str]       # "ooo" | "newsletter" | "spam" | None
    spam_lookalike_category: Optional[str]

    # Idempotency stage
    already_processed: bool
    existing_task_id: Optional[str]     # task_id from DB if thread already has one
    needs_update: bool                  # true if is_reply and task exists

    # Gemini classification output
    gemini_result: Optional[dict]
    gemini_error: Optional[str]

    # Resolved fields (after policy enforcement)
    assignee_id: Optional[str]
    category: Optional[str]
    priority: Optional[str]
    due_date: Optional[str]
    deal_value_inr: Optional[int]
    company_name: Optional[str]
    title: Optional[str]
    description: Optional[str]
    confidence: float
    routing_reason: Optional[str]

    # Task API result
    task_id: Optional[str]
    decision: Optional[str]             # "task_created" | "task_updated" | "skipped" | "error"
    error_message: Optional[str]
