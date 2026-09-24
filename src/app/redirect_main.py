"""Entrypoint: the redirect process.

Resolves short links and emits click events — nothing else. Never writes to
Postgres/ClickHouse in the request path (Global Rule 2).

Run locally with: uv run fastapi dev src/app/redirect_main.py --port 8001
"""

from fastapi import FastAPI

from app.core.errors import register_error_handlers
from app.core.health import build_health_router
from app.core.logging import RequestIdMiddleware, configure_logging

configure_logging()

app = FastAPI(title="RedirectIQ Redirect Service")

app.add_middleware(RequestIdMiddleware)

register_error_handlers(app)

app.include_router(build_health_router())

# The slug-resolution route is added in Phase 2, e.g.:
# from app.links.redirect_router import router as redirect_router
# app.include_router(redirect_router)
