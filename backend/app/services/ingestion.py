import asyncio
import uuid
from datetime import datetime, timezone
import aiosqlite
from app.graph.workflow import email_graph
from app.graph.state import EmailProcessingState
from app.infrastructure.database.repository import EmailDecisionRepository
from app.services.idempotency import check_and_resolve
from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.result import IngestResult

logger = get_logger(__name__)
settings = get_settings()


def _build_initial_state(
    email: dict,
    candidate_id: str,
    run_id: str,
    idempotency: dict,
) -> EmailProcessingState:
    """
    Builds the complete initial LangGraph state for one email.
    All keys must be present — LangGraph raises if any TypedDict key is missing.
    """
    return {
        "email": email,
        "candidate_id": candidate_id,
        "run_id": run_id,

        # Hygiene
        "skip": False,
        "skipped_reason": None,
        "spam_lookalike_category": None,

        # Idempotency — injected from check_and_resolve
        "already_processed": idempotency["already_processed"],
        "existing_task_id": idempotency.get("existing_task_id"),
        "needs_update": idempotency.get("needs_update", False),

        # Gemini output
        "gemini_result": None,
        "gemini_error": None,

        # Resolved routing fields
        "assignee_id": None,
        "category": None,
        "priority": None,
        "due_date": None,
        "deal_value_inr": None,
        "company_name": None,
        "title": None,
        "description": None,
        "confidence": 0.5,
        "routing_reason": None,

        # Task API result
        "task_id": None,
        "decision": idempotency.get("decision"),
        "error_message": None,
    }


async def _process_single_email(
    email: dict,
    candidate_id: str,
    run_id: str,
    db: aiosqlite.Connection,
) -> dict:
    """
    Full pipeline for one email:
      1. Idempotency check  → skip if duplicate
      2. LangGraph run      → classify, route, write to Task API
      3. Persist decision   → store in local DB for chat grounding
      4. Record thread      → track update history

    NEVER raises. All errors are caught, logged, and persisted as decision='error'.
    A logged error is always better than a crashed /ingest.
    """
    email_id = email.get("email_id", "unknown")
    thread_id = email.get("thread_id", "")
    is_reply = email.get("is_reply", False)
    message_index = email.get("message_index", 0)
    repo = EmailDecisionRepository(db)

    try:
        # ── Step 1: Idempotency ───────────────────────────────────────────────
        idempotency = await check_and_resolve(
            email_id, thread_id, is_reply, message_index, db
        )

        if idempotency["already_processed"]:
            logger.info(f"[ingestion] SKIP (duplicate) {email_id}")
            return {"decision": "skipped", "reason": "already_processed"}

        # ── Step 2: LangGraph pipeline ────────────────────────────────────────
        initial_state = _build_initial_state(email, candidate_id, run_id, idempotency)
        final_state = await email_graph.ainvoke(initial_state)
        decision = final_state.get("decision") or "error"

        # ── Step 3: Persist decision to local DB ──────────────────────────────
        decision_record = {
            "email_id": email_id,
            "thread_id": thread_id,
            "run_id": run_id,
            "decision": decision,
            "category": final_state.get("category"),
            "assignee_id": final_state.get("assignee_id"),
            "task_id": final_state.get("task_id"),
            "priority": final_state.get("priority"),
            "confidence": final_state.get("confidence"),
            "skipped_reason": final_state.get("skipped_reason"),
            "spam_lookalike_category": final_state.get("spam_lookalike_category"),
            "deal_value_inr": final_state.get("deal_value_inr"),
            "company_name": final_state.get("company_name"),
            "due_date": final_state.get("due_date"),
            "routing_reason": final_state.get("routing_reason"),
            "raw_subject": email.get("subject"),
            "raw_from_email": email.get("from_email"),
            "raw_from_name": email.get("from_name"),
            "received_at": email.get("received_at"),
        }
        await repo.insert_decision(decision_record)

        # ── Step 4: Record thread update history ──────────────────────────────
        if decision in ("task_created", "task_updated") and final_state.get("task_id"):
            action = "created" if decision == "task_created" else "updated"
            await repo.insert_thread_update(
                thread_id,
                email_id,
                final_state["task_id"],
                action,
            )

        logger.info(
            f"[ingestion] {email_id} -> {decision} "
            f"assignee={final_state.get('assignee_id')} "
            f"task={final_state.get('task_id')}"
        )
        return {"decision": decision}

    except Exception as e:
        # Catch-all — never let one bad email crash the batch
        logger.error(f"[ingestion] UNHANDLED ERROR for {email_id}: {e}", exc_info=True)

        # Best-effort persist of error record
        try:
            await repo.insert_decision({
                "email_id": email_id,
                "thread_id": thread_id,
                "run_id": run_id,
                "decision": "error",
                "raw_subject": email.get("subject"),
                "raw_from_email": email.get("from_email"),
                "raw_from_name": email.get("from_name"),
                "received_at": email.get("received_at"),
            })
        except Exception as persist_err:
            logger.error(f"[ingestion] Failed to persist error for {email_id}: {persist_err}")

        return {"decision": "error", "error_message": str(e), "email_id": email_id}


async def process_batch(
    emails: list[dict],
    candidate_id: str,
    db: aiosqlite.Connection,
) -> IngestResult:
    """
    Processes a batch of up to 100 emails.

    Architecture:
    - Splits emails into sub-batches of gemini_batch_size (default 10)
    - Within each sub-batch: concurrent asyncio.gather
    - Between sub-batches: gemini_batch_delay_sec pause (rate limit compliance)
    - SYNCHRONOUS from the caller's perspective:
        Returns IngestResult only AFTER every email is written to Task API and DB
    - /ingest endpoint returns 200 only when this function returns

    This guarantees Run 2 idempotency:
        If the grader posts the same batch again before we return 200,
        it cannot start until we are done — no race condition possible.
    """
    run_id = str(uuid.uuid4())
    started_at = datetime.now(timezone.utc).isoformat()

    logger.info(
        f"[ingestion] Starting run {run_id} "
        f"with {len(emails)} emails "
        f"batch_size={settings.gemini_batch_size}"
    )

    # Persist run record
    repo = EmailDecisionRepository(db)
    try:
        await db.execute(
            """INSERT OR IGNORE INTO runs
               (run_id, started_at, email_count)
               VALUES (?, ?, ?)""",
            (run_id, started_at, len(emails)),
        )
        await db.commit()
    except Exception as e:
        logger.warning(f"[ingestion] Could not persist run record: {e}")

    # ── Process in rate-limited sub-batches ───────────────────────────────────
    all_results: list[dict] = []
    batch_size = settings.gemini_batch_size
    delay = settings.gemini_batch_delay_sec

    for i in range(0, len(emails), batch_size):
        sub_batch = emails[i: i + batch_size]
        batch_num = (i // batch_size) + 1
        total_batches = (len(emails) + batch_size - 1) // batch_size

        logger.info(
            f"[ingestion] Sub-batch {batch_num}/{total_batches} "
            f"({len(sub_batch)} emails)"
        )

        # Concurrent within sub-batch
        tasks = [
            _process_single_email(email, candidate_id, run_id, db)
            for email in sub_batch
        ]
        results = await asyncio.gather(*tasks, return_exceptions=False)
        all_results.extend(results)

        # Rate limit pause — only between batches, not after the last one
        if i + batch_size < len(emails):
            logger.debug(f"[ingestion] Rate limit pause {delay}s")
            await asyncio.sleep(delay)

    # ── Tally results ─────────────────────────────────────────────────────────
    counts = {
        "task_created": 0,
        "task_updated": 0,
        "skipped": 0,
        "error": 0,
    }
    error_messages: list[str] = []

    for r in all_results:
        decision = r.get("decision", "error")
        if decision in counts:
            counts[decision] += 1
        else:
            counts["skipped"] += 1  # already_processed counts as skipped

        if decision == "error" and r.get("error_message"):
            error_messages.append(
                f"{r.get('email_id', 'unknown')}: {r['error_message']}"
            )

    # ── Update run record with final counts ───────────────────────────────────
    finished_at = datetime.now(timezone.utc).isoformat()
    try:
        await db.execute(
            """UPDATE runs SET
               finished_at=?, created=?, updated=?, skipped=?, errors=?
               WHERE run_id=?""",
            (
                finished_at,
                counts["task_created"],
                counts["task_updated"],
                counts["skipped"],
                counts["error"],
                run_id,
            ),
        )
        await db.commit()
    except Exception as e:
        logger.warning(f"[ingestion] Could not update run record: {e}")

    result = IngestResult(
        processed=len(emails),
        tasks_created=counts["task_created"],
        tasks_updated=counts["task_updated"],
        skipped=counts["skipped"],
        errors=error_messages,
    )

    logger.info(f"[ingestion] Run {run_id} complete: {result}")
    return result
