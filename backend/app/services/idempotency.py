import aiosqlite
from app.infrastructure.database.repository import EmailDecisionRepository
from app.core.logging import get_logger

logger = get_logger(__name__)


async def check_and_resolve(
    email_id: str,
    thread_id: str,
    is_reply: bool,
    message_index: int,
    db: aiosqlite.Connection,
) -> dict:
    """
    Single entry point called BEFORE the LangGraph graph runs.
    Resolves three cases:

    Case 1 — Exact duplicate:
        email_id already exists in email_decisions
        → already_processed=True, return immediately
        → caller skips graph entirely, skips Task API write
        → this is what makes Run 2 idempotent

    Case 2 — Reply on known thread:
        email_id is new BUT thread_id has an existing task_created record
        AND (is_reply=True OR message_index > 0)
        → needs_update=True, existing_task_id=<that task_id>
        → caller runs graph but task_writer does PATCH not POST

    Case 3 — Fresh email, no thread match:
        → normal processing, POST a new task

    CRITICAL: This check uses INSERT OR IGNORE in the repository.
    Even if two concurrent requests for the same email_id race here,
    only one will succeed — the DB PRIMARY KEY constraint is the
    final guard, not application logic alone.
    """
    repo = EmailDecisionRepository(db)

    # ── Case 1: exact duplicate ───────────────────────────────────────────────
    existing = await repo.get_by_email_id(email_id)
    if existing:
        logger.info(
            f"[idempotency] DUPLICATE {email_id} "
            f"(previously: {existing.get('decision')}) — skipping"
        )
        return {
            "already_processed": True,
            "needs_update": False,
            "existing_task_id": existing.get("task_id"),
            "decision": existing.get("decision"),
        }

    # ── Case 2: reply on existing thread ─────────────────────────────────────
    existing_task_id = None
    needs_update = False

    if is_reply or message_index > 0:
        existing_task_id = await repo.get_task_id_by_thread(thread_id)
        if existing_task_id:
            needs_update = True
            logger.info(
                f"[idempotency] REPLY detected {email_id} "
                f"on thread {thread_id} -> will PATCH {existing_task_id}"
            )
        else:
            # is_reply=True but no task exists for thread yet
            # (e.g. original email was skipped as spam)
            # Treat as fresh — POST a new task
            logger.info(
                f"[idempotency] REPLY {email_id} on thread {thread_id} "
                f"but no existing task found — treating as fresh"
            )

    # ── Case 3: fresh email ───────────────────────────────────────────────────
    return {
        "already_processed": False,
        "needs_update": needs_update,
        "existing_task_id": existing_task_id,
    }
