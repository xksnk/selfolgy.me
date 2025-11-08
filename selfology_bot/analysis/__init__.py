"""
Analysis System - Отдельная настраиваемая система анализа ответов

🔬 КОМПОНЕНТЫ:
- AnalysisConfig: Все настройки системы
- AnalysisTemplates: AI промпты для разных моделей и ситуаций
- AIModelRouter: Умный выбор AI модели (будет добавлен в Task 2.2)
- TraitExtractor: Извлечение черт личности (будет добавлен в Task 2.3)
- AnswerAnalyzer: Главный анализатор (будет добавлен в Task 2.4)
- EmbeddingCreator: Векторы для Qdrant (будет добавлен в Task 2.5)

🎯 ФИЛОСОФИЯ:
"Каждый ответ - это штрих в портрете души"
Создаем живой, эволюционирующий портрет личности.
"""

from .analysis_config import AnalysisConfig
from .analysis_templates import AnalysisTemplates
from .ai_model_router import AIModelRouter
from .trait_extractor import TraitExtractor
from .answer_analyzer import AnswerAnalyzer
from .embedding_creator import EmbeddingCreator
from .personality_extractor import PersonalityExtractor

__all__ = [
    'AnalysisConfig',
    'AnalysisTemplates',
    'AIModelRouter',
    'TraitExtractor',
    'AnswerAnalyzer',
    'EmbeddingCreator',
    'PersonalityExtractor'
]

# Версия всей analysis системы
__version__ = "2.0.0"