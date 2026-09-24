# RedirectIQ API

**Backend for RedirectIQ: fast link redirects, event-driven analytics, and AI-powered insights.**

This repository contains the RedirectIQ backend: the main REST API, the redirect service, and the analytics worker. The dashboard lives in **[redirectiq-web](https://github.com/<your-username>/redirectiq-web)**.

> 🚧 **Work in progress.** A learning project built phase by phase to explore backend architecture, caching, event-driven systems, analytics databases, and applied AI. See [plan.md](plan.md) for the roadmap.

---

## ✨ Features

**Link management**
- Short links with random or custom slugs
- Expiration, password protection, tags, and campaigns
- UTM builder, QR codes, and bulk creation from CSV

**Analytics**
- Clicks, unique visitors, and time series
- Breakdowns by country, device, browser, OS, referrer, and UTM
- Bot and link-preview crawler filtering
- Real-time updates via Server-Sent Events

**AI & ML**
- Natural-language analytics questions answered from real data
- LLM access only through validated, tenant-scoped tools
- Anomaly detection and bot scoring

---

## 🏗️ Architecture

Three Python processes share one codebase:

| Service | Role |
|---|---|
| **api** | Auth, organizations, links, analytics endpoints, AI assistant |
| **redirect** | Resolves short links and emits click events. Nothing else. |
| **worker** | Consumes click events, enriches them, writes to ClickHouse |

```text
redirectiq-web ──> api ──> PostgreSQL
                    │ └──> Redis
                    └────> ClickHouse

Visitor ──> redirect ──> Redis ──(miss)──> PostgreSQL
               │
               ├── 302 redirect returned immediately
               └── click event ──> Redis Stream ──> worker ──> ClickHouse
```

> **Redirect fast, collect events asynchronously, analyze at scale, and let AI explain trusted data.**

---

## 🧰 Tech Stack

| Area | Technology |
|---|---|
| Language | Python 3.12+ |
| Framework | FastAPI, Pydantic v2 |
| Database access | SQLAlchemy 2.x (async), Alembic, asyncpg |
| Databases | PostgreSQL, ClickHouse, Redis |
| AI / ML | OpenAI API, scikit-learn, Polars |
| Tooling | uv, ruff, pytest, Docker Compose |

---

## 🚀 Getting Started

> Full setup instructions will be added once Phase 0 is complete.

Requirements: Python 3.12+, [uv](https://github.com/astral-sh/uv), Docker & Docker Compose.

```bash
git clone https://github.com/<your-username>/redirectiq-api.git
cd redirectiq-api
cp .env.example .env
docker compose up -d
uv sync
uv run alembic upgrade head
uv run fastapi dev src/app/api_main.py
```

| Service | Local URL |
|---|---|
| API | http://localhost:8000 |
| API docs (Swagger) | http://localhost:8000/docs |
| Redirect | http://localhost:8001 |

---

## 📄 API Contract

The API publishes an OpenAPI schema at `/openapi.json`. The frontend generates its TypeScript types from this schema, so the two repos stay in sync without copying types by hand.

---

## 📁 Project Structure

```text
redirectiq-api/
├── src/app/
│   ├── core/            # config, db, redis, security
│   ├── auth/
│   ├── organizations/
│   ├── links/
│   ├── analytics/
│   ├── ai/
│   ├── ml/
│   ├── api_main.py      # entrypoint: api
│   ├── redirect_main.py # entrypoint: redirect
│   └── worker_main.py   # entrypoint: worker
├── migrations/
├── tests/
├── docker-compose.yml
├── plan.md
└── pyproject.toml
```

---

## 🗺️ Roadmap

| Phase | Focus | Status |
|---|---|---|
| 0 | Project setup | ⏳ Planned |
| 1 | Users, organizations, links | ⏳ Planned |
| 2 | Redirect service & Redis caching | ⏳ Planned |
| 3 | Event worker & ClickHouse | ⏳ Planned |
| 4 | Analytics API | ⏳ Planned |
| 5 | Campaigns, UTM, QR codes, password links | ⏳ Planned |
| 6 | Real-time analytics (SSE) | ⏳ Planned |
| 7 | AI analytics assistant | ⏳ Planned |
| 8 | Anomaly detection & bot scoring | ⏳ Planned |
| 9 | Optional extensions | ⏳ Planned |

---

## 🔗 Related

- **[redirectiq-web](https://github.com/<your-username>/redirectiq-web)**: the RedirectIQ dashboard

## 📄 License

MIT