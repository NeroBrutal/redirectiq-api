"""Entrypoint: the main API process (auth, organizations, links, analytics, AI).

Run locally with: uv run fastapi dev src/app/api_main.py
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.error_handlers import register_error_handlers
from app.core.health import build_health_router
from app.core.logging import RequestIdMiddleware, configure_logging

configure_logging()

settings = get_settings()

app = FastAPI(title="RedirectIQ API")

# Global Rule 12: explicit allow-list from settings, never "*" with credentials.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestIdMiddleware)

register_error_handlers(app)

app.include_router(build_health_router())

# Feature routers are added here as they're built, e.g.:
# from app.links.router import router as links_router
# app.include_router(links_router)
