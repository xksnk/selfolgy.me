#!/usr/bin/env python3
"""
Обработать все orphaned ответы (без записей в answer_analysis).

Использование:
    python process_orphaned_answers.py [--user USER_ID] [--dry-run]

Примеры:
    python process_orphaned_answers.py                    # Все пользователи
    python process_orphaned_answers.py --user 98005572    # Конкретный пользователь
    python process_orphaned_answers.py --dry-run          # Только показать список
"""

import asyncio
import asyncpg
import sys
import os
import argparse
from datetime import datetime
from typing import List, Dict, Optional
from dotenv import load_dotenv

# Загружаем .env
load_dotenv()

# Добавляем путь к selfology_bot
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from selfology_bot.services.onboarding.orchestrator import OnboardingOrchestrator
from selfology_bot.database.service import DatabaseService
from selfology_bot.database.onboarding_dao import OnboardingDAO
from selfology_bot.database.digital_personality_dao import DigitalPersonalityDAO
from intelligent_question_core.api.core_api import SelfologyQuestionCore
from selfology_bot.core.config import settings


class OrphanedAnswerProcessor:
    """Обработчик orphaned ответов (без AI анализа)"""

    def __init__(self):
        self.db_pool: Optional[asyncpg.Pool] = None
        self.orchestrator: Optional[OnboardingOrchestrator] = None
        self.question_core: Optional[SelfologyQuestionCore] = None
        self.stats = {
            "found": 0,
            "processed": 0,
            "failed": 0,
            "skipped": 0
        }

    async def initialize(self):
        """Инициализация БД и orchestrator"""
        print("🔧 Инициализация системы...")

        # Подключение к БД
        self.db_pool = await asyncpg.create_pool(
            host=os.getenv('DB_HOST', 'localhost'),
            port=int(os.getenv('DB_PORT', 5432)),
            user=os.getenv('DB_USER', 'n8n'),
            password=os.getenv('DB_PASSWORD'),
            database=os.getenv('DB_NAME', 'n8n'),
            min_size=1,
            max_size=5
        )
        print("  ✅ Database pool created")

        # Инициализация Question Core
        self.question_core = SelfologyQuestionCore()
        print("  ✅ Question Core initialized")

        # Инициализация Orchestrator
        self.orchestrator = OnboardingOrchestrator()

        # DatabaseService
        db_service = DatabaseService(
            host=os.getenv('DB_HOST', 'localhost'),
            port=int(os.getenv('DB_PORT', 5432)),
            user=os.getenv('DB_USER', 'n8n'),
            password=os.getenv('DB_PASSWORD'),
            database=os.getenv('DB_NAME', 'n8n')
        )
        await db_service.initialize()
        self.orchestrator.db_service = db_service
        print("  ✅ DatabaseService initialized")

        # DAOs
        self.orchestrator.onboarding_dao = OnboardingDAO(db_service)
        self.orchestrator.personality_dao = DigitalPersonalityDAO(db_service)
        print("  ✅ DAOs initialized")

        print("✅ Система готова к обработке\n")

    async def find_orphaned_answers(self, user_id: Optional[int] = None) -> List[Dict]:
        """Найти все ответы без answer_analysis записей"""

        query = """
            SELECT
                ua.id as answer_id,
                ua.raw_answer,
                ua.question_json_id,
                ua.answered_at,
                os.user_id,
                os.id as session_id
            FROM selfology.user_answers_new ua
            JOIN selfology.onboarding_sessions os ON ua.session_id = os.id
            LEFT JOIN selfology.answer_analysis aa ON aa.user_answer_id = ua.id
            WHERE aa.id IS NULL
        """

        params = []
        if user_id:
            query += " AND os.user_id = $1"
            params.append(user_id)

        query += " ORDER BY ua.id"

        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
            return [dict(row) for row in rows]

    async def process_single_answer(self, answer_data: Dict) -> bool:
        """Обработать один orphaned ответ"""

        answer_id = answer_data['answer_id']
        user_id = answer_data['user_id']
        question_json_id = answer_data['question_json_id']
        raw_answer = answer_data['raw_answer']

        try:
            print(f"  🔄 Processing answer #{answer_id} (user {user_id}, q_{question_json_id})...")

            # Получить метаданные вопроса
            question_data = self.question_core.get_question(question_json_id)
            if not question_data:
                print(f"    ❌ Question {question_json_id} not found in core")
                return False

            # Создать mock сессию для контекста
            mock_session = {
                "user_id": user_id,
                "session_id": answer_data['session_id'],
                "answer_history": [],  # Для orphaned ответов контекст потерян
                "question_history": []
            }

            # Запустить deep analysis pipeline
            await self.orchestrator._deep_analysis_pipeline(
                user_id=user_id,
                question_id=question_json_id,
                answer=raw_answer,
                question_data=question_data,
                session=mock_session,
                answer_id=answer_id
            )

            print(f"    ✅ Successfully processed answer #{answer_id}")
            return True

        except Exception as e:
            print(f"    ❌ Failed to process answer #{answer_id}: {e}")
            import traceback
            traceback.print_exc()
            return False

    async def process_all(self, user_id: Optional[int] = None, dry_run: bool = False):
        """Обработать все orphaned ответы"""

        await self.initialize()

        # Найти orphaned ответы
        print(f"🔍 Поиск orphaned ответов{f' для пользователя {user_id}' if user_id else ''}...")
        orphaned = await self.find_orphaned_answers(user_id)

        self.stats["found"] = len(orphaned)

        if not orphaned:
            print("✅ Orphaned ответов не найдено!")
            return

        print(f"\n📊 Найдено orphaned ответов: {len(orphaned)}")
        print("=" * 60)

        for idx, answer in enumerate(orphaned, 1):
            print(f"\n[{idx}/{len(orphaned)}] Answer #{answer['answer_id']}")
            print(f"  User: {answer['user_id']}")
            print(f"  Question: {answer['question_json_id']}")
            print(f"  Answered: {answer['answered_at']}")
            print(f"  Text: {answer['raw_answer'][:100]}...")

            if dry_run:
                print("  ⏭️  Skipped (dry run)")
                self.stats["skipped"] += 1
                continue

            # Обработать ответ
            success = await self.process_single_answer(answer)

            if success:
                self.stats["processed"] += 1
            else:
                self.stats["failed"] += 1

            # Небольшая пауза между обработкой
            await asyncio.sleep(1)

        # Итоговая статистика
        print("\n" + "=" * 60)
        print("📊 ИТОГОВАЯ СТАТИСТИКА:")
        print(f"  Найдено:     {self.stats['found']}")
        print(f"  Обработано:  {self.stats['processed']}")
        print(f"  Ошибок:      {self.stats['failed']}")
        print(f"  Пропущено:   {self.stats['skipped']}")
        print("=" * 60)

    async def cleanup(self):
        """Очистка ресурсов"""
        if self.db_pool:
            await self.db_pool.close()

        if self.orchestrator and self.orchestrator.db_service:
            await self.orchestrator.db_service.close()


async def main():
    parser = argparse.ArgumentParser(
        description='Обработать orphaned ответы (без AI анализа)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  %(prog)s                      # Все пользователи
  %(prog)s --user 98005572      # Конкретный пользователь
  %(prog)s --dry-run            # Только показать список
  %(prog)s --user 98005572 --dry-run  # Показать список для пользователя
        """
    )

    parser.add_argument(
        '--user',
        type=int,
        help='ID пользователя (опционально, по умолчанию все пользователи)'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Только показать список, не обрабатывать'
    )

    args = parser.parse_args()

    processor = OrphanedAnswerProcessor()

    try:
        await processor.process_all(
            user_id=args.user,
            dry_run=args.dry_run
        )
    except KeyboardInterrupt:
        print("\n⚠️  Прервано пользователем")
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        await processor.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
