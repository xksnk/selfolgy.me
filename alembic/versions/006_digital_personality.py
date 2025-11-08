"""Create digital_personality table

Revision ID: 006
Revises: 005
Create Date: 2025-10-01

Многослойная структура цифровой личности для точного описания пользователя
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers
revision = '006'
down_revision = '005'
branch_labels = None
depends_on = None


def upgrade():
    """
    Создаём таблицу для хранения детальной цифровой личности
    """

    op.execute("""
        CREATE TABLE IF NOT EXISTS selfology.digital_personality (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL UNIQUE,

            -- Слой 1: Идентичность
            identity JSONB DEFAULT '{}'::jsonb,

            -- Слой 2: Интересы и увлечения
            interests JSONB DEFAULT '{}'::jsonb,

            -- Слой 3: Цели и желания
            goals JSONB DEFAULT '{}'::jsonb,

            -- Слой 4: Барьеры и страхи
            barriers JSONB DEFAULT '{}'::jsonb,

            -- Слой 5: Отношения
            relationships JSONB DEFAULT '{}'::jsonb,

            -- Слой 6: Ценности
            values JSONB DEFAULT '{}'::jsonb,

            -- Слой 7: Текущее состояние
            current_state JSONB DEFAULT '{}'::jsonb,

            -- Слой 8: Навыки и способности
            skills JSONB DEFAULT '{}'::jsonb,

            -- Слой 9: Жизненный опыт
            experiences JSONB DEFAULT '{}'::jsonb,

            -- Слой 10: Здоровье и самочувствие
            health JSONB DEFAULT '{}'::jsonb,

            -- Метаданные
            total_answers_analyzed INTEGER DEFAULT 0,
            last_updated TIMESTAMP DEFAULT NOW(),
            personality_version VARCHAR(10) DEFAULT '1.0',
            completeness_score FLOAT DEFAULT 0.0,

            -- Индексы для быстрого поиска по содержимому
            CONSTRAINT fk_user FOREIGN KEY (user_id)
                REFERENCES selfology.onboarding_sessions(user_id)
                ON DELETE CASCADE
        );

        -- Индексы для быстрого поиска
        CREATE INDEX idx_digital_personality_user ON selfology.digital_personality(user_id);
        CREATE INDEX idx_digital_personality_updated ON selfology.digital_personality(last_updated);

        -- GIN индексы для JSONB полей (быстрый поиск по содержимому)
        CREATE INDEX idx_digital_personality_interests ON selfology.digital_personality USING GIN (interests);
        CREATE INDEX idx_digital_personality_goals ON selfology.digital_personality USING GIN (goals);
        CREATE INDEX idx_digital_personality_skills ON selfology.digital_personality USING GIN (skills);

        COMMENT ON TABLE selfology.digital_personality IS 'Многослойная цифровая личность пользователя с детальным извлечением информации из ответов';
        COMMENT ON COLUMN selfology.digital_personality.identity IS 'WHO AM I - самовосприятие, идентичность, характер';
        COMMENT ON COLUMN selfology.digital_personality.interests IS 'WHAT I LOVE - увлечения, хобби, интересы';
        COMMENT ON COLUMN selfology.digital_personality.goals IS 'WHAT I WANT - цели, желания, амбиции';
        COMMENT ON COLUMN selfology.digital_personality.barriers IS 'WHAT HOLDS ME BACK - страхи, барьеры, ограничения';
        COMMENT ON COLUMN selfology.digital_personality.relationships IS 'WHO MATTERS - важные люди, отношения';
        COMMENT ON COLUMN selfology.digital_personality.values IS 'WHAT I VALUE - ценности, принципы';
        COMMENT ON COLUMN selfology.digital_personality.current_state IS 'WHERE I AM NOW - текущее состояние, активности';
        COMMENT ON COLUMN selfology.digital_personality.skills IS 'WHAT I CAN DO - навыки, умения, способности';
        COMMENT ON COLUMN selfology.digital_personality.experiences IS 'WHAT I\'VE BEEN THROUGH - опыт, события';
        COMMENT ON COLUMN selfology.digital_personality.health IS 'HOW I FEEL - физическое и ментальное здоровье';
    """)


def downgrade():
    """Remove digital_personality table"""
    op.execute("DROP TABLE IF EXISTS selfology.digital_personality CASCADE;")
