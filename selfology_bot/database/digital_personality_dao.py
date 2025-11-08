"""
DigitalPersonalityDAO - работа с многослойной цифровой личностью

🎯 ЦЕЛЬ: Сохранение и извлечение детальной информации о пользователе
📊 ПОДХОД: JSONB слои для гибкого хранения конкретных данных
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from selfology_bot.database import DatabaseService

logger = logging.getLogger(__name__)


class DigitalPersonalityDAO:
    """
    DAO для работы с digital_personality

    Принцип: Сохраняем КОНКРЕТИКУ, не абстракцию
    - ✅ "рисование, программирование, боты"
    - ❌ "высокая креативность"
    """

    def __init__(self, db_service: DatabaseService):
        self.db = db_service

    async def get_personality(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Получить цифровую личность пользователя

        Args:
            user_id: ID пользователя

        Returns:
            Полная личность со всеми слоями или None
        """

        query = """
            SELECT
                id, user_id,
                identity, interests, goals, barriers,
                relationships, values, current_state,
                skills, experiences, health,
                total_answers_analyzed, last_updated,
                personality_version, completeness_score
            FROM selfology.digital_personality
            WHERE user_id = $1
        """

        async with self.db.get_connection() as conn:
            row = await conn.fetchrow(query, user_id)

            if not row:
                logger.info(f"No personality found for user {user_id}")
                return None

            import json
            personality = dict(row)

            # Парсим JSONB поля из строк в объекты Python
            jsonb_fields = ['identity', 'interests', 'goals', 'barriers', 'relationships', 'values', 'current_state', 'skills', 'experiences', 'health']
            for field in jsonb_fields:
                if field in personality and personality[field]:
                    if isinstance(personality[field], str):
                        try:
                            personality[field] = json.loads(personality[field])
                        except (json.JSONDecodeError, TypeError):
                            logger.warning(f"Failed to parse {field} for user {user_id}, using empty dict")
                            personality[field] = {}

            logger.info(f"✅ Loaded personality for user {user_id} (version: {personality['personality_version']})")
            return personality

    async def create_personality(
        self,
        user_id: int,
        initial_extraction: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Создать новую цифровую личность

        Args:
            user_id: ID пользователя
            initial_extraction: Первоначальные данные из первого ответа

        Returns:
            ID созданной записи
        """

        # Пустая структура по умолчанию - ARRAY, не dict!
        empty_layer = []

        # Если есть начальные данные - используем их
        layers = initial_extraction if initial_extraction else {
            "identity": empty_layer,
            "interests": empty_layer,
            "goals": empty_layer,
            "barriers": empty_layer,
            "relationships": empty_layer,
            "values": empty_layer,
            "current_state": empty_layer,
            "skills": empty_layer,
            "experiences": empty_layer,
            "health": empty_layer
        }

        query = """
            INSERT INTO selfology.digital_personality (
                user_id,
                identity, interests, goals, barriers,
                relationships, values, current_state,
                skills, experiences, health,
                total_answers_analyzed, last_updated,
                personality_version, completeness_score
            ) VALUES (
                $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11,
                1, NOW(), '1.0', 0.1
            )
            RETURNING id
        """

        import json

        async with self.db.get_connection() as conn:
            personality_id = await conn.fetchval(
                query,
                user_id,
                json.dumps(layers.get("identity", {})),
                json.dumps(layers.get("interests", {})),
                json.dumps(layers.get("goals", {})),
                json.dumps(layers.get("barriers", {})),
                json.dumps(layers.get("relationships", {})),
                json.dumps(layers.get("values", {})),
                json.dumps(layers.get("current_state", {})),
                json.dumps(layers.get("skills", {})),
                json.dumps(layers.get("experiences", {})),
                json.dumps(layers.get("health", {}))
            )

        logger.info(f"✅ Created personality for user {user_id} (id: {personality_id})")
        return personality_id

    async def update_personality(
        self,
        user_id: int,
        new_extraction: Dict[str, Any],
        merge: bool = True
    ) -> bool:
        """
        Обновить цифровую личность новыми данными

        Args:
            user_id: ID пользователя
            new_extraction: Новая извлеченная информация
            merge: Объединять с существующими данными или перезаписать

        Returns:
            True если успешно обновлено
        """

        # Получаем существующую личность
        existing = await self.get_personality(user_id)

        if not existing and merge:
            # Если личности нет - создаём новую
            await self.create_personality(user_id, new_extraction)
            return True

        # Подготавливаем данные для обновления
        if merge and existing:
            # Объединяем слои (правильный формат - arrays)
            updated_layers = {
                "identity": self._merge_layer(existing.get("identity", []), new_extraction.get("identity", [])),
                "interests": self._merge_layer(existing.get("interests", []), new_extraction.get("interests", [])),
                "goals": self._merge_layer(existing.get("goals", []), new_extraction.get("goals", [])),
                "barriers": self._merge_layer(existing.get("barriers", []), new_extraction.get("barriers", [])),
                "relationships": self._merge_layer(existing.get("relationships", []), new_extraction.get("relationships", [])),
                "values": self._merge_layer(existing.get("values", []), new_extraction.get("values", [])),
                "current_state": self._merge_layer(existing.get("current_state", []), new_extraction.get("current_state", [])),
                "skills": self._merge_layer(existing.get("skills", []), new_extraction.get("skills", [])),
                "experiences": self._merge_layer(existing.get("experiences", []), new_extraction.get("experiences", [])),
                "health": self._merge_layer(existing.get("health", []), new_extraction.get("health", []))
            }

            # Обновляем счетчик анализов
            total_analyzed = existing.get("total_answers_analyzed", 0) + 1

            # Вычисляем completeness_score
            completeness = self._calculate_completeness(updated_layers)
        else:
            # Просто перезаписываем
            updated_layers = new_extraction
            total_analyzed = 1
            completeness = self._calculate_completeness(updated_layers)

        # Обновляем в базе
        query = """
            UPDATE selfology.digital_personality
            SET
                identity = $2,
                interests = $3,
                goals = $4,
                barriers = $5,
                relationships = $6,
                values = $7,
                current_state = $8,
                skills = $9,
                experiences = $10,
                health = $11,
                total_answers_analyzed = $12,
                last_updated = NOW(),
                completeness_score = $13
            WHERE user_id = $1
        """

        import json

        async with self.db.get_connection() as conn:
            await conn.execute(
                query,
                user_id,
                json.dumps(updated_layers["identity"]),
                json.dumps(updated_layers["interests"]),
                json.dumps(updated_layers["goals"]),
                json.dumps(updated_layers["barriers"]),
                json.dumps(updated_layers["relationships"]),
                json.dumps(updated_layers["values"]),
                json.dumps(updated_layers["current_state"]),
                json.dumps(updated_layers["skills"]),
                json.dumps(updated_layers["experiences"]),
                json.dumps(updated_layers["health"]),
                total_analyzed,
                completeness
            )

        logger.info(f"✅ Updated personality for user {user_id} (completeness: {completeness:.2f})")
        return True

    def _merge_layer(self, existing: Any, new: Any) -> Any:
        """
        Объединить данные слоя (работает с arrays и dict)

        Правила:
        - Новые элементы добавляются
        - Существующие дополняются новой информацией
        - Ничего не удаляется
        """

        if not existing:
            return new if new else []

        if not new:
            return existing

        # СЛУЧАЙ 1: Оба параметра - arrays (правильный формат PersonalityExtractor)
        if isinstance(existing, list) and isinstance(new, list):
            return self._merge_lists(existing, new)

        # СЛУЧАЙ 2: Оба параметра - dict (старый формат, совместимость)
        if isinstance(existing, dict) and isinstance(new, dict):
            merged = existing.copy()
            for key, value in new.items():
                if key not in merged:
                    merged[key] = value
                else:
                    if isinstance(value, dict) and isinstance(merged[key], dict):
                        merged[key] = self._merge_layer(merged[key], value)
                    elif isinstance(value, list) and isinstance(merged[key], list):
                        merged[key] = self._merge_lists(merged[key], value)
                    else:
                        merged[key] = value
            return merged

        # СЛУЧАЙ 3: Разные типы - приоритет у нового формата (array)
        if isinstance(new, list):
            return new
        if isinstance(existing, list):
            return existing

        # Fallback
        return new

    def _merge_lists(self, existing: List, new: List) -> List:
        """Объединить списки без дубликатов"""

        # Для списков словарей - проверяем дубликаты по содержимому
        if existing and isinstance(existing[0], dict):
            result = existing.copy()
            for new_item in new:
                # Проверяем, есть ли уже такой элемент
                is_duplicate = False
                for existing_item in result:
                    if self._items_similar(new_item, existing_item):
                        # Дубликат найден - обновляем существующий
                        existing_item.update({k: v for k, v in new_item.items() if v})
                        is_duplicate = True
                        break

                if not is_duplicate:
                    result.append(new_item)

            return result
        else:
            # Для простых списков - union
            return list(set(existing + new))

    def _items_similar(self, item1: Dict, item2: Dict) -> bool:
        """Проверка на схожесть элементов (упрощённая)"""

        # Ищем ключевые поля для сравнения
        key_fields = ["activity", "skill", "goal", "barrier", "person", "value", "aspect"]

        for field in key_fields:
            if field in item1 and field in item2:
                val1 = str(item1[field]).lower()
                val2 = str(item2[field]).lower()
                # Простое сравнение (можно улучшить с fuzzy matching)
                if val1 == val2 or val1 in val2 or val2 in val1:
                    return True

        return False

    def _calculate_completeness(self, layers: Dict[str, Any]) -> float:
        """
        Вычислить полноту профиля

        Returns:
            Score от 0.0 до 1.0
        """

        total_fields = 0
        filled_fields = 0

        for layer_name, layer_data in layers.items():
            if not layer_data:
                continue

            total_fields += 1

            # Считаем заполненность слоя
            if isinstance(layer_data, dict):
                # Для JSONB объектов - считаем количество ключей
                if len(layer_data) > 0:
                    filled_fields += min(len(layer_data) / 5, 1.0)  # Нормализуем
            elif isinstance(layer_data, list):
                # Для списков - наличие элементов
                if len(layer_data) > 0:
                    filled_fields += 1

        if total_fields == 0:
            return 0.0

        return filled_fields / total_fields

    async def get_personality_summary(self, user_id: int) -> Optional[str]:
        """
        Получить краткое описание личности для AI

        Это то, что AI увидит при запросе "расскажи про меня"

        Returns:
            Текстовое описание личности
        """

        personality = await self.get_personality(user_id)

        if not personality:
            return None

        # Формируем человекочитаемое описание
        parts = []

        # Интересы
        interests = personality.get("interests", {})
        if interests:
            parts.append(f"**Интересы**: {self._format_layer(interests)}")

        # Навыки
        skills = personality.get("skills", {})
        if skills:
            parts.append(f"**Навыки**: {self._format_layer(skills)}")

        # Цели
        goals = personality.get("goals", {})
        if goals:
            parts.append(f"**Цели**: {self._format_layer(goals)}")

        # Барьеры/страхи
        barriers = personality.get("barriers", {})
        if barriers:
            parts.append(f"**Барьеры**: {self._format_layer(barriers)}")

        # Отношения
        relationships = personality.get("relationships", {})
        if relationships:
            parts.append(f"**Важные люди**: {self._format_layer(relationships)}")

        # Здоровье
        health = personality.get("health", {})
        if health:
            parts.append(f"**Здоровье**: {self._format_layer(health)}")

        # Текущее состояние
        current_state = personality.get("current_state", {})
        if current_state:
            parts.append(f"**Сейчас**: {self._format_layer(current_state)}")

        if not parts:
            return "Информация о личности пока не собрана."

        summary = "\n".join(parts)
        summary += f"\n\n*На основе {personality.get('total_answers_analyzed', 0)} ответов*"

        return summary

    def _format_layer(self, layer_data: Dict[str, Any]) -> str:
        """Форматировать слой для человекочитаемого вывода"""

        if not layer_data:
            return "—"

        # Если это список объектов
        if isinstance(layer_data, dict) and any(isinstance(v, list) for v in layer_data.values()):
            # Извлекаем ключевые поля
            items = []
            for key, value in layer_data.items():
                if isinstance(value, list):
                    for item in value:
                        if isinstance(item, dict):
                            # Берём первое значимое поле
                            for field in ["activity", "skill", "goal", "barrier", "person", "value", "aspect"]:
                                if field in item:
                                    items.append(item[field])
                                    break
                        else:
                            items.append(str(item))

            return ", ".join(items[:10])  # Первые 10

        # Простой dict
        if isinstance(layer_data, dict):
            return ", ".join([f"{k}: {v}" for k, v in list(layer_data.items())[:5]])

        return str(layer_data)
