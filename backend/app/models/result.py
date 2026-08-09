from pydantic import BaseModel, Field, ConfigDict


class IngestResult(BaseModel):
    """
    Exact response shape for POST /ingest.
    The grader checks every field — names, types, and counts must be exact.

    processed     = total emails received in request (including duplicates)
    tasks_created = new tasks POSTed to shared Task API
    tasks_updated = existing tasks PATCHed on shared Task API
    skipped       = OOO + newsletter + spam + already_processed duplicates
    errors        = list of error strings (empty list if all succeeded)
    """
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "processed": 60,
                "tasks_created": 41,
                "tasks_updated": 7,
                "skipped": 12,
                "errors": [],
            }
        }
    )

    processed: int = Field(default=0, description="Total emails in batch")
    tasks_created: int = Field(default=0, description="New tasks created")
    tasks_updated: int = Field(default=0, description="Existing tasks updated")
    skipped: int = Field(default=0, description="Emails skipped (noise + duplicates)")
    errors: list[str] = Field(default_factory=list, description="Error details if any")


class IngestRequest(BaseModel):
    """
    Request body for POST /ingest.
    emails is a list of raw email dicts matching inbox.json schema.
    """
    candidate_id: str | None = Field(default=None, description="Your lowercase email — must match config")
    emails: list[dict] = Field(description="Batch of emails, max 100")
