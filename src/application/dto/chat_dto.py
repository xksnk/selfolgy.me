"""Chat DTOs for application layer."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, Optional, List
from uuid import UUID


@dataclass
class SendMessageDTO:
    """DTO for sending a chat message."""
    
    telegram_id: int
    content: str
    context: Optional[Dict[str, Any]] = None


@dataclass
class ConversationContextDTO:
    """DTO for conversation context."""
    
    topic: Optional[str] = None
    emotional_state: Optional[str] = None
    complexity_level: Optional[str] = None
    personality_insights: Dict[str, Any] = field(default_factory=dict)
    session_goals: List[str] = field(default_factory=list)


@dataclass
class ChatMessageDTO:
    """DTO for chat message response."""
    
    id: UUID
    telegram_id: int
    message_type: str
    content: str
    ai_model_used: Optional[str]
    cost_estimate: Optional[float]
    context: Optional[ConversationContextDTO]
    insights: Dict[str, Any] = field(default_factory=dict)
    personality_updates: Dict[str, Any] = field(default_factory=dict)
    vector_updated: bool = False
    timestamp: datetime