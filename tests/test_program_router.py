#!/usr/bin/env python3
"""
Тесты для ProgramRouter и блочной структуры программ.

Проверяет:
1. Загрузку программ из БД
2. Навигацию по блокам
3. Выбор вопросов
4. Прогресс пользователя
"""

import asyncio
import pytest
import asyncpg
from pathlib import Path
import sys

# Добавляем путь к проекту
sys.path.insert(0, str(Path(__file__).parent.parent))

from selfology_bot.services.onboarding.program_router import (
    ProgramRouter,
    ProgramContext,
    BlockType
)


# Настройки тестовой БД
TEST_DB_CONFIG = {
    'host': 'localhost',
    'port': 5434,
    'database': 'selfology',
    'user': 'selfology_user',
    'password': 'selfology_secure_2024'
}

TEST_USER_ID = 999999  # Тестовый пользователь


@pytest.fixture
async def db_pool():
    """Создать пул подключений к БД."""
    pool = await asyncpg.create_pool(**TEST_DB_CONFIG)
    yield pool
    await pool.close()


@pytest.fixture
async def router(db_pool):
    """Создать ProgramRouter с пулом."""
    return ProgramRouter(db_pool=db_pool)


@pytest.fixture
async def cleanup_test_user(db_pool):
    """Очистить данные тестового пользователя после теста."""
    yield
    async with db_pool.acquire() as conn:
        await conn.execute("""
            DELETE FROM selfology.user_program_progress WHERE user_id = $1
        """, TEST_USER_ID)


class TestProgramRouter:
    """Тесты для ProgramRouter."""

    @pytest.mark.asyncio
    async def test_get_available_programs(self, router):
        """Тест получения списка доступных программ."""
        programs = await router.get_available_programs(TEST_USER_ID)

        assert len(programs) > 0, "Должны быть доступные программы"
        assert programs[0]['program_id'], "Программа должна иметь ID"
        assert programs[0]['name'], "Программа должна иметь название"
        assert 'blocks_count' in programs[0], "Должно быть количество блоков"
        assert 'questions_count' in programs[0], "Должно быть количество вопросов"

        print(f"\n✅ Найдено {len(programs)} программ")
        for p in programs[:5]:
            print(f"  - {p['name']}: {p['blocks_count']} блоков, {p['questions_count']} вопросов")

    @pytest.mark.asyncio
    async def test_get_program_context(self, router, cleanup_test_user):
        """Тест получения контекста программы."""
        # Получаем первую программу
        programs = await router.get_available_programs(TEST_USER_ID)
        program_id = programs[0]['program_id']

        # Получаем контекст (создаёт прогресс)
        context = await router.get_program_context(TEST_USER_ID, program_id)

        assert context is not None, "Контекст должен быть создан"
        assert context.user_id == TEST_USER_ID
        assert context.program_id == program_id
        assert context.program_name, "Должно быть название программы"
        assert context.total_blocks > 0, "Должны быть блоки"

        print(f"\n✅ Контекст программы '{context.program_name}':")
        print(f"  - Блоков: {context.total_blocks}")
        print(f"  - Текущий блок: {context.current_block_id or 'не начат'}")

    @pytest.mark.asyncio
    async def test_get_first_question(self, router, cleanup_test_user):
        """Тест получения первого вопроса программы."""
        programs = await router.get_available_programs(TEST_USER_ID)
        program_id = programs[0]['program_id']

        # Получаем первый вопрос
        question = await router.get_first_question_in_program(TEST_USER_ID, program_id)

        assert question is not None, "Должен быть первый вопрос"
        assert question['id'], "Вопрос должен иметь ID"
        assert question['text'], "Вопрос должен иметь текст"
        assert question['block_type'] == 'Foundation', "Первый блок должен быть Foundation"

        print(f"\n✅ Первый вопрос программы:")
        print(f"  - ID: {question['id']}")
        print(f"  - Блок: {question['block_name']} ({question['block_type']})")
        print(f"  - Текст: {question['text'][:60]}...")

    @pytest.mark.asyncio
    async def test_question_sequence(self, router, cleanup_test_user):
        """Тест последовательности вопросов в блоке."""
        programs = await router.get_available_programs(TEST_USER_ID)
        program_id = programs[0]['program_id']

        # Получаем первый вопрос
        q1 = await router.get_first_question_in_program(TEST_USER_ID, program_id)
        answered = [q1['id']]

        # Получаем следующий вопрос
        q2 = await router.get_next_question_in_block(TEST_USER_ID, program_id, answered)

        if q2:
            assert q2['id'] != q1['id'], "Следующий вопрос должен быть другим"
            assert q2['block_id'] == q1['block_id'], "Должен быть тот же блок"

            print(f"\n✅ Последовательность вопросов:")
            print(f"  1. {q1['text'][:50]}...")
            print(f"  2. {q2['text'][:50]}...")
        else:
            print(f"\n✅ В блоке только 1 вопрос")

    @pytest.mark.asyncio
    async def test_block_transition(self, router, db_pool):
        """Тест перехода между блоками."""
        # Используем уникальный user_id для этого теста
        test_user = TEST_USER_ID + 1

        try:
            programs = await router.get_available_programs(test_user)
            program_id = programs[0]['program_id']

            # Получаем первый вопрос (создаёт прогресс с current_block_id)
            q1 = await router.get_first_question_in_program(test_user, program_id)

            # Переходим к следующему блоку
            next_block = await router.get_next_block(test_user, program_id)

            assert next_block is not None, "Должен быть следующий блок"
            assert next_block['sequence'] > 1, "Следующий блок должен иметь sequence > 1"

            print(f"\n✅ Переход к следующему блоку:")
            print(f"  - Блок: {next_block['name']} ({next_block['type']})")
            print(f"  - Вопросов: {next_block['questions_count']}")

        finally:
            # Очистка
            async with db_pool.acquire() as conn:
                await conn.execute("""
                    DELETE FROM selfology.user_program_progress WHERE user_id = $1
                """, test_user)


class TestDatabaseIntegrity:
    """Тесты целостности данных в БД."""

    @pytest.mark.asyncio
    async def test_programs_count(self, db_pool):
        """Проверка количества программ."""
        async with db_pool.acquire() as conn:
            count = await conn.fetchval(
                "SELECT COUNT(*) FROM selfology.onboarding_programs"
            )
            assert count == 29, f"Ожидается 29 программ, найдено {count}"
            print(f"\n✅ Программ в БД: {count}")

    @pytest.mark.asyncio
    async def test_blocks_count(self, db_pool):
        """Проверка количества блоков."""
        async with db_pool.acquire() as conn:
            count = await conn.fetchval(
                "SELECT COUNT(*) FROM selfology.program_blocks"
            )
            assert count == 190, f"Ожидается 190 блоков, найдено {count}"
            print(f"\n✅ Блоков в БД: {count}")

    @pytest.mark.asyncio
    async def test_questions_count(self, db_pool):
        """Проверка количества вопросов."""
        async with db_pool.acquire() as conn:
            count = await conn.fetchval(
                "SELECT COUNT(*) FROM selfology.program_questions"
            )
            assert count == 674, f"Ожидается 674 вопроса, найдено {count}"
            print(f"\n✅ Вопросов в БД: {count}")

    @pytest.mark.asyncio
    async def test_block_types_distribution(self, db_pool):
        """Проверка распределения типов блоков."""
        async with db_pool.acquire() as conn:
            types = await conn.fetch("""
                SELECT block_type, COUNT(*) as cnt
                FROM selfology.program_blocks
                GROUP BY block_type
                ORDER BY block_type
            """)

            type_counts = {r['block_type']: r['cnt'] for r in types}

            assert type_counts.get('Foundation', 0) == 32, "Должно быть 32 Foundation блока"
            assert type_counts.get('Exploration', 0) == 120, "Должно быть 120 Exploration блоков"
            assert type_counts.get('Integration', 0) == 38, "Должно быть 38 Integration блоков"

            print(f"\n✅ Типы блоков:")
            for bt, cnt in type_counts.items():
                print(f"  - {bt}: {cnt}")

    @pytest.mark.asyncio
    async def test_question_metadata(self, db_pool):
        """Проверка метаданных вопросов."""
        async with db_pool.acquire() as conn:
            # Проверяем что у всех вопросов есть метаданные
            nulls = await conn.fetchval("""
                SELECT COUNT(*) FROM selfology.program_questions
                WHERE depth_level IS NULL OR domain IS NULL
            """)

            assert nulls == 0, f"Найдено {nulls} вопросов без метаданных"

            # Проверяем распределение моделей
            models = await conn.fetch("""
                SELECT recommended_model, COUNT(*) as cnt
                FROM selfology.program_questions
                GROUP BY recommended_model
                ORDER BY cnt DESC
            """)

            print(f"\n✅ Рекомендуемые модели:")
            for m in models:
                print(f"  - {m['recommended_model']}: {m['cnt']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
