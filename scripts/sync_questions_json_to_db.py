"""
Sync Questions from JSON to PostgreSQL

Загружает вопросы из enhanced_questions.json в таблицу selfology.questions
Используется после миграции 011_add_questions_table.sql

Usage:
    python scripts/sync_questions_json_to_db.py --validate  # Dry run с проверкой
    python scripts/sync_questions_json_to_db.py --execute   # Реальная загрузка
    python scripts/sync_questions_json_to_db.py --update    # Обновить существующие
"""

import asyncio
import json
import logging
import asyncpg
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime
import argparse

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class QuestionSyncService:
    """Сервис синхронизации вопросов из JSON в PostgreSQL"""

    def __init__(self, db_config: Dict[str, str]):
        self.db_config = db_config
        self.pool = None

        # Путь к JSON файлу
        self.json_path = Path(__file__).parent.parent / "intelligent_question_core" / "data" / "enhanced_questions.json"

        # Статистика
        self.stats = {
            "total_questions": 0,
            "inserted": 0,
            "updated": 0,
            "skipped": 0,
            "errors": 0
        }

    async def connect(self):
        """Создать connection pool"""
        self.pool = await asyncpg.create_pool(
            host=self.db_config['host'],
            port=self.db_config['port'],
            user=self.db_config['user'],
            password=self.db_config['password'],
            database=self.db_config['database']
        )
        logger.info("✅ Connected to PostgreSQL")

    async def close(self):
        """Закрыть connection pool"""
        if self.pool:
            await self.pool.close()
            logger.info("Connection pool closed")

    def load_questions_from_json(self) -> List[Dict[str, Any]]:
        """Загрузить вопросы из JSON файла"""

        logger.info(f"Loading questions from: {self.json_path}")

        if not self.json_path.exists():
            raise FileNotFoundError(f"JSON file not found: {self.json_path}")

        with open(self.json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        questions = data.get('questions', [])
        logger.info(f"✅ Loaded {len(questions)} questions from JSON")

        self.stats['total_questions'] = len(questions)
        return questions

    def transform_question_to_db_format(self, question: Dict[str, Any]) -> Dict[str, Any]:
        """
        Трансформировать вопрос из JSON формата в формат для БД

        JSON структура:
        {
            "id": "q_001",
            "text": "...",
            "classification": { "journey_stage", "depth_level", "domain", "energy_dynamic" },
            "psychology": { "complexity", "emotional_weight", ... },
            "processing_hints": { ... },
            "connections": [...],
            "original_metadata": {...}
        }
        """

        classification = question.get('classification', {})
        psychology = question.get('psychology', {})
        processing_hints = question.get('processing_hints', {})

        return {
            'question_id': question['id'],
            'text': question['text'],
            'source_system': question.get('source_system', 'onboarding_v7'),

            # Classification
            'journey_stage': classification.get('journey_stage', 'EXPLORING'),
            'depth_level': classification.get('depth_level', 'CONSCIOUS'),
            'domain': classification.get('domain', 'IDENTITY'),
            'energy_dynamic': classification.get('energy_dynamic', 'NEUTRAL'),

            # Psychology (numbers)
            'complexity': psychology.get('complexity', 3),
            'emotional_weight': psychology.get('emotional_weight', 3),
            'insight_potential': psychology.get('insight_potential', 3),
            'safety_level': psychology.get('safety_level', 3),
            'trust_requirement': psychology.get('trust_requirement', 3),

            # JSONB fields
            'processing_hints': json.dumps(processing_hints),
            'metadata': json.dumps(question.get('original_metadata', {})),

            # Connections (array)
            'connections': question.get('connections', []),

            # Active by default
            'is_active': True
        }

    async def validate_data(self, questions: List[Dict[str, Any]]) -> bool:
        """Валидация данных перед загрузкой"""

        logger.info("🔍 Validating questions data...")

        errors = []

        # Проверка уникальности IDs
        question_ids = [q['id'] for q in questions]
        if len(question_ids) != len(set(question_ids)):
            errors.append("Duplicate question IDs found")

        # Проверка обязательных полей
        required_fields = ['id', 'text', 'classification', 'psychology']
        for i, question in enumerate(questions):
            for field in required_fields:
                if field not in question:
                    errors.append(f"Question {i}: missing field '{field}'")

        # Проверка валидности значений
        for i, question in enumerate(questions):
            psychology = question.get('psychology', {})
            for metric in ['complexity', 'emotional_weight', 'safety_level']:
                value = psychology.get(metric)
                if value is not None and (value < 1 or value > 5):
                    errors.append(f"Question {i} ({question['id']}): {metric} out of range (1-5): {value}")

        if errors:
            logger.error(f"❌ Validation failed with {len(errors)} errors:")
            for error in errors[:10]:  # Show first 10 errors
                logger.error(f"  - {error}")
            return False

        logger.info("✅ Validation passed")
        return True

    async def insert_question(self, conn: asyncpg.Connection, question_data: Dict[str, Any]) -> bool:
        """Вставить один вопрос в БД"""

        try:
            await conn.execute("""
                INSERT INTO selfology.questions (
                    question_id, text, source_system,
                    journey_stage, depth_level, domain, energy_dynamic,
                    complexity, emotional_weight, insight_potential, safety_level, trust_requirement,
                    processing_hints, metadata, connections, is_active
                ) VALUES (
                    $1, $2, $3,
                    $4, $5, $6, $7,
                    $8, $9, $10, $11, $12,
                    $13::jsonb, $14::jsonb, $15, $16
                )
                ON CONFLICT (question_id) DO NOTHING
            """,
                question_data['question_id'],
                question_data['text'],
                question_data['source_system'],
                question_data['journey_stage'],
                question_data['depth_level'],
                question_data['domain'],
                question_data['energy_dynamic'],
                question_data['complexity'],
                question_data['emotional_weight'],
                question_data['insight_potential'],
                question_data['safety_level'],
                question_data['trust_requirement'],
                question_data['processing_hints'],
                question_data['metadata'],
                question_data['connections'],
                question_data['is_active']
            )

            self.stats['inserted'] += 1
            return True

        except Exception as e:
            logger.error(f"❌ Error inserting question {question_data['question_id']}: {e}")
            self.stats['errors'] += 1
            return False

    async def update_question(self, conn: asyncpg.Connection, question_data: Dict[str, Any]) -> bool:
        """Обновить существующий вопрос"""

        try:
            result = await conn.execute("""
                UPDATE selfology.questions
                SET
                    text = $2,
                    source_system = $3,
                    journey_stage = $4,
                    depth_level = $5,
                    domain = $6,
                    energy_dynamic = $7,
                    complexity = $8,
                    emotional_weight = $9,
                    insight_potential = $10,
                    safety_level = $11,
                    trust_requirement = $12,
                    processing_hints = $13::jsonb,
                    metadata = $14::jsonb,
                    connections = $15,
                    updated_at = NOW()
                WHERE question_id = $1
            """,
                question_data['question_id'],
                question_data['text'],
                question_data['source_system'],
                question_data['journey_stage'],
                question_data['depth_level'],
                question_data['domain'],
                question_data['energy_dynamic'],
                question_data['complexity'],
                question_data['emotional_weight'],
                question_data['insight_potential'],
                question_data['safety_level'],
                question_data['trust_requirement'],
                question_data['processing_hints'],
                question_data['metadata'],
                question_data['connections']
            )

            if result == "UPDATE 1":
                self.stats['updated'] += 1
                return True
            else:
                self.stats['skipped'] += 1
                return False

        except Exception as e:
            logger.error(f"❌ Error updating question {question_data['question_id']}: {e}")
            self.stats['errors'] += 1
            return False

    async def sync_all_questions(self, mode: str = 'insert'):
        """
        Синхронизировать все вопросы

        Args:
            mode: 'insert' (только новые) или 'update' (обновить существующие)
        """

        # Загрузить вопросы из JSON
        questions = self.load_questions_from_json()

        # Валидация
        if not await self.validate_data(questions):
            raise ValueError("Validation failed")

        # Трансформация
        logger.info("🔄 Transforming questions to DB format...")
        db_questions = [self.transform_question_to_db_format(q) for q in questions]

        # Синхронизация
        logger.info(f"📥 Syncing {len(db_questions)} questions to PostgreSQL (mode: {mode})...")

        async with self.pool.acquire() as conn:
            async with conn.transaction():
                for i, question_data in enumerate(db_questions):
                    if i % 100 == 0:
                        logger.info(f"Progress: {i}/{len(db_questions)}")

                    if mode == 'insert':
                        await self.insert_question(conn, question_data)
                    elif mode == 'update':
                        await self.update_question(conn, question_data)

        # Статистика
        logger.info("✅ Sync completed!")
        logger.info(f"📊 Statistics:")
        logger.info(f"  Total questions: {self.stats['total_questions']}")
        logger.info(f"  Inserted: {self.stats['inserted']}")
        logger.info(f"  Updated: {self.stats['updated']}")
        logger.info(f"  Skipped: {self.stats['skipped']}")
        logger.info(f"  Errors: {self.stats['errors']}")

    async def verify_sync(self):
        """Проверить результаты синхронизации"""

        logger.info("🔍 Verifying sync results...")

        async with self.pool.acquire() as conn:
            # Проверка количества
            count = await conn.fetchval("SELECT COUNT(*) FROM selfology.questions WHERE is_active = true")
            logger.info(f"✅ Total active questions in DB: {count}")

            # Проверка по доменам
            domain_counts = await conn.fetch("""
                SELECT domain, COUNT(*) as count
                FROM selfology.questions
                WHERE is_active = true
                GROUP BY domain
                ORDER BY count DESC
            """)

            logger.info("📊 Questions by domain:")
            for row in domain_counts:
                logger.info(f"  {row['domain']}: {row['count']}")

            # Проверка по depth_level
            depth_counts = await conn.fetch("""
                SELECT depth_level, COUNT(*) as count
                FROM selfology.questions
                WHERE is_active = true
                GROUP BY depth_level
                ORDER BY count DESC
            """)

            logger.info("📊 Questions by depth level:")
            for row in depth_counts:
                logger.info(f"  {row['depth_level']}: {row['count']}")

            # Проверка по energy_dynamic
            energy_counts = await conn.fetch("""
                SELECT energy_dynamic, COUNT(*) as count
                FROM selfology.questions
                WHERE is_active = true
                GROUP BY energy_dynamic
                ORDER BY count DESC
            """)

            logger.info("📊 Questions by energy dynamic:")
            for row in energy_counts:
                logger.info(f"  {row['energy_dynamic']}: {row['count']}")

        logger.info("✅ Verification completed")


async def main():
    """Main entry point"""

    parser = argparse.ArgumentParser(description='Sync questions from JSON to PostgreSQL')
    parser.add_argument('--validate', action='store_true', help='Validate data without inserting')
    parser.add_argument('--execute', action='store_true', help='Execute sync (insert new questions)')
    parser.add_argument('--update', action='store_true', help='Update existing questions')
    parser.add_argument('--verify', action='store_true', help='Verify sync results')

    args = parser.parse_args()

    # Database config
    db_config = {
        'host': 'localhost',
        'port': 5432,
        'user': 'postgres',
        'password': 'sS67wM+1zMBRFHAW4kj9HwFl5J6+veo7Nirx0/I+oiU=',
        'database': 'n8n'
    }

    sync_service = QuestionSyncService(db_config)

    try:
        await sync_service.connect()

        if args.validate:
            logger.info("🔍 VALIDATION MODE - no data will be modified")
            questions = sync_service.load_questions_from_json()
            await sync_service.validate_data(questions)

        elif args.execute:
            logger.info("📥 EXECUTE MODE - inserting new questions")
            await sync_service.sync_all_questions(mode='insert')
            await sync_service.verify_sync()

        elif args.update:
            logger.info("🔄 UPDATE MODE - updating existing questions")
            await sync_service.sync_all_questions(mode='update')
            await sync_service.verify_sync()

        elif args.verify:
            logger.info("🔍 VERIFY MODE - checking database state")
            await sync_service.verify_sync()

        else:
            logger.error("❌ Please specify mode: --validate, --execute, --update, or --verify")
            parser.print_help()

    except Exception as e:
        logger.error(f"❌ Error: {e}")
        raise

    finally:
        await sync_service.close()


if __name__ == "__main__":
    asyncio.run(main())
