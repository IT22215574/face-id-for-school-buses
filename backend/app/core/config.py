from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_ENV: Literal["development", "production", "test"] = "development"
    DATABASE_URL: str = "postgresql+psycopg://schoolbus:schoolbus@localhost:5432/schoolbus"
    JWT_SECRET: str = "change-me-in-production"
    JWT_ACCESS_EXPIRE_MIN: int = 30
    JWT_REFRESH_EXPIRE_DAYS: int = 30
    FCM_PROJECT_ID: str = "school-bus-parent-app"
    FCM_CREDENTIALS_JSON: str = '{"type":"service_account","project_id":"school-bus-parent-app"}'
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_FROM_NUMBER: str = ""
    GOOGLE_MAPS_API_KEY: str = ""
    REDIS_URL: str = "redis://localhost:6379/0"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=True)


@lru_cache
def get_settings() -> Settings:
    return Settings()
