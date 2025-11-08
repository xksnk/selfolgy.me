-- Migration: Create user_context_stories table
-- Description: Store user's free-form context stories for better AI coach understanding
-- Author: Claude Code
-- Date: 2025-10-04

-- ============================================================================
-- 1. CREATE TABLE: user_context_stories
-- ============================================================================

CREATE TABLE IF NOT EXISTS selfology.user_context_stories (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    session_id INTEGER REFERENCES selfology.onboarding_sessions(id) ON DELETE SET NULL,

    -- Story content
    story_text TEXT NOT NULL,
    story_type VARCHAR(50) DEFAULT 'onboarding_context',

    -- Metadata
    metadata JSONB DEFAULT '{}',

    -- Full-text search vector (auto-updated by trigger)
    search_vector tsvector,

    -- Status
    is_active BOOLEAN DEFAULT TRUE,

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    deactivated_at TIMESTAMP,

    -- Constraints
    CONSTRAINT valid_story_text CHECK (LENGTH(story_text) > 0)
);

-- ============================================================================
-- 2. CREATE INDEXES
-- ============================================================================

-- Index for user queries
CREATE INDEX idx_context_stories_user_id ON selfology.user_context_stories(user_id);

-- Index for session queries
CREATE INDEX idx_context_stories_session_id ON selfology.user_context_stories(session_id);

-- Index for active stories
CREATE INDEX idx_context_stories_active ON selfology.user_context_stories(user_id, is_active);

-- GIN index for full-text search (Russian language)
CREATE INDEX idx_context_stories_search ON selfology.user_context_stories USING GIN(search_vector);

-- ============================================================================
-- 3. CREATE TRIGGER: Auto-update search_vector
-- ============================================================================

CREATE OR REPLACE FUNCTION selfology.update_context_story_search_vector()
RETURNS TRIGGER AS $$
BEGIN
    NEW.search_vector := to_tsvector('russian', COALESCE(NEW.story_text, ''));
    NEW.updated_at := NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_context_story_search_vector
    BEFORE INSERT OR UPDATE OF story_text
    ON selfology.user_context_stories
    FOR EACH ROW
    EXECUTE FUNCTION selfology.update_context_story_search_vector();

-- ============================================================================
-- 4. UPDATE TABLE: answer_analysis (add context_story_id support)
-- ============================================================================

-- Add new column for linking context stories
ALTER TABLE selfology.answer_analysis
ADD COLUMN IF NOT EXISTS context_story_id INTEGER REFERENCES selfology.user_context_stories(id) ON DELETE CASCADE;

-- Create index for context story lookups
CREATE INDEX IF NOT EXISTS idx_answer_analysis_context_story
ON selfology.answer_analysis(context_story_id);

-- Add constraint: either user_answer_id or context_story_id must be set
ALTER TABLE selfology.answer_analysis
ADD CONSTRAINT check_analysis_source
CHECK (
    (user_answer_id IS NOT NULL AND context_story_id IS NULL) OR
    (user_answer_id IS NULL AND context_story_id IS NOT NULL)
);

-- ============================================================================
-- 5. CREATE VIEW: context_stories_with_analysis
-- ============================================================================

CREATE OR REPLACE VIEW selfology.context_stories_with_analysis AS
SELECT
    cs.id,
    cs.user_id,
    cs.session_id,
    cs.story_text,
    cs.story_type,
    cs.metadata,
    cs.is_active,
    cs.created_at,

    -- Analysis fields
    aa.id as analysis_id,
    aa.quality_score,
    aa.confidence_score,
    aa.emotional_state,
    aa.special_situation,
    aa.insights,
    aa.trait_scores,
    aa.vectorization_status,
    aa.dp_update_status

FROM selfology.user_context_stories cs
LEFT JOIN selfology.answer_analysis aa ON aa.context_story_id = cs.id
WHERE cs.is_active = TRUE
ORDER BY cs.created_at DESC;

-- ============================================================================
-- 6. CREATE FUNCTION: Search context stories by text
-- ============================================================================

CREATE OR REPLACE FUNCTION selfology.search_user_context_stories(
    p_user_id BIGINT,
    p_search_query TEXT,
    p_limit INTEGER DEFAULT 10
)
RETURNS TABLE (
    id INTEGER,
    story_text TEXT,
    story_type VARCHAR(50),
    relevance REAL,
    created_at TIMESTAMP
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        cs.id,
        cs.story_text,
        cs.story_type,
        ts_rank(cs.search_vector, to_tsquery('russian', p_search_query)) AS relevance,
        cs.created_at
    FROM selfology.user_context_stories cs
    WHERE cs.user_id = p_user_id
      AND cs.is_active = TRUE
      AND cs.search_vector @@ to_tsquery('russian', p_search_query)
    ORDER BY relevance DESC, cs.created_at DESC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- 7. GRANT PERMISSIONS
-- ============================================================================

GRANT ALL ON selfology.user_context_stories TO n8n;
GRANT ALL ON SEQUENCE selfology.user_context_stories_id_seq TO n8n;
GRANT SELECT ON selfology.context_stories_with_analysis TO n8n;
GRANT EXECUTE ON FUNCTION selfology.search_user_context_stories TO n8n;
GRANT EXECUTE ON FUNCTION selfology.update_context_story_search_vector TO n8n;

-- ============================================================================
-- 8. COMMENTS
-- ============================================================================

COMMENT ON TABLE selfology.user_context_stories IS
'User context stories - free-form important information about the user';

COMMENT ON COLUMN selfology.user_context_stories.story_text IS
'User-provided context story text';

COMMENT ON COLUMN selfology.user_context_stories.search_vector IS
'Auto-updated full-text search vector for Russian language search';

COMMENT ON COLUMN selfology.user_context_stories.story_type IS
'Type of story: onboarding_context, chat_insight, etc.';

COMMENT ON COLUMN selfology.answer_analysis.context_story_id IS
'Reference to context story if this analysis is for a story (not a question answer)';

COMMENT ON VIEW selfology.context_stories_with_analysis IS
'Active context stories with their AI analysis results';

COMMENT ON FUNCTION selfology.search_user_context_stories IS
'Full-text search in user context stories with relevance ranking';
