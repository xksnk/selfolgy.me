#!/usr/bin/env python3
"""Health check script for monitoring system status."""

import asyncio
import json
import logging
import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent))

from src.config import get_container
from src.monitoring import HealthCheckService, setup_logging


async def main():
    """Run health check."""
    
    setup_logging()
    logger = logging.getLogger(__name__)
    
    try:
        # Initialize container
        container = get_container()
        await container.initialize()
        
        # Create health check service
        health_service = HealthCheckService(container)
        
        # Get health status
        health_status = await health_service.get_health_status()
        
        # Output results
        print(json.dumps(health_status, indent=2, default=str))
        
        # Exit with appropriate code
        if health_status["status"] == "healthy":
            logger.info("✅ All systems healthy")
            sys.exit(0)
        elif health_status["status"] == "degraded":
            logger.warning("⚠️ Some services degraded")
            sys.exit(1)
        else:
            logger.error("❌ System unhealthy")
            sys.exit(2)
            
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        print(json.dumps({
            "status": "error",
            "error": str(e)
        }, indent=2))
        sys.exit(3)
    
    finally:
        try:
            await container.close()
        except:
            pass


if __name__ == "__main__":
    asyncio.run(main())