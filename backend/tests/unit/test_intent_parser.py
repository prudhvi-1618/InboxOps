import pytest
from unittest.mock import AsyncMock, patch
from app.services.chat.intent_parser import parse_intent


async def mock_gemini(prompt: str, system: str) -> dict:
    """Returns pre-built intents for known queries — no real Gemini call."""
    q = prompt.lower()
    if "rfp" in q or "proposal" in q:
        return {"intent_type": "count", "filters": {"category": "enterprise_rfp"},
                "aggregation": "count", "group_by": None, "sub_intent": None,
                "sum_field": None, "include_fields": [], "limit": None,
                "out_of_scope_reason": None}
    if "marketing" in q and "spam" in q:
        return {"intent_type": "count", "filters": {},
                "aggregation": "count", "group_by": "category",
                "sub_intent": None, "sum_field": None,
                "include_fields": [], "limit": None, "out_of_scope_reason": None}
    if "triage" in q and "why" in q:
        return {"intent_type": "list", "filters": {"assignee_id": "u_triage"},
                "aggregation": "list", "group_by": None,
                "sub_intent": "triage_with_reasons",
                "sum_field": None, "include_fields": [], "limit": None,
                "out_of_scope_reason": None}
    if "spurious" in q:
        return {"intent_type": "rate", "filters": {}, "aggregation": "rate",
                "group_by": None, "sub_intent": "spurious_rate",
                "sum_field": None, "include_fields": [], "limit": None,
                "out_of_scope_reason": None}
    if "high priority" in q and "low confidence" in q:
        return {"intent_type": "compound_filter",
                "filters": {"priority": "high", "confidence_lt": 0.65},
                "aggregation": "list", "group_by": None,
                "sub_intent": "high_priority_low_confidence",
                "sum_field": None, "include_fields": [], "limit": None,
                "out_of_scope_reason": None}
    if "gst refund" in q:
        return {"intent_type": "zero_check", "filters": {}, "aggregation": "count",
                "group_by": None, "sub_intent": "gst_refund_count",
                "sum_field": None, "include_fields": [], "limit": None,
                "out_of_scope_reason": None}
    if "send" in q or "email aarti" in q:
        return {"intent_type": "out_of_scope", "filters": {}, "aggregation": None,
                "group_by": None, "sub_intent": None, "sum_field": None,
                "include_fields": [], "limit": None,
                "out_of_scope_reason": "This system answers questions about processed data — it does not send emails or take actions"}
    if "thread" in q and "updated" in q:
        return {"intent_type": "list", "filters": {}, "aggregation": "list",
                "group_by": None, "sub_intent": "threads_multi_updated",
                "sum_field": None, "include_fields": [], "limit": None,
                "out_of_scope_reason": None}
    return {"intent_type": "count", "filters": {}, "aggregation": "count",
            "group_by": None, "sub_intent": None, "sum_field": None,
            "include_fields": [], "limit": None, "out_of_scope_reason": None}


@pytest.mark.asyncio
@pytest.mark.parametrize("query,expected_type,expected_filter,expected_sub", [
    ("How many emails were RFP related?", "count", {"category": "enterprise_rfp"}, None),
    ("How many marketing vs spam we correctly ignored?", "count", {}, None),
    ("Show me everything in triage and why", "list", {"assignee_id": "u_triage"}, "triage_with_reasons"),
    ("What is our spurious rate?", "rate", {}, "spurious_rate"),
    ("Which tasks are high priority but low confidence?", "compound_filter", {"priority": "high"}, "high_priority_low_confidence"),
    ("How many emails were about GST refunds?", "zero_check", {}, "gst_refund_count"),
    ("Send Aarti an email about Meridian Steel", "out_of_scope", {}, None),
    ("Did any thread get updated more than once?", "list", {}, "threads_multi_updated"),
])
async def test_intent_parsing(query, expected_type, expected_filter, expected_sub):
    with patch("app.services.chat.intent_parser.call_gemini_json", side_effect=mock_gemini):
        intent = await parse_intent(query)

    assert intent["intent_type"] == expected_type
    if expected_sub:
        assert intent["sub_intent"] == expected_sub
    for k, v in expected_filter.items():
        assert intent["filters"].get(k) == v


@pytest.mark.asyncio
async def test_intent_parser_fails_gracefully():
    """Gemini failure → out_of_scope, never raises."""
    with patch(
        "app.services.chat.intent_parser.call_gemini_json",
        side_effect=Exception("Gemini down"),
    ):
        intent = await parse_intent("How many RFPs?")

    assert intent["intent_type"] == "out_of_scope"
    assert intent["out_of_scope_reason"] is not None
