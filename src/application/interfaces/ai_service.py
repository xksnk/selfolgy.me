"""AI service interface."""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

from ...domain.value_objects import AIModel
from ...domain.services import AIRoutingResult


class IAIService(ABC):
    """Interface for AI service operations."""
    
    @abstractmethod
    async def generate_response(
        self,
        model: AIModel,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> str:
        """Generate AI response using specified model."""
        pass
    
    @abstractmethod
    async def route_request(
        self,
        telegram_id: int,
        task_description: str,
        message_content: str = "",
        context: Optional[Dict[str, Any]] = None
    ) -> AIRoutingResult:
        """Route request to appropriate AI model."""
        pass
    
    @abstractmethod
    async def analyze_personality(
        self,
        text: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Analyze personality traits from text."""
        pass
    
    @abstractmethod
    async def generate_insights(
        self,
        user_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Generate personalized insights."""
        pass
    
    @abstractmethod
    async def health_check(self) -> Dict[str, bool]:
        """Check health of AI services."""
        pass