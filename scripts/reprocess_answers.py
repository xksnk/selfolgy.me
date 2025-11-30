#!/usr/bin/env python3
"""
Скрипт для повторной обработки ответов через AnalysisPipeline.

Используется когда ответы были сохранены, но AI анализ не был выполнен.

Запуск:
    python scripts/reprocess_answers.py
"""

import asyncio
import logging
import os
import sys
from datetime import datetime

# Добавляем корневую директорию проекта в PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

import asyncpg

from selfology_bot.services.onboarding.cluster_router import ClusterRouter
from selfology_bot.services.onboarding.analysis_pipeline import AnalysisPipeline

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def get_answers_to_process(pool: asyncpg.Pool) -> list:
    """Получить все ответы из user_answers_v2"""
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT id, user_id, cluster_id, question_id, answer_text, answered_at
            FROM selfology.user_answers_v2
            ORDER BY answered_at ASC
        """)
        return [dict(row) for row in rows]


async def main():
    """Главная функция"""

    logger.info("=" * 60)
    logger.info("🔄 ЗАПУСК ПОВТОРНОЙ ОБРАБОТКИ ОТВЕТОВ")
    logger.info("=" * 60)

    # Подключение к БД
    db_config = {
        "host": os.getenv("DB_HOST", "localhost"),
        "port": int(os.getenv("DB_PORT", 5434)),
        "user": os.getenv("DB_USER", "selfology_user"),
        "password": os.getenv("DB_PASSWORD", "selfology_secure_2024"),
        "database": os.getenv("DB_NAME", "selfology"),
    }

    logger.info(f"📦 Подключение к БД: {db_config['host']}:{db_config['port']}")

    pool = await asyncpg.create_pool(
        **db_config,
        server_settings={'search_path': 'selfology'},
        min_size=2,
        max_size=5
    )

    try:
        # Загружаем ответы
        answers = await get_answers_to_process(pool)
        logger.info(f"📊 Найдено {len(answers)} ответов для обработки")

        if not answers:
            logger.info("✅ Нет ответов для обработки")
            return

        # Инициализируем компоненты
        cluster_router = ClusterRouter()
        pipeline = AnalysisPipeline(pool)
        await pipeline.initialize()

        logger.info("✅ ClusterRouter и AnalysisPipeline инициализированы")

        # Группируем ответы по пользователям для формирования истории
        users_history = {}

        # Обрабатываем каждый ответ
        total = len(answers)
        success = 0
        failed = 0

        for idx, answer in enumerate(answers, 1):
            user_id = answer["user_id"]
            question_id = answer["question_id"]
            answer_text = answer["answer_text"]
            cluster_id = answer["cluster_id"]

            logger.info(f"\n[{idx}/{total}] Обработка ответа #{answer['id']}")
            logger.info(f"  User: {user_id}, Cluster: {cluster_id}, Question: {question_id}")

            try:
                # Получаем данные вопроса из ClusterRouter
                question_data = cluster_router.get_question(question_id)

                if not question_data:
                    logger.warning(f"  ⚠️ Вопрос {question_id} не найден в ClusterRouter")
                    # Создаем минимальные данные вопроса
                    question_data = {
                        "id": question_id,
                        "text": f"Вопрос {question_id}",
                        "block_metadata": {}
                    }

                # Формируем историю ответов пользователя
                if user_id not in users_history:
                    users_history[user_id] = []

                answer_history = users_history[user_id].copy()

                # Запускаем анализ
                result = await pipeline.process_answer(
                    user_id=user_id,
                    question_data=question_data,
                    answer_text=answer_text,
                    answer_history=answer_history
                )

                if result.success:
                    success += 1
                    logger.info(f"  ✅ Успешно (personality: {'✅' if result.personality_updated else '❌'}, vectors: {'✅' if result.vectors_created else '❌'})")

                    # Добавляем в историю
                    users_history[user_id].append({
                        "question_id": question_id,
                        "answer_text": answer_text[:100],
                        "timestamp": answer["answered_at"].isoformat() if answer["answered_at"] else None
                    })
                else:
                    failed += 1
                    logger.error(f"  ❌ Ошибка: {result.error}")

                # Небольшая задержка чтобы не перегружать API
                await asyncio.sleep(0.5)

            except Exception as e:
                failed += 1
                logger.error(f"  ❌ Исключение: {e}")

        # Итоги
        logger.info("\n" + "=" * 60)
        logger.info("📊 ИТОГИ ОБРАБОТКИ")
        logger.info("=" * 60)
        logger.info(f"  Всего ответов: {total}")
        logger.info(f"  Успешно: {success}")
        logger.info(f"  С ошибками: {failed}")
        logger.info(f"  Процент успеха: {success/total*100:.1f}%")

    finally:
        await pool.close()
        logger.info("\n✅ Пул БД закрыт")


if __name__ == "__main__":
    asyncio.run(main())
