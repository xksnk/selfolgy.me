"""
Vector Database Data Access Object - Clean operations for Qdrant vector database
"""
from qdrant_client import QdrantClient
from qdrant_client.http import models
from typing import Dict, List, Any, Optional, Tuple
import numpy as np
import json
from datetime import datetime

from core.config import get_config
from core.logging import vector_logger


class VectorDAO:
    """Data Access Object for vector database operations"""
    
    def __init__(self, client: Optional[QdrantClient] = None):
        self.config = get_config()
        self.client = client or QdrantClient(
            host=self.config.vector.host,
            port=self.config.vector.port
        )
        self.collection_name = self.config.vector.collection_name
        self.vector_size = self.config.vector.vector_size
        self.logger = vector_logger
    
    async def initialize_collection(self) -> bool:
        """Initialize vector collection if it doesn't exist"""
        
        try:
            # Check if collection exists
            collections = self.client.get_collections()
            existing_names = [c.name for c in collections.collections]
            
            if self.collection_name not in existing_names:
                # Create collection
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=models.VectorParams(
                        size=self.vector_size,
                        distance=models.Distance.COSINE
                    )
                )
                self.logger.info(f"Created vector collection: {self.collection_name}")
            
            # Create index for faster search
            self.client.create_payload_index(
                collection_name=self.collection_name,
                field_name="user_id",
                field_schema=models.PayloadSchemaType.KEYWORD
            )
            
            self.client.create_payload_index(
                collection_name=self.collection_name,
                field_name="personality_type",
                field_schema=models.PayloadSchemaType.KEYWORD
            )
            
            self.logger.info("Vector collection initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize vector collection: {e}")
            return False
    
    async def store_personality_vector(self, user_id: str, personality_vector: List[float],
                                     personality_data: Dict[str, Any],
                                     text_description: str) -> str:
        """Store personality vector for user"""
        
        try:
            # Validate vector dimensions
            if len(personality_vector) != self.vector_size:
                raise ValueError(f"Vector size {len(personality_vector)} doesn't match expected {self.vector_size}")
            
            # Create unique point ID
            point_id = f"user_{user_id}_{int(datetime.utcnow().timestamp())}"
            
            # Prepare metadata
            payload = {
                "user_id": user_id,
                "personality_data": personality_data,
                "text_description": text_description,
                "personality_type": self._classify_personality_type(personality_data),
                "created_at": datetime.utcnow().isoformat(),
                "vector_version": personality_data.get("version", 1),
                "confidence_score": personality_data.get("confidence", 0.5)
            }
            
            # Store vector
            self.client.upsert(
                collection_name=self.collection_name,
                points=[
                    models.PointStruct(
                        id=point_id,
                        vector=personality_vector,
                        payload=payload
                    )
                ]
            )
            
            self.logger.log_user_action("personality_vector_stored", user_id, point_id=point_id)
            return point_id
            
        except Exception as e:
            self.logger.error(f"Failed to store personality vector for user {user_id}: {e}")
            raise
    
    async def update_personality_vector(self, point_id: str, user_id: str,
                                      dimension_updates: Dict[str, float],
                                      confidence: float = 0.5) -> bool:
        """Update specific dimensions of personality vector"""
        
        try:
            # Get current vector
            current = self.client.retrieve(
                collection_name=self.collection_name,
                ids=[point_id],
                with_vectors=True
            )
            
            if not current:
                self.logger.warning(f"Vector point {point_id} not found for update")
                return False
            
            current_vector = current[0].vector
            current_payload = current[0].payload
            
            # Apply dimension updates (this would need mapping from dimension names to vector indices)
            updated_vector = self._apply_dimension_updates(current_vector, dimension_updates)
            
            # Update payload
            current_payload["last_updated"] = datetime.utcnow().isoformat()
            current_payload["dimension_updates"] = dimension_updates
            current_payload["update_confidence"] = confidence
            
            # Store updated vector
            self.client.upsert(
                collection_name=self.collection_name,
                points=[
                    models.PointStruct(
                        id=point_id,
                        vector=updated_vector,
                        payload=current_payload
                    )
                ]
            )
            
            self.logger.log_user_action("personality_vector_updated", user_id, 
                                       point_id=point_id, updates=dimension_updates)
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to update personality vector {point_id}: {e}")
            return False
    
    async def find_similar_personalities(self, user_id: str, limit: int = 10,
                                       score_threshold: float = 0.7) -> List[Dict[str, Any]]:
        """Find users with similar personality vectors"""
        
        try:
            # Get user's current vector
            user_vector = await self.get_user_vector(user_id)
            if not user_vector:
                return []
            
            # Search for similar vectors
            search_result = self.client.search(
                collection_name=self.collection_name,
                query_vector=user_vector["vector"],
                limit=limit + 1,  # +1 to exclude self
                score_threshold=score_threshold,
                with_payload=True
            )
            
            # Filter out self and format results
            similar_users = []
            for hit in search_result:
                if hit.payload.get("user_id") != user_id:
                    similar_users.append({
                        "user_id": hit.payload.get("user_id"),
                        "similarity_score": hit.score,
                        "personality_type": hit.payload.get("personality_type"),
                        "personality_data": hit.payload.get("personality_data"),
                        "point_id": hit.id
                    })
            
            self.logger.log_user_action("similar_personalities_found", user_id, 
                                       count=len(similar_users))
            return similar_users
            
        except Exception as e:
            self.logger.error(f"Failed to find similar personalities for user {user_id}: {e}")
            return []
    
    async def get_user_vector(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user's latest personality vector"""
        
        try:
            # Search for user's latest vector
            search_result = self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="user_id",
                            match=models.MatchValue(value=user_id)
                        )
                    ]
                ),
                limit=1,
                with_vectors=True,
                with_payload=True
            )
            
            if search_result and len(search_result[0]) > 0:
                point = search_result[0][0]
                return {
                    "point_id": point.id,
                    "vector": point.vector,
                    "payload": point.payload,
                    "user_id": user_id
                }
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to get vector for user {user_id}: {e}")
            return None
    
    async def search_by_personality_traits(self, trait_query: Dict[str, Any],
                                         limit: int = 20) -> List[Dict[str, Any]]:
        """Search for users by specific personality traits"""
        
        try:
            # Build filter based on personality traits
            filters = []
            
            # Personality type filter
            if "personality_type" in trait_query:
                filters.append(
                    models.FieldCondition(
                        key="personality_type",
                        match=models.MatchValue(value=trait_query["personality_type"])
                    )
                )
            
            # Confidence threshold
            if "min_confidence" in trait_query:
                filters.append(
                    models.FieldCondition(
                        key="confidence_score",
                        range=models.Range(gte=trait_query["min_confidence"])
                    )
                )
            
            # Search with filters
            search_result = self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=models.Filter(must=filters) if filters else None,
                limit=limit,
                with_payload=True
            )
            
            # Format results
            results = []
            if search_result and len(search_result[0]) > 0:
                for point in search_result[0]:
                    results.append({
                        "point_id": point.id,
                        "user_id": point.payload.get("user_id"),
                        "personality_data": point.payload.get("personality_data"),
                        "personality_type": point.payload.get("personality_type"),
                        "confidence": point.payload.get("confidence_score", 0.0)
                    })
            
            self.logger.info(f"Found {len(results)} users matching trait query")
            return results
            
        except Exception as e:
            self.logger.error(f"Failed to search by personality traits: {e}")
            return []
    
    async def delete_user_vectors(self, user_id: str) -> bool:
        """Delete all vectors for a user (GDPR compliance)"""
        
        try:
            # Find all user vectors
            search_result = self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="user_id",
                            match=models.MatchValue(value=user_id)
                        )
                    ]
                ),
                limit=100,  # Should be enough for one user
                with_payload=False
            )
            
            if search_result and len(search_result[0]) > 0:
                point_ids = [point.id for point in search_result[0]]
                
                # Delete points
                self.client.delete(
                    collection_name=self.collection_name,
                    points_selector=models.PointIdsList(points=point_ids)
                )
                
                self.logger.log_user_action("user_vectors_deleted", user_id, 
                                           deleted_count=len(point_ids))
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to delete vectors for user {user_id}: {e}")
            return False
    
    async def get_collection_statistics(self) -> Dict[str, Any]:
        """Get vector collection statistics"""
        
        try:
            # Collection info
            collection_info = self.client.get_collection(self.collection_name)
            
            # Count by personality type
            personality_types = await self._count_by_field("personality_type")
            
            # Recent activity (points created in last 24 hours)
            # Note: This would require timestamp-based filtering
            
            return {
                "total_vectors": collection_info.points_count,
                "vector_size": collection_info.config.params.vectors.size,
                "personality_type_distribution": personality_types,
                "collection_status": collection_info.status,
                "indexed_vectors": collection_info.indexed_vectors_count
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get collection statistics: {e}")
            return {}
    
    def _classify_personality_type(self, personality_data: Dict[str, Any]) -> str:
        """Classify personality type based on Big Five scores"""
        
        personality = personality_data.get("personality", {})
        
        # Simple classification based on dominant traits
        if personality.get("extraversion", 0) > 0.7:
            if personality.get("openness", 0) > 0.7:
                return "extravert_open"
            else:
                return "extravert_conventional"
        elif personality.get("extraversion", 0) < 0.3:
            if personality.get("conscientiousness", 0) > 0.7:
                return "introvert_organized"
            else:
                return "introvert_flexible"
        else:
            return "ambivert"
    
    def _apply_dimension_updates(self, current_vector: List[float], 
                               updates: Dict[str, float]) -> List[float]:
        """Apply dimension updates to vector (placeholder implementation)"""
        
        # This would need a proper mapping from dimension names to vector indices
        # For now, return the current vector unchanged
        # In a real implementation, you'd map dimension names to specific indices
        # and apply the updates accordingly
        
        updated_vector = current_vector.copy()
        
        # Placeholder: apply small random changes based on updates
        for dimension, value in updates.items():
            # This is a simplified example - real implementation would map dimensions properly
            pass
        
        return updated_vector
    
    async def _count_by_field(self, field_name: str) -> Dict[str, int]:
        """Count occurrences by field value"""
        
        try:
            # This is a simplified implementation
            # In practice, you might need to scroll through all points and count manually
            # or use aggregation features if available in newer Qdrant versions
            
            all_points = self.client.scroll(
                collection_name=self.collection_name,
                limit=1000,  # Adjust based on your dataset size
                with_payload=True
            )
            
            counts = {}
            if all_points and len(all_points[0]) > 0:
                for point in all_points[0]:
                    field_value = point.payload.get(field_name, "unknown")
                    counts[field_value] = counts.get(field_value, 0) + 1
            
            return counts
            
        except Exception as e:
            self.logger.error(f"Failed to count by field {field_name}: {e}")
            return {}