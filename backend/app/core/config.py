import json
from functools import lru_cache
from typing import Annotated

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

_INSECURE_DEFAULT = "change-me-in-env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "AI Career Agent"
    app_version: str = "1.0.0"
    environment: str = "development"  # development | test | production
    debug: bool = False
    log_level: str = ""  # empty = DEBUG if debug else INFO
    docs_enabled: bool = True  # set DOCS_ENABLED=false to hide /docs in production
    allowed_hosts: Annotated[list[str], NoDecode] = ["*"]  # Host header allow-list

    # Uploads
    upload_dir: str = "uploads/resumes"
    max_upload_mb: int = 5

    # Global per-IP API limit (requests/minute, 0 = off). In-memory: per process.
    api_rate_limit_per_minute: int = 240

    database_url: str = "sqlite:///./career_agent.db"
    redis_url: str = "redis://localhost:6379/0"

    jwt_secret: str = _INSECURE_DEFAULT
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 15
    refresh_token_days: int = 14

    # NoDecode: accept plain "a,b" from the environment instead of requiring a JSON list.
    cors_origins: Annotated[list[str], NoDecode] = ["http://localhost:5173"]

    # Rate limits (requests per window, per client IP + route)
    auth_rate_limit_attempts: int = 10
    auth_rate_limit_window_seconds: int = 60

    # Tracking (Phase 8)
    default_follow_up_days: int = 7
    ghosted_after_days: int = 30

    # AI (used from Phase 3 onward; configured now so .env is stable)
    groq_api_key: str = ""
    openai_api_key: str = ""
    llm_timeout_seconds: float = 30.0
    # Phase 9: interviews work without any key (rule-based); with a key the LLM
    # adds tailored questions and richer feedback. Flip off to force rule-based.
    interview_use_llm: bool = True
    llm_rate_limit_per_minute: int = 30
    llm_model: str = "groq:llama-3.3-70b-versatile"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"

    @field_validator("cors_origins", "allowed_hosts", mode="before")
    @classmethod
    def _parse_origins(cls, v: object) -> object:
        if isinstance(v, str):
            v = v.strip()
            if v.startswith("["):
                return json.loads(v)
            return [o.strip() for o in v.split(",") if o.strip()]
        return v

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    def validate_for_runtime(self) -> None:
        """Refuse to start in production with an unsafe configuration."""
        if not self.is_production:
            return
        if self.jwt_secret == _INSECURE_DEFAULT or len(self.jwt_secret) < 32:
            raise RuntimeError("JWT_SECRET must be set to a strong value (>=32 chars) in production")
        if self.database_url.startswith("sqlite"):
            raise RuntimeError("DATABASE_URL must point at PostgreSQL in production (SQLite is for dev/tests)")
        if self.debug:
            raise RuntimeError("DEBUG must be false in production")
        if "*" in self.cors_origins:
            raise RuntimeError("CORS_ORIGINS must list explicit origins in production")


@lru_cache
def get_settings() -> Settings:
    return Settings()
