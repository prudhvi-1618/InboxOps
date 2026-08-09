from fastapi import Request
from fastapi.responses import JSONResponse


class InboxOpsException(Exception):
    """Base exception for InboxOps application."""
    def __init__(self, message: str = "An InboxOps error occurred", status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class TaskAPIError(InboxOpsException):
    def __init__(self, status_code: int, detail: str):
        super().__init__(message=detail, status_code=status_code)
        self.detail = detail


class GeminiError(InboxOpsException):
    def __init__(self, detail: str = "Gemini AI processing error"):
        super().__init__(message=detail, status_code=503)


class IdempotencyError(InboxOpsException):
    def __init__(self, detail: str = "Idempotency conflict"):
        super().__init__(message=detail, status_code=409)


class DatabaseError(InboxOpsException):
    def __init__(self, detail: str = "Database operation error"):
        super().__init__(message=detail, status_code=500)


class EmailValidationError(InboxOpsException):
    def __init__(self, detail: str = "Invalid email payload"):
        super().__init__(message=detail, status_code=422)


async def task_api_error_handler(request: Request, exc: TaskAPIError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": "task_api_error", "detail": exc.message},
    )


async def gemini_error_handler(request: Request, exc: GeminiError) -> JSONResponse:
    return JSONResponse(
        status_code=503,
        content={"error": "gemini_unavailable", "detail": exc.message},
    )
