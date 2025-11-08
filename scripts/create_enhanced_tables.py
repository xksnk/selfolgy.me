#!/usr/bin/env python3
"""
Create enhanced database tables for intelligent memory system.
"""

import asyncio
import asyncpg
import os

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", 5432)),
    "user": os.getenv("DB_USER", "n8n"),
    "password": os.getenv("DB_PASSWORD", "sS67wM+1zMBRFHAW4kj9HwFl5J6+veo7Nirx0/I+oiU="),
    "database": os.getenv("DB_NAME", "n8n")
}

ENHANCED_TABLES_SQL = """

-- Enhanced user sessions with intelligent tracking
CREATE TABLE IF NOT EXISTS selfology_intelligent_sessions (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(50) REFERENCES selfology_users(telegram_id),
    session_uuid UUID DEFAULT gen_random_uuid(),
    
    -- Session state tracking
    current_energy DECIMAL(3,2) DEFAULT 0.3,      -- -2.0 to +2.0
    trust_level DECIMAL(3,2) DEFAULT 1.0,         -- 1.0 to 5.0
    healing_debt DECIMAL(3,2) DEFAULT 0.0,        -- Energy debt from HEAVY questions
    resistance_count INTEGER DEFAULT 0,
    breakthrough_count INTEGER DEFAULT 0,
    
    -- Question tracking
    questions_asked JSONB DEFAULT '[]',            -- Array of question IDs
    current_question_id VARCHAR(10),               -- Current question from core
    energy_timeline JSONB DEFAULT '[0.3]',         -- Energy level history
    domain_progress JSONB DEFAULT '{}',            -- Progress per domain
    
    -- Session metadata
    session_start TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_activity TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    session_ended TIMESTAMP WITH TIME ZONE,
    session_type VARCHAR(50) DEFAULT 'onboarding',  -- onboarding, coaching, assessment
    
    UNIQUE(user_id, session_uuid)
);

-- Question answers with versioning
CREATE TABLE IF NOT EXISTS selfology_question_answers (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(50) REFERENCES selfology_users(telegram_id),
    question_id VARCHAR(10) NOT NULL,              -- From intelligent question core
    
    -- Answer versioning
    answer_version INTEGER DEFAULT 1,
    answer_text TEXT NOT NULL,
    answer_analysis JSONB,                         -- AI analysis of answer
    
    -- Correction tracking  
    correction_reason VARCHAR(200),                -- Why was answer corrected
    superseded_by INTEGER REFERENCES selfology_question_answers(id),
    is_current BOOLEAN DEFAULT true,
    
    -- Metadata
    answered_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    ai_model_used VARCHAR(50),                     -- Which AI model analyzed
    processing_cost DECIMAL(8,6),                  -- Cost of AI analysis
    confidence_score DECIMAL(3,2),                 -- AI confidence in analysis
    
    -- Vector impact tracking
    vector_updates JSONB,                          -- What vector dimensions were updated
    vector_impact_magnitude DECIMAL(4,3),          -- How much vector changed
    
    UNIQUE(user_id, question_id, answer_version)
);

-- Chat insights from free-form conversations  
CREATE TABLE IF NOT EXISTS selfology_chat_insights (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(50) REFERENCES selfology_users(telegram_id),
    
    -- Insight content
    insight_text TEXT NOT NULL,
    insight_type VARCHAR(50) NOT NULL,             -- factual_update, emotional_insight, etc.
    trigger_context TEXT,                          -- Full chat message that triggered
    
    -- Classification
    psychological_domain VARCHAR(50) NOT NULL,     -- IDENTITY, EMOTIONS, etc.
    depth_level VARCHAR(20) NOT NULL,              -- SURFACE, CONSCIOUS, EDGE
    significance VARCHAR(20) DEFAULT 'medium',      -- low, medium, high
    
    -- AI analysis
    ai_confidence DECIMAL(3,2),                    -- AI confidence in insight
    psychological_markers JSONB,                   -- Extracted psychological data
    vector_implications JSONB,                     -- Expected vector changes
    
    -- Question connections
    related_question_ids JSONB DEFAULT '[]',       -- Connected core questions
    generated_virtual_question JSONB,              -- AI-generated question if no matches
    
    -- Insight lifecycle
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    superseded_by INTEGER REFERENCES selfology_chat_insights(id),
    is_active BOOLEAN DEFAULT true,
    
    -- Vector tracking
    vector_update_applied BOOLEAN DEFAULT false,
    vector_update_timestamp TIMESTAMP WITH TIME ZONE
);

-- User statements worth remembering
CREATE TABLE IF NOT EXISTS selfology_user_statements (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(50) REFERENCES selfology_users(telegram_id),
    
    -- Statement content
    statement_text TEXT NOT NULL,
    statement_type VARCHAR(50) NOT NULL,           -- belief, goal, pattern, value, fear
    extraction_source VARCHAR(50) NOT NULL,        -- chat, question_answer, insight
    
    -- Classification and metadata
    related_domain VARCHAR(50),                    -- Main psychological domain
    emotional_weight DECIMAL(3,2),                 -- Emotional significance
    confidence_score DECIMAL(3,2),                 -- AI confidence
    
    -- Lifecycle management
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    superseded_by INTEGER REFERENCES selfology_user_statements(id),
    is_current BOOLEAN DEFAULT true,
    
    -- Context and connections
    context_data JSONB,                            -- Additional context
    related_statements JSONB DEFAULT '[]',         -- IDs of related statements
    
    FULLTEXT KEY ft_statement (statement_text)     -- For search
);

-- Personality vector evolution tracking
CREATE TABLE IF NOT EXISTS selfology_vector_evolution (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(50) REFERENCES selfology_users(telegram_id),
    
    -- Vector data
    vector_version INTEGER NOT NULL,
    vector_dimensions JSONB NOT NULL,              -- Current vector state
    dimension_changes JSONB,                       -- What changed from previous version
    
    -- Change triggers
    change_source VARCHAR(50) NOT NULL,            -- question_answer, chat_insight, correction
    source_reference VARCHAR(100),                 -- ID of question/insight that caused change
    change_magnitude DECIMAL(4,3),                 -- Total magnitude of change
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    ai_model_used VARCHAR(50),                     -- Model that generated the change
    confidence_level DECIMAL(3,2),                 -- Confidence in changes
    
    -- Evolution tracking
    domains_affected JSONB,                        -- Which psychological domains changed
    growth_indicators JSONB                        -- Markers of psychological growth
);

-- Session analytics and patterns
CREATE TABLE IF NOT EXISTS selfology_session_analytics (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(50) REFERENCES selfology_users(telegram_id),
    session_uuid UUID REFERENCES selfology_intelligent_sessions(session_uuid),
    
    -- Session quality metrics
    engagement_score DECIMAL(3,2),                 -- How engaged was user
    insight_generation_rate DECIMAL(3,2),          -- Insights per question
    energy_balance_score DECIMAL(3,2),             -- Energy management quality
    safety_maintenance_score DECIMAL(3,2),         -- Psychological safety
    
    -- Progress metrics
    domains_explored INTEGER,                      -- How many domains covered
    average_depth_reached VARCHAR(20),             -- SURFACE, CONSCIOUS, etc.
    breakthrough_moments INTEGER,                  -- Significant insights
    resistance_incidents INTEGER,                  -- Times user showed resistance
    
    -- AI performance
    ai_accuracy_score DECIMAL(3,2),               -- Quality of AI responses
    total_ai_cost DECIMAL(8,6),                   -- Total cost of AI processing
    average_response_time DECIMAL(5,2),            -- Average AI response time
    
    -- Calculated at session end
    calculated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_intelligent_sessions_user_active 
    ON selfology_intelligent_sessions(user_id, last_activity) 
    WHERE session_ended IS NULL;

CREATE INDEX IF NOT EXISTS idx_question_answers_current 
    ON selfology_question_answers(user_id, question_id) 
    WHERE is_current = true;

CREATE INDEX IF NOT EXISTS idx_chat_insights_domain_active 
    ON selfology_chat_insights(user_id, psychological_domain) 
    WHERE is_active = true;

CREATE INDEX IF NOT EXISTS idx_vector_evolution_timeline 
    ON selfology_vector_evolution(user_id, vector_version, created_at);

-- Create triggers for automatic timestamps
CREATE OR REPLACE FUNCTION update_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER trigger_user_statements_updated_at 
    BEFORE UPDATE ON selfology_user_statements 
    FOR EACH ROW EXECUTE FUNCTION update_timestamp();

-- Create function for session activity updates
CREATE OR REPLACE FUNCTION update_session_activity()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE selfology_intelligent_sessions 
    SET last_activity = NOW() 
    WHERE user_id = NEW.user_id;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER trigger_update_session_activity_on_answer
    AFTER INSERT ON selfology_question_answers
    FOR EACH ROW EXECUTE FUNCTION update_session_activity();

CREATE TRIGGER trigger_update_session_activity_on_insight  
    AFTER INSERT ON selfology_chat_insights
    FOR EACH ROW EXECUTE FUNCTION update_session_activity();
"""

async def create_enhanced_tables():
    """Create enhanced tables for intelligent memory system"""
    
    try:
        print("🗄️  Creating enhanced database tables...")
        
        conn = await asyncpg.connect(**DB_CONFIG)
        
        # Execute table creation
        await conn.execute(ENHANCED_TABLES_SQL)
        
        print("✅ Enhanced tables created successfully!")
        
        # Verify tables
        tables = await conn.fetch("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_name LIKE 'selfology_%' 
            AND table_schema = 'public'
            ORDER BY table_name
        """)
        
        print(f"📊 Available tables:")
        for table in tables:
            print(f"   • {table['table_name']}")
        
        await conn.close()
        
    except Exception as e:
        print(f"❌ Failed to create enhanced tables: {e}")
        return False
    
    return True

async def check_table_structure():
    """Check structure of created tables"""
    
    try:
        conn = await asyncpg.connect(**DB_CONFIG)
        
        # Check enhanced tables
        enhanced_tables = [
            'selfology_intelligent_sessions',
            'selfology_question_answers', 
            'selfology_chat_insights',
            'selfology_user_statements',
            'selfology_vector_evolution',
            'selfology_session_analytics'
        ]
        
        for table_name in enhanced_tables:
            print(f"\n📋 Table: {table_name}")
            
            columns = await conn.fetch(f"""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns 
                WHERE table_name = '{table_name}'
                ORDER BY ordinal_position
            """)
            
            for col in columns:
                nullable = "NULL" if col['is_nullable'] == 'YES' else "NOT NULL"
                default = f" DEFAULT {col['column_default']}" if col['column_default'] else ""
                print(f"   {col['column_name']:<25} {col['data_type']:<20} {nullable}{default}")
        
        await conn.close()
        
    except Exception as e:
        print(f"❌ Failed to check table structure: {e}")

if __name__ == "__main__":
    print("🧠 ENHANCED MEMORY SYSTEM - Database Setup")
    print("=" * 60)
    
    async def main():
        if await create_enhanced_tables():
            print("\n🔍 Checking table structure...")
            await check_table_structure()
            print("\n🎉 Enhanced memory system database ready!")
        else:
            print("\n😞 Setup failed.")
    
    asyncio.run(main())