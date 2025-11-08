"""
AI Model Router - Умный выбор AI модели

🧠 ПРИНЦИП: "Выбираем AI как выбираем психолога - под задачу и момент"
💰 ОПТИМИЗАЦИЯ: Баланс качества и стоимости (план: Claude 10%, GPT-4o 75%, Mini 15%)  
🎯 АДАПТИВНОСТЬ: Матрица "Глубина × Важность × Контекст"
"""

import logging
from typing import Dict, Any, Optional, Tuple
from datetime import datetime
import asyncio

from .analysis_config import AnalysisConfig

logger = logging.getLogger(__name__)

class AIModelRouter:
    """
    Интеллектуальный роутер AI моделей
    
    Выбирает оптимальную модель на основе:
    - Сложности вопроса и ответа
    - Эмоциональной важности момента  
    - Контекста пользователя и сессии
    - Бюджетных ограничений
    """
    
    def __init__(self):
        """Инициализация роутера"""
        self.config = AnalysisConfig()
        
        # Статистика использования для оптимизации
        self.usage_stats = {
            "claude-3.5-sonnet": {"requests": 0, "total_cost": 0.0, "avg_quality": 0.0},
            "gpt-4o": {"requests": 0, "total_cost": 0.0, "avg_quality": 0.0},
            "gpt-4o-mini": {"requests": 0, "total_cost": 0.0, "avg_quality": 0.0}
        }
        
        # Дневной бюджет tracker
        self.daily_spending = 0.0
        self.daily_budget = self.config.COST_CONTROL["daily_budget_per_user_usd"]
        
        logger.info("🤖 AIModelRouter initialized with smart selection matrix")
    
    async def select_model_for_analysis(
        self, 
        question_metadata: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Главный метод выбора модели
        
        Args:
            question_metadata: Полные метаданные вопроса (17 параметров)
            context: Контекст пользователя и сессии
            
        Returns:
            Tuple[model_name, model_config] 
        """
        
        try:
            # 1. Проверяем бюджетные ограничения
            budget_constraint = self._check_budget_constraints()
            
            # 2. Проверяем прямую рекомендацию из метаданных вопроса
            if recommended_model := self._get_metadata_recommendation(question_metadata):
                if self._can_afford_model(recommended_model, budget_constraint):
                    logger.info(f"🎯 Using metadata recommendation: {recommended_model}")
                    return self._get_model_config(recommended_model, "metadata_recommended")
            
            # 3. Считаем оценку важности момента
            moment_score = self._calculate_moment_score(question_metadata, context)
            
            # 4. Проверяем специальные триггеры для Claude
            if self._should_use_claude(question_metadata, context, moment_score, budget_constraint):
                logger.info(f"🧠 Selecting Claude for critical moment (score: {moment_score:.2f})")
                return self._get_model_config("claude-3.5-sonnet", "critical_analysis")
            
            # 5. Проверяем пороги для GPT-4o  
            if self._should_use_gpt4o(question_metadata, context, moment_score):
                logger.info(f"🎭 Selecting GPT-4o for standard analysis (score: {moment_score:.2f})")
                return self._get_model_config("gpt-4o", "standard_analysis")
            
            # 6. Fallback на GPT-4o-mini
            logger.info(f"⚡ Selecting GPT-4o-mini for simple task (score: {moment_score:.2f})")
            return self._get_model_config("gpt-4o-mini", "simple_classification")
            
        except Exception as e:
            logger.error(f"❌ Error in model selection: {e}")
            # Emergency fallback
            return self._get_model_config("gpt-4o-mini", "error_fallback")
    
    def _calculate_moment_score(self, question_metadata: Dict, context: Dict) -> float:
        """
        Рассчитать важность момента по матрице "Глубина × Важность × Контекст"
        
        Returns:
            Оценка от 0 до 5 (чем выше, тем важнее момент)
        """
        
        psychology = question_metadata.get("psychology", {})
        classification = question_metadata.get("classification", {})
        
        # Базовые веса из метаданных (каждый от 0 до 1)
        emotional_weight = psychology.get("emotional_weight", 1) / 5.0  
        insight_potential = psychology.get("insight_potential", 1) / 5.0
        complexity = psychology.get("complexity", 1) / 5.0
        safety_level = psychology.get("safety_level", 5) / 5.0
        
        # Контекстные модификаторы
        trust_level = context.get("trust_level", 0.5) 
        question_number = context.get("question_number", 1)
        engagement = context.get("engagement_level", 0.5)
        
        # Формула важности (согласно плану)
        base_score = (
            emotional_weight * 0.25 +      # Эмоциональная нагрузка
            insight_potential * 0.25 +     # Потенциал прорыва  
            trust_level * 0.20 +           # Уровень доверия
            complexity * 0.15 +            # Сложность
            (1.0 - safety_level) * 0.15   # Деликатность темы (инвертированная безопасность)
        )
        
        # Контекстные бонусы
        context_bonus = 0.0
        
        # Вехи пути (25, 50, 75, 100 вопросов)
        if question_number in [25, 50, 75, 100]:
            context_bonus += 0.5
            
        # Признаки прорыва
        if context.get("is_breakthrough", False):
            context_bonus += 1.0
            
        # Высокое вовлечение
        if engagement > 0.8:
            context_bonus += 0.3
            
        # Деликатные домены
        if classification.get("domain") in ["SPIRITUALITY", "IDENTITY", "EMOTIONS"]:
            context_bonus += 0.2
            
        # Глубокие уровни
        if classification.get("depth_level") in ["SHADOW", "CORE"]:
            context_bonus += 0.4
        
        final_score = min(5.0, (base_score * 5.0) + context_bonus)  # Приводим к шкале 0-5
        
        logger.debug(f"📊 Moment score: {final_score:.2f} (base: {base_score:.2f}, bonus: {context_bonus:.2f})")
        return final_score
    
    def _should_use_claude(
        self, 
        question_metadata: Dict, 
        context: Dict, 
        moment_score: float,
        budget_constraint: str
    ) -> bool:
        """Проверить нужен ли Claude для этого анализа"""
        
        # Бюджетные ограничения
        if budget_constraint == "emergency":
            return False
        elif budget_constraint == "restricted" and moment_score < 4.5:
            return False
        
        # Прямые указания использовать Claude
        thresholds = self.config.COMPLEXITY_THRESHOLDS["use_claude_if"]
        
        return any([
            moment_score >= thresholds["complexity_score"],
            context.get("is_breakthrough", False),
            question_metadata["classification"]["depth_level"] in thresholds["depth_level"],
            question_metadata["classification"]["domain"] in thresholds["domain"],
            question_metadata["classification"]["energy_dynamic"] in thresholds["energy_dynamic"],
            self._detect_crisis_indicators(context.get("user_answer", "")),
            context.get("question_number", 0) in [25, 50, 75, 100]  # Важные вехи
        ])
    
    def _should_use_gpt4o(self, question_metadata: Dict, context: Dict, moment_score: float) -> bool:
        """Проверить подходит ли GPT-4o"""
        
        thresholds = self.config.COMPLEXITY_THRESHOLDS["use_gpt4_if"]
        
        return (
            moment_score >= thresholds["complexity_score"] and
            (context.get("answer_length", 0) >= thresholds["answer_length"] or
             context.get("user_engagement", 0) >= thresholds["user_engagement"])
        )
    
    def _get_metadata_recommendation(self, question_metadata: Dict) -> Optional[str]:
        """Получить рекомендацию модели из метаданных вопроса"""
        
        return question_metadata.get("processing_hints", {}).get("recommended_model")
    
    def _check_budget_constraints(self) -> str:
        """
        Проверить бюджетные ограничения
        
        Returns:
            "normal" | "restricted" | "emergency"
        """
        
        budget_used_percent = (self.daily_spending / self.daily_budget) * 100
        
        if budget_used_percent >= 95:
            return "emergency"
        elif budget_used_percent >= 80: 
            return "restricted"
        else:
            return "normal"
    
    def _can_afford_model(self, model: str, budget_constraint: str) -> bool:
        """Проверить можем ли позволить себе эту модель"""
        
        if budget_constraint == "normal":
            return True
        elif budget_constraint == "restricted":
            return model != "claude-3.5-sonnet"  # Только GPT модели
        else:  # emergency
            return model == "gpt-4o-mini"  # Только самая дешевая
    
    def _get_model_config(self, model_name: str, usage_type: str) -> Tuple[str, Dict[str, Any]]:
        """
        Получить конфигурацию для выбранной модели
        
        Args:
            model_name: Название модели
            usage_type: Тип использования
            
        Returns:
            Tuple[model_name, config]
        """
        
        base_config = self.config.AI_MODEL_SETTINGS[model_name].copy()
        
        # Настройки под тип использования
        if usage_type == "critical_analysis":
            base_config["temperature"] = 0.1  # Максимальная точность
            base_config["max_tokens"] = 1000
            
        elif usage_type == "standard_analysis":  
            base_config["temperature"] = 0.3  # Баланс
            base_config["max_tokens"] = 600
            
        elif usage_type == "simple_classification":
            base_config["temperature"] = 0.2  # Низкая для классификации
            base_config["max_tokens"] = 300
            
        elif usage_type == "error_fallback":
            base_config["temperature"] = 0.4  # Высокая для creativity в кризисе
            base_config["max_tokens"] = 200
        
        # Добавляем метаданные для логирования
        base_config.update({
            "selected_for": usage_type,
            "selected_at": datetime.now().isoformat(),
            "budget_mode": self._check_budget_constraints()
        })
        
        return model_name, base_config
    
    def _detect_crisis_indicators(self, user_answer: str) -> bool:
        """Обнаружить кризисные слова в ответе"""
        
        crisis_keywords = self.config.SAFETY_RULES["crisis_keywords"]
        answer_lower = user_answer.lower()
        
        return any(keyword in answer_lower for keyword in crisis_keywords)
    
    async def get_fallback_model(self, primary_model: str, error: Exception) -> Tuple[str, Dict[str, Any]]:
        """
        Получить fallback модель при ошибке
        
        Args:
            primary_model: Модель которая не сработала
            error: Тип ошибки
            
        Returns:
            Fallback модель и конфиг
        """
        
        fallback_chain = {
            "claude-3.5-sonnet": {
                "fallback": "gpt-4o",
                "enrichment": "add_extra_context"
            },
            "gpt-4o": {
                "fallback": "gpt-4o-mini", 
                "enrichment": "simplified_analysis"
            },
            "gpt-4o-mini": {
                "fallback": "rule_based",
                "enrichment": "basic_only"
            }
        }
        
        if primary_model in fallback_chain:
            fallback_info = fallback_chain[primary_model]
            fallback_model = fallback_info["fallback"]
            
            logger.warning(f"⚠️ Fallback: {primary_model} → {fallback_model} (error: {type(error).__name__})")
            
            if fallback_model == "rule_based":
                return await self._get_rule_based_config()
            else:
                return self._get_model_config(fallback_model, "fallback")
        
        # Последний fallback
        logger.error(f"❌ No fallback available for {primary_model}")
        return await self._get_rule_based_config()
    
    async def _get_rule_based_config(self) -> Tuple[str, Dict[str, Any]]:
        """Простой анализ без AI для критических ситуаций"""
        
        return "rule_based", {
            "approach": "simple_heuristics",
            "capabilities": ["emotion_keywords", "length_analysis", "basic_classification"],
            "quality_level": "basic",
            "cost": 0.0
        }
    
    def track_usage(self, model: str, cost: float, quality_score: float, response_time_ms: int):
        """
        Отследить использование модели для оптимизации
        
        Args:
            model: Использованная модель
            cost: Стоимость запроса  
            quality_score: Оценка качества (0-1)
            response_time_ms: Время ответа
        """
        
        if model in self.usage_stats:
            stats = self.usage_stats[model]
            
            # Обновляем статистику
            old_requests = stats["requests"]
            stats["requests"] += 1
            stats["total_cost"] += cost
            
            # Скользящее среднее качества
            if old_requests > 0:
                stats["avg_quality"] = (
                    (stats["avg_quality"] * old_requests + quality_score) / 
                    (old_requests + 1)
                )
            else:
                stats["avg_quality"] = quality_score
            
            # Обновляем дневной бюджет
            self.daily_spending += cost
            
            # Логируем для cost tracking
            logger.info(
                f"💰 Model usage: {model}, cost: ${cost:.4f}, "
                f"quality: {quality_score:.2f}, time: {response_time_ms}ms"
            )
            
            # Предупреждение о бюджете
            budget_used = (self.daily_spending / self.daily_budget) * 100
            if budget_used > 80:
                logger.warning(f"💸 Budget alert: {budget_used:.1f}% used today")
    
    def get_usage_report(self) -> Dict[str, Any]:
        """Получить отчет об использовании моделей"""
        
        total_requests = sum(stats["requests"] for stats in self.usage_stats.values())
        total_cost = sum(stats["total_cost"] for stats in self.usage_stats.values())
        
        if total_requests == 0:
            return {"message": "No requests processed yet"}
        
        report = {
            "total_requests": total_requests,
            "total_cost": total_cost,
            "average_cost_per_request": total_cost / total_requests if total_requests > 0 else 0,
            "daily_budget_used_percent": (self.daily_spending / self.daily_budget) * 100,
            
            "model_distribution": {},
            "quality_scores": {},
            "cost_efficiency": {}
        }
        
        # Статистика по моделям
        for model, stats in self.usage_stats.items():
            if stats["requests"] > 0:
                percent = (stats["requests"] / total_requests) * 100
                cost_per_request = stats["total_cost"] / stats["requests"]
                
                report["model_distribution"][model] = f"{percent:.1f}%"
                report["quality_scores"][model] = f"{stats['avg_quality']:.2f}/1.0"
                report["cost_efficiency"][model] = f"${cost_per_request:.4f}/request"
        
        return report
    
    async def optimize_routing_strategy(self):
        """
        Оптимизировать стратегию роутинга на основе накопленной статистики
        """
        
        report = self.get_usage_report()
        
        # Анализ эффективности
        optimizations = []
        
        for model, stats in self.usage_stats.items():
            if stats["requests"] >= 10:  # Достаточно данных
                target_percent = self.config.AI_MODEL_SETTINGS[model]["usage_target_percent"]
                actual_percent = (stats["requests"] / sum(s["requests"] for s in self.usage_stats.values())) * 100
                
                if abs(actual_percent - target_percent) > 5:  # Отклонение больше 5%
                    optimizations.append({
                        "model": model,
                        "target_percent": target_percent,
                        "actual_percent": actual_percent,
                        "suggestion": "adjust_thresholds"
                    })
        
        if optimizations:
            logger.info(f"📈 Model usage optimization suggestions: {optimizations}")
        
        return optimizations