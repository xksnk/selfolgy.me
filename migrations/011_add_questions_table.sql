-- Migration: Add questions table to PostgreSQL
-- Description: Move questions from JSON to database for better queryability and analytics
-- Author: Backend Architect
-- Date: 2025-10-06
-- Phase: PHASE 1 - Parallel with JSON (no breaking changes)

-- ============================================================================
-- 1. CREATE TABLE: questions
-- ============================================================================

CREATE TABLE IF NOT EXISTS selfology.questions (
    id SERIAL PRIMARY KEY,

    -- Идентификация
    question_id VARCHAR(20) UNIQUE NOT NULL,  -- "q_001", "q_002", etc.
    text TEXT NOT NULL,
    source_system VARCHAR(50) DEFAULT 'onboarding_v7',

    -- Классификация (денормализовано для быстрых запросов)
    journey_stage VARCHAR(20) NOT NULL,       -- EXPLORING, DEEPENING, INTEGRATING, etc.
    depth_level VARCHAR(20) NOT NULL,         -- SURFACE, CONSCIOUS, EDGE, SHADOW, CORE
    domain VARCHAR(30) NOT NULL,              -- IDENTITY, EMOTIONS, RELATIONSHIPS, etc.
    energy_dynamic VARCHAR(20) NOT NULL,      -- OPENING, NEUTRAL, PROCESSING, HEAVY, HEALING

    -- Психологические метрики (числовые для агрегаций!)
    complexity SMALLINT CHECK (complexity BETWEEN 1 AND 5),
    emotional_weight SMALLINT CHECK (emotional_weight BETWEEN 1 AND 5),
    insight_potential SMALLINT CHECK (insight_potential BETWEEN 1 AND 5),
    safety_level SMALLINT CHECK (safety_level BETWEEN 1 AND 5),
    trust_requirement SMALLINT CHECK (trust_requirement BETWEEN 1 AND 5),

    -- Processing hints (редко меняется, можно JSONB)
    processing_hints JSONB DEFAULT '{}'::jsonb,

    -- Metadata (гибкость для будущих расширений)
    metadata JSONB DEFAULT '{}'::jsonb,

    -- Связи с другими вопросами
    connections VARCHAR(20)[] DEFAULT '{}',   -- Array of question_ids

    -- Административные флаги (объединяем с questions_metadata)
    is_flagged BOOLEAN DEFAULT false,
    flagged_by_admin VARCHAR(50),
    flag_reason TEXT,
    flagged_at TIMESTAMP,

    -- Статистика использования (аналитика!)
    times_asked INTEGER DEFAULT 0,
    times_skipped INTEGER DEFAULT 0,
    avg_answer_length INTEGER,
    last_used_at TIMESTAMP,

    -- Активность
    is_active BOOLEAN DEFAULT true,

    -- Audit
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    -- Constraints
    CONSTRAINT valid_complexity CHECK (complexity >= 1 AND complexity <= 5),
    CONSTRAINT valid_emotional_weight CHECK (emotional_weight >= 1 AND emotional_weight <= 5),
    CONSTRAINT valid_insight_potential CHECK (insight_potential >= 1 AND insight_potential <= 5),
    CONSTRAINT valid_safety_level CHECK (safety_level >= 1 AND safety_level <= 5),
    CONSTRAINT valid_trust_requirement CHECK (trust_requirement >= 1 AND trust_requirement <= 5)
);

-- ============================================================================
-- 2. CREATE INDEXES
-- ============================================================================

-- Базовые индексы для фильтрации
CREATE INDEX idx_questions_question_id ON selfology.questions(question_id);
CREATE INDEX idx_questions_domain ON selfology.questions(domain);
CREATE INDEX idx_questions_depth ON selfology.questions(depth_level);
CREATE INDEX idx_questions_energy ON selfology.questions(energy_dynamic);
CREATE INDEX idx_questions_safety ON selfology.questions(safety_level);
CREATE INDEX idx_questions_journey ON selfology.questions(journey_stage);

-- Индексы для административных функций
CREATE INDEX idx_questions_active ON selfology.questions(is_active)
WHERE is_active = true;

CREATE INDEX idx_questions_flagged ON selfology.questions(is_flagged)
WHERE is_flagged = false;

-- Composite индекс для Smart Mix алгоритма (QuestionRouter)
-- Это самый важный индекс - ускоряет поиск следующего вопроса
CREATE INDEX idx_questions_routing ON selfology.questions(
    domain, depth_level, energy_dynamic, safety_level
) WHERE is_active = true AND is_flagged = false;

-- Индекс для поиска по сложности и эмоциональной нагрузке
CREATE INDEX idx_questions_psychology ON selfology.questions(
    complexity, emotional_weight, trust_requirement
);

-- GIN индекс для поиска по connections (связанные вопросы)
CREATE INDEX idx_questions_connections ON selfology.questions
USING GIN(connections);

-- GIN индекс для JSONB полей
CREATE INDEX idx_questions_processing_hints ON selfology.questions
USING GIN(processing_hints);

CREATE INDEX idx_questions_metadata ON selfology.questions
USING GIN(metadata);

-- Полнотекстовый поиск по тексту вопроса (для админки)
CREATE INDEX idx_questions_text_search ON selfology.questions
USING GIN(to_tsvector('russian', text));

-- Индексы для статистики
CREATE INDEX idx_questions_times_asked ON selfology.questions(times_asked DESC);
CREATE INDEX idx_questions_last_used ON selfology.questions(last_used_at DESC);

-- ============================================================================
-- 3. CREATE TRIGGER: Auto-update times_asked statistic
-- ============================================================================

CREATE OR REPLACE FUNCTION selfology.update_question_stats()
RETURNS TRIGGER AS $$
BEGIN
    -- Обновляем статистику при создании ответа
    UPDATE selfology.questions
    SET
        times_asked = times_asked + 1,
        last_used_at = NOW(),
        updated_at = NOW()
    WHERE question_id = NEW.question_json_id;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_question_stats
    AFTER INSERT ON selfology.user_answers_new
    FOR EACH ROW
    EXECUTE FUNCTION selfology.update_question_stats();

-- ============================================================================
-- 4. CREATE TRIGGER: Auto-update updated_at
-- ============================================================================

CREATE OR REPLACE FUNCTION selfology.update_questions_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_questions_timestamp
    BEFORE UPDATE ON selfology.questions
    FOR EACH ROW
    EXECUTE FUNCTION selfology.update_questions_updated_at();

-- ============================================================================
-- 5. CREATE VIEW: questions_with_stats
-- ============================================================================

CREATE OR REPLACE VIEW selfology.questions_with_stats AS
SELECT
    q.*,

    -- Статистика использования
    CASE
        WHEN q.times_asked = 0 THEN 0
        ELSE ROUND(q.times_skipped::numeric / q.times_asked::numeric * 100, 2)
    END as skip_rate_percent,

    -- Популярность
    CASE
        WHEN q.times_asked >= 100 THEN 'popular'
        WHEN q.times_asked >= 50 THEN 'moderate'
        WHEN q.times_asked >= 10 THEN 'low'
        ELSE 'new'
    END as popularity_level,

    -- Сложность в текстовом виде
    CASE
        WHEN q.complexity >= 4 THEN 'very_complex'
        WHEN q.complexity >= 3 THEN 'complex'
        WHEN q.complexity >= 2 THEN 'moderate'
        ELSE 'simple'
    END as complexity_text,

    -- Безопасность в текстовом виде
    CASE
        WHEN q.safety_level >= 4 THEN 'very_safe'
        WHEN q.safety_level >= 3 THEN 'safe'
        WHEN q.safety_level >= 2 THEN 'moderate'
        ELSE 'sensitive'
    END as safety_text

FROM selfology.questions q
WHERE q.is_active = true
ORDER BY q.created_at DESC;

-- ============================================================================
-- 6. CREATE FUNCTION: Search questions with filters
-- ============================================================================

CREATE OR REPLACE FUNCTION selfology.search_questions(
    p_domains VARCHAR(30)[] DEFAULT NULL,
    p_depth_level VARCHAR(20) DEFAULT NULL,
    p_energy_dynamic VARCHAR(20) DEFAULT NULL,
    p_min_safety SMALLINT DEFAULT 1,
    p_max_complexity SMALLINT DEFAULT 5,
    p_exclude_ids VARCHAR(20)[] DEFAULT '{}',
    p_limit INTEGER DEFAULT 50
)
RETURNS TABLE (
    question_id VARCHAR(20),
    text TEXT,
    domain VARCHAR(30),
    depth_level VARCHAR(20),
    energy_dynamic VARCHAR(20),
    complexity SMALLINT,
    emotional_weight SMALLINT,
    safety_level SMALLINT,
    trust_requirement SMALLINT,
    processing_hints JSONB,
    metadata JSONB
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        q.question_id,
        q.text,
        q.domain,
        q.depth_level,
        q.energy_dynamic,
        q.complexity,
        q.emotional_weight,
        q.safety_level,
        q.trust_requirement,
        q.processing_hints,
        q.metadata
    FROM selfology.questions q
    WHERE q.is_active = true
      AND q.is_flagged = false
      AND (p_domains IS NULL OR q.domain = ANY(p_domains))
      AND (p_depth_level IS NULL OR q.depth_level = p_depth_level)
      AND (p_energy_dynamic IS NULL OR q.energy_dynamic = p_energy_dynamic)
      AND q.safety_level >= p_min_safety
      AND q.complexity <= p_max_complexity
      AND q.question_id != ALL(p_exclude_ids)
    ORDER BY RANDOM()
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- 7. CREATE FUNCTION: Get question analytics
-- ============================================================================

CREATE OR REPLACE FUNCTION selfology.get_question_analytics(
    p_question_id VARCHAR(20)
)
RETURNS TABLE (
    question_id VARCHAR(20),
    text TEXT,
    times_asked INTEGER,
    times_skipped INTEGER,
    skip_rate NUMERIC,
    avg_answer_length INTEGER,
    unique_users_answered INTEGER,
    last_used_at TIMESTAMP,
    avg_quality_score NUMERIC,
    avg_confidence_score NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        q.question_id,
        q.text,
        q.times_asked,
        q.times_skipped,
        CASE
            WHEN q.times_asked = 0 THEN 0
            ELSE ROUND(q.times_skipped::numeric / q.times_asked::numeric, 4)
        END as skip_rate,
        q.avg_answer_length,
        (
            SELECT COUNT(DISTINCT os.user_id)
            FROM selfology.user_answers_new ua
            JOIN selfology.onboarding_sessions os ON os.id = ua.session_id
            WHERE ua.question_json_id = q.question_id
        )::INTEGER as unique_users_answered,
        q.last_used_at,
        (
            SELECT ROUND(AVG(aa.quality_score)::numeric, 3)
            FROM selfology.answer_analysis aa
            JOIN selfology.user_answers_new ua ON ua.id = aa.user_answer_id
            WHERE ua.question_json_id = q.question_id
        ) as avg_quality_score,
        (
            SELECT ROUND(AVG(aa.confidence_score)::numeric, 3)
            FROM selfology.answer_analysis aa
            JOIN selfology.user_answers_new ua ON ua.id = aa.user_answer_id
            WHERE ua.question_json_id = q.question_id
        ) as avg_confidence_score
    FROM selfology.questions q
    WHERE q.question_id = p_question_id;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- 8. GRANT PERMISSIONS
-- ============================================================================

GRANT ALL ON selfology.questions TO n8n;
GRANT ALL ON SEQUENCE selfology.questions_id_seq TO n8n;
GRANT SELECT ON selfology.questions_with_stats TO n8n;
GRANT EXECUTE ON FUNCTION selfology.update_question_stats TO n8n;
GRANT EXECUTE ON FUNCTION selfology.update_questions_updated_at TO n8n;
GRANT EXECUTE ON FUNCTION selfology.search_questions TO n8n;
GRANT EXECUTE ON FUNCTION selfology.get_question_analytics TO n8n;

-- ============================================================================
-- 9. COMMENTS
-- ============================================================================

COMMENT ON TABLE selfology.questions IS
'Questions repository - moved from JSON for better queryability and analytics. Source of truth remains JSON file for versioning.';

COMMENT ON COLUMN selfology.questions.question_id IS
'Unique question identifier (e.g., "q_001") - matches JSON file';

COMMENT ON COLUMN selfology.questions.times_asked IS
'How many times this question was asked to users (auto-updated by trigger)';

COMMENT ON COLUMN selfology.questions.avg_answer_length IS
'Average length of answers to this question (calculated periodically)';

COMMENT ON COLUMN selfology.questions.processing_hints IS
'AI processing hints: recommended_model, batch_compatible, requires_context, etc.';

COMMENT ON COLUMN selfology.questions.connections IS
'Array of related question IDs for follow-up questions';

COMMENT ON VIEW selfology.questions_with_stats IS
'Questions with calculated statistics and text representations';

COMMENT ON FUNCTION selfology.search_questions IS
'Smart search for questions with multiple filters - used by QuestionRouter';

COMMENT ON FUNCTION selfology.get_question_analytics IS
'Get detailed analytics for a specific question including quality scores';

-- ============================================================================
-- 10. VALIDATION QUERY
-- ============================================================================

-- После загрузки данных можно проверить:
-- SELECT COUNT(*) FROM selfology.questions WHERE is_active = true;
-- Expected: 693

-- SELECT domain, COUNT(*) FROM selfology.questions GROUP BY domain ORDER BY COUNT(*) DESC;
-- Should show distribution across domains

-- SELECT * FROM selfology.search_questions(
--     p_domains := ARRAY['IDENTITY', 'EMOTIONS'],
--     p_min_safety := 3,
--     p_limit := 10
-- );
-- Should return 10 random safe questions from IDENTITY and EMOTIONS domains
