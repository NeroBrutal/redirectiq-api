"""Base exception hierarchy for the app.

Every error raised on purpose subclasses AppError. Anything else is treated as an
unhandled bug by the global handler in error_handlers.py (logged with a traceback,
returned as a generic 500). Feature modules add specific errors in their own
exceptions.py, subclassing the ones below — never raise these base classes directly.
See .claude/skills/redirectiq-architecture/references/error-handling.md.
"""

from http import HTTPStatus


class AppError(Exception):
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
    """Business-rule validation that Pydantic schemas can't express on their own."""

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
