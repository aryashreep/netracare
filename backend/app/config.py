from datetime import datetime

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Default assumes Docker Compose where host "postgres" resolves on the netracare network.
    # Local dev or tests override via DATABASE_URL env var (tests use sqlite://).
    database_url: str = "postgresql+psycopg://netracare:netracare@postgres:5432/netracare"
    data_dir: str = "/app/data/data-pack-01"
    clinic_now: str | None = None

    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-sonnet-4-6"

    def frozen_now(self) -> datetime | None:
        return datetime.fromisoformat(self.clinic_now) if self.clinic_now else None


settings = Settings()
