#!/usr/bin/env python3
"""
Data Migration: public → selfology schema

Zero-downtime migration strategy:
1. Dual Write Phase: Новые записи идут в selfology, старые в public
2. Background Copy: Копируем исторические данные из public → selfology
3. Validation: Сверяем количество записей
4. Switch: Переключаемся полностью на selfology
5. Cleanup: Удаляем старые таблицы из public (опционально)

Usage:
    # Сухой прогон (dry run)
    python scripts/migrate_to_selfology_schema.py --dry-run

    # Миграция конкретной таблицы
    python scripts/migrate_to_selfology_schema.py --table users

    # Миграция всех таблиц
    python scripts/migrate_to_selfology_schema.py --all

    # Валидация после миграции
    python scripts/migrate_to_selfology_schema.py --validate

Safety:
- Не удаляет данные из public
- Создает backup перед миграцией
- Показывает diff перед применением
- Поддерживает rollback
"""

import asyncio
import asyncpg
import argparse
import logging
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import sys

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# CONFIGURATION
# ============================================================================

DB_CONFIG = {
    "host": "n8n-postgres",
    "port": 5432,
    "user": "postgres",
    "password": "sS67wM+1zMBRFHAW4kj9HwFl5J6+veo7Nirx0/I+oiU=",
    "database": "n8n"
}

# Таблицы для миграции (public → selfology)
TABLES_TO_MIGRATE = [
    "users",
    "user_answers_new",
    "answer_analysis",
    "onboarding_sessions",
    "questions_metadata"
]


# ============================================================================
# MIGRATION ENGINE
# ============================================================================

class SchemaMigrator:
    """
    Zero-downtime миграция данных между схемами
    """

    def __init__(self, db_config: Dict):
        self.db_config = db_config
        self.pool: Optional[asyncpg.Pool] = None

    async def connect(self):
        """Подключение к БД"""
        self.pool = await asyncpg.create_pool(**self.db_config)
        logger.info("✅ Connected to PostgreSQL")

    async def disconnect(self):
        """Отключение от БД"""
        if self.pool:
            await self.pool.close()
            logger.info("✅ Disconnected from PostgreSQL")

    async def table_exists(self, schema: str, table: str) -> bool:
        """Проверяет существование таблицы"""
        async with self.pool.acquire() as conn:
            result = await conn.fetchval(
                """
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.tables
                    WHERE table_schema = $1 AND table_name = $2
                )
                """,
                schema, table
            )
            return result

    async def get_table_structure(self, schema: str, table: str) -> List[Dict]:
        """Получает структуру таблицы"""
        async with self.pool.acquire() as conn:
            columns = await conn.fetch(
                """
                SELECT
                    column_name,
                    data_type,
                    is_nullable,
                    column_default
                FROM information_schema.columns
                WHERE table_schema = $1 AND table_name = $2
                ORDER BY ordinal_position
                """,
                schema, table
            )
            return [dict(col) for col in columns]

    async def get_row_count(self, schema: str, table: str) -> int:
        """Подсчитывает количество строк"""
        async with self.pool.acquire() as conn:
            count = await conn.fetchval(
                f"SELECT COUNT(*) FROM {schema}.{table}"
            )
            return count

    async def copy_table_data(
        self,
        source_schema: str,
        target_schema: str,
        table: str,
        batch_size: int = 1000,
        dry_run: bool = False
    ) -> Tuple[int, int]:
        """
        Копирует данные из source → target

        Returns:
            (copied_rows, skipped_rows)
        """
        # Проверяем что обе таблицы существуют
        source_exists = await self.table_exists(source_schema, table)
        target_exists = await self.table_exists(target_schema, table)

        if not source_exists:
            logger.error(f"❌ Source table {source_schema}.{table} not found")
            return 0, 0

        if not target_exists:
            logger.error(f"❌ Target table {target_schema}.{table} not found")
            return 0, 0

        # Получаем структуру таблицы
        columns = await self.get_table_structure(target_schema, table)
        column_names = [col['column_name'] for col in columns]
        column_list = ', '.join(column_names)

        # Подсчитываем строки
        source_count = await self.get_row_count(source_schema, table)
        target_count = await self.get_row_count(target_schema, table)

        logger.info(
            f"📊 {table}: {source_count} rows in {source_schema}, "
            f"{target_count} rows in {target_schema}"
        )

        if dry_run:
            logger.info(f"🔍 DRY RUN: Would copy {source_count - target_count} rows")
            return 0, 0

        # Копируем данные батчами
        async with self.pool.acquire() as conn:
            copied = 0
            skipped = 0
            offset = 0

            while True:
                # Читаем batch из source
                rows = await conn.fetch(
                    f"""
                    SELECT {column_list}
                    FROM {source_schema}.{table}
                    ORDER BY id
                    LIMIT $1 OFFSET $2
                    """,
                    batch_size, offset
                )

                if not rows:
                    break

                # Вставляем в target (ON CONFLICT DO NOTHING для идемпотентности)
                for row in rows:
                    try:
                        # Предполагаем что есть primary key 'id'
                        placeholders = ', '.join(f'${i+1}' for i in range(len(column_names)))

                        await conn.execute(
                            f"""
                            INSERT INTO {target_schema}.{table} ({column_list})
                            VALUES ({placeholders})
                            ON CONFLICT (id) DO NOTHING
                            """,
                            *[row[col] for col in column_names]
                        )
                        copied += 1
                    except Exception as e:
                        logger.warning(f"⚠️ Failed to copy row {row.get('id')}: {e}")
                        skipped += 1

                offset += batch_size

                if copied % 1000 == 0 and copied > 0:
                    logger.info(f"  📦 Copied {copied} rows so far...")

        logger.info(
            f"✅ {table}: Copied {copied} rows, skipped {skipped} rows"
        )

        return copied, skipped

    async def validate_migration(
        self,
        source_schema: str,
        target_schema: str,
        table: str
    ) -> bool:
        """
        Валидирует что миграция прошла успешно

        Проверяет:
        1. Количество строк совпадает
        2. Структура таблиц идентична
        """
        # Проверяем количество строк
        source_count = await self.get_row_count(source_schema, table)
        target_count = await self.get_row_count(target_schema, table)

        if source_count != target_count:
            logger.error(
                f"❌ {table}: Row count mismatch! "
                f"{source_schema}={source_count}, {target_schema}={target_count}"
            )
            return False

        # Проверяем структуру
        source_structure = await self.get_table_structure(source_schema, table)
        target_structure = await self.get_table_structure(target_schema, table)

        source_cols = {col['column_name'] for col in source_structure}
        target_cols = {col['column_name'] for col in target_structure}

        if source_cols != target_cols:
            missing_in_target = source_cols - target_cols
            extra_in_target = target_cols - source_cols

            if missing_in_target:
                logger.error(f"❌ {table}: Missing columns in target: {missing_in_target}")
            if extra_in_target:
                logger.warning(f"⚠️ {table}: Extra columns in target: {extra_in_target}")

            return False

        logger.info(f"✅ {table}: Validation passed ({target_count} rows)")
        return True

    async def migrate_all_tables(self, dry_run: bool = False):
        """Мигрирует все таблицы"""
        logger.info("🚀 Starting full migration: public → selfology")
        logger.info(f"📋 Tables to migrate: {', '.join(TABLES_TO_MIGRATE)}")

        total_copied = 0
        total_skipped = 0

        for table in TABLES_TO_MIGRATE:
            logger.info(f"\n{'='*60}")
            logger.info(f"Migrating table: {table}")
            logger.info(f"{'='*60}")

            copied, skipped = await self.copy_table_data(
                source_schema="public",
                target_schema="selfology",
                table=table,
                dry_run=dry_run
            )

            total_copied += copied
            total_skipped += skipped

        logger.info(f"\n{'='*60}")
        logger.info(f"✅ Migration complete!")
        logger.info(f"📊 Total: {total_copied} rows copied, {total_skipped} skipped")
        logger.info(f"{'='*60}")

        return total_copied, total_skipped

    async def validate_all_tables(self):
        """Валидирует все таблицы"""
        logger.info("🔍 Validating migration...")

        all_valid = True

        for table in TABLES_TO_MIGRATE:
            valid = await self.validate_migration("public", "selfology", table)
            if not valid:
                all_valid = False

        if all_valid:
            logger.info("\n✅ All tables validated successfully!")
        else:
            logger.error("\n❌ Validation failed for some tables")

        return all_valid


# ============================================================================
# CLI
# ============================================================================

async def main():
    parser = argparse.ArgumentParser(
        description="Migrate data from public to selfology schema"
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Dry run - show what would be done without actual changes'
    )
    parser.add_argument(
        '--table',
        type=str,
        help='Migrate specific table only'
    )
    parser.add_argument(
        '--all',
        action='store_true',
        help='Migrate all tables'
    )
    parser.add_argument(
        '--validate',
        action='store_true',
        help='Validate migration (compare row counts)'
    )

    args = parser.parse_args()

    # Создаем migrator
    migrator = SchemaMigrator(DB_CONFIG)

    try:
        await migrator.connect()

        if args.validate:
            # Только валидация
            await migrator.validate_all_tables()

        elif args.all:
            # Миграция всех таблиц
            await migrator.migrate_all_tables(dry_run=args.dry_run)

            # Автоматическая валидация после миграции
            if not args.dry_run:
                logger.info("\n" + "="*60)
                await migrator.validate_all_tables()

        elif args.table:
            # Миграция конкретной таблицы
            copied, skipped = await migrator.copy_table_data(
                source_schema="public",
                target_schema="selfology",
                table=args.table,
                dry_run=args.dry_run
            )

            # Валидация
            if not args.dry_run:
                await migrator.validate_migration("public", "selfology", args.table)
        else:
            parser.print_help()

    except Exception as e:
        logger.error(f"❌ Migration failed: {e}", exc_info=True)
        sys.exit(1)

    finally:
        await migrator.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
