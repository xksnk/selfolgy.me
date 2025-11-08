#!/usr/bin/env python3
"""Database migration script."""

import asyncio
import logging
import sys
from pathlib import Path

# Add src to path  
sys.path.append(str(Path(__file__).parent.parent))

from src.config import get_settings
from src.infrastructure.database import initialize_database
from src.monitoring import setup_logging


async def main():
    """Run database migrations."""
    
    setup_logging()
    logger = logging.getLogger(__name__)
    
    try:
        settings = get_settings()
        
        logger.info("Starting database migration...")
        logger.info(f"Database URL: {settings.database_url[:20]}...")
        
        # Initialize database
        db_manager = initialize_database(settings.database_url, echo=settings.debug)
        await db_manager.initialize()
        
        # Create/update tables
        await db_manager.create_tables()
        
        # Verify connection
        if await db_manager.health_check():
            logger.info("✅ Migration completed successfully!")
        else:
            logger.error("❌ Migration verification failed")
            sys.exit(1)
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        sys.exit(1)
    
    finally:
        try:
            await db_manager.close()
        except:
            pass


if __name__ == "__main__":
    asyncio.run(main())