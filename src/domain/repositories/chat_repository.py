"""Chat repository interface."""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional, List
from uuid import UUID

from ..entities import ChatMessage
from ..value_objects import TelegramId


class IChatRepository(ABC):
    """Chat repository interface."""
    
    @abstractmethod
    async def create(self, message: ChatMessage) -> ChatMessage:
        """Create a new chat message."""
        pass
    
    @abstractmethod
    async def get_by_id(self, message_id: UUID) -> Optional[ChatMessage]:
        """Get chat message by ID."""
        pass
    
    @abstractmethod
    async def get_recent_messages(
        self, 
        user_id: TelegramId, 
        limit: int = 10
    ) -> List[ChatMessage]:
        """Get recent chat messages for user."""
        pass
    
    @abstractmethod
    async def get_messages_by_date_range(
        self,
        user_id: TelegramId,
        start_date: datetime,
        end_date: datetime
    ) -> List[ChatMessage]:
        """Get messages within date range."""
        pass
    
    @abstractmethod
    async def update(self, message: ChatMessage) -> ChatMessage:
        """Update chat message."""
        pass
    
    @abstractmethod
    async def delete(self, message_id: UUID) -> bool:
        """Delete chat message."""
        pass
    
    @abstractmethod
    async def get_conversation_context(
        self,
        user_id: TelegramId,
        context_window: int = 5
    ) -> List[ChatMessage]:
        """Get recent conversation context."""
        pass
    
    @abstractmethod
    async def search_messages(
        self,
        user_id: TelegramId,
        query: str,
        limit: int = 20
    ) -> List[ChatMessage]:
        """Search messages by content."""
        pass