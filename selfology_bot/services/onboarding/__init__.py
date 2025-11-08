"""
Onboarding System - Чистая архитектура для умного онбординга

Компоненты:
- OnboardingOrchestrator: Главный управляющий
- QuestionRouter: Умный выбор вопросов (алгоритм "Умный Микс")
- SessionManager: Управление сессиями
- FatigueDetector: Определение усталости пользователя
- OnboardingConfig: Настройки системы
"""

from .orchestrator import OnboardingOrchestrator
from .fatigue_detector import FatigueDetector

__all__ = ['OnboardingOrchestrator', 'FatigueDetector']