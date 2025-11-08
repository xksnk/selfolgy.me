"""Create Soul Architect tables

Revision ID: 001_soul_architect
Revises:
Create Date: 2025-09-30

Creates tables for Soul-Architect system:
- personality_profiles - хранение многослойных профилей личности
- trait_history - история изменений черт
- unique_signatures - уникальные подписи личности
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic
revision = '001_soul_architect'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create Soul Architect tables in selfology schema"""

    # Создаем схему selfology если не существует
    op.execute("CREATE SCHEMA IF NOT EXISTS selfology")

    # 1. Таблица personality_profiles
    op.create_table(
        'personality_profiles',
        sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('user_id', sa.BigInteger(), nullable=False, unique=True, index=True),
        sa.Column('profile_data', postgresql.JSONB(), nullable=False, comment='Многослойный профиль личности'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id'),
        schema='selfology',
        comment='Многослойные профили личности (Soul-Architect)'
    )

    # Индексы для personality_profiles
    op.create_index(
        'ix_personality_profiles_user_id',
        'personality_profiles',
        ['user_id'],
        unique=True,
        schema='selfology'
    )
    op.create_index(
        'ix_personality_profiles_updated_at',
        'personality_profiles',
        ['updated_at'],
        schema='selfology'
    )

    # 2. Таблица trait_history
    op.create_table(
        'trait_history',
        sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('user_id', sa.BigInteger(), nullable=False, index=True),
        sa.Column('trait_category', sa.String(50), nullable=False, comment='big_five, core_dynamics, adaptive_traits, domain_affinities'),
        sa.Column('trait_name', sa.String(50), nullable=False),
        sa.Column('old_value', sa.Float(), nullable=True, comment='Старое значение (NULL для первого значения)'),
        sa.Column('new_value', sa.Float(), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False, comment='Уверенность в новом значении'),
        sa.Column('trigger', sa.String(100), nullable=True, comment='Что вызвало изменение'),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.PrimaryKeyConstraint('id'),
        schema='selfology',
        comment='История изменений психологических черт'
    )

    # Индексы для trait_history
    op.create_index(
        'ix_trait_history_user_id',
        'trait_history',
        ['user_id'],
        schema='selfology'
    )
    op.create_index(
        'ix_trait_history_timestamp',
        'trait_history',
        ['timestamp'],
        schema='selfology'
    )
    op.create_index(
        'ix_trait_history_user_trait',
        'trait_history',
        ['user_id', 'trait_category', 'trait_name'],
        schema='selfology'
    )

    # 3. Таблица unique_signatures
    op.create_table(
        'unique_signatures',
        sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('user_id', sa.BigInteger(), nullable=False, unique=True, index=True),
        sa.Column('thinking_style', sa.String(100), nullable=True, comment='Стиль мышления'),
        sa.Column('decision_pattern', sa.String(100), nullable=True, comment='Паттерн принятия решений'),
        sa.Column('energy_rhythm', sa.String(100), nullable=True, comment='Ритм энергии'),
        sa.Column('learning_edge', sa.String(100), nullable=True, comment='Граница обучения'),
        sa.Column('love_language', sa.String(100), nullable=True, comment='Язык любви'),
        sa.Column('stress_response', sa.String(100), nullable=True, comment='Реакция на стресс'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id'),
        schema='selfology',
        comment='Уникальные подписи личности'
    )

    # Индексы для unique_signatures
    op.create_index(
        'ix_unique_signatures_user_id',
        'unique_signatures',
        ['user_id'],
        unique=True,
        schema='selfology'
    )

    print("✅ Soul Architect tables created successfully in selfology schema")


def downgrade() -> None:
    """Drop Soul Architect tables"""

    # Удаляем таблицы в обратном порядке
    op.drop_table('unique_signatures', schema='selfology')
    op.drop_table('trait_history', schema='selfology')
    op.drop_table('personality_profiles', schema='selfology')

    print("❌ Soul Architect tables dropped")
