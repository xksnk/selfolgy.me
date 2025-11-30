"""
Chat MVP Service - AI Coach Chat based on research architecture.

Архитектура:
- UserDossierService: AI-генерация резюме личности (~500 токенов вместо 10K+)
- SessionManager: Управление сессией (Foundation → Exploration → Integration)
- ChatMVP: Основной чат с персонализацией на основе досье

Принципы:
- Без смешивания программ в одной сессии
- Адаптивные переходы при сопротивлении
- Коуч ЗНАЕТ ВСЁ о пользователе через досье
"""

from .session_manager import SessionManager, SessionState, BlockType
from .chat_mvp import ChatMVP, ChatResponse, UserKnowledge
from .user_dossier_service import UserDossierService, UserDossier
from .dossier_validator import (
    DossierValidator,
    CorrectionDetector,
    CheckInManager,
    DetectedCorrection,
    CheckInRequest
)

__all__ = [
    'ChatMVP',
    'ChatResponse',
    'UserKnowledge',
    'SessionManager',
    'SessionState',
    'BlockType',
    'UserDossierService',
    'UserDossier',
    'DossierValidator',
    'CorrectionDetector',
    'CheckInManager',
    'DetectedCorrection',
    'CheckInRequest'
]
