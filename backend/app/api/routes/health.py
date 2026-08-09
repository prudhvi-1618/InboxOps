from datetime import datetime, timezone
from fastapi import APIRouter
from app.core.config import get_settings

router = APIRouter(tags=["Health"])
settings = get_settings()


@router.get("/")
@router.get("/health")
async def health_check():
    return {
        "status": "ok",
        "candidate_id": settings.candidate_id_normalized,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "environment": settings.environment,
    }
