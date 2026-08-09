from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    pluggy_client_id: str = ""
    pluggy_client_secret: str = ""
    pluggy_api_url: str = "https://api.pluggy.ai"
    database_url: str = "sqlite+aiosqlite:///./pluggy.db"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
