import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch
from app.main import app
from app.core.config import get_settings


@pytest.mark.asyncio
async def test_chat_out_of_scope_send_email():
    settings = get_settings()
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post("/api/chat", json={
            "candidate_id": settings.candidate_id_normalized,
            "query": "Send Aarti an email about the Meridian Steel RFP",
        })
    assert resp.status_code == 200
    data = resp.json()
    assert data["supporting_data"] == {}
    assert "does not" in data["answer"].lower() or "can't" in data["answer"].lower()


@pytest.mark.asyncio
async def test_chat_returns_supporting_data():
    settings = get_settings()
    mock_intent = {
        "intent_type": "count",
        "filters": {"category": "enterprise_rfp"},
        "group_by": None, "sub_intent": None,
        "sum_field": None, "include_fields": [],
        "limit": None, "aggregation": "count",
        "out_of_scope_reason": None,
    }
    mock_phrase = {"answer": "There were 3 enterprise RFP emails."}

    with patch("app.api.routes.chat.parse_intent", return_value=mock_intent), \
         patch("app.services.chat.answer_phraser.call_gemini_json", return_value=mock_phrase):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post("/api/chat", json={
                "candidate_id": settings.candidate_id_normalized,
                "query": "How many RFP emails came in?",
            })

    assert resp.status_code == 200
    data = resp.json()
    assert "answer" in data
    assert "supporting_data" in data
    assert isinstance(data["supporting_data"], dict)


@pytest.mark.asyncio
async def test_chat_answer_and_supporting_data_consistent():
    """
    supporting_data must come from SQL result, not from answer text.
    Ask the same question twice — supporting_data must be identical both times.
    """
    settings = get_settings()
    mock_intent = {
        "intent_type": "zero_check", "filters": {},
        "sub_intent": "gst_refund_count", "group_by": None,
        "sum_field": None, "include_fields": [], "limit": None,
        "aggregation": "count", "out_of_scope_reason": None,
    }
    mock_phrase = {"answer": "There were zero emails about GST refunds."}

    with patch("app.api.routes.chat.parse_intent", return_value=mock_intent), \
         patch("app.services.chat.answer_phraser.call_gemini_json", return_value=mock_phrase):

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            r1 = await client.post("/api/chat", json={
                "candidate_id": settings.candidate_id_normalized,
                "query": "How many emails were about GST refunds?",
            })
            r2 = await client.post("/api/chat", json={
                "candidate_id": settings.candidate_id_normalized,
                "query": "How many emails were about GST refunds?",
            })

    assert r1.json()["supporting_data"] == r2.json()["supporting_data"]
    assert r1.json()["supporting_data"].get("gst_refund_count") == 0
