"""
Analysis Config - Настраиваемые параметры анализа

🔧 ЛЕГКО МЕНЯТЬ: Все ключевые параметры системы анализа
📊 ВЕРСИОНИРОВАНИЕ: Поддержка эволюции настроек  
🎯 ОПТИМИЗАЦИЯ: Параметры для балансировки качества и производительности
"""

from typing import Dict, List, Any
from datetime import datetime

class AnalysisConfig:
    """Центральная конфигурация системы анализа"""
    
    # === ВЕРСИОНИРОВАНИЕ ===
    ANALYSIS_VERSION = "2.0"
    CONFIG_UPDATED = "2025-09-09"
    
    # === МОДЕЛЬ ЛИЧНОСТИ ===
    
    # Big Five - базовая модель (всегда извлекаем)
    BIG_FIVE_TRAITS = [
        "openness", "conscientiousness", "extraversion", 
        "agreeableness", "neuroticism"
    ]
    
    # Динамические черты - меняются со временем
    DYNAMIC_TRAITS = [
        "resilience", "authenticity", "growth_mindset",
        "emotional_granularity", "cognitive_flexibility", 
        "self_compassion", "meaning_making"
    ]
    
    # Адаптивные черты - быстро меняющиеся состояния
    ADAPTIVE_TRAITS = [
        "current_energy", "stress_level", "openness_state",
        "creative_flow", "social_battery"
    ]
    
    # Доменные профили - активируются по domain вопроса
    DOMAIN_SPECIFIC_TRAITS = {
        "RELATIONSHIPS": ["empathy", "boundaries", "intimacy_comfort", "conflict_style"],
        "CAREER": ["ambition", "leadership", "team_orientation", "risk_tolerance"],
        "IDENTITY": ["self_awareness", "authenticity", "identity_stability"],
        "EMOTIONS": ["emotional_granularity", "regulation_skill", "alexithymia_level"],
        "CREATIVITY": ["divergent_thinking", "artistic_sensitivity", "imagination"],
        "SPIRITUALITY": ["transcendence", "meaning_seeking", "faith_orientation"],
        "MONEY": ["financial_mindset", "abundance_belief", "money_anxiety"],
        "HEALTH": ["body_awareness", "self_care", "health_anxiety"],
        "WORK": ["work_engagement", "perfectionism", "achievement_drive"],
        "PAST": ["trauma_integration", "forgiveness", "pattern_awareness"],
        "FUTURE": ["optimism", "planning_style", "change_adaptability"],
        "LIFESTYLE": ["balance_skill", "priorities_clarity", "habit_strength"]
    }
    
    # === AI МОДЕЛИ ===
    
    # Распределение моделей (основано на твоем плане оптимизации)
    AI_MODEL_SETTINGS = {
        "claude-3.5-sonnet": {
            "usage_target_percent": 10,        # ~10% самых важных
            "max_tokens": 1000,
            "temperature": 0.1,                # Высокая точность
            "timeout_ms": 5000,
            "cost_per_token": 0.000015,        # Примерная стоимость
            "use_for": [
                "complex_psychological_analysis",
                "breakthrough_moments", 
                "shadow_work",
                "deep_insights",
                "crisis_support"
            ]
        },
        
        "gpt-4o": {
            "usage_target_percent": 75,        # ~75% основных случаев
            "max_tokens": 600,
            "temperature": 0.3,                # Баланс точности/креативности
            "timeout_ms": 3000,
            "cost_per_token": 0.000005,
            "use_for": [
                "trait_extraction",
                "emotional_analysis", 
                "standard_insights",
                "relationship_dynamics"
            ]
        },
        
        "gpt-4o-mini": {
            "usage_target_percent": 15,        # ~15% простых случаев
            "max_tokens": 300,
            "temperature": 0.2,                # Низкая для классификации
            "timeout_ms": 1500,
            "cost_per_token": 0.0000015,
            "use_for": [
                "simple_classification",
                "fatigue_detection",
                "quick_validation",
                "instant_feedback"
            ]
        }
    }
    
    # Пороги сложности для выбора модели
    COMPLEXITY_THRESHOLDS = {
        "use_claude_if": {
            "complexity_score": 4.2,          # Из 5
            "emotional_weight": 4,            # Из 5  
            "insight_potential": 4,           # Из 5
            "is_breakthrough": True,
            "depth_level": ["SHADOW", "CORE"],
            "domain": ["SPIRITUALITY", "IDENTITY"],
            "energy_dynamic": ["HEAVY", "DRAINING"]
        },
        
        "use_gpt4_if": {
            "complexity_score": 1.8,          # Выше 1.8
            "has_emotional_content": True,
            "answer_length": 50,              # Более 50 символов
            "user_engagement": 0.5            # Средняя вовлеченность
        },
        
        "use_mini_if": {
            "complexity_score": 1.8,          # Ниже 1.8
            "answer_length": 20,              # Короткие ответы
            "is_simple_classification": True,
            "instant_mode": True
        }
    }
    
    # === АНАЛИЗ КАЧЕСТВА ===
    
    # Настройки детальности анализа
    ANALYSIS_DEPTH_SETTINGS = {
        "surface": {
            "triggers": {
                "question_number": [1, 2, 3, 4, 5],
                "trust_level": 0.3,            # Низкое доверие
                "energy_level": 0.3,           # Низкая энергия
                "fatigue_level": 0.7           # Высокая усталость
            },
            "word_limit": [100, 150],
            "focus": "поддержка и принятие",
            "tone": "мягкий и безопасный"
        },
        
        "flowing": {
            "triggers": {
                "question_number": [6, 25],
                "trust_level": 0.6,
                "energy_level": 0.5,
                "engagement_level": 0.6
            },
            "word_limit": [200, 300], 
            "focus": "инсайты и паттерны",
            "tone": "аналитический и поддерживающий"
        },
        
        "deep_dive": {
            "triggers": {
                "question_number": 26,         # 26+ вопросов
                "trust_level": 0.7,
                "is_breakthrough": True,
                "shadow_work_readiness": 0.6
            },
            "word_limit": [400, 600],
            "focus": "теневая работа и трансформация", 
            "tone": "глубокий и трансформирующий"
        }
    }
    
    # === БЕЗОПАСНОСТЬ И ГРАНИЦЫ ===
    
    # Правила психологической безопасности
    SAFETY_RULES = {
        "never_diagnose": True,                # Никогда не ставим диагнозы
        "always_supportive": True,             # Всегда поддерживающий тон
        "respect_boundaries": True,            # Уважение границ пользователя
        "crisis_detection": True,              # Детекция кризисных состояний
        
        # Ключевые слова требующие особого внимания
        "crisis_keywords": [
            "suicide", "суицид", "kill myself", "умереть", 
            "нет смысла", "безнадежно", "никому не нужен"
        ],
        
        # Автоматическая эскалация
        "auto_escalation": {
            "to_human_specialist": True,
            "crisis_hotline_reference": True,
            "gentle_support_mode": True
        }
    }
    
    # === PERFORMANCE ===
    
    # Настройки производительности
    PERFORMANCE_SETTINGS = {
        "instant_analysis_timeout_ms": 500,   # Быстрый анализ
        "deep_analysis_timeout_ms": 10000,    # Глубокий анализ
        
        # Батчинг для оптимизации
        "batch_processing": {
            "enabled": True,
            "batch_size": 5,
            "max_wait_seconds": 30
        },
        
        # Кэширование
        "caching": {
            "similar_answer_threshold": 0.85,  # Схожесть для переиспользования
            "cache_ttl_seconds": 3600,         # Время жизни кэша
            "max_cache_size": 1000
        }
    }
    
    # === СТОИМОСТЬ ===
    
    # Контроль расходов
    COST_CONTROL = {
        "daily_budget_per_user_usd": 0.25,    # Максимум на пользователя
        "monthly_budget_total_usd": 100,       # Общий бюджет
        
        # Переключение на дешевые модели при лимите
        "budget_protection": {
            "switch_to_mini_at_percent": 80,   # При 80% бюджета
            "stop_claude_at_percent": 90,      # При 90% бюджета
            "emergency_mode_at_percent": 95    # При 95% только мини
        },
        
        # Отслеживание трендов
        "cost_tracking": {
            "log_every_request": True,
            "daily_reports": True,
            "cost_optimization_suggestions": True
        }
    }
    
    # === ЭКСПЕРИМЕНТАЛЬНЫЕ НАСТРОЙКИ ===
    
    # A/B тесты и эксперименты 
    EXPERIMENTAL = {
        "personality_timeline": {
            "enabled": True,
            "track_evolution": True,
            "detect_breakthroughs": True
        },
        
        "similar_users_matching": {
            "enabled": False,  # Пока отключено
            "min_users_for_matching": 100
        },
        
        "adaptive_prompts": {
            "enabled": True,
            "learn_from_feedback": True,
            "auto_optimize": False  # Ручная проверка изменений
        }
    }
    
    # === СЛУЖЕБНЫЕ МЕТОДЫ ===
    
    @classmethod
    def get_traits_for_domain(cls, domain: str) -> List[str]:
        """Получить релевантные черты для домена"""
        base_traits = cls.BIG_FIVE_TRAITS + cls.DYNAMIC_TRAITS
        domain_traits = cls.DOMAIN_SPECIFIC_TRAITS.get(domain, [])
        return base_traits + domain_traits
    
    @classmethod 
    def should_use_claude(cls, question_metadata: Dict, context: Dict) -> bool:
        """Определить нужен ли Claude для этого вопроса"""
        
        # Проверяем рекомендацию из метаданных
        if question_metadata.get("processing_hints", {}).get("recommended_model") == "claude-3.5-sonnet":
            return True
        
        # Считаем complexity_score
        complexity_score = (
            question_metadata["psychology"]["complexity"] * 0.3 +
            question_metadata["psychology"]["emotional_weight"] * 0.3 +
            question_metadata["psychology"]["insight_potential"] * 0.2 +
            (5 - question_metadata["psychology"]["safety_level"]) * 0.2
        )
        
        # Проверяем пороги
        thresholds = cls.COMPLEXITY_THRESHOLDS["use_claude_if"]
        
        return (
            complexity_score >= thresholds["complexity_score"] or
            context.get("is_breakthrough", False) or
            question_metadata["classification"]["depth_level"] in thresholds["depth_level"] or
            question_metadata["classification"]["domain"] in thresholds["domain"] or
            question_metadata["classification"]["energy_dynamic"] in thresholds["energy_dynamic"]
        )
    
    @classmethod
    def get_analysis_depth(cls, question_number: int, trust_level: float, energy_level: float, fatigue_level: float = 0.0) -> str:
        """Определить уровень детальности анализа"""
        
        # Проверяем каждый уровень
        for depth_name, settings in cls.ANALYSIS_DEPTH_SETTINGS.items():
            triggers = settings["triggers"]
            
            # Проверяем условия для этого уровня
            if depth_name == "surface":
                if (question_number <= max(triggers["question_number"]) or 
                    trust_level <= triggers["trust_level"] or
                    energy_level <= triggers["energy_level"] or
                    fatigue_level >= triggers["fatigue_level"]):
                    return "surface"
                    
            elif depth_name == "flowing":
                if (triggers["question_number"][0] <= question_number <= triggers["question_number"][1] and
                    trust_level >= triggers["trust_level"] and
                    energy_level >= triggers["energy_level"]):
                    return "flowing"
                    
            elif depth_name == "deep_dive":
                if (question_number >= triggers["question_number"] and
                    trust_level >= triggers["trust_level"]):
                    return "deep_dive"
        
        # Fallback
        return "flowing"