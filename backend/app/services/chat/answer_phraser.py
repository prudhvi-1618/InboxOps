"""
Answer phraser.
Receives raw SQL result from query_executor and has Gemini
phrase it into plain English.

CRITICAL RULE:
  Gemini receives the SQL result as input.
  Gemini phrases it — it does not invent it.
  If SQL result is zero → Gemini says zero.
  If SQL result is empty list → Gemini says none found.
  Gemini never sees the original question without the SQL result alongside it.
  This prevents hallucination by construction.
"""

from app.infrastructure.llm.gemini import call_gemini_json
from app.core.logging import get_logger

logger = get_logger(__name__)

_PHRASER_SYSTEM = """
You are a data reporting assistant for an email routing analytics system.
You receive a structured SQL query result and must phrase it as a clear,
plain-English answer for an operations executive.

Rules:
1. Base your answer ONLY on the data provided — never invent numbers
2. If a count is 0 — say zero clearly, do not hedge or speculate
3. If a list is empty — say "none found" clearly
4. Keep the answer concise — 1 to 3 sentences maximum
5. Do not mention SQL, databases, or technical terms
6. If the result contains a routing_reason — quote it briefly
7. Return ONLY this JSON — no prose outside it:

{
  "answer": "Plain English answer based strictly on the data provided"
}
"""

_PHRASER_PROMPT_TEMPLATE = """
The operations executive asked: "{query}"

The system retrieved this data from the database:
{result_json}

Write a plain English answer based ONLY on this data.
If a number is 0, say zero. If a list is empty, say none found.
Return only the JSON object with the "answer" field.
"""


async def phrase_answer(query: str, result: dict) -> str:
    """
    Calls Gemini to phrase the SQL result as plain English.
    Returns the answer string.
    Falls back to a formatted raw result string if Gemini fails —
    never returns an empty answer.
    """
    import json

    result_json = json.dumps(result, indent=2, default=str)
    prompt = _PHRASER_PROMPT_TEMPLATE.format(
        query=query.strip(),
        result_json=result_json,
    )

    try:
        response = await call_gemini_json(prompt, _PHRASER_SYSTEM)
        answer = response.get("answer", "").strip()
        if not answer:
            raise ValueError("Empty answer from Gemini")
        logger.info(f"[answer_phraser] Phrased answer for '{query[:50]}'")
        return answer
    except Exception as e:
        logger.error(f"[answer_phraser] Gemini phrasing failed: {e} — using fallback")
        return _fallback_answer(result)


def _fallback_answer(result: dict) -> str:
    """
    Generates a plain answer from raw result without Gemini.
    Used when Gemini call fails — ensures answer is always returned.
    """
    if result is None:
        return "No data found."

    if isinstance(result, int):
        return f"The count is {result}."

    if isinstance(result, list):
        if len(result) == 0:
            return "No matching records found."
        return f"Found {len(result)} matching records."

    if isinstance(result, dict):
        parts = []
        for k, v in result.items():
            if isinstance(v, (int, float)):
                parts.append(f"{k.replace('_', ' ')}: {v}")
        if parts:
            return ". ".join(parts) + "."
        return "Data retrieved successfully."

    return str(result)
