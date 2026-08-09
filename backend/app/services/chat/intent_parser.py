"""
Intent parser: takes a natural language query and returns a structured
intent dict that the SQL executor can act on directly.

Pipeline:
  NL query → Gemini (intent extraction only) → structured intent dict
  → SQL executor → raw result → Gemini (phrasing only) → response

Gemini is called TWICE per chat query:
  1. Here: to extract intent (what does the user want to know?)
  2. In answer_phraser.py: to phrase the SQL result in plain English

Gemini NEVER sees the answer — it only sees the question (call 1)
and the raw data (call 2). It cannot hallucinate counts it never computed.
"""

from app.infrastructure.llm.gemini import call_gemini_json
from app.core.logging import get_logger

logger = get_logger(__name__)

# ── Intent extraction system prompt ──────────────────────────────────────────
_INTENT_SYSTEM = """
            You are an intent extraction engine for an email routing analytics system.
            Your only job is to read a natural language question and return a JSON object
            describing what structured data the user wants.

            You NEVER answer the question. You NEVER invent numbers or facts.
            You ONLY describe what kind of query should be run.

            The database has one main table: email_decisions
            Columns available:
              email_id, thread_id, decision, category, assignee_id, task_id,
              priority, confidence, skipped_reason, spam_lookalike_category,
              deal_value_inr, company_name, due_date, routing_reason,
              raw_subject, raw_from_email, raw_from_name, received_at, processed_at

            decision values   : task_created | task_updated | skipped | error
            category values   : enterprise_rfp | smb_enquiry | marketing | alliances | finance | triage
            assignee_id values: u_aarti | u_rohit | u_meera | u_karan | u_divya | u_triage
            priority values   : high | medium | low
            skipped_reason    : ooo | newsletter | spam

            Return ONLY this JSON object — no prose, no markdown:
            {
              "intent_type": one of [
                "count",           -- user wants a number or count
                "list",            -- user wants a list of items
                "sum",             -- user wants a total/sum of a numeric field
                "rate",            -- user wants a percentage or ratio
                "compound_filter", -- user wants items matching multiple conditions
                "out_of_scope",    -- request cannot be answered from this data
                "zero_check"       -- question about a category that may have zero matches
              ],
              "filters": {
                "decision": null | "task_created" | "task_updated" | "skipped" | "error",
                "category": null | "enterprise_rfp" | "smb_enquiry" | "marketing" | "alliances" | "finance" | "triage",
                "assignee_id": null | "u_aarti" | "u_rohit" | "u_meera" | "u_karan" | "u_divya" | "u_triage",
                "priority": null | "high" | "medium" | "low",
                "skipped_reason": null | "ooo" | "newsletter" | "spam",
                "confidence_lt": null | float,
                "confidence_gt": null | float,
                "deal_value_not_null": null | true | false
              },
              "aggregation": null | "count" | "sum" | "list" | "rate",
              "sum_field": null | "deal_value_inr",
              "group_by": null | "category" | "assignee_id" | "skipped_reason" | "priority",
              "include_fields": [],
              "limit": null | integer,
              "out_of_scope_reason": null | "string explaining why this cannot be answered",
              "sub_intent": null | "triage_with_reasons" | "threads_multi_updated" | "spurious_rate" | "gst_refund_count" | "high_priority_low_confidence"
            }

            MAPPING RULES — apply these to classify the query:

            "how many X" → intent_type: "count", aggregation: "count"
            "total deal value" / "sum of" → intent_type: "sum", sum_field: "deal_value_inr"
            "show me" / "list" / "what are" → intent_type: "list", aggregation: "list"
            "rate" / "percentage" / "ratio" → intent_type: "rate"
            "high priority AND low confidence" → intent_type: "compound_filter"
            "triage" with "why" → sub_intent: "triage_with_reasons"
            "thread updated more than once" → sub_intent: "threads_multi_updated"
            "spurious rate" → sub_intent: "spurious_rate"
            "GST refund" → sub_intent: "gst_refund_count", intent_type: "zero_check"
            "send email" / "create task" / "assign" / any action → intent_type: "out_of_scope"

            SPAM vs MARKETING distinction:
            "spam we correctly ignored" → decision: "skipped", skipped_reason: "spam"
            "marketing emails" → decision: IN (task_created, task_updated), category: "marketing"
            These are DIFFERENT buckets. If asked for both, set group_by: "category" and note both.

            CANNOT SUB-DISTINGUISH:
            "resellers vs tech integration partners within alliances" →
              intent_type: "count", filters.category: "alliances",
              out_of_scope_reason: "sub-category breakdown not stored — only top-level alliances category available"
      """

_INTENT_PROMPT_TEMPLATE = """
      Extract the intent from this analytics question:

      Question: {query}

      Return only the JSON intent object. No prose.
    """


async def parse_intent(query: str) -> dict:
    """
    Calls Gemini to extract structured intent from the NL query.
    Returns an intent dict the SQL executor can act on.
    Never raises — returns out_of_scope intent on any failure.
    """
    prompt = _INTENT_PROMPT_TEMPLATE.format(query=query.strip())
    try:
        intent = await call_gemini_json(prompt, _INTENT_SYSTEM)
        logger.info(f"[intent_parser] query='{query[:60]}' → intent_type={intent.get('intent_type')}")
        return intent
    except Exception as e:
        logger.error(f"[intent_parser] Failed to parse intent: {e}")
        # Fail safe — return out_of_scope so executor returns honest zero/unknown
        return {
            "intent_type": "out_of_scope",
            "filters": {},
            "aggregation": None,
            "sum_field": None,
            "group_by": None,
            "include_fields": [],
            "limit": None,
            "out_of_scope_reason": f"Intent parsing failed: {e}",
            "sub_intent": None,
        }
