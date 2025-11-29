-- ============================================================
-- МИГРАЦИЯ 001: Блочная структура программ Selfology
-- Дата: 2024-11-29
-- Описание: Создание таблиц для 3-уровневой иерархии
--           Программа -> Блок -> Вопрос
-- ============================================================

-- 1. ТАБЛИЦА ПРОГРАММ
-- Хранит 29 программ рефлексии (после аудита методолога)
CREATE TABLE IF NOT EXISTS selfology.onboarding_programs (
    id SERIAL PRIMARY KEY,
    program_id VARCHAR(100) UNIQUE NOT NULL,           -- program_podumat_o_zhizni
    name VARCHAR(200) NOT NULL,                        -- Подумать о жизни
    description TEXT,                                   -- Глубокие вопросы о смысле жизни
    status VARCHAR(20) DEFAULT 'active',               -- active, draft, archived
    priority INTEGER DEFAULT 0,                         -- Порядок показа в каталоге
    estimated_duration_min INTEGER,                     -- Оценка времени прохождения
    therapeutic_approach TEXT[],                        -- ['CBT', 'existential', 'ACT']
    target_audience TEXT,                               -- Для кого программа
    tags TEXT[],                                        -- ['карьера', 'эмоции', 'отношения']
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Индекс для быстрого поиска по статусу и приоритету
CREATE INDEX IF NOT EXISTS idx_programs_status_priority
ON selfology.onboarding_programs(status, priority);

COMMENT ON TABLE selfology.onboarding_programs IS
'29 программ рефлексии Selfology после аудита методолога';


-- 2. ТАБЛИЦА БЛОКОВ ПРОГРАММ
-- Типы: Foundation (вход), Exploration (углубление), Integration (синтез)
CREATE TABLE IF NOT EXISTS selfology.program_blocks (
    id SERIAL PRIMARY KEY,
    block_id VARCHAR(150) UNIQUE NOT NULL,             -- block_podumat_o_zhiznizdes_i_seychas
    program_id VARCHAR(100) NOT NULL
        REFERENCES selfology.onboarding_programs(program_id) ON DELETE CASCADE,
    name VARCHAR(200) NOT NULL,                        -- Здесь и сейчас
    description TEXT,                                   -- ориентация
    block_type VARCHAR(20) NOT NULL,                   -- Foundation, Exploration, Integration
    sequence INTEGER NOT NULL,                          -- Порядок в программе (1, 2, 3...)

    -- Базовые метаданные блока (наследуются вопросами)
    base_journey_stage VARCHAR(20),                    -- ENTRY, EXPLORATION, INTEGRATION
    base_depth_range JSONB,                            -- ["SURFACE", "CONSCIOUS"]
    base_energy_dynamic VARCHAR(20),                   -- OPENING, PROCESSING, HEALING
    base_safety_minimum INTEGER,                        -- Минимальный safety для вопросов
    base_complexity_range JSONB,                       -- [1, 2]
    base_emotional_weight_range JSONB,                 -- [1, 2]

    estimated_duration_min INTEGER,                     -- Оценка времени на блок
    can_skip BOOLEAN DEFAULT false,                    -- Можно ли пропустить блок
    created_at TIMESTAMP DEFAULT NOW()
);

-- Индексы для быстрого поиска блоков
CREATE INDEX IF NOT EXISTS idx_blocks_program ON selfology.program_blocks(program_id);
CREATE INDEX IF NOT EXISTS idx_blocks_type ON selfology.program_blocks(block_type);
CREATE INDEX IF NOT EXISTS idx_blocks_sequence ON selfology.program_blocks(program_id, sequence);

COMMENT ON TABLE selfology.program_blocks IS
'190 блоков программ: Foundation (32), Exploration (120), Integration (38)';


-- 3. ТАБЛИЦА ВОПРОСОВ ПРОГРАММ
-- 674 вопроса с метаданными
CREATE TABLE IF NOT EXISTS selfology.program_questions (
    id SERIAL PRIMARY KEY,
    question_id VARCHAR(150) UNIQUE NOT NULL,          -- q_podumat_o_zhiznib1q1
    block_id VARCHAR(150) NOT NULL
        REFERENCES selfology.program_blocks(block_id) ON DELETE CASCADE,
    program_id VARCHAR(100) NOT NULL
        REFERENCES selfology.onboarding_programs(program_id) ON DELETE CASCADE,
    position INTEGER NOT NULL,                          -- Позиция в программе (сквозная нумерация)
    position_in_block INTEGER,                          -- Позиция внутри блока
    text TEXT NOT NULL,                                 -- Текст вопроса
    format VARCHAR(20) DEFAULT 'both',                 -- book_only, ai_only, both

    -- Финальные метаданные (после наследования от блока)
    journey_stage VARCHAR(20),                         -- ENTRY, EXPLORATION, INTEGRATION
    depth_level VARCHAR(20),                           -- SURFACE, CONSCIOUS, EDGE, SHADOW, CORE
    domain VARCHAR(50),                                -- IDENTITY, RELATIONSHIPS, CAREER, HEALTH...
    energy_dynamic VARCHAR(20),                        -- OPENING, NEUTRAL, PROCESSING, HEAVY, HEALING
    complexity INTEGER CHECK (complexity BETWEEN 1 AND 5),
    emotional_weight INTEGER CHECK (emotional_weight BETWEEN 1 AND 5),
    safety_level INTEGER CHECK (safety_level BETWEEN 1 AND 5),
    trust_requirement INTEGER CHECK (trust_requirement BETWEEN 1 AND 5),
    recommended_model VARCHAR(50),                     -- gpt-4o-mini, gpt-4o, claude-sonnet
    requires_context BOOLEAN DEFAULT false,            -- Требует ли контекста предыдущих ответов

    -- Валидация и ревью
    confidence_score FLOAT,                            -- Уверенность AI в метаданных (0-1)
    needs_human_review BOOLEAN DEFAULT false,          -- Требует проверки психологом
    reviewed_by VARCHAR(100),                          -- Кто проверил
    reviewed_at TIMESTAMP,                             -- Когда проверено
    review_notes TEXT,                                 -- Заметки ревьюера

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Индексы для вопросов
CREATE INDEX IF NOT EXISTS idx_questions_block ON selfology.program_questions(block_id);
CREATE INDEX IF NOT EXISTS idx_questions_program ON selfology.program_questions(program_id);
CREATE INDEX IF NOT EXISTS idx_questions_format ON selfology.program_questions(format);
CREATE INDEX IF NOT EXISTS idx_questions_position ON selfology.program_questions(program_id, position);
CREATE INDEX IF NOT EXISTS idx_questions_depth ON selfology.program_questions(depth_level);
CREATE INDEX IF NOT EXISTS idx_questions_domain ON selfology.program_questions(domain);
CREATE INDEX IF NOT EXISTS idx_questions_needs_review ON selfology.program_questions(needs_human_review)
    WHERE needs_human_review = true;

COMMENT ON TABLE selfology.program_questions IS
'674 вопроса: book_only (323), ai_only (225), both (126)';


-- 4. ТАБЛИЦА ПРОГРЕССА ПОЛЬЗОВАТЕЛЯ ПО ПРОГРАММАМ
CREATE TABLE IF NOT EXISTS selfology.user_program_progress (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,                          -- ID пользователя
    program_id VARCHAR(100) NOT NULL
        REFERENCES selfology.onboarding_programs(program_id),
    session_id INTEGER,                                -- Связь с onboarding_sessions

    -- Текущее состояние
    current_block_id VARCHAR(150),                     -- Текущий блок
    current_question_position INTEGER,                 -- Текущая позиция вопроса

    -- История прохождения
    blocks_completed VARCHAR(150)[],                   -- Завершённые блоки
    blocks_skipped VARCHAR(150)[],                     -- Пропущенные блоки
    questions_answered INTEGER DEFAULT 0,              -- Сколько вопросов отвечено
    questions_skipped INTEGER DEFAULT 0,               -- Сколько вопросов пропущено

    -- Прогресс
    completion_percentage INTEGER DEFAULT 0,           -- Процент прохождения (0-100)
    total_time_spent_sec INTEGER DEFAULT 0,           -- Общее время на программу

    -- Статус
    status VARCHAR(20) DEFAULT 'active',               -- active, completed, paused, abandoned
    pause_reason TEXT,                                 -- Причина паузы

    -- Даты
    started_at TIMESTAMP DEFAULT NOW(),
    last_activity_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,

    -- Уникальность: один активный прогресс на пользователя и программу
    CONSTRAINT unique_active_progress UNIQUE (user_id, program_id, status)
);

-- Индексы для прогресса
CREATE INDEX IF NOT EXISTS idx_progress_user ON selfology.user_program_progress(user_id);
CREATE INDEX IF NOT EXISTS idx_progress_session ON selfology.user_program_progress(session_id);
CREATE INDEX IF NOT EXISTS idx_progress_status ON selfology.user_program_progress(status);
CREATE INDEX IF NOT EXISTS idx_progress_user_active ON selfology.user_program_progress(user_id, status)
    WHERE status = 'active';

COMMENT ON TABLE selfology.user_program_progress IS
'Прогресс пользователей по программам с историей прохождения';


-- 5. ОБНОВЛЕНИЕ СУЩЕСТВУЮЩЕЙ ТАБЛИЦЫ СЕССИЙ
-- Добавляем связь с программами и блоками
DO $$
BEGIN
    -- Добавить current_program_id если не существует
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'selfology'
        AND table_name = 'onboarding_sessions'
        AND column_name = 'current_program_id'
    ) THEN
        ALTER TABLE selfology.onboarding_sessions
        ADD COLUMN current_program_id VARCHAR(100);
    END IF;

    -- Добавить current_block_id если не существует
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'selfology'
        AND table_name = 'onboarding_sessions'
        AND column_name = 'current_block_id'
    ) THEN
        ALTER TABLE selfology.onboarding_sessions
        ADD COLUMN current_block_id VARCHAR(150);
    END IF;

    -- Добавить program_progress_id если не существует
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'selfology'
        AND table_name = 'onboarding_sessions'
        AND column_name = 'program_progress_id'
    ) THEN
        ALTER TABLE selfology.onboarding_sessions
        ADD COLUMN program_progress_id INTEGER;
    END IF;
END $$;

-- Индекс для связи сессий с программами
CREATE INDEX IF NOT EXISTS idx_sessions_program
ON selfology.onboarding_sessions(current_program_id);


-- 6. ФУНКЦИЯ ДЛЯ ОБНОВЛЕНИЯ updated_at
CREATE OR REPLACE FUNCTION selfology.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Триггеры для автоматического обновления updated_at
DROP TRIGGER IF EXISTS update_programs_updated_at ON selfology.onboarding_programs;
CREATE TRIGGER update_programs_updated_at
    BEFORE UPDATE ON selfology.onboarding_programs
    FOR EACH ROW EXECUTE FUNCTION selfology.update_updated_at_column();

DROP TRIGGER IF EXISTS update_questions_updated_at ON selfology.program_questions;
CREATE TRIGGER update_questions_updated_at
    BEFORE UPDATE ON selfology.program_questions
    FOR EACH ROW EXECUTE FUNCTION selfology.update_updated_at_column();


-- 7. ПРЕДСТАВЛЕНИЕ ДЛЯ БЫСТРОГО ДОСТУПА К СТРУКТУРЕ ПРОГРАММ
CREATE OR REPLACE VIEW selfology.v_program_structure AS
SELECT
    p.program_id,
    p.name as program_name,
    p.status as program_status,
    b.block_id,
    b.name as block_name,
    b.block_type,
    b.sequence as block_sequence,
    COUNT(q.id) as questions_count,
    SUM(CASE WHEN q.format = 'book_only' THEN 1 ELSE 0 END) as book_only_count,
    SUM(CASE WHEN q.format = 'ai_only' THEN 1 ELSE 0 END) as ai_only_count,
    SUM(CASE WHEN q.format = 'both' THEN 1 ELSE 0 END) as both_count
FROM selfology.onboarding_programs p
JOIN selfology.program_blocks b ON p.program_id = b.program_id
LEFT JOIN selfology.program_questions q ON b.block_id = q.block_id
GROUP BY p.program_id, p.name, p.status, b.block_id, b.name, b.block_type, b.sequence
ORDER BY p.program_id, b.sequence;

COMMENT ON VIEW selfology.v_program_structure IS
'Представление структуры программ с количеством вопросов по блокам';


-- 8. ПРЕДСТАВЛЕНИЕ ПРОГРЕССА ПОЛЬЗОВАТЕЛЕЙ
CREATE OR REPLACE VIEW selfology.v_user_progress AS
SELECT
    up.user_id,
    p.name as program_name,
    b.name as current_block_name,
    b.block_type as current_block_type,
    up.questions_answered,
    up.completion_percentage,
    up.status,
    up.total_time_spent_sec / 60 as total_time_min,
    up.started_at,
    up.last_activity_at
FROM selfology.user_program_progress up
JOIN selfology.onboarding_programs p ON up.program_id = p.program_id
LEFT JOIN selfology.program_blocks b ON up.current_block_id = b.block_id;

COMMENT ON VIEW selfology.v_user_progress IS
'Представление прогресса пользователей по программам';


-- ============================================================
-- ГОТОВО! Структура для блочных программ создана
-- Следующий шаг: Заполнение таблиц из selfology_programs_v2.json
-- ============================================================
