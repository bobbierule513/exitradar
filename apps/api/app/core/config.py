"""Application configuration loaded exclusively from environment variables."""

from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings for ExitRadar API and workers."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""
    supabase_jwt_secret: str = ""
    database_url: str = ""

    redis_url: str = "redis://localhost:6379/0"

    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_origins: str = "http://localhost:5173,http://localhost:3000"
    environment: str = "development"

    google_places_api_key: str = ""

    openai_api_key: str = ""
    anthropic_api_key: str = ""
    groq_api_key: str = ""
    llm_provider: str = "openai"
    llm_model: str = "gpt-4o-mini"

    # Demo mode uses seeded data when external APIs are absent
    demo_mode: bool = True

    @property
    def cors_origin_list(self) -> List[str]:
        """Parse comma-separated CORS origins into a list."""
        origins = [o.strip() for o in self.cors_origins.split(",") if o.strip()]
        # Always allow local Vite hosts in development
        for extra in (
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:5174",
            "http://127.0.0.1:5174",
        ):
            if extra not in origins:
                origins.append(extra)
        return origins


@lru_cache
def get_settings() -> Settings:
    """Return cached settings singleton."""
    return Settings()
