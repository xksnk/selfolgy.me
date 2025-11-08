from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional


class Settings(BaseSettings):
    # FastAPI
    app_name: str = "Selfology Bot"
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 8000
    
    # Telegram
    telegram_bot_token: str = Field(..., env="TELEGRAM_BOT_TOKEN")
    telegram_webhook_url: Optional[str] = Field(None, env="TELEGRAM_WEBHOOK_URL")
    
    # AI APIs
    anthropic_api_key: str = Field(..., env="ANTHROPIC_API_KEY")
    openai_api_key: str = Field(..., env="OPENAI_API_KEY")
    
    # Database
    database_url: str = Field(..., env="DATABASE_URL")
    
    # Redis
    redis_url: str = Field(default="redis://localhost:6379", env="REDIS_URL")
    
    # Qdrant Vector DB
    qdrant_url: str = Field(default="http://localhost:6333", env="QDRANT_URL")
    qdrant_api_key: Optional[str] = Field(None, env="QDRANT_API_KEY")
    
    # ChromaDB (additional vector store)
    chromadb_url: str = Field(default="http://localhost:8000", env="CHROMADB_URL")
    
    # n8n Integration
    n8n_api_key: str = Field(..., env="N8N_API_KEY")
    n8n_base_url: str = Field(..., env="N8N_BASE_URL")
    
    # AI Router Settings
    ai_router_default_model: str = "gpt-4o-mini"
    ai_router_premium_model: str = "gpt-4"
    ai_router_deep_analysis_model: str = "claude-3-5-sonnet-20241022"
    
    # Cost optimization thresholds
    simple_task_threshold: float = 0.3
    complex_task_threshold: float = 0.8
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # Allow extra fields in .env (e.g., monitoring settings)


settings = Settings()