"""Gateway configuration loaded from environment variables via Pydantic Settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings populated from environment variables.

    All secrets and tunables are loaded here. Never hard-code secrets.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ── Core ──────────────────────────────────────────────────────────
    gateway_secret_key: str = "change-me"
    gateway_debug: bool = False
    gateway_log_level: str = "INFO"

    # ── Database ──────────────────────────────────────────────────────
    database_url: str = "postgresql+asyncpg://gateway:gateway_secret@localhost:5432/ai_gateway"

    # ── Redis ─────────────────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"

    # ── LLM Providers ─────────────────────────────────────────────────
    openai_api_key: str = ""
    openai_api_base: str = "https://api.openai.com/v1"
    anthropic_api_key: str = ""
    anthropic_api_base: str = "https://api.anthropic.com"
    ollama_api_base: str = "http://localhost:11434"

    # ── Rate Limiting ─────────────────────────────────────────────────
    default_rate_limit_capacity: int = 60
    default_rate_limit_refill_rate: float = 1.0
    default_daily_token_limit: int = 1_000_000

    # ── Cache ─────────────────────────────────────────────────────────
    cache_default_ttl: int = 3600
    cache_enabled: bool = True

    # ── Circuit Breaker ───────────────────────────────────────────────
    cb_failure_threshold: int = 5
    cb_recovery_timeout: int = 30
    cb_half_open_max_requests: int = 3


settings = Settings()
