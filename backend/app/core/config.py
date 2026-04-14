"""
Core configuration using Pydantic Settings.
"""
from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # App
    APP_NAME: str = "FatturaMVP"
    APP_VERSION: str = "2.0.0"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://fatturamvp:fatturamvp@localhost:5432/fatturamvp"
    DATABASE_URL_SYNC: str = "postgresql+psycopg2://fatturamvp:fatturamvp@localhost:5432/fatturamvp"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Security
    SECRET_KEY: str = "change-me-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Telegram
    TELEGRAM_BOT_TOKEN: Optional[str] = None

    # AI APIs
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    MINIMAX_API_KEY: Optional[str] = None
    MINIMAX_BASE_URL: str = "https://api.minimax.chat/v1"

    # CORS
    CORS_ORIGINS: list[str] = ["*"]

    # File Storage
    UPLOAD_DIR: str = "/app/data/invoices"
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB

    # Stripe Billing
    STRIPE_API_KEY: Optional[str] = None
    STRIPE_WEBHOOK_SECRET: Optional[str] = None

    # Twilio WhatsApp
    TWILIO_ACCOUNT_SID: Optional[str] = None
    TWILIO_AUTH_TOKEN: Optional[str] = None
    TWILIO_WHATSAPP_FROM: Optional[str] = None  # formato: whatsapp:+39xxxxxxxxx

    # Interessi di mora (D.Lgs 231/2002)
    INTERESSI_TASSO_BASE: float = 0.12   # 12% annuo (BCE 4% + spread 8% B2B)
    PENALTY_PERCENTUALE: float = 0.01    # 1% ogni PENALTY_GIORNI oltre i 60gg
    PENALTY_GIORNI: int = 30            # ogni quanti gg si applica la penalty

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
