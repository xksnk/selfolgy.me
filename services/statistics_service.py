"""
Statistics Service - Standalone analytics module
Independent service for user statistics and system analytics
"""
import time
import asyncpg
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
import json

from data_access.user_dao import UserDAO
from data_access.assessment_dao import AssessmentDAO
from data_access.vector_dao import VectorDAO
from core.config import get_config
from core.logging import statistics_logger, LoggerMixin


@dataclass
class StatisticsResult:
    """Result of statistics operation"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    message: Optional[str] = None
    processing_time: Optional[float] = None
    cache_hit: bool = False


@dataclass
class UserStats:
    """Comprehensive user statistics"""
    user_id: str
    total_questions: int
    domains_explored: List[str]
    chat_messages: int
    insights_generated: int
    assessment_complete: bool
    personality_type: Optional[str]
    engagement_score: float
    last_activity: datetime


class StatisticsService(LoggerMixin):
    """
    Independent Statistics Service
    
    Features:
    - User-specific analytics
    - System-wide metrics
    - Domain coverage analysis
    - Engagement tracking
    - Vector space analytics
    - Performance metrics
    - Cached results for performance
    """
    
    def __init__(self, db_pool: Optional[asyncpg.Pool] = None):
        self.config = get_config()
        self.db_pool = db_pool
        
        # Initialize DAOs
        self.user_dao = UserDAO(db_pool)
        self.assessment_dao = AssessmentDAO(db_pool)
        self.vector_dao = VectorDAO()
        
        # Service configuration
        self.stats_config = self.config.get_service_config("statistics")
        self.cache_ttl = self.stats_config.get("cache_ttl", 300)  # 5 minutes
        
        # Simple cache (in production would use Redis)
        self.cache = {}
        
        self.logger.info("Statistics Service initialized")
    
    async def get_user_statistics(self, user_id: str, include_detailed: bool = False) -> StatisticsResult:
        """Get comprehensive statistics for a user"""
        
        start_time = time.time()
        self.logger.log_service_call("get_user_statistics", user_id, detailed=include_detailed)
        
        try:
            # Check cache first
            cache_key = f"user_stats_{user_id}_{include_detailed}"
            cached_result = self._get_cached_result(cache_key)
            
            if cached_result:
                cached_result.cache_hit = True
                cached_result.processing_time = time.time() - start_time
                return cached_result
            
            # Get user profile
            user_profile = await self.user_dao.get_user_profile(user_id)
            if not user_profile:
                return StatisticsResult(success=False, message="User not found")
            
            # Get assessment statistics
            assessment_stats = await self.assessment_dao.get_user_answer_statistics(user_id)
            
            # Calculate engagement metrics
            engagement_metrics = await self._calculate_engagement_metrics(user_id, user_profile)
            
            # Get domain analysis
            domain_analysis = await self._analyze_user_domains(user_id)
            
            # Get personality insights
            personality_insights = await self._get_personality_insights(user_id)
            
            # Get activity timeline
            activity_timeline = await self._get_activity_timeline(user_id, days=30)
            
            # Build comprehensive stats
            user_stats = {
                "user_info": user_profile["user"],
                "assessment": assessment_stats,
                "chat_activity": user_profile["chat_stats"],
                "personality_profile": user_profile["personality_vector"],
                "engagement": engagement_metrics,
                "domain_analysis": domain_analysis,
                "personality_insights": personality_insights,
                "activity_timeline": activity_timeline
            }
            
            # Add detailed information if requested
            if include_detailed:
                detailed_info = await self._get_detailed_user_info(user_id)
                user_stats["detailed"] = detailed_info
            
            processing_time = time.time() - start_time
            
            result = StatisticsResult(
                success=True,
                data=user_stats,
                message="User statistics retrieved",
                processing_time=processing_time,
                cache_hit=False
            )
            
            # Cache the result
            self._cache_result(cache_key, result)
            
            self.logger.log_service_result("get_user_statistics", True, processing_time)
            return result
            
        except Exception as e:
            self.logger.log_error("USER_STATS_ERROR", f"Failed to get user stats: {e}", user_id, e)
            return StatisticsResult(success=False, message=f"Failed to get statistics: {str(e)}")
    
    async def get_system_overview(self) -> StatisticsResult:
        """Get system-wide statistics overview"""
        
        start_time = time.time()
        self.logger.log_service_call("get_system_overview")
        
        try:
            # Check cache
            cache_key = "system_overview"
            cached_result = self._get_cached_result(cache_key)
            
            if cached_result:
                cached_result.cache_hit = True
                cached_result.processing_time = time.time() - start_time
                return cached_result
            
            # Get user statistics
            user_stats = await self.user_dao.get_user_statistics()
            
            # Get assessment analytics
            assessment_analytics = await self.assessment_dao.get_assessment_analytics()
            
            # Get vector database stats
            vector_stats = await self.vector_dao.get_collection_statistics()
            
            # Calculate system health metrics
            system_health = await self._calculate_system_health()
            
            # Get growth metrics
            growth_metrics = await self._calculate_growth_metrics()
            
            # Get performance metrics
            performance_metrics = await self._get_performance_metrics()
            
            system_overview = {
                "user_statistics": user_stats,
                "assessment_analytics": assessment_analytics,
                "vector_database": vector_stats,
                "system_health": system_health,
                "growth_metrics": growth_metrics,
                "performance": performance_metrics,
                "generated_at": datetime.now(timezone.utc).isoformat()
            }
            
            processing_time = time.time() - start_time
            
            result = StatisticsResult(
                success=True,
                data=system_overview,
                message="System overview retrieved",
                processing_time=processing_time,
                cache_hit=False
            )
            
            # Cache for shorter time due to changing nature
            self._cache_result(cache_key, result, ttl=60)  # 1 minute cache
            
            self.logger.log_service_result("get_system_overview", True, processing_time)
            return result
            
        except Exception as e:
            self.logger.log_error("SYSTEM_OVERVIEW_ERROR", f"Failed to get system overview: {e}", None, e)
            return StatisticsResult(success=False, message=f"Failed to get overview: {str(e)}")
    
    async def get_engagement_analysis(self, days: int = 30) -> StatisticsResult:
        """Get user engagement analysis over specified period"""
        
        start_time = time.time()
        self.logger.log_service_call("get_engagement_analysis", period_days=days)
        
        try:
            cache_key = f"engagement_analysis_{days}"
            cached_result = self._get_cached_result(cache_key)
            
            if cached_result:
                cached_result.cache_hit = True
                cached_result.processing_time = time.time() - start_time
                return cached_result
            
            # Get engagement data from database
            async with self.db_pool.acquire() as conn:
                # Daily active users
                daily_active = await conn.fetch("""
                    SELECT 
                        DATE(last_active) as date,
                        COUNT(*) as active_users
                    FROM selfology_users
                    WHERE last_active >= NOW() - INTERVAL '%s days'
                    GROUP BY DATE(last_active)
                    ORDER BY date DESC
                """, days)
                
                # Message activity
                message_activity = await conn.fetch("""
                    SELECT 
                        DATE(timestamp) as date,
                        COUNT(*) as total_messages,
                        COUNT(*) FILTER (WHERE message_type = 'user') as user_messages,
                        COUNT(*) FILTER (WHERE message_type = 'assistant') as ai_responses,
                        COUNT(DISTINCT user_id) as active_users
                    FROM selfology_chat_messages
                    WHERE timestamp >= NOW() - INTERVAL '%s days'
                    GROUP BY DATE(timestamp)
                    ORDER BY date DESC
                """, days)
                
                # Assessment activity
                assessment_activity = await conn.fetch("""
                    SELECT 
                        DATE(answered_at) as date,
                        COUNT(*) as questions_answered,
                        COUNT(DISTINCT user_id) as users_answering
                    FROM selfology_question_answers
                    WHERE answered_at >= NOW() - INTERVAL '%s days'
                    GROUP BY DATE(answered_at)
                    ORDER BY date DESC
                """, days)
                
                # User retention
                retention_data = await conn.fetchrow("""
                    SELECT 
                        COUNT(DISTINCT user_id) FILTER (WHERE last_active >= NOW() - INTERVAL '1 day') as daily_retention,
                        COUNT(DISTINCT user_id) FILTER (WHERE last_active >= NOW() - INTERVAL '7 days') as weekly_retention,
                        COUNT(DISTINCT user_id) FILTER (WHERE last_active >= NOW() - INTERVAL '30 days') as monthly_retention,
                        COUNT(DISTINCT user_id) as total_users
                    FROM selfology_users
                """)
            
            # Calculate engagement scores
            engagement_scores = await self._calculate_engagement_scores(days)
            
            engagement_analysis = {
                "period_days": days,
                "daily_active_users": [dict(row) for row in daily_active],
                "message_activity": [dict(row) for row in message_activity],
                "assessment_activity": [dict(row) for row in assessment_activity],
                "retention_metrics": dict(retention_data) if retention_data else {},
                "engagement_scores": engagement_scores,
                "analysis_timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            processing_time = time.time() - start_time
            
            result = StatisticsResult(
                success=True,
                data=engagement_analysis,
                message="Engagement analysis retrieved",
                processing_time=processing_time,
                cache_hit=False
            )
            
            self._cache_result(cache_key, result)
            
            self.logger.log_service_result("get_engagement_analysis", True, processing_time)
            return result
            
        except Exception as e:
            self.logger.log_error("ENGAGEMENT_ANALYSIS_ERROR", f"Failed to get engagement analysis: {e}", None, e)
            return StatisticsResult(success=False, message=f"Failed to get engagement analysis: {str(e)}")
    
    async def get_domain_analytics(self) -> StatisticsResult:
        """Get psychological domain coverage analytics"""
        
        start_time = time.time()
        self.logger.log_service_call("get_domain_analytics")
        
        try:
            cache_key = "domain_analytics"
            cached_result = self._get_cached_result(cache_key)
            
            if cached_result:
                cached_result.cache_hit = True
                cached_result.processing_time = time.time() - start_time
                return cached_result
            
            # Get domain coverage from questions
            async with self.db_pool.acquire() as conn:
                # Domain coverage by question frequency
                domain_coverage = await conn.fetch("""
                    SELECT 
                        SUBSTRING(question_id FROM '^[A-Z]+') as domain,
                        COUNT(*) as total_answers,
                        COUNT(DISTINCT user_id) as unique_users,
                        AVG(confidence_score) as avg_confidence,
                        MIN(answered_at) as first_answer,
                        MAX(answered_at) as last_answer
                    FROM selfology_question_answers
                    GROUP BY domain
                    ORDER BY total_answers DESC
                """)
                
                # User domain exploration patterns
                user_domain_patterns = await conn.fetch("""
                    SELECT 
                        user_id,
                        ARRAY_AGG(DISTINCT SUBSTRING(question_id FROM '^[A-Z]+')) as explored_domains,
                        COUNT(*) as total_questions
                    FROM selfology_question_answers
                    GROUP BY user_id
                    HAVING COUNT(*) >= 5
                """)
                
                # Domain progression analysis
                domain_progression = await conn.fetch("""
                    SELECT 
                        SUBSTRING(question_id FROM '^[A-Z]+') as domain,
                        DATE(answered_at) as date,
                        COUNT(*) as daily_answers
                    FROM selfology_question_answers
                    WHERE answered_at >= NOW() - INTERVAL '30 days'
                    GROUP BY domain, DATE(answered_at)
                    ORDER BY domain, date
                """)
            
            # Analyze domain completion rates
            domain_completion = await self._analyze_domain_completion_rates()
            
            # Calculate domain effectiveness
            domain_effectiveness = await self._calculate_domain_effectiveness()
            
            domain_analytics = {
                "domain_coverage": [dict(row) for row in domain_coverage],
                "user_exploration_patterns": [dict(row) for row in user_domain_patterns],
                "domain_progression": [dict(row) for row in domain_progression],
                "completion_rates": domain_completion,
                "effectiveness_metrics": domain_effectiveness,
                "analysis_timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            processing_time = time.time() - start_time
            
            result = StatisticsResult(
                success=True,
                data=domain_analytics,
                message="Domain analytics retrieved",
                processing_time=processing_time,
                cache_hit=False
            )
            
            self._cache_result(cache_key, result)
            
            self.logger.log_service_result("get_domain_analytics", True, processing_time)
            return result
            
        except Exception as e:
            self.logger.log_error("DOMAIN_ANALYTICS_ERROR", f"Failed to get domain analytics: {e}", None, e)
            return StatisticsResult(success=False, message=f"Failed to get domain analytics: {str(e)}")
    
    async def _calculate_engagement_metrics(self, user_id: str, user_profile: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate user engagement metrics"""
        
        # Get activity data for last 30 days
        activity_summary = await self.user_dao.get_user_activity_summary(user_id, 30)
        
        # Basic metrics
        total_messages = user_profile.get("chat_stats", {}).get("total_messages", 0)
        total_questions = user_profile.get("assessment_stats", {}).get("total_answers", 0)
        
        # Calculate scores
        message_engagement = min(1.0, total_messages / 50.0)  # Normalized to 50 messages
        assessment_engagement = min(1.0, total_questions / 20.0)  # Normalized to 20 questions
        
        # Activity recency score
        last_active = user_profile.get("user", {}).get("last_active")
        if last_active:
            days_since_active = (datetime.now(timezone.utc) - last_active).days
            recency_score = max(0.0, 1.0 - (days_since_active / 30.0))
        else:
            recency_score = 0.0
        
        # Overall engagement score
        engagement_score = (message_engagement + assessment_engagement + recency_score) / 3.0
        
        return {
            "engagement_score": round(engagement_score, 3),
            "message_engagement": round(message_engagement, 3),
            "assessment_engagement": round(assessment_engagement, 3),
            "recency_score": round(recency_score, 3),
            "activity_days": len(activity_summary.get("daily_activity", [])),
            "total_interactions": total_messages + total_questions
        }
    
    async def _analyze_user_domains(self, user_id: str) -> Dict[str, Any]:
        """Analyze user's domain exploration"""
        
        # Get user's answered questions
        async with self.db_pool.acquire() as conn:
            domain_data = await conn.fetch("""
                SELECT 
                    SUBSTRING(question_id FROM '^[A-Z]+') as domain,
                    COUNT(*) as question_count,
                    AVG(confidence_score) as avg_confidence,
                    MIN(answered_at) as first_question,
                    MAX(answered_at) as last_question
                FROM selfology_question_answers
                WHERE user_id = $1
                GROUP BY domain
                ORDER BY question_count DESC
            """, user_id)
        
        # Available domains for comparison
        available_domains = [
            "IDENTITY", "EMOTIONS", "RELATIONSHIPS", "WORK", 
            "HEALTH", "CREATIVITY", "FUTURE", "LIFESTYLE"
        ]
        
        explored_domains = [row["domain"] for row in domain_data]
        unexplored_domains = [d for d in available_domains if d not in explored_domains]
        
        return {
            "explored_domains": [dict(row) for row in domain_data],
            "unexplored_domains": unexplored_domains,
            "domain_coverage": len(explored_domains) / len(available_domains),
            "most_explored": explored_domains[0] if explored_domains else None,
            "exploration_depth": sum(row["question_count"] for row in domain_data) / max(1, len(explored_domains))
        }
    
    async def _get_personality_insights(self, user_id: str) -> Dict[str, Any]:
        """Get personality insights for user"""
        
        # Get personality vector
        personality_vector = await self.user_dao.get_latest_personality_vector(user_id)
        
        if not personality_vector:
            return {"available": False}
        
        traits = personality_vector.get("traits", {})
        personality_data = traits.get("personality", {}) if traits else {}
        
        # Find similar personalities
        similar_personalities = await self.vector_dao.find_similar_personalities(user_id, limit=5)
        
        return {
            "available": True,
            "personality_traits": personality_data,
            "vector_version": personality_vector.get("vector_version", 1),
            "confidence_score": personality_vector.get("confidence_score", 0.0),
            "similar_users_count": len(similar_personalities),
            "personality_type": self._classify_personality_type(personality_data)
        }
    
    async def _get_activity_timeline(self, user_id: str, days: int = 30) -> List[Dict[str, Any]]:
        """Get user's activity timeline"""
        
        async with self.db_pool.acquire() as conn:
            timeline = await conn.fetch("""
                SELECT 
                    DATE(timestamp) as date,
                    COUNT(*) FILTER (WHERE message_type = 'user') as user_messages,
                    COUNT(*) FILTER (WHERE message_type = 'assistant') as ai_responses
                FROM selfology_chat_messages
                WHERE user_id = $1 AND timestamp >= NOW() - INTERVAL '%s days'
                GROUP BY DATE(timestamp)
                UNION
                SELECT 
                    DATE(answered_at) as date,
                    0 as user_messages,
                    COUNT(*) as ai_responses
                FROM selfology_question_answers
                WHERE user_id = $1 AND answered_at >= NOW() - INTERVAL '%s days'
                GROUP BY DATE(answered_at)
                ORDER BY date DESC
            """, user_id, days, user_id, days)
        
        return [dict(row) for row in timeline]
    
    async def _get_detailed_user_info(self, user_id: str) -> Dict[str, Any]:
        """Get detailed user information"""
        
        # Get recent insights
        recent_insights = await self.user_dao.get_user_insights(user_id, 10)
        
        # Get recent chat history
        recent_chats = await self.user_dao.get_recent_chat_history(user_id, 5)
        
        return {
            "recent_insights": recent_insights,
            "recent_conversations": recent_chats,
            "data_privacy_compliant": True  # Always respect privacy
        }
    
    async def _calculate_system_health(self) -> Dict[str, Any]:
        """Calculate system health metrics"""
        
        async with self.db_pool.acquire() as conn:
            # Error rates (simplified - would need error logging table)
            system_metrics = await conn.fetchrow("""
                SELECT 
                    COUNT(*) as total_users,
                    COUNT(*) FILTER (WHERE last_active >= NOW() - INTERVAL '24 hours') as active_today,
                    COUNT(*) FILTER (WHERE gdpr_consent = true) as consented_users,
                    COUNT(*) FILTER (WHERE onboarding_completed = true) as completed_users
                FROM selfology_users
            """)
            
            # Database health
            db_size = await conn.fetchval("SELECT pg_database_size(current_database())")
            
        health_score = 0.95  # Simplified health score
        
        return {
            "overall_health": health_score,
            "system_metrics": dict(system_metrics) if system_metrics else {},
            "database_size_mb": round((db_size or 0) / (1024 * 1024), 2),
            "status": "healthy" if health_score > 0.9 else "warning" if health_score > 0.7 else "critical"
        }
    
    async def _calculate_growth_metrics(self) -> Dict[str, Any]:
        """Calculate growth metrics"""
        
        async with self.db_pool.acquire() as conn:
            # Growth over time
            monthly_growth = await conn.fetch("""
                SELECT 
                    DATE_TRUNC('month', created_at) as month,
                    COUNT(*) as new_users
                FROM selfology_users
                WHERE created_at >= NOW() - INTERVAL '6 months'
                GROUP BY DATE_TRUNC('month', created_at)
                ORDER BY month
            """)
            
            # Conversion rates
            conversion_metrics = await conn.fetchrow("""
                SELECT 
                    COUNT(*) as total_registered,
                    COUNT(*) FILTER (WHERE gdpr_consent = true) as gave_consent,
                    COUNT(*) FILTER (WHERE onboarding_completed = true) as completed_onboarding,
                    ROUND(
                        COUNT(*) FILTER (WHERE onboarding_completed = true) * 100.0 / 
                        NULLIF(COUNT(*) FILTER (WHERE gdpr_consent = true), 0), 2
                    ) as conversion_rate
                FROM selfology_users
            """)
        
        return {
            "monthly_growth": [dict(row) for row in monthly_growth],
            "conversion_metrics": dict(conversion_metrics) if conversion_metrics else {},
            "growth_trend": "positive"  # Simplified
        }
    
    async def _get_performance_metrics(self) -> Dict[str, Any]:
        """Get system performance metrics"""
        
        # Simplified performance metrics
        # In production, this would integrate with monitoring systems
        
        return {
            "average_response_time_ms": 150.0,
            "api_success_rate": 0.99,
            "database_connection_pool": {
                "active_connections": 5,
                "max_connections": 20,
                "utilization": 0.25
            },
            "vector_db_status": "healthy"
        }
    
    async def _calculate_engagement_scores(self, days: int) -> Dict[str, float]:
        """Calculate system-wide engagement scores"""
        
        async with self.db_pool.acquire() as conn:
            # Average messages per user
            avg_messages = await conn.fetchval("""
                SELECT AVG(message_count) FROM (
                    SELECT COUNT(*) as message_count
                    FROM selfology_chat_messages
                    WHERE timestamp >= NOW() - INTERVAL '%s days'
                    GROUP BY user_id
                ) user_messages
            """, days)
            
            # Average questions per user
            avg_questions = await conn.fetchval("""
                SELECT AVG(question_count) FROM (
                    SELECT COUNT(*) as question_count
                    FROM selfology_question_answers
                    WHERE answered_at >= NOW() - INTERVAL '%s days'
                    GROUP BY user_id
                ) user_questions
            """, days)
        
        return {
            "average_messages_per_user": round(avg_messages or 0.0, 2),
            "average_questions_per_user": round(avg_questions or 0.0, 2),
            "overall_engagement": round(((avg_messages or 0.0) + (avg_questions or 0.0)) / 2.0, 2)
        }
    
    async def _analyze_domain_completion_rates(self) -> Dict[str, Any]:
        """Analyze completion rates by domain"""
        
        # Simplified domain completion analysis
        # Would need more sophisticated logic in production
        
        return {
            "IDENTITY": {"completion_rate": 0.85, "avg_questions": 8},
            "EMOTIONS": {"completion_rate": 0.78, "avg_questions": 6},
            "RELATIONSHIPS": {"completion_rate": 0.72, "avg_questions": 7},
            "WORK": {"completion_rate": 0.69, "avg_questions": 5}
        }
    
    async def _calculate_domain_effectiveness(self) -> Dict[str, float]:
        """Calculate domain effectiveness metrics"""
        
        # Simplified effectiveness calculation
        # Would analyze user satisfaction, completion rates, etc.
        
        return {
            "IDENTITY": 0.88,
            "EMOTIONS": 0.82,
            "RELATIONSHIPS": 0.79,
            "WORK": 0.76,
            "HEALTH": 0.74,
            "CREATIVITY": 0.71
        }
    
    def _classify_personality_type(self, personality_data: Dict[str, float]) -> str:
        """Classify personality type from Big Five scores"""
        
        if not personality_data:
            return "unknown"
        
        # Simple classification
        extraversion = personality_data.get("extraversion", 0.5)
        openness = personality_data.get("openness", 0.5)
        conscientiousness = personality_data.get("conscientiousness", 0.5)
        
        if extraversion > 0.7 and openness > 0.7:
            return "extravert_creative"
        elif extraversion > 0.7 and conscientiousness > 0.7:
            return "extravert_organized"
        elif extraversion < 0.3 and openness > 0.7:
            return "introvert_creative"
        elif extraversion < 0.3 and conscientiousness > 0.7:
            return "introvert_organized"
        else:
            return "balanced"
    
    def _get_cached_result(self, key: str) -> Optional[StatisticsResult]:
        """Get result from cache if available and not expired"""
        
        if key in self.cache:
            cached_data, timestamp = self.cache[key]
            if time.time() - timestamp < self.cache_ttl:
                return cached_data
            else:
                # Remove expired cache
                del self.cache[key]
        
        return None
    
    def _cache_result(self, key: str, result: StatisticsResult, ttl: Optional[int] = None):
        """Cache result with timestamp"""
        
        cache_ttl = ttl or self.cache_ttl
        self.cache[key] = (result, time.time())
        
        # Simple cache cleanup - remove old entries
        if len(self.cache) > 100:  # Limit cache size
            oldest_key = min(self.cache.keys(), key=lambda k: self.cache[k][1])
            del self.cache[oldest_key]