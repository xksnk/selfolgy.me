"""Dependency injection container."""

import logging
from functools import lru_cache
from typing import Any, Dict

from ...domain.services import AIRoutingService, PersonalityAnalysisService, UserTierService
from ...application.use_cases import (
    CreateUserUseCase, GetUserUseCase, UpdateUserUseCase,
    SendMessageUseCase, GetConversationHistoryUseCase
)
from ...infrastructure.database import initialize_database
from ...infrastructure.repositories import SQLUserRepository
from ...infrastructure.external_services import AIServiceImpl
from .settings import Settings, get_settings

logger = logging.getLogger(__name__)


class Container:
    """Dependency injection container."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self._instances: Dict[str, Any] = {}
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize container and all dependencies."""
        if self._initialized:
            return
        
        try:
            # Initialize database
            db_manager = initialize_database(
                self.settings.database_url,
                echo=self.settings.debug
            )
            await db_manager.initialize()
            await db_manager.create_tables()
            
            # Register services
            self._register_domain_services()
            await self._register_infrastructure_services()
            self._register_use_cases()
            
            self._initialized = True
            logger.info("Dependency injection container initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize container: {e}")
            raise
    
    def _register_domain_services(self) -> None:
        """Register domain services."""
        self._instances["ai_routing_service"] = AIRoutingService()
        self._instances["personality_analysis_service"] = PersonalityAnalysisService()
        self._instances["user_tier_service"] = UserTierService()
    
    async def _register_infrastructure_services(self) -> None:
        """Register infrastructure services."""
        # Repositories would need session injection - simplified here
        self._instances["user_repository"] = SQLUserRepository
        
        # AI Service
        self._instances["ai_service"] = AIServiceImpl(
            anthropic_api_key=self.settings.anthropic_api_key,
            openai_api_key=self.settings.openai_api_key,
            user_repository=self._instances["user_repository"],
            ai_routing_service=self._instances["ai_routing_service"]
        )
    
    def _register_use_cases(self) -> None:
        """Register use cases."""
        # Use cases would be instantiated with their dependencies
        pass
    
    def get(self, service_name: str) -> Any:
        """Get service instance."""
        if not self._initialized:
            raise RuntimeError("Container not initialized")
        
        instance = self._instances.get(service_name)
        if not instance:
            raise ValueError(f"Service '{service_name}' not found")
        
        return instance
    
    async def health_check(self) -> Dict[str, bool]:
        """Check health of all services."""
        health_status = {}
        
        # Database health
        try:
            from ...infrastructure.database import get_database_manager
            db_manager = get_database_manager()
            health_status["database"] = await db_manager.health_check()
        except Exception:
            health_status["database"] = False
        
        # AI services health
        try:
            ai_service = self.get("ai_service")
            ai_health = await ai_service.health_check()
            health_status.update(ai_health)
        except Exception:
            health_status["ai_services"] = False
        
        return health_status
    
    async def close(self) -> None:
        """Close container and cleanup resources."""
        try:
            from ...infrastructure.database import get_database_manager
            db_manager = get_database_manager()
            await db_manager.close()
            logger.info("Container closed successfully")
        except Exception as e:
            logger.error(f"Error closing container: {e}")


# Global container instance
_container: Container = None


@lru_cache()
def get_container() -> Container:
    """Get cached container instance."""
    global _container
    if not _container:
        settings = get_settings()
        _container = Container(settings)
    return _container