import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    VectorParams, Distance, CreateCollection, PointStruct, 
    UpdateStatus, SearchRequest, Filter, FieldCondition, MatchValue
)
import numpy as np
from openai import AsyncOpenAI

from ..core.config import settings


class VectorService:
    """
    Service for managing personality vectors in Qdrant.
    Handles embedding generation, storage, and semantic search.
    """
    
    def __init__(self):
        self.qdrant_client = AsyncQdrantClient(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key,
            timeout=60
        )
        self.openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
        
        # Collection names
        self.personality_collection = "personality_profiles"
        self.chat_collection = "chat_embeddings"
        self.insights_collection = "user_insights"
        
        # Embedding model
        self.embedding_model = "text-embedding-3-small"  # More cost-effective
        self.vector_size = 1536  # text-embedding-3-small dimension
    
    async def initialize_collections(self):
        """Initialize Qdrant collections if they don't exist"""
        
        collections = [
            (self.personality_collection, "User personality vectors and traits"),
            (self.chat_collection, "Chat message embeddings for context"),
            (self.insights_collection, "AI-generated insights and patterns")
        ]
        
        for collection_name, description in collections:
            try:
                await self.qdrant_client.create_collection(
                    collection_name=collection_name,
                    vectors_config=VectorParams(
                        size=self.vector_size,
                        distance=Distance.COSINE
                    ),
                    optimizers_config={
                        "default_segment_number": 2,
                        "memmap_threshold": 20000
                    }
                )
                print(f"Created collection: {collection_name}")
                
            except Exception as e:
                # Collection might already exist
                print(f"Collection {collection_name} might already exist: {e}")
    
    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding using OpenAI API"""
        
        try:
            response = await self.openai_client.embeddings.create(
                model=self.embedding_model,
                input=text,
                encoding_format="float"
            )
            
            return response.data[0].embedding
            
        except Exception as e:
            raise Exception(f"Failed to generate embedding: {str(e)}")
    
    async def store_personality_profile(
        self,
        user_id: str,
        personality_data: Dict[str, Any],
        text_description: str
    ) -> str:
        """
        Store user personality profile as vector.
        
        Args:
            user_id: Telegram user ID
            personality_data: Big Five + values + goals data
            text_description: Human-readable description for embedding
        
        Returns:
            point_id: Qdrant point ID
        """
        
        # Generate embedding from text description
        embedding = await self.generate_embedding(text_description)
        
        point_id = str(uuid.uuid4())
        
        point = PointStruct(
            id=point_id,
            vector=embedding,
            payload={
                "user_id": user_id,
                "type": "personality_profile",
                "personality_data": personality_data,
                "text_description": text_description,
                "created_at": datetime.utcnow().isoformat(),
                "version": personality_data.get("version", 1)
            }
        )
        
        await self.qdrant_client.upsert(
            collection_name=self.personality_collection,
            points=[point]
        )
        
        return point_id
    
    async def store_chat_embedding(
        self,
        user_id: str,
        message_content: str,
        message_type: str = "user",
        insights: Optional[Dict] = None
    ) -> str:
        """Store chat message embedding for context search"""
        
        embedding = await self.generate_embedding(message_content)
        
        point_id = str(uuid.uuid4())
        
        point = PointStruct(
            id=point_id,
            vector=embedding,
            payload={
                "user_id": user_id,
                "type": "chat_message",
                "content": message_content,
                "message_type": message_type,
                "insights": insights or {},
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        
        await self.qdrant_client.upsert(
            collection_name=self.chat_collection,
            points=[point]
        )
        
        return point_id
    
    async def search_similar_personality_patterns(
        self,
        query_text: str,
        user_id: Optional[str] = None,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Search for similar personality patterns.
        
        Args:
            query_text: Search query
            user_id: Limit to specific user (optional)
            limit: Number of results
        
        Returns:
            List of similar personality profiles
        """
        
        query_embedding = await self.generate_embedding(query_text)
        
        search_filter = None
        if user_id:
            search_filter = Filter(
                must=[
                    FieldCondition(
                        key="user_id",
                        match=MatchValue(value=user_id)
                    )
                ]
            )
        
        search_result = await self.qdrant_client.search(
            collection_name=self.personality_collection,
            query_vector=query_embedding,
            query_filter=search_filter,
            limit=limit,
            with_payload=True
        )
        
        return [
            {
                "score": hit.score,
                "personality_data": hit.payload.get("personality_data"),
                "description": hit.payload.get("text_description"),
                "user_id": hit.payload.get("user_id"),
                "created_at": hit.payload.get("created_at")
            }
            for hit in search_result
        ]
    
    async def search_user_chat_context(
        self,
        user_id: str,
        query_text: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Search user's chat history for relevant context"""
        
        query_embedding = await self.generate_embedding(query_text)
        
        search_filter = Filter(
            must=[
                FieldCondition(
                    key="user_id",
                    match=MatchValue(value=user_id)
                ),
                FieldCondition(
                    key="type",
                    match=MatchValue(value="chat_message")
                )
            ]
        )
        
        search_result = await self.qdrant_client.search(
            collection_name=self.chat_collection,
            query_vector=query_embedding,
            query_filter=search_filter,
            limit=limit,
            with_payload=True
        )
        
        return [
            {
                "score": hit.score,
                "content": hit.payload.get("content"),
                "message_type": hit.payload.get("message_type"),
                "insights": hit.payload.get("insights"),
                "timestamp": hit.payload.get("timestamp")
            }
            for hit in search_result
        ]
    
    async def store_insight(
        self,
        user_id: str,
        insight_text: str,
        insight_type: str,
        metadata: Optional[Dict] = None
    ) -> str:
        """Store AI-generated insight with vector for future retrieval"""
        
        embedding = await self.generate_embedding(insight_text)
        
        point_id = str(uuid.uuid4())
        
        point = PointStruct(
            id=point_id,
            vector=embedding,
            payload={
                "user_id": user_id,
                "type": "insight",
                "insight_type": insight_type,  # pattern, recommendation, analysis
                "text": insight_text,
                "metadata": metadata or {},
                "created_at": datetime.utcnow().isoformat()
            }
        )
        
        await self.qdrant_client.upsert(
            collection_name=self.insights_collection,
            points=[point]
        )
        
        return point_id
    
    async def find_user_patterns(
        self,
        user_id: str,
        pattern_type: str = "behavioral",
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Find behavioral/emotional patterns for specific user"""
        
        # Create search query for patterns
        pattern_queries = {
            "behavioral": "behavioral patterns habits routines consistent actions",
            "emotional": "emotional patterns feelings mood emotional responses",
            "cognitive": "thinking patterns decision making cognitive biases thoughts",
            "social": "social patterns relationships communication interpersonal"
        }
        
        query_text = pattern_queries.get(pattern_type, pattern_queries["behavioral"])
        
        # Search in both chat history and insights
        chat_patterns = await self.search_user_chat_context(user_id, query_text, limit)
        
        search_filter = Filter(
            must=[
                FieldCondition(key="user_id", match=MatchValue(value=user_id)),
                FieldCondition(key="insight_type", match=MatchValue(value="pattern"))
            ]
        )
        
        query_embedding = await self.generate_embedding(query_text)
        
        insight_patterns = await self.qdrant_client.search(
            collection_name=self.insights_collection,
            query_vector=query_embedding,
            query_filter=search_filter,
            limit=limit,
            with_payload=True
        )
        
        insights = [
            {
                "type": "insight",
                "score": hit.score,
                "text": hit.payload.get("text"),
                "insight_type": hit.payload.get("insight_type"),
                "metadata": hit.payload.get("metadata"),
                "created_at": hit.payload.get("created_at")
            }
            for hit in insight_patterns
        ]
        
        # Combine and sort by relevance score
        all_patterns = []
        
        for pattern in chat_patterns:
            pattern["type"] = "chat_context"
            all_patterns.append(pattern)
        
        all_patterns.extend(insights)
        all_patterns.sort(key=lambda x: x["score"], reverse=True)
        
        return all_patterns[:limit]
    
    async def get_user_profile_context(
        self,
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get user's latest personality profile for context"""
        
        search_filter = Filter(
            must=[
                FieldCondition(key="user_id", match=MatchValue(value=user_id)),
                FieldCondition(key="type", match=MatchValue(value="personality_profile"))
            ]
        )
        
        # Get most recent profile (search with generic query)
        generic_embedding = await self.generate_embedding("personality profile traits")
        
        result = await self.qdrant_client.search(
            collection_name=self.personality_collection,
            query_vector=generic_embedding,
            query_filter=search_filter,
            limit=1,
            with_payload=True
        )
        
        if result:
            hit = result[0]
            return {
                "personality_data": hit.payload.get("personality_data"),
                "description": hit.payload.get("text_description"),
                "version": hit.payload.get("version"),
                "created_at": hit.payload.get("created_at")
            }
        
        return None