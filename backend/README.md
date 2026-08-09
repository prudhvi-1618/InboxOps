# Sales Inbox Router — Backend

High-performance email classification and task routing engine built with FastAPI, LangGraph, and Google Gemini.

## Architecture Highlights
- **FastAPI**: Async HTTP server with structured Pydantic schemas.
- **LangGraph**: Declarative directed graph workflow for multi-stage email processing (Preprocess -> Analyze -> Hygiene -> Extract -> Route -> Prioritize -> Validate -> Threading -> Task Writer -> Persistence).
- **Gemini LLM**: Structured JSON extraction for sales context, intent, entities, sentiment, and urgency.
- **SQLite / SQLAlchemy**: Local persistence for runs, idempotency, decisions, and offline reconciliation.

## Setup & Running

```bash
# Install dependencies
pip install -e .

# Configure environment
cp .env.example .env

# Run development server
uvicorn app.main:app --reload --port 8000
```

## Running Tests & Evaluations

```bash
pytest tests/unit
pytest tests/integration
python -m tests.evals.evaluate
```
