from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
import aiosqlite
import httpx
from app.core.config import get_settings
from app.infrastructure.database.connection import get_db
from app.infrastructure.database.repository import EmailDecisionRepository
from app.api.dependencies import get_repository
from app.models.task import TaskCreate, TaskPatch, TaskResponse
from app.core.logging import get_logger

router = APIRouter(tags=["Tasks"])
logger = get_logger(__name__)
settings = get_settings()


@router.get("/api/tasks")
async def list_enriched_tasks(
    thread_id: str = Query(None),
    assignee_id: str = Query(None),
    source_email_id: str = Query(None),
    db: aiosqlite.Connection = Depends(get_db),
):
    """
    Proxies GET /tasks from the shared Task API and joins with
    local DB metadata (routing_reason, confidence, skipped_reason,
    spam_lookalike_category) that the Task API does not store.

    This enriched response is what the chat interface reads —
    it needs routing_reason to answer "show me triage and why".

    Query params forwarded to Task API:
        thread_id, assignee_id, source_email_id
    All scoped to candidate_id automatically — never leaks other candidates.
    """
    # ── Step 1: fetch from shared Task API (or fallback to local DB) ────────
    params = {"candidate_id": settings.candidate_id_normalized}
    if thread_id:
        params["thread_id"] = thread_id
    if assignee_id:
        params["assignee_id"] = assignee_id
    if source_email_id:
        params["source_email_id"] = source_email_id

    repo = EmailDecisionRepository(db)
    upstream_tasks: list[dict] = []
    try:
        async with httpx.AsyncClient(timeout=settings.task_api_timeout_sec) as client:
            resp = await client.get(
                f"{settings.task_api_base_url.rstrip('/')}/tasks",
                params=params,
            )
        resp.raise_for_status()
        upstream_tasks = resp.json()
    except httpx.HTTPStatusError as e:
        logger.error(f"[tasks] Task API returned {e.response.status_code}: {e.response.text}")
        return {"error": "task_api_error", "detail": str(e), "tasks": []}
    except httpx.RequestError as e:
        logger.debug(f"[tasks] Task API unreachable over HTTP ({e}), fetching from local DB")
        filters = {}
        if thread_id:
            filters["thread_id"] = thread_id
        if assignee_id:
            filters["assignee_id"] = assignee_id
        if source_email_id:
            filters["source_email_id"] = source_email_id
        upstream_tasks = await repo.list_tasks(filters)

    if not upstream_tasks:
        return {"tasks": [], "total": 0}

    # ── Step 2: enrich with local DB metadata ────────────────────────────────
    all_decisions = await repo.get_all_for_chat()

    # Build lookup: source_email_id -> local decision record
    decision_map: dict[str, dict] = {
        d["email_id"]: d for d in all_decisions
    }

    enriched = []
    for task in upstream_tasks:
        email_id = task.get("source_email_id", "")
        local = decision_map.get(email_id, {})
        enriched.append({
            **task,
            # Fields from local DB not present in Task API response
            "routing_reason": local.get("routing_reason"),
            "confidence": local.get("confidence"),
            "skipped_reason": local.get("skipped_reason"),
            "spam_lookalike_category": local.get("spam_lookalike_category"),
            "raw_subject": local.get("raw_subject"),
            "raw_from_name": local.get("raw_from_name"),
            "raw_from_email": local.get("raw_from_email"),
        })

    logger.info(f"[tasks] Returning {len(enriched)} tasks (enriched with local metadata)")
    return {"tasks": enriched, "total": len(enriched)}


# ── Task API CRUD endpoints (exposed directly on the backend) ─────────────────

@router.post("/tasks", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    payload: TaskCreate,
    repo: EmailDecisionRepository = Depends(get_repository),
):
    """
    Creates a new task in the Task API.
    """
    task_dict = await repo.create_task(payload.model_dump())
    return task_dict


@router.patch("/tasks/{task_id}", response_model=TaskResponse)
async def patch_task(
    task_id: str,
    payload: TaskPatch,
    repo: EmailDecisionRepository = Depends(get_repository),
):
    """
    Updates an existing task in the Task API.
    """
    updated = await repo.update_task(task_id, payload.model_dump(exclude_unset=True))
    if not updated:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    return updated


@router.get("/tasks", response_model=List[TaskResponse])
async def list_tasks(
    candidate_id: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    assignee_id: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    repo: EmailDecisionRepository = Depends(get_repository),
):
    """
    Lists tasks from the Task API with optional filtering.
    """
    filters = {}
    if candidate_id:
        filters["candidate_id"] = candidate_id
    if category:
        filters["category"] = category
    if assignee_id:
        filters["assignee_id"] = assignee_id
    if priority:
        filters["priority"] = priority

    return await repo.list_tasks(filters)


@router.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task_by_id(
    task_id: str,
    repo: EmailDecisionRepository = Depends(get_repository),
):
    """
    Retrieves a single task by ID.
    """
    task = await repo.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    return task


@router.get("/tasks-decisions")
async def list_email_decisions(
    repo: EmailDecisionRepository = Depends(get_repository),
):
    """
    Returns full decision list for debugging and analytics.
    """
    decisions = await repo.get_all_for_chat()
    return {"decisions": decisions}
