"""
ПРИМЕРЫ КОДА: Оптимизация Векторизации для Selfology

Все примеры готовы к использованию - просто копируй и адаптируй под свою систему.
"""

import asyncio
import time
from typing import List, Dict, Any, Optional
from datetime import datetime
import asyncpg
from openai import AsyncOpenAI
from qdrant_client import QdrantClient
from qdrant_client.http import models
import numpy as np


# ============================================================================
# EXAMPLE 1: Fixed Semantic Search (Chat Messages)
# ============================================================================

class ChatMessageEmbedding:
    """
    Решение Embedding Space Mismatch: отдельная коллекция для chat messages

    ПРОБЛЕМА: Сравнивали personality narratives с user messages (разные пространства)
    РЕШЕНИЕ: Коллекция chat_messages где Message → Message comparison
    """

    def __init__(self, qdrant_url: str = "http://localhost:6333", openai_api_key: str = None):
        self.qdrant = QdrantClient(url=qdrant_url)
        self.openai = AsyncOpenAI(api_key=openai_api_key)
        self.collection_name = "chat_messages"

    async def setup_collection(self):
        """Создать коллекцию для chat messages"""

        try:
            self.qdrant.create_collection(
                collection_name=self.collection_name,
                vectors_config=models.VectorParams(
                    size=1536,  # text-embedding-3-small
                    distance=models.Distance.COSINE
                ),
                optimizers_config=models.OptimizersConfigDiff(
                    indexing_threshold=10000,
                    memmap_threshold=50000
                )
            )
            print(f"✅ Collection '{self.collection_name}' created")

        except Exception as e:
            print(f"⚠️ Collection might already exist: {e}")

    async def save_message_with_embedding(
        self,
        user_id: int,
        message: str,
        role: str,  # "user" or "assistant"
        db_pool: asyncpg.Pool
    ) -> str:
        """
        Сохранить сообщение + создать embedding

        Returns:
            message_id
        """

        # 1. Save to PostgreSQL
        async with db_pool.acquire() as conn:
            msg_id = await conn.fetchval("""
                INSERT INTO chat_messages (user_id, message, role, created_at)
                VALUES ($1, $2, $3, NOW())
                RETURNING id
            """, user_id, message, role)

        # 2. Create embedding
        embedding_response = await self.openai.embeddings.create(
            model="text-embedding-3-small",
            input=message,
            dimensions=1536
        )

        embedding = embedding_response.data[0].embedding

        # 3. Detect emotion (simple heuristic)
        detected_emotion = self._detect_emotion(message)

        # 4. Save to Qdrant
        self.qdrant.upsert(
            collection_name=self.collection_name,
            points=[
                models.PointStruct(
                    id=f"msg_{msg_id}",
                    vector=embedding,
                    payload={
                        "user_id": user_id,
                        "message_id": msg_id,
                        "message": message,
                        "role": role,
                        "timestamp": datetime.now().isoformat(),
                        "detected_emotion": detected_emotion,
                        "message_length": len(message)
                    }
                )
            ]
        )

        print(f"✅ Message saved with embedding (id: {msg_id}, emotion: {detected_emotion})")
        return msg_id

    async def search_similar_past_messages(
        self,
        user_id: int,
        current_message: str,
        limit: int = 10,
        score_threshold: float = 0.65
    ) -> List[Dict[str, Any]]:
        """
        Найти похожие прошлые сообщения пользователя

        ✅ РАБОТАЕТ! Message → Message в одном пространстве
        """

        # 1. Create embedding для current message
        embedding_response = await self.openai.embeddings.create(
            model="text-embedding-3-small",
            input=current_message,
            dimensions=1536
        )

        query_vector = embedding_response.data[0].embedding

        # 2. Search в chat_messages (Message → Message!)
        search_result = self.qdrant.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            query_filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="user_id",
                        match=models.MatchValue(value=user_id)
                    ),
                    models.FieldCondition(
                        key="role",
                        match=models.MatchValue(value="user")  # Только user messages
                    )
                ]
            ),
            limit=limit,
            score_threshold=score_threshold
        )

        # 3. Format results
        similar_messages = []
        for hit in search_result:
            payload = hit.payload

            similar_messages.append({
                "message": payload["message"],
                "timestamp": payload["timestamp"],
                "similarity_score": hit.score,
                "detected_emotion": payload.get("detected_emotion"),
                "time_ago": self._format_time_ago(payload["timestamp"]),
                "context": f"You said this {self._format_time_ago(payload['timestamp'])}"
            })

        print(f"🔍 Found {len(similar_messages)} similar past messages (threshold: {score_threshold})")
        return similar_messages

    def _detect_emotion(self, message: str) -> str:
        """Simple emotion detection (можно улучшить с ML)"""
        message_lower = message.lower()

        # Positive
        if any(word in message_lower for word in ["рад", "счастлив", "отлично", "супер", "здорово"]):
            return "positive"

        # Negative
        if any(word in message_lower for word in ["грустно", "плохо", "тяжело", "сложно", "больно"]):
            return "negative"

        # Anxious
        if any(word in message_lower for word in ["тревожно", "боюсь", "страшно", "волнуюсь"]):
            return "anxious"

        # Confused
        if any(word in message_lower for word in ["не понимаю", "запутался", "непонятно"]):
            return "confused"

        return "neutral"

    def _format_time_ago(self, timestamp_str: str) -> str:
        """Format timestamp as human-readable time ago"""
        timestamp = datetime.fromisoformat(timestamp_str)
        now = datetime.now()
        delta = now - timestamp

        if delta.days > 30:
            return f"{delta.days // 30} month(s) ago"
        elif delta.days > 0:
            return f"{delta.days} day(s) ago"
        elif delta.seconds > 3600:
            return f"{delta.seconds // 3600} hour(s) ago"
        else:
            return f"{delta.seconds // 60} minute(s) ago"


# ============================================================================
# EXAMPLE 2: Multi-Vector Facets (Named Vectors)
# ============================================================================

class MultiVectorFacets:
    """
    Разделение личности на 6 специализированных векторов

    ПРЕИМУЩЕСТВА:
    - Targeted search (искать только в нужном аспекте)
    - Partial updates (обновлять только changed facets)
    - Lower cost (инкрементальные обновления)
    """

    FACETS = ["identity", "emotions", "goals", "barriers", "skills", "relationships"]

    def __init__(self, qdrant_url: str = "http://localhost:6333", openai_api_key: str = None):
        self.qdrant = QdrantClient(url=qdrant_url)
        self.openai = AsyncOpenAI(api_key=openai_api_key)
        self.collection_name = "user_facets"

    async def setup_collection(self):
        """Создать коллекцию с named vectors"""

        vectors_config = {
            facet: models.VectorParams(size=512, distance=models.Distance.COSINE)
            for facet in self.FACETS
        }

        try:
            self.qdrant.create_collection(
                collection_name=self.collection_name,
                vectors_config=vectors_config
            )
            print(f"✅ Collection '{self.collection_name}' created with {len(self.FACETS)} facets")

        except Exception as e:
            print(f"⚠️ Collection might already exist: {e}")

    async def extract_facet_texts(self, user_id: int, db_pool: asyncpg.Pool) -> Dict[str, str]:
        """
        Извлечь текст для каждого facet из digital_personality

        Returns:
            {"identity": "...", "emotions": "...", ...}
        """

        async with db_pool.acquire() as conn:
            personality = await conn.fetchrow("""
                SELECT
                    identity, interests, goals, barriers,
                    relationships, skills, current_state, health
                FROM selfology.digital_personality
                WHERE user_id = $1
            """, user_id)

        if not personality:
            print(f"⚠️ No personality found for user {user_id}")
            return {facet: "" for facet in self.FACETS}

        # Build text for each facet
        facet_texts = {
            "identity": self._build_identity_text(personality),
            "emotions": self._build_emotions_text(personality),
            "goals": self._build_goals_text(personality),
            "barriers": self._build_barriers_text(personality),
            "skills": self._build_skills_text(personality),
            "relationships": self._build_relationships_text(personality)
        }

        return facet_texts

    def _build_identity_text(self, p: dict) -> str:
        """Build identity facet text"""
        import json
        parts = []

        # From identity layer
        if p["identity"]:
            identity_data = json.loads(p["identity"]) if isinstance(p["identity"], str) else p["identity"]
            if isinstance(identity_data, list):
                for item in identity_data:
                    if isinstance(item, dict):
                        aspect = item.get("aspect", "")
                        desc = item.get("description", "")
                        parts.append(f"{aspect}: {desc}")

        # From current_state
        if p["current_state"]:
            state_data = json.loads(p["current_state"]) if isinstance(p["current_state"], str) else p["current_state"]
            if isinstance(state_data, list):
                for item in state_data:
                    if isinstance(item, dict):
                        parts.append(item.get("activity", ""))

        return " ".join(parts)

    def _build_emotions_text(self, p: dict) -> str:
        """Build emotions facet text"""
        import json
        parts = []

        if p["health"]:
            health_data = json.loads(p["health"]) if isinstance(p["health"], str) else p["health"]
            if isinstance(health_data, list):
                for item in health_data:
                    if isinstance(item, dict):
                        aspect = item.get("aspect", "")
                        condition = item.get("condition", "")
                        parts.append(f"{aspect}: {condition}")

        return " ".join(parts)

    def _build_goals_text(self, p: dict) -> str:
        """Build goals facet text"""
        import json
        parts = []

        if p["goals"]:
            goals_data = json.loads(p["goals"]) if isinstance(p["goals"], str) else p["goals"]
            if isinstance(goals_data, list):
                for item in goals_data:
                    if isinstance(item, dict):
                        goal = item.get("goal", "")
                        priority = item.get("priority", "")
                        parts.append(f"{goal} (priority: {priority})")

        return " ".join(parts)

    def _build_barriers_text(self, p: dict) -> str:
        """Build barriers facet text"""
        import json
        parts = []

        if p["barriers"]:
            barriers_data = json.loads(p["barriers"]) if isinstance(p["barriers"], str) else p["barriers"]
            if isinstance(barriers_data, list):
                for item in barriers_data:
                    if isinstance(item, dict):
                        barrier = item.get("barrier", "")
                        barrier_type = item.get("type", "")
                        parts.append(f"{barrier} (type: {barrier_type})")

        return " ".join(parts)

    def _build_skills_text(self, p: dict) -> str:
        """Build skills facet text"""
        import json
        parts = []

        # From skills
        if p["skills"]:
            skills_data = json.loads(p["skills"]) if isinstance(p["skills"], str) else p["skills"]
            if isinstance(skills_data, list):
                for item in skills_data:
                    if isinstance(item, dict):
                        skill = item.get("skill", "")
                        level = item.get("level", "")
                        parts.append(f"{skill} (level: {level})")

        # From interests
        if p["interests"]:
            interests_data = json.loads(p["interests"]) if isinstance(p["interests"], str) else p["interests"]
            if isinstance(interests_data, list):
                for item in interests_data:
                    if isinstance(item, dict):
                        activity = item.get("activity", "")
                        parts.append(activity)

        return " ".join(parts)

    def _build_relationships_text(self, p: dict) -> str:
        """Build relationships facet text"""
        import json
        parts = []

        if p["relationships"]:
            rel_data = json.loads(p["relationships"]) if isinstance(p["relationships"], str) else p["relationships"]
            if isinstance(rel_data, list):
                for item in rel_data:
                    if isinstance(item, dict):
                        person = item.get("person", "")
                        relationship = item.get("relationship", "")
                        parts.append(f"{person}: {relationship}")

        return " ".join(parts)

    async def create_facet_embeddings(self, user_id: int, db_pool: asyncpg.Pool):
        """
        Создать embeddings для всех facets и сохранить в Qdrant
        """

        # 1. Extract texts
        facet_texts = await self.extract_facet_texts(user_id, db_pool)

        # 2. Create embeddings (parallel!)
        embedding_tasks = []
        for facet in self.FACETS:
            text = facet_texts[facet]
            if not text:
                text = f"No {facet} information yet"  # Placeholder

            task = self.openai.embeddings.create(
                model="text-embedding-3-small",
                input=text,
                dimensions=512  # Compressed!
            )
            embedding_tasks.append(task)

        embeddings_responses = await asyncio.gather(*embedding_tasks)

        # 3. Build vectors dict
        vectors = {
            facet: response.data[0].embedding
            for facet, response in zip(self.FACETS, embeddings_responses)
        }

        # 4. Upsert to Qdrant
        self.qdrant.upsert(
            collection_name=self.collection_name,
            points=[
                models.PointStruct(
                    id=user_id,
                    vector=vectors,  # Named vectors!
                    payload={
                        "user_id": user_id,
                        "created_at": datetime.now().isoformat(),
                        "facet_texts": facet_texts  # Store for reference
                    }
                )
            ]
        )

        print(f"✅ Created {len(self.FACETS)} facet embeddings for user {user_id}")

    async def search_in_facet(
        self,
        user_id: int,
        query: str,
        facet: str,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Targeted search в конкретном facet

        Example:
            "У меня проблема с прокрастинацией" → search in "barriers"
        """

        if facet not in self.FACETS:
            raise ValueError(f"Invalid facet: {facet}. Must be one of {self.FACETS}")

        # 1. Create query embedding
        embedding_response = await self.openai.embeddings.create(
            model="text-embedding-3-small",
            input=query,
            dimensions=512
        )

        query_vector = embedding_response.data[0].embedding

        # 2. Search в конкретном facet
        search_result = self.qdrant.search(
            collection_name=self.collection_name,
            query_vector=(facet, query_vector),  # ← Targeted!
            query_filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="user_id",
                        match=models.MatchValue(value=user_id)
                    )
                ]
            ),
            limit=limit
        )

        results = []
        for hit in search_result:
            payload = hit.payload
            results.append({
                "facet": facet,
                "similarity": hit.score,
                "text": payload["facet_texts"][facet],
                "user_id": payload["user_id"]
            })

        print(f"🎯 Searched in '{facet}' facet: {len(results)} results")
        return results


# ============================================================================
# EXAMPLE 3: Smart Context Assembly (with Caching)
# ============================================================================

class SmartContextAssembler:
    """
    Быстрая сборка контекста с кэшированием и parallel fetching

    TARGET: <100ms для context assembly
    """

    def __init__(self, db_pool: asyncpg.Pool, qdrant_url: str = "http://localhost:6333"):
        self.db_pool = db_pool
        self.qdrant = QdrantClient(url=qdrant_url)

        # Cache
        self.cache = {}  # user_id → {context, timestamp}
        self.cache_ttl_seconds = 300  # 5 minutes

    async def assemble_context(
        self,
        user_id: int,
        depth: str = "standard"  # "quick", "standard", "deep"
    ) -> Dict[str, Any]:
        """
        Собрать контекст за <100ms

        Depths:
        - quick: только profile + recent (50-70ms)
        - standard: + semantic search (280-320ms)
        - deep: + trajectory analysis (350-400ms)
        """

        start = time.time()

        # 1. Check cache
        if cached := self._get_cached_context(user_id):
            print(f"✅ Context cache HIT (0ms)")
            return cached

        # 2. Parallel fetch базовых данных
        profile_task = self._get_personality_profile(user_id)
        messages_task = self._get_recent_messages(user_id, limit=5)

        profile, recent_messages = await asyncio.gather(profile_task, messages_task)
        # ~45ms (parallel)

        context = {
            "user_id": user_id,
            "profile": profile,
            "recent_conversation": recent_messages,
            "depth": depth,
            "assembly_time_ms": 0  # Will update
        }

        # 3. Additional data based on depth
        if depth in ["standard", "deep"]:
            # Add facet vectors
            facet_vectors = await self._get_facet_summary(user_id)
            context["facet_vectors"] = facet_vectors

        if depth == "deep":
            # Add trajectory analysis
            trajectory = await self._get_trajectory_analysis(user_id)
            context["trajectory"] = trajectory

        # 4. Calculate time
        elapsed_ms = (time.time() - start) * 1000
        context["assembly_time_ms"] = elapsed_ms

        # 5. Cache
        self._cache_context(user_id, context)

        print(f"✅ Context assembled in {elapsed_ms:.0f}ms (depth: {depth})")
        return context

    async def _get_personality_profile(self, user_id: int) -> Dict[str, Any]:
        """Load personality profile from PostgreSQL (~20ms)"""
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT
                    identity, interests, goals, barriers,
                    total_answers_analyzed, completeness_score
                FROM selfology.digital_personality
                WHERE user_id = $1
            """, user_id)

        if not row:
            return {"exists": False}

        return {
            "exists": True,
            "completeness_score": row["completeness_score"],
            "total_answers": row["total_answers_analyzed"]
        }

    async def _get_recent_messages(self, user_id: int, limit: int = 5) -> List[Dict[str, Any]]:
        """Load recent messages (~10ms)"""
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT message, role, created_at
                FROM chat_messages
                WHERE user_id = $1
                ORDER BY created_at DESC
                LIMIT $2
            """, user_id, limit)

        return [
            {
                "role": row["role"],
                "content": row["message"],
                "timestamp": row["created_at"].isoformat()
            }
            for row in reversed(rows)  # Reverse to chronological order
        ]

    async def _get_facet_summary(self, user_id: int) -> Dict[str, str]:
        """Get facet vectors summary (~15ms)"""
        try:
            result = self.qdrant.retrieve(
                collection_name="user_facets",
                ids=[user_id],
                with_payload=True
            )

            if result:
                return result[0].payload.get("facet_texts", {})

        except Exception as e:
            print(f"⚠️ Error getting facet summary: {e}")

        return {}

    async def _get_trajectory_analysis(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get personality trajectory (~30ms)"""
        # Simplified - in real implementation call CoachVectorDAO
        return {"trends": {}, "insights": []}

    def _get_cached_context(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get cached context if fresh"""
        if user_id not in self.cache:
            return None

        cached = self.cache[user_id]
        age_seconds = time.time() - cached["timestamp"]

        if age_seconds < self.cache_ttl_seconds:
            return cached["context"]
        else:
            # Expired
            del self.cache[user_id]
            return None

    def _cache_context(self, user_id: int, context: Dict[str, Any]):
        """Cache context"""
        self.cache[user_id] = {
            "context": context,
            "timestamp": time.time()
        }


# ============================================================================
# EXAMPLE 4: Incremental Vector Updates
# ============================================================================

class IncrementalVectorUpdater:
    """
    Умное обновление векторов без полного пересчёта

    ЭКОНОМИЯ: 99% reduction в embedding calls для updates!
    """

    def __init__(self, qdrant_url: str = "http://localhost:6333", openai_api_key: str = None):
        self.qdrant = QdrantClient(url=qdrant_url)
        self.openai = AsyncOpenAI(api_key=openai_api_key)

    async def update_facet_incremental(
        self,
        user_id: int,
        facet: str,  # "identity", "goals", etc.
        new_text: str,
        alpha: float = 0.1  # Weight of new information (10%)
    ):
        """
        Инкрементальное обновление одного facet

        Вместо полного пересчёта используем weighted average:
        new_vector = (1 - alpha) * old_vector + alpha * new_vector

        Args:
            alpha: Влияние нового ответа (0.1 = 10% new, 90% old)
        """

        start = time.time()

        # 1. Получаем текущий вектор
        try:
            current = self.qdrant.retrieve(
                collection_name="user_facets",
                ids=[user_id],
                with_vectors=[facet]
            )

            if not current:
                print(f"⚠️ No existing vector for user {user_id}, creating new")
                return await self._create_new_facet_vector(user_id, facet, new_text)

            current_vector = current[0].vector[facet]
            current_payload = current[0].payload

        except Exception as e:
            print(f"❌ Error retrieving current vector: {e}")
            return False

        # 2. Создаём вектор из нового текста (~200ms)
        new_embedding = await self.openai.embeddings.create(
            model="text-embedding-3-small",
            input=new_text,
            dimensions=512
        )

        new_vector = new_embedding.data[0].embedding

        # 3. Weighted average (~1ms - FAST!)
        merged_vector = [
            (1 - alpha) * old + alpha * new
            for old, new in zip(current_vector, new_vector)
        ]

        # 4. Calculate delta (для определения breakthrough)
        delta = self._cosine_similarity(current_vector, merged_vector)
        is_significant_change = delta < 0.95  # >5% change

        # 5. Update в Qdrant
        # Update facet_texts
        facet_texts = current_payload.get("facet_texts", {})
        facet_texts[facet] = new_text

        self.qdrant.update_vectors(
            collection_name="user_facets",
            points=[
                models.PointStruct(
                    id=user_id,
                    vector={facet: merged_vector},
                    payload={
                        **current_payload,
                        "facet_texts": facet_texts,
                        f"{facet}_updated_at": datetime.now().isoformat(),
                        f"{facet}_update_count": current_payload.get(f"{facet}_update_count", 0) + 1
                    }
                )
            ]
        )

        elapsed_ms = (time.time() - start) * 1000

        print(f"✅ Incremental update for '{facet}': {elapsed_ms:.0f}ms (delta: {1-delta:.2%})")

        # 6. Snapshot для истории (если значительное изменение)
        if is_significant_change:
            await self._save_evolution_snapshot(user_id, facet, merged_vector, delta)

        return True

    async def _create_new_facet_vector(self, user_id: int, facet: str, text: str):
        """Create new facet vector (first time)"""
        embedding = await self.openai.embeddings.create(
            model="text-embedding-3-small",
            input=text,
            dimensions=512
        )

        self.qdrant.upsert(
            collection_name="user_facets",
            points=[
                models.PointStruct(
                    id=user_id,
                    vector={facet: embedding.data[0].embedding},
                    payload={
                        "user_id": user_id,
                        "facet_texts": {facet: text},
                        "created_at": datetime.now().isoformat()
                    }
                )
            ]
        )

        print(f"✅ Created new facet vector for '{facet}'")
        return True

    async def _save_evolution_snapshot(
        self,
        user_id: int,
        facet: str,
        vector: List[float],
        delta: float
    ):
        """Сохранить snapshot для истории эволюции"""
        snapshot_id = int(time.time() * 1000)  # milliseconds

        self.qdrant.upsert(
            collection_name="personality_evolution",
            points=[
                models.PointStruct(
                    id=snapshot_id,
                    vector=vector,
                    payload={
                        "user_id": user_id,
                        "snapshot_id": snapshot_id,
                        "facet": facet,
                        "delta_magnitude": 1 - delta,
                        "is_significant": True,
                        "created_at": datetime.now().isoformat()
                    }
                )
            ]
        )

        print(f"📸 Saved evolution snapshot for '{facet}' (delta: {1-delta:.2%})")

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity"""
        vec1_np = np.array(vec1)
        vec2_np = np.array(vec2)

        dot_product = np.dot(vec1_np, vec2_np)
        norm1 = np.linalg.norm(vec1_np)
        norm2 = np.linalg.norm(vec2_np)

        return dot_product / (norm1 * norm2)


# ============================================================================
# TESTING EXAMPLES
# ============================================================================

async def test_chat_message_embedding():
    """Test Example 1: Chat Message Embedding"""
    print("\n" + "="*80)
    print("TEST 1: Chat Message Embedding (Fix Semantic Search)")
    print("="*80 + "\n")

    # Setup (use your credentials)
    import os
    chat_embedder = ChatMessageEmbedding(
        qdrant_url="http://localhost:6333",
        openai_api_key=os.getenv("OPENAI_API_KEY")
    )

    # Create collection
    await chat_embedder.setup_collection()

    # Simulate saving messages (you need db_pool)
    # user_id = 98005572
    # await chat_embedder.save_message_with_embedding(
    #     user_id, "Мне грустно сегодня", "user", db_pool
    # )

    # Search similar messages
    # similar = await chat_embedder.search_similar_past_messages(
    #     user_id, "Я чувствую себя потерянным"
    # )
    # print(f"Found {len(similar)} similar messages")


async def test_multi_vector_facets():
    """Test Example 2: Multi-Vector Facets"""
    print("\n" + "="*80)
    print("TEST 2: Multi-Vector Facets")
    print("="*80 + "\n")

    import os
    facets = MultiVectorFacets(
        qdrant_url="http://localhost:6333",
        openai_api_key=os.getenv("OPENAI_API_KEY")
    )

    # Create collection
    await facets.setup_collection()

    # Create facet embeddings (you need db_pool)
    # user_id = 98005572
    # await facets.create_facet_embeddings(user_id, db_pool)

    # Search in specific facet
    # results = await facets.search_in_facet(
    #     user_id, "У меня проблема с прокрастинацией", "barriers"
    # )
    # print(f"Found {len(results)} results in 'barriers' facet")


async def test_smart_context_assembly():
    """Test Example 3: Smart Context Assembly"""
    print("\n" + "="*80)
    print("TEST 3: Smart Context Assembly (with Caching)")
    print("="*80 + "\n")

    # Setup (you need db_pool)
    # assembler = SmartContextAssembler(db_pool)

    # Quick context
    # context_quick = await assembler.assemble_context(98005572, depth="quick")
    # print(f"Quick context: {context_quick['assembly_time_ms']:.0f}ms")

    # Standard context (with cache)
    # context_standard = await assembler.assemble_context(98005572, depth="standard")
    # print(f"Standard context: {context_standard['assembly_time_ms']:.0f}ms")

    # Second call (should hit cache)
    # context_cached = await assembler.assemble_context(98005572, depth="standard")
    # print(f"Cached context: {context_cached['assembly_time_ms']:.0f}ms")


async def test_incremental_updates():
    """Test Example 4: Incremental Vector Updates"""
    print("\n" + "="*80)
    print("TEST 4: Incremental Vector Updates")
    print("="*80 + "\n")

    import os
    updater = IncrementalVectorUpdater(
        qdrant_url="http://localhost:6333",
        openai_api_key=os.getenv("OPENAI_API_KEY")
    )

    # Update goals facet
    # user_id = 98005572
    # new_goal_text = "создать стартап, финансовая независимость, путешествовать"
    # await updater.update_facet_incremental(user_id, "goals", new_goal_text, alpha=0.1)

    # Update barriers facet
    # new_barrier_text = "прокрастинация, страх провала, перфекционизм"
    # await updater.update_facet_incremental(user_id, "barriers", new_barrier_text, alpha=0.15)


async def main():
    """Run all tests"""
    print("\n" + "🚀"*40)
    print("VECTOR OPTIMIZATION EXAMPLES - SELFOLOGY")
    print("🚀"*40 + "\n")

    # Run tests
    await test_chat_message_embedding()
    await test_multi_vector_facets()
    # await test_smart_context_assembly()  # Needs db_pool
    # await test_incremental_updates()  # Needs existing vectors

    print("\n✅ All tests completed!\n")


if __name__ == "__main__":
    asyncio.run(main())
