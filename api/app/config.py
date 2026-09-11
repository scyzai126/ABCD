"""Runtime configuration.

Credentials come from the project-root `.env` that already drives docker-compose
(`ABCD_APP_PASSWORD`); nothing new needs to be provisioned to run the API locally.
"""
from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env", "../../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Either set DATABASE_URL outright, or let it be assembled from the parts below.
    database_url: str = ""

    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "abcd"
    db_user: str = "abcd_app"
    abcd_app_password: str = ""

    pool_min_size: int = 1
    pool_max_size: int = 10
    statement_timeout_ms: int = 15_000

    # The Vite dev server; override in deployment.
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    @property
    def dsn(self) -> str:
        if self.database_url:
            return self.database_url
        return (
            f"postgresql://{self.db_user}:{self.abcd_app_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    @property
    def cors_origin_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
