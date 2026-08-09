import asyncio
import json
import re
import time
from collections import deque
from google import genai
from google.genai import types
from app.core.config import get_settings
from app.core.exceptions import GeminiError
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()

# ── Single client — instantiated once at module load ─────────────────────────
_client = genai.Client(api_key=settings.gemini_api_key)


def get_client() -> genai.Client:
    return _client

# ── Token-bucket rate limiter — 15 RPM free tier ─────────────────────────────
# Tracks timestamps of recent requests in a sliding window of 60 seconds.
_request_timestamps: deque[float] = deque()
_rate_lock = asyncio.Lock()


async def _acquire_rate_slot() -> None:
    """
    Blocks until a request slot is available within the 60-second window.
    Allows up to gemini_rpm_limit requests per 60 seconds.
    Uses a sliding window — not a fixed bucket reset.
    """
    async with _rate_lock:
        while True:
            now = time.monotonic()
            # Drop timestamps older than 60 seconds
            while _request_timestamps and now - _request_timestamps[0] > 60.0:
                _request_timestamps.popleft()

            if len(_request_timestamps) < settings.gemini_rpm_limit:
                _request_timestamps.append(now)
                return

            # Wait until the oldest request falls out of the window
            oldest = _request_timestamps[0]
            wait_sec = 60.0 - (now - oldest) + 0.1  # +0.1s buffer
            logger.debug(f"[rate_limiter] RPM limit reached — waiting {wait_sec:.1f}s")
            await asyncio.sleep(wait_sec)


def _parse_gemini_response(raw: str) -> dict:
    """
    Strips markdown fences and parses JSON.
    Raises ValueError if parsing fails.
    """
    raw = raw.strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # Fallback: extract substring between first { and last }
        match = re.search(r"(\{.*\})", raw, re.DOTALL)
        if match:
            return json.loads(match.group(1))
        raise


async def call_gemini_json(prompt: str, system: str) -> dict:
    """
    Calls Gemini with rate limiting and exponential backoff retry.

    Retry behaviour:
      - 429 / quota errors    → exponential backoff, always retry
      - JSON parse errors     → retry (model occasionally wraps response)
      - Other errors          → retry up to max_retries, then raise GeminiError
    """
    last_error: Exception | None = None

    for attempt in range(settings.gemini_max_retries):
        try:
            await _acquire_rate_slot()

            response = await asyncio.to_thread(
                _client.models.generate_content,
                model=settings.gemini_model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system,
                    temperature=0.0,
                    max_output_tokens=4096,
                    response_mime_type="application/json",
                ),
            )

            raw = response.text or ""
            result = _parse_gemini_response(raw)
            return result

        except json.JSONDecodeError as e:
            logger.warning(
                f"[gemini] JSON parse failed (attempt {attempt + 1}/{settings.gemini_max_retries}): {e}"
            )
            last_error = GeminiError(f"JSON parse failed: {e}")
            # Short pause before retry — model sometimes fixes itself
            await asyncio.sleep(1.0)

        except Exception as e:
            err_str = str(e).lower()
            is_rate_limit = "429" in err_str or "quota" in err_str or "resource_exhausted" in err_str

            if is_rate_limit:
                delay = settings.gemini_retry_base_delay * (2 ** attempt)
                delay_match = re.search(r"retry in (\d+(?:\.\d+)?)s", err_str) or re.search(r"retrydelay['\":\s]+(\d+)", err_str)
                if delay_match:
                    delay = max(delay, float(delay_match.group(1)) + 1.0)
                logger.warning(
                    f"[gemini] Rate limit hit (attempt {attempt + 1}/{settings.gemini_max_retries}) "
                    f"— backing off {delay:.1f}s"
                )
                await asyncio.sleep(delay)
                last_error = GeminiError(f"Rate limit: {e}")
            else:
                delay = settings.gemini_retry_base_delay * (2 ** attempt)
                logger.error(
                    f"[gemini] Call failed (attempt {attempt + 1}/{settings.gemini_max_retries}): {e} "
                    f"— retrying in {delay:.1f}s"
                )
                await asyncio.sleep(delay)
                last_error = GeminiError(str(e))

    # All retries exhausted
    logger.error(f"[gemini] All {settings.gemini_max_retries} retries exhausted")
    raise last_error or GeminiError("All Gemini retries exhausted")


async def call_gemini_json_with_fallback(prompt: str, system: str) -> dict | None:
    """
    Same as call_gemini_json but returns None instead of raising.
    Use this when you want the caller to handle the None gracefully
    rather than catching an exception.
    """
    try:
        return await call_gemini_json(prompt, system)
    except GeminiError as e:
        logger.error(f"[gemini] Fallback triggered: {e}")
        return None
