"""
Soul Architect Service - Главный API системы

Единственная точка входа для работы с многослойной моделью личности.
Изолирован от других систем, использует только DatabaseService.

API:
- create_profile(user_id) - создать профиль
- get_profile(user_id) - получить профиль
- update_trait(user_id, trait_name, value, confidence) - обновить черту
- get_evolution(user_id, days) - получить историю изменений
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from ..database.service import DatabaseService
from .models import PersonalityProfile, TraitAssessment, TraitHistory, EvolutionSummary
from .profile_builder import ProfileBuilder
from .trait_scorer import TraitScorer
from .evolution_tracker import EvolutionTracker
from .config import config

logger = logging.getLogger(__name__)


class SoulArchitectService:
    """
    Soul Architect Service - главный API для работы с профилями личности

    Примеры:
        >>> service = SoulArchitectService(db_service)
        >>> await service.initialize()
        >>> profile = await service.create_profile(123456)
        >>> await service.update_trait(
        ...     user_id=123456,
        ...     category="big_five",
        ...     trait_name="openness",
        ...     value=0.75,
        ...     confidence=0.85
        ... )
    """

    def __init__(self, database_service: DatabaseService):
        """
        Args:
            database_service: DatabaseService для работы с БД
        """
        self.db = database_service
        self.builder = ProfileBuilder()
        self.scorer = TraitScorer()
        self.evolution = EvolutionTracker()

        logger.info("SoulArchitectService initialized")

    async def initialize(self) -> bool:
        """
        Инициализация сервиса

        Проверяет наличие таблиц в БД.

        Returns:
            True если успешно
        """
        try:
            # Проверяем наличие таблиц
            async with self.db.get_connection() as conn:
                # Проверяем personality_profiles
                result = await conn.fetchval("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables
                        WHERE table_schema = 'selfology'
                        AND table_name = 'personality_profiles'
                    )
                """)

                if not result:
                    logger.warning("personality_profiles table not found. Run migrations first!")
                    return False

            logger.info("SoulArchitectService initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize SoulArchitectService: {e}")
            return False

    # ========================================================================
    # ПРОФИЛИ
    # ========================================================================

    async def create_profile(self, user_id: int) -> PersonalityProfile:
        """
        Создать новый профиль личности

        Args:
            user_id: ID пользователя

        Returns:
            PersonalityProfile

        Raises:
            Exception: Если профиль уже существует или ошибка БД
        """
        logger.info(f"Creating profile for user {user_id}")

        # Проверяем, не существует ли профиль
        existing = await self.get_profile(user_id, raise_if_not_found=False)
        if existing:
            logger.warning(f"Profile for user {user_id} already exists")
            return existing

        # Создаем пустой профиль
        profile = self.builder.create_empty_profile(user_id)

        # Сохраняем в БД
        await self._save_profile_to_db(profile)

        logger.info(f"Profile created for user {user_id}")
        return profile

    async def get_profile(
        self,
        user_id: int,
        raise_if_not_found: bool = True
    ) -> Optional[PersonalityProfile]:
        """
        Получить профиль личности

        Args:
            user_id: ID пользователя
            raise_if_not_found: Выбросить ошибку если не найден

        Returns:
            PersonalityProfile или None

        Raises:
            ValueError: Если профиль не найден и raise_if_not_found=True
        """
        logger.debug(f"Getting profile for user {user_id}")

        async with self.db.get_connection() as conn:
            row = await conn.fetchrow("""
                SELECT profile_data, created_at, updated_at
                FROM selfology.personality_profiles
                WHERE user_id = $1
            """, user_id)

            if not row:
                if raise_if_not_found:
                    raise ValueError(f"Profile for user {user_id} not found")
                return None

            # Десериализуем профиль
            profile_data = json.loads(row['profile_data'])
            profile = PersonalityProfile(**profile_data)

            return profile

    async def delete_profile(self, user_id: int) -> bool:
        """
        Удалить профиль личности

        Args:
            user_id: ID пользователя

        Returns:
            True если удалено
        """
        logger.info(f"Deleting profile for user {user_id}")

        async with self.db.get_connection() as conn:
            await conn.execute("""
                DELETE FROM selfology.personality_profiles
                WHERE user_id = $1
            """, user_id)

        return True

    # ========================================================================
    # ЧЕРТЫ
    # ========================================================================

    async def update_trait(
        self,
        user_id: int,
        category: str,
        trait_name: str,
        value: float,
        confidence: float,
        trigger: Optional[str] = None
    ) -> PersonalityProfile:
        """
        Обновить значение черты

        Args:
            user_id: ID пользователя
            category: Категория (big_five, core_dynamics, etc.)
            trait_name: Имя черты
            value: Новое значение (0.0 - 1.0)
            confidence: Уверенность в значении
            trigger: Что вызвало обновление

        Returns:
            Обновленный PersonalityProfile

        Raises:
            ValueError: Если профиль не найден или неверные параметры
        """
        logger.info(f"Updating trait {category}.{trait_name} for user {user_id}")

        # Получаем текущий профиль
        profile = await self.get_profile(user_id)

        # Получаем текущую черту
        layer = getattr(profile, category)
        current_trait = getattr(layer, trait_name)

        # Обновляем черту через scorer
        new_trait = self.scorer.update_trait(
            current_trait=current_trait,
            new_value=value
        )

        # Обновляем confidence
        new_trait.confidence = confidence

        # Записываем в историю
        await self._record_trait_change(
            user_id=user_id,
            category=category,
            trait_name=trait_name,
            old_value=current_trait.value,
            new_value=new_trait.value,
            confidence=confidence,
            trigger=trigger
        )

        # Обновляем профиль
        profile = self.builder.update_profile_trait(
            profile=profile,
            category=category,
            trait_name=trait_name,
            new_trait=new_trait
        )

        # Сохраняем в БД
        await self._save_profile_to_db(profile)

        logger.info(
            f"Trait updated: {category}.{trait_name} "
            f"{current_trait.value:.2f} -> {new_trait.value:.2f}"
        )

        return profile

    async def batch_update_traits(
        self,
        user_id: int,
        updates: List[Dict]
    ) -> PersonalityProfile:
        """
        Обновить несколько черт за раз

        Args:
            user_id: ID пользователя
            updates: Список обновлений [
                {
                    "category": "big_five",
                    "trait_name": "openness",
                    "value": 0.75,
                    "confidence": 0.85
                }
            ]

        Returns:
            Обновленный профиль
        """
        logger.info(f"Batch updating {len(updates)} traits for user {user_id}")

        profile = await self.get_profile(user_id)

        for update in updates:
            category = update["category"]
            trait_name = update["trait_name"]
            value = update["value"]
            confidence = update.get("confidence", 0.7)
            trigger = update.get("trigger", None)

            # Получаем и обновляем черту
            layer = getattr(profile, category)
            current_trait = getattr(layer, trait_name)

            new_trait = self.scorer.update_trait(current_trait, value)
            new_trait.confidence = confidence

            # Записываем в историю
            await self._record_trait_change(
                user_id=user_id,
                category=category,
                trait_name=trait_name,
                old_value=current_trait.value,
                new_value=new_trait.value,
                confidence=confidence,
                trigger=trigger
            )

            # Обновляем профиль
            profile = self.builder.update_profile_trait(
                profile, category, trait_name, new_trait
            )

        # Сохраняем один раз
        await self._save_profile_to_db(profile)

        logger.info(f"Batch update completed for user {user_id}")
        return profile

    # ========================================================================
    # ЭВОЛЮЦИЯ
    # ========================================================================

    async def get_evolution(
        self,
        user_id: int,
        days: int = 30
    ) -> EvolutionSummary:
        """
        Получить сводку эволюции личности

        Args:
            user_id: ID пользователя
            days: Период для анализа (дней)

        Returns:
            EvolutionSummary
        """
        logger.info(f"Getting evolution for user {user_id}, period {days} days")

        # Загружаем историю из БД
        history = await self._load_history_from_db(user_id, days)

        # Вычисляем сводку
        summary = self.evolution.calculate_evolution_summary(
            user_id=user_id,
            all_history=history,
            period_days=days
        )

        return summary

    async def get_trait_history(
        self,
        user_id: int,
        category: str,
        trait_name: str,
        days: Optional[int] = None
    ) -> List[TraitHistory]:
        """
        Получить историю изменений конкретной черты

        Args:
            user_id: ID пользователя
            category: Категория черты
            trait_name: Имя черты
            days: Период (если None - вся история)

        Returns:
            Список TraitHistory
        """
        async with self.db.get_connection() as conn:
            if days:
                cutoff = datetime.utcnow() - timedelta(days=days)
                rows = await conn.fetch("""
                    SELECT * FROM selfology.trait_history
                    WHERE user_id = $1
                    AND trait_category = $2
                    AND trait_name = $3
                    AND timestamp >= $4
                    ORDER BY timestamp DESC
                """, user_id, category, trait_name, cutoff)
            else:
                rows = await conn.fetch("""
                    SELECT * FROM selfology.trait_history
                    WHERE user_id = $1
                    AND trait_category = $2
                    AND trait_name = $3
                    ORDER BY timestamp DESC
                """, user_id, category, trait_name)

            return [TraitHistory(**dict(row)) for row in rows]

    # ========================================================================
    # ПРИВАТНЫЕ МЕТОДЫ
    # ========================================================================

    async def _save_profile_to_db(self, profile: PersonalityProfile) -> None:
        """Сохранить профиль в БД"""
        profile_json = profile.model_dump_json()

        async with self.db.get_connection() as conn:
            await conn.execute("""
                INSERT INTO selfology.personality_profiles
                (user_id, profile_data, created_at, updated_at)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (user_id)
                DO UPDATE SET
                    profile_data = EXCLUDED.profile_data,
                    updated_at = EXCLUDED.updated_at
            """, profile.user_id, profile_json, profile.created_at, profile.updated_at)

    async def _record_trait_change(
        self,
        user_id: int,
        category: str,
        trait_name: str,
        old_value: float,
        new_value: float,
        confidence: float,
        trigger: Optional[str] = None
    ) -> None:
        """Записать изменение черты в историю"""
        history_record = await self.evolution.record_change(
            user_id=user_id,
            trait_category=category,
            trait_name=trait_name,
            old_value=old_value,
            new_value=new_value,
            confidence=confidence,
            trigger=trigger
        )

        async with self.db.get_connection() as conn:
            await conn.execute("""
                INSERT INTO selfology.trait_history
                (user_id, trait_category, trait_name, old_value, new_value, confidence, trigger, timestamp)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """, user_id, category, trait_name, old_value, new_value, confidence, trigger, history_record.timestamp)

    async def _load_history_from_db(
        self,
        user_id: int,
        days: Optional[int] = None
    ) -> List[TraitHistory]:
        """Загрузить историю из БД"""
        async with self.db.get_connection() as conn:
            if days:
                cutoff = datetime.utcnow() - timedelta(days=days)
                rows = await conn.fetch("""
                    SELECT * FROM selfology.trait_history
                    WHERE user_id = $1 AND timestamp >= $2
                    ORDER BY timestamp DESC
                """, user_id, cutoff)
            else:
                rows = await conn.fetch("""
                    SELECT * FROM selfology.trait_history
                    WHERE user_id = $1
                    ORDER BY timestamp DESC
                """, user_id)

            return [TraitHistory(**dict(row)) for row in rows]
