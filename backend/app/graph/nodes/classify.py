from app.graph.state import EmailProcessingState
from app.infrastructure.llm.gemini import call_gemini_json
from app.infrastructure.llm.prompts import SYSTEM_PROMPT, build_classification_prompt
from app.core.logging import get_logger

logger = get_logger(__name__)


async def classify_node(state: EmailProcessingState) -> dict:
    """
    Calls Gemini to classify the email.
    On failure: stores error, does NOT raise (graceful degradation).
    """
    email = state["email"]
    try:
        prompt = build_classification_prompt(email)
        result = await call_gemini_json(prompt, SYSTEM_PROMPT)
        logger.info(f"[classify] {email['email_id']} -> {result.get('assignee_id')} conf={result.get('confidence')}")
        return {"gemini_result": result, "gemini_error": None}
    except Exception as e:
        logger.error(f"[classify] {email['email_id']} FAILED: {e}")
        return {
            "gemini_result": None,
            "gemini_error": str(e),
            "skip": True,
            "decision": "error",
            "error_message": str(e),
        }
