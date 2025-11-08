"""AI model value objects."""

from enum import Enum
from dataclasses import dataclass
from typing import Dict


class TaskComplexity(Enum):
    """Task complexity levels for AI routing."""
    SIMPLE = "simple"           # Validation, categorization, simple responses
    DAILY = "daily"             # Daily chat, emotional analysis, basic insights  
    DEEP = "deep"              # Psychological analysis, personality assessment


class AIModel(Enum):
    """Available AI models."""
    GPT_4O_MINI = "gpt-4o-mini"
    GPT_4 = "gpt-4"
    CLAUDE_SONNET = "claude-3-5-sonnet-20241022"


@dataclass(frozen=True)
class AIModelMetadata:
    """Metadata for AI models."""
    
    model: AIModel
    cost_per_request: float
    max_tokens: int
    context_window: int
    best_for: list[TaskComplexity]
    
    
# Model metadata registry
AI_MODEL_METADATA: Dict[AIModel, AIModelMetadata] = {
    AIModel.GPT_4O_MINI: AIModelMetadata(
        model=AIModel.GPT_4O_MINI,
        cost_per_request=0.01,
        max_tokens=4096,
        context_window=128000,
        best_for=[TaskComplexity.SIMPLE]
    ),
    AIModel.GPT_4: AIModelMetadata(
        model=AIModel.GPT_4, 
        cost_per_request=0.05,
        max_tokens=4096,
        context_window=8192,
        best_for=[TaskComplexity.DAILY]
    ),
    AIModel.CLAUDE_SONNET: AIModelMetadata(
        model=AIModel.CLAUDE_SONNET,
        cost_per_request=0.15,
        max_tokens=4096,
        context_window=200000,
        best_for=[TaskComplexity.DEEP, TaskComplexity.DAILY]
    )
}