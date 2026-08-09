from .email import InboundEmail
from .result import IngestRequest, IngestResult
from .task import TaskCreate, TaskPatch, TaskResponse
from .analysis import EmailAnalysis, EmailCategory, HygieneCategory

__all__ = [
    "InboundEmail",
    "IngestRequest",
    "IngestResult",
    "TaskCreate",
    "TaskPatch",
    "TaskResponse",
    "EmailAnalysis",
    "EmailCategory",
    "HygieneCategory",
]
