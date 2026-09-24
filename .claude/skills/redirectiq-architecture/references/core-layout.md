# `core/` Layout: When a File Becomes a Package

`core/` holds cross-cutting infrastructure shared by every feature and all three
processes (`api`, `redirect`, `worker`): config, database, cache, logging, error
handling, health checks. It gets structured, not left as a pile of files, for the
same reason feature modules do (`layering.md`) — so a concern is always in exactly
one predictable place.

## The rule

One concern, one cohesive unit of code → **one file**. One concern that's actually
more than one cohesive piece (data + wiring, a client + its helpers) → **one
package**, with an `__init__.py` that re-exports the public API so every call site
imports from the package root, never a submodule:

```python
# always this:
from app.core.errors import AppError, register_error_handlers
from app.core.redis import get_redis

# never this:
from app.core.errors.exceptions import AppError
from app.core.redis.client import get_redis
```

This is Global Rule 10 (no abstraction until needed) applied to file layout: don't
pre-split `config.py` into a package on day one because it *might* grow — split
when a file is actually doing two distinct jobs, or is about to.

## Current layout

```
src/app/core/
├── config.py       # Pydantic Settings — one job, stays a file
├── db.py            # engine/session factory + Base + get_db — one job, stays a file
├── logging.py        # JSON logging + RequestIdMiddleware — one job, stays a file
├── health.py           # the shared /health router factory — one job, stays a file
├── errors/                # two jobs: the exception hierarchy, and registering it
│   ├── __init__.py          # re-exports AppError + subclasses + register_error_handlers
│   ├── exceptions.py         # AppError and its subclasses (NotFoundError, ConflictError, ...)
│   └── handlers.py            # register_error_handlers(app) — FastAPI wiring only
└── redis/                  # one job today (a client), but built to grow
    ├── __init__.py            # re-exports get_redis, check_redis_connection
    └── client.py               # get_redis() (lru_cached) + check_redis_connection()
```

Why `errors/` split into two files instead of one: `exceptions.py` is pure data —
no FastAPI import, importable from anywhere, including feature `exceptions.py`
files and even the `worker` process, which has no FastAPI app to register handlers
on. `handlers.py` is pure wiring — it imports FastAPI and Starlette and has no
reason to exist without an app to register on. Keeping them apart means a feature
module or the worker can depend on the hierarchy without pulling in a web
framework it doesn't use.

Why `redis/` is a package already, even with one file in it: Redis' role grows
fast per plan.md — cache reads today, rate limiting and idempotency keys in Phase
2, Streams (`XADD`/`XREADGROUP`) in Phase 3, pub/sub for SSE in Phase 6. Each of
those is its own cohesive piece of logic with its own tests, and none of them
belong bolted onto `client.py`, which owns exactly one thing: producing the
shared `Redis` instance. The package is the right shape from the start here
because the growth is already written into the roadmap, not speculative.

## Adding to an existing package

- New Redis capability (e.g. a rate limiter in Phase 2) → new file
  `core/redis/rate_limit.py`, its public function(s) re-exported from
  `core/redis/__init__.py`. Don't add it to `client.py`.
- New cross-cutting error type used by more than one feature → add it to
  `core/errors/exceptions.py` and re-export it. A error type used by exactly one
  feature belongs in that feature's own `exceptions.py` instead (see
  `error-handling.md`) — don't promote something to `core/` on its first use.

## When to promote a file to a package

Promote when a file starts doing two jobs that have different reasons to change
(business logic vs. framework wiring, like `errors/`) or when a roadmap phase is
about to add a second cohesive piece to what's currently one file (like `redis/`).
Don't promote speculatively — a `core/db/` package with a single `engine.py` file
inside it is worse than `core/db.py`, because it adds a layer of indirection for
no current benefit. Wait until `db.py` actually needs a second file (e.g. a
`session.py` separate from `engine.py`) before splitting it.
