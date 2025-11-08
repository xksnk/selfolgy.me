"""Application settings and configuration."""

import os
from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""
    
    # Application
    app_name: str = "Selfology Bot"
    debug: bool = False
    environment: str = "production"
    host: str = "0.0.0.0"
    port: int = 8000
    
    # Security
    secret_key: str = Field(..., env="SECRET_KEY")
    
    # Database
    database_url: str = Field(..., env="DATABASE_URL")
    
    # Redis
    redis_url: str = Field(default="redis://localhost:6379", env="REDIS_URL")
    
    # Telegram Bot
    telegram_bot_token: str = Field(..., env="TELEGRAM_BOT_TOKEN")
    telegram_webhook_url: Optional[str] = Field(None, env="TELEGRAM_WEBHOOK_URL")
    
    # AI APIs
    anthropic_api_key: str = Field(..., env="ANTHROPIC_API_KEY")
    openai_api_key: str = Field(..., env="OPENAI_API_KEY")
    
    # Vector Database
    qdrant_url: str = Field(default="http://localhost:6333", env="QDRANT_URL")
    qdrant_api_key: Optional[str] = Field(None, env="QDRANT_API_KEY")
    
    # External APIs
    n8n_api_key: str = Field(..., env="N8N_API_KEY")
    n8n_base_url: str = Field(..., env="N8N_BASE_URL")
    
    # Monitoring
    sentry_dsn: Optional[str] = Field(None, env="SENTRY_DSN")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    
    # Feature Flags
    enable_analytics: bool = Field(default=True, env="ENABLE_ANALYTICS")
    enable_vector_storage: bool = Field(default=True, env="ENABLE_VECTOR_STORAGE")
    enable_personality_analysis: bool = Field(default=True, env="ENABLE_PERSONALITY_ANALYSIS")
    
    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()