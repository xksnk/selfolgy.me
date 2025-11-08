"""
Fatigue Detector - Умная забота о пользователе

😴 ПРИНЦИП: "Лучше короткая приятная сессия, чем длинная мучительная"
💙 ЗАБОТА: Система чувствует когда пользователь устает
🎯 КАЧЕСТВО: Усталые ответы менее информативны
📈 RETENTION: Забота = лучший user experience
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class FatigueDetector:
    """
    Детектор усталости пользователя
    
    Анализирует множественные индикаторы:
    - Длину и качество ответов
    - Время обдумывания
    - Эмоциональную траекторию
    - Длительность сессии
    - Прямые сигналы усталости
    """
    
    def __init__(self):
        """Инициализация детектора"""
        
        # Пороговые значения для определения усталости
        self.fatigue_thresholds = {
            "high_fatigue": {
                "score": 0.6,
                "action": "suggest_end_session",
                "message_type": "caring_completion"
            },
            "medium_fatigue": {
                "score": 0.3,
                "action": "offer_pause",
                "message_type": "gentle_pause_offer"
            },
            "energized": {
                "score": 0.0,
                "action": "continue",
                "message_type": "encouraging_continuation"
            }
        }
        
        # Индикаторы усталости с весами
        self.fatigue_indicators = {
            "short_answers": {"weight": 0.25, "threshold": 20},      # Короткие ответы < 20 символов
            "quick_responses": {"weight": 0.15, "threshold": 10},    # Быстрые ответы < 10 сек
            "long_session": {"weight": 0.20, "threshold": 15},      # Долгая сессия > 15 мин
            "many_questions": {"weight": 0.15, "threshold": 10},    # Много вопросов > 10
            "explicit_fatigue": {"weight": 0.40, "threshold": 1},   # Прямо говорит об усталости
            "declining_mood": {"weight": 0.25, "threshold": 0.5},   # Падение настроения
            "frequent_skips": {"weight": 0.35, "threshold": 5}      # ✅ Частые пропуски >5 из 10
        }
        
        # Ключевые слова усталости
        self.fatigue_keywords = [
            "устал", "устала", "надоело", "хватит", "достаточно",
            "много вопросов", "утомился", "утомилась", "сил нет"
        ]
        
        # Ключевые слова энергии (противоположные)
        self.energy_keywords = [
            "интересно", "еще", "продолжим", "любопытно", "хочу еще",
            "давайте дальше", "мне нравится", "увлекательно"
        ]
        
        logger.info("😴 FatigueDetector initialized with caring approach")
    
    def analyze_fatigue_level(
        self, 
        user_context: Dict[str, Any],
        session_history: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Главный метод анализа усталости
        
        Args:
            user_context: Текущий контекст пользователя
            session_history: История вопросов и ответов сессии
            
        Returns:
            Анализ усталости с рекомендациями
        """
        
        try:
            logger.info(f"😴 Analyzing fatigue for user {user_context.get('user_id')} (session: {len(session_history)} answers)")
            
            # Вычисляем каждый индикатор
            indicators = {}
            
            # 1. Короткие ответы
            indicators["short_answers"] = self._analyze_answer_length(user_context, session_history)
            
            # 2. Быстрые ответы
            indicators["quick_responses"] = self._analyze_response_time(user_context)
            
            # 3. Длительность сессии
            indicators["long_session"] = self._analyze_session_duration(user_context)
            
            # 4. Количество вопросов
            indicators["many_questions"] = self._analyze_question_count(session_history)
            
            # 5. Прямые сигналы усталости
            indicators["explicit_fatigue"] = self._detect_explicit_fatigue(user_context, session_history)
            
            # 6. Эмоциональная траектория
            indicators["declining_mood"] = self._analyze_mood_trajectory(session_history)

            # 7. ✅ Частота пропусков вопросов
            indicators["frequent_skips"] = self._analyze_skip_frequency(session_history)

            # Вычисляем общий score усталости
            fatigue_score = self._calculate_fatigue_score(indicators)
            
            # Определяем уровень и рекомендации
            fatigue_level = self._determine_fatigue_level(fatigue_score)
            
            # Формируем результат
            result = {
                "fatigue_score": round(fatigue_score, 2),
                "fatigue_level": fatigue_level,
                "indicators": indicators,
                "recommendation": self._get_recommendation(fatigue_level, user_context),
                "message_template": self._get_message_template(fatigue_level, session_history),
                "should_pause": fatigue_level in ["medium_fatigue", "high_fatigue"],
                "should_end": fatigue_level == "high_fatigue",
                "analysis_timestamp": datetime.now().isoformat()
            }
            
            logger.info(
                f"😴 Fatigue analysis: {fatigue_level} (score: {fatigue_score:.2f}) "
                f"-> {result['recommendation']['action']}"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Error analyzing fatigue: {e}")
            return self._get_safe_fatigue_result()
    
    def _analyze_answer_length(self, context: Dict, history: List[Dict]) -> Dict[str, Any]:
        """Анализ длины ответов как индикатор усталости"""
        
        current_length = context.get("answer_length", 50)
        threshold = self.fatigue_indicators["short_answers"]["threshold"]
        
        # Сравниваем с историей
        if history:
            avg_length = sum(len(item.get("answer", "")) for item in history[-5:]) / min(5, len(history))
            length_decline = (avg_length - current_length) / max(1, avg_length)
            
            is_declining = length_decline > 0.3  # Ответы стали на 30% короче
        else:
            is_declining = False
            
        is_short = current_length < threshold
        
        return {
            "current_length": current_length,
            "is_short": is_short,
            "is_declining": is_declining,
            "indicator_active": is_short or is_declining,
            "confidence": 0.8 if is_short and is_declining else 0.5
        }
    
    def _analyze_response_time(self, context: Dict) -> Dict[str, Any]:
        """Анализ времени ответа"""
        
        response_time = context.get("response_time_seconds", 30)
        threshold = self.fatigue_indicators["quick_responses"]["threshold"]
        
        # Быстрые ответы могут означать:
        # 1. Усталость (не хочет думать)
        # 2. Энтузиазм (быстро отвечает)
        # Различаем по длине ответа
        answer_length = context.get("answer_length", 0)
        
        is_quick = response_time < threshold
        likely_fatigue = is_quick and answer_length < 30  # Быстро И коротко = усталость
        
        return {
            "response_time": response_time,
            "is_quick": is_quick,
            "likely_fatigue": likely_fatigue,
            "indicator_active": likely_fatigue,
            "confidence": 0.7 if likely_fatigue else 0.3
        }
    
    def _analyze_session_duration(self, context: Dict) -> Dict[str, Any]:
        """Анализ длительности сессии"""
        
        session_minutes = context.get("session_length_minutes", 0)
        threshold = self.fatigue_indicators["long_session"]["threshold"]
        
        is_long = session_minutes > threshold
        
        # Прогрессивная усталость - чем дольше, тем хуже
        duration_factor = min(1.0, session_minutes / (threshold * 2))  # 0-1 шкала
        
        return {
            "session_minutes": session_minutes,
            "is_long": is_long,
            "duration_factor": duration_factor,
            "indicator_active": is_long,
            "confidence": 0.6
        }
    
    def _analyze_question_count(self, history: List[Dict]) -> Dict[str, Any]:
        """Анализ количества вопросов"""
        
        question_count = len(history)
        threshold = self.fatigue_indicators["many_questions"]["threshold"]
        
        is_many = question_count > threshold
        
        return {
            "question_count": question_count,
            "is_many": is_many,
            "indicator_active": is_many,
            "confidence": 0.5
        }
    
    def _detect_explicit_fatigue(self, context: Dict, history: List[Dict]) -> Dict[str, Any]:
        """Детекция прямых сигналов усталости"""
        
        # Проверяем текущий ответ
        current_answer = context.get("user_answer", "").lower()
        
        # Проверяем последние 3 ответа
        recent_answers = [item.get("answer", "") for item in history[-3:]]
        recent_answers.append(current_answer)
        
        all_text = " ".join(recent_answers).lower()
        
        # Подсчет ключевых слов усталости
        fatigue_count = sum(1 for keyword in self.fatigue_keywords if keyword in all_text)
        energy_count = sum(1 for keyword in self.energy_keywords if keyword in all_text)
        
        # Прямое упоминание усталости
        explicit_fatigue = fatigue_count > 0
        explicit_energy = energy_count > 0
        
        # Если есть и усталость и энергия - смотрим что последнее
        if explicit_fatigue and explicit_energy:
            # Ищем последнее упоминание
            last_fatigue_pos = max([all_text.rfind(keyword) for keyword in self.fatigue_keywords])
            last_energy_pos = max([all_text.rfind(keyword) for keyword in self.energy_keywords])
            explicit_fatigue = last_fatigue_pos > last_energy_pos
        
        return {
            "fatigue_keywords_found": fatigue_count,
            "energy_keywords_found": energy_count,
            "explicit_fatigue": explicit_fatigue,
            "explicit_energy": explicit_energy,
            "indicator_active": explicit_fatigue,
            "confidence": 0.9 if explicit_fatigue else 0.1
        }
    
    def _analyze_mood_trajectory(self, history: List[Dict]) -> Dict[str, Any]:
        """Анализ эмоциональной траектории"""
        
        if len(history) < 3:
            return {
                "trajectory": "insufficient_data",
                "indicator_active": False,
                "confidence": 0.0
            }
        
        # Анализируем эмоциональные слова в последних ответах
        mood_scores = []
        
        for item in history[-5:]:  # Последние 5 ответов
            answer = item.get("answer", "").lower()
            
            positive_count = sum(1 for word in ["хорошо", "отлично", "интересно", "нравится"] if word in answer)
            negative_count = sum(1 for word in ["плохо", "сложно", "тяжело", "грустно"] if word in answer)
            
            # Простая оценка настроения (-1 до 1)
            if positive_count > negative_count:
                mood_score = 0.5
            elif negative_count > positive_count:
                mood_score = -0.5
            else:
                mood_score = 0.0
                
            mood_scores.append(mood_score)
        
        # Анализируем тренд
        if len(mood_scores) >= 3:
            early_avg = sum(mood_scores[:2]) / 2
            recent_avg = sum(mood_scores[-2:]) / 2
            decline = early_avg - recent_avg > 0.3  # Значимое снижение
        else:
            decline = False
        
        return {
            "mood_scores": mood_scores,
            "trajectory": "declining" if decline else "stable",
            "indicator_active": decline,
            "confidence": 0.6 if len(mood_scores) >= 3 else 0.3
        }

    def _analyze_skip_frequency(self, history: List[Dict]) -> Dict[str, Any]:
        """
        Анализ частоты пропусков вопросов как индикатор усталости

        >5 пропусков из последних 10 вопросов = сигнал усталости
        """

        # Берём последние 10 записей (вопросов + ответов/пропусков)
        recent_history = history[-10:] if len(history) > 10 else history

        if not recent_history:
            return {
                "skip_count": 0,
                "total_checked": 0,
                "skip_rate": 0.0,
                "indicator_active": False,
                "confidence": 0.0
            }

        # Подсчитываем пропуски (записи с флагом skipped=True)
        skip_count = sum(1 for item in recent_history if item.get("skipped", False))
        total_checked = len(recent_history)
        skip_rate = skip_count / total_checked if total_checked > 0 else 0.0

        threshold = self.fatigue_indicators["frequent_skips"]["threshold"]
        is_frequent = skip_count > threshold  # >5 пропусков

        return {
            "skip_count": skip_count,
            "total_checked": total_checked,
            "skip_rate": round(skip_rate, 2),
            "indicator_active": is_frequent,
            "confidence": 0.9 if is_frequent else 0.5  # Высокая уверенность при частых пропусках
        }

    def _calculate_fatigue_score(self, indicators: Dict[str, Dict]) -> float:
        """Вычисление общего score усталости (0-1)"""
        
        total_score = 0.0
        total_weight = 0.0
        
        for indicator_name, indicator_data in indicators.items():
            if indicator_name in self.fatigue_indicators:
                weight = self.fatigue_indicators[indicator_name]["weight"]
                is_active = indicator_data.get("indicator_active", False)
                confidence = indicator_data.get("confidence", 0.5)
                
                # Учитываем активность индикатора и уверенность
                contribution = weight * (1.0 if is_active else 0.0) * confidence
                
                total_score += contribution
                total_weight += weight * confidence
        
        # Нормализуем на максимально возможный score
        if total_weight > 0:
            normalized_score = total_score / total_weight
        else:
            normalized_score = 0.0
        
        return min(1.0, normalized_score)
    
    def _determine_fatigue_level(self, fatigue_score: float) -> str:
        """Определение уровня усталости"""
        
        if fatigue_score >= self.fatigue_thresholds["high_fatigue"]["score"]:
            return "high_fatigue"
        elif fatigue_score >= self.fatigue_thresholds["medium_fatigue"]["score"]:
            return "medium_fatigue"
        else:
            return "energized"
    
    def _get_recommendation(self, fatigue_level: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Получение рекомендаций на основе уровня усталости"""
        
        base_rec = self.fatigue_thresholds[fatigue_level].copy()
        question_count = context.get("previous_answers_count", 0)
        
        if fatigue_level == "high_fatigue":
            return {
                "action": "suggest_end_session",
                "urgency": "high",
                "reasoning": f"Обнаружено несколько индикаторов усталости после {question_count} вопросов",
                "suggested_buttons": ["🏁 Закончить на сегодня", "⚡ Нет, мне интересно!"],
                "continue_available": True,  # Пользователь может настоять на продолжении
                "next_session_suggestion": "Попробуйте продолжить завтра утром"
            }
        
        elif fatigue_level == "medium_fatigue":
            return {
                "action": "offer_pause",
                "urgency": "medium", 
                "reasoning": f"Легкие признаки усталости, но можно продолжать",
                "suggested_buttons": ["⏸️ Пауза", "✅ Продолжаем", "🏁 Хватит на сегодня"],
                "continue_available": True,
                "pause_duration_suggestion": "5-10 минут"
            }
        
        else:  # energized
            return {
                "action": "continue",
                "urgency": "none",
                "reasoning": "Пользователь активен и вовлечен",
                "suggested_buttons": ["✅ Следующий вопрос"],
                "encouragement": "Отличный прогресс! Продолжаем?"
            }
    
    def _get_message_template(self, fatigue_level: str, history: List[Dict]) -> Dict[str, str]:
        """Получение шаблонов сообщений для разных уровней усталости"""
        
        question_count = len(history)
        
        if fatigue_level == "high_fatigue":
            return {
                "template": """😌 <b>Кажется, вы устали</b>

🎯 Мы уже узнали много интересного о вас! 
📊 Пройдено: {question_count}/693 вопросов

Достаточно на сегодня? Можем продолжить в любое время!

💡 <i>Качественные ответы важнее количества</i>""",
                "variables": {"question_count": question_count},
                "tone": "caring_completion"
            }
        
        elif fatigue_level == "medium_fatigue":
            return {
                "template": """⏸️ <b>Хотите сделать паузу?</b>

📈 Отличный прогресс: {question_count} вопросов!
💡 Может быть, передохнем немного?

🌱 <i>Самопознание - это марафон, не спринт</i>""",
                "variables": {"question_count": question_count},
                "tone": "gentle_pause_offer"
            }
        
        else:  # energized
            return {
                "template": """✨ <b>Отличный настрой!</b>

🚀 Вы активно погружены в процесс самопознания
📊 Пройдено: {question_count} вопросов

Продолжаем исследование? 🤗""",
                "variables": {"question_count": question_count},
                "tone": "encouraging_continuation"
            }
    
    def should_force_pause(self, fatigue_analysis: Dict[str, Any], user_context: Dict[str, Any]) -> bool:
        """
        Определить нужна ли принудительная пауза (критические случаи)
        
        Returns:
            True если система должна настоять на паузе
        """
        
        # Принудительная пауза только в критических случаях
        critical_indicators = [
            fatigue_analysis["fatigue_score"] > 0.8,  # Очень высокая усталость
            user_context.get("session_length_minutes", 0) > 30,  # Более 30 минут
            user_context.get("previous_answers_count", 0) > 20,   # Более 20 вопросов
            fatigue_analysis["indicators"]["explicit_fatigue"]["explicit_fatigue"]  # Прямо говорит об усталости
        ]
        
        return sum(critical_indicators) >= 2  # Минимум 2 критических фактора
    
    def get_continuation_strategy(self, fatigue_analysis: Dict[str, Any]) -> Dict[str, str]:
        """
        Стратегия продолжения если пользователь настаивает
        
        Returns:
            Рекомендации для адаптации процесса
        """
        
        fatigue_level = fatigue_analysis["fatigue_level"]
        
        if fatigue_level == "high_fatigue":
            return {
                "question_strategy": "only_light_questions",
                "complexity_adjustment": "decrease_significantly", 
                "energy_preference": "OPENING_or_NEUTRAL_only",
                "max_additional_questions": "3",
                "frequent_check_ins": "every_2_questions",
                "tone_adjustment": "extra_supportive"
            }
        
        elif fatigue_level == "medium_fatigue":
            return {
                "question_strategy": "prefer_engaging_domains",
                "complexity_adjustment": "slight_decrease",
                "energy_preference": "avoid_HEAVY",
                "max_additional_questions": "5", 
                "frequent_check_ins": "every_3_questions",
                "tone_adjustment": "encouraging"
            }
        
        else:
            return {
                "question_strategy": "normal",
                "complexity_adjustment": "maintain",
                "energy_preference": "balanced",
                "max_additional_questions": "unlimited",
                "frequent_check_ins": "every_5_questions",
                "tone_adjustment": "normal"
            }
    
    def _get_safe_fatigue_result(self) -> Dict[str, Any]:
        """Безопасный fallback результат при ошибках"""
        
        return {
            "fatigue_score": 0.5,  # Средний уровень
            "fatigue_level": "medium_fatigue", 
            "recommendation": {
                "action": "offer_pause",
                "reasoning": "Не удалось точно определить усталость - предосторожность"
            },
            "should_pause": True,
            "should_end": False,
            "error": "fatigue_analysis_failed",
            "fallback_used": True
        }
    
    def get_smart_session_limits(self, user_profile: Dict[str, Any]) -> Dict[str, int]:
        """
        Умные лимиты сессии на основе профиля пользователя
        
        Returns:
            Персонализированные лимиты
        """
        
        # Базовые лимиты
        base_limits = {
            "max_questions": 15,
            "max_duration_minutes": 20,
            "fatigue_check_interval": 5
        }
        
        # Адаптация под личность пользователя
        big_five = user_profile.get("traits", {}).get("big_five", {})
        
        if big_five:
            # Высокая conscientiousness = может дольше
            if big_five.get("conscientiousness", 0.5) > 0.7:
                base_limits["max_questions"] += 5
                base_limits["max_duration_minutes"] += 10
            
            # Высокий neuroticism = нужны частые проверки
            if big_five.get("neuroticism", 0.5) > 0.6:
                base_limits["fatigue_check_interval"] = 3
                base_limits["max_duration_minutes"] -= 5
            
            # Высокая openness = может больше вопросов
            if big_five.get("openness", 0.5) > 0.7:
                base_limits["max_questions"] += 3
        
        return base_limits