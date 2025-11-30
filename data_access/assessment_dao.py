"""
Assessment Data Access Object - Clean database operations for assessments
"""
import asyncpg
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timezone
import json

from core.config import get_config
from core.logging import assessment_logger


class AssessmentDAO:
    """Data Access Object for assessment operations"""
    
    def __init__(self, db_pool: Optional[asyncpg.Pool] = None):
        self.db_pool = db_pool
        self.config = get_config()
        self.logger = assessment_logger
    
    async def create_user_profile(self, user_id: str, telegram_data: Dict[str, Any]) -> int:
        """Create new user profile if doesn't exist"""
        
        async with self.db_pool.acquire() as conn:
            # Check if user exists
            existing = await conn.fetchval("""
                SELECT id FROM selfology_users WHERE telegram_id = $1
            """, user_id)
            
            if existing:
                return existing
            
            # Create new user
            user_record_id = await conn.fetchval("""
                INSERT INTO selfology_users 
                (telegram_id, username, first_name, last_name, last_active, gdpr_consent)
                VALUES ($1, $2, $3, $4, $5, $6)
                RETURNING id
            """, 
            user_id, 
            telegram_data.get("username"),
            telegram_data.get("first_name"),
            telegram_data.get("last_name"),
            datetime.now(timezone.utc),
            False)
            
            self.logger.log_user_action("user_created", user_id)
            return user_record_id
    
    async def get_user_by_telegram_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user data by telegram ID"""
        
        async with self.db_pool.acquire() as conn:
            user = await conn.fetchrow("""
                SELECT * FROM selfology_users WHERE telegram_id = $1
            """, user_id)
            
            return dict(user) if user else None
    
    async def update_user_consent(self, user_id: str, consent: bool) -> bool:
        """Update user GDPR consent"""
        
        async with self.db_pool.acquire() as conn:
            result = await conn.execute("""
                UPDATE selfology_users 
                SET gdpr_consent = $1, updated_at = NOW()
                WHERE telegram_id = $2
            """, consent, user_id)
            
            success = result == "UPDATE 1"
            if success:
                self.logger.log_user_action("gdpr_consent_updated", user_id, consent=consent)
            
            return success
    
    async def start_question_session(self, user_id: str, initial_state: Dict[str, Any]) -> str:
        """Start new question session - FIXED: No session-based approach"""
        
        # Instead of creating sessions, we track user progress directly
        async with self.db_pool.acquire() as conn:
            # Clear any existing incomplete progress for fresh start
            await conn.execute("""
                DELETE FROM selfology_user_question_progress 
                WHERE user_id = $1 AND session_completed = false
            """, user_id)
            
            # Create new progress tracking
            progress_id = await conn.fetchval("""
                INSERT INTO selfology_user_question_progress
                (user_id, current_energy, trust_level, questions_completed, session_completed)
                VALUES ($1, $2, $3, $4, false)
                RETURNING id
            """, user_id, initial_state.get("energy", 0.3), initial_state.get("trust", 1.0), json.dumps([]))
            
            self.logger.log_user_action("assessment_started", user_id, progress_id=progress_id)
            return str(progress_id)
    
    async def save_question_answer(self, user_id: str, question_id: str, 
                                  answer_text: str, analysis: Dict[str, Any]) -> int:
        """Save individual question answer with analysis"""
        
        async with self.db_pool.acquire() as conn:
            answer_id = await conn.fetchval("""
                INSERT INTO selfology_question_answers
                (user_id, question_id, answer_text, answer_analysis, 
                 ai_model_used, confidence_score, answered_at)
                VALUES ($1, $2, $3, $4, $5, $6, NOW())
                RETURNING id
            """,
            user_id,
            question_id, 
            answer_text,
            json.dumps(analysis),
            analysis.get("ai_model_used", "unknown"),
            analysis.get("confidence_score", 0.5))
            
            # Update user progress - add question to completed list
            await conn.execute("""
                UPDATE selfology_user_question_progress 
                SET questions_completed = questions_completed || $1,
                    current_energy = $2,
                    trust_level = $3,
                    last_activity = NOW()
                WHERE user_id = $4 AND session_completed = false
            """, json.dumps([question_id]), 
                analysis.get("new_energy_level", 0.3),
                analysis.get("new_trust_level", 1.0),
                user_id)
            
            self.logger.log_user_action("question_answered", user_id, 
                                       question_id=question_id, answer_id=answer_id)
            return answer_id
    
    async def get_user_completed_questions(self, user_id: str) -> List[str]:
        """Get list of questions already completed by user - NO SESSIONS"""
        
        async with self.db_pool.acquire() as conn:
            # Get all questions this user has ever answered (not session-based)
            question_ids = await conn.fetch("""
                SELECT DISTINCT question_id 
                FROM selfology_question_answers 
                WHERE user_id = $1
                ORDER BY answered_at DESC
            """, user_id)
            
            return [row["question_id"] for row in question_ids]
    
    async def get_user_assessment_state(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get current assessment state for user"""
        
        async with self.db_pool.acquire() as conn:
            # Get current progress (not session-based)
            progress = await conn.fetchrow("""
                SELECT * FROM selfology_user_question_progress
                WHERE user_id = $1 AND session_completed = false
                ORDER BY created_at DESC
                LIMIT 1
            """, user_id)
            
            if not progress:
                return None
            
            # Get total answers count
            total_answers = await conn.fetchval("""
                SELECT COUNT(*) FROM selfology_question_answers
                WHERE user_id = $1
            """, user_id)
            
            completed_questions = json.loads(progress["questions_completed"]) if progress["questions_completed"] else []
            
            return {
                "progress_id": progress["id"],
                "current_energy": float(progress["current_energy"]),
                "trust_level": float(progress["trust_level"]),
                "questions_completed": completed_questions,
                "total_answers": total_answers,
                "created_at": progress["created_at"],
                "last_activity": progress["last_activity"]
            }
    
    async def complete_assessment(self, user_id: str) -> bool:
        """Mark assessment as completed"""
        
        async with self.db_pool.acquire() as conn:
            # Mark progress as completed
            result = await conn.execute("""
                UPDATE selfology_user_question_progress
                SET session_completed = true, completed_at = NOW()
                WHERE user_id = $1 AND session_completed = false
            """, user_id)
            
            # Update user onboarding status
            await conn.execute("""
                UPDATE selfology_users
                SET onboarding_completed = true, updated_at = NOW()
                WHERE telegram_id = $1
            """, user_id)
            
            success = result == "UPDATE 1"
            if success:
                self.logger.log_user_action("assessment_completed", user_id)
            
            return success
    
    async def get_user_answer_statistics(self, user_id: str) -> Dict[str, Any]:
        """Get comprehensive answer statistics for user"""
        
        async with self.db_pool.acquire() as conn:
            # Basic stats
            basic_stats = await conn.fetchrow("""
                SELECT 
                    COUNT(*) as total_answers,
                    AVG(confidence_score) as avg_confidence,
                    MIN(answered_at) as first_answer,
                    MAX(answered_at) as last_answer
                FROM selfology_question_answers
                WHERE user_id = $1
            """, user_id)
            
            # Domain coverage (requires question core integration)
            domain_stats = await conn.fetch("""
                SELECT 
                    SUBSTRING(question_id FROM '^[A-Z]+') as domain_prefix,
                    COUNT(*) as count
                FROM selfology_question_answers
                WHERE user_id = $1
                GROUP BY domain_prefix
                ORDER BY count DESC
            """, user_id)
            
            # Analysis insights
            insights = await conn.fetch("""
                SELECT 
                    answer_analysis,
                    answered_at
                FROM selfology_question_answers
                WHERE user_id = $1 AND answer_analysis IS NOT NULL
                ORDER BY answered_at DESC
                LIMIT 10
            """, user_id)
            
            # Process insights
            parsed_insights = []
            for insight in insights:
                if insight["answer_analysis"]:
                    try:
                        analysis = json.loads(insight["answer_analysis"])
                        parsed_insights.append({
                            "date": insight["answered_at"],
                            "emotional_state": analysis.get("emotional_state"),
                            "openness_level": analysis.get("openness_level"),
                            "key_insights": analysis.get("key_insights", [])
                        })
                    except json.JSONDecodeError:
                        continue
            
            return {
                "basic_stats": dict(basic_stats) if basic_stats else {},
                "domain_coverage": [dict(row) for row in domain_stats],
                "recent_insights": parsed_insights,
                "assessment_complete": basic_stats["total_answers"] > 0 if basic_stats else False
            }
    
    async def cleanup_incomplete_sessions(self, older_than_hours: int = 24) -> int:
        """Clean up incomplete assessment sessions older than specified hours"""
        
        async with self.db_pool.acquire() as conn:
            result = await conn.execute("""
                DELETE FROM selfology_user_question_progress
                WHERE session_completed = false 
                AND created_at < NOW() - INTERVAL '%s hours'
            """, older_than_hours)
            
            cleaned_count = int(result.split()[-1]) if result.split() else 0
            if cleaned_count > 0:
                self.logger.info(f"Cleaned up {cleaned_count} incomplete assessment sessions")
            
            return cleaned_count
    
    async def get_assessment_analytics(self) -> Dict[str, Any]:
        """Get system-wide assessment analytics"""
        
        async with self.db_pool.acquire() as conn:
            # Overall statistics
            overall = await conn.fetchrow("""
                SELECT 
                    COUNT(DISTINCT user_id) as total_users,
                    COUNT(*) as total_answers,
                    AVG(confidence_score) as avg_confidence,
                    COUNT(DISTINCT DATE(answered_at)) as active_days
                FROM selfology_question_answers
                WHERE answered_at >= NOW() - INTERVAL '30 days'
            """)
            
            # Completion rates
            completion = await conn.fetchrow("""
                SELECT 
                    COUNT(*) FILTER (WHERE onboarding_completed = true) as completed_users,
                    COUNT(*) as total_users,
                    ROUND(
                        COUNT(*) FILTER (WHERE onboarding_completed = true) * 100.0 / 
                        NULLIF(COUNT(*), 0), 2
                    ) as completion_rate
                FROM selfology_users
                WHERE gdpr_consent = true
            """)
            
            # Daily activity
            daily_activity = await conn.fetch("""
                SELECT 
                    DATE(answered_at) as date,
                    COUNT(*) as answers,
                    COUNT(DISTINCT user_id) as active_users
                FROM selfology_question_answers
                WHERE answered_at >= NOW() - INTERVAL '7 days'
                GROUP BY DATE(answered_at)
                ORDER BY date DESC
            """)
            
            return {
                "overall_stats": dict(overall) if overall else {},
                "completion_metrics": dict(completion) if completion else {},
                "daily_activity": [dict(row) for row in daily_activity]
            }