"""
Selfology AI Psychology Coach - Refactored Main Entry Point
Clean modular architecture with independent services
"""
#!/usr/bin/env python3

import asyncio
import sys
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from telegram_interface.bot import SelfologyBot
from core.config import get_config
from core.logging import get_logger


async def main():
    """
    Main entry point for refactored Selfology system
    
    Architecture Features:
    ✅ Clean separation of concerns
    ✅ Independent service layer  
    ✅ Pure routing in handlers
    ✅ NO session-based assessment (FIXED)
    ✅ Intelligent question core integration
    ✅ Vector database support
    ✅ Comprehensive logging
    ✅ GDPR compliance
    """
    
    # Initialize logging
    logger = get_logger("selfology.main", "main")
    config = get_config()
    
    logger.info("Starting Selfology AI Psychology Coach - Refactored Architecture")
    
    print("🧠 Selfology AI Psychology Coach")
    print("=" * 50)
    print("✅ Modular architecture initialized")
    print("✅ Independent services loaded")
    print("✅ Clean Telegram interface ready")
    print("✅ Assessment Engine: NO SESSIONS (FIXED)")
    print("✅ Chat Coach: Personalization ready")
    print("✅ Statistics Service: Analytics ready") 
    print("✅ Vector Service: 693D personality vectors")
    print("✅ User Profile Service: GDPR compliant")
    print("=" * 50)
    
    try:
        # Create and initialize bot
        bot = SelfologyBot()
        
        if await bot.initialize():
            logger.info("Bot initialized successfully")
            print("🚀 Bot ready! Starting polling...")
            
            # Start bot polling
            await bot.start_polling()
            
        else:
            logger.error("Failed to initialize bot")
            print("❌ Bot initialization failed")
            sys.exit(1)
    
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
        print("\n🛑 Shutting down gracefully...")
        
    except Exception as e:
        logger.error(f"Critical error: {e}", exc_info=True)
        print(f"💥 Critical error: {e}")
        sys.exit(1)
    
    finally:
        print("👋 Selfology stopped")


if __name__ == "__main__":
    # Ensure logs directory exists
    Path("logs").mkdir(exist_ok=True)
    
    # Run the refactored system
    asyncio.run(main())