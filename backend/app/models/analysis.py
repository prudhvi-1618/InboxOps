from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field


class EmailCategory(str, Enum):
    DEMO_REQUEST = "demo_request"
    PRICING_INQUIRY = "pricing_inquiry"
    CONTRACT_RENEWAL = "contract_renewal"
    TECHNICAL_SUPPORT = "technical_support"
    PARTNERSHIP = "partnership"
    GENERAL_INQUIRY = "general_inquiry"
    SPAM = "spam"
    NEWSLETTER = "newsletter"
    OUT_OF_OFFICE = "out_of_office"


class HygieneCategory(str, Enum):
    ACTIONABLE = "actionable"
    SPAM = "spam"
    NEWSLETTER = "newsletter"
    OUT_OF_OFFICE = "out_of_office"
    AUTO_REPLY = "auto_reply"


class EmailAnalysis(BaseModel):
    is_actionable: bool = Field(..., description="Whether this email requires task creation")
    hygiene_category: HygieneCategory = Field(default=HygieneCategory.ACTIONABLE)
    category: Optional[EmailCategory] = Field(default=None)
    sentiment: str = Field(default="neutral", description="positive, neutral, negative, urgent")
    confidence: float = Field(default=0.95, ge=0.0, le=1.0)
    company_name: Optional[str] = Field(default=None)
    deal_value_raw: Optional[str] = Field(default=None)
    deal_value_inr: Optional[int] = Field(default=None)
    urgency_deadline_raw: Optional[str] = Field(default=None)
    due_date: Optional[str] = Field(default=None)
    suggested_assignee: Optional[str] = Field(default=None)
    routing_reason: Optional[str] = Field(default=None)
    summary: str = Field(default="")
