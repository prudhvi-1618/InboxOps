import aiosqlite
from app.infrastructure.database.repository import EmailDecisionRepository
from app.infrastructure.task_api.client import TaskAPIClient
from app.core.logging import get_logger

logger = get_logger(__name__)

_task_client = TaskAPIClient()


async def resolve_thread_action(
    thread_id: str,
    db: aiosqlite.Connection,
) -> tuple[str | None, bool]:
    """
    Determines whether to POST (new task) or PATCH (existing task).

    Returns:
        (existing_task_id, needs_update)
        - (None, False)      → POST a new task
        - ("tsk_xxx", True)  → PATCH existing task
    """
    repo = EmailDecisionRepository(db)
    existing_task_id = await repo.get_task_id_by_thread(thread_id)

    if existing_task_id:
        logger.debug(f"[thread_service] thread {thread_id} → existing task {existing_task_id}")
        return existing_task_id, True

    logger.debug(f"[thread_service] thread {thread_id} → no existing task, will POST")
    return None, False


async def build_patch_payload(state: dict) -> dict:
    """
    Builds the PATCH payload from graph state.
    Only includes fields that are non-None and actually changed.
    Never patches candidate_id, source_email_id, thread_id — those are immutable.

    Fields eligible for patch:
        title, description, assignee_id, category,
        priority, due_date, deal_value_inr, company_name, confidence
    """
    patchable = [
        "title", "description", "assignee_id", "category",
        "priority", "due_date", "deal_value_inr", "company_name", "confidence",
    ]
    payload = {}
    for field in patchable:
        val = state.get(field)
        if val is not None:
            payload[field] = val

    return payload


async def patch_existing_task(task_id: str, state: dict) -> dict:
    """
    Builds patch payload from state and calls Task API PATCH.
    Returns the Task API response dict.
    Raises TaskAPIError on failure — caller handles it.
    """
    payload = await build_patch_payload(state)
    if not payload:
        logger.warning(f"[thread_service] PATCH {task_id} called with empty payload — skipping")
        return {"task_id": task_id, "skipped_patch": True}

    logger.info(f"[thread_service] PATCH {task_id} fields={list(payload.keys())}")
    result = await _task_client.update_task(task_id, payload)
    return result


async def post_new_task(email: dict, state: dict, candidate_id: str) -> dict:
    """
    Builds POST payload from email + state and calls Task API POST.
    Returns the Task API response dict containing task_id.
    Raises TaskAPIError on failure — caller handles it.
    """
    payload = {
        "candidate_id": candidate_id,
        "source_email_id": email["email_id"],
        "thread_id": email["thread_id"],
        "title": state.get("title") or f"Email: {email.get('subject', '')}",
        "description": state.get("description"),
        "assignee_id": state["assignee_id"],
        "category": state["category"],
        "priority": state["priority"],
        "due_date": state.get("due_date"),
        "deal_value_inr": state.get("deal_value_inr"),
        "company_name": state.get("company_name"),
        "confidence": state.get("confidence", 0.5),
    }

    logger.info(
        f"[thread_service] POST new task for {email['email_id']} "
        f"-> {state['assignee_id']} / {state['category']}"
    )
    result = await _task_client.create_task(payload)
    return result
