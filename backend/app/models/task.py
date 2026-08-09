from pydantic import BaseModel, Field
from typing import Optional, Literal


AssigneeID = Literal["u_aarti", "u_rohit", "u_meera", "u_karan", "u_divya", "u_triage"]
Category = Literal["enterprise_rfp", "smb_enquiry", "marketing", "alliances", "finance", "triage"]
Priority = Literal["high", "medium", "low"]


class TaskCreate(BaseModel):
    candidate_id: str
    source_email_id: str
    thread_id: str
    title: str
    description: Optional[str] = None
    assignee_id: AssigneeID
    category: Category
    priority: Priority
    due_date: Optional[str] = None       # YYYY-MM-DD or null
    deal_value_inr: Optional[int] = None # integer rupees or null
    company_name: Optional[str] = None
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)


class TaskPatch(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    assignee_id: Optional[AssigneeID] = None
    category: Optional[Category] = None
    priority: Optional[Priority] = None
    due_date: Optional[str] = None
    deal_value_inr: Optional[int] = None
    company_name: Optional[str] = None
    confidence: Optional[float] = None


class TaskResponse(BaseModel):
    task_id: str
    candidate_id: str
    source_email_id: str
    thread_id: str
    title: str
    description: Optional[str] = None
    assignee_id: str
    category: str
    priority: str
    due_date: Optional[str] = None
    deal_value_inr: Optional[int] = None
    company_name: Optional[str] = None
    confidence: float = 0.5
    created_at: str
    updated_at: Optional[str] = None
