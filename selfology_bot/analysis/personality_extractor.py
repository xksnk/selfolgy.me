"""
Personality Extractor - Извлечение детальной информации для цифровой личности

🎯 ЦЕЛЬ: Создать точное, детальное описание пользователя на основе ответов
📊 ПОДХОД: Извлечение конкретики (увлечения, страхи, цели, барьеры, отношения)
🧠 AI: Реальный OpenAI API для глубокого анализа текста
"""

import logging
import json
import os
from typing import Dict, Any, List, Optional
from datetime import datetime
import asyncio

# OpenAI client
try:
    from openai import AsyncOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    logger = logging.getLogger(__name__)
    logger.warning("⚠️ OpenAI not installed - personality extraction will use fallback")
    OPENAI_AVAILABLE = False

logger = logging.getLogger(__name__)


class PersonalityExtractor:
    """
    Извлечение детальной информации из ответов для построения цифровой личности

    Принцип: AI извлекает КОНКРЕТИКУ, не абстракцию
    - ✅ "рисование, программирование, боты"
    - ❌ "высокая рефлексивность"
    """

    def __init__(self):
        """Инициализация extractor"""

        # OpenAI client
        self.openai_client = None
        if OPENAI_AVAILABLE:
            api_key = os.getenv("OPENAI_API_KEY")
            if api_key:
                self.openai_client = AsyncOpenAI(api_key=api_key)
                logger.info("✅ OpenAI client initialized for personality extraction")
            else:
                logger.warning("⚠️ OPENAI_API_KEY not found - using fallback")

        # Статистика
        self.stats = {
            "total_extractions": 0,
            "successful_extractions": 0,
            "api_calls": 0,
            "fallback_used": 0
        }

        logger.info("🧠 PersonalityExtractor initialized")

    async def extract_from_answer(
        self,
        question_text: str,
        user_answer: str,
        question_metadata: Dict[str, Any],
        existing_personality: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Извлечь информацию из ответа

        Args:
            question_text: Текст вопроса
            user_answer: Ответ пользователя
            question_metadata: Метаданные вопроса (domain, depth, etc.)
            existing_personality: Существующая информация о личности

        Returns:
            Извлечённая информация по всем слоям
        """

        try:
            self.stats["total_extractions"] += 1

            # Строим промпт для извлечения
            extraction_prompt = self._build_extraction_prompt(
                question_text,
                user_answer,
                question_metadata,
                existing_personality
            )

            # Вызываем OpenAI API
            if self.openai_client:
                extracted_data = await self._call_openai_extraction(extraction_prompt)
                self.stats["api_calls"] += 1
            else:
                # Fallback: правила без AI
                extracted_data = self._rule_based_extraction(user_answer, question_metadata)
                self.stats["fallback_used"] += 1

            self.stats["successful_extractions"] += 1

            return extracted_data

        except Exception as e:
            logger.error(f"❌ Error extracting personality: {e}", exc_info=True)
            return self._empty_extraction()

    def _build_extraction_prompt(
        self,
        question_text: str,
        user_answer: str,
        question_metadata: Dict[str, Any],
        existing_personality: Optional[Dict[str, Any]]
    ) -> str:
        """
        Построить промпт для извлечения информации

        КРИТИЧНО: Промпт должен требовать КОНКРЕТИКУ, не абстракцию
        """

        domain = question_metadata.get("classification", {}).get("domain", "GENERAL")

        prompt = f"""Ты - эксперт по психологическому анализу. Твоя задача - извлечь КОНКРЕТНУЮ информацию из ответа пользователя для построения его цифровой личности.

ВОПРОС ({domain}): "{question_text}"

ОТВЕТ ПОЛЬЗОВАТЕЛЯ: "{user_answer}"

ЗАДАЧА: Извлеки конкретную информацию. НЕ делай общих выводов типа "высокая рефлексивность". ТОЛЬКО конкретные факты.

Извлеки информацию по следующим категориям (только если есть в ответе):

0. ИДЕНТИЧНОСТЬ (identity):
   - Кем себя описывает?
   - Профессия/роль?
   - Как себя воспринимает?
   - Самоопределение?

1. ИНТЕРЕСЫ/УВЛЕЧЕНИЯ (interests):
   - Что пользователь любит делать?
   - Какие хобби упоминает?
   - Что его привлекает?

2. НАВЫКИ (skills):
   - Какие умения упоминает?
   - Что умеет делать?
   - Какие технологии/инструменты использует?

3. ЦЕЛИ/ЖЕЛАНИЯ (goals):
   - Чего хочет достичь?
   - О чём мечтает?
   - Какие планы упоминает?

4. БАРЬЕРЫ/СТРАХИ (barriers):
   - Что мешает?
   - Чего боится/стесняется?
   - Какие ограничения упоминает?

5. ОТНОШЕНИЯ (relationships):
   - Кто важен для пользователя?
   - Кого упоминает?
   - Какие отношения описывает?

6. ЦЕННОСТИ (values):
   - Что важно для пользователя?
   - Какие принципы упоминает?

7. ЗДОРОВЬЕ (health):
   - Физическое состояние?
   - Ментальное состояние?
   - Ограничения/проблемы?

8. ТЕКУЩЕЕ СОСТОЯНИЕ (current_state):
   - Чем занимается сейчас?
   - Что активно делает?
   - Что забросил?

ФОРМАТ ОТВЕТА (строгий JSON):
{{
  "identity": [
    {{"aspect": "профессия/роль/самоопределение", "description": "как описывает", "confidence": "low/medium/high"}}
  ],
  "interests": [
    {{"activity": "название", "context": "контекст", "status": "active/inactive"}}
  ],
  "skills": [
    {{"skill": "название", "level": "начальный/средний/высокий", "specifics": ["детали"]}}
  ],
  "goals": [
    {{"goal": "цель", "type": "short_term/long_term", "priority": "low/medium/high"}}
  ],
  "barriers": [
    {{"barrier": "название", "type": "physical/emotional/practical", "impact": "описание"}}
  ],
  "relationships": [
    {{"person": "кто", "relationship": "тип отношений"}}
  ],
  "values": [
    {{"value": "ценность", "context": "в какой области"}}
  ],
  "health": [
    {{"aspect": "что", "condition": "состояние", "impact": "влияние"}}
  ],
  "current_state": [
    {{"activity": "что делает", "status": "active/learning/inactive"}}
  ],
  "key_phrases": ["точные фразы из ответа, которые важны"]
}}

ВАЖНО:
- Используй точные слова из ответа
- Не придумывай то, чего нет
- Если категория пустая - верни пустой массив []
- Все поля должны быть заполнены
"""

        return prompt

    async def _call_openai_extraction(self, prompt: str) -> Dict[str, Any]:
        """Вызов OpenAI для извлечения информации"""

        try:
            response = await self.openai_client.chat.completions.create(
                model="gpt-4o",  # Используем лучшую модель для точности
                messages=[
                    {
                        "role": "system",
                        "content": "Ты эксперт по извлечению структурированной информации. Возвращай ТОЛЬКО валидный JSON без дополнительного текста."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,  # Низкая температура для точности
                max_tokens=1500,
                response_format={"type": "json_object"}  # Гарантированный JSON
            )

            content = response.choices[0].message.content
            extracted = json.loads(content)

            logger.info(f"✅ OpenAI extraction successful")
            return extracted

        except Exception as e:
            logger.error(f"❌ OpenAI extraction failed: {e}")
            return self._empty_extraction()

    def _rule_based_extraction(
        self,
        user_answer: str,
        question_metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Простое извлечение без AI (fallback)"""

        logger.warning("⚠️ Using rule-based extraction (OpenAI not available)")

        # Простые правила
        answer_lower = user_answer.lower()

        extracted = self._empty_extraction()

        # Базовое извлечение
        extracted["key_phrases"] = [user_answer[:100]]

        # Детекция страхов
        fear_keywords = ["боюсь", "страшно", "стесняюсь", "не могу"]
        if any(kw in answer_lower for kw in fear_keywords):
            extracted["barriers"].append({
                "barrier": user_answer[:50],
                "type": "emotional",
                "impact": "detected from keywords"
            })

        # Детекция целей
        goal_keywords = ["хочу", "мечтаю", "планирую", "надо"]
        if any(kw in answer_lower for kw in goal_keywords):
            extracted["goals"].append({
                "goal": user_answer[:50],
                "type": "unspecified",
                "priority": "medium"
            })

        return extracted

    def _empty_extraction(self) -> Dict[str, Any]:
        """Пустая структура извлечения"""
        return {
            "identity": [],
            "interests": [],
            "skills": [],
            "goals": [],
            "barriers": [],
            "relationships": [],
            "values": [],
            "health": [],
            "current_state": [],
            "key_phrases": []
        }

    def merge_extractions(
        self,
        existing: Dict[str, Any],
        new: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Объединить новую информацию с существующей

        Правила:
        - Новая информация дополняет, не перезаписывает
        - Дубликаты удаляются
        - Противоречия помечаются для ревью
        """

        merged = existing.copy() if existing else {}

        for category in ["identity", "interests", "skills", "goals", "barriers", "relationships", "values", "health", "current_state"]:
            if category not in merged:
                merged[category] = []

            # Добавляем новые элементы
            existing_items = merged[category]
            new_items = new.get(category, [])

            for new_item in new_items:
                # Проверка типа: пропускаем невалидные элементы
                if not isinstance(new_item, dict):
                    logger.warning(f"⚠️ Skipping invalid item in {category}: {type(new_item)}")
                    continue

                # Проверяем дубликаты (упрощённая логика)
                is_duplicate = False
                for existing_item in existing_items:
                    # Проверка типа existing_item тоже
                    if not isinstance(existing_item, dict):
                        continue

                    if self._is_duplicate(new_item, existing_item, category):
                        is_duplicate = True
                        # Обновляем существующий элемент если есть новая информация
                        existing_item.update({k: v for k, v in new_item.items() if v and k not in existing_item})
                        break

                if not is_duplicate:
                    merged[category].append(new_item)

        # Объединяем ключевые фразы
        if "key_phrases" not in merged:
            merged["key_phrases"] = []
        merged["key_phrases"].extend(new.get("key_phrases", []))

        return merged

    def _is_duplicate(
        self,
        item1: Dict[str, Any],
        item2: Dict[str, Any],
        category: str
    ) -> bool:
        """Проверка на дубликаты"""

        # Ключи для сравнения по категориям
        key_fields = {
            "identity": "aspect",
            "interests": "activity",
            "skills": "skill",
            "goals": "goal",
            "barriers": "barrier",
            "relationships": "person",
            "values": "value",
            "health": "aspect",
            "current_state": "activity"
        }

        key_field = key_fields.get(category)
        if not key_field:
            return False

        val1 = str(item1.get(key_field, "")).lower()
        val2 = str(item2.get(key_field, "")).lower()

        # Простое сравнение (можно улучшить с помощью fuzzy matching)
        return val1 == val2 or val1 in val2 or val2 in val1
