"""
Vector Storage Service для сохранения embeddings в Qdrant

Работает с 5 коллекциями:
- episodic_memory (768d)
- semantic_knowledge (2048d)
- emotional_thematic (1536d)
- psychological_constructs (1024d)
- meta_patterns (1024d)
"""

import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, Filter, FieldCondition, MatchValue
import numpy as np
import logging

from selfology_bot.services.embedding_service import get_embedding_service
from core.error_collector import error_collector

logger = logging.getLogger(__name__)


class VectorStorageService:
    """
    Unified service для хранения и поиска в 5 коллекциях Qdrant
    """

    def __init__(self, host: str = "localhost", port: int = 6333):
        self.client = QdrantClient(host=host, port=port)
        self.embedding_service = get_embedding_service()

        # Коллекции и их размерности
        self.collections = {
            "episodic_memory": 768,
            "semantic_knowledge": 2048,
            "emotional_thematic": 1536,
            "psychological_constructs": 1024,
            "meta_patterns": 1024
        }

        logger.info(f"VectorStorageService initialized (Qdrant: {host}:{port})")

    # ===================
    # SETUP METHODS
    # ===================

    async def setup_collections(self) -> bool:
        """
        Создание 5 коллекций для VectorStorageService

        Вызывается при старте онбординга ПЕРЕД первым использованием
        """
        from qdrant_client.models import VectorParams, Distance

        try:
            logger.info("🏗️ Setting up VectorStorageService collections...")

            collections_config = [
                {
                    "name": "episodic_memory",
                    "size": 768,  # RuBERT
                    "distance": Distance.COSINE,
                    "description": "Raw user answers for semantic search"
                },
                {
                    "name": "semantic_knowledge",
                    "size": 2048,  # OpenAI text-embedding-3-large
                    "distance": Distance.COSINE,
                    "description": "AI analyses and psychological insights"
                },
                {
                    "name": "emotional_thematic",
                    "size": 1536,  # Hybrid (RuBERT 768 + emotion 768)
                    "distance": Distance.COSINE,
                    "description": "Emotional patterns and themes"
                },
                {
                    "name": "psychological_constructs",
                    "size": 1024,  # OpenAI 1024d
                    "distance": Distance.COSINE,
                    "description": "Core beliefs, distortions, defenses"
                },
                {
                    "name": "meta_patterns",
                    "size": 1024,  # OpenAI 1024d
                    "distance": Distance.COSINE,
                    "description": "Blind spots, growth areas, meta-patterns"
                }
            ]

            created_count = 0
            for config in collections_config:
                try:
                    # Check if exists
                    existing = self.client.get_collections()
                    collection_names = [c.name for c in existing.collections]

                    if config["name"] in collection_names:
                        logger.info(f"✅ Collection '{config['name']}' already exists")
                        created_count += 1
                        continue

                    # Create collection
                    self.client.create_collection(
                        collection_name=config["name"],
                        vectors_config=VectorParams(
                            size=config["size"],
                            distance=config["distance"]
                        )
                    )
                    logger.info(f"✅ Created '{config['name']}' ({config['description']})")
                    created_count += 1

                except Exception as e:
                    logger.error(f"❌ Failed to create '{config['name']}': {e}")
                    raise  # НЕ подавляем ошибку

            success = created_count == len(collections_config)
            if success:
                logger.info(f"🎉 VectorStorageService: {created_count} collections ready")

            return success

        except Exception as e:
            logger.error(f"❌ VectorStorageService setup failed: {e}")
            return False

    # ===================
    # STORE METHODS
    # ===================

    async def store_episodic(
        self,
        user_id: int,
        text: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Сохранить сырой ответ пользователя в episodic_memory

        Returns: point_id (UUID)
        """
        # Generate embedding
        embedding = self.embedding_service.encode_episodic(text)

        # Create point
        point_id = str(uuid.uuid4())
        payload = {
            "user_id": user_id,
            "text": text[:500],  # Truncate for payload
            "created_at": datetime.now(timezone.utc).isoformat(),
            "type": "user_answer",
            **(metadata or {})
        }

        # Upsert to Qdrant
        self.client.upsert(
            collection_name="episodic_memory",
            points=[PointStruct(
                id=point_id,
                vector=embedding.tolist(),
                payload=payload
            )]
        )

        logger.info(f"✅ Stored episodic memory for user {user_id}: {point_id}")
        return point_id

    async def store_semantic(
        self,
        user_id: int,
        analysis_text: str,
        turn_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Сохранить AI анализ в semantic_knowledge

        Returns: point_id (UUID)
        """
        embedding = self.embedding_service.encode_semantic(analysis_text)

        point_id = str(uuid.uuid4())
        payload = {
            "user_id": user_id,
            "analysis": analysis_text[:1000],
            "turn_id": turn_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "type": "ai_analysis",
            **(metadata or {})
        }

        self.client.upsert(
            collection_name="semantic_knowledge",
            points=[PointStruct(
                id=point_id,
                vector=embedding.tolist(),
                payload=payload
            )]
        )

        logger.info(f"✅ Stored semantic knowledge for user {user_id}: {point_id}")
        return point_id

    async def store_emotional(
        self,
        user_id: int,
        text: str,
        emotion: str,
        intensity: float = 0.5,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Сохранить эмоциональный паттерн в emotional_thematic

        Returns: point_id (UUID)
        """
        embedding = self.embedding_service.encode_emotional(text, emotion)

        point_id = str(uuid.uuid4())
        payload = {
            "user_id": user_id,
            "text": text[:500],
            "emotion": emotion,
            "intensity": intensity,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "type": "emotional_pattern",
            **(metadata or {})
        }

        self.client.upsert(
            collection_name="emotional_thematic",
            points=[PointStruct(
                id=point_id,
                vector=embedding.tolist(),
                payload=payload
            )]
        )

        logger.info(f"✅ Stored emotional pattern for user {user_id}: {emotion}")
        return point_id

    async def store_construct(
        self,
        user_id: int,
        construct_text: str,
        construct_type: str,  # 'core_belief', 'defense_mechanism', etc
        confidence: float = 0.5,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Сохранить психологический конструкт в psychological_constructs

        Returns: point_id (UUID)
        """
        embedding = self.embedding_service.encode_construct(construct_text)

        point_id = str(uuid.uuid4())
        payload = {
            "user_id": user_id,
            "text": construct_text,
            "construct_type": construct_type,
            "confidence": confidence,
            "created_at": datetime.now(timezone.utc).isoformat(),
            **(metadata or {})
        }

        self.client.upsert(
            collection_name="psychological_constructs",
            points=[PointStruct(
                id=point_id,
                vector=embedding.tolist(),
                payload=payload
            )]
        )

        logger.info(f"✅ Stored {construct_type} for user {user_id}: {point_id}")
        return point_id

    async def store_pattern(
        self,
        user_id: int,
        pattern_text: str,
        pattern_type: str,  # 'blind_spot', 'growth_area', etc
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Сохранить мета-паттерн в meta_patterns

        Returns: point_id (UUID)
        """
        embedding = self.embedding_service.encode_pattern(pattern_text)

        point_id = str(uuid.uuid4())
        payload = {
            "user_id": user_id,
            "text": pattern_text,
            "pattern_type": pattern_type,
            "created_at": datetime.now(timezone.utc).isoformat(),
            **(metadata or {})
        }

        self.client.upsert(
            collection_name="meta_patterns",
            points=[PointStruct(
                id=point_id,
                vector=embedding.tolist(),
                payload=payload
            )]
        )

        logger.info(f"✅ Stored {pattern_type} for user {user_id}: {point_id}")
        return point_id

    # ===================
    # SEARCH METHODS
    # ===================

    async def search_episodic(
        self,
        user_id: int,
        query: str,
        top_k: int = 10,
        score_threshold: float = 0.5
    ) -> List[Dict[str, Any]]:
        """
        Поиск в episodic_memory по семантическому запросу
        """
        try:
            query_embedding = self.embedding_service.encode_episodic(query)

            results = self.client.search(
                collection_name="episodic_memory",
                query_vector=query_embedding.tolist(),
                query_filter=Filter(
                    must=[FieldCondition(key="user_id", match=MatchValue(value=user_id))]
                ),
                limit=top_k,
                score_threshold=score_threshold
            )

            return [
                {
                    "id": str(r.id),
                    "score": r.score,
                    "text": r.payload.get("text"),
                    "created_at": r.payload.get("created_at"),
                    **r.payload
                }
                for r in results
            ]
        except Exception as e:
            logger.error(f"❌ search_episodic failed for user {user_id}: {e}")
            await error_collector.collect(
                error=e,
                service="VectorStorageService",
                component="search_episodic",
                user_id=user_id,
                context={"query_length": len(query), "top_k": top_k}
            )
            return []  # Возвращаем пустой список при ошибке

    async def search_emotional(
        self,
        user_id: int,
        query: str,
        emotion: Optional[str] = None,
        top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Поиск эмоциональных паттернов
        """
        query_embedding = self.embedding_service.encode_emotional(query, emotion)

        filter_conditions = [
            FieldCondition(key="user_id", match=MatchValue(value=user_id))
        ]

        if emotion:
            filter_conditions.append(
                FieldCondition(key="emotion", match=MatchValue(value=emotion))
            )

        results = self.client.search(
            collection_name="emotional_thematic",
            query_vector=query_embedding.tolist(),
            query_filter=Filter(must=filter_conditions),
            limit=top_k
        )

        return [
            {
                "id": str(r.id),
                "score": r.score,
                **r.payload
            }
            for r in results
        ]

    async def search_constructs(
        self,
        user_id: int,
        query: str,
        construct_type: Optional[str] = None,
        top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Поиск психологических конструктов
        """
        query_embedding = self.embedding_service.encode_construct(query)

        filter_conditions = [
            FieldCondition(key="user_id", match=MatchValue(value=user_id))
        ]

        if construct_type:
            filter_conditions.append(
                FieldCondition(key="construct_type", match=MatchValue(value=construct_type))
            )

        results = self.client.search(
            collection_name="psychological_constructs",
            query_vector=query_embedding.tolist(),
            query_filter=Filter(must=filter_conditions),
            limit=top_k
        )

        return [
            {
                "id": str(r.id),
                "score": r.score,
                **r.payload
            }
            for r in results
        ]

    # ===================
    # UTILITY METHODS
    # ===================

    def get_collection_stats(self) -> Dict[str, int]:
        """Get point counts for all collections"""
        stats = {}
        for collection in self.collections:
            try:
                info = self.client.get_collection(collection)
                stats[collection] = info.points_count
            except Exception as e:
                stats[collection] = -1
                logger.error(f"Failed to get stats for {collection}: {e}")
        return stats

    def health_check(self) -> bool:
        """Check Qdrant connectivity"""
        try:
            self.client.get_collections()
            return True
        except Exception as e:
            logger.error(f"Qdrant health check failed: {e}")
            return False


# Singleton
_vector_storage = None

def get_vector_storage() -> VectorStorageService:
    """Get singleton VectorStorageService instance"""
    global _vector_storage
    if _vector_storage is None:
        _vector_storage = VectorStorageService()
    return _vector_storage
