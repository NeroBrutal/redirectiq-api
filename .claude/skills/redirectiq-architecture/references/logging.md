# Logging

Every error handled in `core/error_handlers.py` is logged once, with structured fields,
never with a bare `print()` or an f-string. This is what makes logs greppable/queryable
later (and is the whole "error portal" for local dev — see error-handling.md §4).

## Setup — `core/logging.py`

```python
# src/app/core/logging.py
import logging
import sys
import uuid
from contextvars import ContextVar

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from pythonjsonlogger import jsonlogger  # add to pyproject deps

_request_id_ctx: ContextVar[str] = ContextVar("request_id", default="-")


def configure_logging(level: int = logging.INFO) -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        jsonlogger.JsonFormatter("%(asctime)s %(name)s %(levelname)s %(message)s %(request_id)s")
    )
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
        request.state.request_id = request_id
        token = _request_id_ctx.set(request_id)
        try:
            response = await call_next(request)
        finally:
            _request_id_ctx.reset(token)
        response.headers["x-request-id"] = request_id
        return response
```

`request_id` ties a client-visible header to every log line for that request, including
the ones `error_handlers.py` writes — so a user-reported error can be found by its
request ID without guessing timestamps.

## Rules

- **Log at the boundary, not in the middle.** Services and repositories don't call
  `logger.error` themselves for expected failures — they raise, and the one handler in
  `error_handlers.py` logs it. Logging in three places for one error produces three log
  lines for one incident.
- **Structured fields, not string interpolation.** `logger.warning("link not found",
  extra={"link_id": id})`, not `logger.warning(f"link {id} not found")` — the former is
  queryable, the latter is grep-and-pray.
- **Never log secrets or full request bodies.** Tokens, passwords, API keys — redact
  before logging, even at debug level.
- **5xx vs 4xx:** unexpected exceptions and `AppError`s with `status_code >= 500` log at
  `error` (with `logger.exception` for a traceback); expected 4xx domain errors
  (not-found, validation, conflict) log at `warning` — they're not bugs, they're normal
  traffic, and paging on every 404 would drown real signal.
- **The `worker` process** logs the same way (`configure_logging()` at startup) but has
  no HTTP request to attach a request ID to — use the click event's own ID as the
  correlating field instead (`extra={"event_id": ...}`).
