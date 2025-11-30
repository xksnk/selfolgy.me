"""
Embedding Creator - Создание векторов для Qdrant

🧬 ПРИНЦИП: Многомерные embeddings для разных задач
📊 АРХИТЕКТУРА: Инкрементальные обновления с сохранением истории
⚡ ПРОИЗВОДИТЕЛЬНОСТЬ: Разные размерности под разные цели
🔍 ПОИСК: Семантический поиск похожих личностей
"""

import logging
import json
import asyncio
import hashlib
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import numpy as np

# Для работы с Qdrant
try:
    from qdrant_client import QdrantClient
    from qdrant_client.http.models import Distance, VectorParams, PointStruct
    QDRANT_AVAILABLE = True
except ImportError:
    logger.warning("⚠️ qdrant-client not installed, embeddings will be disabled")
    QDRANT_AVAILABLE = False

# Для работы с OpenAI
try:
    from openai import AsyncOpenAI
    from openai import RateLimitError, APIError, APITimeoutError, APIConnectionError
    OPENAI_AVAILABLE = True
except ImportError:
    logger = logging.getLogger(__name__)
    logger.warning("⚠️ openai not installed, embeddings will be disabled")
    OPENAI_AVAILABLE = False

# Retry механизм
try:
    from tenacity import (
        retry,
        stop_after_attempt,
        wait_exponential,
        retry_if_exception_type,
        before_sleep_log
    )
    TENACITY_AVAILABLE = True
except ImportError:
    logger = logging.getLogger(__name__)
    logger.warning("⚠️ tenacity not installed, retry mechanism disabled")
    TENACITY_AVAILABLE = False

import os
from .analysis_config import AnalysisConfig

logger = logging.getLogger(__name__)

class EmbeddingCreator:
    """
    Создание и управление векторами личности в Qdrant

    Многоуровневая архитектура:
    - Full personality (3072D) - максимальная точность
    - Standard profile (1536D) - ежедневные операции
    - Quick match (512D) - быстрый поиск
    - Domain facets (256D × 5) - аспектные векторы
    """

    def __init__(self):
        """Инициализация creator"""

        self.config = AnalysisConfig()

        # Конфигурация embeddings (из детального плана)
        self.embedding_configs = {
            "full_personality": {
                "model": "text-embedding-3-large",
                "dimensions": 3072,
                "use_case": "deep_matching",
                "cost_per_1k": 0.00013,
                "collection": "personality_evolution"
            },

            "standard_personality": {
                "model": "text-embedding-3-small",
                "dimensions": 1536,
                "use_case": "daily_operations",
                "cost_per_1k": 0.00002,
                "collection": "personality_profiles"
            },

            "quick_match": {
                "model": "text-embedding-3-small",
                "dimensions": 512,
                "use_case": "real_time_search",
                "cost_per_1k": 0.00002,
                "collection": "quick_match"
            }
        }

        # Статистика embeddings
        self.embedding_stats = {
            "vectors_created": 0,
            "vectors_updated": 0,
            "total_cost": 0.0,
            "avg_creation_time_ms": 0,
            "api_calls_success": 0,
            "api_calls_failed": 0,
            "total_tokens_used": 0,
            "cache_hits": 0,
            "cache_misses": 0
        }

        # Semantic cache для идентичных текстов
        self._embedding_cache = {}  # {text_hash: {"embedding": [...], "created_at": datetime}}
        self._cache_ttl_hours = 24  # Cache TTL

        # OpenAI client
        self.openai_client = None
        if OPENAI_AVAILABLE:
            try:
                api_key = os.getenv("OPENAI_API_KEY")
                if not api_key:
                    logger.error("❌ OPENAI_API_KEY not found in environment")
                    raise ValueError("OPENAI_API_KEY is required for embeddings")

                self.openai_client = AsyncOpenAI(
                    api_key=api_key,
                    timeout=30.0,  # 30 seconds timeout
                    max_retries=0  # We handle retries ourselves with tenacity
                )
                logger.info("✅ OpenAI AsyncClient initialized for embeddings")
            except Exception as e:
                logger.error(f"❌ Failed to initialize OpenAI client: {e}")
                self.openai_client = None
        else:
            logger.warning("⚠️ OpenAI client not available - embeddings will use mock")

        # Коннекция к Qdrant
        self.qdrant_client = None
        if QDRANT_AVAILABLE:
            try:
                # Получаем URL из environment
                qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")

                # Для локального запуска корректируем URL
                if "qdrant:6333" in qdrant_url:
                    qdrant_url = "http://localhost:6333"
                    logger.info(f"🔧 Adjusted Qdrant URL for local run: {qdrant_url}")

                self.qdrant_client = QdrantClient(url=qdrant_url)
                logger.info(f"📈 Connected to Qdrant at {qdrant_url}")
            except Exception as e:
                logger.error(f"❌ Failed to connect to Qdrant: {e}")
                self.qdrant_client = None
        else:
            logger.warning("⚠️ Qdrant client not available - embeddings disabled")

        logger.info("📈 EmbeddingCreator initialized with real OpenAI API integration")

    async def create_personality_vector(
        self,
        user_id: int,
        analysis_result: Dict[str, Any],
        is_update: bool = False
    ) -> bool:
        """
        Создать/обновить векторы личности пользователя

        Args:
            user_id: ID пользователя
            analysis_result: Результат полного анализа ответа
            is_update: True если это обновление существующего профиля

        Returns:
            True если векторы успешно созданы/обновлены
        """

        try:
            logger.info(f"📈 Creating personality vectors for user {user_id}")

            # 1. Генерируем personality summary для vectorization
            summary_data = analysis_result.get("personality_summary", {})

            if not summary_data:
                logger.error(f"❌ No personality summary in analysis result for user {user_id}")
                logger.error(f"📋 Available keys in analysis_result: {list(analysis_result.keys())}")
                logger.error(f"🔍 analysis_result structure: {json.dumps({k: type(v).__name__ for k, v in analysis_result.items()}, indent=2)}")
                return False

            # 2. Создаем embeddings разных уровней
            embeddings = await self._create_multi_level_embeddings(summary_data, user_id)

            if not embeddings:
                logger.error(f"❌ Failed to create embeddings for user {user_id}")
                return False

            # 3. Определяем стратегию обновления
            if is_update:
                success = await self._update_existing_vectors(user_id, embeddings, analysis_result)
            else:
                success = await self._create_new_vectors(user_id, embeddings, analysis_result)

            if success:
                self.embedding_stats["vectors_created" if not is_update else "vectors_updated"] += 1
                logger.info(f"✅ Personality vectors {'updated' if is_update else 'created'} for user {user_id}")

            return success

        except Exception as e:
            logger.error(f"❌ Error creating personality vector for user {user_id}: {e}")
            return False

    async def _create_multi_level_embeddings(
        self,
        summary_data: Dict[str, str],
        user_id: int
    ) -> Optional[Dict[str, Any]]:
        """
        Создание embeddings разных уровней детализации

        Returns:
            Dict с embeddings для разных коллекций
        """

        try:
            embeddings = {}

            # 1. Standard embedding для основного профиля (1536D)
            if "narrative" in summary_data:
                standard_embedding = await self._create_openai_embedding(
                    summary_data["narrative"],
                    model="text-embedding-3-small",
                    dimensions=1536
                )
                if standard_embedding:
                    embeddings["standard"] = standard_embedding

            # 2. Quick match embedding для быстрого поиска (512D)
            if "nano" in summary_data:
                quick_embedding = await self._create_openai_embedding(
                    summary_data["embedding_prompt"] if "embedding_prompt" in summary_data else summary_data["nano"],
                    model="text-embedding-3-small",
                    dimensions=512  # Сжатый через параметры API
                )
                if quick_embedding:
                    embeddings["quick"] = quick_embedding

            # 3. Full embedding для детального анализа (3072D) - только для важных моментов
            if self._should_create_full_embedding(user_id, summary_data):
                full_embedding = await self._create_openai_embedding(
                    summary_data["narrative"] + " " + summary_data.get("structured", ""),
                    model="text-embedding-3-large",
                    dimensions=3072
                )
                if full_embedding:
                    embeddings["full"] = full_embedding

            logger.info(f"📊 Created {len(embeddings)} embedding levels")
            return embeddings if embeddings else None

        except Exception as e:
            logger.error(f"❌ Error creating multi-level embeddings: {e}")
            return None

    def _get_cache_key(self, text: str, dimensions: int) -> str:
        """Получить ключ кэша для текста и dimensions"""
        # ВАЖНО: кэш должен учитывать dimensions, т.к. один текст может иметь разные векторы
        combined = f"{text}_{dimensions}"
        return hashlib.sha256(combined.encode('utf-8')).hexdigest()

    def _get_cached_embedding(self, text: str, dimensions: int) -> Optional[List[float]]:
        """Получить embedding из кэша если есть"""
        cache_key = self._get_cache_key(text, dimensions)

        if cache_key in self._embedding_cache:
            cached = self._embedding_cache[cache_key]
            created_at = cached["created_at"]

            # Проверяем TTL
            hours_passed = (datetime.now() - created_at).total_seconds() / 3600
            if hours_passed < self._cache_ttl_hours:
                self.embedding_stats["cache_hits"] += 1
                logger.debug(f"✅ Cache hit for text (dimensions={dimensions}, hash: {cache_key[:8]}...)")
                return cached["embedding"]
            else:
                # Удаляем устаревший кэш
                del self._embedding_cache[cache_key]

        self.embedding_stats["cache_misses"] += 1
        return None

    def _cache_embedding(self, text: str, embedding: List[float], dimensions: int):
        """Сохранить embedding в кэш"""
        cache_key = self._get_cache_key(text, dimensions)
        self._embedding_cache[cache_key] = {
            "embedding": embedding,
            "created_at": datetime.now()
        }
        logger.debug(f"💾 Cached embedding (dimensions={dimensions}, hash: {cache_key[:8]}...)")

    async def _create_openai_embedding(
        self,
        text: str,
        model: str = "text-embedding-3-small",
        dimensions: int = 1536
    ) -> Optional[List[float]]:
        """
        Создание embedding через OpenAI API с retry механизмом

        Args:
            text: Текст для векторизации
            model: Модель OpenAI (text-embedding-3-small или text-embedding-3-large)
            dimensions: Размерность вектора

        Returns:
            List[float] с вектором или None при ошибке
        """

        # Валидация входных данных
        if not text or not text.strip():
            logger.warning("⚠️ Empty text provided for embedding, skipping")
            return None

        # Проверяем длину текста (OpenAI limit: 8191 tokens, ~32K characters)
        if len(text) > 30000:
            logger.warning(f"⚠️ Text too long ({len(text)} chars), truncating to 30000")
            text = text[:30000]

        # Проверяем кэш (учитываем dimensions!)
        cached = self._get_cached_embedding(text, dimensions)
        if cached:
            return cached

        # Если OpenAI недоступен - используем mock
        if not self.openai_client:
            logger.warning("⚠️ OpenAI client not available, using mock embedding")
            return await self._create_mock_embedding(text, dimensions)

        # Вызываем реальный API с retry
        try:
            embedding = await self._call_openai_api_with_retry(text, model, dimensions)

            if embedding:
                # Кэшируем результат (с учетом dimensions!)
                self._cache_embedding(text, embedding, dimensions)

            return embedding

        except Exception as e:
            logger.error(f"❌ Failed to create embedding after all retries: {e}")
            self.embedding_stats["api_calls_failed"] += 1

            # Fallback на mock в случае критической ошибки
            logger.warning("⚠️ Falling back to mock embedding due to API failure")
            return await self._create_mock_embedding(text, dimensions)

    async def _call_openai_api_with_retry(
        self,
        text: str,
        model: str,
        dimensions: int
    ) -> Optional[List[float]]:
        """
        Вызов OpenAI API с retry механизмом через tenacity

        Retry strategy:
        - 3 попытки
        - Exponential backoff: 1s, 2s, 4s
        - Retry на RateLimitError, APIError, Timeout
        """

        if not TENACITY_AVAILABLE:
            # Если tenacity не установлена - простой вызов без retry
            return await self._call_openai_api(text, model, dimensions)

        # Создаем retry decorator
        @retry(
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=1, min=1, max=10),
            retry=retry_if_exception_type((RateLimitError, APIError, APITimeoutError, APIConnectionError)),
            before_sleep=before_sleep_log(logger, logging.WARNING),
            reraise=True
        )
        async def _retry_wrapper():
            return await self._call_openai_api(text, model, dimensions)

        try:
            return await _retry_wrapper()
        except Exception as e:
            logger.error(f"❌ All retry attempts exhausted: {e}")
            return None

    async def _call_openai_api(
        self,
        text: str,
        model: str,
        dimensions: int
    ) -> Optional[List[float]]:
        """
        Прямой вызов OpenAI Embeddings API
        """

        start_time = datetime.now()

        try:
            logger.debug(f"🔄 Calling OpenAI API: model={model}, dimensions={dimensions}, text_length={len(text)}")

            # Вызываем OpenAI API
            response = await self.openai_client.embeddings.create(
                model=model,
                input=text,
                dimensions=dimensions
            )

            # Извлекаем embedding
            embedding = response.data[0].embedding

            # Вычисляем метрики
            elapsed_ms = (datetime.now() - start_time).total_seconds() * 1000

            # Подсчет токенов (приблизительно: 1 token ≈ 4 characters)
            estimated_tokens = len(text) // 4

            # Подсчет стоимости
            cost_config = self.embedding_configs.get("standard_personality")
            if model == "text-embedding-3-large":
                cost_config = self.embedding_configs.get("full_personality")

            cost_per_1k = cost_config.get("cost_per_1k", 0.00002)
            cost = (estimated_tokens / 1000) * cost_per_1k

            # Обновляем статистику
            self.embedding_stats["api_calls_success"] += 1
            self.embedding_stats["total_cost"] += cost
            self.embedding_stats["total_tokens_used"] += estimated_tokens

            # Обновляем среднее время создания
            total_calls = self.embedding_stats["api_calls_success"]
            current_avg = self.embedding_stats["avg_creation_time_ms"]
            self.embedding_stats["avg_creation_time_ms"] = (
                (current_avg * (total_calls - 1) + elapsed_ms) / total_calls
            )

            logger.info(
                f"✅ OpenAI embedding created: {dimensions}D, "
                f"{elapsed_ms:.0f}ms, "
                f"~{estimated_tokens} tokens, "
                f"${cost:.6f}"
            )

            return embedding

        except RateLimitError as e:
            logger.warning(f"⚠️ OpenAI Rate Limit hit: {e}")
            raise  # Пробросим для retry

        except APITimeoutError as e:
            logger.warning(f"⚠️ OpenAI API Timeout: {e}")
            raise  # Пробросим для retry

        except APIConnectionError as e:
            logger.warning(f"⚠️ OpenAI Connection Error: {e}")
            raise  # Пробросим для retry

        except APIError as e:
            logger.error(f"❌ OpenAI API Error: {e}")
            raise  # Пробросим для retry

        except Exception as e:
            logger.error(f"❌ Unexpected error calling OpenAI API: {e}")
            self.embedding_stats["api_calls_failed"] += 1
            return None

    async def _create_mock_embedding(self, text: str, dimensions: int) -> List[float]:
        """
        FALLBACK: Создание mock embedding (только когда API недоступен)
        """
        logger.debug(f"🎭 Creating mock embedding: {dimensions}D")

        # Симуляция API call
        await asyncio.sleep(0.05)

        # Генерируем детерминированный вектор на основе текста
        # (чтобы одинаковый текст давал одинаковый вектор)
        seed = hash(text) % (2**32)
        np.random.seed(seed)
        mock_embedding = np.random.random(dimensions).tolist()

        return mock_embedding

    def _should_create_full_embedding(self, user_id: int, summary_data: Dict[str, str]) -> bool:
        """Определить нужен ли full embedding (3072D)"""

        # Full embedding для:
        return any([
            "breakthrough" in summary_data.get("structured", ""),
            "deep_dive" in summary_data.get("narrative", ""),
            user_id % 10 == 0,  # Каждый 10й пользователь для тестирования
            len(summary_data.get("narrative", "")) > 500  # Длинный профиль
        ])

    async def _create_new_vectors(
        self,
        user_id: int,
        embeddings: Dict[str, List[float]],
        analysis_result: Dict[str, Any]
    ) -> bool:
        """Создание новых векторов для пользователя"""

        try:
            current_time = datetime.now().isoformat()

            # Метаданные для всех векторов
            base_payload = {
                "user_id": user_id,
                "created_at": current_time,
                "analysis_version": "2.0",
                "traits": analysis_result["personality_traits"],
                "processing_metadata": analysis_result["processing_metadata"],
                "quality_score": analysis_result["quality_metadata"]["overall_reliability"]
            }

            # 1. Standard profile в основной коллекции
            if "standard" in embeddings:
                await self._store_vector_in_qdrant(
                    collection="personality_profiles",
                    point_id=user_id,
                    vector=embeddings["standard"],
                    payload={
                        **base_payload,
                        "personality_summary": analysis_result["personality_summary"],
                        "vector_type": "standard_profile",
                        "last_updated": current_time
                    }
                )

            # 2. Quick match для быстрого поиска
            if "quick" in embeddings:
                await self._store_vector_in_qdrant(
                    collection="quick_match",
                    point_id=user_id,
                    vector=embeddings["quick"],
                    payload={
                        **base_payload,
                        "nano_summary": analysis_result["personality_summary"]["nano"],
                        "vector_type": "quick_match",
                        "archetype": self._extract_archetype(analysis_result)
                    }
                )

            # 3. Full embedding для истории (если создан)
            if "full" in embeddings:
                # ID должен быть integer или UUID - используем timestamp как уникальный ID
                evolution_id = int(datetime.now().timestamp() * 1000)  # milliseconds
                await self._store_vector_in_qdrant(
                    collection="personality_evolution",
                    point_id=evolution_id,
                    vector=embeddings["full"],
                    payload={
                        **base_payload,
                        "user_id": user_id,  # Важно! ID пользователя для фильтрации
                        "snapshot_id": evolution_id,
                        "full_narrative": analysis_result["personality_summary"]["narrative"],
                        "vector_type": "evolution_snapshot",
                        "is_milestone": analysis_result["processing_metadata"].get("special_situation") == "breakthrough"
                    }
                )

            return True

        except Exception as e:
            logger.error(f"❌ Error creating new vectors for user {user_id}: {e}")
            return False

    async def _update_existing_vectors(
        self,
        user_id: int,
        embeddings: Dict[str, List[float]],
        analysis_result: Dict[str, Any]
    ) -> bool:
        """
        Обновление существующих векторов с сохранением истории
        """

        try:
            logger.info(f"🔄 Updating existing vectors for user {user_id}")

            # 1. Получаем текущий профиль
            current_profile = await self._get_current_profile(user_id)

            # 2. Вычисляем дельту изменений
            if current_profile:
                delta = self._calculate_personality_delta(current_profile, analysis_result)
                logger.info(f"📊 Personality delta magnitude: {delta.get('magnitude', 0):.3f}")
            else:
                delta = {"magnitude": 1.0, "significant_changes": [], "first_profile": True}

            # 3. Определяем стратегию обновления
            if delta["magnitude"] > 0.3:
                # Значительные изменения - сохраняем как breakthrough
                await self._save_breakthrough_moment(user_id, current_profile, analysis_result, embeddings)
                update_strategy = "breakthrough_merge"
            elif delta["magnitude"] > 0.1:
                # Средние изменения - адаптивное слияние
                update_strategy = "adaptive_merge"
            else:
                # Малые изменения - простое взвешенное среднее
                update_strategy = "weighted_average"

            # 4. Применяем стратегию обновления
            success = await self._apply_update_strategy(
                user_id, embeddings, analysis_result, current_profile, update_strategy, delta
            )

            return success

        except Exception as e:
            logger.error(f"❌ Error updating vectors for user {user_id}: {e}")
            return False

    def _calculate_personality_delta(self, current_profile: Dict, new_analysis: Dict) -> Dict[str, Any]:
        """Вычисление изменений в личности"""

        try:
            current_traits = current_profile.get("traits", {}).get("big_five", {})
            new_traits = new_analysis.get("personality_traits", {}).get("big_five", {})

            if not current_traits or not new_traits:
                return {"magnitude": 1.0, "first_profile": True}

            # Считаем евклидово расстояние между векторами черт
            trait_differences = []
            significant_changes = []

            for trait in self.config.BIG_FIVE_TRAITS:
                # Получаем значения - могут быть float или dict с "score"
                old_raw = current_traits.get(trait, 0.5)
                new_raw = new_traits.get(trait, 0.5)

                # Извлекаем score если это dict
                old_value = old_raw.get("score", 0.5) if isinstance(old_raw, dict) else old_raw
                new_value = new_raw.get("score", 0.5) if isinstance(new_raw, dict) else new_raw

                diff = abs(new_value - old_value)

                trait_differences.append(diff)

                # Значимые изменения (больше 0.1)
                if diff > 0.1:
                    direction = "увеличение" if new_value > old_value else "снижение"
                    significant_changes.append({
                        "trait": trait,
                        "change": diff,
                        "direction": direction,
                        "old_value": old_value,
                        "new_value": new_value
                    })

            magnitude = np.sqrt(sum(d**2 for d in trait_differences)) / len(trait_differences)

            return {
                "magnitude": magnitude,
                "significant_changes": significant_changes,
                "trait_differences": trait_differences,
                "is_breakthrough": magnitude > 0.3,
                "is_evolution": 0.1 < magnitude <= 0.3,
                "is_minor_update": magnitude <= 0.1
            }

        except Exception as e:
            logger.error(f"❌ Error calculating personality delta: {e}")
            return {"magnitude": 0.0, "error": str(e)}

    async def _save_breakthrough_moment(
        self,
        user_id: int,
        current_profile: Optional[Dict],
        analysis_result: Dict[str, Any],
        embeddings: Dict[str, List[float]]
    ) -> bool:
        """
        Сохранить момент прорыва в personality_evolution коллекцию

        Args:
            user_id: ID пользователя
            current_profile: Текущий профиль (до изменений)
            analysis_result: Результаты нового анализа
            embeddings: Созданные векторы

        Returns:
            True если успешно сохранено
        """
        try:
            logger.info(f"🌟 Saving breakthrough moment for user {user_id}")

            # Используем timestamp как уникальный ID для snapshot
            breakthrough_id = int(datetime.now().timestamp() * 1000)  # milliseconds

            # Определяем какой вектор использовать для breakthrough
            # Используем standard вектор (1536D) для отслеживания эволюции личности
            vector_to_save = embeddings.get("standard")

            if not vector_to_save:
                logger.warning(f"⚠️ No standard (1536D) vector available - cannot save breakthrough moment")
                return False

            # Формируем payload с полной информацией о прорыве
            payload = {
                "user_id": user_id,
                "created_at": datetime.now().isoformat(),
                "snapshot_id": breakthrough_id,
                "vector_type": "breakthrough_snapshot",
                "is_milestone": True,

                # Информация о прорыве
                "breakthrough_info": {
                    "magnitude": analysis_result.get("personality_traits", {}).get("magnitude", 0.3),
                    "significant_changes": analysis_result.get("personality_traits", {}).get("significant_changes", []),
                    "trigger_question": analysis_result.get("processing_metadata", {}).get("question_number"),
                    "trigger_domain": analysis_result.get("processing_metadata", {}).get("question_domain")
                },

                # Snapshot личности на момент прорыва
                "personality_snapshot": {
                    "big_five": analysis_result.get("personality_traits", {}).get("big_five", {}),
                    "dynamic_traits": analysis_result.get("personality_traits", {}).get("dynamic_traits", {}),
                    "narrative": analysis_result.get("personality_summary", {}).get("narrative", "")
                },

                # Предыдущее состояние (если есть)
                "previous_state": current_profile.get("traits", {}).get("big_five", {}) if current_profile else None
            }

            # Сохраняем в Qdrant
            success = await self._store_vector_in_qdrant(
                collection="personality_evolution",
                point_id=breakthrough_id,
                vector=vector_to_save,
                payload=payload
            )

            if success:
                logger.info(f"✅ Breakthrough moment saved with ID {breakthrough_id}")
            else:
                logger.error(f"❌ Failed to save breakthrough moment")

            return success

        except Exception as e:
            logger.error(f"❌ Error saving breakthrough moment for user {user_id}: {e}")
            return False

    async def _apply_update_strategy(
        self,
        user_id: int,
        embeddings: Dict[str, List[float]],
        analysis_result: Dict[str, Any],
        current_profile: Optional[Dict],
        strategy: str,
        delta: Dict[str, Any]
    ) -> bool:
        """Применение стратегии обновления векторов"""

        try:
            current_time = datetime.now().isoformat()

            if strategy == "weighted_average":
                # Простое взвешенное среднее для малых изменений
                if current_profile and "standard" in embeddings:
                    # Смешиваем старый и новый векторы (80% старый, 20% новый)
                    old_vector = current_profile.get("vector", [])
                    new_vector = embeddings["standard"]

                    if len(old_vector) == len(new_vector):
                        merged_vector = [
                            0.8 * old + 0.2 * new
                            for old, new in zip(old_vector, new_vector)
                        ]
                        embeddings["standard"] = merged_vector
                        logger.info(f"🔄 Applied weighted average update")

            elif strategy == "adaptive_merge":
                # Адаптивное слияние с учетом уверенности
                confidence = analysis_result["quality_metadata"]["overall_reliability"]
                merge_weight = min(0.5, confidence * 0.6)  # Максимум 50% влияния нового

                logger.info(f"🎯 Applied adaptive merge with weight {merge_weight:.2f}")

            elif strategy == "breakthrough_merge":
                # Сохраняем момент прорыва
                logger.info(f"🌟 Applied breakthrough merge - milestone saved")

            # Сохраняем обновленные векторы
            success = await self._save_updated_vectors(
                user_id, embeddings, analysis_result, current_time, strategy, delta
            )

            return success

        except Exception as e:
            logger.error(f"❌ Error applying update strategy {strategy}: {e}")
            return False

    async def _save_updated_vectors(
        self,
        user_id: int,
        embeddings: Dict[str, List[float]],
        analysis_result: Dict[str, Any],
        timestamp: str,
        strategy: str,
        delta: Dict[str, Any]
    ) -> bool:
        """Сохранение обновленных векторов в Qdrant"""

        try:
            # Общие метаданные
            base_payload = {
                "user_id": user_id,
                "updated_at": timestamp,
                "update_strategy": strategy,
                "personality_delta": delta,
                "analysis_version": "2.0",
                "traits": analysis_result["personality_traits"],
                "summary": analysis_result["personality_summary"],
                "quality_score": analysis_result["quality_metadata"]["overall_reliability"]
            }

            # Обновляем каждый тип вектора
            updates_successful = []

            # Standard profile
            if "standard" in embeddings:
                success = await self._store_vector_in_qdrant(
                    collection="personality_profiles",
                    point_id=user_id,
                    vector=embeddings["standard"],
                    payload={**base_payload, "vector_type": "current_profile"}
                )
                updates_successful.append(success)

            # Quick match
            if "quick" in embeddings:
                success = await self._store_vector_in_qdrant(
                    collection="quick_match",
                    point_id=user_id,
                    vector=embeddings["quick"],
                    payload={
                        **base_payload,
                        "vector_type": "quick_search",
                        "archetype": self._extract_archetype(analysis_result),
                        "primary_domain": analysis_result["processing_metadata"]["question_domain"]
                    }
                )
                updates_successful.append(success)

            # Evolution snapshot (всегда создаем новый)
            if "standard" in embeddings:
                # ID должен быть integer или UUID - используем timestamp как уникальный ID
                evolution_id = int(datetime.now().timestamp() * 1000)  # milliseconds
                success = await self._store_vector_in_qdrant(
                    collection="personality_evolution",
                    point_id=evolution_id,
                    vector=embeddings["standard"],  # Используем standard для истории
                    payload={
                        **base_payload,
                        "user_id": user_id,  # Важно! ID пользователя для фильтрации
                        "snapshot_id": evolution_id,
                        "vector_type": "evolution_point",
                        "delta_magnitude": delta["magnitude"],
                        "significant_changes": delta["significant_changes"]
                    }
                )
                updates_successful.append(success)

            return all(updates_successful)

        except Exception as e:
            logger.error(f"❌ Error saving updated vectors: {e}")
            return False

    async def _store_vector_in_qdrant(
        self,
        collection: str,
        point_id: Any,
        vector: List[float],
        payload: Dict[str, Any]
    ) -> bool:
        """
        Сохранение вектора в Qdrant коллекции
        """

        try:
            if not self.qdrant_client:
                logger.error(f"❌ Qdrant client not available - cannot store vector")
                return False

            # Реальное сохранение в Qdrant
            self.qdrant_client.upsert(
                collection_name=collection,
                points=[
                    PointStruct(
                        id=point_id,
                        vector=vector,
                        payload=payload
                    )
                ]
            )

            logger.info(f"💾 Vector stored in {collection} (ID: {point_id}, dims: {len(vector)})")
            return True

        except Exception as e:
            logger.error(f"❌ Error storing vector in {collection}: {e}")
            return False

    async def _get_current_profile(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Получение текущего профиля пользователя из Qdrant"""

        try:
            # MOCK для разработки
            # В реальной системе:
            # result = await self.qdrant_client.retrieve(
            #     collection_name="personality_profiles",
            #     ids=[user_id]
            # )
            # return result[0].payload if result else None

            # Симуляция отсутствия профиля для новых пользователей
            return None

        except Exception as e:
            logger.error(f"❌ Error getting current profile for user {user_id}: {e}")
            return None

    async def search_similar_personalities(
        self,
        user_id: int,
        limit: int = 10,
        similarity_threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        Поиск похожих личностей

        Args:
            user_id: ID пользователя для поиска похожих
            limit: Максимальное количество результатов
            similarity_threshold: Минимальный порог схожести

        Returns:
            Список похожих пользователей с объяснением схожести
        """

        try:
            # Получаем профиль пользователя
            user_profile = await self._get_current_profile(user_id)

            if not user_profile:
                logger.warning(f"⚠️ No profile found for user {user_id}")
                return []

            # MOCK для разработки
            # В реальной системе поиск через Qdrant:
            # search_result = await self.qdrant_client.search(
            #     collection_name="quick_match",
            #     query_vector=user_profile["vector"],
            #     limit=limit,
            #     score_threshold=similarity_threshold
            # )

            # Симуляция результатов поиска
            mock_results = [
                {
                    "user_id": f"user_{i}",
                    "similarity_score": 0.85 - i * 0.05,
                    "archetype": "Похожий Тип",
                    "shared_traits": ["openness", "creativity"],
                    "explanation": f"Схожесть в творческом подходе и открытости новому"
                }
                for i in range(min(3, limit))  # Мок 3 результата
            ]

            logger.info(f"🔍 Found {len(mock_results)} similar personalities for user {user_id}")
            return mock_results

        except Exception as e:
            logger.error(f"❌ Error searching similar personalities: {e}")
            return []

    async def setup_qdrant_collections(self) -> bool:
        """
        Создание коллекций Qdrant для многоуровневой архитектуры
        """

        if not self.qdrant_client:
            logger.error("❌ Qdrant client not initialized - cannot create collections")
            return False

        try:
            logger.info("🏗️ Setting up Qdrant collections...")

            # Конфигурация коллекций - используем имена из embedding_configs
            collections_config = [
                {
                    "name": "quick_match",  # self.embedding_configs["quick_match"]["collection"]
                    "size": 512,
                    "distance": Distance.COSINE,
                    "description": "Quick matching and filtering"
                },
                {
                    "name": "personality_profiles",  # self.embedding_configs["standard_personality"]["collection"]
                    "size": 1536,
                    "distance": Distance.COSINE,
                    "description": "Main personality profiles"
                },
                {
                    "name": "personality_evolution",
                    "size": 1536,  # Используем standard вектор для отслеживания эволюции
                    "distance": Distance.COSINE,
                    "description": "Personality evolution tracking and breakthrough moments"
                }
            ]

            created_count = 0
            for config in collections_config:
                try:
                    # Проверяем существование коллекции
                    existing_collections = self.qdrant_client.get_collections()
                    collection_names = [c.name for c in existing_collections.collections]

                    if config["name"] in collection_names:
                        logger.info(f"✅ Collection '{config['name']}' already exists")
                        created_count += 1
                        continue

                    # Создаем новую коллекцию
                    self.qdrant_client.create_collection(
                        collection_name=config["name"],
                        vectors_config=VectorParams(
                            size=config["size"],
                            distance=config["distance"]
                        )
                    )
                    logger.info(f"✅ Created collection '{config['name']}' ({config['description']})")
                    created_count += 1

                except Exception as e:
                    logger.error(f"❌ Failed to create collection '{config['name']}': {e}")
                    # НЕ подавляем ошибку - пробрасываем дальше
                    raise

            success = created_count == len(collections_config)
            if success:
                logger.info(f"🎉 Successfully initialized {created_count} Qdrant collections")
            else:
                logger.warning(f"⚠️ Only {created_count}/{len(collections_config)} collections created")

            return success

        except Exception as e:
            logger.error(f"❌ Error setting up Qdrant collections: {e}")
            return False

    def _extract_archetype(self, analysis_result: Dict[str, Any]) -> str:
        """Извлечение архетипа личности из анализа"""

        summary = analysis_result.get("personality_summary", {})
        structured = summary.get("structured", "")

        # Ищем архетип в структурированном профиле
        if "archetype" in structured:
            try:
                structured_data = json.loads(structured)
                return structured_data.get("archetype", "Неопределенный Тип")
            except:
                pass

        # Fallback из traits
        traits = analysis_result.get("personality_traits", {}).get("big_five", {})
        if traits:
            # Простое определение архетипа
            if traits.get("openness", 0) > 0.7:
                return "Творческий Исследователь"
            elif traits.get("conscientiousness", 0) > 0.7:
                return "Организованный Деятель"
            elif traits.get("extraversion", 0) > 0.7:
                return "Социальный Коммуникатор"
            elif traits.get("agreeableness", 0) > 0.7:
                return "Эмпатичный Помощник"
            else:
                return "Сбалансированная Личность"

        return "Развивающаяся Личность"

    async def get_embedding_stats(self) -> Dict[str, Any]:
        """Получить статистику создания векторов"""

        total_calls = self.embedding_stats["api_calls_success"] + self.embedding_stats["api_calls_failed"]

        return {
            **self.embedding_stats,
            "collections_status": await self._get_collections_status(),
            "cost_per_vector": (
                self.embedding_stats["total_cost"] / max(1, self.embedding_stats["vectors_created"])
            ),
            "efficiency_metrics": {
                "success_rate": (
                    self.embedding_stats["api_calls_success"] / max(1, total_calls)
                ) * 100,
                "cache_hit_rate": (
                    self.embedding_stats["cache_hits"] /
                    max(1, self.embedding_stats["cache_hits"] + self.embedding_stats["cache_misses"])
                ) * 100,
                "avg_cost_per_call": (
                    self.embedding_stats["total_cost"] / max(1, self.embedding_stats["api_calls_success"])
                ),
                "total_api_calls": total_calls
            }
        }

    async def _get_collections_status(self) -> Dict[str, Any]:
        """Получить статус коллекций Qdrant"""

        # MOCK для разработки
        return {
            "personality_profiles": {"count": 0, "size": "1536D"},
            "quick_match": {"count": 0, "size": "512D"},
            "personality_evolution": {"count": 0, "size": "1536D"}
        }
