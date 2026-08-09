from pydantic import BaseModel, Field
from typing import Optional, List


class InboundEmail(BaseModel):
    email_id: str
    thread_id: str
    message_index: int = 0
    from_name: str = ""
    from_email: str = ""
    to: str = ""
    cc: list[str] = Field(default_factory=list)
    subject: str = ""
    body: str = ""
    received_at: str = ""
    attachments: list[str] = Field(default_factory=list)
    is_reply: bool = False
