"""
Configuration - конфигурация бота

Все константы и настройки в одном месте.
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Bot Token
BOT_TOKEN = os.getenv("BOT_TOKEN", "8197893707:AAEbGC7r_4GGWXvgah-q-mLw5pp7YIxhK9g")

# Database Configuration
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_USER = os.getenv("DB_USER", "n8n")
DB_PASSWORD = os.getenv("DB_PASSWORD", "sS67wM+1zMBRFHAW4kj9HwFl5J6+veo7Nirx0/I+oiU=")
DB_NAME = os.getenv("DB_NAME", "n8n")
DB_SCHEMA = os.getenv("DB_SCHEMA", "selfology")

# Redis FSM Storage Configuration
REDIS_FSM_HOST = os.getenv("REDIS_FSM_HOST", "localhost")
REDIS_FSM_PORT = int(os.getenv("REDIS_FSM_PORT", "6379"))
REDIS_FSM_DB = int(os.getenv("REDIS_FSM_DB", "1"))

# Bot Instance Lock Configuration
BOT_INSTANCE_LOCK_KEY = "selfology:bot:instance_lock"
BOT_INSTANCE_LOCK_TTL = 30  # seconds

# Admin Configuration
ADMIN_USER_ID = "98005572"

# Debug Configuration
DEBUG_MESSAGES = os.getenv("DEBUG_MESSAGES", "false").lower() == "true"
