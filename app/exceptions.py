from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from sqlalchemy.exc import IntegrityError

logger = logging.getLogger(__name__)

FOREIGN_KEY_VIOLATION = "23503"
UNIQUE_VIOLATION = "23505"


class AppError(Exception):
    """Base class for all application-raised errors."""

    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_code: str = "internal_error"

    def __init__(self, message: str, *, details: Any = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details


class ValidationError(AppError):
    status_code = status.HTTP_400_BAD_REQUEST
    error_code = "validation_error"


class NotFoundError(AppError):
    status_code = status.HTTP_404_NOT_FOUND
    error_code = "not_found"


class DeviceNotFoundError(AppError):
    status_code = status.HTTP_400_BAD_REQUEST
    error_code = "device_not_found"

    def __init__(self, device_id: str) -> None:
        super().__init__(f"No device found with device_id '{device_id}'.")


class SortingEventNotFoundError(NotFoundError):
    error_code = "sorting_event_not_found"

    def __init__(self, event_id: str) -> None:
        super().__init__(f"No sorting event found with id '{event_id}'.")


class ConflictError(AppError):
    status_code = status.HTTP_409_CONFLICT
    error_code = "conflict"


class UnauthorizedError(AppError):
    status_code = status.HTTP_401_UNAUTHORIZED
    error_code = "unauthorized"


class InvalidApiKeyError(UnauthorizedError):
    error_code = "invalid_api_key"

    def __init__(self) -> None:
        super().__init__("A valid X-API-Key header is required.")


class InvalidDashboardTokenError(UnauthorizedError):
    error_code = "invalid_dashboard_token"

    def __init__(self) -> None:
        super().__init__("A valid dashboard access token is required.")


class ForbiddenError(AppError):
    status_code = status.HTTP_403_FORBIDDEN
    error_code = "forbidden"


def translate_integrity_error(exc: IntegrityError, *, device_id: str) -> AppError:
    sqlstate = getattr(exc.orig, "sqlstate", None)
    if sqlstate == FOREIGN_KEY_VIOLATION:
        return DeviceNotFoundError(device_id)
    return AppError("A database integrity error occurred.")


def _envelope(code: str, message: str, details: Any = None) -> dict[str, Any]:
    return {"error": {"code": code, "message": message, "details": details}}


async def app_error_handler(request: Request, exc: AppError | Exception) -> JSONResponse:
    assert isinstance(exc, AppError)

    logger.warning("app_error code=%s path=%s", exc.error_code, request.url.path)
    return JSONResponse(
        status_code=exc.status_code,
        content=_envelope(exc.error_code, exc.message, exc.details),
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError | Exception
) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)


    details = [
        {"field": ".".join(str(p) for p in err["loc"] if p != "body"), "message": err["msg"]}
        for err in exc.errors()
    ]
    logger.warning("validation_error path=%s details=%s", request.url.path, details)
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=_envelope(
            "validation_error",
            "The request payload failed validation.",
            details,
        ),
    )


async def rate_limit_exceeded_handler(
    request: Request, exc: RateLimitExceeded | Exception
) -> JSONResponse:
    assert isinstance(exc, RateLimitExceeded)

    logger.warning("rate_limit_exceeded path=%s", request.url.path)
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content=_envelope(
            "rate_limit_exceeded",
            f"Rate limit exceeded: {exc.detail}",
        ),
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(
        RequestValidationError,
        validation_exception_handler,
    )
    app.add_exception_handler(
        RateLimitExceeded,
        rate_limit_exceeded_handler,
    )
