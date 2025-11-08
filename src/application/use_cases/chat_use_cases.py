"""Chat-related use cases."""

from uuid import uuid4
from typing import List, Optional, Dict, Any

from ...domain.entities import ChatMessage, MessageType, ConversationContext, User
from ...domain.repositories import IChatRepository, IUserRepository
from ...domain.services import UserTierService, AIRoutingService
from ...domain.value_objects import TelegramId, AIModel
from ..dto import SendMessageDTO, ChatMessageDTO, ConversationContextDTO
from ..interfaces import IAIService, IVectorService


class SendMessageUseCase:
    """Use case for sending a chat message and generating AI response."""
    
    def __init__(
        self,
        chat_repository: IChatRepository,
        user_repository: IUserRepository,
        ai_service: IAIService,
        vector_service: IVectorService,
        user_tier_service: UserTierService,
        ai_routing_service: AIRoutingService
    ):
        self.chat_repository = chat_repository
        self.user_repository = user_repository
        self.ai_service = ai_service
        self.vector_service = vector_service
        self.user_tier_service = user_tier_service
        self.ai_routing_service = ai_routing_service
    
    async def execute(self, dto: SendMessageDTO) -> tuple[ChatMessageDTO, ChatMessageDTO]:
        """Send message and generate AI response."""
        
        telegram_id = TelegramId(dto.telegram_id)
        
        # Get user
        user = await self.user_repository.get_by_telegram_id(telegram_id)
        if not user:
            raise ValueError("User not found")
        
        # Check user limits
        recent_messages = await self.chat_repository.get_recent_messages(telegram_id, limit=50)
        daily_messages = len([msg for msg in recent_messages if msg.is_user_message])
        
        if not self.user_tier_service.can_send_message(user, daily_messages):
            raise ValueError("Daily message limit exceeded")
        
        # Create conversation context
        context = self._create_context(dto.context) if dto.context else None
        
        # Save user message
        user_message = ChatMessage.create_user_message(
            user_id=telegram_id,
            content=dto.content,
            context=context
        )
        
        saved_user_message = await self.chat_repository.create(user_message)
        
        # Get conversation history for context
        conversation_history = await self.chat_repository.get_conversation_context(
            user_id=telegram_id,
            context_window=5
        )
        
        # Route AI request
        routing_result = await self.ai_service.route_request(
            telegram_id=dto.telegram_id,
            task_description="chat_response",
            message_content=dto.content,
            context=dto.context
        )
        
        # Prepare messages for AI
        messages = self._prepare_ai_messages(conversation_history, dto.content)
        
        # Generate AI response
        ai_response = await self.ai_service.generate_response(
            model=routing_result.model,
            messages=messages,
            system_prompt=self._get_system_prompt(user)
        )
        
        # Create AI message
        ai_message = ChatMessage.create_assistant_message(
            user_id=telegram_id,
            content=ai_response,
            ai_model=routing_result.model,
            cost_estimate=routing_result.estimated_cost,
            context=context
        )
        
        # Analyze personality insights
        insights = await self.ai_service.analyze_personality(
            text=dto.content,
            context=dto.context
        )
        
        if insights:
            ai_message.add_insight("personality_analysis", insights)
        
        # Save AI message
        saved_ai_message = await self.chat_repository.create(ai_message)
        
        # Store embeddings for future similarity search
        await self.vector_service.store_chat_embedding(
            user_id=dto.telegram_id,
            message_id=saved_user_message.id,
            text=dto.content,
            metadata={"type": "user_message"}
        )
        
        return (
            self._to_message_dto(saved_user_message),
            self._to_message_dto(saved_ai_message)
        )
    
    def _create_context(self, context_data: Dict[str, Any]) -> ConversationContext:
        """Create conversation context from DTO data."""
        return ConversationContext(
            topic=context_data.get("topic"),
            emotional_state=context_data.get("emotional_state"),
            complexity_level=context_data.get("complexity_level"),
            personality_insights=context_data.get("personality_insights", {}),
            session_goals=context_data.get("session_goals", [])
        )
    
    def _prepare_ai_messages(
        self,
        conversation_history: List[ChatMessage],
        current_message: str
    ) -> List[Dict[str, str]]:
        """Prepare messages for AI processing."""
        
        messages = []
        
        # Add conversation history
        for msg in conversation_history[-5:]:  # Last 5 messages for context
            messages.append({
                "role": "user" if msg.is_user_message else "assistant",
                "content": msg.content
            })
        
        # Add current message
        messages.append({
            "role": "user", 
            "content": current_message
        })
        
        return messages
    
    def _get_system_prompt(self, user: User) -> str:
        """Get system prompt based on user profile."""
        return f"""You are Selfology, an AI psychology coach providing personalized guidance.

User Profile:
- Name: {user.display_name}
- Tier: {user.tier.value}
- Privacy Level: {user.privacy_level.value}
- Onboarding Complete: {user.onboarding_completed}

Guidelines:
- Provide empathetic, personalized coaching
- Use psychological insights when appropriate
- Respect user's privacy level
- Be supportive and non-judgmental
- Ask follow-up questions to deepen understanding
- Offer practical advice and exercises
"""
    
    def _to_message_dto(self, message: ChatMessage) -> ChatMessageDTO:
        """Convert message entity to DTO."""
        context_dto = None
        if message.context:
            context_dto = ConversationContextDTO(
                topic=message.context.topic,
                emotional_state=message.context.emotional_state,
                complexity_level=message.context.complexity_level,
                personality_insights=message.context.personality_insights,
                session_goals=message.context.session_goals
            )
        
        return ChatMessageDTO(
            id=message.id,
            telegram_id=message.user_id.value,
            message_type=message.message_type.value,
            content=message.content,
            ai_model_used=message.ai_model_used.value if message.ai_model_used else None,
            cost_estimate=message.cost_estimate,
            context=context_dto,
            insights=message.insights,
            personality_updates=message.personality_updates,
            vector_updated=message.vector_updated,
            timestamp=message.timestamp
        )


class GetConversationHistoryUseCase:
    """Use case for getting conversation history."""
    
    def __init__(self, chat_repository: IChatRepository):
        self.chat_repository = chat_repository
    
    async def execute(self, telegram_id: int, limit: int = 20) -> List[ChatMessageDTO]:
        """Get conversation history for user."""
        
        messages = await self.chat_repository.get_recent_messages(
            user_id=TelegramId(telegram_id),
            limit=limit
        )
        
        return [self._to_message_dto(msg) for msg in messages]
    
    def _to_message_dto(self, message: ChatMessage) -> ChatMessageDTO:
        """Convert message entity to DTO."""
        context_dto = None
        if message.context:
            context_dto = ConversationContextDTO(
                topic=message.context.topic,
                emotional_state=message.context.emotional_state,
                complexity_level=message.context.complexity_level,
                personality_insights=message.context.personality_insights,
                session_goals=message.context.session_goals
            )
        
        return ChatMessageDTO(
            id=message.id,
            telegram_id=message.user_id.value,
            message_type=message.message_type.value,
            content=message.content,
            ai_model_used=message.ai_model_used.value if message.ai_model_used else None,
            cost_estimate=message.cost_estimate,
            context=context_dto,
            insights=message.insights,
            personality_updates=message.personality_updates,
            vector_updated=message.vector_updated,
            timestamp=message.timestamp
        )