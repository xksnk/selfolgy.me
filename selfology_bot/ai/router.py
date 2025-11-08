from enum import Enum
from typing import Optional, Dict, Any
from dataclasses import dataclass
import re


class TaskComplexity(Enum):
    SIMPLE = "simple"           # Validation, categorization, simple responses
    DAILY = "daily"             # Daily chat, emotional analysis, basic insights
    DEEP = "deep"              # Psychological analysis, personality assessment


class AIModel(Enum):
    GPT_4O_MINI = "gpt-4o-mini"
    GPT_4 = "gpt-4"
    CLAUDE_SONNET = "claude-3-5-sonnet-20241022"


@dataclass
class AIRouterResult:
    model: AIModel
    reasoning: str
    estimated_cost: float
    complexity: TaskComplexity


class AIRouter:
    """
    Intelligent AI model selection based on task complexity and cost optimization.
    
    Routing Logic:
    - Simple tasks (80% of requests) → GPT-4o-mini ($0.01)
    - Daily interactions (15% of requests) → GPT-4 ($0.05) 
    - Deep analysis (5% of requests) → Claude Sonnet ($0.15)
    """
    
    COST_ESTIMATES = {
        AIModel.GPT_4O_MINI: 0.01,
        AIModel.GPT_4: 0.05,
        AIModel.CLAUDE_SONNET: 0.15
    }
    
    SIMPLE_KEYWORDS = [
        "validate", "check", "categorize", "tag", "classify", 
        "yes/no", "true/false", "quick", "simple"
    ]
    
    DEEP_KEYWORDS = [
        "analyze personality", "psychological", "deep analysis", 
        "personality assessment", "psychological profile", 
        "complex analysis", "strategic", "life planning"
    ]
    
    DAILY_KEYWORDS = [
        "chat", "daily", "mood", "feeling", "emotional", 
        "advice", "coaching", "journal", "reflection"
    ]
    
    def __init__(self, user_tier: str = "free"):
        self.user_tier = user_tier
    
    def route_request(
        self, 
        task_description: str, 
        message_content: str = "", 
        context: Optional[Dict[str, Any]] = None
    ) -> AIRouterResult:
        """
        Route AI request to optimal model based on task complexity and user tier.
        """
        complexity = self._assess_complexity(task_description, message_content, context)
        model = self._select_model(complexity)
        
        return AIRouterResult(
            model=model,
            reasoning=self._get_routing_reasoning(complexity, model),
            estimated_cost=self.COST_ESTIMATES[model],
            complexity=complexity
        )
    
    def _assess_complexity(
        self, 
        task_description: str, 
        message_content: str, 
        context: Optional[Dict[str, Any]]
    ) -> TaskComplexity:
        """Assess task complexity based on content analysis."""
        
        full_text = f"{task_description} {message_content}".lower()
        
        # Check for deep analysis indicators
        if any(keyword in full_text for keyword in self.DEEP_KEYWORDS):
            return TaskComplexity.DEEP
        
        # Check for simple task indicators  
        if any(keyword in full_text for keyword in self.SIMPLE_KEYWORDS):
            return TaskComplexity.SIMPLE
        
        # Check for daily interaction indicators
        if any(keyword in full_text for keyword in self.DAILY_KEYWORDS):
            return TaskComplexity.DAILY
        
        # Length-based complexity assessment
        if len(message_content) < 50:
            return TaskComplexity.SIMPLE
        elif len(message_content) > 300:
            return TaskComplexity.DEEP
        
        # Context-based complexity
        if context:
            if context.get("questionnaire_type") in ["personality", "deep_assessment"]:
                return TaskComplexity.DEEP
            if context.get("is_onboarding"):
                return TaskComplexity.DEEP
            if context.get("daily_checkin"):
                return TaskComplexity.DAILY
        
        # Default to daily interaction
        return TaskComplexity.DAILY
    
    def _select_model(self, complexity: TaskComplexity) -> AIModel:
        """Select AI model based on complexity and user tier."""
        
        # Free tier limitations
        if self.user_tier == "free":
            if complexity == TaskComplexity.DEEP:
                return AIModel.GPT_4  # Downgrade from Claude for free users
            elif complexity == TaskComplexity.DAILY:
                return AIModel.GPT_4O_MINI  # Downgrade from GPT-4 for free users
            else:
                return AIModel.GPT_4O_MINI
        
        # Premium/Professional tier routing
        if complexity == TaskComplexity.SIMPLE:
            return AIModel.GPT_4O_MINI
        elif complexity == TaskComplexity.DAILY:
            return AIModel.GPT_4
        else:  # DEEP
            return AIModel.CLAUDE_SONNET
    
    def _get_routing_reasoning(self, complexity: TaskComplexity, model: AIModel) -> str:
        """Get human-readable reasoning for the routing decision."""
        
        base_reasons = {
            TaskComplexity.SIMPLE: "Simple validation/categorization task",
            TaskComplexity.DAILY: "Daily interaction requiring conversational AI",
            TaskComplexity.DEEP: "Complex psychological analysis requiring advanced reasoning"
        }
        
        tier_suffix = ""
        if self.user_tier == "free":
            if complexity == TaskComplexity.DEEP:
                tier_suffix = " (downgraded to GPT-4 for free tier)"
            elif complexity == TaskComplexity.DAILY:
                tier_suffix = " (downgraded to GPT-4o-mini for free tier)"
        
        return f"{base_reasons[complexity]}{tier_suffix}. Using {model.value}."