#!/usr/bin/env python3
"""
AI MODEL ROUTER - Умный роутер для выбора подходящей AI модели для разных задач
Оптимизирует затраты и качество анализа
"""

import os
import json
from enum import Enum
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

class AnalysisTask(Enum):
    """Типы задач анализа"""
    QUESTION_CLASSIFICATION = "question_classification"    # Классификация вопросов
    ANSWER_ANALYSIS = "answer_analysis"                   # Анализ ответов пользователей
    PERSONALITY_BUILDING = "personality_building"         # Построение личности
    QUESTION_CONNECTIONS = "question_connections"         # Связи между вопросами  
    SIMILARITY_DETECTION = "similarity_detection"        # Поиск похожих вопросов
    EMOTIONAL_ANALYSIS = "emotional_analysis"            # Эмоциональный анализ
    TEXT_EMBEDDING = "text_embedding"                    # Векторизация текста

class AIModel(Enum):
    """Доступные AI модели"""
    GPT_4O_MINI = "gpt-4o-mini"                 # Быстрый и дешевый
    GPT_4O = "gpt-4o"                           # Балансированный
    CLAUDE_SONNET = "claude-3-5-sonnet-20241022"   # Глубокий анализ
    CLAUDE_HAIKU = "claude-3-haiku-20240307"    # Быстрый и точный
    TEXT_EMBEDDING_SMALL = "text-embedding-3-small"  # Векторизация

@dataclass
class ModelSpec:
    """Спецификация модели"""
    name: str
    cost_per_1k_tokens: float
    speed: str  # fast/medium/slow
    quality: str  # basic/good/excellent
    best_for: List[str]

class AIModelRouter:
    """Умный роутер AI моделей"""
    
    def __init__(self):
        # Загружаем API ключи
        self.load_api_keys()
        
        # Спецификации моделей
        self.models = {
            AIModel.GPT_4O_MINI: ModelSpec(
                name="GPT-4o-mini",
                cost_per_1k_tokens=0.00015,
                speed="fast", 
                quality="good",
                best_for=["batch_classification", "simple_analysis", "routing_decisions"]
            ),
            AIModel.GPT_4O: ModelSpec(
                name="GPT-4o", 
                cost_per_1k_tokens=0.005,
                speed="medium",
                quality="excellent", 
                best_for=["complex_analysis", "nuanced_understanding"]
            ),
            AIModel.CLAUDE_SONNET: ModelSpec(
                name="Claude-3.5-Sonnet",
                cost_per_1k_tokens=0.003,
                speed="medium",
                quality="excellent",
                best_for=["deep_analysis", "personality_building", "psychological_insights"]
            ),
            AIModel.CLAUDE_HAIKU: ModelSpec(
                name="Claude-3-Haiku",
                cost_per_1k_tokens=0.00025,
                speed="fast",
                quality="good", 
                best_for=["quick_classification", "pattern_detection"]
            ),
            AIModel.TEXT_EMBEDDING_SMALL: ModelSpec(
                name="text-embedding-3-small",
                cost_per_1k_tokens=0.00002,
                speed="very_fast",
                quality="specialized",
                best_for=["vectorization", "similarity_search"]
            )
        }
        
        # Правила выбора модели для каждой задачи
        self.task_routing = {
            AnalysisTask.QUESTION_CLASSIFICATION: {
                "primary": AIModel.GPT_4O_MINI,    # дешево и достаточно
                "fallback": AIModel.CLAUDE_HAIKU,
                "batch_size": 25,
                "reasoning": "Массовая классификация не требует максимального качества"
            },
            AnalysisTask.ANSWER_ANALYSIS: {
                "primary": AIModel.CLAUDE_SONNET,   # глубокий анализ психологии
                "fallback": AIModel.GPT_4O,
                "batch_size": 1,
                "reasoning": "Анализ ответов критически важен для точности"
            },
            AnalysisTask.PERSONALITY_BUILDING: {
                "primary": AIModel.CLAUDE_SONNET,   # лучший для психологии
                "fallback": AIModel.GPT_4O,
                "batch_size": 5,
                "reasoning": "Построение личности требует глубокого понимания"
            },
            AnalysisTask.QUESTION_CONNECTIONS: {
                "primary": AIModel.GPT_4O_MINI,     # быстро для больших объемов
                "fallback": AIModel.CLAUDE_HAIKU,
                "batch_size": 50,
                "reasoning": "Поиск связей - вычислительная задача"
            },
            AnalysisTask.SIMILARITY_DETECTION: {
                "primary": AIModel.TEXT_EMBEDDING_SMALL,  # специализированная модель
                "fallback": AIModel.GPT_4O_MINI,
                "batch_size": 100,
                "reasoning": "Embeddings точнее для семантической схожести"
            },
            AnalysisTask.EMOTIONAL_ANALYSIS: {
                "primary": AIModel.CLAUDE_SONNET,   # лучше понимает эмоции
                "fallback": AIModel.GPT_4O,
                "batch_size": 10,
                "reasoning": "Эмоциональный анализ требует тонкого понимания"
            }
        }
    
    def load_api_keys(self):
        """Загружает API ключи из .env файла"""
        self.api_keys = {}
        try:
            with open('.env', 'r') as f:
                for line in f:
                    if '=' in line and not line.startswith('#'):
                        key, value = line.strip().split('=', 1)
                        self.api_keys[key] = value
            print("✅ API ключи загружены")
        except FileNotFoundError:
            print("❌ Файл .env не найден")
    
    def select_optimal_model(self, task: AnalysisTask, data_size: int = 1, 
                           priority: str = "balanced") -> Dict[str, Any]:
        """Выбирает оптимальную модель для задачи"""
        
        task_config = self.task_routing[task]
        selected_model = task_config["primary"]
        
        # Корректируем выбор на основе приоритета
        if priority == "cost":
            # Выбираем самую дешевую подходящую модель
            if task in [AnalysisTask.QUESTION_CLASSIFICATION, AnalysisTask.QUESTION_CONNECTIONS]:
                selected_model = AIModel.GPT_4O_MINI
        elif priority == "quality":
            # Выбираем лучшую модель независимо от стоимости
            if task in [AnalysisTask.ANSWER_ANALYSIS, AnalysisTask.PERSONALITY_BUILDING]:
                selected_model = AIModel.CLAUDE_SONNET
        
        model_spec = self.models[selected_model]
        
        # Рассчитываем стоимость
        estimated_tokens = self._estimate_tokens(task, data_size)
        estimated_cost = estimated_tokens * model_spec.cost_per_1k_tokens / 1000
        
        return {
            "selected_model": selected_model.value,
            "model_spec": model_spec,
            "task_config": task_config,
            "estimated_cost": estimated_cost,
            "estimated_tokens": estimated_tokens,
            "batch_size": task_config["batch_size"],
            "reasoning": task_config["reasoning"]
        }
    
    def _estimate_tokens(self, task: AnalysisTask, data_size: int) -> int:
        """Оценивает количество токенов для задачи"""
        
        # Базовые оценки токенов на основе типа задачи
        token_estimates = {
            AnalysisTask.QUESTION_CLASSIFICATION: 300,  # промпт + ответ
            AnalysisTask.ANSWER_ANALYSIS: 500,         # более глубокий анализ
            AnalysisTask.PERSONALITY_BUILDING: 800,    # комплексный анализ
            AnalysisTask.QUESTION_CONNECTIONS: 200,    # простое сравнение
            AnalysisTask.EMOTIONAL_ANALYSIS: 400      # средняя сложность
        }
        
        base_tokens = token_estimates.get(task, 300)
        return base_tokens * data_size
    
    def create_cost_optimization_plan(self, total_questions: int) -> Dict[str, Any]:
        """Создает план оптимизации затрат"""
        
        print("💰 Создаем план оптимизации затрат...")
        
        # Разные стратегии обработки
        strategies = {
            "aggressive_cost_saving": {
                "core_questions": 100,    # только ключевые вопросы
                "batch_classification": True,
                "primary_model": AIModel.GPT_4O_MINI,
                "estimated_cost": 0.08,
                "quality": "good_enough"
            },
            "balanced": {
                "core_questions": 300,    # треть всех вопросов  
                "mixed_models": True,
                "estimated_cost": 0.25,
                "quality": "high"
            },
            "premium_quality": {
                "all_questions": total_questions,
                "best_models": True,
                "estimated_cost": 0.60,
                "quality": "excellent"
            }
        }
        
        # Рекомендация
        recommendation = {
            "recommended_strategy": "balanced",
            "reasoning": "Оптимальное соотношение цена/качество для MVP",
            "phased_approach": {
                "phase_1": "100 ключевых вопросов с полными метаданными",
                "phase_2": "200 основных вопросов с базовой классификацией", 
                "phase_3": "393 остальных по мере необходимости"
            }
        }
        
        return {
            "strategies": strategies,
            "recommendation": recommendation
        }
    
    def generate_classification_prompts(self):
        """Генерирует промпты для разных типов анализа"""
        
        prompts = {
            "question_classification": """
Классифицируй эти вопросы психологического опросника по системе:

JOURNEY_STAGE: ENTRY/WARMING/EXPLORING/DEEPENING/BREAKTHROUGH/INTEGRATION
DEPTH_LEVEL: SURFACE/CONSCIOUS/EDGE/SHADOW/CORE  
DOMAIN: IDENTITY/EMOTIONS/RELATIONSHIPS/WORK/CREATIVITY/SPIRITUALITY/etc
ENERGY: OPENING/NEUTRAL/PROCESSING/HEAVY/HEALING

Для каждого вопроса добавь:
- complexity (1-5): сложность понимания
- emotional_weight (1-5): эмоциональная нагрузка
- insight_potential (1-5): потенциал глубоких инсайтов
- safety_level (1-5): безопасность для новичков

ВОПРОСЫ:
{questions}

JSON ответ с analysis массивом.
""",
            
            "answer_analysis": """
Проанализируй этот ответ пользователя на психологический вопрос:

ВОПРОС: "{question}"
ОТВЕТ: "{answer}"

Определи:
1. Эмоциональное состояние (positive/neutral/negative + intensity 1-5)
2. Уровень открытости (1-5) 
3. Признаки избегания или сопротивления
4. Ключевые психологические маркеры
5. Рекомендации для следующего вопроса

JSON ответ с детальным анализом.
""",
            
            "personality_vector_update": """
На основе этого ответа обнови векторную модель личности пользователя:

ОТВЕТ: "{answer}"
ТЕКУЩИЙ ВЕКТОР: {current_vector}

Определи изменения для каждого измерения (-1.0 до +1.0):
- self_awareness, emotional_intelligence, openness, conscientiousness
- extraversion, agreeableness, neuroticism, growth_mindset
- life_satisfaction, resilience, authenticity, meaning_making

JSON с обновлениями вектора + объяснением.
""",
            
            "connection_analysis": """
Найди семантические связи между этими вопросами:

БАЗОВЫЙ ВОПРОС: "{base_question}"
КАНДИДАТЫ: {candidate_questions}

Для каждого кандидата определи:
1. Тип связи: logical_sequence/thematic_cluster/depth_progression/emotional_bridge
2. Силу связи (0.0-1.0)
3. Направление: bidirectional/from_base/to_base
4. Рекомендуемый порядок

JSON с массивом connections.
"""
        }
        
        with open('ai_analysis_prompts.json', 'w', encoding='utf-8') as f:
            json.dump(prompts, f, ensure_ascii=False, indent=2)
        
        print("✅ Промпты для AI анализа созданы: ai_analysis_prompts.json")

def main():
    """Демонстрация работы роутера"""
    
    print("🧠 AI MODEL ROUTER")
    print("🎯 Умный выбор AI модели для каждой задачи")
    print("=" * 60)
    
    router = AIModelRouter()
    
    # Демо: выбор моделей для разных задач
    tasks_demo = [
        (AnalysisTask.QUESTION_CLASSIFICATION, 693, "cost"),
        (AnalysisTask.ANSWER_ANALYSIS, 1, "quality"),
        (AnalysisTask.PERSONALITY_BUILDING, 5, "balanced"),
        (AnalysisTask.SIMILARITY_DETECTION, 100, "cost")
    ]
    
    total_estimated_cost = 0
    
    print("\n📊 РЕКОМЕНДАЦИИ ПО МОДЕЛЯМ:")
    for task, data_size, priority in tasks_demo:
        recommendation = router.select_optimal_model(task, data_size, priority)
        total_estimated_cost += recommendation["estimated_cost"]
        
        print(f"\n🎯 {task.value}:")
        print(f"  📱 Модель: {recommendation['selected_model']}")
        print(f"  💰 Стоимость: ${recommendation['estimated_cost']:.4f}")
        print(f"  📊 Размер батча: {recommendation['batch_size']}")
        print(f"  💡 Обоснование: {recommendation['reasoning']}")
    
    print(f"\n💰 ОБЩАЯ СТОИМОСТЬ АНАЛИЗА: ${total_estimated_cost:.2f}")
    
    # Создаем план оптимизации
    cost_plan = router.create_cost_optimization_plan(693)
    
    print(f"\n📋 РЕКОМЕНДУЕМАЯ СТРАТЕГИЯ:")
    print(f"🎯 {cost_plan['recommendation']['recommended_strategy']}")
    print(f"💡 {cost_plan['recommendation']['reasoning']}")
    
    # Создаем промпты
    router.generate_classification_prompts()
    
    print(f"\n✅ AI роутер готов к работе!")

if __name__ == "__main__":
    main()