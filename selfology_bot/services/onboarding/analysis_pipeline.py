"""
AnalysisPipeline - Единый интерфейс для анализа ответов пользователей.

Инкапсулирует весь пайплайн:
1. AI анализ ответа (AnswerAnalyzer)
2. Извлечение данных личности (PersonalityExtractor)
3. Обновление цифрового профиля (DigitalPersonalityDAO)
4. Создание векторов (EmbeddingCreator)

Использование:
    pipeline = AnalysisPipeline(db_pool)
    await pipeline.initialize()
    result = await pipeline.process_answer(user_id, question_data, answer_text)
"""

import logging
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass
from contextlib import asynccontextmanager

import asyncpg

logger = logging.getLogger(__name__)


class PoolWrapper:
    """
    Wrapper для asyncpg.Pool с интерфейсом DatabaseService.

    DigitalPersonalityDAO ожидает объект с методом get_connection(),
    а у нас есть Pool. Этот wrapper делает их совместимыми.
    """

    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool

    @asynccontextmanager
    async def get_connection(self):
        """Получить соединение из пула (как в DatabaseService)"""
        async with self.pool.acquire() as connection:
            yield connection


@dataclass
class AnalysisResult:
    """Результат анализа ответа"""
    success: bool
    analysis_id: Optional[int] = None
    ai_analysis: Optional[Dict] = None
    personality_updated: bool = False
    vectors_created: bool = False
    processing_time_ms: int = 0
    error: Optional[str] = None


class AnalysisPipeline:
    """
    Единый пайплайн анализа ответов.

    Координирует:
    - AnswerAnalyzer: AI анализ (Big Five, эмоции, инсайты)
    - PersonalityExtractor: извлечение конкретных данных
    - DigitalPersonalityDAO: обновление профиля в PostgreSQL
    - EmbeddingCreator: векторы в Qdrant
    """

    def __init__(self, db_pool: asyncpg.Pool = None):
        """
        Инициализация пайплайна.

        Args:
            db_pool: Пул подключений к PostgreSQL
        """
        self.db_pool = db_pool
        self._initialized = False

        # Компоненты (инициализируются в initialize())
        self.answer_analyzer = None
        self.personality_extractor = None
        self.embedding_creator = None
        self.personality_dao = None

        logger.info("📊 AnalysisPipeline created (not initialized yet)")

    async def initialize(self) -> bool:
        """
        Инициализация всех компонентов.

        Returns:
            True если успешно, False при ошибке
        """
        if self._initialized:
            return True

        try:
            # Импортируем компоненты (lazy import для избежания циклических зависимостей)
            from selfology_bot.analysis.answer_analyzer import AnswerAnalyzer
            from selfology_bot.analysis.personality_extractor import PersonalityExtractor
            from selfology_bot.analysis.embedding_creator import EmbeddingCreator
            from selfology_bot.database.digital_personality_dao import DigitalPersonalityDAO

            # Инициализируем компоненты
            self.answer_analyzer = AnswerAnalyzer()
            self.personality_extractor = PersonalityExtractor()
            self.embedding_creator = EmbeddingCreator()

            # DAO требует объект с get_connection() - используем wrapper
            if self.db_pool:
                db_wrapper = PoolWrapper(self.db_pool)
                self.personality_dao = DigitalPersonalityDAO(db_wrapper)
            else:
                logger.warning("⚠️ No db_pool - personality updates will be skipped")

            # Инициализируем Qdrant коллекции
            await self._setup_qdrant_collections()

            self._initialized = True
            logger.info("✅ AnalysisPipeline initialized with all components")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to initialize AnalysisPipeline: {e}")
            return False

    async def _setup_qdrant_collections(self):
        """Создать Qdrant коллекции если не существуют"""
        if self.embedding_creator:
            try:
                await self.embedding_creator.setup_qdrant_collections()
                logger.info("✅ Qdrant collections ready")
            except Exception as e:
                logger.warning(f"⚠️ Qdrant setup warning: {e}")

    async def process_answer(
        self,
        user_id: int,
        question_data: Dict[str, Any],
        answer_text: str,
        answer_history: Optional[list] = None
    ) -> AnalysisResult:
        """
        Обработать ответ пользователя через полный пайплайн.

        Args:
            user_id: ID пользователя
            question_data: Данные вопроса (text, id, metadata)
            answer_text: Текст ответа
            answer_history: История предыдущих ответов (для контекста)

        Returns:
            AnalysisResult с результатами обработки
        """
        if not self._initialized:
            await self.initialize()

        start_time = datetime.now()
        result = AnalysisResult(success=False)

        try:
            logger.info(f"🔬 Starting analysis pipeline for user {user_id}")

            # ═══════════════════════════════════════════════════════════════
            # ЭТАП 1: AI Анализ ответа
            # ═══════════════════════════════════════════════════════════════

            user_context = self._build_user_context(user_id, answer_history)

            ai_analysis = await self.answer_analyzer.analyze_answer(
                question_data=question_data,
                user_answer=answer_text,
                user_context=user_context
            )

            result.ai_analysis = ai_analysis
            logger.info(f"✅ AI analysis complete for user {user_id}")

            # ═══════════════════════════════════════════════════════════════
            # ЭТАП 2: Извлечение и обновление цифровой личности
            # ═══════════════════════════════════════════════════════════════

            if self.personality_dao:
                try:
                    # Получаем существующий профиль
                    existing_personality = await self.personality_dao.get_personality(user_id)

                    # Извлекаем конкретные данные из ответа
                    extracted = await self.personality_extractor.extract_from_answer(
                        question_text=question_data.get("text", ""),
                        user_answer=answer_text,
                        question_metadata=question_data.get("block_metadata", {}),
                        existing_personality=existing_personality
                    )

                    # Обновляем или создаём профиль
                    if existing_personality:
                        merged = self.personality_extractor.merge_extractions(
                            existing_personality,
                            extracted
                        )
                        await self.personality_dao.update_personality(user_id, merged, merge=True)
                        logger.info(f"🧬 Updated digital personality for user {user_id}")
                    else:
                        await self.personality_dao.create_personality(user_id, extracted)
                        logger.info(f"🧬 Created digital personality for user {user_id}")

                    result.personality_updated = True

                except Exception as e:
                    logger.error(f"❌ Personality update failed for user {user_id}: {e}")

            # ═══════════════════════════════════════════════════════════════
            # ЭТАП 3: Создание векторов в Qdrant
            # ═══════════════════════════════════════════════════════════════

            if self.embedding_creator:
                try:
                    is_update = bool(answer_history and len(answer_history) > 0)

                    vector_success = await self.embedding_creator.create_personality_vector(
                        user_id=user_id,
                        analysis_result=ai_analysis,
                        is_update=is_update
                    )

                    result.vectors_created = vector_success
                    if vector_success:
                        logger.info(f"📊 Vectors created for user {user_id}")
                    else:
                        logger.warning(f"⚠️ Vector creation returned False for user {user_id}")

                except Exception as e:
                    logger.error(f"❌ Vector creation failed for user {user_id}: {e}")

            # ═══════════════════════════════════════════════════════════════
            # ФИНАЛ: Подсчёт времени и результат
            # ═══════════════════════════════════════════════════════════════

            result.processing_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            result.success = True

            logger.info(
                f"✅ Analysis pipeline completed for user {user_id} in {result.processing_time_ms}ms "
                f"(personality: {'✅' if result.personality_updated else '❌'}, "
                f"vectors: {'✅' if result.vectors_created else '❌'})"
            )

        except Exception as e:
            result.error = str(e)
            result.processing_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            logger.error(f"❌ Analysis pipeline failed for user {user_id}: {e}", exc_info=True)

        return result

    def _build_user_context(
        self,
        user_id: int,
        answer_history: Optional[list] = None
    ) -> Dict[str, Any]:
        """Построить контекст пользователя для AI анализа"""
        return {
            "user_id": user_id,
            "answer_history": answer_history or [],
            "total_answers": len(answer_history) if answer_history else 0,
            "session_start": datetime.now().isoformat()
        }

    async def shutdown(self):
        """Graceful shutdown пайплайна"""
        logger.info("🛑 AnalysisPipeline shutting down")
        # Компоненты не требуют явного shutdown
        self._initialized = False
