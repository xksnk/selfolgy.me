#!/usr/bin/env python3
"""Setup script for Selfology application."""

import asyncio
import logging
import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent))

from src.config import get_settings, get_container
from src.monitoring import setup_logging


async def main():
    """Main setup function."""
    
    # Setup logging
    setup_logging()
    logger = logging.getLogger(__name__)
    
    logger.info("Starting Selfology setup...")
    
    try:
        # Load settings
        settings = get_settings()
        logger.info(f"Environment: {settings.environment}")
        
        # Initialize container
        container = get_container()
        await container.initialize()
        
        # Run health check
        health = await container.health_check()
        logger.info(f"Health check: {health}")
        
        # Verify all services are healthy
        if all(health.values()):
            logger.info("✅ Setup completed successfully!")
            logger.info("System is ready to serve requests.")
        else:
            logger.error("❌ Setup completed with issues:")
            for service, healthy in health.items():
                status = "✅" if healthy else "❌"
                logger.error(f"  {status} {service}")
            sys.exit(1)
        
    except Exception as e:
        logger.error(f"Setup failed: {e}")
        sys.exit(1)
    
    finally:
        try:
            await container.close()
        except:
            pass


if __name__ == "__main__":
    asyncio.run(main())