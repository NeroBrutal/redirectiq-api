"""Centralized exception -> JSON response mapping.

Registered once per FastAPI app (api_main.py, redirect_main.py). Routers and
services never catch these themselves — they raise an AppError subclass and this
is the only place that converts it into the response shape from plan.md Global
Rule 9: {"error": {"code": ..., "message": ...}}.
"""

import logging
from http import HTTPStatus

from fastapi import FastAPI, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.requests import Request

from app.core.errors import AppError

logger = logging.getLogger("app.errors")

# Routing-level failures (unmatched route, wrong method, ...) raise Starlette's
# plain HTTPException before any of our code runs, so they need their own code
# mapping to still come back in the AppError envelope (Global Rule 9 has no
# exception for these).
_HTTP_EXCEPTION_CODES = {
    status.HTTP_400_BAD_REQUEST: "bad_request",
    status.HTTP_401_UNAUTHORIZED: "unauthorized",
    status.HTTP_403_FORBIDDEN: "forbidden",
    status.HTTP_404_NOT_FOUND: "not_found",
    status.HTTP_405_METHOD_NOT_ALLOWED: "method_not_allowed",
    status.HTTP_409_CONFLICT: "conflict",
    status.HTTP_429_TOO_MANY_REQUESTS: "rate_limited",
}


def _error_response(status_code: int, code: str, message: str) -> JSONResponse:
    body = {"error": {"code": code, "message": message}}
    return JSONResponse(status_code=status_code, content=body)


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

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = _HTTP_EXCEPTION_CODES.get(exc.status_code, f"http_{exc.status_code}")
        message = exc.detail if isinstance(exc.detail, str) else "Request failed."
        return _error_response(exc.status_code, code, message)

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return _error_response(status.HTTP_422_UNPROCESSABLE_ENTITY, "invalid_request", str(exc))

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        request_id = getattr(request.state, "request_id", None)
        logger.exception(
            "unhandled_exception",
            extra={"path": request.url.path, "request_id": request_id},
        )
        return _error_response(
            HTTPStatus.INTERNAL_SERVER_ERROR, "internal_error", "Something went wrong."
        )
