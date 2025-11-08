"""Domain repository interfaces."""

from .user_repository import IUserRepository
from .personality_repository import IPersonalityRepository
from .chat_repository import IChatRepository
from .assessment_repository import IAssessmentRepository

__all__ = [
    "IUserRepository",
    "IPersonalityRepository", 
    "IChatRepository",
    "IAssessmentRepository",
]