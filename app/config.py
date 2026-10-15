from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configurações lidas do ambiente/`.env` (nunca versionar segredos)."""

    pluggy_client_id: str = ""
    pluggy_client_secret: str = ""
    pluggy_api_url: str = "https://api.pluggy.ai"
    database_url: str = "sqlite+aiosqlite:///./pluggy.db"
    telegram_bot_token: str = ""
    telegram_allowed_user_id: int | None = None

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    """Retorna as configurações em cache (uma leitura do `.env` por processo).

    Returns:
        Instância única de `Settings` para o processo atual.
    """
    return Settings()
