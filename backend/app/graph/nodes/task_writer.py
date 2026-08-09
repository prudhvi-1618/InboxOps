from app.graph.state import EmailProcessingState
from app.domain.services.thread_service import patch_existing_task, post_new_task
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


async def task_writer_node(state: EmailProcessingState) -> dict:
    """
    Final LangGraph node.
    Delegates entirely to thread_service — no Task API calls here directly.

    - needs_update=True + existing_task_id → PATCH
    - otherwise → POST
    """
    email = state["email"]
    candidate_id = settings.candidate_id_normalized

    try:
        if state.get("needs_update") and state.get("existing_task_id"):
            result = await patch_existing_task(
                state["existing_task_id"], dict(state)
            )
            task_id = state["existing_task_id"]
            logger.info(f"[task_writer] PATCH complete → {task_id}")
            return {"task_id": task_id, "decision": "task_updated"}

        result = await post_new_task(email, dict(state), candidate_id)
        task_id = result["task_id"]
        logger.info(f"[task_writer] POST complete → {task_id}")
        return {"task_id": task_id, "decision": "task_created"}

    except Exception as e:
        logger.error(f"[task_writer] Failed for {email.get('email_id')}: {e}")
        return {"decision": "error", "error_message": str(e)}
