from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str
    sql_echo: bool = False
    cors_allow_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    edge_api_key: str
    dashboard_access_token: str
    telemetry_events_rate_limit: str = "100/minute"


@lru_cache
def get_settings() -> Settings:
    return Settings()  # pyright: ignore[reportCallIssue]  # values are supplied via env/.env at runtime
