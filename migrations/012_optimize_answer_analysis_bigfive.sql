-- Migration: Optimize answer_analysis with denormalized Big Five
-- Description: Extract Big Five traits from JSONB to separate columns for SQL analytics
-- Author: Backend Architect
-- Date: 2025-10-06
-- Phase: PHASE 3 - Performance optimization for analytics

-- ============================================================================
-- 1. ADD COLUMNS: Big Five traits as separate columns
-- ============================================================================

-- Добавляем колонки для Big Five (числовые для агрегаций)
ALTER TABLE selfology.answer_analysis
ADD COLUMN IF NOT EXISTS openness NUMERIC(4,3) CHECK (openness BETWEEN 0 AND 1),
ADD COLUMN IF NOT EXISTS conscientiousness NUMERIC(4,3) CHECK (conscientiousness BETWEEN 0 AND 1),
ADD COLUMN IF NOT EXISTS extraversion NUMERIC(4,3) CHECK (extraversion BETWEEN 0 AND 1),
ADD COLUMN IF NOT EXISTS agreeableness NUMERIC(4,3) CHECK (agreeableness BETWEEN 0 AND 1),
ADD COLUMN IF NOT EXISTS neuroticism NUMERIC(4,3) CHECK (neuroticism BETWEEN 0 AND 1);

-- Переименовываем trait_scores в extended_traits (более точное название)
ALTER TABLE selfology.answer_analysis
RENAME COLUMN trait_scores TO extended_traits;

-- ============================================================================
-- 2. BACKFILL DATA: Извлечь Big Five из JSONB в колонки
-- ============================================================================

-- Обновляем существующие записи (извлекаем из extended_traits)
UPDATE selfology.answer_analysis
SET
    openness = CASE
        WHEN extended_traits->'big_five'->>'openness' ~ '^\d+(\.\d+)?$'
        THEN (extended_traits->'big_five'->>'openness')::numeric
        ELSE NULL
    END,
    conscientiousness = CASE
        WHEN extended_traits->'big_five'->>'conscientiousness' ~ '^\d+(\.\d+)?$'
        THEN (extended_traits->'big_five'->>'conscientiousness')::numeric
        ELSE NULL
    END,
    extraversion = CASE
        WHEN extended_traits->'big_five'->>'extraversion' ~ '^\d+(\.\d+)?$'
        THEN (extended_traits->'big_five'->>'extraversion')::numeric
        ELSE NULL
    END,
    agreeableness = CASE
        WHEN extended_traits->'big_five'->>'agreeableness' ~ '^\d+(\.\d+)?$'
        THEN (extended_traits->'big_five'->>'agreeableness')::numeric
        ELSE NULL
    END,
    neuroticism = CASE
        WHEN extended_traits->'big_five'->>'neuroticism' ~ '^\d+(\.\d+)?$'
        THEN (extended_traits->'big_five'->>'neuroticism')::numeric
        ELSE NULL
    END
WHERE extended_traits IS NOT NULL
  AND extended_traits->'big_five' IS NOT NULL;

-- ============================================================================
-- 3. CREATE INDEXES: Для быстрого поиска и аналитики
-- ============================================================================

-- Индексы для каждой черты (для фильтрации)
CREATE INDEX IF NOT EXISTS idx_analysis_openness ON selfology.answer_analysis(openness)
WHERE openness IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_analysis_conscientiousness ON selfology.answer_analysis(conscientiousness)
WHERE conscientiousness IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_analysis_extraversion ON selfology.answer_analysis(extraversion)
WHERE extraversion IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_analysis_agreeableness ON selfology.answer_analysis(agreeableness)
WHERE agreeableness IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_analysis_neuroticism ON selfology.answer_analysis(neuroticism)
WHERE neuroticism IS NOT NULL;

-- Composite index для поиска похожих личностных профилей
CREATE INDEX IF NOT EXISTS idx_analysis_personality_profile ON selfology.answer_analysis(
    openness, conscientiousness, extraversion, agreeableness, neuroticism
) WHERE openness IS NOT NULL;

-- Индексы для качественных метрик
CREATE INDEX IF NOT EXISTS idx_analysis_quality_high ON selfology.answer_analysis(quality_score)
WHERE quality_score >= 0.7;

CREATE INDEX IF NOT EXISTS idx_analysis_confidence_high ON selfology.answer_analysis(confidence_score)
WHERE confidence_score >= 0.7;

-- GIN индекс для extended_traits (оставшиеся динамические traits)
CREATE INDEX IF NOT EXISTS idx_analysis_extended_traits ON selfology.answer_analysis
USING GIN(extended_traits);

-- ============================================================================
-- 4. CREATE VIEW: Full answer context with Big Five
-- ============================================================================

CREATE OR REPLACE VIEW selfology.full_answer_context AS
SELECT
    -- Answer info
    ua.id as answer_id,
    ua.session_id,
    ua.question_json_id,
    ua.raw_answer,
    ua.answer_length,
    ua.answered_at,

    -- Question details (будет работать после миграции 011)
    -- Пока используем question_json_id, после миграции добавим JOIN
    ua.question_json_id as question_id,

    -- Analysis Big Five (денормализованные)
    aa.openness,
    aa.conscientiousness,
    aa.extraversion,
    aa.agreeableness,
    aa.neuroticism,

    -- Analysis quality
    aa.quality_score,
    aa.confidence_score,
    aa.emotional_state,
    aa.fatigue_level,

    -- Special situations
    aa.special_situation,
    aa.is_milestone,

    -- Extended traits (JSONB)
    aa.extended_traits,

    -- Insights
    aa.psychological_insights,

    -- Metadata
    aa.ai_model_used,
    aa.processing_time_ms,
    aa.processed_at,
    aa.analysis_version,

    -- Session context
    os.user_id,
    os.questions_answered,
    os.started_at as session_started

FROM selfology.user_answers_new ua
LEFT JOIN selfology.answer_analysis aa ON aa.user_answer_id = ua.id
LEFT JOIN selfology.onboarding_sessions os ON os.id = ua.session_id;

-- ============================================================================
-- 5. CREATE FUNCTION: Get user personality evolution
-- ============================================================================

CREATE OR REPLACE FUNCTION selfology.get_personality_evolution(
    p_user_id INTEGER,
    p_limit INTEGER DEFAULT 100
)
RETURNS TABLE (
    answer_id INTEGER,
    answered_at TIMESTAMP,
    question_text TEXT,
    openness NUMERIC,
    conscientiousness NUMERIC,
    extraversion NUMERIC,
    agreeableness NUMERIC,
    neuroticism NUMERIC,
    emotional_state VARCHAR,
    quality_score NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        ua.id as answer_id,
        ua.answered_at,
        ua.question_json_id as question_text,  -- После миграции 011 будет q.text
        aa.openness,
        aa.conscientiousness,
        aa.extraversion,
        aa.agreeableness,
        aa.neuroticism,
        aa.emotional_state,
        aa.quality_score
    FROM selfology.user_answers_new ua
    JOIN selfology.onboarding_sessions os ON os.id = ua.session_id
    LEFT JOIN selfology.answer_analysis aa ON aa.user_answer_id = ua.id
    WHERE os.user_id = p_user_id
      AND aa.openness IS NOT NULL  -- Only analyzed answers
    ORDER BY ua.answered_at ASC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- 6. CREATE FUNCTION: Get average Big Five for user
-- ============================================================================

CREATE OR REPLACE FUNCTION selfology.get_user_avg_bigfive(
    p_user_id INTEGER
)
RETURNS TABLE (
    avg_openness NUMERIC,
    avg_conscientiousness NUMERIC,
    avg_extraversion NUMERIC,
    avg_agreeableness NUMERIC,
    avg_neuroticism NUMERIC,
    stddev_openness NUMERIC,
    stddev_conscientiousness NUMERIC,
    stddev_extraversion NUMERIC,
    stddev_agreeableness NUMERIC,
    stddev_neuroticism NUMERIC,
    total_analyses INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        ROUND(AVG(aa.openness)::numeric, 3) as avg_openness,
        ROUND(AVG(aa.conscientiousness)::numeric, 3) as avg_conscientiousness,
        ROUND(AVG(aa.extraversion)::numeric, 3) as avg_extraversion,
        ROUND(AVG(aa.agreeableness)::numeric, 3) as avg_agreeableness,
        ROUND(AVG(aa.neuroticism)::numeric, 3) as avg_neuroticism,
        ROUND(STDDEV(aa.openness)::numeric, 3) as stddev_openness,
        ROUND(STDDEV(aa.conscientiousness)::numeric, 3) as stddev_conscientiousness,
        ROUND(STDDEV(aa.extraversion)::numeric, 3) as stddev_extraversion,
        ROUND(STDDEV(aa.agreeableness)::numeric, 3) as stddev_agreeableness,
        ROUND(STDDEV(aa.neuroticism)::numeric, 3) as stddev_neuroticism,
        COUNT(*)::INTEGER as total_analyses
    FROM selfology.answer_analysis aa
    JOIN selfology.user_answers_new ua ON ua.id = aa.user_answer_id
    JOIN selfology.onboarding_sessions os ON os.id = ua.session_id
    WHERE os.user_id = p_user_id
      AND aa.openness IS NOT NULL;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- 7. CREATE FUNCTION: Find similar users by Big Five
-- ============================================================================

CREATE OR REPLACE FUNCTION selfology.find_similar_users_by_bigfive(
    p_user_id INTEGER,
    p_similarity_threshold NUMERIC DEFAULT 0.1,  -- Max difference per trait
    p_limit INTEGER DEFAULT 10
)
RETURNS TABLE (
    user_id INTEGER,
    similarity_score NUMERIC,
    openness_diff NUMERIC,
    conscientiousness_diff NUMERIC,
    extraversion_diff NUMERIC,
    agreeableness_diff NUMERIC,
    neuroticism_diff NUMERIC
) AS $$
DECLARE
    v_target_o NUMERIC;
    v_target_c NUMERIC;
    v_target_e NUMERIC;
    v_target_a NUMERIC;
    v_target_n NUMERIC;
BEGIN
    -- Получить средние Big Five для целевого пользователя
    SELECT
        avg_openness, avg_conscientiousness, avg_extraversion,
        avg_agreeableness, avg_neuroticism
    INTO v_target_o, v_target_c, v_target_e, v_target_a, v_target_n
    FROM selfology.get_user_avg_bigfive(p_user_id);

    -- Найти похожих пользователей
    RETURN QUERY
    WITH user_avg_traits AS (
        SELECT
            os.user_id,
            AVG(aa.openness) as avg_o,
            AVG(aa.conscientiousness) as avg_c,
            AVG(aa.extraversion) as avg_e,
            AVG(aa.agreeableness) as avg_a,
            AVG(aa.neuroticism) as avg_n
        FROM selfology.answer_analysis aa
        JOIN selfology.user_answers_new ua ON ua.id = aa.user_answer_id
        JOIN selfology.onboarding_sessions os ON os.id = ua.session_id
        WHERE os.user_id != p_user_id
          AND aa.openness IS NOT NULL
        GROUP BY os.user_id
        HAVING COUNT(*) >= 5  -- Minimum 5 analyses
    )
    SELECT
        uat.user_id,
        -- Similarity score (0.0 = identical, 1.0 = very different)
        ROUND(
            (ABS(uat.avg_o - v_target_o) +
             ABS(uat.avg_c - v_target_c) +
             ABS(uat.avg_e - v_target_e) +
             ABS(uat.avg_a - v_target_a) +
             ABS(uat.avg_n - v_target_n)) / 5.0,
            3
        ) as similarity_score,
        ROUND(ABS(uat.avg_o - v_target_o), 3) as openness_diff,
        ROUND(ABS(uat.avg_c - v_target_c), 3) as conscientiousness_diff,
        ROUND(ABS(uat.avg_e - v_target_e), 3) as extraversion_diff,
        ROUND(ABS(uat.avg_a - v_target_a), 3) as agreeableness_diff,
        ROUND(ABS(uat.avg_n - v_target_n), 3) as neuroticism_diff
    FROM user_avg_traits uat
    WHERE (ABS(uat.avg_o - v_target_o) +
           ABS(uat.avg_c - v_target_c) +
           ABS(uat.avg_e - v_target_e) +
           ABS(uat.avg_a - v_target_a) +
           ABS(uat.avg_n - v_target_n)) / 5.0 <= p_similarity_threshold
    ORDER BY similarity_score ASC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- 8. CREATE MATERIALIZED VIEW: User personality summaries
-- ============================================================================

CREATE MATERIALIZED VIEW IF NOT EXISTS selfology.user_personality_summary AS
SELECT
    os.user_id,

    -- Big Five averages
    ROUND(AVG(aa.openness)::numeric, 3) as avg_openness,
    ROUND(AVG(aa.conscientiousness)::numeric, 3) as avg_conscientiousness,
    ROUND(AVG(aa.extraversion)::numeric, 3) as avg_extraversion,
    ROUND(AVG(aa.agreeableness)::numeric, 3) as avg_agreeableness,
    ROUND(AVG(aa.neuroticism)::numeric, 3) as avg_neuroticism,

    -- Big Five standard deviations (stability)
    ROUND(STDDEV(aa.openness)::numeric, 3) as stddev_openness,
    ROUND(STDDEV(aa.conscientiousness)::numeric, 3) as stddev_conscientiousness,
    ROUND(STDDEV(aa.extraversion)::numeric, 3) as stddev_extraversion,
    ROUND(STDDEV(aa.agreeableness)::numeric, 3) as stddev_agreeableness,
    ROUND(STDDEV(aa.neuroticism)::numeric, 3) as stddev_neuroticism,

    -- Quality metrics
    ROUND(AVG(aa.quality_score)::numeric, 3) as avg_quality,
    ROUND(AVG(aa.confidence_score)::numeric, 3) as avg_confidence,

    -- Counts
    COUNT(*) as total_analyses,
    COUNT(*) FILTER (WHERE aa.is_milestone = true) as milestone_count,
    COUNT(*) FILTER (WHERE aa.special_situation = 'crisis') as crisis_count,
    COUNT(*) FILTER (WHERE aa.special_situation = 'breakthrough') as breakthrough_count,

    -- Timestamps
    MIN(aa.processed_at) as first_analysis,
    MAX(aa.processed_at) as last_analysis

FROM selfology.answer_analysis aa
JOIN selfology.user_answers_new ua ON ua.id = aa.user_answer_id
JOIN selfology.onboarding_sessions os ON os.id = ua.session_id
WHERE aa.openness IS NOT NULL
GROUP BY os.user_id;

-- Уникальный индекс для REFRESH CONCURRENTLY
CREATE UNIQUE INDEX IF NOT EXISTS idx_user_personality_summary_user_id
ON selfology.user_personality_summary(user_id);

-- ============================================================================
-- 9. GRANT PERMISSIONS
-- ============================================================================

GRANT SELECT ON selfology.full_answer_context TO n8n;
GRANT SELECT ON selfology.user_personality_summary TO n8n;
GRANT EXECUTE ON FUNCTION selfology.get_personality_evolution TO n8n;
GRANT EXECUTE ON FUNCTION selfology.get_user_avg_bigfive TO n8n;
GRANT EXECUTE ON FUNCTION selfology.find_similar_users_by_bigfive TO n8n;

-- ============================================================================
-- 10. COMMENTS
-- ============================================================================

COMMENT ON COLUMN selfology.answer_analysis.openness IS
'Big Five: Openness to experience (0.0-1.0) - extracted from extended_traits for fast SQL queries';

COMMENT ON COLUMN selfology.answer_analysis.conscientiousness IS
'Big Five: Conscientiousness (0.0-1.0) - organization, responsibility, self-discipline';

COMMENT ON COLUMN selfology.answer_analysis.extraversion IS
'Big Five: Extraversion (0.0-1.0) - sociability, assertiveness, energy';

COMMENT ON COLUMN selfology.answer_analysis.agreeableness IS
'Big Five: Agreeableness (0.0-1.0) - compassion, cooperation, trust';

COMMENT ON COLUMN selfology.answer_analysis.neuroticism IS
'Big Five: Neuroticism (0.0-1.0) - emotional stability, anxiety, vulnerability';

COMMENT ON COLUMN selfology.answer_analysis.extended_traits IS
'Extended traits in JSONB: dynamic, adaptive, domain-specific traits beyond Big Five';

COMMENT ON VIEW selfology.full_answer_context IS
'Complete answer context: question + answer + Big Five + analysis + session - optimized for AI Coach';

COMMENT ON MATERIALIZED VIEW selfology.user_personality_summary IS
'Aggregated personality profile per user with Big Five averages and stability metrics - refresh hourly';

COMMENT ON FUNCTION selfology.get_personality_evolution IS
'Get user personality evolution over time - shows how Big Five traits changed during onboarding';

COMMENT ON FUNCTION selfology.get_user_avg_bigfive IS
'Get average Big Five profile for a user with standard deviations';

COMMENT ON FUNCTION selfology.find_similar_users_by_bigfive IS
'Find users with similar Big Five personality profiles - useful for recommendations';

-- ============================================================================
-- 11. REFRESH SCHEDULE (setup in cron or pg_cron)
-- ============================================================================

-- Рекомендуется обновлять каждый час:
-- REFRESH MATERIALIZED VIEW CONCURRENTLY selfology.user_personality_summary;

-- Или создать функцию для автоматического обновления:
CREATE OR REPLACE FUNCTION selfology.refresh_personality_summary()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY selfology.user_personality_summary;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- 12. VALIDATION QUERIES
-- ============================================================================

-- После миграции можно проверить:

-- 1. Проверка backfill Big Five
-- SELECT COUNT(*) FROM selfology.answer_analysis WHERE openness IS NOT NULL;

-- 2. Средние Big Five по всем пользователям
-- SELECT
--     ROUND(AVG(openness), 3) as avg_o,
--     ROUND(AVG(conscientiousness), 3) as avg_c,
--     ROUND(AVG(extraversion), 3) as avg_e,
--     ROUND(AVG(agreeableness), 3) as avg_a,
--     ROUND(AVG(neuroticism), 3) as avg_n
-- FROM selfology.answer_analysis
-- WHERE openness IS NOT NULL;

-- 3. Эволюция личности конкретного пользователя
-- SELECT * FROM selfology.get_personality_evolution(98005572, 20);

-- 4. Средние Big Five конкретного пользователя
-- SELECT * FROM selfology.get_user_avg_bigfive(98005572);

-- 5. Похожие пользователи
-- SELECT * FROM selfology.find_similar_users_by_bigfive(98005572, 0.15, 5);
