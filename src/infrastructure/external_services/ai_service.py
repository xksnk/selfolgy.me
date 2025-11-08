"""AI service implementation."""

import asyncio
import logging
from typing import List, Dict, Any, Optional

import httpx
from anthropic import AsyncAnthropic
from openai import AsyncOpenAI

from ...application.interfaces import IAIService
from ...domain.entities import User
from ...domain.repositories import IUserRepository  
from ...domain.services import AIRoutingService, AIRoutingResult
from ...domain.value_objects import AIModel, TelegramId

logger = logging.getLogger(__name__)


class AIServiceImpl(IAIService):
    """AI service implementation using OpenAI and Anthropic."""
    
    def __init__(
        self,
        anthropic_api_key: str,
        openai_api_key: str,
        user_repository: IUserRepository,
        ai_routing_service: AIRoutingService
    ):
        self.anthropic_client = AsyncAnthropic(api_key=anthropic_api_key)
        self.openai_client = AsyncOpenAI(api_key=openai_api_key)
        self.user_repository = user_repository
        self.ai_routing_service = ai_routing_service
    
    async def generate_response(
        self,
        model: AIModel,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> str:
        """Generate AI response using specified model."""
        
        try:
            if model == AIModel.CLAUDE_SONNET:
                return await self._generate_anthropic_response(
                    messages, system_prompt, model.value, **kwargs
                )
            else:
                return await self._generate_openai_response(
                    messages, system_prompt, model.value, **kwargs
                )
        except Exception as e:
            logger.error(f"Error generating AI response: {e}")
            raise
    
    async def route_request(
        self,
        telegram_id: int,
        task_description: str,
        message_content: str = "",
        context: Optional[Dict[str, Any]] = None
    ) -> AIRoutingResult:
        """Route request to appropriate AI model."""
        
        user = await self.user_repository.get_by_telegram_id(TelegramId(telegram_id))
        if not user:
            raise ValueError("User not found")
        
        return self.ai_routing_service.route_request(
            user=user,
            task_description=task_description,
            message_content=message_content,
            context=context
        )
    
    async def analyze_personality(
        self,
        text: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Analyze personality traits from text."""
        
        system_prompt = """
        Analyze the personality traits expressed in this text.
        Return a JSON object with Big Five traits scores (0-1) and insights.
        """
        
        messages = [{"role": "user", "content": text}]
        
        try:
            response = await self._generate_anthropic_response(
                messages, system_prompt, AIModel.CLAUDE_SONNET.value
            )
            # Parse JSON response (simplified)
            return {"analysis": response}
        except Exception as e:
            logger.error(f"Error analyzing personality: {e}")
            return {}
    
    async def generate_insights(
        self,
        user_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Generate personalized insights."""
        
        system_prompt = """
        Generate personalized insights based on user data.
        Provide actionable recommendations and observations.
        """
        
        messages = [{
            "role": "user",
            "content": f"User data: {user_data}"
        }]
        
        try:
            response = await self._generate_anthropic_response(
                messages, system_prompt, AIModel.CLAUDE_SONNET.value
            )
            return {"insights": response}
        except Exception as e:
            logger.error(f"Error generating insights: {e}")
            return {}
    
    async def health_check(self) -> Dict[str, bool]:
        """Check health of AI services."""
        
        status = {"openai": False, "anthropic": False}
        
        # Test OpenAI
        try:
            await self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": "test"}],
                max_tokens=1
            )
            status["openai"] = True
        except Exception as e:
            logger.error(f"OpenAI health check failed: {e}")
        
        # Test Anthropic
        try:
            await self.anthropic_client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=1,
                messages=[{"role": "user", "content": "test"}]
            )
            status["anthropic"] = True
        except Exception as e:
            logger.error(f"Anthropic health check failed: {e}")
        
        return status
    
    async def _generate_openai_response(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str],
        model: str,
        **kwargs
    ) -> str:
        """Generate OpenAI response."""
        
        if system_prompt:
            messages.insert(0, {"role": "system", "content": system_prompt})
        
        response = await self.openai_client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=kwargs.get("max_tokens", 1024),
            **kwargs
        )
        
        return response.choices[0].message.content
    
    async def _generate_anthropic_response(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str],
        model: str,
        **kwargs
    ) -> str:
        """Generate Anthropic response."""
        
        # Filter out system messages for Anthropic
        user_messages = [msg for msg in messages if msg["role"] != "system"]
        
        response = await self.anthropic_client.messages.create(
            model=model,
            max_tokens=kwargs.get("max_tokens", 1024),
            system=system_prompt or "",
            messages=user_messages,
            **kwargs
        )
        
        return response.content[0].text