# PLAN.md — RedirectIQ API (Backend)

This file is the single source of truth for building the RedirectIQ backend.
It is written for Claude (or any AI coding assistant) and for the developer.

The frontend lives in a separate repo, `redirectiq-web`, with its own plan.md.
This repo builds **only the backend**. Never add frontend code here.

---

## How to Use This Plan (Read First, Claude)

- Work on **one phase at a time**. Never start the next phase unless asked.
- At the start of a phase, restate its goal and task list, then build it step by step.
- At the end of a phase, check every acceptance criterion, run all tests, and **stop**.
  Summarize what was built, what was learned, and anything left open.
- Do not add technologies, libraries, or services that are not listed in the current phase.
- Prefer simple, readable code over clever code. This is a learning project:
  add short comments explaining *why*, not just *what*, for any non-obvious design choice.
- If a task is ambiguous, ask the developer before guessing.
- Update the **Progress Log** at the bottom of this file when a phase is complete.

Example prompts for the developer:

```text
Read plan.md. Start Phase 0.
Read plan.md. Continue Phase 2 from task 4.
Read plan.md. Phase 3 is done — review it against the acceptance criteria.
```

---

## 1. Project Summary

RedirectIQ is a link management and analytics platform, built for learning.

Users create short links. When someone clicks a short link, they are redirected
instantly, and the click is recorded asynchronously for analytics. Later phases add
analytics APIs, real-time stats, an AI analytics assistant, and simple ML.
The `redirectiq-web` dashboard consumes this API.

**Core rule:** Redirect fast, collect events asynchronously, analyze at scale,
and let AI explain trusted structured data.

---

## 2. Tech Stack (One Backend Language: Python)

| Area | Choice |
|---|---|
| Language | Python 3.12+ |
| Package manager | uv |
| Web framework | FastAPI + Pydantic v2 |
| ORM / migrations | SQLAlchemy 2.x (async) + Alembic + asyncpg |
| Transactional DB | PostgreSQL 16 |
| Cache / queues | Redis 7 (cache, rate limits, Redis Streams, pub/sub) |
| Analytics DB | ClickHouse (added in Phase 3) |
| AI | OpenAI Python SDK (Phase 7) |
| ML | scikit-learn, Polars (Phase 8) |
| Lint / format | ruff |
| Tests | pytest + pytest-asyncio + httpx |
| Local infra | Docker Compose |

**Not used unless a later phase says so:** Go, Redpanda/Kafka, Celery, Kubernetes, pandas, PyTorch.

---

## 3. Architecture

```text
redirectiq-web ──> api (FastAPI) ──> PostgreSQL
                                   │      └────> Redis (cache write-through)
                                   └───────────> ClickHouse (analytics queries)

Visitor ──> redirect (FastAPI) ──> Redis ──(miss)──> PostgreSQL
                  │
                  └── returns 302 immediately
                  └── pushes click event ──> Redis Stream "clicks"
                                                   │
                                   worker (Python) ┘──> ClickHouse
```

Three Python processes, one codebase:

- **api** — main backend: auth, organizations, links, analytics endpoints, AI.
- **redirect** — tiny, fast app that only resolves slugs and emits click events.
- **worker** — consumes click events, enriches them, writes to ClickHouse.

---

## 4. Repository Structure

```text
redirectiq-api/
├── plan.md
├── README.md
├── docker-compose.yml
├── .env.example
├── pyproject.toml
├── alembic.ini
├── migrations/
├── tests/
├── src/app/
│   ├── core/          # config, db sessions, redis client, security, logging
│   ├── models/        # SQLAlchemy models
│   ├── schemas/       # Pydantic schemas
│   ├── auth/
│   ├── organizations/
│   ├── links/
│   ├── analytics/
│   ├── ai/            # Phase 7
│   ├── ml/            # Phase 8
│   ├── api_main.py        # entrypoint: api (port 8000)
│   ├── redirect_main.py   # entrypoint: redirect (port 8001)
│   └── worker_main.py     # entrypoint: worker
```

Each feature folder contains its own `router.py`, `service.py`, and (if needed) `repository.py`.
Routers stay thin; business logic lives in services.

---

## 5. Global Rules (Apply to Every Phase)

1. **Multi-tenancy:** every business table has `organization_id`. Every query filters by it.
   The organization always comes from the authenticated session, never from request input.
2. **Redirect path stays fast:** the redirect app never writes to PostgreSQL or ClickHouse
   during a request. It only reads Redis (and Postgres on cache miss) and pushes events.
3. **Config via environment variables** loaded through a Pydantic `Settings` class. No secrets in code.
4. **Validation:** all input goes through Pydantic schemas. Destination URLs must be
   `http`/`https` only, with a max length, and must not point to private/internal IPs.
5. **Tests:** every phase adds tests for its features. All tests pass before a phase ends.
6. **Migrations:** every schema change goes through Alembic. Never edit the DB by hand.
7. **IDs:** use UUIDs for primary keys. Slugs are separate, unique per domain.
8. **Timestamps:** store everything in UTC.
9. **Errors:** return consistent JSON errors `{ "error": { "code": "...", "message": "..." } }`.
10. **Keep it small:** no abstraction until it is needed at least twice.
11. **API contract for the frontend:** every endpoint has explicit Pydantic request/response
    models, a clear `operation_id`, and a tag, so `/openapi.json` generates clean TypeScript
    types in `redirectiq-web`. All routes live under `/v1/`. Breaking changes to response
    shapes must be noted in the Progress Log.
12. **Cross-origin setup:** the frontend runs on a different origin (`http://localhost:4321`).
    Configure CORS with an explicit allow-list from settings (never `*` with credentials),
    `allow_credentials=True`, and CSRF protection for cookie-authenticated state-changing requests.

---

## 6. Phases

### Phase 0 — Project Setup

**Goal:** a running skeleton with the development workflow in place.

Tasks:
1. Create the repo structure from Section 4.
2. `docker-compose.yml` with PostgreSQL and Redis (with named volumes and healthchecks).
3. Backend project with uv, FastAPI, SQLAlchemy async, Alembic, ruff, pytest.
4. `core/config.py` with Pydantic Settings; `.env.example` listing every variable.
5. `api_main.py` and `redirect_main.py` each expose `GET /health` checking DB and Redis.
6. First empty Alembic migration runs successfully.
7. Pytest setup with a separate test database and an async HTTP test client.
8. README with "how to run locally" steps.
9. CORS configured from an `ALLOWED_ORIGINS` setting (see Global Rule 12).

Acceptance criteria:
- [ ] `docker compose up` starts Postgres and Redis.
- [ ] Both apps start and `/health` returns OK.
- [ ] `alembic upgrade head` works.
- [ ] `pytest` and `ruff check` pass.

Learning focus: project layout, async SQLAlchemy, config management, Docker Compose.

---

### Phase 1 — Users, Organizations, and Links

**Goal:** a user can sign up, belongs to an organization, and can manage links via the API.

Tasks:
1. Models: `users`, `organizations`, `memberships` (role: `owner`, `admin`, `member`, `viewer`), `links`.
2. Auth: email + password (argon2 hashing), login creates a server-side session stored in Redis,
   sent as an HTTP-only, SameSite=Lax cookie. Logout deletes the session.
3. On signup, create a personal organization with the user as `owner`.
4. Dependency `get_current_context()` returning the user, active organization, and role.
5. Link CRUD: create, list (paginated), get, update, delete.
   Fields: `id`, `organization_id`, `slug`, `destination_url`, `title`, `is_active`,
   `expires_at`, `created_at`, `updated_at`.
6. Slug generation: random 7-character base62; allow custom slugs with validation
   (length, allowed characters, reserved words like `api`, `health`, `login`).
7. Role checks: `viewer` can read only; `member` and above can create and edit.
8. Basic rate limiting on login and link creation using Redis.

Acceptance criteria:
- [ ] Signup, login, logout, and "me" endpoints work.
- [ ] A user cannot read or modify links from another organization (tested).
- [ ] Invalid URLs, private-IP destinations, and duplicate slugs are rejected (tested).
- [ ] Role permissions are enforced (tested).

Learning focus: authentication, sessions, authorization, tenant isolation.

---

### Phase 2 — Redirect Service and Caching

**Goal:** short links redirect quickly using Redis, with clicks captured asynchronously.

Tasks:
1. `redirect_main.py`: `GET /{slug}` → 302 to the destination.
2. Lookup order: Redis `link:{slug}` → on miss, PostgreSQL → store in Redis with a TTL.
   Cache a small JSON object (`link_id`, `organization_id`, `destination_url`, `is_active`, `expires_at`).
3. **Negative caching:** unknown slugs are cached as "not found" for a short TTL
   so repeated random requests do not hit PostgreSQL.
4. **Write-through invalidation:** when the api updates or deletes a link, it updates or deletes
   the Redis key immediately.
5. Inactive or expired links return a simple 404/410 page.
6. After responding, push a click event to Redis Stream `clicks` using a background task.
   Event fields: `event_id` (UUID), `link_id`, `organization_id`, `timestamp`, `ip`,
   `user_agent`, `referrer`, `accept_language`.
7. A simple benchmark script (e.g. with `httpx` or `hey`) measuring redirect latency
   with a warm and cold cache.

Acceptance criteria:
- [ ] Redirect works; a warm-cache redirect performs no database query (tested).
- [ ] Editing a link's destination takes effect immediately.
- [ ] Unknown slugs are negatively cached.
- [ ] Click events appear in the Redis Stream.
- [ ] Benchmark results are written to the Progress Log.

Learning focus: caching patterns, cache invalidation, async background work, measuring performance.

---

### Phase 3 — Event Worker and ClickHouse

**Goal:** click events flow from Redis Stream into ClickHouse, enriched and deduplicated.

Tasks:
1. Add ClickHouse to Docker Compose.
2. ClickHouse table `clicks` using `ReplacingMergeTree(event_id)` for deduplication,
   `ORDER BY (organization_id, link_id, timestamp)`, partitioned by month, with a TTL
   for data retention (e.g. 13 months).
3. `worker_main.py`: consume the stream with a consumer group, batch events
   (e.g. up to 1,000 events or 2 seconds), insert into ClickHouse, then acknowledge.
4. Enrichment:
   - Parse user agent → browser, OS, device type.
   - Geo lookup from IP → country, region, city (MaxMind GeoLite2 local database).
   - **Privacy:** store a salted hash of the IP, never the raw IP.
   - Bot flag: mark known bots and link-preview crawlers (Slackbot, WhatsApp,
     facebookexternalhit, Twitterbot, etc.) as `is_bot = 1`.
   - Parse UTM parameters from the destination URL.
5. Failed events go to a dead-letter stream after a few retries.
6. A materialized view for daily rollups (clicks per link per day).

Acceptance criteria:
- [ ] Clicking a link results in a row in ClickHouse within a few seconds.
- [ ] Replaying the same event does not double-count.
- [ ] Stopping and restarting the worker loses no events.
- [ ] Bot clicks are flagged.

Learning focus: event-driven design, at-least-once delivery, idempotency, columnar databases.

---

### Phase 4 — Analytics API

**Goal:** analytics endpoints the dashboard can use.

Tasks:
1. Analytics endpoints, all scoped by organization and with a date range:
   - Summary: total clicks, unique visitors (by hashed IP + user agent per day), bot share.
   - Time series: clicks per hour/day.
   - Breakdowns: countries, devices, browsers, OS, referrers, UTM source/medium/campaign.
2. Exclude bot clicks by default, with an option to include them.
3. Parameterized ClickHouse queries only. Never build SQL from raw user strings.
4. Response shapes designed for charts: time series as `[{ "bucket": ..., "clicks": ... }]`,
   breakdowns as `[{ "value": ..., "clicks": ..., "share": ... }]`.
5. A seed script that generates realistic fake clicks so the dashboard has data to show.

Acceptance criteria:
- [ ] A link created via the API, then clicked, shows up in the analytics endpoints.
- [ ] Endpoint results match the raw ClickHouse data (tested).
- [ ] Analytics endpoints cannot return another organization's data (tested).

Learning focus: analytics SQL, API design for dashboards.

---

### Phase 5 — Link Features

**Goal:** the features that make it a real link manager.

Tasks:
1. Tags and campaigns (campaign has a name and default UTM values; links can belong to one).
2. UTM builder endpoint that appends UTM parameters to a destination URL.
3. QR code generation for any link (PNG and SVG) using the `segno` library.
4. Password-protected links: redirect app serves a minimal password form;
   correct password sets a short-lived signed cookie, then redirects.
5. Bulk link creation from a CSV upload (with validation report per row).
6. Campaign analytics: compare campaigns side by side.

Acceptance criteria:
- [ ] All features work end to end and have tests.
- [ ] Password links cannot be bypassed by calling the redirect directly (tested).

Learning focus: feature design, file handling, signed tokens.

---

### Phase 6 — Real-Time Analytics (SSE)

**Goal:** the dashboard updates live when links are clicked.

Tasks:
1. The worker publishes lightweight updates to Redis pub/sub channel
   `live:{organization_id}` after each batch.
2. api endpoint `GET /analytics/live` streams Server-Sent Events for the user's organization.
3. Endpoint `GET /analytics/live/summary` returns clicks in the last few minutes (from Redis counters).
4. Do **not** poll ClickHouse for live data.

Acceptance criteria:
- [ ] Clicking a link produces an SSE event on an open connection within a few seconds.
- [ ] Users only receive events for their own organization (tested).

Learning focus: SSE, pub/sub, streaming responses.

---

### Phase 7 — AI Analytics Assistant

**Goal:** users ask questions in natural language and get answers based on real data.

Tasks:
1. Define a small set of tools using OpenAI function calling:
   `get_link_stats`, `compare_periods`, `get_top_breakdown` (dimension: country/device/referrer/...),
   `get_campaign_stats`, `list_links`.
2. Each tool has a strict Pydantic input schema. The server injects `organization_id`
   from the session — **the LLM can never choose or see another organization**.
3. Orchestrator loop: user question → model picks tools → validate → run query →
   return structured result → model explains. Limit the number of tool calls per question.
4. Chat endpoint that streams the answer back (SSE), plus endpoints to list past conversations.
5. System prompt instructs the model to only state numbers returned by tools.
6. Log every question, tool call, and token usage. Add a per-organization daily limit.

Acceptance criteria:
- [ ] "Why did clicks drop yesterday?" triggers a period comparison and a grounded answer.
- [ ] Tool calls with invalid parameters are rejected safely.
- [ ] Attempts to access other organizations' data via prompts fail (tested).

Learning focus: LLM tool use, prompt design, guarding AI against misuse.

---

### Phase 8 — Machine Learning

**Goal:** simple, explainable ML on top of the analytics data.

Tasks:
1. Anomaly detection: flag unusual hourly click counts per link
   (start with a rolling mean/std baseline, then try `IsolationForest`).
2. Bot scoring: train a simple classifier (logistic regression or random forest) on features
   like clicks per IP hash per minute, user agent traits, and time patterns.
3. Run ML jobs in the worker on a schedule, never inside api requests.
4. Store results in ClickHouse; expose them via an anomalies endpoint and to the AI
   assistant as a `get_anomalies` tool.

Acceptance criteria:
- [ ] Anomalies appear for synthetic traffic spikes (use a data-generator script).
- [ ] Model training and evaluation steps are documented in the Progress Log.

Learning focus: feature engineering, model evaluation, running ML in production-like settings.

---

### Phase 9 — Optional Extensions (Pick Any)

Only start these after Phases 0–8 are complete.

- API keys (hashed, scoped per organization) and a public REST API.
- Webhooks with signed payloads and retries.
- Conversion tracking: click ID appended to destinations + a conversion endpoint.
- Replace Redis Streams with Redpanda.
- Rewrite the redirect service in Go and compare benchmarks.
- Deploy to a VPS with a real domain behind Cloudflare.
- OpenTelemetry tracing + Prometheus + Grafana.

---

## 7. Progress Log

Update after every phase: date, what was built, benchmark numbers, lessons learned, open issues.

| Phase | Status | Date | Notes |
|---|---|---|---|
| 0 | Not started | | |
| 1 | Not started | | |
| 2 | Not started | | |
| 3 | Not started | | |
| 4 | Not started | | |
| 5 | Not started | | |
| 6 | Not started | | |
| 7 | Not started | | |
| 8 | Not started | | |
