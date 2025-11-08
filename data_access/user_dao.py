"""
User Data Access Object - Clean database operations for user management
"""
import asyncpg
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
import json

from core.config import get_config
from core.logging import get_logger


class UserDAO:
    """Data Access Object for user operations"""

    def __init__(self, db_pool: Optional[asyncpg.Pool] = None):
        self.db_pool = db_pool
        self.config = get_config()
        self.logger = get_logger("selfology.user_dao", "user_service")

    async def get_or_create_user(self, telegram_id: str, telegram_data: Dict[str, Any]) -> Dict[str, Any]:
        """Get existing user or create new one"""

        async with self.db_pool.acquire() as conn:
            # Try to get existing user
            user = await conn.fetchrow("""
                SELECT * FROM selfology_users WHERE telegram_id = $1
            """, telegram_id)

            if user:
                # Update last active
                await conn.execute("""
                    UPDATE selfology_users
                    SET last_active = NOW(),
                        username = $2,
                        first_name = $3,
                        last_name = $4
                    WHERE telegram_id = $1
                """, telegram_id,
                    telegram_data.get("username"),
                    telegram_data.get("first_name"),
                    telegram_data.get("last_name"))

                self.logger.log_user_action("user_activity_updated", telegram_id)
                return dict(user)

            # Create new user
            new_user = await conn.fetchrow("""
                INSERT INTO selfology_users
                (telegram_id, username, first_name, last_name, last_active, created_at)
                VALUES ($1, $2, $3, $4, NOW(), NOW())
                RETURNING *
            """, telegram_id,
                telegram_data.get("username"),
                telegram_data.get("first_name"),
                telegram_data.get("last_name"))

            self.logger.log_user_action("user_created", telegram_id)
            return dict(new_user)

    async def update_user_consent(self, telegram_id: str, gdpr_consent: bool) -> bool:
        """Update user GDPR consent"""

        async with self.db_pool.acquire() as conn:
            result = await conn.execute("""
                UPDATE selfology_users
                SET gdpr_consent = $1, updated_at = NOW()
                WHERE telegram_id = $2
            """, gdpr_consent, telegram_id)

            success = result == "UPDATE 1"
            if success:
                self.logger.log_user_action("gdpr_consent_updated", telegram_id, consent=gdpr_consent)

            return success

    async def update_onboarding_status(self, telegram_id: str, completed: bool = True) -> bool:
        """Update user onboarding completion status"""

        async with self.db_pool.acquire() as conn:
            result = await conn.execute("""
                UPDATE selfology_users
                SET onboarding_completed = $1, updated_at = NOW()
                WHERE telegram_id = $2
            """, completed, telegram_id)

            success = result == "UPDATE 1"
            if success:
                self.logger.log_user_action("onboarding_status_updated", telegram_id, completed=completed)

            return success

    async def update_user_tier(self, telegram_id: str, tier: str) -> bool:
        """Update user tier (free, premium, professional)"""

        async with self.db_pool.acquire() as conn:
            result = await conn.execute("""
                UPDATE selfology_users
                SET tier = $1, updated_at = NOW()
                WHERE telegram_id = $2
            """, tier, telegram_id)

            success = result == "UPDATE 1"
            if success:
                self.logger.log_user_action("user_tier_updated", telegram_id, tier=tier)

            return success

    async def get_user_profile(self, telegram_id: str) -> Optional[Dict[str, Any]]:
        """Get complete user profile with related data"""

        async with self.db_pool.acquire() as conn:
            # Get basic user data
            user = await conn.fetchrow("""
                SELECT * FROM selfology_users WHERE telegram_id = $1
            """, telegram_id)

            if not user:
                return None

            # Get question statistics
            question_stats = await conn.fetchrow("""
                SELECT
                    COUNT(*) as total_answers,
                    COUNT(DISTINCT DATE(answered_at)) as active_days,
                    -- Note: confidence_score removed - not in selfology_question_answers schema
                    MIN(answered_at) as first_answer,
                    MAX(answered_at) as last_answer
                FROM selfology_question_answers
                WHERE user_id = $1
            """, telegram_id)

            # Get recent chat activity
            chat_stats = await conn.fetchrow("""
                SELECT
                    COUNT(*) as total_messages,
                    COUNT(*) FILTER (WHERE message_type = 'user') as user_messages,
                    COUNT(*) FILTER (WHERE message_type = 'assistant') as ai_responses,
                    MAX(timestamp) as last_chat
                FROM selfology_chat_messages
                WHERE user_id = $1
            """, telegram_id)

            # Get personality vector info
            vector_info = await conn.fetchrow("""
                SELECT
                    vector_version,
                    confidence_score,
                    created_at as vector_created,
                    qdrant_point_id
                FROM selfology_personality_vectors
                WHERE user_id = $1
                ORDER BY vector_version DESC
                LIMIT 1
            """, telegram_id)

            return {
                "user": dict(user),
                "assessment_stats": dict(question_stats) if question_stats else {},
                "chat_stats": dict(chat_stats) if chat_stats else {},
                "personality_vector": dict(vector_info) if vector_info else {}
            }

    async def save_chat_message(self, telegram_id: str, content: str, message_type: str,
                               ai_model_used: Optional[str] = None, insights: Optional[Dict] = None,
                               response_time: Optional[float] = None) -> int:
        """Save chat message to history"""

        async with self.db_pool.acquire() as conn:
            message_id = await conn.fetchval("""
                INSERT INTO selfology_chat_messages
                (user_id, content, message_type, ai_model_used, insights, response_time_ms, timestamp)
                VALUES ($1, $2, $3, $4, $5, $6, NOW())
                RETURNING id
            """, telegram_id, content, message_type, ai_model_used,
                json.dumps(insights) if insights else None,
                round(response_time * 1000) if response_time else None)

            self.logger.log_user_action("chat_message_saved", telegram_id,
                                       message_type=message_type, message_id=message_id)
            return message_id

    async def get_recent_chat_history(self, telegram_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent chat history for context"""

        async with self.db_pool.acquire() as conn:
            messages = await conn.fetch("""
                SELECT * FROM selfology_chat_messages
                WHERE user_id = $1
                ORDER BY timestamp DESC
                LIMIT $2
            """, telegram_id, limit)

            # Return in chronological order (oldest first)
            return [dict(msg) for msg in reversed(messages)]

    async def save_user_insight(self, telegram_id: str, insight_text: str, insight_type: str,
                               psychological_domain: Optional[str] = None,
                               confidence: Optional[float] = None) -> int:
        """Save user insight from chat or analysis"""

        async with self.db_pool.acquire() as conn:
            insight_id = await conn.fetchval("""
                INSERT INTO selfology_chat_insights
                (user_id, insight_text, insight_type, psychological_domain, confidence_score, created_at)
                VALUES ($1, $2, $3, $4, $5, NOW())
                RETURNING id
            """, telegram_id, insight_text, insight_type, psychological_domain, confidence)

            self.logger.log_user_action("insight_saved", telegram_id,
                                       insight_type=insight_type, insight_id=insight_id)
            return insight_id

    async def get_user_insights(self, telegram_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Get user insights for coaching context"""

        async with self.db_pool.acquire() as conn:
            insights = await conn.fetch("""
                SELECT * FROM selfology_chat_insights
                WHERE user_id = $1
                ORDER BY created_at DESC
                LIMIT $2
            """, telegram_id, limit)

            return [dict(insight) for insight in insights]

    async def save_personality_vector(self, telegram_id: str, traits: Dict[str, Any],
                                    confidence_score: Optional[float] = None,
                                    qdrant_point_id: Optional[str] = None,
                                    source_data: Optional[str] = None) -> Dict[str, Any]:
        """Save personality vector data"""

        async with self.db_pool.acquire() as conn:
            # Get current version
            current_version = await conn.fetchval("""
                SELECT MAX(vector_version) FROM selfology_personality_vectors
                WHERE user_id = $1
            """, telegram_id) or 0

            new_version = current_version + 1

            vector_record = await conn.fetchrow("""
                INSERT INTO selfology_personality_vectors
                (user_id, vector_version, traits, confidence_score, qdrant_point_id, source_data, created_at)
                VALUES ($1, $2, $3, $4, $5, $6, NOW())
                RETURNING *
            """, telegram_id, new_version, json.dumps(traits), confidence_score, qdrant_point_id, source_data)

            self.logger.log_user_action("personality_vector_saved", telegram_id,
                                       version=new_version, vector_id=vector_record["id"])
            return dict(vector_record)

    async def get_latest_personality_vector(self, telegram_id: str) -> Optional[Dict[str, Any]]:
        """Get user's latest personality vector"""

        async with self.db_pool.acquire() as conn:
            vector = await conn.fetchrow("""
                SELECT * FROM selfology_personality_vectors
                WHERE user_id = $1
                ORDER BY vector_version DESC
                LIMIT 1
            """, telegram_id)

            if vector:
                vector_dict = dict(vector)
                # Parse traits JSON
                if vector_dict.get("traits"):
                    try:
                        vector_dict["traits"] = json.loads(vector_dict["traits"])
                    except json.JSONDecodeError:
                        vector_dict["traits"] = {}

                return vector_dict

            return None

    async def get_onboarding_answers(self, telegram_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get user's onboarding answers with question context

        Returns answers from most recent completed or active session

        FIXED:
        1. telegram_id конвертируется в int для совместимости с onboarding_sessions.user_id (INTEGER)
        2. Обновлены поля из answer_analysis согласно новой схеме (psychological_insights вместо ai_interpretation)
        """
        async with self.db_pool.acquire() as conn:
            # КРИТИЧНО: Конвертируем telegram_id в int для совместимости с onboarding_sessions.user_id (INTEGER)
            try:
                user_id_int = int(telegram_id)
            except (ValueError, TypeError):
                self.logger.warning(f"Invalid telegram_id for onboarding answers: {telegram_id}")
                return []

            # Get most recent session for this user
            session = await conn.fetchrow("""
                SELECT id FROM selfology.onboarding_sessions
                WHERE user_id = $1
                ORDER BY started_at DESC
                LIMIT 1
            """, user_id_int)

            if not session:
                return []

            # Get answers from this session with updated schema
            answers = await conn.fetch("""
                SELECT
                    a.question_json_id,
                    a.raw_answer,
                    a.answered_at,
                    aa.psychological_insights,
                    aa.trait_scores,
                    aa.emotional_state,
                    aa.confidence_score
                FROM selfology.user_answers_new a
                LEFT JOIN selfology.answer_analysis aa ON a.id = aa.user_answer_id
                WHERE a.session_id = $1
                ORDER BY a.answered_at DESC
                LIMIT $2
            """, session['id'], limit)

            return [dict(answer) for answer in answers]

    async def get_context_stories(self, telegram_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get user's context stories (специальные вопросы: цели, дилеммы, контекст)

        Returns most recent active stories of type 'onboarding_context'
        """
        async with self.db_pool.acquire() as conn:
            try:
                user_id_int = int(telegram_id)
            except (ValueError, TypeError):
                self.logger.warning(f"Invalid telegram_id for context stories: {telegram_id}")
                return []

            stories = await conn.fetch("""
                SELECT
                    id,
                    story_text,
                    story_type,
                    metadata,
                    created_at
                FROM selfology.user_context_stories
                WHERE user_id = $1 AND is_active = TRUE
                ORDER BY created_at DESC
                LIMIT $2
            """, user_id_int, limit)

            return [dict(story) for story in stories]

    async def update_user_activity(self, telegram_id: str, activity_type: str, metadata: Optional[Dict] = None):
        """Update user last activity and log activity type"""

        async with self.db_pool.acquire() as conn:
            # Update last active timestamp
            await conn.execute("""
                UPDATE selfology_users
                SET last_active = NOW()
                WHERE telegram_id = $1
            """, telegram_id)

            # Log activity
            await conn.execute("""
                INSERT INTO selfology_user_activity_log
                (user_id, activity_type, metadata, timestamp)
                VALUES ($1, $2, $3, NOW())
            """, telegram_id, activity_type, json.dumps(metadata) if metadata else None)

            self.logger.log_user_action("user_activity_logged", telegram_id,
                                       activity_type=activity_type)

    async def get_user_activity_summary(self, telegram_id: str, days: int = 30) -> Dict[str, Any]:
        """Get user activity summary for specified days"""

        async with self.db_pool.acquire() as conn:
            # Activity counts by type
            activity_counts = await conn.fetch("""
                SELECT
                    activity_type,
                    COUNT(*) as count,
                    MAX(timestamp) as last_occurrence
                FROM selfology_user_activity_log
                WHERE user_id = $1 AND timestamp >= NOW() - INTERVAL '%s days'
                GROUP BY activity_type
                ORDER BY count DESC
            """, telegram_id, days)

            # Daily activity
            daily_activity = await conn.fetch("""
                SELECT
                    DATE(timestamp) as date,
                    COUNT(*) as activities
                FROM selfology_user_activity_log
                WHERE user_id = $1 AND timestamp >= NOW() - INTERVAL '%s days'
                GROUP BY DATE(timestamp)
                ORDER BY date DESC
            """, telegram_id, days)

            return {
                "activity_by_type": [dict(row) for row in activity_counts],
                "daily_activity": [dict(row) for row in daily_activity],
                "period_days": days
            }

    async def get_user_statistics(self) -> Dict[str, Any]:
        """Get system-wide user statistics"""

        async with self.db_pool.acquire() as conn:
            # Basic user stats
            basic_stats = await conn.fetchrow("""
                SELECT
                    COUNT(*) as total_users,
                    COUNT(*) FILTER (WHERE gdpr_consent = true) as consented_users,
                    COUNT(*) FILTER (WHERE onboarding_completed = true) as completed_users,
                    COUNT(*) FILTER (WHERE last_active >= NOW() - INTERVAL '7 days') as active_weekly,
                    COUNT(*) FILTER (WHERE last_active >= NOW() - INTERVAL '24 hours') as active_daily
                FROM selfology_users
            """)

            # User tiers
            tier_stats = await conn.fetch("""
                SELECT
                    COALESCE(tier, 'unknown') as tier,
                    COUNT(*) as count
                FROM selfology_users
                GROUP BY tier
                ORDER BY count DESC
            """)

            # Registration trends
            registration_trends = await conn.fetch("""
                SELECT
                    DATE(created_at) as date,
                    COUNT(*) as new_users
                FROM selfology_users
                WHERE created_at >= NOW() - INTERVAL '30 days'
                GROUP BY DATE(created_at)
                ORDER BY date DESC
            """)

            return {
                "basic_stats": dict(basic_stats) if basic_stats else {},
                "tier_distribution": [dict(row) for row in tier_stats],
                "registration_trends": [dict(row) for row in registration_trends]
            }
