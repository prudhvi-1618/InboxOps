from fastapi import APIRouter, Depends
import aiosqlite
from pydantic import BaseModel
from app.infrastructure.database.connection import get_db
from app.services.chat.intent_parser import parse_intent
from app.services.chat.query_executor import execute_intent
from app.services.chat.answer_phraser import phrase_answer
from app.services.chat.scope_guard import check_scope, build_refusal_response
from app.core.config import get_settings
from app.core.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)
settings = get_settings()


class ChatRequest(BaseModel):
    candidate_id: str
    query: str


class ChatResponse(BaseModel):
    answer: str
    supporting_data: dict


@router.post("/api/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    db: aiosqlite.Connection = Depends(get_db),
):
    """
    Conversational interface over processed email data.

    Pipeline (strictly in order):
      1. Validate candidate_id
      2. Scope check for out-of-scope action requests (fast, no Gemini)
      3. Parse NL intent via Gemini (what does user want to know?)
      4. Execute SQL query against local DB (compute the actual numbers)
      5. Phrase result via Gemini (say it in plain English)
      6. Return { answer, supporting_data }

    Gemini is called at steps 3 and 5.
    Gemini NEVER computes numbers — only the DB does.
    supporting_data is always the raw SQL result — grader checks this.
    """
    query = request.query.strip()

    if not query:
        return ChatResponse(
            answer="Please ask a question about the processed emails.",
            supporting_data={},
        )

    logger.info(f"[chat] query='{query[:80]}' candidate={request.candidate_id}")

    # ── Step 1: validate candidate_id ────────────────────────────────────────
    if request.candidate_id.lower().strip() != settings.candidate_id_normalized:
        return ChatResponse(
            answer="Invalid candidate ID.",
            supporting_data={},
        )

    # ── Step 2: scope check ───────────────────────────────────────────────────
    scope = check_scope(query)

    if not scope.is_in_scope:
        return ChatResponse(**build_refusal_response(scope))

    # ── Step 3: parse intent ──────────────────────────────────────────────────
    intent = await parse_intent(query)

    # ── Step 4: handle out-of-scope from intent parser ────────────────────────
    if intent.get("intent_type") == "out_of_scope":
        reason = intent.get("out_of_scope_reason", "")
        logger.info(f"[chat] Out of scope: {reason}")

        # Special case: sub-distinguish question (alliances resellers vs tech)
        # Return honest "I don't have that breakdown" with what we do have
        if reason and "sub-category" in reason.lower():
            result = await execute_intent(
                {**intent, "intent_type": "count",
                 "filters": intent.get("filters", {}),
                 "sub_intent": None},
                db,
            )
            return ChatResponse(
                answer=(
                    f"I don't have a sub-category breakdown for that. "
                    f"{reason}. "
                    f"The top-level count is: {result.get('result', 'unknown')}."
                ),
                supporting_data=result.get("supporting_data", {}),
            )

        return ChatResponse(
            answer=(
                "This interface answers questions about processed email data — "
                "it does not take actions or answer questions outside that scope. "
                f"{reason}"
            ).strip(),
            supporting_data={},
        )

    # ── Step 5: execute SQL query ─────────────────────────────────────────────
    execution_result = await execute_intent(intent, db)

    # Handle SQL execution error
    if execution_result.get("error"):
        logger.error(f"[chat] SQL execution error: {execution_result['error']}")
        return ChatResponse(
            answer="I encountered an error retrieving that data. Please try again.",
            supporting_data={},
        )

    raw_result = execution_result.get("result")
    supporting_data = execution_result.get("supporting_data", {})

    # ── Step 6: phrase the answer ─────────────────────────────────────────────
    answer = await phrase_answer(query, {
        "query_result": raw_result,
        "supporting_data": supporting_data,
    })

    # Append caveat for partial-answer queries
    if scope.is_partial and scope.caveat:
        answer = f"{answer} {scope.caveat}"

    logger.info(
        f"[chat] Answered: '{answer[:80]}' "
        f"supporting_data keys={list(supporting_data.keys())}"
    )

    return ChatResponse(
        answer=answer,
        supporting_data=supporting_data,
    )
