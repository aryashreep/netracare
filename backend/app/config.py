from datetime import datetime

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Default assumes Docker Compose where host "postgres" resolves on the netracare network.
    # Local dev or tests override via DATABASE_URL env var (tests use sqlite://).
    database_url: str = "postgresql+psycopg://netracare:netracare@postgres:5432/netracare"
    data_dir: str = "/app/data/data-pack-01"
    data_dir_02: str = "/app/data/data-pack-02"
    clinic_now: str | None = None

    # LLM (Iter 2)
    anthropic_api_key: str | None = None
    llm_provider: str = "anthropic"
    llm_model_fast: str = "claude-haiku-4-5-20251001"
    llm_model_quality: str = "claude-sonnet-4-6"
    llm_timeout_fast: float = 5.0
    llm_timeout_quality: float = 8.0
    llm_max_tokens_red_flag: int = 2000
    llm_max_tokens_fact: int = 3000
    llm_max_tokens_summary: int = 4000

    # Ollama (local-first fallback provider, used when LLM_PROVIDER=ollama)
    # Default base URL is the Docker host-gateway address used by Colima and
    # Docker Desktop for Mac to reach a process listening on the host.
    ollama_base_url: str = "http://host.docker.internal:11434"
    # Default to gpt-oss:20b for both chains. In spike testing, qwen3:8b was
    # fast but returned schema-invalid red-flag output on ~1 in 4 calls, which
    # the fail-closed path rejects (safe, but unusable). gpt-oss:20b held up
    # 5/5 on the brief §09 samples with sub-5s warm latency.
    ollama_model_fast: str = "gpt-oss:20b"
    ollama_model_quality: str = "gpt-oss:20b"

    def frozen_now(self) -> datetime | None:
        return datetime.fromisoformat(self.clinic_now) if self.clinic_now else None


settings = Settings()
