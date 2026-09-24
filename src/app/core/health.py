"""Shared /health route factory.

Both api_main.py and redirect_main.py expose GET /health checking DB and Redis
(Phase 0, task 5). One implementation, reused by both entrypoints instead of
duplicating the same three lines twice (Global Rule 10).
"""

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from app.core.db import check_db_connection
from app.core.redis import check_redis_connection


def build_health_router() -> APIRouter:
    router = APIRouter(tags=["health"])

    @router.get("/health", operation_id="get_health")
    async def health() -> JSONResponse:
        db_ok, redis_ok = await check_db_connection(), await check_redis_connection()
        healthy = db_ok and redis_ok
        body = {"status": "ok" if healthy else "degraded", "db": db_ok, "redis": redis_ok}
        code = status.HTTP_200_OK if healthy else status.HTTP_503_SERVICE_UNAVAILABLE
        return JSONResponse(status_code=code, content=body)

    return router
