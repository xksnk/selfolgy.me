"""
Multi-Model Embedding Service для цифрового отпечатка личности

Поддерживает:
- RuBERT Conversational (768d) - для episodic_memory
- GigaEmbeddings/Cohere (2048d/1024d) - для semantic_knowledge
- Hybrid embeddings (1536d) - для emotional_thematic
"""

import numpy as np
from typing import List, Optional, Dict, Any
from sentence_transformers import SentenceTransformer
import logging
import time
import os
from dotenv import load_dotenv

from core.error_collector import error_collector
import asyncio

# Загружаем .env если есть
load_dotenv()

logger = logging.getLogger(__name__)

# OpenAI for semantic embeddings
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("⚠️ OpenAI package not installed")


class EmbeddingService:
    """
    Unified embedding service с multiple models для разных коллекций Qdrant

    Коллекции и модели:
    - episodic_memory: RuBERT (768d) - сырые ответы пользователя
    - semantic_knowledge: GigaEmbed/Cohere (2048d/1024d) - AI анализ
    - emotional_thematic: Hybrid (1536d) - эмоциональные паттерны
    - psychological_constructs: GigaEmbed (1024d) - убеждения, защиты
    - meta_patterns: GigaEmbed (1024d) - слепые зоны, рост
    """

    def __init__(self):
        self._rubert_model = None
        self._gigaembed_client = None
        self._cohere_client = None
        self._openai_client = None

        # Флаги инициализации
        self._rubert_loaded = False
        self._gigaembed_available = False
        self._cohere_available = False
        self._openai_available = False

        # Инициализируем OpenAI если есть ключ
        if OPENAI_AVAILABLE:
            api_key = os.getenv("OPENAI_API_KEY")
            if api_key:
                self._openai_client = OpenAI(api_key=api_key)
                self._openai_available = True
                logger.info("✅ OpenAI client initialized for semantic embeddings (2048d)")
            else:
                logger.warning("⚠️ OPENAI_API_KEY not found")

        logger.info("EmbeddingService initialized (lazy loading)")

    def _load_rubert(self):
        """Lazy load RuBERT model (768d)"""
        if not self._rubert_loaded:
            logger.info("Loading RuBERT Conversational model...")
            start = time.time()
            self._rubert_model = SentenceTransformer('DeepPavlov/rubert-base-cased-conversational')
            self._rubert_loaded = True
            logger.info(f"✅ RuBERT loaded in {time.time()-start:.1f}s")
        return self._rubert_model

    def _setup_gigaembed(self, api_key: str):
        """Setup GigaEmbeddings API (2048d)"""
        # TODO: Implement GigaChat API integration
        # https://developers.sber.ru/docs/ru/gigachat/api/reference/rest/post-embeddings
        self._gigaembed_available = False
        logger.warning("⚠️ GigaEmbeddings not yet implemented")

    def _setup_cohere(self, api_key: str):
        """Setup Cohere API as fallback (1024d)"""
        try:
            import cohere
            self._cohere_client = cohere.Client(api_key)
            self._cohere_available = True
            logger.info("✅ Cohere client initialized")
        except ImportError:
            logger.warning("⚠️ Cohere package not installed")
        except Exception as e:
            logger.error(f"❌ Cohere setup failed: {e}")

    # ===================
    # PUBLIC API
    # ===================

    def encode_episodic(self, text: str) -> np.ndarray:
        """
        Encode raw user text for episodic_memory collection

        Model: RuBERT Conversational (768d)
        Use: Сырые ответы пользователя
        """
        model = self._load_rubert()
        embedding = model.encode(text, convert_to_numpy=True)
        return embedding.astype(np.float32)

    def encode_episodic_batch(self, texts: List[str], batch_size: int = 32) -> np.ndarray:
        """Batch encode for episodic_memory"""
        model = self._load_rubert()
        embeddings = model.encode(texts, batch_size=batch_size, convert_to_numpy=True)
        return embeddings.astype(np.float32)

    def encode_semantic(self, text: str) -> np.ndarray:
        """
        Encode AI analysis for semantic_knowledge collection

        Model: OpenAI text-embedding-3-large (2048d) или fallbacks
        Use: AI анализ, психологические конструкты
        """
        # Try OpenAI first (best quality for semantic analysis)
        if self._openai_available:
            return self._encode_openai(text, dimensions=2048)

        # Try GigaEmbeddings
        if self._gigaembed_available:
            return self._encode_gigaembed(text)

        # Fallback to Cohere
        if self._cohere_available:
            return self._encode_cohere(text)

        # Ultimate fallback: use RuBERT and pad to 2048d
        logger.warning("⚠️ No semantic model available, using RuBERT fallback (768d → 2048d padded)")
        rubert_emb = self.encode_episodic(text)
        # Pad to 2048 dimensions
        padded = np.zeros(2048, dtype=np.float32)
        padded[:768] = rubert_emb
        return padded

    def _encode_openai(self, text: str, dimensions: int = 2048) -> np.ndarray:
        """
        OpenAI text-embedding-3-large API call

        Supports variable dimensions (256-3072)
        """
        if not self._openai_client:
            raise RuntimeError("OpenAI client not initialized")

        try:
            response = self._openai_client.embeddings.create(
                model="text-embedding-3-large",
                input=text,
                dimensions=dimensions
            )

            embedding = np.array(response.data[0].embedding, dtype=np.float32)
            return embedding
        except Exception as e:
            logger.error(f"❌ OpenAI embedding API failed: {e}")
            # Собираем ошибку синхронно (через asyncio)
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(error_collector.collect(
                        error=e,
                        service="EmbeddingService",
                        component="openai_embedding",
                        context={"text_length": len(text), "dimensions": dimensions}
                    ))
            except Exception:
                pass  # Не блокируем основную ошибку
            raise

    def encode_emotional(self, text: str, emotion: Optional[str] = None) -> np.ndarray:
        """
        Encode for emotional_thematic collection

        Model: Hybrid (text + emotion context) = 1536d
        Use: Эмоциональные паттерны
        """
        # Base text embedding (768d from RuBERT)
        text_emb = self.encode_episodic(text)

        # Emotion context embedding (768d)
        if emotion:
            emotion_text = f"Эмоция: {emotion}. {text[:100]}"
            emotion_emb = self.encode_episodic(emotion_text)
        else:
            emotion_emb = np.zeros(768, dtype=np.float32)

        # Concatenate to 1536d
        hybrid = np.concatenate([text_emb, emotion_emb])
        return hybrid.astype(np.float32)

    def encode_construct(self, text: str) -> np.ndarray:
        """
        Encode for psychological_constructs collection

        Model: OpenAI text-embedding-3-large (1024d) или fallback
        Use: Core beliefs, defense mechanisms
        """
        # Use OpenAI with native 1024d dimensions
        if self._openai_available:
            return self._encode_openai(text, dimensions=1024)

        # Fallback: use semantic model and truncate/pad to 1024
        semantic_emb = self.encode_semantic(text)

        if len(semantic_emb) >= 1024:
            return semantic_emb[:1024]
        else:
            padded = np.zeros(1024, dtype=np.float32)
            padded[:len(semantic_emb)] = semantic_emb
            return padded

    def encode_pattern(self, text: str) -> np.ndarray:
        """
        Encode for meta_patterns collection

        Model: 1024d
        Use: Blind spots, growth areas
        """
        return self.encode_construct(text)

    # ===================
    # PRIVATE METHODS
    # ===================

    def _encode_gigaembed(self, text: str) -> np.ndarray:
        """GigaEmbeddings API call"""
        # TODO: Implement
        raise NotImplementedError("GigaEmbeddings not yet implemented")

    def _encode_cohere(self, text: str) -> np.ndarray:
        """Cohere API call"""
        if not self._cohere_client:
            raise RuntimeError("Cohere client not initialized")

        response = self._cohere_client.embed(
            texts=[text],
            model="embed-multilingual-v3.0",
            input_type="search_document"
        )
        embedding = np.array(response.embeddings[0], dtype=np.float32)

        # Pad to 2048d if needed (Cohere is 1024d)
        if len(embedding) < 2048:
            padded = np.zeros(2048, dtype=np.float32)
            padded[:len(embedding)] = embedding
            return padded

        return embedding

    # ===================
    # UTILITY METHODS
    # ===================

    def get_model_info(self) -> Dict[str, Any]:
        """Get information about available models"""
        return {
            "rubert": {
                "available": self._rubert_loaded or True,  # Always available
                "dimensions": 768,
                "model": "DeepPavlov/rubert-base-cased-conversational",
                "use_case": "episodic_memory"
            },
            "openai": {
                "available": self._openai_available,
                "dimensions": "2048/1024 (configurable)",
                "model": "text-embedding-3-large",
                "use_case": "semantic_knowledge, psychological_constructs, meta_patterns"
            },
            "gigaembed": {
                "available": self._gigaembed_available,
                "dimensions": 2048,
                "model": "GigaChat Embeddings",
                "use_case": "semantic_knowledge (alternative)"
            },
            "cohere": {
                "available": self._cohere_available,
                "dimensions": 1024,
                "model": "embed-multilingual-v3.0",
                "use_case": "semantic_knowledge (fallback)"
            },
            "hybrid": {
                "available": True,
                "dimensions": 1536,
                "model": "RuBERT + Emotion context",
                "use_case": "emotional_thematic"
            }
        }

    def health_check(self) -> Dict[str, bool]:
        """Check health of all embedding services"""
        return {
            "rubert": self._rubert_loaded or self._load_rubert() is not None,
            "openai": self._openai_available,
            "gigaembed": self._gigaembed_available,
            "cohere": self._cohere_available
        }


# Singleton instance
_embedding_service = None

def get_embedding_service() -> EmbeddingService:
    """Get singleton EmbeddingService instance"""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service
