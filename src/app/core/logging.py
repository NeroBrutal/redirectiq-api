"""Structured JSON logging + request-ID correlation.

Every log line is JSON with a request_id field, so one incident's logs can be found
by the x-request-id header returned to the client. See
.claude/skills/redirectiq-architecture/references/logging.md.
"""

import logging
import sys
import uuid
from collections.abc import Awaitable, Callable

from pythonjsonlogger import json as jsonlogger
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


def configure_logging(level: int = logging.INFO) -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(jsonlogger.JsonFormatter("%(asctime)s %(name)s %(levelname)s %(message)s"))
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Assigns/propagates a request ID and stashes it on request.state for handlers
    and logs to read (see core/errors/handlers.py)."""

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["x-request-id"] = request_id
        return response
