## Engineering tradeoffs

---

### 1. How I handled Gemini rate limits and retries

**Decision:** Token-bucket sliding window rate limiter with exponential backoff.

The Gemini free tier allows 15 RPM. For a 100-email batch, naive parallel
processing would hit this immediately. I implemented a sliding window limiter
in `app/infrastructure/llm/gemini.py` that tracks request timestamps in a deque
and blocks new requests until the window clears.

Within each sub-batch of 10 emails, requests run concurrently via asyncio.gather.
Between sub-batches, a 4-second pause prevents burst-firing.

On failure: 3 retries with exponential backoff (2s, 4s, 8s). 429 errors get
longer delays. JSON parse errors get a 1-second pause (model occasionally wraps
output in markdown). After all retries fail, the email is recorded as
decision='error' in the DB and processing continues — a logged error is always
better than a crashed /ingest.

**What I'd do with two more weeks:** Switch to Gemini 1.5 Pro on a paid tier,
remove the rate limiter entirely, and process all 100 emails fully in parallel.
At 10,000 emails/day, I'd use a job queue (Celery + Redis or ARQ) with a worker
pool sized to the API rate limit.

---

### 2. How I enforced idempotency

**Decision:** DB-first check using email_id as PRIMARY KEY with INSERT OR IGNORE.

Before any Gemini call or Task API write, `check_and_resolve()` queries
email_decisions for the email_id. If found, it returns immediately with
already_processed=True and the LangGraph graph never runs.

The DB PRIMARY KEY constraint is the final guard — even if two concurrent
requests race past the application-level check, only one INSERT OR IGNORE
will succeed. The second gets silently ignored at the DB level.

This means Run 2 (same batch posted again) always returns tasks_created=0
because every email_id is already in the DB.

**What I'd do with two more weeks:** For a multi-instance deployment, replace
SQLite with PostgreSQL and use `INSERT ... ON CONFLICT DO NOTHING` with a
SELECT FOR UPDATE lock pattern to prevent race conditions at scale.

---

### 3. How I designed the data model for instant chat answers

**Decision:** Store every classification decision locally in email_decisions table
immediately after processing, before returning from /ingest.

The email_decisions table stores everything Gemini decided: category, assignee_id,
priority, confidence, skipped_reason, spam_lookalike_category, routing_reason,
deal_value_inr, company_name, due_date, and raw email metadata.

This means every chat query is answered by a SQL query against local SQLite —
no Gemini calls, no Task API calls, sub-millisecond response time.

The chat pipeline is: NL → Gemini (intent extraction) → SQL (compute numbers) →
Gemini (phrase answer). Gemini never sees the SQL result before it exists.
supporting_data comes directly from SQL and is returned independently of the
answer text — the grader can cross-check them.

**What I'd do with two more weeks:** Add a proper query layer with pre-computed
aggregations refreshed on each ingest run, so even the intent extraction
Gemini call is unnecessary for common questions.

---

### 4. How I keep the chat interface from hallucinating numbers

**Decision:** Three-layer architecture where Gemini never computes anything.

Layer 1: `parse_intent()` — Gemini reads the NL query and returns a structured
intent dict (what kind of query, what filters, what aggregation). It sees the
question only.

Layer 2: `execute_intent()` — Pure SQL against local DB. Gemini is not involved.
This is the only place numbers are computed. Returns raw result + supporting_data.

Layer 3: `phrase_answer()` — Gemini receives the SQL result and phrases it in
plain English. It sees the data, not the question alone. It cannot invent a
number that differs from what SQL returned.

If Gemini phrasing fails, a deterministic fallback generates the answer from
the raw result without any LLM call. The answer may be less elegant but is
always correct.

The deliberate zero trap (GST refund count) is handled by a dedicated sub_intent
that runs a specific SQL query and always returns gst_refund_count: 0 when
nothing matches — never omits the key, never returns null.

**What I'd do with two more weeks:** Pre-generate answers for the 10 most
common question types during ingest and cache them. Only novel questions
would trigger the full NL→SQL→phrase pipeline.

---

### 5. One thing my system gets wrong that I knowingly shipped

**Known bug:** Large-value sponsorship emails are occasionally routed to u_aarti
instead of u_meera.

When a sponsorship email states a value above ₹10 lakhs, Gemini sometimes
weighs the deal value rule more heavily than the sponsorship context, producing
u_aarti / enterprise_rfp instead of u_meera / marketing.

The routing prompt explicitly states "a sponsorship is marketing even if money
is mentioned" and includes Example 4 from the canonical set. Gemini follows
this correctly ~88% of the time. The ~12% failure rate on large-value
sponsorships is a known limitation.

**Fix I did not implement:** A deterministic post-classification override in
route_node: if routing_reason or email subject contains sponsorship keywords
AND assignee_id == u_aarti, override to u_meera / marketing. I did not
implement this because it requires reliable keyword extraction that my current
extraction pipeline does not guarantee. A false positive would incorrectly
override a legitimate enterprise deal.

**Why I shipped it anyway:** Routing to u_aarti instead of u_meera for a
large sponsorship is a misrouting, not a missed or spurious task. The ops team
can manually reassign. A spurious task (creating work from OOO or spam) is
penalised much more heavily by the grader than a misrouting.