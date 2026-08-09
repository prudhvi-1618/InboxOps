from fastapi import APIRouter, Depends, HTTPException
import aiosqlite
from app.models.result import IngestRequest, IngestResult
from app.services.ingestion import process_batch
from app.infrastructure.database.connection import get_db
from app.core.config import get_settings
from app.core.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)
settings = get_settings()


@router.post(
    "/ingest",
    response_model=IngestResult,
    summary="Classify and route a batch of emails",
    response_description="Summary of processing results",
)
async def ingest(
    request: IngestRequest,
    db: aiosqlite.Connection = Depends(get_db),
):
    # ── Validate candidate_id ─────────────────────────────────────────────────
    request_candidate_id = request.candidate_id or settings.candidate_id_normalized
    if request_candidate_id.lower().strip() != settings.candidate_id_normalized:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "invalid_candidate_id",
                "received": request_candidate_id,
                "expected": settings.candidate_id_normalized,
            },
        )
    # Ensure it's set for processing
    request.candidate_id = request_candidate_id

    # ── Validate batch size ───────────────────────────────────────────────────
    if not request.emails:
        raise HTTPException(
            status_code=400,
            detail={"error": "emails must be a non-empty array"},
        )

    if len(request.emails) > 100:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "batch_too_large",
                "received": len(request.emails),
                "limit": 100,
            },
        )

    # ── Validate each email has required fields ───────────────────────────────
    for i, email in enumerate(request.emails):
        if not email.get("email_id"):
            raise HTTPException(
                status_code=400,
                detail={"error": f"email at index {i} missing email_id"},
            )
        if not email.get("thread_id"):
            raise HTTPException(
                status_code=400,
                detail={"error": f"email at index {i} missing thread_id"},
            )

    logger.info(
        f"[ingest] Received batch of {len(request.emails)} emails "
        f"from candidate {request.candidate_id}"
    )

    # ── Process — synchronous, returns only after ALL writes complete ─────────
    result = await process_batch(request.emails, request.candidate_id, db)
    return result
