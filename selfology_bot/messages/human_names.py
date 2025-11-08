"""
Human Names - Человечные названия для debug режима

🧠 ПРИНЦИП: Технические термины → понятные человеку названия
🔍 DEBUG: Только для админа, обычные пользователи не видят
📚 ПОНЯТНОСТЬ: Психологические термины простым языком
"""

from typing import Dict, Any

class HumanNames:
    """Преобразование технических названий в человечные"""
    
    # Домены вопросов
    DOMAIN_NAMES = {
        "IDENTITY": "Личность",
        "RELATIONSHIPS": "Отношения", 
        "WORK": "Работа",
        "EMOTIONS": "Эмоции",
        "MONEY": "Финансы",
        "HEALTH": "Здоровье", 
        "CREATIVITY": "Творчество",
        "SPIRITUALITY": "Духовность",
        "PAST": "Прошлое",
        "FUTURE": "Будущее",
        "LIFESTYLE": "Образ жизни",
        "THOUGHTS": "Мышление"
    }
    
    # Уровни глубины
    DEPTH_NAMES = {
        "SURFACE": "Поверхностный",
        "CONSCIOUS": "Осознанный", 
        "EDGE": "Глубокий",
        "SHADOW": "Теневой",
        "CORE": "Глубинный"
    }
    
    # Энергетические состояния
    ENERGY_NAMES = {
        "OPENING": "Вдохновляющий",
        "NEUTRAL": "Спокойный",
        "PROCESSING": "Размышляющий", 
        "HEAVY": "Серьезный",
        "HEALING": "Исцеляющий",
        "DRAINING": "Затратный"
    }
    
    # Стадии путешествия
    JOURNEY_NAMES = {
        "ENTRY": "Знакомство",
        "WARMING": "Разогрев",
        "EXPLORING": "Исследование", 
        "DEEPENING": "Углубление",
        "BREAKTHROUGH": "Прорыв",
        "INTEGRATION": "Интеграция"
    }
    
    # AI модели (для понимания админа)
    MODEL_NAMES = {
        "claude-3.5-sonnet": "Claude (премиум анализ)",
        "gpt-4o": "GPT-4 (стандарт)",
        "gpt-4o-mini": "GPT-Mini (быстрый)",
        "rule_based": "Правила (без AI)"
    }
    
    # Уровни сложности
    COMPLEXITY_NAMES = {
        1: "Очень простой",
        2: "Простой", 
        3: "Средний",
        4: "Сложный",
        5: "Очень сложный"
    }
    
    # Эмоциональные веса
    EMOTIONAL_WEIGHT_NAMES = {
        1: "Легкий",
        2: "Спокойный",
        3: "Средний", 
        4: "Эмоциональный",
        5: "Очень эмоциональный"
    }
    
    # Типы дополнений (elaborations)
    ELABORATION_ICONS = {
        "инструкции_по_ответу": "🎯",
        "предостережения": "⚠️", 
        "призывы_к_действию": "🚀",
        "психологические_объяснения": "🧠",
        "связующие_анализы": "🔗"
    }
    
    ELABORATION_NAMES = {
        "инструкции_по_ответу": "Как отвечать",
        "предостережения": "Важно знать",
        "призывы_к_действию": "Действие",
        "психологические_объяснения": "Психология",
        "связующие_анализы": "Связи"
    }
    
    @classmethod
    def get_domain_human(cls, domain: str) -> str:
        """Получить человечное название домена"""
        return cls.DOMAIN_NAMES.get(domain, domain)
    
    @classmethod
    def get_depth_human(cls, depth: str) -> str:
        """Получить человечное название глубины"""
        return cls.DEPTH_NAMES.get(depth, depth)
    
    @classmethod
    def get_energy_human(cls, energy: str) -> str:
        """Получить человечное название энергии"""
        return cls.ENERGY_NAMES.get(energy, energy)
    
    @classmethod
    def get_journey_human(cls, journey: str) -> str:
        """Получить человечное название стадии"""
        return cls.JOURNEY_NAMES.get(journey, journey)
    
    @classmethod
    def get_model_human(cls, model: str) -> str:
        """Получить человечное название модели"""
        return cls.MODEL_NAMES.get(model, model)
    
    @classmethod
    def get_complexity_human(cls, complexity: int) -> str:
        """Получить человечное описание сложности"""
        return cls.COMPLEXITY_NAMES.get(complexity, f"Уровень {complexity}")
    
    @classmethod
    def get_emotional_weight_human(cls, weight: int) -> str:
        """Получить человечное описание эмоционального веса"""
        return cls.EMOTIONAL_WEIGHT_NAMES.get(weight, f"Уровень {weight}")
    
    @classmethod
    def get_elaboration_icon(cls, elaboration_type: str) -> str:
        """Получить иконку для типа дополнения"""
        return cls.ELABORATION_ICONS.get(elaboration_type, "💡")
    
    @classmethod
    def get_elaboration_name(cls, elaboration_type: str) -> str:
        """Получить человечное название типа дополнения"""
        return cls.ELABORATION_NAMES.get(elaboration_type, elaboration_type)
    
    @classmethod
    def format_debug_info(cls, question_data: Dict[str, Any], analysis_data: Dict[str, Any] = None) -> str:
        """
        Форматирование debug информации для админа
        
        Args:
            question_data: Данные вопроса из JSON
            analysis_data: Данные анализа (опционально)
            
        Returns:
            Красиво отформатированная debug информация
        """
        
        classification = question_data.get("classification", {})
        psychology = question_data.get("psychology", {})
        
        debug_info = f"""🔍 <b>Debug информация:</b>
        
<b>📍 Вопрос:</b>
• ID: {question_data.get('id', 'unknown')}
• Тема: {cls.get_domain_human(classification.get('domain', 'UNKNOWN'))}
• Глубина: {cls.get_depth_human(classification.get('depth_level', 'UNKNOWN'))}
• Энергия: {cls.get_energy_human(classification.get('energy_dynamic', 'UNKNOWN'))}
• Стадия: {cls.get_journey_human(classification.get('journey_stage', 'UNKNOWN'))}

<b>🎯 Характеристики:</b>
• Сложность: {cls.get_complexity_human(psychology.get('complexity', 1))}
• Эмоц. вес: {cls.get_emotional_weight_human(psychology.get('emotional_weight', 1))}
• Потенциал: {psychology.get('insight_potential', 1)}/5
• Доверие: {psychology.get('trust_requirement', 1)}/5
• Безопасность: {psychology.get('safety_level', 5)}/5"""

        if analysis_data:
            processing_meta = analysis_data.get("processing_metadata", {})
            quality_meta = analysis_data.get("quality_metadata", {})
            
            debug_info += f"""

<b>🤖 Анализ:</b>
• Модель: {cls.get_model_human(processing_meta.get('model_used', 'unknown'))}
• Время: {processing_meta.get('processing_time_ms', 0)}ms  
• Качество: {quality_meta.get('overall_reliability', 0):.2f}/1.0
• Ситуация: {processing_meta.get('special_situation', 'обычная')}"""
        
        return debug_info
    
    @classmethod
    def format_user_progress(cls, session_data: Dict[str, Any]) -> str:
        """Форматирование прогресса пользователя"""
        
        question_count = len(session_data.get("answer_history", []))
        session_length = session_data.get("session_length_minutes", 0)
        domains_covered = set(
            item.get("question", {}).get("classification", {}).get("domain", "UNKNOWN")
            for item in session_data.get("question_history", [])
        )
        
        human_domains = [cls.get_domain_human(domain) for domain in domains_covered if domain != "UNKNOWN"]
        
        return f"""📊 <b>Ваш прогресс:</b>

🎯 <b>Вопросов пройдено:</b> {question_count}
⏰ <b>Время сессии:</b> {session_length:.0f} минут
🌟 <b>Изученные темы:</b> {', '.join(human_domains) if human_domains else 'начальное знакомство'}

💫 <b>Следующий шаг:</b> Продолжаем углубляться в понимание вашей личности"""