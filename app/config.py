from functools import lru_cache

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.domain.value_objects import AiMode


def normalize_database_url(url: str) -> str:
    """Railway/Heroku often provide postgres:// — convert for SQLAlchemy async."""
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+asyncpg://", 1)
    if url.startswith("postgresql://") and "+asyncpg" not in url and "+psycopg" not in url:
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


def database_url_for_alembic(async_url: str) -> str:
    """Alembic uses sync driver."""
    url = normalize_database_url(async_url)
    if url.startswith("sqlite+aiosqlite"):
        return url.replace("sqlite+aiosqlite", "sqlite", 1)
    if url.startswith("postgresql+asyncpg"):
        return url.replace("postgresql+asyncpg", "postgresql+psycopg2", 1)
    return url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    bot_token: str = Field(alias="BOT_TOKEN")
    telegram_api_id: int = Field(default=2040, alias="TELEGRAM_API_ID")
    telegram_api_hash: str = Field(
        default="b18441a1ff607e10a989891a5462e627",
        alias="TELEGRAM_API_HASH",
    )
    admin_ids: str = Field(alias="ADMIN_IDS")
    database_url: str = Field(default="sqlite+aiosqlite:///./app.db", alias="DATABASE_URL")
    sessions_dir: str = Field(default="./sessions", alias="SESSIONS_DIR")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    log_json: bool = Field(default=True, alias="LOG_JSON")
    floodwait_buffer_sec: int = Field(default=3, alias="FLOODWAIT_BUFFER_SEC")
    ai_mode: str = Field(default="suggestion-only", alias="AI_MODE")
    ai_provider: str = Field(default="stub", alias="AI_PROVIDER")
    ai_agent_enabled: bool = Field(default=True, alias="AI_AGENT_ENABLED")
    project_root: str = Field(default=".", alias="PROJECT_ROOT")
    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4o-mini", alias="OPENAI_MODEL")
    openai_base_url: str | None = Field(default=None, alias="OPENAI_BASE_URL")
    agent_notify_on_error: bool = Field(default=False, alias="AGENT_NOTIFY_ON_ERROR")
    agent_max_context_files: int = Field(default=12, alias="AGENT_MAX_CONTEXT_FILES")
    telegram_proxy: str | None = Field(default=None, alias="TELEGRAM_PROXY")

    @field_validator("bot_token")
    @classmethod
    def validate_bot_token(cls, value: str) -> str:
        if not value or ":" not in value:
            raise ValueError("BOT_TOKEN must be a valid Telegram bot token.")
        return value

    @field_validator("database_url")
    @classmethod
    def normalize_db_url(cls, value: str) -> str:
        return normalize_database_url(value)

    @property
    def admin_id_list(self) -> list[int]:
        return [int(item.strip()) for item in self.admin_ids.split(",") if item.strip()]

    @property
    def ai_mode_enum(self) -> AiMode:
        return AiMode(self.ai_mode)

    @model_validator(mode="after")
    def validate_admin_ids_present(self) -> "Settings":
        if not self.admin_id_list:
            raise ValueError("ADMIN_IDS must contain at least one numeric user id.")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
