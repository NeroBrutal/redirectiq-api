# Error Handling

Goal: every error the API returns has a stable machine-readable `code`, a human message,
the right HTTP status, and gets logged once with enough context to debug it — without any
router or service writing `try/except HTTPException` by hand.

## 1. The exception hierarchy — `src/app/core/errors.py`

One base class. Every domain error subclasses it and declares its own HTTP status + code.

```python
# src/app/core/errors.py
from http import HTTPStatus


class AppError(Exception):
    """Base for every error the app raises on purpose.

    Anything NOT subclassing this is treated as an unhandled bug by the global
    handler (logged with a stack trace, returned as a generic 500 — see below).
    """

    status_code: int = HTTPStatus.INTERNAL_SERVER_ERROR
    code: str = "internal_error"

    def __init__(self, message: str, *, code: str | None = None, **context: object) -> None:
        self.message = message
        self.code = code or self.code
        self.context = context  # extra fields for logs only, never sent to the client
        super().__init__(message)


class NotFoundError(AppError):
    status_code = HTTPStatus.NOT_FOUND
    code = "not_found"


class ValidationAppError(AppError):
    """For business-rule validation that Pydantic can't express (e.g. slug taken)."""

    status_code = HTTPStatus.UNPROCESSABLE_ENTITY
    code = "validation_error"


class ConflictError(AppError):
    status_code = HTTPStatus.CONFLICT
    code = "conflict"


class UnauthorizedError(AppError):
    status_code = HTTPStatus.UNAUTHORIZED
    code = "unauthorized"


class ForbiddenError(AppError):
    status_code = HTTPStatus.FORBIDDEN
    code = "forbidden"


class RateLimitedError(AppError):
    status_code = HTTPStatus.TOO_MANY_REQUESTS
    code = "rate_limited"
```

Each feature adds **specific** errors in its own `exceptions.py`, subclassing these —
never raise the base classes directly from a service:

```python
# src/app/links/exceptions.py
from app.core.errors import ConflictError, NotFoundError


class LinkNotFoundError(NotFoundError):
    code = "link_not_found"

    def __init__(self, link_id: str) -> None:
        super().__init__(f"Link {link_id} was not found.", link_id=link_id)


class SlugAlreadyTakenError(ConflictError):
    code = "link_slug_taken"

    def __init__(self, slug: str) -> None:
        super().__init__(f"Slug '{slug}' is already in use.", slug=slug)
```

Error `code` values follow `<domain>_<reason>` — this is the string the frontend
switches on, so it must never change once shipped. The `message` can change freely.

## 2. Centralized handlers — `src/app/core/error_handlers.py`

Register once, in every entrypoint (`api_main.py`, `redirect_main.py`; `worker_main.py`
uses the logging half only, see below). Routers and services never catch these — they
just raise.

```python
# src/app/core/error_handlers.py
import logging
from http import HTTPStatus

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.errors import AppError

logger = logging.getLogger("app.errors")


def _error_response(status_code: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code, content={"error": {"code": code, "message": message}}
    )


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        log = logger.warning if exc.status_code < 500 else logger.error
        log(
            "request_failed",
            extra={
                "error_code": exc.code,
                "status_code": exc.status_code,
                "path": request.url.path,
                "request_id": getattr(request.state, "request_id", None),
                **exc.context,
            },
        )
        return _error_response(exc.status_code, exc.code, exc.message)

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        # Pydantic/FastAPI input validation — same envelope as domain errors.
        return _error_response(status.HTTP_422_UNPROCESSABLE_ENTITY, "invalid_request", str(exc))

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        # Anything not an AppError is a bug, not an expected outcome: log full
        # traceback, never leak internals to the client.
        logger.exception(
            "unhandled_exception",
            extra={
                "path": request.url.path,
                "request_id": getattr(request.state, "request_id", None),
            },
        )
        return _error_response(
            HTTPStatus.INTERNAL_SERVER_ERROR, "internal_error", "Something went wrong."
        )
```

Wire it up:

```python
# src/app/api_main.py
from fastapi import FastAPI
from app.core.error_handlers import register_error_handlers
from app.core.logging import RequestIdMiddleware, configure_logging

configure_logging()
app = FastAPI(title="RedirectIQ API")
app.add_middleware(RequestIdMiddleware)
register_error_handlers(app)
```

## 3. Raising errors — services only

```python
# src/app/links/service.py
from app.links.exceptions import LinkNotFoundError, SlugAlreadyTakenError
from app.links.repository import LinkRepository


class LinkService:
    def __init__(self, repo: LinkRepository) -> None:
        self._repo = repo

    async def get_link(self, org_id: str, link_id: str):
        link = await self._repo.get(org_id=org_id, link_id=link_id)
        if link is None:
            raise LinkNotFoundError(link_id)
        return link

    async def create_link(self, org_id: str, slug: str, destination: str):
        if await self._repo.slug_exists(org_id=org_id, slug=slug):
            raise SlugAlreadyTakenError(slug)
        return await self._repo.create(org_id=org_id, slug=slug, destination=destination)
```

The router does nothing but call the service — no `try/except` needed, the global
handler converts the raised error into the right JSON response:

```python
# src/app/links/router.py
@router.get("/{link_id}", response_model=LinkOut, operation_id="get_link", tags=["links"])
async def get_link(
    link_id: str, service: LinkService = Depends(get_link_service), org=Depends(get_current_org)
):
    return await service.get_link(org.id, link_id)
```

## 4. The "error login portal" question

If what you actually meant is an **admin/ops view of errors** (a place to see what's
failing in production), that isn't a route to hand-build — it's what the structured
logs above are *for*. Options, in order of effort:

- **Cheapest, works from day one:** every `AppError` and unhandled exception is already
  logged as structured JSON with `error_code`, `status_code`, `path`, `request_id`, and
  org context (§2 above). Ship logs to stdout in Docker Compose and `docker compose logs
  -f api` is your error portal locally.
- **Phase 9 candidate:** OpenTelemetry + a log sink (already listed in plan.md's optional
  extensions) gives you a real searchable dashboard without building one yourself.
- Do **not** build a custom "errors" table/endpoint/UI before Phase 9 — it's exactly the
  kind of premature abstraction plan.md's Global Rule 10 says to avoid, and a log
  aggregator does it better.
