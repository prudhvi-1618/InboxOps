import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import get_settings
from app.core.logging import setup_logging, get_logger
from app.core.exceptions import (
    TaskAPIError, GeminiError,
    task_api_error_handler, gemini_error_handler,
)
from app.infrastructure.database.connection import init_db
from app.api.routes import health, ingest, tasks, stats, chat, generate

setup_logging()
logger = get_logger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting inbox-router backend")
    try:
        settings.validate_all()
    except Exception as e:
        logger.warning(f"Config validation: {e}")
    await init_db()
    logger.info(f"candidate_id : {settings.candidate_id_normalized}")
    logger.info(f"task_api_base: {settings.task_api_base_url}")
    logger.info(f"environment  : {settings.environment}")
    yield
    logger.info("Shutting down inbox-router backend")


app = FastAPI(
    title="Inbox Router",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS ──────────────────────────────────────────────────────────────────────
# allow_origin_regex covers:
#   - Any Vercel preview or production URL (*.vercel.app)
#   - Any Netlify URL (*.netlify.app)
#   - Local dev on any port
#   - Any explicit FRONTEND_URL set in env (production custom domain)
_FRONTEND_URL = os.getenv("FRONTEND_URL", "")

_CORS_REGEX = (
    r"https://.*\.vercel\.app"
    r"|https://.*\.netlify\.app"
    r"|http://localhost:\d+"
    r"|http://127\.0\.0\.1:\d+"
)

if _FRONTEND_URL:
    # Escape dots in custom domain for regex safety
    _escaped = _FRONTEND_URL.replace(".", r"\.")
    _CORS_REGEX = _CORS_REGEX + f"|{_escaped}"
    logger.info(f"[cors] Custom frontend origin added: {_FRONTEND_URL}")

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=_CORS_REGEX,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Accept"],
    max_age=600,  # preflight cache 10 minutes
)

# ── Exception handlers ────────────────────────────────────────────────────────
app.add_exception_handler(TaskAPIError, task_api_error_handler)
app.add_exception_handler(GeminiError, gemini_error_handler)

# ── Routes ────────────────────────────────────────────────────────────────────
app.include_router(health.router)
app.include_router(ingest.router)
app.include_router(tasks.router)
app.include_router(stats.router)
app.include_router(chat.router)
app.include_router(generate.router)
