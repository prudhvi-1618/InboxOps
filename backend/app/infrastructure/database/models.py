from typing import Optional, Literal
from pydantic import BaseModel, Field


DecisionType = Literal["task_created", "task_updated", "skipped", "error"]


class EmailDecision(BaseModel):
    email_id: str
    thread_id: str
    run_id: Optional[str] = None
    decision: DecisionType
    category: Optional[str] = None
    assignee_id: Optional[str] = None
    task_id: Optional[str] = None
    priority: Optional[str] = None
    confidence: Optional[float] = None
    skipped_reason: Optional[str] = None
    spam_lookalike_category: Optional[str] = None
    deal_value_inr: Optional[int] = None
    company_name: Optional[str] = None
    due_date: Optional[str] = None
    routing_reason: Optional[str] = None
    raw_subject: Optional[str] = None
    raw_from_email: Optional[str] = None
    raw_from_name: Optional[str] = None
    received_at: Optional[str] = None
    processed_at: Optional[str] = None


class RunRecord(BaseModel):
    run_id: str
    started_at: str
    finished_at: Optional[str] = None
    email_count: int = 0
    created: int = 0
    updated: int = 0
    skipped: int = 0
    errors: int = 0


class ThreadUpdateRecord(BaseModel):
    id: Optional[int] = None
    thread_id: str
    email_id: str
    task_id: str
    action: Literal["created", "updated"]
    updated_at: Optional[str] = None
