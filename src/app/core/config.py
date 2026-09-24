"""Application configuration, loaded once from the environment.

Every setting the app needs comes through this Settings object — nothing reads
os.environ directly anywhere else (Global Rule 3 in plan.md). This keeps config
centrally documented (see .env.example) and easy to override in tests.
"""

from functools import lru_cache
from typing import Annotated

from pydantic import Field, PostgresDsn, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    environment: str = "local"

    # --- PostgreSQL ---
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "redirectiq"
    postgres_password: str = "redirectiq"
    postgres_db: str = "redirectiq"
    database_url: str | None = None

    # --- Redis ---
    redis_url: str = "redis://localhost:6379/0"

    # --- CORS (Global Rule 12): explicit allow-list, never "*" ---
    # NoDecode: read as a plain string (comma-separated) instead of pydantic-settings'
    # default JSON-decode-then-validate for list fields, which rejects "a,b" outright.
    allowed_origins: Annotated[list[str], NoDecode] = Field(default_factory=list)

    # --- api process ---
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # --- redirect process ---
    redirect_host: str = "0.0.0.0"
    redirect_port: int = 8001

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @property
    def sqlalchemy_database_url(self) -> str:
        """The async SQLAlchemy URL, built from parts unless DATABASE_URL is set."""
        if self.database_url:
            return self.database_url
        return str(
            PostgresDsn.build(
                scheme="postgresql+asyncpg",
                username=self.postgres_user,
                password=self.postgres_password,
                host=self.postgres_host,
                port=self.postgres_port,
                path=self.postgres_db,
            )
        )


@lru_cache
def get_settings() -> Settings:
    """Cached so Settings() — which reads .env/os.environ — runs once per process."""
    return Settings()
