"""Chat domain entity."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional, List
from uuid import UUID

from ..value_objects import TelegramId, AIModel


class MessageType(Enum):
    """Chat message types."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


@dataclass
class ConversationContext:
    """Context for a conversation."""
    
    topic: Optional[str] = None
    emotional_state: Optional[str] = None
    complexity_level: Optional[str] = None
    personality_insights: Dict[str, Any] = field(default_factory=dict)
    session_goals: List[str] = field(default_factory=list)
    
    def add_insight(self, key: str, value: Any) -> None:
        """Add personality insight to context."""
        self.personality_insights[key] = value
    
    def set_topic(self, topic: str) -> None:
        """Set conversation topic."""
        self.topic = topic
    
    def update_emotional_state(self, state: str) -> None:
        """Update user's emotional state."""
        self.emotional_state = state


@dataclass
class ChatMessage:
    """Chat message domain entity."""
    
    id: UUID
    user_id: TelegramId
    message_type: MessageType
    content: str
    ai_model_used: Optional[AIModel]
    cost_estimate: Optional[float]
    context: Optional[ConversationContext]
    insights: Dict[str, Any] = field(default_factory=dict)
    personality_updates: Dict[str, Any] = field(default_factory=dict)
    vector_updated: bool = False
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    @property
    def is_user_message(self) -> bool:
        """Check if message is from user."""
        return self.message_type == MessageType.USER
    
    @property
    def is_assistant_message(self) -> bool:
        """Check if message is from assistant."""
        return self.message_type == MessageType.ASSISTANT
    
    @property
    def has_insights(self) -> bool:
        """Check if message has personality insights."""
        return bool(self.insights)
    
    @property
    def has_personality_updates(self) -> bool:
        """Check if message triggered personality updates."""
        return bool(self.personality_updates)
    
    def add_insight(self, key: str, value: Any) -> None:
        """Add insight to message."""
        self.insights[key] = value
    
    def add_personality_update(self, trait: str, update: Dict[str, Any]) -> None:
        """Add personality trait update."""
        self.personality_updates[trait] = update
    
    def mark_vector_updated(self) -> None:
        """Mark that vector storage was updated."""
        self.vector_updated = True
    
    def get_message_length(self) -> int:
        """Get message content length."""
        return len(self.content)
    
    def is_long_message(self, threshold: int = 300) -> bool:
        """Check if message is considered long."""
        return self.get_message_length() > threshold
    
    @classmethod
    def create_user_message(
        cls,
        user_id: TelegramId,
        content: str,
        context: Optional[ConversationContext] = None
    ) -> "ChatMessage":
        """Create user message."""
        return cls(
            id=UUID(),
            user_id=user_id,
            message_type=MessageType.USER,
            content=content,
            ai_model_used=None,
            cost_estimate=None,
            context=context
        )
    
    @classmethod
    def create_assistant_message(
        cls,
        user_id: TelegramId,
        content: str,
        ai_model: AIModel,
        cost_estimate: float,
        context: Optional[ConversationContext] = None
    ) -> "ChatMessage":
        """Create assistant message."""
        return cls(
            id=UUID(),
            user_id=user_id,
            message_type=MessageType.ASSISTANT,
            content=content,
            ai_model_used=ai_model,
            cost_estimate=cost_estimate,
            context=context
        )