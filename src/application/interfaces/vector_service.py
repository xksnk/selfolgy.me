"""Vector service interface."""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from uuid import UUID


class IVectorService(ABC):
    """Interface for vector database operations."""
    
    @abstractmethod
    async def store_personality_vector(
        self,
        user_id: int,
        vector_data: Dict[str, float],
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Store personality vector in vector database."""
        pass
    
    @abstractmethod
    async def update_personality_vector(
        self,
        point_id: str,
        vector_data: Dict[str, float],
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Update existing personality vector."""
        pass
    
    @abstractmethod
    async def search_similar_personalities(
        self,
        vector_data: Dict[str, float],
        limit: int = 10,
        threshold: float = 0.8
    ) -> List[Dict[str, Any]]:
        """Search for similar personality profiles."""
        pass
    
    @abstractmethod
    async def store_chat_embedding(
        self,
        user_id: int,
        message_id: UUID,
        text: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Store chat message embedding."""
        pass
    
    @abstractmethod
    async def search_similar_conversations(
        self,
        user_id: int,
        query_text: str,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Search for similar conversations."""
        pass
    
    @abstractmethod
    async def delete_user_vectors(self, user_id: int) -> bool:
        """Delete all vectors for a user."""
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Check vector service health."""
        pass