from typing import Optional, List
from pydantic import BaseModel, Field


class GeminiExtractionSchema(BaseModel):
    is_actionable: bool = Field(description="True if email requires human task creation, False if spam/newsletter/ooo")
    category: str = Field(description="demo_request, pricing_inquiry, contract_renewal, technical_support, partnership, general_inquiry, spam, newsletter, out_of_office")
    sentiment: str = Field(default="neutral", description="positive, neutral, negative, urgent")
    confidence: float = Field(default=0.95, description="Confidence score between 0.0 and 1.0")
    company_name: Optional[str] = Field(default=None, description="Prospect/customer company name")
    deal_value_raw: Optional[str] = Field(default=None, description="Raw currency string if mentioned")
    urgency_deadline_raw: Optional[str] = Field(default=None, description="Raw deadline or timeframe if mentioned")
    suggested_assignee: Optional[str] = Field(default=None, description="Suggested rep: aarti, rohit, meera, ananya")
    summary: str = Field(default="", description="1-2 sentence executive summary of the email")
