"""
Centralized Configuration Management for Selfology
"""
import os
from typing import Dict, Any, Optional
from pathlib import Path
from dataclasses import dataclass


@dataclass
class DatabaseConfig:
    """Database configuration"""
    host: str
    port: int
    user: str
    password: str
    database: str
    
    @property
    def url(self) -> str:
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"
    
    @property
    def async_url(self) -> str:
        return f"postgresql+asyncpg://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"


@dataclass
class VectorConfig:
    """Vector database configuration"""
    host: str = "localhost"
    port: int = 6333
    collection_name: str = "selfology_personalities"
    vector_size: int = 693  # Matches the 693-question core


@dataclass
class AIConfig:
    """AI configuration"""
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    default_model: str = "gpt-4o-mini"
    max_tokens: int = 1000
    temperature: float = 0.7


@dataclass
class TelegramConfig:
    """Telegram bot configuration"""
    bot_token: str
    webhook_url: Optional[str] = None
    webhook_path: Optional[str] = None


class Config:
    """Main configuration class"""
    
    def __init__(self):
        # Database configuration
        self.database = DatabaseConfig(
            host=os.getenv("DB_HOST", "localhost"),
            port=int(os.getenv("DB_PORT", 5432)),
            user=os.getenv("DB_USER", "n8n"),
            password=os.getenv("DB_PASSWORD", "sS67wM+1zMBRFHAW4kj9HwFl5J6+veo7Nirx0/I+oiU="),
            database=os.getenv("DB_NAME", "n8n")
        )
        
        # Vector database
        self.vector = VectorConfig(
            host=os.getenv("QDRANT_HOST", "localhost"),
            port=int(os.getenv("QDRANT_PORT", 6333)),
            collection_name=os.getenv("VECTOR_COLLECTION", "selfology_personalities")
        )
        
        # AI configuration
        self.ai = AIConfig(
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
            default_model=os.getenv("DEFAULT_AI_MODEL", "gpt-4o-mini"),
            max_tokens=int(os.getenv("AI_MAX_TOKENS", 1000)),
            temperature=float(os.getenv("AI_TEMPERATURE", 0.7))
        )
        
        # Telegram bot
        self.telegram = TelegramConfig(
            bot_token=os.getenv("BOT_TOKEN", "8197893707:AAEbGC7r_4GGWXvgah-q-mLw5pp7YIxhK9g"),
            webhook_url=os.getenv("WEBHOOK_URL"),
            webhook_path=os.getenv("WEBHOOK_PATH")
        )
        
        # Question core path
        self.question_core_path = str(Path(__file__).parent.parent / "intelligent_question_core/data/selfology_intelligent_core.json")
        
        # Service configuration
        self.services = {
            "assessment_engine": {
                "max_questions_per_session": 50,
                "energy_safety_threshold": -1.5,
                "trust_building_rate": 0.1,
                "healing_debt_limit": 1.0
            },
            "chat_coach": {
                "context_window": 10,  # Last 10 messages
                "personality_weight": 0.7,  # How much personality influences responses
                "memory_retention_days": 30
            },
            "statistics": {
                "cache_ttl": 300,  # 5 minutes
                "batch_update_size": 100
            }
        }
        
        # Logging configuration
        self.logging = {
            "level": os.getenv("LOG_LEVEL", "INFO"),
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            "file_path": Path("logs"),
            "max_file_size": 10 * 1024 * 1024,  # 10MB
            "backup_count": 5
        }
    
    def get_service_config(self, service_name: str) -> Dict[str, Any]:
        """Get configuration for specific service"""
        return self.services.get(service_name, {})


# Global configuration instance
config = Config()


def get_config() -> Config:
    """Get the global configuration instance"""
    return config