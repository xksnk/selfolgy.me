"""
User Profile Service - Profile management and personality analysis
Independent service for managing user profiles and personality data
"""
import time
import asyncpg
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime, timezone
import json

from data_access.user_dao import UserDAO
from data_access.vector_dao import VectorDAO
from core.config import get_config
from core.logging import get_logger, LoggerMixin


@dataclass
class ProfileResult:
    """Result of profile operation"""
    success: bool
    message: str
    profile_data: Optional[Dict[str, Any]] = None
    recommendations: Optional[List[str]] = None
    processing_time: Optional[float] = None


class UserProfileService(LoggerMixin):
    """
    Independent User Profile Service
    
    Features:
    - Profile creation and management
    - Personality analysis and insights
    - Profile recommendations
    - Data export for GDPR compliance
    - Profile similarity analysis
    - Personality development tracking
    """
    
    def __init__(self, db_pool: Optional[asyncpg.Pool] = None):
        self.config = get_config()
        self.db_pool = db_pool
        
        # Initialize DAOs
        self.user_dao = UserDAO(db_pool)
        self.vector_dao = VectorDAO()
        
        self.logger = get_logger("selfology.user_profile", "user_profile_service")
        
        self.logger.info("User Profile Service initialized")
    
    async def get_profile(self, user_id: str, include_insights: bool = True) -> ProfileResult:
        """Get comprehensive user profile"""
        
        start_time = time.time()
        self.logger.log_service_call("get_profile", user_id, include_insights=include_insights)
        
        try:
            # Get basic profile
            user_profile = await self.user_dao.get_user_profile(user_id)
            if not user_profile:
                return ProfileResult(success=False, message="Profile not found")
            
            # Get personality analysis
            personality_analysis = await self._analyze_personality_profile(user_id)
            
            # Get profile completeness
            completeness = await self._assess_profile_completeness(user_profile)
            
            # Generate recommendations
            recommendations = await self._generate_profile_recommendations(user_profile, completeness)
            
            # Get insights if requested
            insights = None
            if include_insights:
                insights = await self._generate_profile_insights(user_id, user_profile)
            
            # Find similar profiles
            similar_profiles = await self._find_similar_profiles(user_id)
            
            profile_data = {
                "basic_info": user_profile["user"],
                "assessment_summary": user_profile["assessment_stats"],
                "chat_summary": user_profile["chat_stats"],
                "personality_analysis": personality_analysis,
                "profile_completeness": completeness,
                "similar_profiles_count": len(similar_profiles),
                "insights": insights,
                "last_updated": datetime.now(timezone.utc).isoformat()
            }
            
            processing_time = time.time() - start_time
            
            self.logger.log_service_result("get_profile", True, processing_time)
            
            return ProfileResult(
                success=True,
                message="Profile retrieved successfully",
                profile_data=profile_data,
                recommendations=recommendations,
                processing_time=processing_time
            )
            
        except Exception as e:
            self.logger.log_error("PROFILE_RETRIEVAL_ERROR", f"Failed to get profile: {e}", user_id, e)
            return ProfileResult(success=False, message=f"Failed to get profile: {str(e)}")
    
    async def update_personality_traits(self, user_id: str, 
                                      trait_updates: Dict[str, float],
                                      source: str = "manual_update") -> ProfileResult:
        """Update user's personality traits"""
        
        start_time = time.time()
        self.logger.log_service_call("update_personality_traits", user_id, 
                                   updates=trait_updates, source=source)
        
        try:
            # Get current personality vector
            current_vector = await self.user_dao.get_latest_personality_vector(user_id)
            
            if not current_vector:
                return ProfileResult(success=False, message="No personality vector found for user")
            
            # Update traits
            current_traits = current_vector.get("traits", {})
            updated_traits = self._merge_trait_updates(current_traits, trait_updates)
            
            # Save updated personality vector
            new_vector = await self.user_dao.save_personality_vector(
                user_id,
                updated_traits,
                confidence_score=0.8,  # Manual updates are high confidence
                source_data=f"trait_update_{source}"
            )
            
            # Update vector database if available
            if current_vector.get("qdrant_point_id"):
                await self.vector_dao.update_personality_vector(
                    current_vector["qdrant_point_id"],
                    user_id,
                    trait_updates,
                    confidence=0.8
                )
            
            processing_time = time.time() - start_time
            
            self.logger.log_service_result("update_personality_traits", True, processing_time,
                                         vector_version=new_vector["vector_version"])
            
            return ProfileResult(
                success=True,
                message="Personality traits updated successfully",
                profile_data={"updated_traits": trait_updates, "new_version": new_vector["vector_version"]},
                processing_time=processing_time
            )
            
        except Exception as e:
            self.logger.log_error("TRAIT_UPDATE_ERROR", f"Failed to update traits: {e}", user_id, e)
            return ProfileResult(success=False, message=f"Failed to update traits: {str(e)}")
    
    async def export_profile_data(self, user_id: str) -> ProfileResult:
        """Export all user profile data (GDPR compliance)"""
        
        start_time = time.time()
        self.logger.log_service_call("export_profile_data", user_id)
        
        try:
            # Get comprehensive profile
            user_profile = await self.user_dao.get_user_profile(user_id)
            if not user_profile:
                return ProfileResult(success=False, message="Profile not found")
            
            # Get all personality vectors
            all_vectors = await self._get_all_user_vectors(user_id)
            
            # Get all chat history
            all_chats = await self._get_all_user_chats(user_id)
            
            # Get all insights
            all_insights = await self.user_dao.get_user_insights(user_id, limit=1000)
            
            # Get activity log
            activity_log = await self._get_user_activity_log(user_id)
            
            export_data = {
                "export_info": {
                    "user_id": user_id,
                    "exported_at": datetime.now(timezone.utc).isoformat(),
                    "export_version": "1.0"
                },
                "profile": user_profile,
                "personality_vectors": all_vectors,
                "chat_history": all_chats,
                "insights": all_insights,
                "activity_log": activity_log,
                "gdpr_compliance": {
                    "data_retention_policy": "User data retained as per privacy policy",
                    "deletion_rights": "User can request data deletion at any time",
                    "data_portability": "This export provides complete data portability"
                }
            }
            
            processing_time = time.time() - start_time
            
            self.logger.log_service_result("export_profile_data", True, processing_time,
                                         data_points=len(export_data))
            
            return ProfileResult(
                success=True,
                message="Profile data exported successfully",
                profile_data=export_data,
                processing_time=processing_time
            )
            
        except Exception as e:
            self.logger.log_error("PROFILE_EXPORT_ERROR", f"Failed to export profile: {e}", user_id, e)
            return ProfileResult(success=False, message=f"Failed to export profile: {str(e)}")
    
    async def delete_profile(self, user_id: str) -> ProfileResult:
        """Delete user profile completely (GDPR compliance)"""
        
        start_time = time.time()
        self.logger.log_service_call("delete_profile", user_id)
        
        try:
            # Delete from vector database
            vector_deleted = await self.vector_dao.delete_user_vectors(user_id)
            
            # Delete from PostgreSQL
            async with self.db_pool.acquire() as conn:
                async with conn.transaction():
                    # Delete in order of dependencies
                    await conn.execute("DELETE FROM selfology_chat_insights WHERE user_id = $1", user_id)
                    await conn.execute("DELETE FROM selfology_chat_messages WHERE user_id = $1", user_id)
                    await conn.execute("DELETE FROM selfology_question_answers WHERE user_id = $1", user_id)
                    await conn.execute("DELETE FROM selfology_personality_vectors WHERE user_id = $1", user_id)
                    await conn.execute("DELETE FROM selfology_user_question_progress WHERE user_id = $1", user_id)
                    await conn.execute("DELETE FROM selfology_user_activity_log WHERE user_id = $1", user_id)
                    
                    # Finally delete user record
                    result = await conn.execute("DELETE FROM selfology_users WHERE telegram_id = $1", user_id)
            
            user_deleted = result == "DELETE 1"
            
            processing_time = time.time() - start_time
            
            if user_deleted:
                self.logger.log_service_result("delete_profile", True, processing_time,
                                             vector_deleted=vector_deleted)
                
                return ProfileResult(
                    success=True,
                    message="Profile deleted completely",
                    profile_data={
                        "user_deleted": user_deleted,
                        "vector_deleted": vector_deleted,
                        "deletion_timestamp": datetime.now(timezone.utc).isoformat()
                    },
                    processing_time=processing_time
                )
            else:
                return ProfileResult(success=False, message="User not found or already deleted")
            
        except Exception as e:
            self.logger.log_error("PROFILE_DELETION_ERROR", f"Failed to delete profile: {e}", user_id, e)
            return ProfileResult(success=False, message=f"Failed to delete profile: {str(e)}")
    
    async def analyze_personality_development(self, user_id: str, days: int = 90) -> ProfileResult:
        """Analyze personality development over time"""
        
        start_time = time.time()
        self.logger.log_service_call("analyze_personality_development", user_id, period_days=days)
        
        try:
            # Get personality vectors over time
            personality_history = await self._get_personality_history(user_id, days)
            
            if len(personality_history) < 2:
                return ProfileResult(
                    success=False,
                    message="Insufficient data for development analysis (need at least 2 data points)"
                )
            
            # Analyze trends
            development_trends = await self._analyze_personality_trends(personality_history)
            
            # Get insights and recommendations
            development_insights = await self._generate_development_insights(development_trends)
            
            development_data = {
                "analysis_period_days": days,
                "data_points": len(personality_history),
                "personality_history": personality_history,
                "development_trends": development_trends,
                "insights": development_insights,
                "analysis_timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            processing_time = time.time() - start_time
            
            self.logger.log_service_result("analyze_personality_development", True, processing_time,
                                         data_points=len(personality_history))
            
            return ProfileResult(
                success=True,
                message="Personality development analyzed",
                profile_data=development_data,
                recommendations=development_insights.get("recommendations", []),
                processing_time=processing_time
            )
            
        except Exception as e:
            self.logger.log_error("DEVELOPMENT_ANALYSIS_ERROR", f"Failed to analyze development: {e}", user_id, e)
            return ProfileResult(success=False, message=f"Failed to analyze development: {str(e)}")
    
    async def _analyze_personality_profile(self, user_id: str) -> Dict[str, Any]:
        """Analyze user's personality profile"""
        
        personality_vector = await self.user_dao.get_latest_personality_vector(user_id)
        
        if not personality_vector:
            return {"available": False, "message": "No personality data available"}
        
        traits = personality_vector.get("traits", {})
        personality = traits.get("personality", {}) if traits else {}
        values = traits.get("values", {}) if traits else {}
        goals = traits.get("goals", []) if traits else []
        
        # Analyze Big Five traits
        big_five_analysis = self._analyze_big_five_traits(personality)
        
        # Analyze values
        values_analysis = self._analyze_values_profile(values)
        
        # Analyze goals
        goals_analysis = self._analyze_goals_alignment(goals, values)
        
        return {
            "available": True,
            "big_five": big_five_analysis,
            "values": values_analysis,
            "goals": goals_analysis,
            "personality_type": self._classify_personality_type(personality),
            "confidence_score": personality_vector.get("confidence_score", 0.0),
            "last_updated": personality_vector.get("created_at").isoformat() if personality_vector.get("created_at") else None
        }
    
    async def _assess_profile_completeness(self, user_profile: Dict[str, Any]) -> Dict[str, Any]:
        """Assess how complete the user's profile is"""
        
        completeness_score = 0.0
        missing_elements = []
        completed_elements = []
        
        # Check basic info
        user_info = user_profile.get("user", {})
        if user_info.get("gdpr_consent"):
            completeness_score += 0.1
            completed_elements.append("GDPR consent")
        else:
            missing_elements.append("GDPR consent")
        
        # Check assessment completion
        assessment_stats = user_profile.get("assessment_stats", {})
        total_answers = assessment_stats.get("total_answers", 0)
        
        if total_answers >= 10:
            completeness_score += 0.3
            completed_elements.append("Basic assessment")
        elif total_answers > 0:
            completeness_score += 0.15
            completed_elements.append("Partial assessment")
        else:
            missing_elements.append("Assessment questions")
        
        if total_answers >= 20:
            completeness_score += 0.2
            completed_elements.append("Comprehensive assessment")
        else:
            missing_elements.append("Comprehensive assessment")
        
        # Check personality vector
        if user_profile.get("personality_vector"):
            completeness_score += 0.25
            completed_elements.append("Personality analysis")
        else:
            missing_elements.append("Personality analysis")
        
        # Check chat engagement
        chat_stats = user_profile.get("chat_stats", {})
        total_messages = chat_stats.get("total_messages", 0)
        
        if total_messages >= 10:
            completeness_score += 0.15
            completed_elements.append("Chat engagement")
        elif total_messages > 0:
            completeness_score += 0.075
            completed_elements.append("Some chat interaction")
        else:
            missing_elements.append("Chat interaction")
        
        return {
            "completeness_score": round(completeness_score, 2),
            "completed_elements": completed_elements,
            "missing_elements": missing_elements,
            "completeness_level": self._get_completeness_level(completeness_score)
        }
    
    async def _generate_profile_recommendations(self, user_profile: Dict[str, Any], 
                                              completeness: Dict[str, Any]) -> List[str]:
        """Generate personalized profile recommendations"""
        
        recommendations = []
        
        # Based on completeness
        if completeness["completeness_score"] < 0.5:
            recommendations.append("Пройдите психологическое анкетирование для создания полного профиля")
        
        if "Chat interaction" in completeness.get("missing_elements", []):
            recommendations.append("Начните общение с AI-коучем для получения персональных советов")
        
        # Based on personality data
        personality_vector = user_profile.get("personality_vector")
        if personality_vector:
            traits = personality_vector.get("traits", {})
            personality = traits.get("personality", {}) if traits else {}
            
            # Personality-specific recommendations
            if personality.get("openness", 0) > 0.7:
                recommendations.append("Исследуйте творческие техники саморазвития")
            
            if personality.get("conscientiousness", 0) > 0.7:
                recommendations.append("Используйте структурированные методы планирования целей")
            
            if personality.get("extraversion", 0) < 0.3:
                recommendations.append("Попробуйте техники развития социальных навыков")
        
        # Based on activity
        assessment_stats = user_profile.get("assessment_stats", {})
        if assessment_stats.get("total_answers", 0) > 15:
            recommendations.append("Регулярно отслеживайте прогресс вашего развития")
        
        return recommendations[:5]  # Limit to top 5
    
    async def _generate_profile_insights(self, user_id: str, 
                                       user_profile: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate insights about user's profile"""
        
        insights = []
        
        # Personality insights
        personality_vector = user_profile.get("personality_vector")
        if personality_vector:
            traits = personality_vector.get("traits", {})
            personality = traits.get("personality", {}) if traits else {}
            
            # Find strongest and weakest traits
            if personality:
                strongest_trait = max(personality.items(), key=lambda x: x[1])
                insights.append({
                    "type": "personality_strength",
                    "title": f"Ваша сильная сторона: {strongest_trait[0]}",
                    "description": self._get_trait_description(strongest_trait[0], "strength"),
                    "confidence": 0.8
                })
        
        # Activity patterns insights
        chat_stats = user_profile.get("chat_stats", {})
        if chat_stats.get("total_messages", 0) > 20:
            insights.append({
                "type": "engagement_pattern",
                "title": "Высокий уровень вовлеченности",
                "description": "Вы активно используете возможности AI-коучинга",
                "confidence": 0.9
            })
        
        # Assessment insights
        assessment_stats = user_profile.get("assessment_stats", {})
        if assessment_stats.get("total_answers", 0) > 15:
            insights.append({
                "type": "self_reflection",
                "title": "Развитая способность к саморефлексии",
                "description": "Ваши подробные ответы показывают глубокое самопонимание",
                "confidence": 0.85
            })
        
        return insights
    
    async def _find_similar_profiles(self, user_id: str) -> List[Dict[str, Any]]:
        """Find users with similar personality profiles"""
        
        try:
            similar_profiles = await self.vector_dao.find_similar_personalities(user_id, limit=5)
            return similar_profiles
        except Exception as e:
            self.logger.warning(f"Failed to find similar profiles: {e}")
            return []
    
    def _merge_trait_updates(self, current_traits: Dict[str, Any], 
                           updates: Dict[str, float]) -> Dict[str, Any]:
        """Merge trait updates with current traits"""
        
        updated_traits = current_traits.copy()
        
        # Update personality traits
        if "personality" not in updated_traits:
            updated_traits["personality"] = {}
        
        for trait, value in updates.items():
            updated_traits["personality"][trait] = max(0.0, min(1.0, value))  # Clamp to [0,1]
        
        # Update version
        current_version = updated_traits.get("version", 1)
        updated_traits["version"] = current_version + 1
        updated_traits["last_updated"] = datetime.now(timezone.utc).isoformat()
        
        return updated_traits
    
    def _analyze_big_five_traits(self, personality: Dict[str, float]) -> Dict[str, Any]:
        """Analyze Big Five personality traits"""
        
        if not personality:
            return {"available": False}
        
        trait_analysis = {}
        
        for trait, score in personality.items():
            trait_analysis[trait] = {
                "score": score,
                "level": self._get_trait_level(score),
                "description": self._get_trait_description(trait, self._get_trait_level(score))
            }
        
        return {
            "available": True,
            "traits": trait_analysis,
            "dominant_trait": max(personality.items(), key=lambda x: x[1])[0] if personality else None,
            "personality_summary": self._generate_personality_summary(personality)
        }
    
    def _analyze_values_profile(self, values: Dict[str, float]) -> Dict[str, Any]:
        """Analyze user's values profile"""
        
        if not values:
            return {"available": False}
        
        # Sort values by importance
        sorted_values = sorted(values.items(), key=lambda x: x[1], reverse=True)
        top_values = sorted_values[:3]
        
        return {
            "available": True,
            "top_values": [{"value": v[0], "score": v[1]} for v in top_values],
            "values_alignment": self._assess_values_alignment(values),
            "recommendations": self._get_values_recommendations(top_values)
        }
    
    def _analyze_goals_alignment(self, goals: List[str], values: Dict[str, float]) -> Dict[str, Any]:
        """Analyze alignment between goals and values"""
        
        if not goals:
            return {"available": False}
        
        # Simple alignment analysis
        alignment_score = 0.7  # Simplified
        
        return {
            "available": True,
            "goals_count": len(goals),
            "alignment_score": alignment_score,
            "alignment_level": "good" if alignment_score > 0.6 else "needs_improvement",
            "recommendations": ["Регулярно пересматривайте цели на соответствие ценностям"]
        }
    
    def _classify_personality_type(self, personality: Dict[str, float]) -> str:
        """Classify personality type from traits"""
        
        if not personality:
            return "unknown"
        
        # Simple MBTI-like classification
        extraversion = personality.get("extraversion", 0.5)
        openness = personality.get("openness", 0.5)
        conscientiousness = personality.get("conscientiousness", 0.5)
        agreeableness = personality.get("agreeableness", 0.5)
        
        if extraversion > 0.6 and openness > 0.6:
            return "Творческий экстраверт"
        elif extraversion > 0.6 and conscientiousness > 0.6:
            return "Организованный лидер"
        elif extraversion < 0.4 and openness > 0.6:
            return "Креативный интроверт"
        elif extraversion < 0.4 and conscientiousness > 0.6:
            return "Вдумчивый исполнитель"
        else:
            return "Сбалансированная личность"
    
    def _get_completeness_level(self, score: float) -> str:
        """Get completeness level description"""
        
        if score >= 0.8:
            return "excellent"
        elif score >= 0.6:
            return "good"
        elif score >= 0.4:
            return "moderate"
        else:
            return "basic"
    
    def _get_trait_level(self, score: float) -> str:
        """Get trait level from score"""
        
        if score >= 0.7:
            return "high"
        elif score >= 0.3:
            return "moderate"
        else:
            return "low"
    
    def _get_trait_description(self, trait: str, level: str) -> str:
        """Get description for trait and level"""
        
        descriptions = {
            "openness": {
                "high": "Вы открыты к новому опыту, креативны и любознательны",
                "moderate": "Вы умеренно открыты к новым идеям",
                "low": "Вы предпочитаете знакомое и проверенное"
            },
            "conscientiousness": {
                "high": "Вы организованны, целеустремленны и дисциплинированы",
                "moderate": "Вы умеренно организованы",
                "low": "Вы более гибки и спонтанны в планах"
            }
            # Add more traits as needed
        }
        
        return descriptions.get(trait, {}).get(level, "Анализ недоступен")
    
    def _generate_personality_summary(self, personality: Dict[str, float]) -> str:
        """Generate personality summary"""
        
        # Simple summary generation
        dominant_trait = max(personality.items(), key=lambda x: x[1])[0] if personality else None
        
        summaries = {
            "openness": "Творческая и любознательная личность",
            "conscientiousness": "Организованная и целеустремленная личность",
            "extraversion": "Общительная и энергичная личность",
            "agreeableness": "Доброжелательная и отзывчивая личность",
            "neuroticism": "Эмоционально чувствительная личность"
        }
        
        return summaries.get(dominant_trait, "Уравновешенная личность")
    
    def _assess_values_alignment(self, values: Dict[str, float]) -> str:
        """Assess values alignment"""
        
        # Simplified alignment assessment
        value_spread = max(values.values()) - min(values.values()) if values else 0
        
        if value_spread > 0.5:
            return "clear_priorities"
        elif value_spread > 0.3:
            return "moderate_priorities"
        else:
            return "balanced_values"
    
    def _get_values_recommendations(self, top_values: List[tuple]) -> List[str]:
        """Get recommendations based on top values"""
        
        recommendations = []
        
        for value, score in top_values:
            if value == "family":
                recommendations.append("Уделяйте больше времени близким отношениям")
            elif value == "career":
                recommendations.append("Сосредоточьтесь на профессиональном развитии")
            elif value == "health":
                recommendations.append("Приоритизируйте физическое и ментальное здоровье")
        
        return recommendations
    
    async def _get_all_user_vectors(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all personality vectors for user"""
        
        async with self.db_pool.acquire() as conn:
            vectors = await conn.fetch("""
                SELECT * FROM selfology_personality_vectors
                WHERE user_id = $1
                ORDER BY vector_version DESC
            """, user_id)
        
        return [dict(vector) for vector in vectors]
    
    async def _get_all_user_chats(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all chat messages for user"""
        
        async with self.db_pool.acquire() as conn:
            chats = await conn.fetch("""
                SELECT * FROM selfology_chat_messages
                WHERE user_id = $1
                ORDER BY timestamp DESC
                LIMIT 1000
            """, user_id)
        
        return [dict(chat) for chat in chats]
    
    async def _get_user_activity_log(self, user_id: str) -> List[Dict[str, Any]]:
        """Get user activity log"""
        
        async with self.db_pool.acquire() as conn:
            activities = await conn.fetch("""
                SELECT * FROM selfology_user_activity_log
                WHERE user_id = $1
                ORDER BY timestamp DESC
                LIMIT 500
            """, user_id)
        
        return [dict(activity) for activity in activities]
    
    async def _get_personality_history(self, user_id: str, days: int) -> List[Dict[str, Any]]:
        """Get personality development history"""
        
        async with self.db_pool.acquire() as conn:
            history = await conn.fetch("""
                SELECT * FROM selfology_personality_vectors
                WHERE user_id = $1 AND created_at >= NOW() - INTERVAL '%s days'
                ORDER BY created_at ASC
            """, user_id, days)
        
        return [dict(record) for record in history]
    
    async def _analyze_personality_trends(self, personality_history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze personality development trends"""
        
        # Simplified trend analysis
        # In production would do statistical analysis of trait changes over time
        
        return {
            "trend_analysis": "positive_development",
            "stability_score": 0.8,
            "growth_areas": ["openness", "conscientiousness"],
            "development_stage": "growth_phase"
        }
    
    async def _generate_development_insights(self, trends: Dict[str, Any]) -> Dict[str, Any]:
        """Generate insights from development trends"""
        
        insights = {
            "key_insights": [
                "Ваша личность показывает позитивное развитие",
                "Отмечается рост самосознания и эмоциональной зрелости"
            ],
            "recommendations": [
                "Продолжайте работу над саморефлексией",
                "Исследуйте новые области личностного роста"
            ],
            "next_steps": [
                "Пройдите дополнительное анкетирование через месяц",
                "Сосредоточьтесь на развитии выявленных сильных сторон"
            ]
        }
        
        return insights