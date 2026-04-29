from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    anthropic_api_key: str = Field(..., alias="ANTHROPIC_API_KEY")
    voyage_api_key: str | None = Field(None, alias="VOYAGE_API_KEY")
    openai_api_key: str | None = Field(None, alias="OPENAI_API_KEY")

    database_url: str = Field(..., alias="DATABASE_URL")

    default_tenant_id: str = Field("tenant_acme", alias="DEFAULT_TENANT_ID")
    default_user_id: str = Field("alice", alias="DEFAULT_USER_ID")

    log_level: str = Field("INFO", alias="LOG_LEVEL")

    model_reasoning: str = "claude-sonnet-4-6"
    model_router: str = "claude-haiku-4-5-20251001"
    embedding_dim: int = 1024
    embedding_model: str = "voyage-3"

    max_react_iterations: int = 4
    max_session_tokens: int = 50_000

    static_dir: Path = Path(__file__).parent.parent / "static"

    def has_embedding_provider(self) -> bool:
        return bool(self.voyage_api_key or self.openai_api_key)


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    if not s.has_embedding_provider():
        raise RuntimeError(
            "No embedding provider configured. Set VOYAGE_API_KEY or OPENAI_API_KEY. "
            "See .env.example for the full list."
        )
    return s
