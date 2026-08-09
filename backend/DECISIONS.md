# Architectural Decision Records (ADR)

## ADR 1: LangGraph for Workflow Orchestration
- **Decision**: Use LangGraph state machine rather than single-prompt monolithic LLM calls.
- **Rationale**: Decomposing email handling into discreet stages (Hygiene -> Extraction -> Routing -> Priority -> Task Sync) enables deterministic rule enforcement, unit testing of intermediate states, and lower LLM token latency.

## ADR 2: Deterministic Policy Fallback
- **Decision**: Combine LLM extraction with deterministic domain policies (money parser, 72-hour deadline calculation, team roster matching).
- **Rationale**: Ensures strict compliance with enterprise routing rules and eliminates non-deterministic routing hallucinations.

## ADR 3: Idempotency & Thread Reconciliation
- **Decision**: Local SQLite tracking for all inbound emails and thread states with upstream Task API synchronization.
- **Rationale**: Protects against duplicate task creation for batch replays and handles email thread updates seamlessly.
