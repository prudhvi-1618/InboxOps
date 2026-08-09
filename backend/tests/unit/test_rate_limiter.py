import asyncio
import time
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.infrastructure.llm.gemini import (
    _acquire_rate_slot,
    _request_timestamps,
    call_gemini_json,
)


@pytest.mark.asyncio
async def test_rate_limiter_allows_under_limit():
    """Under the RPM limit, requests go through immediately."""
    _request_timestamps.clear()
    start = time.monotonic()
    for _ in range(5):
        await _acquire_rate_slot()
    elapsed = time.monotonic() - start
    assert elapsed < 1.0, "5 requests under limit should complete instantly"
    _request_timestamps.clear()


@pytest.mark.asyncio
async def test_rate_limiter_blocks_at_limit(monkeypatch):
    """At the RPM limit, next request should be delayed."""
    from app.core.config import get_settings
    settings = get_settings()

    _request_timestamps.clear()
    # Fill up to the limit with old-ish timestamps (55 seconds ago)
    fake_time = time.monotonic() - 55.0
    for _ in range(settings.gemini_rpm_limit):
        _request_timestamps.append(fake_time)

    # Next call should wait ~5 seconds for window to clear
    start = time.monotonic()
    await _acquire_rate_slot()
    elapsed = time.monotonic() - start
    assert elapsed >= 4.0, f"Should have waited ~5s, waited {elapsed:.1f}s"
    _request_timestamps.clear()


@pytest.mark.asyncio
async def test_gemini_retries_on_json_error():
    """If Gemini returns bad JSON, it retries."""
    bad_response = MagicMock()
    bad_response.text = "not valid json {{{"

    good_response = MagicMock()
    good_response.text = '{"decision": "task_created", "assignee_id": "u_aarti"}'

    call_count = 0

    def fake_generate(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return bad_response
        return good_response

    with patch("app.infrastructure.llm.gemini._client") as mock_client:
        mock_client.models.generate_content.side_effect = fake_generate
        _request_timestamps.clear()
        result = await call_gemini_json("test prompt", "test system")

    assert result["assignee_id"] == "u_aarti"
    assert call_count == 2
    _request_timestamps.clear()


@pytest.mark.asyncio
async def test_gemini_raises_after_all_retries_exhausted():
    """After max retries, GeminiError is raised — not a crash."""
    from app.core.exceptions import GeminiError

    def always_fail(*args, **kwargs):
        raise Exception("503 service unavailable")

    with patch("app.infrastructure.llm.gemini._client") as mock_client:
        mock_client.models.generate_content.side_effect = always_fail
        _request_timestamps.clear()
        with pytest.raises(GeminiError):
            await call_gemini_json("test", "test")
    _request_timestamps.clear()
