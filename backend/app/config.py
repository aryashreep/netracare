from datetime import datetime

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "sqlite:////app/data/netracare.db"
    data_dir: str = "/app/data/data-pack-01"
    clinic_now: str | None = None

    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-sonnet-4-6"

    def frozen_now(self) -> datetime | None:
        return datetime.fromisoformat(self.clinic_now) if self.clinic_now else None


settings = Settings()
