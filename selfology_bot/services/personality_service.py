"""
PersonalityService - Unified access to user personality data from Qdrant

🎯 Single Source of Truth: Qdrant vector database
📊 Multi-Resolution: Loads from 4 specialized collections
⚡ Performance: Parallel queries + optional caching
🔄 Clean Architecture: Eliminates PostgreSQL duplication
"""

import logging
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime
from dataclasses import dataclass

from qdrant_client import QdrantClient
from qdrant_client.models import FieldCondition, Filter, MatchValue

logger = logging.getLogger(__name__)


@dataclass
class PersonalityData:
    """Complete personality profile from all Qdrant collections"""

    # Core identity
    user_id: int
    last_updated: str
    completeness_score: float

    # Structured data (from digital_personality_structured)
    interests: List[str]
    goals: List[str]
    values: List[str]
    skills: List[str]
    barriers: List[str]

    # Personality traits (from personality_profiles)
    big_five: Dict[str, float]
    dynamic_traits: Optional[Dict[str, float]]

    # Narrative (from digital_personality_narrative)
    narrative_text: Optional[str]
    life_stories: Optional[List[str]]

    # Quick access metadata (from quick_match)
    key_markers: Optional[Dict[str, Any]]

    # Evolution tracking
    breakthrough_moments: List[Dict[str, Any]]

    # Raw vectors (if needed for semantic operations)
    vectors: Optional[Dict[str, List[float]]]


class PersonalityService:
    """
    Unified service for accessing user personality data from Qdrant

    Architecture:
    - Loads from 4 Qdrant collections in parallel
    - Merges data intelligently
    - No PostgreSQL duplication
    - Qdrant is the single source of truth
    """

    def __init__(self, qdrant_host: str = "localhost", qdrant_port: int = 6333):
        """Initialize PersonalityService with Qdrant connection"""

        self.qdrant = QdrantClient(host=qdrant_host, port=qdrant_port)
        logger.info(f"🧠 PersonalityService initialized (Qdrant: {qdrant_host}:{qdrant_port})")

        # Collection names
        self.collections = {
            "structured": "digital_personality_structured",  # 1536D - structured data
            "narrative": "digital_personality_narrative",    # 3072D - stories & context
            "profile": "personality_profiles",               # 1536D - holistic profile
            "quick": "quick_match"                          # 512D - quick access
        }

    async def get_full_personality(
        self,
        user_id: int,
        include_vectors: bool = False,
        include_evolution: bool = True
    ) -> Optional[PersonalityData]:
        """
        Load complete personality profile from all Qdrant collections

        Args:
            user_id: User identifier
            include_vectors: Include raw vectors for semantic operations
            include_evolution: Include breakthrough moments from personality_evolution

        Returns:
            PersonalityData object with all personality information
        """

        try:
            logger.info(f"🔍 Loading full personality for user {user_id}")
            start_time = datetime.now()

            # Parallel queries to all 4 collections
            results = await self._load_from_all_collections(user_id, include_vectors)

            if not results or not any(results.values()):
                logger.warning(f"⚠️ No personality data found for user {user_id}")
                return None

            # Load breakthrough moments if requested
            breakthrough_moments = []
            if include_evolution:
                breakthrough_moments = await self._load_breakthrough_moments(user_id)

            # Merge data from all sources
            personality = self._merge_personality_data(user_id, results, breakthrough_moments)

            elapsed = (datetime.now() - start_time).total_seconds()
            logger.info(f"✅ Personality loaded in {elapsed:.2f}s (completeness: {personality.completeness_score:.0%})")

            return personality

        except Exception as e:
            logger.error(f"❌ Error loading personality for user {user_id}: {e}", exc_info=True)
            return None

    async def _load_from_all_collections(
        self,
        user_id: int,
        include_vectors: bool
    ) -> Dict[str, Any]:
        """Load data from all 4 personality collections in parallel"""

        try:
            # Create parallel tasks for all collections
            tasks = {
                name: self._retrieve_from_collection(
                    collection_name=collection,
                    user_id=user_id,
                    with_vectors=include_vectors
                )
                for name, collection in self.collections.items()
            }

            # Execute in parallel
            results = await asyncio.gather(*tasks.values(), return_exceptions=True)

            # Map results back to collection names
            collection_data = {}
            for (name, _), result in zip(tasks.items(), results):
                if isinstance(result, Exception):
                    logger.warning(f"⚠️ Failed to load from {name}: {result}")
                    collection_data[name] = None
                else:
                    collection_data[name] = result

            # Log what we loaded
            loaded = [name for name, data in collection_data.items() if data]
            logger.debug(f"📊 Loaded from collections: {', '.join(loaded)}")

            return collection_data

        except Exception as e:
            logger.error(f"❌ Error loading from collections: {e}")
            return {}

    async def _retrieve_from_collection(
        self,
        collection_name: str,
        user_id: int,
        with_vectors: bool
    ) -> Optional[Dict[str, Any]]:
        """Retrieve personality data from a specific Qdrant collection"""

        try:
            result = self.qdrant.retrieve(
                collection_name=collection_name,
                ids=[user_id],
                with_vectors=with_vectors,
                with_payload=True
            )

            if result and len(result) > 0:
                return {
                    "payload": result[0].payload,
                    "vector": result[0].vector if with_vectors else None
                }

            return None

        except Exception as e:
            logger.debug(f"Collection {collection_name} not available or empty for user {user_id}: {e}")
            return None

    async def _load_breakthrough_moments(self, user_id: int, limit: int = 5) -> List[Dict[str, Any]]:
        """Load breakthrough moments from personality_evolution collection"""

        try:
            search_results = self.qdrant.scroll(
                collection_name="personality_evolution",
                scroll_filter=Filter(
                    must=[
                        FieldCondition(
                            key="user_id",
                            match=MatchValue(value=user_id)
                        )
                    ]
                ),
                limit=limit,
                with_payload=True,
                with_vectors=False
            )

            moments = []
            if search_results and search_results[0]:
                for point in search_results[0]:
                    moments.append({
                        "created_at": point.payload.get("created_at"),
                        "breakthrough_info": point.payload.get("breakthrough_info", {}),
                        "narrative": point.payload.get("personality_snapshot", {}).get("narrative", "")
                    })

            if moments:
                logger.info(f"🌟 Loaded {len(moments)} breakthrough moments")

            return moments

        except Exception as e:
            logger.debug(f"Could not load breakthrough moments: {e}")
            return []

    def _merge_personality_data(
        self,
        user_id: int,
        collection_data: Dict[str, Any],
        breakthrough_moments: List[Dict[str, Any]]
    ) -> PersonalityData:
        """Intelligently merge data from all collections into PersonalityData"""

        # Extract structured data (interests, goals, etc.)
        structured = collection_data.get("structured", {})
        structured_payload = structured.get("payload", {}) if structured else {}

        # Extract narrative data
        narrative = collection_data.get("narrative", {})
        narrative_payload = narrative.get("payload", {}) if narrative else {}

        # Extract profile data (Big Five, traits)
        profile = collection_data.get("profile", {})
        profile_payload = profile.get("payload", {}) if profile else {}

        # Extract quick match data
        quick = collection_data.get("quick", {})
        quick_payload = quick.get("payload", {}) if quick else {}

        # Determine last_updated and completeness from most recent source
        last_updated = (
            profile_payload.get("last_updated") or
            structured_payload.get("last_updated") or
            narrative_payload.get("last_updated") or
            datetime.now().isoformat()
        )

        completeness_score = (
            profile_payload.get("completeness_score") or
            structured_payload.get("completeness_score") or
            0.0
        )

        # Build vectors dict if available
        vectors = None
        if any(collection_data.get(name, {}).get("vector") for name in ["structured", "narrative", "profile", "quick"]):
            vectors = {
                name: collection_data.get(name, {}).get("vector")
                for name in ["structured", "narrative", "profile", "quick"]
                if collection_data.get(name, {}).get("vector")
            }

        # Create PersonalityData object
        return PersonalityData(
            user_id=user_id,
            last_updated=last_updated,
            completeness_score=float(completeness_score),

            # Structured data
            interests=structured_payload.get("interests", []),
            goals=structured_payload.get("goals", []),
            values=structured_payload.get("values", []),
            skills=structured_payload.get("skills", []),
            barriers=structured_payload.get("barriers", []),

            # Traits
            big_five=profile_payload.get("traits", {}).get("big_five", {}),
            dynamic_traits=profile_payload.get("traits", {}).get("dynamic_traits"),

            # Narrative
            narrative_text=narrative_payload.get("narrative_text"),
            life_stories=narrative_payload.get("life_stories"),

            # Quick access
            key_markers=quick_payload.get("key_markers"),

            # Evolution
            breakthrough_moments=breakthrough_moments,

            # Vectors
            vectors=vectors
        )

    async def get_personality_for_chat(self, user_id: int) -> Dict[str, Any]:
        """
        Optimized method specifically for chat context

        Returns a dict ready to be injected into system prompt
        """

        personality = await self.get_full_personality(
            user_id=user_id,
            include_vectors=False,  # Chat doesn't need raw vectors
            include_evolution=True   # Include breakthrough moments for context
        )

        if not personality:
            return {}

        # Format for chat system prompt
        return {
            "user_id": personality.user_id,
            "completeness_score": personality.completeness_score,
            "last_updated": personality.last_updated,

            # Core data
            "interests": personality.interests,
            "goals": personality.goals,
            "values": personality.values,
            "skills": personality.skills,
            "barriers": personality.barriers,

            # Traits
            "big_five": personality.big_five,
            "dynamic_traits": personality.dynamic_traits or {},

            # Context
            "narrative": personality.narrative_text,
            "life_stories": personality.life_stories or [],

            # Evolution
            "breakthrough_moments": personality.breakthrough_moments
        }

    def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about Qdrant collections"""

        stats = {}
        for name, collection in self.collections.items():
            try:
                info = self.qdrant.get_collection(collection)
                stats[name] = {
                    "points_count": info.points_count,
                    "vectors_count": info.vectors_count,
                    "status": info.status
                }
            except Exception as e:
                stats[name] = {"error": str(e)}

        return stats
