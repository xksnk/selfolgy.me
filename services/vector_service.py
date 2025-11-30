"""
Vector Service - Vector DB operations service
Independent service for managing personality vectors in Qdrant
"""
import time
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timezone
import json

from data_access.vector_dao import VectorDAO
from core.config import get_config
from core.logging import vector_logger, LoggerMixin


@dataclass
class VectorResult:
    """Result of vector operation"""
    success: bool
    message: str
    vector_id: Optional[str] = None
    similarity_results: Optional[List[Dict[str, Any]]] = None
    analytics: Optional[Dict[str, Any]] = None
    processing_time: Optional[float] = None


class VectorService(LoggerMixin):
    """
    Independent Vector Service
    
    Features:
    - Store and update personality vectors
    - Find similar personalities
    - Vector space analytics
    - Personality clustering
    - Dimensional analysis
    - Vector quality assessment
    """
    
    def __init__(self):
        self.config = get_config()
        self.vector_dao = VectorDAO()
        self.vector_size = self.config.vector.vector_size  # 693 dimensions
        
        # Personality dimension mapping (simplified for demo)
        self.dimension_mapping = self._initialize_dimension_mapping()
        
        self.logger = vector_logger
        self.logger.info("Vector Service initialized")
    
    async def store_personality_profile(self, user_id: str, personality_data: Dict[str, Any],
                                      text_description: str) -> VectorResult:
        """Store personality profile as vector"""
        
        start_time = time.time()
        self.logger.log_service_call("store_personality_profile", user_id)
        
        try:
            # Generate personality vector from data
            personality_vector = self._generate_personality_vector(personality_data)
            
            # Validate vector
            if not self._validate_vector(personality_vector):
                return VectorResult(success=False, message="Invalid personality vector generated")
            
            # Store in vector database
            vector_id = await self.vector_dao.store_personality_vector(
                user_id, personality_vector, personality_data, text_description
            )
            
            processing_time = time.time() - start_time
            
            self.logger.log_service_result("store_personality_profile", True, processing_time,
                                         vector_id=vector_id)
            
            return VectorResult(
                success=True,
                message="Personality profile stored successfully",
                vector_id=vector_id,
                processing_time=processing_time
            )
            
        except Exception as e:
            self.logger.log_error("VECTOR_STORAGE_ERROR", f"Failed to store vector: {e}", user_id, e)
            return VectorResult(success=False, message=f"Failed to store vector: {str(e)}")
    
    async def update_personality_dimensions(self, user_id: str, 
                                          dimension_updates: Dict[str, float],
                                          source_question: Optional[str] = None,
                                          confidence: float = 0.5) -> VectorResult:
        """Update specific personality dimensions"""
        
        start_time = time.time()
        self.logger.log_service_call("update_personality_dimensions", user_id, 
                                   updates=dimension_updates, source=source_question)
        
        try:
            # Get current user vector
            current_vector = await self.vector_dao.get_user_vector(user_id)
            if not current_vector:
                return VectorResult(success=False, message="User vector not found")
            
            # Update vector with new dimensions
            success = await self.vector_dao.update_personality_vector(
                current_vector["point_id"], user_id, dimension_updates, confidence
            )
            
            if success:
                processing_time = time.time() - start_time
                
                self.logger.log_service_result("update_personality_dimensions", True, processing_time,
                                             dimensions_updated=len(dimension_updates))
                
                return VectorResult(
                    success=True,
                    message="Personality dimensions updated",
                    vector_id=current_vector["point_id"],
                    processing_time=processing_time
                )
            else:
                return VectorResult(success=False, message="Failed to update vector")
            
        except Exception as e:
            self.logger.log_error("VECTOR_UPDATE_ERROR", f"Failed to update vector: {e}", user_id, e)
            return VectorResult(success=False, message=f"Failed to update vector: {str(e)}")
    
    async def find_personality_matches(self, user_id: str, limit: int = 10,
                                     min_similarity: float = 0.7) -> VectorResult:
        """Find users with similar personality profiles"""
        
        start_time = time.time()
        self.logger.log_service_call("find_personality_matches", user_id, 
                                   limit=limit, min_similarity=min_similarity)
        
        try:
            # Find similar personalities
            similar_personalities = await self.vector_dao.find_similar_personalities(
                user_id, limit, min_similarity
            )
            
            # Analyze similarity patterns
            similarity_analysis = self._analyze_similarity_patterns(similar_personalities)
            
            processing_time = time.time() - start_time
            
            self.logger.log_service_result("find_personality_matches", True, processing_time,
                                         matches_found=len(similar_personalities))
            
            return VectorResult(
                success=True,
                message=f"Found {len(similar_personalities)} similar personalities",
                similarity_results=similar_personalities,
                analytics=similarity_analysis,
                processing_time=processing_time
            )
            
        except Exception as e:
            self.logger.log_error("SIMILARITY_SEARCH_ERROR", f"Failed to find matches: {e}", user_id, e)
            return VectorResult(success=False, message=f"Failed to find matches: {str(e)}")
    
    async def analyze_personality_space(self, trait_filters: Optional[Dict[str, Any]] = None) -> VectorResult:
        """Analyze the personality vector space"""
        
        start_time = time.time()
        self.logger.log_service_call("analyze_personality_space", filters=trait_filters)
        
        try:
            # Get vector collection statistics
            collection_stats = await self.vector_dao.get_collection_statistics()
            
            # Search for personalities with specific traits
            trait_analysis = {}
            if trait_filters:
                trait_results = await self.vector_dao.search_by_personality_traits(trait_filters)
                trait_analysis = self._analyze_trait_distribution(trait_results)
            
            # Calculate space analytics
            space_analytics = await self._calculate_space_analytics(collection_stats)
            
            processing_time = time.time() - start_time
            
            analytics_data = {
                "collection_statistics": collection_stats,
                "trait_analysis": trait_analysis,
                "space_analytics": space_analytics,
                "analysis_timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            self.logger.log_service_result("analyze_personality_space", True, processing_time,
                                         total_vectors=collection_stats.get("total_vectors", 0))
            
            return VectorResult(
                success=True,
                message="Personality space analyzed",
                analytics=analytics_data,
                processing_time=processing_time
            )
            
        except Exception as e:
            self.logger.log_error("SPACE_ANALYSIS_ERROR", f"Failed to analyze space: {e}", None, e)
            return VectorResult(success=False, message=f"Failed to analyze space: {str(e)}")
    
    async def get_personality_insights(self, user_id: str) -> VectorResult:
        """Get insights about user's personality from vector analysis"""
        
        start_time = time.time()
        self.logger.log_service_call("get_personality_insights", user_id)
        
        try:
            # Get user's vector
            user_vector = await self.vector_dao.get_user_vector(user_id)
            if not user_vector:
                return VectorResult(success=False, message="User vector not found")
            
            # Find similar personalities for comparison
            similar_personalities = await self.vector_dao.find_similar_personalities(user_id, limit=5)
            
            # Analyze user's position in personality space
            position_analysis = self._analyze_personality_position(user_vector, similar_personalities)
            
            # Generate dimensional insights
            dimensional_insights = self._generate_dimensional_insights(user_vector)
            
            # Calculate uniqueness score
            uniqueness_score = self._calculate_uniqueness_score(user_vector, similar_personalities)
            
            insights_data = {
                "position_analysis": position_analysis,
                "dimensional_insights": dimensional_insights,
                "uniqueness_score": uniqueness_score,
                "similar_profiles": len(similar_personalities),
                "vector_quality": self._assess_vector_quality(user_vector)
            }
            
            processing_time = time.time() - start_time
            
            self.logger.log_service_result("get_personality_insights", True, processing_time)
            
            return VectorResult(
                success=True,
                message="Personality insights generated",
                analytics=insights_data,
                similarity_results=similar_personalities,
                processing_time=processing_time
            )
            
        except Exception as e:
            self.logger.log_error("INSIGHTS_ERROR", f"Failed to get insights: {e}", user_id, e)
            return VectorResult(success=False, message=f"Failed to get insights: {str(e)}")
    
    async def cluster_personalities(self, min_cluster_size: int = 5) -> VectorResult:
        """Perform personality clustering analysis"""
        
        start_time = time.time()
        self.logger.log_service_call("cluster_personalities", min_cluster_size=min_cluster_size)
        
        try:
            # This is a simplified clustering implementation
            # In production would use proper clustering algorithms like K-means
            
            # Get personality types distribution
            personality_types = await self._get_personality_type_distribution()
            
            # Simple clustering based on personality types
            clusters = self._perform_simple_clustering(personality_types, min_cluster_size)
            
            # Analyze cluster characteristics
            cluster_analysis = self._analyze_clusters(clusters)
            
            processing_time = time.time() - start_time
            
            clustering_data = {
                "clusters_found": len(clusters),
                "cluster_details": cluster_analysis,
                "personality_distribution": personality_types,
                "clustering_method": "personality_type_based",
                "analysis_timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            self.logger.log_service_result("cluster_personalities", True, processing_time,
                                         clusters_found=len(clusters))
            
            return VectorResult(
                success=True,
                message=f"Found {len(clusters)} personality clusters",
                analytics=clustering_data,
                processing_time=processing_time
            )
            
        except Exception as e:
            self.logger.log_error("CLUSTERING_ERROR", f"Failed to cluster personalities: {e}", None, e)
            return VectorResult(success=False, message=f"Failed to cluster personalities: {str(e)}")
    
    async def delete_user_vector(self, user_id: str) -> VectorResult:
        """Delete user's personality vector (GDPR compliance)"""
        
        start_time = time.time()
        self.logger.log_service_call("delete_user_vector", user_id)
        
        try:
            success = await self.vector_dao.delete_user_vectors(user_id)
            
            processing_time = time.time() - start_time
            
            if success:
                self.logger.log_service_result("delete_user_vector", True, processing_time)
                
                return VectorResult(
                    success=True,
                    message="User vector deleted successfully",
                    processing_time=processing_time
                )
            else:
                return VectorResult(success=False, message="User vector not found or already deleted")
            
        except Exception as e:
            self.logger.log_error("VECTOR_DELETION_ERROR", f"Failed to delete vector: {e}", user_id, e)
            return VectorResult(success=False, message=f"Failed to delete vector: {str(e)}")
    
    def _generate_personality_vector(self, personality_data: Dict[str, Any]) -> List[float]:
        """Generate 693-dimensional personality vector from assessment data"""
        
        # Initialize vector with zeros
        vector = [0.0] * self.vector_size
        
        # Extract personality traits
        personality = personality_data.get("personality", {})
        values = personality_data.get("values", {})
        goals = personality_data.get("goals", [])
        
        # Map Big Five traits to vector dimensions
        big_five_mapping = {
            "openness": 0,
            "conscientiousness": 1,
            "extraversion": 2,
            "agreeableness": 3,
            "neuroticism": 4
        }
        
        for trait, score in personality.items():
            if trait in big_five_mapping:
                vector[big_five_mapping[trait]] = float(score)
        
        # Map values to vector dimensions (starting from index 5)
        values_start_idx = 5
        for i, (value, score) in enumerate(values.items()):
            if values_start_idx + i < self.vector_size:
                vector[values_start_idx + i] = float(score)
        
        # Map goals to vector dimensions (starting from index 15)
        goals_start_idx = 15
        goal_weights = {
            "career": 1.0,
            "relationships": 0.9,
            "health": 0.8,
            "learning": 0.7,
            "creativity": 0.6,
            "travel": 0.5,
            "finance": 0.4,
            "spirituality": 0.3
        }
        
        for goal in goals:
            if goal in goal_weights and goals_start_idx < self.vector_size:
                vector[goals_start_idx] = goal_weights[goal]
                goals_start_idx += 1
        
        # Fill remaining dimensions with derived features
        self._fill_derived_dimensions(vector, personality_data)
        
        # Normalize vector
        vector = self._normalize_vector(vector)
        
        return vector
    
    def _fill_derived_dimensions(self, vector: List[float], personality_data: Dict[str, Any]):
        """Fill remaining vector dimensions with derived psychological features"""
        
        personality = personality_data.get("personality", {})
        
        # Derived features starting from index 25
        derived_start = 25
        
        if derived_start < self.vector_size:
            # Psychological balance scores
            openness = personality.get("openness", 0.5)
            conscientiousness = personality.get("conscientiousness", 0.5)
            extraversion = personality.get("extraversion", 0.5)
            
            # Balance indicators
            vector[derived_start] = abs(openness - conscientiousness)  # Structure vs Creativity balance
            vector[derived_start + 1] = (openness + extraversion) / 2  # Social creativity
            vector[derived_start + 2] = (conscientiousness + extraversion) / 2  # Leadership potential
            
            # Fill remaining with noise + patterns (simplified)
            for i in range(derived_start + 3, min(self.vector_size, derived_start + 50)):
                # Combination features based on personality traits
                base_value = (openness + conscientiousness + extraversion) / 3
                variation = (i % 7) * 0.1 - 0.3  # Add some variation
                vector[i] = max(0.0, min(1.0, base_value + variation))
    
    def _normalize_vector(self, vector: List[float]) -> List[float]:
        """Normalize vector to unit length"""
        
        # Convert to numpy for easier computation
        vec = np.array(vector)
        
        # Calculate L2 norm
        norm = np.linalg.norm(vec)
        
        if norm > 0:
            vec = vec / norm
        
        return vec.tolist()
    
    def _validate_vector(self, vector: List[float]) -> bool:
        """Validate personality vector"""
        
        if len(vector) != self.vector_size:
            return False
        
        # Check for NaN or infinite values
        if not all(isinstance(x, (int, float)) and np.isfinite(x) for x in vector):
            return False
        
        # Check if vector is not all zeros
        if all(x == 0 for x in vector):
            return False
        
        return True
    
    def _analyze_similarity_patterns(self, similar_personalities: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze patterns in similar personalities"""
        
        if not similar_personalities:
            return {"pattern": "no_similar_personalities"}
        
        # Analyze similarity scores
        scores = [p["similarity_score"] for p in similar_personalities]
        
        # Analyze personality types
        personality_types = [p["personality_type"] for p in similar_personalities if p.get("personality_type")]
        type_distribution = {}
        for ptype in personality_types:
            type_distribution[ptype] = type_distribution.get(ptype, 0) + 1
        
        return {
            "average_similarity": np.mean(scores) if scores else 0.0,
            "similarity_range": {"min": min(scores), "max": max(scores)} if scores else None,
            "personality_type_distribution": type_distribution,
            "most_common_type": max(type_distribution.items(), key=lambda x: x[1])[0] if type_distribution else None
        }
    
    def _analyze_trait_distribution(self, trait_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze trait distribution in search results"""
        
        if not trait_results:
            return {"analysis": "no_results"}
        
        # Analyze confidence scores
        confidence_scores = [r["confidence"] for r in trait_results if r.get("confidence")]
        
        # Analyze personality types
        types = [r["personality_type"] for r in trait_results if r.get("personality_type")]
        type_counts = {}
        for ptype in types:
            type_counts[ptype] = type_counts.get(ptype, 0) + 1
        
        return {
            "results_count": len(trait_results),
            "average_confidence": np.mean(confidence_scores) if confidence_scores else 0.0,
            "personality_type_distribution": type_counts
        }
    
    async def _calculate_space_analytics(self, collection_stats: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate analytics about the personality vector space"""
        
        total_vectors = collection_stats.get("total_vectors", 0)
        
        # Calculate space utilization metrics
        space_density = total_vectors / 1000.0  # Relative to expected user base
        
        # Personality type diversity
        type_distribution = collection_stats.get("personality_type_distribution", {})
        diversity_score = len(type_distribution) / 10.0  # Relative to expected types
        
        return {
            "space_utilization": {
                "total_vectors": total_vectors,
                "space_density": round(space_density, 3),
                "diversity_score": round(diversity_score, 3)
            },
            "quality_metrics": {
                "indexed_percentage": collection_stats.get("indexed_vectors_count", 0) / max(1, total_vectors),
                "collection_status": collection_stats.get("status", "unknown")
            }
        }
    
    def _analyze_personality_position(self, user_vector: Dict[str, Any], 
                                    similar_personalities: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze user's position in personality space"""
        
        position_analysis = {
            "vector_id": user_vector.get("point_id"),
            "similar_count": len(similar_personalities),
            "uniqueness_indicators": {
                "has_close_matches": len(similar_personalities) > 0,
                "closest_similarity": similar_personalities[0]["similarity_score"] if similar_personalities else 0.0
            }
        }
        
        # Analyze personality type relative to similar users
        if similar_personalities:
            user_type = user_vector.get("payload", {}).get("personality_type")
            similar_types = [p["personality_type"] for p in similar_personalities]
            
            position_analysis["type_consistency"] = {
                "user_type": user_type,
                "matches_similar": user_type in similar_types,
                "similar_types": list(set(similar_types))
            }
        
        return position_analysis
    
    def _generate_dimensional_insights(self, user_vector: Dict[str, Any]) -> List[Dict[str, str]]:
        """Generate insights about user's dimensional profile"""
        
        insights = []
        
        # Analyze payload data
        payload = user_vector.get("payload", {})
        personality_data = payload.get("personality_data", {})
        
        if personality_data:
            personality = personality_data.get("personality", {})
            
            # Find dominant traits
            if personality:
                max_trait = max(personality.items(), key=lambda x: x[1])
                insights.append({
                    "type": "dominant_trait",
                    "description": f"Ваша доминирующая черта: {max_trait[0]} ({max_trait[1]:.2f})"
                })
                
                min_trait = min(personality.items(), key=lambda x: x[1])
                insights.append({
                    "type": "development_area",
                    "description": f"Область для развития: {min_trait[0]} ({min_trait[1]:.2f})"
                })
        
        # Add vector quality insight
        confidence = payload.get("confidence_score", 0.0)
        insights.append({
            "type": "data_quality",
            "description": f"Уверенность в профиле: {confidence:.1%}"
        })
        
        return insights
    
    def _calculate_uniqueness_score(self, user_vector: Dict[str, Any], 
                                  similar_personalities: List[Dict[str, Any]]) -> float:
        """Calculate how unique the user's personality is"""
        
        if not similar_personalities:
            return 1.0  # Very unique if no similar personalities
        
        # Calculate uniqueness based on similarity scores
        highest_similarity = similar_personalities[0]["similarity_score"]
        
        # Uniqueness is inverse of similarity
        uniqueness = 1.0 - highest_similarity
        
        # Factor in number of similar personalities
        uniqueness *= (1.0 - len(similar_personalities) / 20.0)  # Penalize many similar personalities
        
        return max(0.0, min(1.0, uniqueness))
    
    def _assess_vector_quality(self, user_vector: Dict[str, Any]) -> Dict[str, Any]:
        """Assess the quality of the user's personality vector"""
        
        payload = user_vector.get("payload", {})
        
        quality_metrics = {
            "confidence_score": payload.get("confidence_score", 0.0),
            "data_completeness": self._assess_data_completeness(payload),
            "vector_consistency": self._assess_vector_consistency(user_vector),
            "last_updated": payload.get("created_at", "unknown")
        }
        
        # Overall quality score
        quality_score = (
            quality_metrics["confidence_score"] * 0.4 +
            quality_metrics["data_completeness"] * 0.3 +
            quality_metrics["vector_consistency"] * 0.3
        )
        
        quality_metrics["overall_quality"] = quality_score
        quality_metrics["quality_level"] = self._get_quality_level(quality_score)
        
        return quality_metrics
    
    def _assess_data_completeness(self, payload: Dict[str, Any]) -> float:
        """Assess completeness of personality data"""
        
        personality_data = payload.get("personality_data", {})
        
        completeness = 0.0
        
        # Check personality traits
        personality = personality_data.get("personality", {})
        if personality:
            expected_traits = ["openness", "conscientiousness", "extraversion", "agreeableness", "neuroticism"]
            present_traits = sum(1 for trait in expected_traits if trait in personality)
            completeness += (present_traits / len(expected_traits)) * 0.5
        
        # Check values
        values = personality_data.get("values", {})
        if values:
            completeness += min(0.3, len(values) / 5.0 * 0.3)  # Up to 0.3 for values
        
        # Check goals
        goals = personality_data.get("goals", [])
        if goals:
            completeness += min(0.2, len(goals) / 3.0 * 0.2)  # Up to 0.2 for goals
        
        return min(1.0, completeness)
    
    def _assess_vector_consistency(self, user_vector: Dict[str, Any]) -> float:
        """Assess internal consistency of the vector"""
        
        # Simplified consistency check
        # In production would check for contradictory patterns
        
        vector_data = user_vector.get("vector", [])
        
        if not vector_data:
            return 0.0
        
        # Check for extreme values or patterns
        vec = np.array(vector_data)
        
        # Consistency based on value distribution
        std_dev = np.std(vec)
        mean_val = np.mean(vec)
        
        # Good consistency has moderate standard deviation
        consistency = 1.0 - abs(std_dev - 0.3)  # Optimal std around 0.3
        consistency = max(0.0, min(1.0, consistency))
        
        return consistency
    
    def _get_quality_level(self, quality_score: float) -> str:
        """Get quality level description"""
        
        if quality_score >= 0.8:
            return "excellent"
        elif quality_score >= 0.6:
            return "good"
        elif quality_score >= 0.4:
            return "moderate"
        else:
            return "needs_improvement"
    
    async def _get_personality_type_distribution(self) -> Dict[str, int]:
        """Get distribution of personality types"""
        
        # Simplified implementation
        # In production would query the actual vector database
        
        return {
            "extravert_creative": 25,
            "extravert_organized": 20,
            "introvert_creative": 18,
            "introvert_organized": 15,
            "balanced": 22
        }
    
    def _perform_simple_clustering(self, personality_types: Dict[str, int], 
                                 min_cluster_size: int) -> List[Dict[str, Any]]:
        """Perform simple clustering based on personality types"""
        
        clusters = []
        
        for personality_type, count in personality_types.items():
            if count >= min_cluster_size:
                clusters.append({
                    "cluster_id": f"cluster_{personality_type}",
                    "personality_type": personality_type,
                    "size": count,
                    "characteristics": self._get_cluster_characteristics(personality_type)
                })
        
        return clusters
    
    def _analyze_clusters(self, clusters: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze cluster characteristics"""
        
        if not clusters:
            return {"analysis": "no_clusters_found"}
        
        total_size = sum(c["size"] for c in clusters)
        largest_cluster = max(clusters, key=lambda x: x["size"])
        smallest_cluster = min(clusters, key=lambda x: x["size"])
        
        return {
            "cluster_count": len(clusters),
            "total_personalities": total_size,
            "largest_cluster": {
                "type": largest_cluster["personality_type"],
                "size": largest_cluster["size"],
                "percentage": (largest_cluster["size"] / total_size) * 100
            },
            "smallest_cluster": {
                "type": smallest_cluster["personality_type"], 
                "size": smallest_cluster["size"],
                "percentage": (smallest_cluster["size"] / total_size) * 100
            },
            "cluster_balance": self._assess_cluster_balance(clusters)
        }
    
    def _get_cluster_characteristics(self, personality_type: str) -> Dict[str, Any]:
        """Get characteristics of a personality cluster"""
        
        characteristics = {
            "extravert_creative": {
                "traits": ["high_openness", "high_extraversion"],
                "strengths": ["creativity", "social_energy", "innovation"],
                "growth_areas": ["focus", "routine_building"]
            },
            "extravert_organized": {
                "traits": ["high_extraversion", "high_conscientiousness"],
                "strengths": ["leadership", "organization", "motivation"],
                "growth_areas": ["flexibility", "stress_management"]
            },
            "introvert_creative": {
                "traits": ["high_openness", "low_extraversion"],
                "strengths": ["deep_thinking", "creativity", "independence"],
                "growth_areas": ["social_connection", "self_promotion"]
            },
            "introvert_organized": {
                "traits": ["low_extraversion", "high_conscientiousness"],
                "strengths": ["attention_to_detail", "reliability", "planning"],
                "growth_areas": ["spontaneity", "social_interaction"]
            },
            "balanced": {
                "traits": ["moderate_all_traits"],
                "strengths": ["adaptability", "balance", "versatility"],
                "growth_areas": ["specialization", "distinctive_strengths"]
            }
        }
        
        return characteristics.get(personality_type, {"traits": [], "strengths": [], "growth_areas": []})
    
    def _assess_cluster_balance(self, clusters: List[Dict[str, Any]]) -> str:
        """Assess balance across clusters"""
        
        sizes = [c["size"] for c in clusters]
        std_dev = np.std(sizes)
        mean_size = np.mean(sizes)
        
        coefficient_of_variation = std_dev / mean_size if mean_size > 0 else 0
        
        if coefficient_of_variation < 0.3:
            return "well_balanced"
        elif coefficient_of_variation < 0.6:
            return "moderately_balanced"
        else:
            return "imbalanced"
    
    def _initialize_dimension_mapping(self) -> Dict[str, int]:
        """Initialize mapping of personality dimensions to vector indices"""
        
        # This would be a comprehensive mapping in production
        # For now, simplified mapping for key dimensions
        
        mapping = {
            "openness": 0,
            "conscientiousness": 1,
            "extraversion": 2,
            "agreeableness": 3,
            "neuroticism": 4,
            # Values start at index 5
            "family_value": 5,
            "career_value": 6,
            "health_value": 7,
            "creativity_value": 8,
            "security_value": 9,
            # Goals start at index 15
            "career_goal": 15,
            "relationship_goal": 16,
            "health_goal": 17,
            "learning_goal": 18
            # Additional derived dimensions would continue...
        }
        
        return mapping