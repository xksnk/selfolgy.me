"""
Answer Analyzer - Главный анализатор системы

🧠 ПРИНЦИП: "Каждый ответ - это штрих в портрете души"
🔬 АРХИТЕКТУРА: Координация всех компонентов анализа
⚡ ПРОИЗВОДИТЕЛЬНОСТЬ: Двухфазная обработка (instant + deep)
🛡️ БЕЗОПАСНОСТЬ: Детекция кризисов и деликатная работа
"""

import logging
import json
import asyncio
import os
from typing import Dict, Any, Optional, List
from datetime import datetime

from .analysis_config import AnalysisConfig
from .analysis_templates import AnalysisTemplates
from .ai_model_router import AIModelRouter
from .trait_extractor import TraitExtractor

# AI clients
try:
    from openai import AsyncOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    from anthropic import AsyncAnthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

logger = logging.getLogger(__name__)

class AnswerAnalyzer:
    """
    Главный координатор анализа ответов пользователей
    
    Интегрирует:
    - Умный выбор AI модели (AIModelRouter)
    - Адаптивные промпты (AnalysisTemplates)  
    - Извлечение черт личности (TraitExtractor)
    - Настраиваемые параметры (AnalysisConfig)
    
    Создает живой, эволюционирующий портрет личности.
    """
    
    def __init__(self):
        """Инициализация главного анализатора"""

        # Инициализируем все компоненты
        self.config = AnalysisConfig()
        self.templates = AnalysisTemplates()
        self.ai_router = AIModelRouter()
        self.trait_extractor = TraitExtractor()

        # AI клиенты
        self.openai_client = None
        self.anthropic_client = None

        if OPENAI_AVAILABLE:
            api_key = os.getenv("OPENAI_API_KEY")
            if api_key:
                self.openai_client = AsyncOpenAI(api_key=api_key)
                logger.info("✅ OpenAI client initialized for AnswerAnalyzer")
            else:
                logger.warning("⚠️ OPENAI_API_KEY not found")

        if ANTHROPIC_AVAILABLE:
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if api_key:
                self.anthropic_client = AsyncAnthropic(api_key=api_key)
                logger.info("✅ Anthropic client initialized for AnswerAnalyzer")
            else:
                logger.warning("⚠️ ANTHROPIC_API_KEY not found")

        # Статистика работы
        self.analysis_stats = {
            "total_analyses": 0,
            "successful_analyses": 0,
            "crisis_detections": 0,
            "breakthrough_moments": 0,
            "avg_processing_time_ms": 0
        }

        logger.info("🔬 AnswerAnalyzer initialized - ready to analyze souls")
    
    async def analyze_answer(
        self,
        question_data: Dict[str, Any], 
        user_answer: str,
        user_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        ГЛАВНЫЙ МЕТОД - полный анализ ответа пользователя
        
        Args:
            question_data: Полный объект вопроса из JSON (17 метаданных)
            user_answer: Текст ответа пользователя
            user_context: Контекст пользователя (ID, история, состояние)
            
        Returns:
            Полный анализ с психологическими инсайтами и численными чертами
        """
        
        start_time = datetime.now()
        user_id = user_context.get("user_id", "unknown")
        
        try:
            logger.info(f"🔬 Starting comprehensive analysis for user {user_id}")
            
            # 1. ПОДГОТОВКА КОНТЕКСТА
            enriched_context = await self._enrich_context(question_data, user_answer, user_context)
            
            # 2. ДЕТЕКЦИЯ ОСОБЫХ СИТУАЦИЙ
            special_situation = self._detect_special_situations(user_answer, enriched_context)
            
            # 3. ВЫБОР AI МОДЕЛИ 
            model_name, model_config = await self.ai_router.select_model_for_analysis(
                question_data, enriched_context
            )
            
            # 4. ОПРЕДЕЛЕНИЕ ГЛУБИНЫ АНАЛИЗА
            analysis_depth = self.config.get_analysis_depth(
                question_number=enriched_context.get("question_number", 1),
                trust_level=enriched_context.get("trust_level", 0.5),
                energy_level=enriched_context.get("energy_level", 0.5),
                fatigue_level=enriched_context.get("fatigue_level", 0.0)
            )
            
            # 5. ПОЛУЧЕНИЕ AI АНАЛИЗА
            ai_analysis = await self._get_ai_analysis(
                model_name, 
                model_config,
                question_data,
                user_answer, 
                enriched_context,
                analysis_depth,
                special_situation
            )
            
            # 6. ИЗВЛЕЧЕНИЕ ЧЕРТ ЛИЧНОСТИ
            trait_analysis = await self.trait_extractor.extract_traits_from_analysis(
                ai_analysis, question_data, enriched_context
            )
            
            # 7. ФОРМИРОВАНИЕ ФИНАЛЬНОГО РЕЗУЛЬТАТА
            final_result = self._build_final_analysis(
                ai_analysis,
                trait_analysis,
                question_data,
                enriched_context,
                model_name,
                analysis_depth,
                special_situation
            )
            
            # 8. ОБНОВЛЕНИЕ СТАТИСТИКИ
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            self._update_analysis_stats(final_result, processing_time, True)
            
            # 9. ТРЕКИНГ AI МОДЕЛИ
            await self._track_ai_usage(model_name, model_config, final_result, processing_time)
            
            logger.info(f"✅ Comprehensive analysis completed for user {user_id} in {processing_time:.0f}ms")
            return final_result
            
        except Exception as e:
            logger.error(f"❌ Error in comprehensive analysis for user {user_id}: {e}")
            
            # Fallback анализ
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            self._update_analysis_stats({}, processing_time, False)
            
            return await self._get_emergency_analysis(question_data, user_answer, user_context, str(e))
    
    async def _enrich_context(
        self, 
        question_data: Dict[str, Any], 
        user_answer: str, 
        user_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Обогащение контекста дополнительными данными"""
        
        enriched = user_context.copy()
        
        # Добавляем анализ ответа
        enriched.update({
            "answer_length": len(user_answer),
            "answer_word_count": len(user_answer.split()),
            "answer_sentence_count": user_answer.count('.') + user_answer.count('!') + user_answer.count('?'),
            "time_of_day": datetime.now().hour,
            "user_answer": user_answer,  # Для анализа
            
            # Из метаданных вопроса
            "question_domain": question_data["classification"]["domain"],
            "question_depth": question_data["classification"]["depth_level"],
            "question_energy": question_data["classification"]["energy_dynamic"],
            "question_complexity": question_data["psychology"]["complexity"],
            "question_emotional_weight": question_data["psychology"]["emotional_weight"],
            "question_insight_potential": question_data["psychology"]["insight_potential"]
        })
        
        # Определяем уровень доверия на основе прогресса
        question_number = enriched.get("question_number", 1)
        enriched["trust_level"] = min(1.0, 0.2 + (question_number / 30.0) * 0.8)
        
        # Оцениваем энергию пользователя
        enriched["energy_level"] = self._estimate_user_energy(enriched)
        
        return enriched
    
    def _detect_special_situations(self, user_answer: str, context: Dict[str, Any]) -> Optional[str]:
        """
        Детекция особых ситуаций требующих специального подхода
        
        Returns:
            "crisis" | "breakthrough" | "resistance" | None
        """
        
        answer_lower = user_answer.lower()
        
        # Детекция кризиса
        crisis_keywords = self.config.SAFETY_RULES["crisis_keywords"]
        if any(keyword in answer_lower for keyword in crisis_keywords):
            logger.warning(f"🚨 Crisis indicators detected in answer")
            return "crisis"
        
        # Детекция прорыва (по признакам в ответе)
        breakthrough_indicators = [
            "понял", "осознал", "прорыв", "инсайт", "вдруг понял",
            "теперь вижу", "открылось", "стало ясно"
        ]
        if (any(indicator in answer_lower for indicator in breakthrough_indicators) and
            len(user_answer) > 100):
            logger.info(f"🌟 Breakthrough moment detected")
            return "breakthrough"
        
        # Детекция сопротивления  
        resistance_indicators = [
            "не хочу", "не буду", "глупый вопрос", "не понимаю зачем",
            "какая разница", "не важно", "без понятия"
        ]
        if any(indicator in answer_lower for indicator in resistance_indicators):
            logger.info(f"🛡️ Resistance detected")
            return "resistance"
        
        return None
    
    async def _get_ai_analysis(
        self,
        model_name: str,
        model_config: Dict[str, Any],
        question_data: Dict[str, Any],
        user_answer: str,
        context: Dict[str, Any],
        analysis_depth: str,
        special_situation: Optional[str]
    ) -> Dict[str, Any]:
        """Получить анализ от AI модели"""
        
        try:
            # Получаем подходящий промпт
            prompt = self._build_ai_prompt(
                model_name, analysis_depth, special_situation, 
                question_data, user_answer, context
            )
            
            # Здесь будет вызов реальной AI API
            # Пока что mock для разработки
            ai_response = await self._call_ai_api(model_name, prompt, model_config)
            
            # Парсим и валидируем ответ
            parsed_analysis = self._parse_and_validate_ai_response(ai_response, model_name)
            
            return parsed_analysis
            
        except Exception as e:
            logger.error(f"❌ AI analysis failed: {e}")
            
            # Fallback на другую модель
            fallback_model, fallback_config = await self.ai_router.get_fallback_model(model_name, e)
            
            if fallback_model != "rule_based":
                return await self._get_ai_analysis(
                    fallback_model, fallback_config, question_data, 
                    user_answer, context, analysis_depth, special_situation
                )
            else:
                # Последний fallback - правила без AI
                return self._get_rule_based_analysis(user_answer, question_data, context)
    
    def _build_ai_prompt(
        self,
        model_name: str,
        analysis_depth: str, 
        special_situation: Optional[str],
        question_data: Dict[str, Any],
        user_answer: str,
        context: Dict[str, Any]
    ) -> str:
        """Построить промпт для AI модели"""
        
        # Базовый контекст для промпта
        prompt_context = {
            "question_text": question_data["text"],
            "domain": question_data["classification"]["domain"], 
            "depth_level": question_data["classification"]["depth_level"],
            "energy_dynamic": question_data["classification"]["energy_dynamic"],
            "complexity": question_data["psychology"]["complexity"],
            "emotional_weight": question_data["psychology"]["emotional_weight"],
            "insight_potential": question_data["psychology"]["insight_potential"],
            "trust_requirement": question_data["psychology"]["trust_requirement"],
            "safety_level": question_data["psychology"]["safety_level"],
            
            "user_answer": user_answer,
            "question_number": context.get("question_number", 1),
            "response_time_seconds": context.get("response_time_seconds", 30),
            "answer_length": len(user_answer),
            "time_of_day": context.get("time_of_day", datetime.now().hour),
            "current_timestamp": datetime.now().isoformat(),
            
            # Дополнительная информация
            "domain_description": self._get_domain_description(question_data["classification"]["domain"]),
            "previous_domains": context.get("previous_domains", [])
        }
        
        # Выбираем тип анализа
        if special_situation:
            analysis_type = special_situation  # crisis, breakthrough, resistance
        else:
            analysis_type = "standard"
        
        # Получаем промпт из templates
        if special_situation in ["crisis", "breakthrough", "resistance"]:
            prompt = self.templates.get_prompt_for_model(model_name, special_situation, prompt_context)
        else:
            prompt = self.templates.get_depth_prompt(analysis_depth, prompt_context)
        
        return prompt
    
    async def _call_ai_api(self, model_name: str, prompt: str, model_config: Dict[str, Any]) -> str:
        """
        Вызов AI API (реальный OpenAI/Anthropic)

        Args:
            model_name: Название модели (gpt-4o, gpt-4o-mini, claude-3.5-sonnet)
            prompt: Промпт для анализа
            model_config: Конфигурация модели (timeout, temperature, etc.)

        Returns:
            JSON строка с анализом от AI
        """

        start_time = datetime.now()

        try:
            if model_name == "claude-3.5-sonnet":
                # Anthropic Claude
                if not self.anthropic_client:
                    raise ValueError("Anthropic client not initialized - check ANTHROPIC_API_KEY")

                response = await self.anthropic_client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=model_config.get("max_tokens", 2000),
                    temperature=model_config.get("temperature", 0.7),
                    messages=[{"role": "user", "content": prompt}]
                )

                ai_response = response.content[0].text

            elif model_name in ["gpt-4o", "gpt-4o-mini"]:
                # OpenAI GPT
                if not self.openai_client:
                    raise ValueError("OpenAI client not initialized - check OPENAI_API_KEY")

                response = await self.openai_client.chat.completions.create(
                    model=model_name,
                    messages=[
                        {
                            "role": "system",
                            "content": "Ты профессиональный психолог-аналитик. Возвращай ТОЛЬКО валидный JSON без дополнительного текста."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    temperature=model_config.get("temperature", 0.7),
                    max_tokens=model_config.get("max_tokens", 2000),
                    response_format={"type": "json_object"}  # Гарантированный JSON
                )

                ai_response = response.choices[0].message.content

            else:
                raise ValueError(f"Unknown model: {model_name}")

            # Измеряем время
            processing_time = (datetime.now() - start_time).total_seconds() * 1000

            logger.info(f"🤖 AI analysis completed using {model_name} in {processing_time:.0f}ms")

            return ai_response

        except Exception as e:
            logger.error(f"❌ AI API call failed for {model_name}: {e}")
            # Fallback на упрощенный анализ
            raise
    
    def _parse_and_validate_ai_response(self, ai_response: str, model_name: str) -> Dict[str, Any]:
        """Парсинг и валидация ответа AI"""
        
        try:
            # Парсим JSON
            parsed = json.loads(ai_response)
            
            # Валидируем обязательные поля
            required_fields = ["core_analysis", "traits"]
            if self.templates.validate_response(ai_response, required_fields):
                return parsed
            else:
                logger.warning(f"⚠️ AI response validation failed for {model_name}")
                return self._fix_malformed_response(parsed)
                
        except json.JSONDecodeError as e:
            logger.error(f"❌ JSON parsing failed for {model_name}: {e}")
            return self._extract_from_malformed_json(ai_response)
    
    def _fix_malformed_response(self, parsed: Dict) -> Dict[str, Any]:
        """Исправление неполного ответа AI"""
        
        # Добавляем отсутствующие обязательные поля
        if "core_analysis" not in parsed:
            parsed["core_analysis"] = {
                "emotional_state": {"primary": "neutral", "valence": 0.0, "arousal": 0.0},
                "insights": {"main": "Анализ частично доступен"}
            }
        
        if "traits" not in parsed:
            parsed["traits"] = {
                "big_five": {trait: 0.5 for trait in self.config.BIG_FIVE_TRAITS}
            }
        
        # Валидируем Big Five значения
        big_five = parsed.get("traits", {}).get("big_five", {})
        for trait in self.config.BIG_FIVE_TRAITS:
            if trait not in big_five or not (0 <= big_five[trait] <= 1):
                big_five[trait] = 0.5
        
        parsed["_fixed_by_validator"] = True
        return parsed
    
    def _build_final_analysis(
        self,
        ai_analysis: Dict[str, Any],
        trait_analysis: Dict[str, Any], 
        question_data: Dict[str, Any],
        context: Dict[str, Any],
        model_name: str,
        analysis_depth: str,
        special_situation: Optional[str]
    ) -> Dict[str, Any]:
        """Формирование финального результата анализа"""
        
        return {
            # Версионирование и метаданные
            "analysis_version": "2.0",
            "created_at": datetime.now().isoformat(),
            "processing_metadata": {
                "model_used": model_name,
                "analysis_depth": analysis_depth,
                "special_situation": special_situation,
                "question_domain": question_data["classification"]["domain"],
                "question_number": context.get("question_number", 1)
            },
            
            # Основной психологический анализ
            "psychological_analysis": {
                "insights": ai_analysis.get("core_analysis", {}).get("insights", {}),
                "emotional_assessment": ai_analysis.get("core_analysis", {}).get("emotional_state", {}),
                "behavioral_patterns": ai_analysis.get("patterns", []),
                "growth_indicators": ai_analysis.get("growth_indicators", [])
            },
            
            # Численные оценки черт
            "personality_traits": trait_analysis["traits"],
            
            # Метаданные качества
            "quality_metadata": {
                "trait_confidence": trait_analysis["assessment_metadata"]["confidence_scores"],
                "overall_reliability": trait_analysis["assessment_metadata"]["reliability_indicators"]["overall_reliability"],
                "data_completeness": self._assess_data_completeness(ai_analysis, trait_analysis),
                "needs_validation": trait_analysis["assessment_metadata"]["reliability_indicators"]["needs_validation"]
            },
            
            # Рекомендации для роутера
            "router_recommendations": ai_analysis.get("recommendations", {}),
            
            # Для векторизации
            "personality_summary": self._generate_personality_summary(ai_analysis, trait_analysis, context),
            
            # Служебная информация
            "debug_info": {
                "raw_ai_response_length": len(str(ai_analysis)),
                "trait_extraction_successful": True,
                "fallback_used": context.get("fallback_used", False),
                "processing_notes": []
            }
        }
    
    def _generate_personality_summary(
        self, 
        ai_analysis: Dict[str, Any], 
        trait_analysis: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, str]:
        """
        Генерация многослойного summary для векторной БД
        
        Returns:
            Словарь с разными уровнями детализации
        """
        
        insights = ai_analysis.get("core_analysis", {}).get("insights", {})
        main_insight = insights.get("main", "")
        traits = trait_analysis["traits"]["big_five"]
        
        # Определяем архетип личности
        archetype = self._determine_personality_archetype(traits)
        
        # Уровень 1: Nano-summary (50 символов)
        dominant_traits = sorted(traits.items(), key=lambda x: x[1], reverse=True)[:2]
        nano = f"{archetype} ({dominant_traits[0][0]}: {dominant_traits[0][1]:.1f})"
        
        # Уровень 2: Структурированный профиль
        structured = {
            "archetype": archetype,
            "core_traits": [f"{trait}: {value:.2f}" for trait, value in dominant_traits[:3]],
            "communication_style": self._infer_communication_style(traits, ai_analysis),
            "energy_signature": self._infer_energy_pattern(context),
            "growth_edge": insights.get("growth_edge", "развитие самосознания")
        }
        
        # Уровень 3: Narrative (200-300 слов)
        narrative = f"""
        {main_insight}
        
        Основные черты: высокая {dominant_traits[0][0]} ({dominant_traits[0][1]:.2f}) и 
        {dominant_traits[1][0]} ({dominant_traits[1][1]:.2f}), что создает уникальный паттерн 
        личности. {insights.get('patterns', [''])[0] if insights.get('patterns') else ''}
        
        Стиль взаимодействия: {structured['communication_style']}.
        Зона роста: {structured['growth_edge']}.
        """
        
        # Уровень 4: Embedding prompt
        embedding_prompt = f"""
        {archetype}, {' '.join([f'{trait} {value:.1f}' for trait, value in traits.items()])},
        {structured['communication_style']}, {structured['energy_signature']}
        """
        
        return {
            "nano": nano[:50],  # Строго ограничиваем длину
            "structured": json.dumps(structured, ensure_ascii=False),
            "narrative": narrative.strip(),
            "embedding_prompt": embedding_prompt
        }
    
    def _determine_personality_archetype(self, big_five_traits: Dict[str, float]) -> str:
        """Определение архетипа личности на основе Big Five"""

        o, c, e, a, n = [big_five_traits[trait] for trait in ["openness", "conscientiousness", "extraversion", "agreeableness", "neuroticism"]]

        # Простая логика архетипов на основе доминирующих черт
        if o > 0.7 and e < 0.5:
            return "Мудрый Созерцатель"
        elif o > 0.7 and e > 0.6:
            return "Вдохновляющий Творец"
        elif c > 0.7 and a > 0.6:
            return "Надежный Организатор"
        elif e > 0.7 and a > 0.6:
            return "Теплый Коммуникатор"
        elif o > 0.6 and c > 0.6:
            return "Аналитический Исследователь"
        elif a > 0.7:
            return "Чуткий Помощник"
        elif c > 0.6:
            return "Целеустремленный Деятель"
        elif e > 0.6:
            return "Социальный Энтузиаст"
        elif o > 0.6:
            return "Ищущий Нового"
        else:
            return "Гармоничная Личность"

    def _infer_communication_style(self, big_five_traits: Dict[str, float], ai_analysis: Dict[str, Any]) -> str:
        """
        Определение стиля коммуникации на основе черт личности

        Args:
            big_five_traits: Big Five черты личности
            ai_analysis: Результат AI анализа

        Returns:
            Описание стиля коммуникации
        """
        e = big_five_traits.get("extraversion", 0.5)
        a = big_five_traits.get("agreeableness", 0.5)
        o = big_five_traits.get("openness", 0.5)
        c = big_five_traits.get("conscientiousness", 0.5)

        # Определяем стиль на основе комбинации черт
        if e > 0.7 and a > 0.6:
            return "открытый и эмпатичный, легко устанавливает контакт"
        elif e > 0.7 and o > 0.6:
            return "энергичный и творческий, вдохновляет собеседников"
        elif e < 0.4 and o > 0.6:
            return "вдумчивый и глубокий, предпочитает содержательные беседы"
        elif c > 0.7 and a > 0.6:
            return "структурированный и внимательный к деталям"
        elif a > 0.7:
            return "дипломатичный и чуткий, находит общий язык с разными людьми"
        elif e > 0.6:
            return "активный и общительный, легко включается в диалог"
        elif o > 0.6:
            return "любознательный и открытый новым идеям"
        else:
            return "сбалансированный и гибкий в общении"

    def _infer_energy_pattern(self, context: Dict[str, Any]) -> str:
        """
        Определение энергетического паттерна пользователя

        Args:
            context: Контекст пользователя

        Returns:
            Описание энергетического паттерна
        """
        energy_level = context.get("energy_level", 0.5)
        engagement = context.get("engagement_level", 0.5)
        fatigue = context.get("fatigue_level", 0.0)

        if fatigue > 0.6:
            return "необходим отдых и восстановление"
        elif energy_level > 0.7 and engagement > 0.7:
            return "высокая энергия и вовлечённость"
        elif energy_level > 0.6:
            return "стабильная энергия"
        elif energy_level < 0.4:
            return "низкий уровень энергии, требуется поддержка"
        else:
            return "умеренная энергия"
    
    def _get_rule_based_analysis(self, user_answer: str, question_data: Dict, context: Dict) -> Dict[str, Any]:
        """Простой анализ без AI (последний fallback)"""
        
        logger.warning("🔄 Using rule-based analysis (no AI available)")
        
        # Базовый анализ на ключевых словах и эвристиках
        answer_lower = user_answer.lower()
        answer_length = len(user_answer)
        
        # Простая эмоциональная классификация
        if any(word in answer_lower for word in ["рад", "счастлив", "хорошо", "отлично"]):
            emotional_state = "positive"
            valence = 0.7
        elif any(word in answer_lower for word in ["грустно", "плохо", "сложно", "тяжело"]):
            emotional_state = "negative"
            valence = -0.3
        else:
            emotional_state = "neutral"
            valence = 0.0
        
        # Простые эвристики для Big Five
        simple_traits = {}
        for trait in self.config.BIG_FIVE_TRAITS:
            simple_traits[trait] = self.trait_extractor._estimate_trait_from_text(
                trait, user_answer, question_data
            )
        
        return {
            "analysis_version": "2.0",
            "timestamp": datetime.now().isoformat(),
            "core_analysis": {
                "emotional_state": {
                    "primary": emotional_state,
                    "valence": valence,
                    "arousal": 0.3
                },
                "insights": {
                    "main": f"Анализ на основе эвристик. Ответ длиной {answer_length} символов показывает {emotional_state} настрой.",
                    "note": "Ограниченный анализ без AI"
                }
            },
            "traits": {
                "big_five": simple_traits
            },
            "meta_assessment": {
                "confidence": 0.3,  # Низкая уверенность
                "method": "rule_based",
                "needs_ai_reanalysis": True
            },
            "_is_fallback": True
        }
    
    def _assess_data_completeness(self, ai_analysis: Dict, trait_analysis: Dict) -> float:
        """Оценка полноты данных анализа"""
        
        completeness_score = 0.0
        total_checks = 0
        
        # Проверяем наличие ключевых компонентов
        checks = [
            ("emotional_state" in ai_analysis.get("core_analysis", {}), 0.2),
            ("insights" in ai_analysis.get("core_analysis", {}), 0.2),
            ("big_five" in trait_analysis.get("traits", {}), 0.3),
            ("confidence_scores" in trait_analysis.get("assessment_metadata", {}), 0.1),
            ("recommendations" in ai_analysis, 0.2)
        ]
        
        for check, weight in checks:
            total_checks += weight
            if check:
                completeness_score += weight
        
        return round(completeness_score / total_checks if total_checks > 0 else 0.0, 2)
    
    def _update_analysis_stats(self, result: Dict, processing_time_ms: float, success: bool):
        """Обновление статистики анализа"""
        
        self.analysis_stats["total_analyses"] += 1
        
        if success:
            self.analysis_stats["successful_analyses"] += 1
            
            # Обновляем среднее время
            old_avg = self.analysis_stats["avg_processing_time_ms"]
            old_count = self.analysis_stats["successful_analyses"] - 1
            
            if old_count > 0:
                new_avg = (old_avg * old_count + processing_time_ms) / (old_count + 1)
            else:
                new_avg = processing_time_ms
                
            self.analysis_stats["avg_processing_time_ms"] = round(new_avg, 1)
            
            # Специальные события
            if result.get("processing_metadata", {}).get("special_situation") == "crisis":
                self.analysis_stats["crisis_detections"] += 1
            elif result.get("processing_metadata", {}).get("special_situation") == "breakthrough":
                self.analysis_stats["breakthrough_moments"] += 1
    
    async def _track_ai_usage(self, model_name: str, model_config: Dict, result: Dict, processing_time_ms: float):
        """Трекинг использования AI для оптимизации"""
        
        # Оцениваем качество анализа
        quality_score = result.get("quality_metadata", {}).get("overall_reliability", 0.5)
        
        # Оцениваем стоимость (примерно)
        tokens_used = len(str(result)) // 4  # Грубая оценка токенов
        model_cost_per_token = self.config.AI_MODEL_SETTINGS[model_name].get("cost_per_token", 0.00001)
        estimated_cost = tokens_used * model_cost_per_token
        
        # Отправляем в роутер для статистики
        self.ai_router.track_usage(model_name, estimated_cost, quality_score, int(processing_time_ms))

    def _estimate_user_energy(self, context: Dict[str, Any]) -> float:
        """
        Оценка энергетического уровня пользователя на основе контекста

        Args:
            context: Обогащенный контекст с данными о пользователе

        Returns:
            float от 0.0 до 1.0 (0.0 = низкая энергия, 1.0 = высокая)
        """

        energy_score = 0.5  # Базовая оценка

        # 1. Анализ длины ответов (более длинные = выше энергия)
        answer_length = context.get("answer_length", 50)
        if answer_length > 200:
            energy_score += 0.2
        elif answer_length < 30:
            energy_score -= 0.2

        # 2. Анализ скорости ответов (быстрые = выше энергия)
        response_time = context.get("response_time_seconds", 60)
        if response_time < 30:
            energy_score += 0.1
        elif response_time > 120:
            energy_score -= 0.1

        # 3. Прогресс в онбординге (усталость накапливается)
        question_number = context.get("question_number", 1)
        fatigue_factor = min(0.3, question_number / 100)  # Max 0.3 усталости
        energy_score -= fatigue_factor

        # 4. Fatigue level из контекста
        fatigue_level = context.get("fatigue_level", 0.0)
        energy_score -= fatigue_level * 0.3

        # Нормализуем в диапазон [0.0, 1.0]
        return max(0.0, min(1.0, energy_score))

    def _get_domain_description(self, domain: str) -> str:
        """
        Получить человекочитаемое описание психологического домена

        Args:
            domain: Код домена (IDENTITY, EMOTIONS, etc.)

        Returns:
            Описание домена на русском языке
        """

        domain_descriptions = {
            "IDENTITY": "Идентичность и самопознание",
            "EMOTIONS": "Эмоции и чувства",
            "RELATIONSHIPS": "Отношения и связи",
            "VALUES": "Ценности и убеждения",
            "GOALS": "Цели и стремления",
            "FEARS": "Страхи и опасения",
            "GROWTH": "Рост и развитие",
            "PAST": "Прошлое и опыт",
            "FUTURE": "Будущее и мечты",
            "WORK": "Работа и призвание",
            "CREATIVITY": "Творчество и самовыражение",
            "BODY": "Тело и здоровье",
            "SPIRITUALITY": "Духовность и смыслы"
        }

        return domain_descriptions.get(domain, f"Домен: {domain}")

    async def _get_emergency_analysis(
        self,
        question_data: Dict[str, Any],
        user_answer: str,
        user_context: Dict[str, Any],
        error_message: str
    ) -> Dict[str, Any]:
        """
        Emergency fallback анализ при сбое основного pipeline

        Args:
            question_data: Данные вопроса
            user_answer: Ответ пользователя
            user_context: Контекст пользователя
            error_message: Сообщение об ошибке

        Returns:
            Минимальный но валидный анализ
        """

        user_id = user_context.get("user_id", "unknown")

        logger.warning(f"🚨 Using emergency analysis for user {user_id} due to: {error_message}")

        # Создаем минимальный валидный анализ
        return {
            "user_id": user_id,
            "question_id": question_data.get("id", "unknown"),

            # Personality traits (версия 2.0)
            "personality_traits": {
                "version": "2.0",
                "big_five": {
                    "openness": {"score": 0.5, "confidence": 0.2},
                    "conscientiousness": {"score": 0.5, "confidence": 0.2},
                    "extraversion": {"score": 0.5, "confidence": 0.2},
                    "agreeableness": {"score": 0.5, "confidence": 0.2},
                    "neuroticism": {"score": 0.5, "confidence": 0.2}
                },
                "timestamp": datetime.now().isoformat()
            },

            # Психологические insights
            "psychological_analysis": {
                "insights": {
                    "primary": "Спасибо за ваш ответ. Обрабатываю информацию...",
                    "secondary": []
                },
                "emotional_assessment": {
                    "primary": "neutral",
                    "intensity": 0.3
                }
            },

            # Router recommendations (пустые)
            "router_recommendations": {},

            # Processing metadata
            "processing_metadata": {
                "model_used": "emergency_handler",
                "processing_time_ms": 0,
                "timestamp": datetime.now().isoformat(),
                "special_situation": None
            },

            # Quality metadata
            "quality_metadata": {
                "overall_reliability": 0.3,
                "data_completeness": 0.5,
                "fatigue_indicators": 0.0
            },

            # Debug info
            "debug_info": {
                "is_emergency_analysis": True,
                "original_error": error_message
            },

            # ✅ Для векторизации - минимальный personality_summary
            "personality_summary": {
                "nano": user_answer[:50] if user_answer else "No answer",
                "structured": "{}",
                "narrative": f"Emergency analysis. Answer: {user_answer[:200] if user_answer else 'No answer'}",
                "embedding_prompt": user_answer[:500] if user_answer else "No answer provided"
            },

            # Analysis version
            "analysis_version": "emergency_fallback_v1"
        }

    async def get_analysis_stats(self) -> Dict[str, Any]:
        """Получить статистику работы анализатора"""
        
        success_rate = 0
        if self.analysis_stats["total_analyses"] > 0:
            success_rate = (self.analysis_stats["successful_analyses"] / self.analysis_stats["total_analyses"]) * 100
        
        return {
            **self.analysis_stats,
            "success_rate_percent": round(success_rate, 1),
            "ai_router_stats": self.ai_router.get_usage_report()
        }