-- Migration: Create user_context_stories table for free-form user narratives
-- Date: 2025-10-04
-- Purpose: Store user's self-descriptions and context shared during onboarding

-- Main table for storing context stories
CREATE TABLE IF NOT EXISTS selfology.user_context_stories (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    session_id INTEGER REFERENCES selfology.onboarding_sessions(id) ON DELETE SET NULL,

    -- Story content
    story_text TEXT NOT NULL,
    story_length INTEGER NOT NULL,

    -- Categorization
    story_type VARCHAR(30) DEFAULT 'onboarding_intro',  -- onboarding_intro, crisis_context, goal_setting, etc
    story_source VARCHAR(20) DEFAULT 'user_input',     -- user_input, bot_prompted, admin_added

    -- Metadata
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE,

    -- Full-text search vector (for Russian language)
    search_vector tsvector,

    -- Additional metadata
    metadata JSONB DEFAULT '{}'
);

-- Add comments for documentation
COMMENT ON TABLE selfology.user_context_stories IS 'Free-form user narratives and context shared during onboarding and sessions';
COMMENT ON COLUMN selfology.user_context_stories.story_type IS 'Type of story: onboarding_intro (default), crisis_context, goal_setting, breakthrough_moment, etc.';
COMMENT ON COLUMN selfology.user_context_stories.story_source IS 'How story was collected: user_input, bot_prompted, admin_added';
COMMENT ON COLUMN selfology.user_context_stories.search_vector IS 'Full-text search vector for Russian language using ru_stem configuration';
COMMENT ON COLUMN selfology.user_context_stories.metadata IS 'Additional flexible metadata (tags, sentiment, etc.)';

-- Create indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_context_stories_user
ON selfology.user_context_stories(user_id);

CREATE INDEX IF NOT EXISTS idx_context_stories_session
ON selfology.user_context_stories(session_id);

CREATE INDEX IF NOT EXISTS idx_context_stories_type
ON selfology.user_context_stories(story_type);

CREATE INDEX IF NOT EXISTS idx_context_stories_active
ON selfology.user_context_stories(user_id, is_active) WHERE is_active = true;

CREATE INDEX IF NOT EXISTS idx_context_stories_created
ON selfology.user_context_stories(created_at DESC);

-- Full-text search GIN index (for Russian language)
CREATE INDEX IF NOT EXISTS idx_context_stories_search
ON selfology.user_context_stories USING GIN(search_vector);

-- Trigger to auto-update search_vector when story_text changes
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

-- Extended answer_analysis to support context stories (alternative to user_answers)
-- This allows reusing the entire analysis infrastructure
ALTER TABLE selfology.answer_analysis
ADD COLUMN IF NOT EXISTS context_story_id INTEGER REFERENCES selfology.user_context_stories(id) ON DELETE CASCADE;

-- Index for linking analysis to context stories
CREATE INDEX IF NOT EXISTS idx_analysis_context_story
ON selfology.answer_analysis(context_story_id) WHERE context_story_id IS NOT NULL;

-- Add constraint to ensure either user_answer_id OR context_story_id is set
ALTER TABLE selfology.answer_analysis
ADD CONSTRAINT check_analysis_source
CHECK (
    (user_answer_id IS NOT NULL AND context_story_id IS NULL) OR
    (user_answer_id IS NULL AND context_story_id IS NOT NULL)
);

-- View for easy querying of context stories with their analysis
CREATE OR REPLACE VIEW selfology.context_stories_with_analysis AS
SELECT
    cs.id as story_id,
    cs.user_id,
    cs.session_id,
    cs.story_text,
    cs.story_type,
    cs.story_source,
    cs.created_at,
    cs.is_active,
    aa.id as analysis_id,
    aa.psychological_insights,
    aa.trait_scores,
    aa.emotional_state,
    aa.quality_score,
    aa.confidence_score,
    aa.special_situation,
    aa.is_milestone,
    aa.ai_model_used,
    aa.processed_at,
    aa.vectorization_status,
    aa.dp_update_status
FROM selfology.user_context_stories cs
LEFT JOIN selfology.answer_analysis aa ON aa.context_story_id = cs.id
WHERE cs.is_active = true
ORDER BY cs.created_at DESC;

COMMENT ON VIEW selfology.context_stories_with_analysis IS 'Context stories enriched with AI analysis results';

-- Function for full-text search across context stories
CREATE OR REPLACE FUNCTION selfology.search_user_context_stories(
    p_user_id INTEGER,
    p_search_query TEXT,
    p_limit INTEGER DEFAULT 10
)
RETURNS TABLE (
    story_id INTEGER,
    story_text TEXT,
    story_type VARCHAR(30),
    created_at TIMESTAMP,
    relevance REAL
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        cs.id,
        cs.story_text,
        cs.story_type,
        cs.created_at,
        ts_rank(cs.search_vector, plainto_tsquery('russian', p_search_query)) AS relevance
    FROM selfology.user_context_stories cs
    WHERE cs.user_id = p_user_id
        AND cs.is_active = true
        AND cs.search_vector @@ plainto_tsquery('russian', p_search_query)
    ORDER BY relevance DESC, cs.created_at DESC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION selfology.search_user_context_stories IS 'Full-text search across user context stories using Russian language stemming';
