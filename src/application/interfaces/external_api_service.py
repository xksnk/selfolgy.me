"""External API service interface."""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class IExternalAPIService(ABC):
    """Interface for external API operations."""
    
    @abstractmethod
    async def trigger_n8n_workflow(
        self,
        workflow_id: str,
        payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Trigger n8n workflow."""
        pass
    
    @abstractmethod
    async def send_analytics_event(
        self,
        event_type: str,
        user_id: int,
        properties: Dict[str, Any]
    ) -> bool:
        """Send analytics event."""
        pass
    
    @abstractmethod
    async def backup_user_data(
        self,
        user_id: int,
        backup_type: str = "full"
    ) -> Optional[str]:
        """Backup user data to external storage."""
        pass
    
    @abstractmethod
    async def health_check(self) -> Dict[str, bool]:
        """Check health of external services."""
        pass