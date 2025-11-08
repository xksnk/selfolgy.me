"""
Trait Extractor - Извлечение черт личности

🧬 ПРИНЦИП: Многослойная модель личности с контекстной адаптацией
📊 ТОЧНОСТЬ: 2 знака после запятой + уровень уверенности
🎯 АДАПТИВНОСТЬ: Разные черты для разных доменов вопросов
"""

import logging
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
import numpy as np

from .analysis_config import AnalysisConfig

logger = logging.getLogger(__name__)

class TraitExtractor:
    """
    Извлечение численных оценок черт личности из AI анализа
    
    Многослойная архитектура:
    - Big Five (фундамент)
    - Динамические черты (меняются со временем)
    - Адаптивные черты (быстро меняющиеся состояния)  
    - Доменные профили (специфичные для области вопроса)
    """
    
    def __init__(self):
        """Инициализация экстрактора"""
        self.config = AnalysisConfig()
        
        # Кэш для временных оценок (пока не накопились данные)
        self.trait_cache = {}
        
        # Статистика для нормализации
        self.population_stats = {
            "mean": {},
            "std": {},
            "sample_size": 0
        }
        
        logger.info("📊 TraitExtractor initialized with multilayer personality model")
    
    async def extract_traits_from_analysis(
        self, 
        ai_analysis: Dict[str, Any],
        question_metadata: Dict[str, Any],
        user_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Главный метод извлечения черт из AI анализа
        
        Args:
            ai_analysis: Структурированный ответ от AI
            question_metadata: Метаданные вопроса (17 параметров)
            user_context: Контекст пользователя и сессии
            
        Returns:
            Полная структура черт личности с метаданными
        """
        
        try:
            logger.info(f"📊 Extracting traits from AI analysis (model: {user_context.get('model_used', 'unknown')})")
            
            # 1. Извлекаем базовые черты (Big Five)
            big_five = self._extract_big_five(ai_analysis, question_metadata, user_context)
            
            # 2. Извлекаем динамические черты
            dynamic_traits = self._extract_dynamic_traits(ai_analysis, question_metadata)
            
            # 3. Извлекаем адаптивные черты (текущее состояние)
            adaptive_traits = self._extract_adaptive_traits(ai_analysis, user_context)
            
            # 4. Извлекаем доменные черты (если релевантно)
            domain_traits = self._extract_domain_specific_traits(ai_analysis, question_metadata)
            
            # 5. Добавляем метаданные оценки
            assessment_metadata = self._generate_assessment_metadata(
                ai_analysis, question_metadata, user_context
            )
            
            # 6. Нормализуем и валидируем все значения
            normalized_traits = self._normalize_and_validate_traits({
                "big_five": big_five,
                "dynamic_traits": dynamic_traits,
                "adaptive_traits": adaptive_traits,
                "domain_specific": domain_traits
            })
            
            # 7. Формируем финальную структуру
            timestamp = datetime.now().isoformat()
            result = {
                "version": "2.0",
                "timestamp": timestamp,  # Для DB constraint
                "extracted_at": timestamp,  # Для читаемости
                "big_five": big_five,  # Для DB constraint (прямой доступ)
                "traits": normalized_traits,
                "assessment_metadata": assessment_metadata,
                "extraction_context": {
                    "question_domain": question_metadata["classification"]["domain"],
                    "question_depth": question_metadata["classification"]["depth_level"],
                    "analysis_model": user_context.get("model_used"),
                    "user_question_number": user_context.get("question_number", 1)
                }
            }
            
            logger.info(f"✅ Traits extracted successfully: {len(big_five)} Big Five + {len(dynamic_traits)} dynamic + {len(domain_traits)} domain-specific")
            return result
            
        except Exception as e:
            logger.error(f"❌ Error extracting traits: {e}")
            return self._get_fallback_traits(question_metadata, user_context)
    
    def _extract_big_five(
        self, 
        ai_analysis: Dict[str, Any], 
        question_metadata: Dict[str, Any],
        user_context: Dict[str, Any]
    ) -> Dict[str, float]:
        """Извлечение Big Five черт"""
        
        big_five_traits = {}
        
        # Пытаемся получить из структурированного ответа AI
        ai_traits = ai_analysis.get("traits", {}).get("big_five", {})
        
        for trait in self.config.BIG_FIVE_TRAITS:
            # Если AI дал оценку - используем её
            if trait in ai_traits and isinstance(ai_traits[trait], (int, float)):
                raw_value = float(ai_traits[trait])
                
                # Применяем контекстную нормализацию
                normalized_value = self._apply_contextual_normalization(
                    raw_value, trait, question_metadata, user_context
                )
                
                big_five_traits[trait] = round(normalized_value, 2)
                
            else:
                # Fallback - эвристический анализ текста ответа
                estimated_value = self._estimate_trait_from_text(
                    trait, 
                    user_context.get("user_answer", ""),
                    question_metadata
                )
                big_five_traits[trait] = round(estimated_value, 2)
        
        return big_five_traits
    
    def _extract_dynamic_traits(self, ai_analysis: Dict[str, Any], question_metadata: Dict[str, Any]) -> Dict[str, float]:
        """Извлечение динамических черт"""
        
        dynamic_traits = {}
        ai_dynamic = ai_analysis.get("traits", {}).get("dynamic_traits", {})
        
        for trait in self.config.DYNAMIC_TRAITS:
            if trait in ai_dynamic:
                dynamic_traits[trait] = round(float(ai_dynamic[trait]), 2)
            else:
                # Эвристическая оценка на основе контекста
                estimated = self._estimate_dynamic_trait(trait, ai_analysis, question_metadata)
                dynamic_traits[trait] = round(estimated, 2)
        
        return dynamic_traits
    
    def _extract_adaptive_traits(self, ai_analysis: Dict[str, Any], user_context: Dict[str, Any]) -> Dict[str, float]:
        """Извлечение адаптивных черт (текущее состояние)"""
        
        adaptive_traits = {}
        
        # Извлекаем из мета-оценки AI
        meta_assessment = ai_analysis.get("meta_assessment", {})
        
        for trait in self.config.ADAPTIVE_TRAITS:
            if trait in meta_assessment:
                adaptive_traits[trait] = round(float(meta_assessment[trait]), 2)
            else:
                # Оценка на основе контекстных признаков
                estimated = self._estimate_adaptive_trait(trait, ai_analysis, user_context)
                adaptive_traits[trait] = round(estimated, 2)
        
        return adaptive_traits
    
    def _extract_domain_specific_traits(self, ai_analysis: Dict[str, Any], question_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Извлечение доменных черт"""
        
        domain = question_metadata["classification"]["domain"]
        domain_traits = {}
        
        # Получаем релевантные черты для домена
        relevant_traits = self.config.DOMAIN_SPECIFIC_TRAITS.get(domain, [])
        
        if relevant_traits:
            ai_domain_traits = ai_analysis.get("traits", {}).get("domain_specific", {}).get(domain, {})
            
            domain_traits[domain] = {}
            
            for trait in relevant_traits:
                if trait in ai_domain_traits:
                    domain_traits[domain][trait] = round(float(ai_domain_traits[trait]), 2)
                else:
                    # Эвристическая оценка для домена
                    estimated = self._estimate_domain_trait(trait, domain, ai_analysis)
                    domain_traits[domain][trait] = round(estimated, 2)
        
        return domain_traits
    
    def _apply_contextual_normalization(
        self, 
        raw_value: float, 
        trait_name: str,
        question_metadata: Dict[str, Any],
        user_context: Dict[str, Any]
    ) -> float:
        """
        Применить контекстную нормализацию для точности оценки
        
        Args:
            raw_value: Сырое значение от AI (0-1)
            trait_name: Название черты
            question_metadata: Метаданные вопроса
            user_context: Контекст пользователя
            
        Returns:
            Нормализованное значение
        """
        
        depth_level = question_metadata["classification"]["depth_level"]
        energy_dynamic = question_metadata["classification"]["energy_dynamic"]
        time_of_day = user_context.get("time_of_day", 12)
        
        normalized = raw_value
        
        # Коррекция по глубине вопроса
        if depth_level == "SHADOW":
            # На глубоких уровнях люди более открыты
            normalized *= 0.95  # Компенсируем завышенные оценки
        elif depth_level == "SURFACE":
            # На поверхности люди более осторожны
            normalized *= 1.05  # Компенсируем заниженные
        
        # Коррекция по энергии
        if energy_dynamic == "HEAVY" and trait_name in ["neuroticism"]:
            # В тяжелые моменты neuroticism может быть завышен
            normalized *= 0.9
        elif energy_dynamic == "OPENING" and trait_name in ["openness"]:
            # В вдохновляющие моменты openness может быть завышен  
            normalized *= 0.95
        
        # Коррекция по времени суток
        if time_of_day >= 20:  # Вечером
            if trait_name == "conscientiousness":
                normalized *= 0.95  # Вечером менее организованы
        elif time_of_day <= 8:  # Утром  
            if trait_name == "extraversion":
                normalized *= 0.9  # Утром менее социальны
        
        # Убеждаемся что значение в диапазоне 0-1
        return max(0.0, min(1.0, normalized))
    
    def _estimate_trait_from_text(self, trait_name: str, answer_text: str, question_metadata: Dict) -> float:
        """Эвристическая оценка черты из текста (fallback)"""
        
        if not answer_text:
            return 0.5  # Нейтральное значение
        
        answer_lower = answer_text.lower()
        answer_length = len(answer_text)
        
        # Эвристики для каждой черты Big Five
        if trait_name == "openness":
            # Маркеры открытости: абстрактные слова, метафоры, нестандартные ответы
            openness_markers = ["интересно", "возможно", "может быть", "творчество", "искусство", "необычно"]
            marker_count = sum(1 for marker in openness_markers if marker in answer_lower)
            return min(0.9, 0.3 + (marker_count * 0.1) + (answer_length / 1000))
        
        elif trait_name == "conscientiousness":
            # Маркеры добросовестности: структура, планы, организация
            conscient_markers = ["план", "организ", "системно", "порядок", "регулярно", "дисциплин"]
            marker_count = sum(1 for marker in conscient_markers if marker in answer_lower)
            return min(0.9, 0.3 + (marker_count * 0.15))
        
        elif trait_name == "extraversion":
            # Маркеры экстраверсии: люди, общение, энергия
            extra_markers = ["люди", "друзья", "общение", "команда", "энергия", "активность"]
            marker_count = sum(1 for marker in extra_markers if marker in answer_lower)
            return min(0.9, 0.2 + (marker_count * 0.12))
        
        elif trait_name == "agreeableness":
            # Маркеры доброжелательности: помощь, понимание, гармония
            agree_markers = ["помощь", "понимание", "поддержка", "гармония", "мир", "забота"]
            marker_count = sum(1 for marker in agree_markers if marker in answer_lower)
            return min(0.9, 0.4 + (marker_count * 0.1))
        
        elif trait_name == "neuroticism":
            # Маркеры нейротизма: тревога, стресс, проблемы
            neurotic_markers = ["волнуюсь", "тревога", "стресс", "проблема", "сложно", "боюсь"]
            marker_count = sum(1 for marker in neurotic_markers if marker in answer_lower)
            return min(0.9, 0.1 + (marker_count * 0.15))
        
        # Fallback для неизвестных черт
        return 0.5
    
    def _estimate_dynamic_trait(self, trait_name: str, ai_analysis: Dict, question_metadata: Dict) -> float:
        """Эвристическая оценка динамической черты"""
        
        insights = ai_analysis.get("insights", {})
        emotional_state = ai_analysis.get("emotional_state", {})
        
        if trait_name == "resilience":
            # Устойчивость к стрессу
            valence = emotional_state.get("valence", 0.0)
            return max(0.1, min(0.9, 0.5 + valence * 0.3))
        
        elif trait_name == "authenticity":
            # Уровень аутентичности из AI анализа
            return ai_analysis.get("meta_assessment", {}).get("answer_authenticity", 0.5)
        
        elif trait_name == "growth_mindset":
            # Установка на рост
            growth_indicators = ["развитие", "рост", "изменение", "учусь", "развиваюсь"]
            main_insight = insights.get("main", "").lower()
            indicator_count = sum(1 for indicator in growth_indicators if indicator in main_insight)
            return min(0.9, 0.4 + indicator_count * 0.15)
        
        elif trait_name == "emotional_granularity":
            # Тонкость различения эмоций  
            nuances = emotional_state.get("nuances", [])
            return min(0.9, 0.3 + len(nuances) * 0.1)
        
        elif trait_name == "cognitive_flexibility":
            # Гибкость мышления
            complexity = question_metadata.get("psychology", {}).get("complexity", 1)
            return min(0.9, 0.2 + (complexity / 5.0) * 0.6)
        
        # Fallback
        return 0.5
    
    def _estimate_adaptive_trait(self, trait_name: str, ai_analysis: Dict, user_context: Dict) -> float:
        """Оценка адаптивных черт (текущее состояние)"""
        
        if trait_name == "current_energy":
            # Текущий уровень энергии
            arousal = ai_analysis.get("emotional_state", {}).get("arousal", 0.5)
            time_factor = self._get_time_energy_factor(user_context.get("time_of_day", 12))
            return max(0.1, min(0.9, arousal * time_factor))
        
        elif trait_name == "stress_level":
            # Уровень стресса
            return ai_analysis.get("meta_assessment", {}).get("fatigue_indicators", 0.3)
        
        elif trait_name == "openness_state":
            # Текущая готовность открываться
            depth_readiness = ai_analysis.get("meta_assessment", {}).get("insight_readiness", 0.5)
            trust_level = user_context.get("trust_level", 0.5)
            return (depth_readiness + trust_level) / 2.0
        
        elif trait_name == "creative_flow":
            # В потоке ли сейчас
            answer_length = user_context.get("answer_length", 50)
            response_time = user_context.get("response_time_seconds", 30)
            
            # Длинный ответ + быстрая реакция = поток
            if answer_length > 100 and response_time < 60:
                return 0.8
            elif answer_length < 20:
                return 0.2
            else:
                return 0.5
        
        elif trait_name == "social_battery":
            # Социальная энергия
            extraversion_context = user_context.get("current_extraversion", 0.5)
            session_length = user_context.get("session_length_minutes", 5)
            
            # Уменьшается от времени сессии для интровертов
            if extraversion_context < 0.5:  # Интроверт
                battery = max(0.1, 0.9 - (session_length / 60.0) * 0.5)
            else:  # Экстраверт
                battery = max(0.3, 0.9 - (session_length / 120.0) * 0.3)
            
            return battery
        
        return 0.5
    
    def _extract_domain_specific_traits(self, ai_analysis: Dict, question_metadata: Dict) -> Dict[str, Any]:
        """Извлечение доменных черт"""
        
        domain = question_metadata["classification"]["domain"]
        relevant_traits = self.config.DOMAIN_SPECIFIC_TRAITS.get(domain, [])
        
        if not relevant_traits:
            return {}
        
        domain_traits = {}
        ai_domain_data = ai_analysis.get("traits", {}).get("domain_specific", {}).get(domain, {})
        
        for trait in relevant_traits:
            if trait in ai_domain_data:
                domain_traits[trait] = round(float(ai_domain_data[trait]), 2)
            else:
                # Эвристическая оценка для конкретного домена и черты
                estimated = self._estimate_domain_trait(trait, domain, ai_analysis)
                domain_traits[trait] = round(estimated, 2)
        
        return {domain: domain_traits} if domain_traits else {}
    
    def _estimate_domain_trait(self, trait_name: str, domain: str, ai_analysis: Dict) -> float:
        """Эвристическая оценка доменной черты"""
        
        insights = ai_analysis.get("insights", {}).get("main", "").lower()
        
        # Специфичные эвристики для каждого домена
        if domain == "RELATIONSHIPS":
            if trait_name == "empathy":
                empathy_markers = ["понимаю", "чувствую", "сопереживаю", "эмпатия"]
                return min(0.9, 0.3 + sum(0.15 for marker in empathy_markers if marker in insights))
            elif trait_name == "boundaries":
                boundary_markers = ["границы", "сказать нет", "своё мнение", "отказать"]
                return min(0.9, 0.2 + sum(0.2 for marker in boundary_markers if marker in insights))
                
        elif domain == "CAREER":
            if trait_name == "ambition":
                ambition_markers = ["карьера", "цели", "достижения", "успех", "амбиции"]
                return min(0.9, 0.3 + sum(0.12 for marker in ambition_markers if marker in insights))
            elif trait_name == "leadership":
                leader_markers = ["лидер", "команда", "руководить", "ответственность"]
                return min(0.9, 0.2 + sum(0.15 for marker in leader_markers if marker in insights))
        
        elif domain == "CREATIVITY":
            if trait_name == "divergent_thinking":
                creative_markers = ["необычно", "по-другому", "креативно", "альтернатива"]
                return min(0.9, 0.4 + sum(0.1 for marker in creative_markers if marker in insights))
        
        # Fallback - средняя оценка
        return 0.5
    
    def _generate_assessment_metadata(
        self,
        ai_analysis: Dict[str, Any],
        question_metadata: Dict[str, Any], 
        user_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Генерация метаданных оценки для отслеживания качества"""
        
        return {
            "confidence_scores": {
                trait: self._calculate_trait_confidence(trait, ai_analysis, question_metadata)
                for trait in self.config.BIG_FIVE_TRAITS
            },
            
            "data_quality": {
                "answer_length": user_context.get("answer_length", 0),
                "response_time": user_context.get("response_time_seconds", 0),
                "ai_model_confidence": ai_analysis.get("meta_assessment", {}).get("confidence", 0.5),
                "question_insight_potential": question_metadata.get("psychology", {}).get("insight_potential", 1)
            },
            
            "normalization_applied": {
                "contextual_adjustment": True,
                "depth_level_factor": question_metadata["classification"]["depth_level"],
                "time_of_day_factor": user_context.get("time_of_day"),
                "domain_specificity": question_metadata["classification"]["domain"]
            },
            
            "reliability_indicators": {
                "overall_reliability": self._calculate_overall_reliability(ai_analysis, user_context),
                "trait_variance_expected": self._calculate_expected_variance(question_metadata),
                "needs_validation": self._needs_additional_validation(ai_analysis, user_context)
            }
        }
    
    def _normalize_and_validate_traits(self, traits_dict: Dict[str, Dict]) -> Dict[str, Dict]:
        """Финальная нормализация и валидация всех черт"""
        
        normalized = {}
        
        for trait_category, traits in traits_dict.items():
            normalized[trait_category] = {}
            
            for trait_name, value in traits.items():
                # Убеждаемся что значение в диапазоне 0-1
                if isinstance(value, dict):
                    # Для вложенных структур (domain_specific)
                    normalized[trait_category][trait_name] = {
                        k: max(0.0, min(1.0, round(float(v), 2))) 
                        for k, v in value.items()
                        if isinstance(v, (int, float))
                    }
                else:
                    # Для простых значений
                    normalized[trait_category][trait_name] = max(0.0, min(1.0, round(float(value), 2)))
        
        return normalized
    
    def _get_fallback_traits(self, question_metadata: Dict, user_context: Dict) -> Dict[str, Any]:
        """Fallback структура черт при ошибке извлечения"""
        
        logger.warning("🔄 Using fallback trait extraction")

        # Базовые нейтральные значения
        timestamp = datetime.now().isoformat()
        big_five_fallback = {trait: 0.5 for trait in self.config.BIG_FIVE_TRAITS}

        fallback = {
            "version": "2.0",
            "timestamp": timestamp,  # Для DB constraint
            "extracted_at": timestamp,
            "big_five": big_five_fallback,  # Для DB constraint (прямой доступ)
            "traits": {
                "big_five": big_five_fallback,
                "dynamic_traits": {trait: 0.5 for trait in self.config.DYNAMIC_TRAITS},
                "adaptive_traits": {trait: 0.5 for trait in self.config.ADAPTIVE_TRAITS},
                "domain_specific": {}
            },
            "assessment_metadata": {
                "is_fallback": True,
                "reliability_indicators": {
                    "overall_reliability": 0.1,  # Низкая надежность
                    "needs_validation": True
                }
            },
            "extraction_context": {
                "question_domain": question_metadata.get("classification", {}).get("domain", "UNKNOWN"),
                "fallback_reason": "extraction_error"
            }
        }
        
        return fallback
    
    def _calculate_trait_confidence(self, trait_name: str, ai_analysis: Dict, question_metadata: Dict) -> float:
        """Рассчитать уверенность в оценке черты"""
        
        # Базовая уверенность от AI
        base_confidence = ai_analysis.get("meta_assessment", {}).get("confidence", 0.5)
        
        # Модификаторы уверенности
        insight_potential = question_metadata.get("psychology", {}).get("insight_potential", 1) / 5.0
        complexity = question_metadata.get("psychology", {}).get("complexity", 1) / 5.0
        
        # Чем выше потенциал инсайта и сложность, тем больше уверенности
        final_confidence = min(0.95, base_confidence * (1 + insight_potential * 0.2 + complexity * 0.1))
        
        return round(final_confidence, 2)
    
    def _calculate_overall_reliability(self, ai_analysis: Dict, user_context: Dict) -> float:
        """Рассчитать общую надежность оценки"""
        
        factors = []
        
        # Длина ответа
        answer_length = user_context.get("answer_length", 0)
        if answer_length > 100:
            factors.append(0.9)
        elif answer_length > 50:
            factors.append(0.7)
        else:
            factors.append(0.3)
        
        # Время обдумывания
        response_time = user_context.get("response_time_seconds", 30)
        if 20 <= response_time <= 180:  # Оптимальное время обдумывания
            factors.append(0.8)
        else:
            factors.append(0.6)
        
        # Структурированность ответа AI
        if all(key in ai_analysis for key in ["emotional_state", "traits", "insights"]):
            factors.append(0.9)
        else:
            factors.append(0.5)
        
        # Среднее арифметическое
        return round(sum(factors) / len(factors), 2)

    def _get_time_energy_factor(self, hour: int) -> float:
        """
        Оценка энергетического фактора в зависимости от времени суток

        Args:
            hour: Час дня (0-23)

        Returns:
            float: Множитель энергии (0.5 - 1.2)
        """

        # Утро (6-9): высокая энергия
        if 6 <= hour < 9:
            return 1.2

        # День (9-12): пиковая энергия
        elif 9 <= hour < 12:
            return 1.3

        # После обеда (12-14): спад
        elif 12 <= hour < 14:
            return 0.9

        # Послеобеденная активность (14-18): хорошая энергия
        elif 14 <= hour < 18:
            return 1.1

        # Вечер (18-22): снижение
        elif 18 <= hour < 22:
            return 0.8

        # Ночь (22-6): низкая энергия
        else:
            return 0.5

    def _calculate_expected_variance(self, question_metadata: Dict) -> float:
        """
        Рассчитать ожидаемую вариативность трейтов в зависимости от типа вопроса

        Args:
            question_metadata: Метаданные вопроса

        Returns:
            float от 0.0 до 1.0 (0.0 = низкая вариативность, 1.0 = высокая)
        """

        # Базовая вариативность
        variance = 0.3

        # Глубина вопроса влияет на вариативность
        depth_level = question_metadata.get("classification", {}).get("depth_level", "SURFACE")
        depth_variance_map = {
            "SURFACE": 0.1,  # Поверхностные вопросы - низкая вариативность
            "CONSCIOUS": 0.2,
            "EDGE": 0.4,  # Пограничные вопросы - высокая вариативность
            "SHADOW": 0.5,
            "CORE": 0.6  # Глубинные вопросы - максимальная вариативность
        }
        variance = depth_variance_map.get(depth_level, 0.3)

        # Энергетика вопроса
        energy = question_metadata.get("classification", {}).get("energy_dynamic", "NEUTRAL")
        if energy in ["HEAVY", "PROCESSING"]:
            variance += 0.1  # Тяжелые вопросы дают больше вариативности

        # Домен может влиять
        domain = question_metadata.get("classification", {}).get("domain", "")
        if domain in ["FEARS", "SHADOW", "PAST"]:
            variance += 0.1  # Сложные домены дают больше вариативности

        return min(1.0, max(0.0, variance))

    def _needs_additional_validation(self, ai_analysis: Dict, user_context: Dict) -> bool:
        """Определить нужна ли дополнительная валидация"""

        # Нужна валидация если:
        return any([
            self._calculate_overall_reliability(ai_analysis, user_context) < 0.6,
            user_context.get("answer_length", 0) < 20,
            user_context.get("question_number", 1) < 3,  # Первые вопросы менее надежны
            ai_analysis.get("meta_assessment", {}).get("fatigue_indicators", 0) > 0.7
        ])