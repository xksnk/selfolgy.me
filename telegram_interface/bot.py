"""
Clean Telegram Bot Interface - Pure routing to services
NO business logic in handlers - only routing to appropriate services
"""
import asyncio
import asyncpg
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from pathlib import Path
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from .handlers.assessment_handler import setup_assessment_handlers
from .handlers.chat_handler import setup_chat_handlers  
from .handlers.stats_handler import setup_stats_handlers
from .handlers.profile_handler import setup_profile_handlers
from ..core.config import get_config
from ..core.logging import telegram_logger


class SelfologyBot:
    """
    Clean Telegram Bot Interface
    
    Pure routing architecture:
    - Handlers only route to services
    - No business logic in Telegram layer
    - Clean separation of concerns
    - Independent services
    """
    
    def __init__(self):
        self.config = get_config()
        self.logger = telegram_logger
        
        # Initialize bot and dispatcher
        self.bot = Bot(token=self.config.telegram.bot_token)
        self.dp = Dispatcher(storage=MemoryStorage())
        
        # Database pool for services
        self.db_pool = None
        
        self.logger.info("Selfology Bot interface initialized")
    
    async def initialize(self) -> bool:
        """Initialize bot and database connection"""
        
        try:
            # Create database pool
            self.db_pool = await asyncpg.create_pool(**{
                "host": self.config.database.host,
                "port": self.config.database.port,
                "user": self.config.database.user,
                "password": self.config.database.password,
                "database": self.config.database.database
            })
            
            self.logger.info("Database pool created successfully")
            
            # Setup handlers - pure routing only
            await self._setup_handlers()
            
            self.logger.info("All handlers configured")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize bot: {e}")
            return False
    
    async def _setup_handlers(self):
        """Setup all handler groups"""
        
        # Pass db_pool to handlers for service initialization
        setup_assessment_handlers(self.dp, self.db_pool)
        setup_chat_handlers(self.dp, self.db_pool)
        setup_stats_handlers(self.dp, self.db_pool)
        setup_profile_handlers(self.dp, self.db_pool)
        
        self.logger.info("Handler setup completed")
    
    async def start_polling(self):
        """Start bot polling"""
        
        try:
            self.logger.info("Starting Selfology Bot polling...")
            
            print("🚀 Selfology AI Psychology Coach Bot")
            print("✅ Clean modular architecture")
            print("✅ Independent services") 
            print("✅ Pure routing handlers")
            print("✅ NO session-based assessment")
            print("✅ Intelligent question core integrated")
            print("🔗 Ready for users!")
            
            await self.dp.start_polling(self.bot)
            
        except KeyboardInterrupt:
            self.logger.info("Bot stopped by user")
        except Exception as e:
            self.logger.error(f"Bot polling error: {e}")
            raise
    
    async def stop(self):
        """Stop bot and cleanup"""
        
        try:
            if self.db_pool:
                await self.db_pool.close()
                self.logger.info("Database pool closed")
            
            await self.bot.session.close()
            self.logger.info("Bot session closed")
            
        except Exception as e:
            self.logger.error(f"Error during bot shutdown: {e}")


async def main():
    """Main entry point"""
    
    bot = SelfologyBot()
    
    if await bot.initialize():
        try:
            await bot.start_polling()
        finally:
            await bot.stop()
    else:
        print("❌ Failed to initialize bot")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())