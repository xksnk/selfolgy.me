"""
ProgramRouter - Роутер вопросов на основе блочной структуры программ.

Логика:
1. Программа состоит из блоков (Foundation → Exploration → Integration)
2. Внутри блока вопросы идут по позиции (можно Smart Mix)
3. Переход между блоками строго последовательный
4. Foundation обязателен перед Exploration
5. Один блок = одна сессия (рекомендуется)

Интеграция:
- Используется новыми сессиями с program_id
- Старые сессии используют legacy QuestionRouter
"""

import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum
import asyncpg

logger = logging.getLogger(__name__)


class BlockType(Enum):
    """Типы блоков программы"""
    FOUNDATION = "Foundation"      # Вход, безопасность, ориентация
    EXPLORATION = "Exploration"    # Углубление, исследование
    INTEGRATION = "Integration"    # Синтез, закрытие, действие


@dataclass
class ProgramContext:
    """Контекст программы для пользователя"""
    user_id: int
    program_id: str
    program_name: str
    current_block_id: Optional[str] = None
    current_block_type: Optional[BlockType] = None
    current_block_sequence: int = 0
    questions_answered_in_block: int = 0
    total_questions_in_block: int = 0
    blocks_completed: List[str] = None
    total_blocks: int = 0
    completion_percentage: int = 0

    def __post_init__(self):
        if self.blocks_completed is None:
            self.blocks_completed = []


class ProgramRouter:
    """
    Роутер вопросов на основе блочной структуры программ.

    Правила:
    - Foundation блок обязателен первым
    - Exploration блоки идут после Foundation
    - Integration блок завершает программу
    - Внутри блока вопросы по позиции (или Smart Mix если настроено)
    """

    def __init__(self, db_pool: asyncpg.Pool = None):
        """
        Инициализация роутера.

        Args:
            db_pool: Пул подключений к PostgreSQL
        """
        self.db_pool = db_pool
        logger.info("🎯 ProgramRouter initialized for block-based navigation")

    async def get_program_context(
        self,
        user_id: int,
        program_id: str
    ) -> Optional[ProgramContext]:
        """
        Получить контекст программы для пользователя.

        Создаёт новый прогресс если не существует.
        """
        async with self.db_pool.acquire() as conn:
            # Проверяем существующий прогресс
            progress = await conn.fetchrow("""
                SELECT
                    up.current_block_id,
                    up.blocks_completed,
                    up.questions_answered,
                    up.completion_percentage,
                    p.name as program_name,
                    (SELECT COUNT(*) FROM selfology.program_blocks WHERE program_id = $2) as total_blocks
                FROM selfology.user_program_progress up
                JOIN selfology.onboarding_programs p ON up.program_id = p.program_id
                WHERE up.user_id = $1 AND up.program_id = $2 AND up.status = 'active'
            """, user_id, program_id)

            if not progress:
                # Получаем информацию о программе
                program = await conn.fetchrow("""
                    SELECT name FROM selfology.onboarding_programs WHERE program_id = $1
                """, program_id)

                if not program:
                    logger.error(f"❌ Program not found: {program_id}")
                    return None

                total_blocks = await conn.fetchval("""
                    SELECT COUNT(*) FROM selfology.program_blocks WHERE program_id = $1
                """, program_id)

                # Создаём новый прогресс
                await conn.execute("""
                    INSERT INTO selfology.user_program_progress
                    (user_id, program_id, status, blocks_completed)
                    VALUES ($1, $2, 'active', '{}')
                    ON CONFLICT (user_id, program_id, status) DO NOTHING
                """, user_id, program_id)

                return ProgramContext(
                    user_id=user_id,
                    program_id=program_id,
                    program_name=program['name'],
                    total_blocks=total_blocks
                )

            # Получаем информацию о текущем блоке
            block_info = None
            if progress['current_block_id']:
                block_info = await conn.fetchrow("""
                    SELECT
                        b.block_type,
                        b.sequence,
                        (SELECT COUNT(*) FROM selfology.program_questions WHERE block_id = b.block_id) as total_questions
                    FROM selfology.program_blocks b
                    WHERE b.block_id = $1
                """, progress['current_block_id'])

            return ProgramContext(
                user_id=user_id,
                program_id=program_id,
                program_name=progress['program_name'],
                current_block_id=progress['current_block_id'],
                current_block_type=BlockType(block_info['block_type']) if block_info else None,
                current_block_sequence=block_info['sequence'] if block_info else 0,
                total_questions_in_block=block_info['total_questions'] if block_info else 0,
                blocks_completed=progress['blocks_completed'] or [],
                total_blocks=progress['total_blocks'],
                completion_percentage=progress['completion_percentage']
            )

    async def get_first_question_in_program(
        self,
        user_id: int,
        program_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Получить первый вопрос программы (первый вопрос Foundation блока).
        """
        async with self.db_pool.acquire() as conn:
            # Находим первый Foundation блок
            first_block = await conn.fetchrow("""
                SELECT block_id, name
                FROM selfology.program_blocks
                WHERE program_id = $1 AND block_type = 'Foundation'
                ORDER BY sequence ASC
                LIMIT 1
            """, program_id)

            if not first_block:
                # Если нет Foundation, берём первый блок
                first_block = await conn.fetchrow("""
                    SELECT block_id, name
                    FROM selfology.program_blocks
                    WHERE program_id = $1
                    ORDER BY sequence ASC
                    LIMIT 1
                """, program_id)

            if not first_block:
                logger.error(f"❌ No blocks found for program: {program_id}")
                return None

            # Создаём или обновляем прогресс пользователя
            await conn.execute("""
                INSERT INTO selfology.user_program_progress
                (user_id, program_id, current_block_id, status, blocks_completed)
                VALUES ($1, $2, $3, 'active', '{}')
                ON CONFLICT (user_id, program_id, status) DO UPDATE
                SET current_block_id = $3, last_activity_at = NOW()
            """, user_id, program_id, first_block['block_id'])

            # Получаем первый вопрос блока
            question = await conn.fetchrow("""
                SELECT
                    q.question_id as id,
                    q.text,
                    q.format,
                    q.position,
                    q.position_in_block,
                    q.journey_stage,
                    q.depth_level,
                    q.domain,
                    q.energy_dynamic,
                    q.complexity,
                    q.emotional_weight,
                    q.safety_level,
                    q.recommended_model,
                    q.requires_context,
                    b.block_id,
                    b.name as block_name,
                    b.block_type
                FROM selfology.program_questions q
                JOIN selfology.program_blocks b ON q.block_id = b.block_id
                WHERE q.block_id = $1
                ORDER BY q.position_in_block ASC
                LIMIT 1
            """, first_block['block_id'])

            if not question:
                logger.error(f"❌ No questions in block: {first_block['block_id']}")
                return None

            logger.info(f"✅ First question for {program_id}: {question['id']}")

            return self._format_question(question)

    async def get_next_question_in_block(
        self,
        user_id: int,
        program_id: str,
        answered_question_ids: List[str]
    ) -> Optional[Dict[str, Any]]:
        """
        Получить следующий вопрос в текущем блоке.

        Args:
            user_id: ID пользователя
            program_id: ID программы
            answered_question_ids: Список уже отвеченных вопросов

        Returns:
            Следующий вопрос или None если блок завершён
        """
        async with self.db_pool.acquire() as conn:
            # Получаем текущий блок
            progress = await conn.fetchrow("""
                SELECT current_block_id
                FROM selfology.user_program_progress
                WHERE user_id = $1 AND program_id = $2 AND status = 'active'
            """, user_id, program_id)

            if not progress or not progress['current_block_id']:
                logger.warning(f"⚠️ No active block for user {user_id} in {program_id}")
                return None

            current_block_id = progress['current_block_id']

            # Находим следующий неотвеченный вопрос в блоке
            question = await conn.fetchrow("""
                SELECT
                    q.question_id as id,
                    q.text,
                    q.format,
                    q.position,
                    q.position_in_block,
                    q.journey_stage,
                    q.depth_level,
                    q.domain,
                    q.energy_dynamic,
                    q.complexity,
                    q.emotional_weight,
                    q.safety_level,
                    q.recommended_model,
                    q.requires_context,
                    b.block_id,
                    b.name as block_name,
                    b.block_type
                FROM selfology.program_questions q
                JOIN selfology.program_blocks b ON q.block_id = b.block_id
                WHERE q.block_id = $1
                  AND q.question_id != ALL($2::varchar[])
                ORDER BY q.position_in_block ASC
                LIMIT 1
            """, current_block_id, answered_question_ids)

            if not question:
                logger.info(f"📦 Block {current_block_id} completed for user {user_id}")
                return None

            logger.info(f"➡️ Next question in block: {question['id']}")

            return self._format_question(question)

    async def can_proceed_to_next_block(
        self,
        user_id: int,
        program_id: str,
        min_questions_answered: int = 2
    ) -> bool:
        """
        Проверить, можно ли перейти к следующему блоку.

        Правила:
        - Отвечено минимум N вопросов в текущем блоке
        - Foundation блок должен быть завершён полностью
        """
        async with self.db_pool.acquire() as conn:
            # Получаем текущий блок и прогресс
            progress = await conn.fetchrow("""
                SELECT
                    up.current_block_id,
                    up.questions_answered,
                    b.block_type,
                    (SELECT COUNT(*) FROM selfology.program_questions WHERE block_id = b.block_id) as total_in_block
                FROM selfology.user_program_progress up
                JOIN selfology.program_blocks b ON up.current_block_id = b.block_id
                WHERE up.user_id = $1 AND up.program_id = $2 AND up.status = 'active'
            """, user_id, program_id)

            if not progress:
                return False

            # Foundation блок должен быть пройден полностью (или почти)
            if progress['block_type'] == 'Foundation':
                min_required = max(min_questions_answered, progress['total_in_block'] - 1)
            else:
                min_required = min_questions_answered

            # TODO: Подсчитать реальное количество отвеченных вопросов в блоке
            # Пока используем общий счётчик

            return True  # Пока разрешаем переход

    async def get_next_block(
        self,
        user_id: int,
        program_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Получить следующий блок программы.

        Правила последовательности:
        1. Foundation → Exploration → Integration
        2. Все Exploration блоки по порядку sequence
        """
        async with self.db_pool.acquire() as conn:
            # Получаем текущий прогресс
            progress = await conn.fetchrow("""
                SELECT current_block_id, blocks_completed
                FROM selfology.user_program_progress
                WHERE user_id = $1 AND program_id = $2 AND status = 'active'
            """, user_id, program_id)

            if not progress:
                return None

            completed = progress['blocks_completed'] or []

            # Находим следующий блок по sequence
            next_block = await conn.fetchrow("""
                SELECT
                    b.block_id,
                    b.name,
                    b.block_type,
                    b.sequence,
                    b.description,
                    (SELECT COUNT(*) FROM selfology.program_questions WHERE block_id = b.block_id) as questions_count
                FROM selfology.program_blocks b
                WHERE b.program_id = $1
                  AND b.block_id != ALL($2::varchar[])
                ORDER BY b.sequence ASC
                LIMIT 1
            """, program_id, completed + [progress['current_block_id']] if progress['current_block_id'] else completed)

            if not next_block:
                logger.info(f"✅ Program {program_id} completed for user {user_id}")
                return None

            # Обновляем прогресс: добавляем текущий блок в completed, устанавливаем новый
            if progress['current_block_id']:
                await conn.execute("""
                    UPDATE selfology.user_program_progress
                    SET
                        current_block_id = $3,
                        blocks_completed = array_append(blocks_completed, $4),
                        last_activity_at = NOW()
                    WHERE user_id = $1 AND program_id = $2 AND status = 'active'
                """, user_id, program_id, next_block['block_id'], progress['current_block_id'])
            else:
                await conn.execute("""
                    UPDATE selfology.user_program_progress
                    SET current_block_id = $3, last_activity_at = NOW()
                    WHERE user_id = $1 AND program_id = $2 AND status = 'active'
                """, user_id, program_id, next_block['block_id'])

            logger.info(f"📦 Moving to next block: {next_block['name']} ({next_block['block_type']})")

            return {
                "block_id": next_block['block_id'],
                "name": next_block['name'],
                "type": next_block['block_type'],
                "sequence": next_block['sequence'],
                "description": next_block['description'],
                "questions_count": next_block['questions_count']
            }

    async def complete_program(
        self,
        user_id: int,
        program_id: str
    ) -> bool:
        """Завершить программу для пользователя."""
        async with self.db_pool.acquire() as conn:
            result = await conn.execute("""
                UPDATE selfology.user_program_progress
                SET
                    status = 'completed',
                    completion_percentage = 100,
                    completed_at = NOW()
                WHERE user_id = $1 AND program_id = $2 AND status = 'active'
            """, user_id, program_id)

            logger.info(f"✅ Program {program_id} completed for user {user_id}")
            return True

    async def get_available_programs(
        self,
        user_id: int,
        include_completed: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Получить список доступных программ для пользователя.

        Args:
            user_id: ID пользователя
            include_completed: Включать завершённые программы

        Returns:
            Список программ с информацией о прогрессе
        """
        async with self.db_pool.acquire() as conn:
            programs = await conn.fetch("""
                SELECT
                    p.program_id,
                    p.name,
                    p.description,
                    p.estimated_duration_min,
                    p.priority,
                    COALESCE(up.status, 'not_started') as user_status,
                    COALESCE(up.completion_percentage, 0) as completion,
                    (SELECT COUNT(*) FROM selfology.program_blocks WHERE program_id = p.program_id) as blocks_count,
                    (SELECT COUNT(*) FROM selfology.program_questions WHERE program_id = p.program_id) as questions_count
                FROM selfology.onboarding_programs p
                LEFT JOIN selfology.user_program_progress up
                    ON p.program_id = up.program_id AND up.user_id = $1
                WHERE p.status = 'active'
                ORDER BY p.priority ASC, p.name ASC
            """, user_id)

            result = []
            for p in programs:
                if not include_completed and p['user_status'] == 'completed':
                    continue

                result.append({
                    "program_id": p['program_id'],
                    "name": p['name'],
                    "description": p['description'],
                    "estimated_duration_min": p['estimated_duration_min'],
                    "user_status": p['user_status'],
                    "completion_percentage": p['completion'],
                    "blocks_count": p['blocks_count'],
                    "questions_count": p['questions_count']
                })

            return result

    def _format_question(self, row: asyncpg.Record) -> Dict[str, Any]:
        """Форматировать вопрос из записи БД в словарь."""
        return {
            "id": row['id'],
            "text": row['text'],
            "format": row['format'],
            "position": row['position'],
            "position_in_block": row['position_in_block'],
            "block_id": row['block_id'],
            "block_name": row['block_name'],
            "block_type": row['block_type'],
            "classification": {
                "journey_stage": row['journey_stage'],
                "depth_level": row['depth_level'],
                "domain": row['domain'],
                "energy_dynamic": row['energy_dynamic']
            },
            "psychology": {
                "complexity": row['complexity'],
                "emotional_weight": row['emotional_weight'],
                "safety_level": row['safety_level']
            },
            "recommended_model": row['recommended_model'],
            "requires_context": row['requires_context']
        }


# ============================================================
# ИНТЕГРАЦИЯ С LEGACY ROUTER
# ============================================================

async def create_program_router(db_pool: asyncpg.Pool) -> ProgramRouter:
    """Фабричный метод для создания роутера."""
    return ProgramRouter(db_pool=db_pool)
