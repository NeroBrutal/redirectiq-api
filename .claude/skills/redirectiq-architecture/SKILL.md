---
name: redirectiq-architecture
description: Use whenever writing, extending, or reviewing backend code in this repo (redirectiq-api) — adding an endpoint, feature module, exception, dependency, helper, or middleware. Enforces the project's layered architecture (router/service/repository), the custom exception hierarchy with centralized error handling + logging, and DRY/reusable-code conventions. Load this before scaffolding a new feature folder, raising or catching an error, or touching core/. Complements plan.md, which owns the phase roadmap — this skill owns *how* code is structured within any phase.
---

# RedirectIQ Backend Architecture

This skill is the coding standard for `redirectiq-api`. `plan.md` says **what** to build and
**when** (phase by phase). This skill says **how** to structure the code so it stays
consistent, testable, and reusable across all three processes (`api`, `redirect`, `worker`).

Read the relevant reference file before doing the matching work — don't guess the pattern
from scratch each time:

| Doing this | Read |
|---|---|
| Adding/changing a feature module (router, service, repository) | `references/layering.md` |
| Raising, catching, or adding a new error type | `references/error-handling.md` |
| Adding a shared dependency, base class, or utility | `references/reusable-code.md` |
| Setting up logging or reviewing what gets logged | `references/logging.md` |

## Non-negotiables (from plan.md, restated so they're not missed)

- Every business table/query is scoped by `organization_id`, taken from the authenticated
  session — never from request input.
- The redirect app (`redirect_main.py`) never writes to Postgres/ClickHouse in the request
  path. Reads only (Redis, then Postgres on miss), then pushes a click event.
- All input validated via Pydantic v2 schemas. All config via `core/config.py` Settings.
- All errors return `{ "error": { "code": "...", "message": "..." } }` — see
  `references/error-handling.md` for the mechanism that guarantees this.
- Every route lives under `/v1/`, has an explicit `response_model`, a unique `operation_id`,
  and a tag.
- No abstraction until it's needed twice. Don't pre-build generic layers for a single caller.

## The shape of a feature module

Every feature (`links`, `organizations`, `analytics`, ...) is a folder under `src/app/`
with the same five files, each with one job:

```
src/app/links/
├── router.py        # HTTP only: path, status codes, calls one service method, DI via Depends
├── service.py        # business logic: orchestrates repositories, raises domain errors
├── repository.py     # DB access only: SQLAlchemy queries, no business rules
├── schemas.py         # Pydantic request/response models for this feature
└── exceptions.py       # this feature's error types, subclassing core.errors.AppError
```

Routers never touch SQLAlchemy. Services never touch `Request`/`Response`. Repositories
never raise HTTP errors — they raise nothing domain-specific or return `None`, and the
service decides what that means. This one-way dependency (`router → service → repository`)
is what keeps each layer independently testable.

## Before you write an endpoint, check

1. Does this logic belong in a router, service, or repository? (Rule above.)
2. Is there already a domain exception for this failure, or do I add one to
   `exceptions.py` per `references/error-handling.md`?
3. Is there a shared dependency for this (`get_db`, `get_current_org`, pagination) in
   `core/dependencies.py`, or am I about to duplicate one? Check
   `references/reusable-code.md` first.
4. Does the response model exist in `schemas.py`, with an `operation_id` and tag set on
   the route per plan.md rule 11?
