"""create event_outbox table for outbox pattern

Revision ID: 002
Revises: 001
Create Date: 2025-09-30 00:15:00

Создает таблицу event_outbox для Outbox Pattern.

Outbox Pattern решает проблему атомарности операций "сохранить в БД + опубликовать событие"
без использования двухфазных коммитов (2PC).

Архитектура:
1. Бизнес-логика сохраняет данные + событие в одной транзакции
2. Фоновый worker (OutboxRelay) читает pending события и публикует в Event Bus
3. События гарантированно публикуются даже при сбоях
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create event_outbox table"""

    # Создаем таблицу в схеме selfology
    op.create_table(
        'event_outbox',
        sa.Column('id', sa.BigInteger(), nullable=False, autoincrement=True),
        sa.Column('event_type', sa.String(100), nullable=False, comment='Тип события (user.created, profile.updated)'),
        sa.Column('payload', postgresql.JSONB(astext_type=sa.Text()), nullable=False, comment='Данные события в JSON'),
        sa.Column('status', sa.String(20), nullable=False, default='pending', comment='Статус: pending, published, failed'),
        sa.Column('retry_count', sa.Integer(), nullable=False, default=0, comment='Количество попыток публикации'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()'), comment='Время создания'),
        sa.Column('published_at', sa.DateTime(), nullable=True, comment='Время успешной публикации'),
        sa.Column('last_error', sa.Text(), nullable=True, comment='Последняя ошибка (для DLQ)'),
        sa.Column('trace_id', sa.String(100), nullable=True, comment='Trace ID для distributed tracing'),

        sa.PrimaryKeyConstraint('id', name='event_outbox_pkey'),

        schema='selfology',
        comment='Outbox Pattern: события ожидающие публикации в Event Bus'
    )

    # Индекс для быстрого поиска pending событий
    op.create_index(
        'idx_event_outbox_status_created',
        'event_outbox',
        ['status', 'created_at'],
        unique=False,
        schema='selfology'
    )

    # Индекс для поиска событий по типу
    op.create_index(
        'idx_event_outbox_event_type',
        'event_outbox',
        ['event_type'],
        unique=False,
        schema='selfology'
    )

    # Индекс для distributed tracing
    op.create_index(
        'idx_event_outbox_trace_id',
        'event_outbox',
        ['trace_id'],
        unique=False,
        schema='selfology',
        postgresql_where=sa.text("trace_id IS NOT NULL")
    )

    # Constraint на status (только валидные значения)
    op.create_check_constraint(
        'event_outbox_status_check',
        'event_outbox',
        sa.text("status IN ('pending', 'published', 'failed')"),
        schema='selfology'
    )

    print("✅ Таблица selfology.event_outbox создана")
    print("✅ Индексы для outbox созданы")
    print("✅ Outbox Pattern готов к использованию")


def downgrade() -> None:
    """Drop event_outbox table"""

    # Удаляем индексы
    op.drop_index('idx_event_outbox_trace_id', table_name='event_outbox', schema='selfology')
    op.drop_index('idx_event_outbox_event_type', table_name='event_outbox', schema='selfology')
    op.drop_index('idx_event_outbox_status_created', table_name='event_outbox', schema='selfology')

    # Удаляем constraint
    op.drop_constraint('event_outbox_status_check', 'event_outbox', schema='selfology', type_='check')

    # Удаляем таблицу
    op.drop_table('event_outbox', schema='selfology')

    print("❌ Таблица selfology.event_outbox удалена")
