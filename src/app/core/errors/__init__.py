"""Public surface of the errors package: hierarchy (exceptions.py) + wiring (handlers.py).

Call sites import from here — `from app.core.errors import AppError,
register_error_handlers` — and never care whether that's one file or several.
Feature-level exceptions.py modules subclass the hierarchy from here (see
.claude/skills/redirectiq-architecture/references/error-handling.md); they never
import from app.core.errors.exceptions or app.core.errors.handlers directly.
"""

from app.core.errors.exceptions import (
    AppError,
    ConflictError,
    ForbiddenError,
    NotFoundError,
    RateLimitedError,
    UnauthorizedError,
    ValidationAppError,
)
from app.core.errors.handlers import register_error_handlers

__all__ = [
    "AppError",
    "ConflictError",
    "ForbiddenError",
    "NotFoundError",
    "RateLimitedError",
    "UnauthorizedError",
    "ValidationAppError",
    "register_error_handlers",
]
