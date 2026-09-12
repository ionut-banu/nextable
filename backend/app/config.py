"""Settings from the environment. Never from the database (spec 7)."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    staff_password: str
    session_secret: str
    database_url: str = "sqlite:///./nextable.db"

    #: Failed logins allowed per caller before the door closes for a while.
    login_attempt_limit: int = 5
    login_attempt_window_seconds: int = 300


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
