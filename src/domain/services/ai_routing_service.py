"""AI routing domain service."""

from dataclasses import dataclass
from typing import Optional, Dict, Any

from ..entities import User
from ..value_objects import AIModel, TaskComplexity, AI_MODEL_METADATA


@dataclass
class AIRoutingResult:
    """Result of AI routing decision."""
    
    model: AIModel
    reasoning: str
    estimated_cost: float
    complexity: TaskComplexity
    downgraded: bool = False


class AIRoutingService:
    """Domain service for AI model routing decisions."""
    
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
    
    def route_request(
        self,
        user: User,
        task_description: str,
        message_content: str = "",
        context: Optional[Dict[str, Any]] = None
    ) -> AIRoutingResult:
        """Route AI request to optimal model based on complexity and user tier."""
        
        complexity = self._assess_complexity(task_description, message_content, context)
        model, downgraded = self._select_model(complexity, user)
        metadata = AI_MODEL_METADATA[model]
        
        return AIRoutingResult(
            model=model,
            reasoning=self._get_routing_reasoning(complexity, model, user, downgraded),
            estimated_cost=metadata.cost_per_request,
            complexity=complexity,
            downgraded=downgraded
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
    
    def _select_model(self, complexity: TaskComplexity, user: User) -> tuple[AIModel, bool]:
        """Select AI model based on complexity and user tier."""
        
        downgraded = False
        
        # Free tier limitations
        if not user.is_premium:
            if complexity == TaskComplexity.DEEP:
                downgraded = True
                return AIModel.GPT_4, downgraded  # Downgrade from Claude
            elif complexity == TaskComplexity.DAILY:
                downgraded = True
                return AIModel.GPT_4O_MINI, downgraded  # Downgrade from GPT-4
            else:
                return AIModel.GPT_4O_MINI, downgraded
        
        # Premium/Professional tier routing
        if complexity == TaskComplexity.SIMPLE:
            return AIModel.GPT_4O_MINI, downgraded
        elif complexity == TaskComplexity.DAILY:
            return AIModel.GPT_4, downgraded
        else:  # DEEP
            return AIModel.CLAUDE_SONNET, downgraded
    
    def _get_routing_reasoning(
        self,
        complexity: TaskComplexity,
        model: AIModel,
        user: User,
        downgraded: bool
    ) -> str:
        """Get human-readable reasoning for the routing decision."""
        
        base_reasons = {
            TaskComplexity.SIMPLE: "Simple validation/categorization task",
            TaskComplexity.DAILY: "Daily interaction requiring conversational AI",
            TaskComplexity.DEEP: "Complex psychological analysis requiring advanced reasoning"
        }
        
        tier_suffix = ""
        if not user.is_premium and downgraded:
            if complexity == TaskComplexity.DEEP:
                tier_suffix = " (downgraded to GPT-4 for free tier)"
            elif complexity == TaskComplexity.DAILY:
                tier_suffix = " (downgraded to GPT-4o-mini for free tier)"
        
        return f"{base_reasons[complexity]}{tier_suffix}. Using {model.value}."