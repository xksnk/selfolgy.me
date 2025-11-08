from typing import Dict, Any, Optional
from abc import ABC, abstractmethod
import asyncio
import httpx
from anthropic import AsyncAnthropic
from openai import AsyncOpenAI

from ..core.config import settings
from .router import AIModel


class BaseAIClient(ABC):
    """Base class for AI clients"""
    
    @abstractmethod
    async def chat_completion(
        self, 
        messages: list, 
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> str:
        pass


class AnthropicClient(BaseAIClient):
    """Claude/Anthropic API client"""
    
    def __init__(self):
        self.client = AsyncAnthropic(api_key=settings.anthropic_api_key)
    
    async def chat_completion(
        self, 
        messages: list, 
        system_prompt: Optional[str] = None,
        model: str = "claude-3-5-sonnet-20241022",
        max_tokens: int = 1024,
        **kwargs
    ) -> str:
        try:
            # Convert OpenAI format to Anthropic format
            anthropic_messages = []
            for msg in messages:
                if msg["role"] != "system":  # System handled separately
                    anthropic_messages.append({
                        "role": msg["role"],
                        "content": msg["content"]
                    })
            
            response = await self.client.messages.create(
                model=model,
                max_tokens=max_tokens,
                system=system_prompt if system_prompt else "",
                messages=anthropic_messages,
                **kwargs
            )
            
            return response.content[0].text
            
        except Exception as e:
            raise Exception(f"Anthropic API error: {str(e)}")


class OpenAIClient(BaseAIClient):
    """OpenAI GPT client"""
    
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
    
    async def chat_completion(
        self, 
        messages: list, 
        system_prompt: Optional[str] = None,
        model: str = "gpt-4",
        max_tokens: int = 1024,
        **kwargs
    ) -> str:
        try:
            # Add system prompt to messages if provided
            if system_prompt and messages[0]["role"] != "system":
                messages.insert(0, {"role": "system", "content": system_prompt})
            
            response = await self.client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                **kwargs
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            raise Exception(f"OpenAI API error: {str(e)}")


class AIClientManager:
    """
    Manages AI clients and handles routing to appropriate models.
    """
    
    def __init__(self):
        self.anthropic_client = AnthropicClient()
        self.openai_client = OpenAIClient()
        
        self.model_mapping = {
            AIModel.CLAUDE_SONNET: self.anthropic_client,
            AIModel.GPT_4: self.openai_client,
            AIModel.GPT_4O_MINI: self.openai_client
        }
    
    async def generate_response(
        self,
        model: AIModel,
        messages: list,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> str:
        """Generate response using specified model"""
        
        client = self.model_mapping[model]
        
        # Set model-specific parameters
        if model == AIModel.CLAUDE_SONNET:
            kwargs.setdefault("model", "claude-3-5-sonnet-20241022")
        elif model == AIModel.GPT_4:
            kwargs.setdefault("model", "gpt-4")
        elif model == AIModel.GPT_4O_MINI:
            kwargs.setdefault("model", "gpt-4o-mini")
        
        return await client.chat_completion(
            messages=messages,
            system_prompt=system_prompt,
            **kwargs
        )
    
    async def health_check(self) -> Dict[str, bool]:
        """Check if AI services are available"""
        
        status = {}
        
        # Test OpenAI
        try:
            await self.openai_client.chat_completion(
                messages=[{"role": "user", "content": "test"}],
                max_tokens=1
            )
            status["openai"] = True
        except:
            status["openai"] = False
        
        # Test Anthropic
        try:
            await self.anthropic_client.chat_completion(
                messages=[{"role": "user", "content": "test"}],
                max_tokens=1
            )
            status["anthropic"] = True
        except:
            status["anthropic"] = False
        
        return status


# Global instance
ai_client_manager = AIClientManager()