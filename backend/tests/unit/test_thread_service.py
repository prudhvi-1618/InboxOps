import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.domain.services.thread_service import (
    build_patch_payload,
    patch_existing_task,
    post_new_task,
)


@pytest.mark.asyncio
async def test_build_patch_payload_excludes_none():
    state = {
        "priority": "high",
        "due_date": "2026-08-11",
        "deal_value_inr": 3_200_000,
        "assignee_id": None,   # None — must be excluded
        "company_name": None,  # None — must be excluded
        "confidence": 0.91,
    }
    payload = await build_patch_payload(state)
    assert "assignee_id" not in payload
    assert "company_name" not in payload
    assert payload["priority"] == "high"
    assert payload["deal_value_inr"] == 3_200_000
    assert payload["confidence"] == 0.91


@pytest.mark.asyncio
async def test_build_patch_payload_empty_when_all_none():
    state = {k: None for k in [
        "title", "description", "assignee_id", "category",
        "priority", "due_date", "deal_value_inr", "company_name", "confidence"
    ]}
    payload = await build_patch_payload(state)
    assert payload == {}


@pytest.mark.asyncio
async def test_patch_existing_task_calls_api():
    state = {"priority": "high", "due_date": "2026-08-11", "deal_value_inr": 3_200_000}
    mock_client = AsyncMock()
    mock_client.update_task.return_value = {"task_id": "tsk_abc"}

    with patch("app.domain.services.thread_service._task_client", mock_client):
        result = await patch_existing_task("tsk_abc", state)

    mock_client.update_task.assert_called_once_with(
        "tsk_abc",
        {"priority": "high", "due_date": "2026-08-11", "deal_value_inr": 3_200_000},
    )


@pytest.mark.asyncio
async def test_post_new_task_includes_candidate_id():
    email = {
        "email_id": "em_001",
        "thread_id": "th_001",
        "subject": "RFP Test",
    }
    state = {
        "assignee_id": "u_aarti",
        "category": "enterprise_rfp",
        "priority": "medium",
        "due_date": "2026-08-12",
        "deal_value_inr": 2_500_000,
        "company_name": "Meridian Steel",
        "confidence": 0.91,
        "title": "RFP — Meridian Steel",
        "description": "Enterprise DMS RFP.",
    }
    mock_client = AsyncMock()
    mock_client.create_task.return_value = {"task_id": "tsk_new"}

    with patch("app.domain.services.thread_service._task_client", mock_client):
        result = await post_new_task(email, state, "test@example.com")

    call_args = mock_client.create_task.call_args[0][0]
    assert call_args["candidate_id"] == "test@example.com"
    assert call_args["source_email_id"] == "em_001"
    assert call_args["thread_id"] == "th_001"
    assert call_args["assignee_id"] == "u_aarti"
    assert call_args["deal_value_inr"] == 2_500_000


@pytest.mark.asyncio
async def test_patch_skipped_when_payload_empty():
    """Empty patch payload → no API call, returns skipped flag."""
    state = {k: None for k in [
        "title", "description", "assignee_id", "category",
        "priority", "due_date", "deal_value_inr", "company_name", "confidence"
    ]}
    mock_client = AsyncMock()

    with patch("app.domain.services.thread_service._task_client", mock_client):
        result = await patch_existing_task("tsk_empty", state)

    mock_client.update_task.assert_not_called()
    assert result.get("skipped_patch") is True
