from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from ...infrastructure.database.repository import InboxRepository
from ..dependencies import get_db_session

router = APIRouter(prefix="/api/runs", tags=["Runs"])


@router.get("/")
async def list_runs(
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db_session),
):
    repo = InboxRepository(db)
    return await repo.get_recent_runs(limit=limit)


@router.get("/stats")
async def get_stats(
    db: AsyncSession = Depends(get_db_session),
):
    repo = InboxRepository(db)
    return await repo.get_aggregate_stats()


@router.get("/{run_id}")
async def get_run_details(
    run_id: str,
    db: AsyncSession = Depends(get_db_session),
):
    repo = InboxRepository(db)
    run = await repo.get_run_by_id(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    decisions = await repo.get_decisions_for_run(run_id)
    return {"run": run, "decisions": decisions}
