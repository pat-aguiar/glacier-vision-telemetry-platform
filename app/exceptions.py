from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
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


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    logger.warning("app_error code=%s path=%s", exc.error_code, request.url.path)
    return JSONResponse(
        status_code=exc.status_code,
        content=_envelope(exc.error_code, exc.message, exc.details),
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
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


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, app_error_handler)  # pyright: ignore[reportArgumentType]
    app.add_exception_handler(
        RequestValidationError,
        validation_exception_handler,  # pyright: ignore[reportArgumentType]
    )
