#!/usr/bin/env python3
"""
Database setup script for Selfology bot.
Creates necessary tables in the existing n8n PostgreSQL database.
"""

import asyncio
import asyncpg
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Database connection details (using existing n8n database)
DB_CONFIG = {
    "host": "localhost",  # Will be n8n-postgres in container
    "port": 5432,
    "user": "n8n",
    "password": "sS67wM+1zMBRFHAW4kj9HwFl5J6+veo7Nirx0/I+oiU=",
    "database": "n8n"
}

# SQL for creating Selfology tables
CREATE_TABLES_SQL = """
-- Users table for Selfology bot
CREATE TABLE IF NOT EXISTS selfology_users (
    id SERIAL PRIMARY KEY,
    telegram_id VARCHAR(50) UNIQUE NOT NULL,
    username VARCHAR(100),
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    
    -- User tier and state
    tier VARCHAR(20) DEFAULT 'free',
    onboarding_completed BOOLEAN DEFAULT false,
    current_state VARCHAR(50),
    
    -- Privacy settings
    privacy_level VARCHAR(20) DEFAULT 'balanced',
    gdpr_consent BOOLEAN DEFAULT false,
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_active TIMESTAMP WITH TIME ZONE
);

-- Questionnaires table
CREATE TABLE IF NOT EXISTS selfology_questionnaires (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(50) REFERENCES selfology_users(telegram_id),
    questionnaire_type VARCHAR(50) NOT NULL,
    responses JSONB NOT NULL,
    completed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    vector_id VARCHAR(100)
);

-- Chat history table  
CREATE TABLE IF NOT EXISTS selfology_chat_history (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(50) REFERENCES selfology_users(telegram_id),
    message_type VARCHAR(20) DEFAULT 'user',
    content TEXT NOT NULL,
    ai_model_used VARCHAR(50),
    cost_estimate VARCHAR(20),
    
    -- AI analysis and insights
    insights JSONB,
    personality_updates JSONB,
    vector_updated BOOLEAN DEFAULT false,
    
    -- Metadata
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Personality vectors table
CREATE TABLE IF NOT EXISTS selfology_personality_vectors (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(50) REFERENCES selfology_users(telegram_id),
    vector_version INTEGER DEFAULT 1,
    
    -- Personality traits
    traits JSONB NOT NULL,
    confidence_score VARCHAR(10),
    
    -- Vector metadata  
    qdrant_point_id VARCHAR(100),
    source_data VARCHAR(100),
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_selfology_users_telegram_id ON selfology_users(telegram_id);
CREATE INDEX IF NOT EXISTS idx_selfology_chat_user_id ON selfology_chat_history(user_id);
CREATE INDEX IF NOT EXISTS idx_selfology_chat_timestamp ON selfology_chat_history(timestamp);
CREATE INDEX IF NOT EXISTS idx_selfology_vectors_user_id ON selfology_personality_vectors(user_id);

-- Create triggers for updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_selfology_users_updated_at 
    BEFORE UPDATE ON selfology_users 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_selfology_personality_vectors_updated_at 
    BEFORE UPDATE ON selfology_personality_vectors 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
"""

async def setup_database():
    """Set up database tables for Selfology bot."""
    
    try:
        print("🔗 Connecting to PostgreSQL...")
        conn = await asyncpg.connect(**DB_CONFIG)
        
        print("📋 Creating Selfology tables...")
        await conn.execute(CREATE_TABLES_SQL)
        
        print("✅ Database setup completed successfully!")
        
        # Verify tables were created
        result = await conn.fetch("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_name LIKE 'selfology_%' AND table_schema = 'public'
        """)
        
        print(f"📊 Created tables: {[r['table_name'] for r in result]}")
        
        await conn.close()
        
    except Exception as e:
        print(f"❌ Database setup failed: {e}")
        return False
    
    return True

async def check_database_connection():
    """Check if database is accessible."""
    
    try:
        print("🔍 Checking database connection...")
        conn = await asyncpg.connect(**DB_CONFIG)
        
        # Test query
        result = await conn.fetchval("SELECT version()")
        print(f"✅ Connected to: {result}")
        
        await conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Selfology Database Setup")
    print("=" * 50)
    
    async def main():
        # Check connection first
        if not await check_database_connection():
            print("\n💡 If running in Docker, make sure containers are on the same network")
            return
        
        # Setup tables
        if await setup_database():
            print("\n🎉 Setup completed! Ready to start Selfology bot.")
        else:
            print("\n😞 Setup failed. Please check the error messages above.")
    
    asyncio.run(main())