"""Health check system."""

import logging
import time
from typing import Dict, Any

logger = logging.getLogger(__name__)


class HealthCheckService:
    """Service for system health monitoring."""
    
    def __init__(self, container):
        self.container = container
        self.startup_time = time.time()
    
    async def get_health_status(self) -> Dict[str, Any]:
        """Get comprehensive health status."""
        
        health_data = {
            "status": "healthy",
            "timestamp": time.time(),
            "uptime": time.time() - self.startup_time,
            "version": "1.0.0",
            "services": {}
        }
        
        try:
            # Check all services
            service_health = await self.container.health_check()
            health_data["services"] = service_health
            
            # Determine overall status
            if not all(service_health.values()):
                health_data["status"] = "degraded"
                unhealthy_services = [
                    service for service, healthy in service_health.items() 
                    if not healthy
                ]
                health_data["unhealthy_services"] = unhealthy_services
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            health_data["status"] = "unhealthy"
            health_data["error"] = str(e)
        
        return health_data
    
    async def get_readiness_status(self) -> Dict[str, Any]:
        """Check if system is ready to serve requests."""
        
        readiness_data = {
            "ready": True,
            "timestamp": time.time(),
            "checks": {}
        }
        
        # Database connectivity
        try:
            service_health = await self.container.health_check()
            readiness_data["checks"]["database"] = service_health.get("database", False)
            
            if not readiness_data["checks"]["database"]:
                readiness_data["ready"] = False
                
        except Exception as e:
            logger.error(f"Readiness check failed: {e}")
            readiness_data["ready"] = False
            readiness_data["error"] = str(e)
        
        return readiness_data