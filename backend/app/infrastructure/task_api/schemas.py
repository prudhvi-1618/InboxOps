from typing import Optional
from pydantic import BaseModel


class TaskApiResponse(BaseModel):
    id: str
    status: str
    message: Optional[str] = None
