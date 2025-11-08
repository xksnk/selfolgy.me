#!/usr/bin/env python3
"""
Selfology Bot - NEW Modular Entry Point

SPRINT 1 Refactoring Complete (Nov 2025):
Использует новую модульную архитектуру telegram_interface

Запуск:
    python selfology_bot_new.py
    # или
    ./selfology_bot_new.py
"""

import asyncio
import logging
from telegram_interface import SelfologyController

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def main():
    """
    Main entry point
    
    Creates and starts the modular Selfology Bot controller.
    """
    logger.info("=" * 50)
    logger.info("🚀 Selfology Bot - Modular Architecture")
    logger.info("=" * 50)

    # Create controller
    controller = SelfologyController()

    # Start bot (lifecycle handles everything)
    await controller.start()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n👋 Bot stopped by user")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}", exc_info=True)
