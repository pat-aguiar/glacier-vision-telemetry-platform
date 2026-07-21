from fastapi import APIRouter

from app.api.v1 import telemetry, telemetry_stream

api_router = APIRouter()
api_router.include_router(telemetry.router, prefix="/telemetry", tags=["telemetry"])
api_router.include_router(telemetry_stream.router, prefix="/telemetry", tags=["telemetry-stream"])
