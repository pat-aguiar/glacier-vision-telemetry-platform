from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.exceptions import register_exception_handlers
from app.api.v1.router import api_router
from app.middleware import BodySizeLimitMiddleware

STATIC_DIR = Path(__file__).parent / "static"


def _openapi_without_422(app: FastAPI):
    """Drop FastAPI's auto-added 422 response from every operation.

    The global RequestValidationError handler always normalizes validation
    failures to 400, so the app never actually emits a 422 -- leaving it in
    the schema would show Swagger consumers a status code the API doesn't use.
    """

    def custom_openapi() -> dict:
        if app.openapi_schema:
            return app.openapi_schema
        schema = get_openapi(title=app.title, version=app.version, routes=app.routes)
        for path in schema.get("paths", {}).values():
            for operation in path.values():
                operation.get("responses", {}).pop("422", None)
        app.openapi_schema = schema
        return app.openapi_schema

    return custom_openapi


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Glacier Vision Telemetry Platform")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    # Added after CORS so it wraps outermost -- oversized bodies get
    # rejected before any other middleware or app logic runs.
    app.add_middleware(BodySizeLimitMiddleware)

    register_exception_handlers(app)
    app.include_router(api_router, prefix="/api/v1")
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    app.openapi = _openapi_without_422(app)

    return app


app = create_app()
