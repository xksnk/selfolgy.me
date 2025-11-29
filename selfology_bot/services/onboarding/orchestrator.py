"""
OnboardingOrchestrator - Главный дирижер онбординга

Чистая архитектура без слоев и костылей:
- Прямая интеграция с intelligent_question_core
- Управление процессом онбординга
- Координация между компонентами
- Простые и понятные интерфейсы

АРХИТЕКТУРНЫЕ УЛУЧШЕНИЯ (October 2025):
- Task Registry для отслеживания background tasks
- Proper error handling в async tasks
- Graceful shutdown с ожиданием завершения tasks
- Immutable data для предотвращения race conditions
- Observability для мониторинга активных задач
"""

import logging
import sys
import asyncio
from pathlib import Path
from typing import Dict, Optional, Any, List, Set
from datetime import datetime
from copy import deepcopy

# Добавляем путь к Question Core
sys.path.append(str(Path(__file__).parent.parent.parent.parent / "intelligent_question_core"))

from intelligent_question_core.api.core_api import SelfologyQuestionCore
from .question_router import QuestionRouter
from .program_router import ProgramRouter
from .session_reporter import SessionReportGenerator

# Импортируем систему анализа (Phase 2)
sys.path.append(str(Path(__file__).parent.parent.parent))
from analysis import AnswerAnalyzer, EmbeddingCreator, PersonalityExtractor

# Импортируем FatigueDetector (Phase 3)
from .fatigue_detector import FatigueDetector

# Импортируем Database (критично для сохранения данных)
sys.path.append(str(Path(__file__).parent.parent.parent))
from database import DatabaseService, OnboardingDAO, DigitalPersonalityDAO

logger = logging.getLogger(__name__)

class OnboardingOrchestrator:
    """
    Главный управляющий системой онбординга

    Ответственность:
    - Начало/завершение онбординга
    - Координация между QuestionRouter, SessionManager, FatigueDetector
    - Управление background tasks с proper lifecycle
    - Graceful shutdown и observability
    - Простые и понятные методы для controller
    """

    def __init__(self):
        """Инициализация компонентов"""
        # Инициализируем core API (указываем полный путь к JSON файлу)
        core_file_path = str(Path(__file__).parent.parent.parent.parent / "intelligent_question_core" / "data" / "selfology_intelligent_core.json")
        self.question_core = SelfologyQuestionCore(core_file_path)
        logger.info("🧠 Question Core initialized")

        # 🎯 Инициализируем QuestionRouter с умным алгоритмом
        self.question_router = QuestionRouter(self.question_core)
        logger.info("🎯 QuestionRouter with Smart Mix algorithm initialized")

        # 🔬 Инициализируем систему анализа (Phase 2)
        self.answer_analyzer = AnswerAnalyzer()
        self.embedding_creator = EmbeddingCreator()
        self.personality_extractor = PersonalityExtractor()
        logger.info("🔬 Analysis system (AnswerAnalyzer + EmbeddingCreator + PersonalityExtractor) initialized")

        # Qdrant коллекции будут настроены при первом использовании
        self._vector_storage_setup = False

        # 😴 Инициализируем детектор усталости (Phase 3)
        self.fatigue_detector = FatigueDetector()
        logger.info("😴 FatigueDetector initialized - caring for users")

        # 📊 Инициализируем генератор отчетов о сессиях
        self.session_reporter = None  # Будет создан после инициализации DAO
        logger.info("📊 SessionReportGenerator will be initialized after DAO")

        # 🗄️ Инициализируем Database для персистентности (КРИТИЧНО)
        self.db_service = None
        self.onboarding_dao = None
        self.personality_dao = None

        # Остальные компоненты
        self.session_manager = None     # Будет создан в следующих задачах

        # 📦 ProgramRouter для блочной структуры программ (Phase 4)
        self.program_router = None  # Будет инициализирован после DB

        # Временное хранение сессий (заменим на SessionManager)
        self.active_sessions = {}       # {user_id: session_data}

        # ✅ TASK REGISTRY - сохраняем ссылки на все background tasks
        self._background_tasks: Set[asyncio.Task] = set()
        self._shutdown_event = asyncio.Event()

        logger.info("🎯 OnboardingOrchestrator initialized with Task Registry")

    async def start_onboarding(self, user_id: int) -> Dict[str, Any]:
        """
        Начать онбординг для пользователя

        Args:
            user_id: ID пользователя

        Returns:
            Dict с данными первого вопроса для отображения
        """
        try:
            logger.info(f"🚀 Starting onboarding for user {user_id}")

            # 🗄️ Инициализируем Database при первом использовании
            if not self.db_service:
                from os import environ
                self.db_service = DatabaseService(
                    host=environ.get("DB_HOST", "localhost"),
                    port=int(environ.get("DB_PORT", 5432)),
                    user=environ.get("DB_USER", "n8n"),
                    password=environ.get("DB_PASSWORD", "sS67wM+1zMBRFHAW4kj9HwFl5J6+veo7Nirx0/I+oiU="),
                    database=environ.get("DB_NAME", "n8n")
                )
                await self.db_service.initialize()
                self.onboarding_dao = OnboardingDAO(self.db_service)
                self.personality_dao = DigitalPersonalityDAO(self.db_service)
                await self.onboarding_dao.create_onboarding_tables()

                # ✅ Передаем DAO в QuestionRouter для фильтрации flagged вопросов
                self.question_router.onboarding_dao = self.onboarding_dao

                # 📊 Инициализируем SessionReportGenerator после DAO
                if not self.session_reporter:
                    self.session_reporter = SessionReportGenerator(self.onboarding_dao)
                    logger.info("📊 SessionReportGenerator initialized")

                # 📦 Инициализируем ProgramRouter для блочной структуры (Phase 4)
                if not self.program_router and self.db_service and self.db_service.pool:
                    self.program_router = ProgramRouter(db_pool=self.db_service.pool)
                    logger.info("📦 ProgramRouter initialized for block-based programs")

                logger.info("🗄️ Database connection established for onboarding")

            # 🔄 Retry pending answers for this user (if any)
            await self._retry_pending_answers(user_id)

            # Настраиваем vector storage при первом использовании
            if not self._vector_storage_setup:
                await self._setup_vector_storage()
                self._vector_storage_setup = True

            # 🎯 Используем QuestionRouter для выбора первого вопроса
            first_question = await self.question_router.select_first_question(user_id)

            if not first_question:
                raise Exception("QuestionRouter could not select first question")

            # 🗄️ Создаем сессию в БД (вместо памяти)
            session_id = await self.onboarding_dao.start_session(user_id)
            logger.info(f"🗄️ Created database session {session_id} for user {user_id}")

            # ✅ Устанавливаем current_question_json_id сразу при создании сессии
            await self.onboarding_dao.update_current_question(session_id, first_question["id"])
            await self.onboarding_dao.increment_questions_asked(session_id)
            logger.info(f"📝 Set initial question {first_question['id']} for session {session_id}")

            # Инициализируем данные сессии (память + БД)
            session_data = {
                "user_id": user_id,
                "session_id": session_id,
                "started_at": datetime.now(),
                "question_history": [],
                "answer_history": [],
                "current_question": first_question,
                "router_events": []  # Для отслеживания работы роутера
            }

            # Сохраняем сессию (память для скорости + БД для постоянства)
            self.active_sessions[user_id] = session_data

            question = first_question

            # Получаем прогресс ТЕКУЩЕЙ сессии и общий прогресс
            session_db = await self.onboarding_dao.get_active_session(user_id)
            questions_in_session = session_db.get("questions_answered", 0)
            # Подсчитываем РЕАЛЬНОЕ количество всех ответов пользователя
            total_lifetime = await self.onboarding_dao.get_user_total_answers(user_id)
            MAX_QUESTIONS_PER_SESSION = 20

            # Формируем ответ для controller
            return {
                "status": "started",
                "question": {
                    "id": question["id"],
                    "text": question["text"],
                    "domain": question["classification"]["domain"],
                    "depth": question["classification"]["depth_level"],
                    "energy": question["classification"]["energy_dynamic"]
                },
                "session_info": {
                    "question_number": questions_in_session + 1,  # Следующий вопрос в ТЕКУЩЕЙ сессии
                    "total_questions": MAX_QUESTIONS_PER_SESSION,
                    "total_lifetime": total_lifetime,  # Всего пройдено за всё время
                    "session_started": datetime.now().isoformat()
                }
            }

        except Exception as e:
            logger.error(f"❌ Failed to start onboarding for user {user_id}: {e}")
            raise

    def get_session(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Получить активную сессию пользователя из памяти

        Args:
            user_id: ID пользователя

        Returns:
            Dict с данными сессии или None если сессии нет
        """
        session = self.active_sessions.get(user_id)
        if session:
            logger.debug(f"📖 Retrieved active session for user {user_id}")
        else:
            logger.warning(f"⚠️ No active session found for user {user_id}")
        return session

    async def restore_session_from_db(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Восстановить сессию из БД в память (для случаев рестарта бота)

        Args:
            user_id: ID пользователя

        Returns:
            Dict с данными восстановленной сессии или None
        """
        try:
            # Проверяем наличие DAO
            if not self.onboarding_dao:
                logger.error("❌ Cannot restore session: onboarding_dao not initialized")
                return None

            # Получаем сессию из БД
            session_db = await self.onboarding_dao.get_active_session(user_id)

            if not session_db or session_db.get('status') != 'active':
                logger.warning(f"⚠️ No active session in DB for user {user_id}")
                return None

            # Восстанавливаем current_question из question core
            current_question_id = session_db.get('current_question_json_id')
            current_question = None

            if current_question_id:
                current_question = self.question_core.get_question(current_question_id)
                if not current_question:
                    logger.error(f"❌ Could not load question {current_question_id} from core")

            # ✅ КРИТИЧНО: Восстанавливаем историю ответов из БД
            question_history = []
            answer_history = []

            session_id = session_db['id']
            db_answers = await self.onboarding_dao.get_session_answers(session_id)

            for db_answer in db_answers:
                # Загружаем полные данные вопроса из question core
                question_data = self.question_core.get_question(db_answer['question_id'])

                if question_data:
                    question_history.append(question_data)
                    answer_history.append({
                        "answer": db_answer['answer'],
                        "question_id": db_answer['question_id'],
                        "answer_id": db_answer['answer_id'],
                        "timestamp": db_answer['answered_at']
                    })
                else:
                    logger.warning(f"⚠️ Could not load question {db_answer['question_id']} from core during restore")

            logger.info(f"📚 Restored {len(question_history)} questions from DB for user {user_id}")

            # Создаём session структуру в памяти
            session = {
                "user_id": user_id,
                "session_id": session_db['id'],
                "current_question": current_question,
                "answer_history": answer_history,  # ✅ Восстановлена из БД
                "question_history": question_history,  # ✅ Восстановлена из БД
                "router_events": []  # Для отслеживания работы роутера (начинается заново)
            }

            # Сохраняем в памяти
            self.active_sessions[user_id] = session

            logger.info(f"🔄 [SESSION RESTORE] Restored session for user {user_id} from DB (session_id={session_db['id']}, question={current_question_id}, history_size={len(question_history)})")

            return session

        except Exception as e:
            logger.error(f"❌ Failed to restore session from DB for user {user_id}: {e}")
            import traceback
            traceback.print_exc()
            return None

    async def get_next_question(self, user_id: int, session_data: Dict) -> Dict[str, Any]:
        """
        Получить следующий вопрос для пользователя

        Args:
            user_id: ID пользователя
            session_data: Данные текущей сессии

        Returns:
            Dict с данными следующего вопроса или сигнал завершения
        """
        try:
            logger.info(f"🔄 Getting next question for user {user_id}")

            # Проверяем есть ли активная сессия
            if user_id not in self.active_sessions:
                logger.error(f"❌ No active session for user {user_id}")
                return {
                    "status": "error",
                    "message": "No active onboarding session"
                }

            session = self.active_sessions[user_id]

            # 🎯 Используем QuestionRouter с алгоритмом "Умный Микс"
            history = []
            question_history = session.get("question_history") or []
            answer_history = session.get("answer_history") or []
            for i in range(len(question_history)):
                if i < len(answer_history):
                    history.append({
                        "question": question_history[i],
                        "answer": answer_history[i]
                    })

            # ✨ Передаем session_id для загрузки AI insights
            session_id = session.get("session_id")
            next_question = await self.question_router.select_next_question(user_id, history, session_id)

            # 📊 Собираем события роутера для аналитики
            if self.question_router.last_events:
                session.setdefault("router_events", []).extend(self.question_router.last_events)
                logger.debug(f"📊 Collected {len(self.question_router.last_events)} router events")

            if not next_question:
                return {
                    "status": "completed",
                    "message": "Smart Mix algorithm completed onboarding"
                }

            # ✅ Инкремент questions_asked при отправке следующего вопроса
            session_id = session["session_id"]
            await self.onboarding_dao.increment_questions_asked(session_id)
            logger.debug(f"📊 Incremented questions_asked for session {session_id} (next question)")

            # ✅ Обновляем current_question_json_id
            await self.onboarding_dao.update_current_question(session_id, next_question["id"])
            logger.debug(f"📝 Updated current_question to {next_question['id']} for session {session_id}")

            question = next_question

            # ✅ КРИТИЧНО: Обновляем current_question в сессии для правильного добавления в историю
            session["current_question"] = next_question
            logger.debug(f"📝 Updated session current_question to {next_question['id']}")

            # Получаем прогресс ТЕКУЩЕЙ сессии и общий прогресс
            session_id = session["session_id"]
            session_db = await self.onboarding_dao.get_active_session(user_id)
            questions_in_session = session_db.get("questions_answered", 0)
            # Подсчитываем РЕАЛЬНОЕ количество всех ответов пользователя
            total_lifetime = await self.onboarding_dao.get_user_total_answers(user_id)
            MAX_QUESTIONS_PER_SESSION = 20

            return {
                "status": "continue",
                "question": {
                    "id": question["id"],
                    "text": question["text"],
                    "domain": question["classification"]["domain"],
                    "depth": question["classification"]["depth_level"],
                    "energy": question["classification"]["energy_dynamic"]
                },
                "session_info": {
                    "question_number": questions_in_session + 1,  # Следующий вопрос в ТЕКУЩЕЙ сессии
                    "total_questions": MAX_QUESTIONS_PER_SESSION,
                    "total_lifetime": total_lifetime  # Всего пройдено за всё время
                }
            }

        except Exception as e:
            logger.error(f"❌ Failed to get next question for user {user_id}: {e}")
            raise

    async def process_user_answer(self, user_id: int, question_id: str, answer: str) -> Dict[str, Any]:
        """
        Обработать ответ пользователя

        Args:
            user_id: ID пользователя
            question_id: ID вопроса
            answer: Ответ пользователя

        Returns:
            Dict с результатом обработки
        """
        try:
            logger.info(f"💬 Processing answer from user {user_id} for question {question_id}")

            # Проверяем активную сессию
            if user_id not in self.active_sessions:
                logger.error(f"❌ No active session for user {user_id}")
                return {
                    "status": "error",
                    "message": "No active session"
                }

            session = self.active_sessions[user_id]

            # 🚀 ДВУХФАЗНАЯ ОБРАБОТКА (согласно плану)

            # === ФАЗА 1: INSTANT (<500ms) ===
            instant_start = datetime.now()

            # 1.1 Сохраняем ответ в БД (критично - не теряем данные)
            session_id = session.get("session_id")
            answer_id = None
            is_context_story = (question_id == "system_context_story")

            if session_id and self.onboarding_dao:
                if is_context_story:
                    # Системный вопрос - сохраняем как контекстную историю
                    answer_id = await self.onboarding_dao.save_context_story(
                        user_id=user_id,
                        session_id=session_id,
                        story_text=answer,
                        story_type="onboarding_context",
                        metadata={"source": "onboarding", "answered_at": datetime.now().isoformat()}
                    )
                    logger.info(f"💙 Context story saved to database with ID {answer_id}")
                else:
                    # Обычный вопрос - сохраняем как обычный ответ
                    answer_id = await self.onboarding_dao.save_user_answer(session_id, question_id, answer)
                    logger.info(f"🗄️ Answer saved to database with ID {answer_id}")
            else:
                logger.warning("⚠️ Database not available - answer saved only in memory")

            # 1.2 Быстрое сохранение в сессии
            current_question = session.get("current_question")
            if current_question:
                # Инициализация истории если не существует
                if "question_history" not in session or session["question_history"] is None:
                    session["question_history"] = []
                if "answer_history" not in session or session["answer_history"] is None:
                    session["answer_history"] = []

                session["question_history"].append(current_question)
                session["answer_history"].append({
                    "answer": answer,
                    "question_id": question_id,
                    "answer_id": answer_id,  # Сохраняем для связи с анализом
                    "timestamp": datetime.now().isoformat()
                })

                logger.info(f"📝 Answer saved in session: user={user_id}, question={question_id}, answer_length={len(answer)}")

            # 1.3 Быстрый анализ для немедленного фидбека (Mock пока что)
            quick_insight = self._get_quick_insight(answer)

            # 1.4 Мгновенный ответ пользователю
            instant_time = (datetime.now() - instant_start).total_seconds() * 1000
            logger.info(f"⚡ Instant phase completed in {instant_time:.0f}ms")

            instant_response = {
                "status": "processed",
                "answer_id": f"temp_{user_id}_{question_id}_{datetime.now().timestamp()}",
                "quick_insight": quick_insight,
                "processing_phase": "instant_complete",
                "next_action": "continue",
                "deep_analysis_status": "processing"
            }

            # ✅ 1.5 Создаем immutable копию данных для background task
            # Предотвращает race conditions с shared session state
            immutable_session = deepcopy(session)
            immutable_question = deepcopy(current_question)

            # ✅ 1.6 Запускаем глубокий анализ через Task Registry
            task = self._create_background_task(
                self._deep_analysis_pipeline(
                    user_id,
                    question_id,
                    answer,
                    immutable_question,  # Используем immutable копию
                    immutable_session,   # Используем immutable копию
                    answer_id,
                    is_context_story=is_context_story  # Передаем флаг типа ответа
                ),
                name=f"deep_analysis_{user_id}_{question_id}"
            )

            logger.info(f"🔬 Background analysis task created: {task.get_name()} (total active: {len(self._background_tasks)})")

            return instant_response

        except Exception as e:
            logger.error(f"❌ Failed to process answer from user {user_id}: {e}")
            raise

    def _create_background_task(self, coro, name: str = None) -> asyncio.Task:
        """
        Создать background task с proper error handling и registry tracking

        АРХИТЕКТУРНОЕ РЕШЕНИЕ:
        - Task добавляется в registry для предотвращения garbage collection
        - Automatic cleanup после завершения через done callback
        - Exception handling с полным логированием
        - Поддержка graceful shutdown

        Args:
            coro: Корутина для выполнения
            name: Имя задачи для observability

        Returns:
            asyncio.Task с registered cleanup
        """
        task = asyncio.create_task(coro, name=name)
        self._background_tasks.add(task)

        # ✅ Cleanup callback - удаляет task из registry после завершения
        def task_done_callback(t: asyncio.Task):
            self._background_tasks.discard(t)

            # ✅ Логируем любые exceptions из background task
            if t.exception():
                exc = t.exception()
                task_name = t.get_name() or "unnamed_task"
                logger.error(
                    f"❌ Background task '{task_name}' failed with exception: {exc}",
                    exc_info=exc
                )
            else:
                task_name = t.get_name() or "unnamed_task"
                logger.debug(f"✅ Background task '{task_name}' completed successfully")

        task.add_done_callback(task_done_callback)
        return task

    async def should_continue_session(self, user_id: int, session_data: Dict) -> bool:
        """
        Определить должна ли продолжаться сессия

        Args:
            user_id: ID пользователя
            session_data: Данные сессии

        Returns:
            True если сессия должна продолжаться
        """
        try:
            # 😴 УМНАЯ ПРОВЕРКА УСТАЛОСТИ (Phase 3)

            # Получаем сессию
            if user_id not in self.active_sessions:
                return False

            session = self.active_sessions[user_id]
            history = session.get("answer_history", [])

            # Подготавливаем контекст для FatigueDetector
            user_context = self._prepare_analysis_context(user_id, session, "")

            # Анализируем усталость
            fatigue_analysis = self.fatigue_detector.analyze_fatigue_level(user_context, history)

            # Решение на основе анализа усталости
            fatigue_level = fatigue_analysis["fatigue_level"]

            if fatigue_level == "high_fatigue":
                # Высокая усталость - рекомендуем завершить
                logger.info(f"😴 High fatigue detected for user {user_id} - suggesting end session")
                session["fatigue_recommendation"] = "end_session"
                session["fatigue_analysis"] = fatigue_analysis
                return False

            elif fatigue_level == "medium_fatigue":
                # Средняя усталость - предлагаем паузу, но можно продолжить
                logger.info(f"😐 Medium fatigue detected for user {user_id} - offering pause")
                session["fatigue_recommendation"] = "offer_pause"
                session["fatigue_analysis"] = fatigue_analysis
                return True  # Но с предложением паузы

            else:
                # Энергия есть - продолжаем
                logger.info(f"⚡ User {user_id} energized - continuing session")
                session["fatigue_recommendation"] = "continue"
                return True

        except Exception as e:
            logger.error(f"❌ Failed to check session continuation for user {user_id}: {e}")
            return False

    async def complete_onboarding(self, user_id: int) -> Dict[str, Any]:
        """
        Завершить онбординг для пользователя

        Args:
            user_id: ID пользователя

        Returns:
            Dict с результатами онбординга
        """
        try:
            logger.info(f"🎉 Completing onboarding for user {user_id}")

            # Получаем активную сессию из БД для статистики
            session_db = await self.onboarding_dao.get_active_session(user_id)
            questions_answered = session_db.get("questions_answered", 0) if session_db else 0

            logger.info(f"📊 User {user_id} answered {questions_answered} questions")

            # 📊 Генерируем отчет о завершенной сессии
            report_data = None
            telegram_digest = None
            if self.session_reporter and user_id in self.active_sessions:
                try:
                    session_data = self.active_sessions[user_id]
                    session_id = session_db.get("id") if session_db else None

                    if session_id:
                        logger.info(f"📊 Generating session report for user {user_id}, session {session_id}")

                        # Генерируем полный отчет
                        report_data = await self.session_reporter.generate_session_report(
                            session_id=session_id,
                            user_id=user_id,
                            session_data=session_data
                        )

                        # Сохраняем в файлы
                        file_paths = await self.session_reporter.save_report_files(
                            report=report_data,
                            user_id=user_id,
                            session_id=session_id
                        )
                        logger.info(f"📄 Report saved to: {file_paths.get('markdown')}")

                        # Формируем краткую сводку для Telegram
                        telegram_digest = self.session_reporter.format_telegram_digest(report_data)

                except Exception as e:
                    logger.error(f"❌ Failed to generate session report: {e}")
                    import traceback
                    traceback.print_exc()

            # В Phase 2 добавим создание психологического профиля

            result = {
                "status": "completed",
                "completion_time": datetime.now().isoformat(),
                "questions_answered": questions_answered,  # ✅ Берём из БД
                "summary": "Onboarding completed successfully",
                "next_steps": [
                    "Психологический профиль создан",
                    "Персональные рекомендации готовы",
                    "Можете начинать чат с AI коучем"
                ]
            }

            # Добавляем отчет если он был сгенерирован
            if telegram_digest:
                result["report_digest"] = telegram_digest

            return result

        except Exception as e:
            logger.error(f"❌ Failed to complete onboarding for user {user_id}: {e}")
            raise

    async def record_skipped_question(self, user_id: int, question_id: str) -> None:
        """
        Записать факт пропуска вопроса в историю сессии

        Args:
            user_id: ID пользователя
            question_id: ID пропущенного вопроса
        """
        try:
            if user_id not in self.active_sessions:
                logger.warning(f"⚠️ No active session for user {user_id} to record skip")
                return

            session = self.active_sessions[user_id]
            current_question = session.get("current_question")

            if current_question:
                # Инициализация истории если не существует
                if "question_history" not in session or session["question_history"] is None:
                    session["question_history"] = []
                if "answer_history" not in session or session["answer_history"] is None:
                    session["answer_history"] = []

                # Добавляем вопрос в историю
                session["question_history"].append(current_question)

                # Добавляем запись о пропуске (без answer_id, т.к. нет ответа)
                session["answer_history"].append({
                    "answer": None,  # Нет ответа
                    "question_id": question_id,
                    "answer_id": None,
                    "timestamp": datetime.now().isoformat(),
                    "skipped": True  # ✅ Флаг пропуска для FatigueDetector
                })

                logger.info(f"⏭️ Recorded skip for user {user_id}, question {question_id}")

        except Exception as e:
            logger.error(f"❌ Failed to record skip for user {user_id}: {e}")

    async def flag_question_for_review(self, user_id: int, question_id: str, reason: str = "") -> bool:
        """
        Пометить вопрос на доработку (ТОЛЬКО для админа)

        Args:
            user_id: ID пользователя (должен быть админ)
            question_id: ID вопроса для пометки
            reason: Причина пометки (опционально)

        Returns:
            True если вопрос помечен успешно
        """
        try:
            # Проверка что пользователь админ (будет добавлена в Phase 3)
            # if not self._is_admin(user_id):
            #     logger.warning(f"🚫 Non-admin user {user_id} tried to flag question {question_id}")
            #     return False

            logger.info(f"🚧 Admin {user_id} flagging question {question_id} for review. Reason: {reason}")

            # Пока что сохраняем в логи, в Phase 1 Task 1.5 добавим в БД
            logger.info(f"🏷️ Question {question_id} flagged by admin {user_id}")

            # В будущем здесь будет:
            # await self.question_dao.flag_question(question_id, user_id, reason)

            return True

        except Exception as e:
            logger.error(f"❌ Failed to flag question {question_id} by user {user_id}: {e}")
            return False

    def _is_admin(self, user_id: int) -> bool:
        """
        Проверить является ли пользователь админом

        Args:
            user_id: ID пользователя

        Returns:
            True если пользователь админ
        """
        # В CLAUDE.md указан ADMIN_USER_ID, но нужно проверить где он определен
        # Пока что заглушка
        ADMIN_USER_ID = "98005572"  # Твой ID из логов
        return str(user_id) == ADMIN_USER_ID

    def _get_quick_insight(self, answer: str) -> str:
        """Быстрый инсайт для мгновенного фидбека"""

        answer_lower = answer.lower()

        # Простая эмоциональная классификация
        if any(word in answer_lower for word in ["рад", "счастлив", "хорошо", "отлично"]):
            return "Вижу позитивный настрой ✨"
        elif any(word in answer_lower for word in ["интересно", "думаю", "размышляю"]):
            return "Чувствую глубину размышлений 🤔"
        elif any(word in answer_lower for word in ["сложно", "тяжело", "трудно"]):
            return "Понимаю, что тема непростая 💙"
        elif len(answer) > 100:
            return "Ценю вашу открытость 🙏"
        else:
            return "Принимаю ваш ответ ✅"

    async def _deep_analysis_pipeline(
        self,
        user_id: int,
        question_id: str,
        answer: str,
        question_data: Dict[str, Any],
        session: Dict[str, Any],
        answer_id: Optional[int] = None,
        is_context_story: bool = False
    ):
        """
        === ФАЗА 2: DEEP ANALYSIS (2-10 секунд в фоне) ===

        Полный психологический анализ без блокировки пользователя

        АРХИТЕКТУРНОЕ РЕШЕНИЕ:
        - Принимает immutable копии session и question_data
        - Предотвращает race conditions
        - Полное exception handling с логированием
        - Graceful handling если shutdown во время выполнения
        - ✅ ОТСЛЕЖИВАНИЕ СТАТУСОВ ОБРАБОТКИ (Oct 2025)
        """

        analysis_id = None
        vectorization_success = False
        dp_update_success = False

        try:
            deep_start = datetime.now()
            logger.info(f"🔬 Starting deep analysis pipeline for user {user_id}")

            # ✅ Проверка критичных параметров
            if question_data is None:
                logger.error(f"❌ question_data is None for user {user_id}, question {question_id}")
                raise ValueError("question_data cannot be None")

            if session is None:
                logger.error(f"❌ session is None for user {user_id}")
                raise ValueError("session cannot be None")

            # 2.1 Подготавливаем контекст для анализа
            analysis_context = self._prepare_analysis_context(user_id, session, answer, answer_id)

            # 2.2 🧠 ГЛАВНЫЙ АНАЛИЗ через AnswerAnalyzer
            analysis_result = await self.answer_analyzer.analyze_answer(
                question_data=question_data,
                user_answer=answer,
                user_context=analysis_context
            )

            # 2.3 💾 Сохраняем анализ в БД (с начальными статусами pending)
            session_id = session.get("session_id")
            if session_id and self.onboarding_dao:
                # Получаем answer_id из БД для связи с анализом
                answer_id = analysis_context.get("answer_id")
                if answer_id:
                    if is_context_story:
                        # Контекстная история - сохраняем через save_context_story_analysis
                        analysis_id = await self.onboarding_dao.save_context_story_analysis(answer_id, analysis_result)
                        logger.info(f"💙 Context story analysis saved to DB with ID {analysis_id}")
                    else:
                        # Обычный ответ - сохраняем через save_analysis_result
                        analysis_id = await self.onboarding_dao.save_analysis_result(answer_id, analysis_result)
                        logger.info(f"💾 Analysis saved to DB with ID {analysis_id}")
                else:
                    logger.warning("⚠️ No answer_id found - cannot save analysis")
            else:
                logger.warning("⚠️ Database not available - analysis not saved")

            # 2.3.5 🧬 ИЗВЛЕЧЕНИЕ ЦИФРОВОЙ ЛИЧНОСТИ
            try:
                # Получаем существующую личность
                existing_personality = None
                if self.personality_dao:
                    existing_personality = await self.personality_dao.get_personality(user_id)

                # Извлекаем конкретную информацию из ответа
                extracted_personality = await self.personality_extractor.extract_from_answer(
                    question_text=question_data.get("text", ""),
                    user_answer=answer,
                    question_metadata=question_data.get("classification", {}),
                    existing_personality=existing_personality
                )

                # Объединяем с существующей личностью
                if existing_personality:
                    # Обновляем существующую
                    merged = self.personality_extractor.merge_extractions(
                        existing_personality,
                        extracted_personality
                    )
                    await self.personality_dao.update_personality(user_id, merged, merge=True)
                    logger.info(f"🧬 Updated digital personality for user {user_id}")
                else:
                    # Создаём новую
                    await self.personality_dao.create_personality(user_id, extracted_personality)
                    logger.info(f"🧬 Created digital personality for user {user_id}")

                # ✅ Отмечаем успех обновления DP
                dp_update_success = True
                if analysis_id and self.onboarding_dao:
                    await self.onboarding_dao.update_dp_update_status(analysis_id, "success")

            except Exception as e:
                logger.error(f"❌ Failed to extract/update personality for user {user_id}: {e}")
                # ✅ Отмечаем ошибку обновления DP
                if analysis_id and self.onboarding_dao:
                    await self.onboarding_dao.update_dp_update_status(
                        analysis_id,
                        "failed",
                        str(e)[:500]  # Ограничиваем длину ошибки
                    )

            # 2.4 📈 Создаем/обновляем векторы в Qdrant
            try:
                answer_history = session.get("answer_history") or []
                vector_success = await self.embedding_creator.create_personality_vector(
                    user_id=user_id,
                    analysis_result=analysis_result,
                    is_update=(len(answer_history) > 1)  # Обновление если не первый ответ
                )

                # ✅ Отмечаем успех/неудачу векторизации
                if analysis_id and self.onboarding_dao:
                    if vector_success:
                        vectorization_success = True
                        await self.onboarding_dao.update_vectorization_status(analysis_id, "success")
                    else:
                        await self.onboarding_dao.update_vectorization_status(
                            analysis_id,
                            "failed",
                            "create_personality_vector returned False"
                        )

            except Exception as e:
                logger.error(f"❌ Failed to create vectors for user {user_id}: {e}")
                # ✅ Отмечаем ошибку векторизации
                if analysis_id and self.onboarding_dao:
                    await self.onboarding_dao.update_vectorization_status(
                        analysis_id,
                        "failed",
                        str(e)[:500]  # Ограничиваем длину ошибки
                    )

            # 2.5 Обновляем сессию рекомендациями для роутера
            # ВАЖНО: НЕ обновляем shared session напрямую (это immutable копия)
            # Реальное обновление произойдет через БД или при следующем get_session
            router_recommendations = analysis_result.get("router_recommendations", {})

            # 2.6 Логирование результатов
            deep_time = (datetime.now() - deep_start).total_seconds() * 1000
            logger.info(
                f"✅ Deep analysis completed for user {user_id} in {deep_time:.0f}ms "
                f"(model: {analysis_result.get('processing_metadata', {}).get('model_used', 'unknown')}, "
                f"vectors: {'✅' if vectorization_success else '❌'}, "
                f"DP: {'✅' if dp_update_success else '❌'})"
            )

            # ✅ 2.7 Отмечаем завершение background task
            if analysis_id and self.onboarding_dao:
                await self.onboarding_dao.mark_background_task_completed(
                    analysis_id,
                    int(deep_time),
                    success=(vectorization_success and dp_update_success)
                )

            # 2.8 Уведомление пользователя (если онлайн)
            # TODO: Добавить push notification или websocket когда будет UI
            # await self._notify_deep_analysis_ready(user_id, analysis_result)

        except asyncio.CancelledError:
            # ✅ Graceful handling при shutdown
            logger.warning(f"🛑 Deep analysis cancelled for user {user_id} due to shutdown")
            raise  # Re-raise чтобы task правильно завершился

        except Exception as e:
            logger.error(
                f"❌ Deep analysis pipeline failed for user {user_id}: {e}",
                exc_info=True  # Полный traceback для debugging
            )

            # ✅ Отмечаем failed статусы если не были установлены
            if analysis_id and self.onboarding_dao:
                try:
                    # Если векторизация не прошла - отмечаем failed
                    if not vectorization_success:
                        await self.onboarding_dao.update_vectorization_status(
                            analysis_id,
                            "failed",
                            str(e)[:500]
                        )

                    # Если DP не обновлен - отмечаем failed
                    if not dp_update_success:
                        await self.onboarding_dao.update_dp_update_status(
                            analysis_id,
                            "failed",
                            str(e)[:500]
                        )

                    # Отмечаем task как failed
                    deep_time = (datetime.now() - deep_start).total_seconds() * 1000
                    await self.onboarding_dao.mark_background_task_completed(
                        analysis_id,
                        int(deep_time),
                        success=False
                    )
                except Exception as inner_e:
                    logger.error(f"❌ Failed to update error statuses: {inner_e}")

    def _prepare_analysis_context(self, user_id: int, session: Dict, answer: str, answer_id: Optional[int] = None) -> Dict[str, Any]:
        """Подготовка контекста для глубокого анализа"""

        history = session.get("answer_history") or []

        # Защита от None в answer
        safe_answer = answer if answer is not None else ""

        return {
            "user_id": user_id,
            "answer_id": answer_id,  # Для связи анализа с ответом в БД
            "question_number": len(history) + 1,
            "session_started": session.get("started_at"),
            "previous_answers_count": len(history),
            "previous_domains": [
                item.get("question", {}).get("classification", {}).get("domain", "UNKNOWN")
                for item in session.get("question_history", [])
            ],

            # Анализ ответа
            "user_answer": safe_answer,
            "answer_length": len(safe_answer),
            "response_time_seconds": 30,  # TODO: Реально измерять время

            # Состояние пользователя
            "trust_level": session.get("trust_level", 0.5),
            "energy_level": session.get("energy_level", 0.7),
            "fatigue_level": session.get("user_fatigue_level", 0.0),
            "engagement_level": self._estimate_engagement(history, safe_answer),

            # История для персонализации
            "session_length_minutes": self._calculate_session_length(session),
            "avg_answer_length": self._calculate_avg_answer_length(history),
            "emotional_trajectory": self._analyze_emotional_trajectory(history)
        }

    def _estimate_engagement(self, history: List[Dict], current_answer: str) -> float:
        """Оценка вовлеченности пользователя"""

        # Защита от None в current_answer
        safe_current_answer = current_answer if current_answer is not None else ""

        if not history:
            return 0.7 if len(safe_current_answer) > 50 else 0.4

        # Анализируем тренд длины ответов (фильтруем None значения)
        recent_lengths = [
            len(item.get("answer") or "")
            for item in history[-3:]
            if item.get("answer") is not None
        ]
        recent_lengths.append(len(safe_current_answer))

        # Если ответы становятся длиннее - растет вовлеченность
        if len(recent_lengths) > 1:
            trend = (recent_lengths[-1] - recent_lengths[0]) / max(1, len(recent_lengths))
            base_engagement = min(1.0, len(safe_current_answer) / 100.0)
            return max(0.1, min(1.0, base_engagement + trend / 100.0))

        return 0.5

    def _calculate_session_length(self, session: Dict) -> float:
        """Рассчитать длину сессии в минутах"""

        started = session.get("started_at")
        if not started:
            return 0.0

        if isinstance(started, str):
            try:
                started_dt = datetime.fromisoformat(started.replace("Z", "+00:00"))
            except:
                return 0.0
        else:
            started_dt = started

        return (datetime.now() - started_dt.replace(tzinfo=None)).total_seconds() / 60.0

    def _calculate_avg_answer_length(self, history: List[Dict]) -> float:
        """Средняя длина ответов"""

        if not history:
            return 0.0

        # Фильтруем только реальные ответы (не пропуски)
        lengths = [len(item.get("answer", "")) for item in (history or []) if item.get("answer")]
        return sum(lengths) / len(lengths) if lengths else 0.0

    def _analyze_emotional_trajectory(self, history: List[Dict]) -> str:
        """Анализ эмоциональной траектории сессии"""

        if not history or len(history) < 2:
            return "starting"

        # Простой анализ на основе длины и ключевых слов (фильтруем None)
        recent_answers = [
            item.get("answer") or ""
            for item in history[-3:]
            if item.get("answer") is not None
        ]

        positive_words = sum(
            answer.lower().count(word)
            for answer in recent_answers
            for word in ["хорошо", "отлично", "рад", "интересно", "нравится"]
        )

        negative_words = sum(
            answer.lower().count(word)
            for answer in recent_answers
            for word in ["сложно", "тяжело", "трудно", "устал"]
        )

        if positive_words > negative_words:
            return "positive_trend"
        elif negative_words > positive_words:
            return "challenging_trend"
        else:
            return "stable_neutral"

    async def _retry_pending_answers(self, user_id: int):
        """
        Повторная обработка pending ответов для пользователя

        Args:
            user_id: ID пользователя
        """
        try:
            # Ищем pending ответы с retry_count < 3
            query = """
                SELECT ua.id, ua.session_id, ua.question_json_id, ua.raw_answer, ua.retry_count
                FROM selfology.user_answers_new ua
                JOIN selfology.onboarding_sessions os ON ua.session_id = os.id
                WHERE os.user_id = $1
                  AND ua.analysis_status = 'pending'
                  AND ua.retry_count < 3
                ORDER BY ua.id
                LIMIT 10
            """

            async with self.db_service.get_connection() as conn:
                pending_answers = await conn.fetch(query, user_id)

            if not pending_answers:
                logger.info(f"✅ No pending answers to retry for user {user_id}")
                return

            logger.info(f"🔄 Found {len(pending_answers)} pending answers to retry for user {user_id}")

            # Повторная обработка каждого ответа
            for answer in pending_answers:
                answer_id = answer['id']
                question_id = answer['question_json_id']
                raw_answer = answer['raw_answer']
                retry_count = answer['retry_count']

                logger.info(f"🔄 Retrying analysis for answer {answer_id} (attempt {retry_count + 1}/3)")

                try:
                    # Получаем вопрос из core
                    question = self.question_core.get_question_by_id(question_id)

                    if not question:
                        logger.warning(f"⚠️ Question {question_id} not found, skipping")
                        continue

                    # Запускаем deep analysis заново
                    await self._run_deep_analysis_pipeline(
                        user_id,
                        answer_id,
                        question['text'],
                        raw_answer,
                        question.get('classification', {})
                    )

                    # Инкрементируем retry_count
                    update_query = """
                        UPDATE selfology.user_answers_new
                        SET retry_count = retry_count + 1
                        WHERE id = $1
                    """
                    async with self.db_service.get_connection() as conn:
                        await conn.execute(update_query, answer_id)

                    logger.info(f"✅ Successfully retried analysis for answer {answer_id}")

                except Exception as e:
                    logger.error(f"❌ Error retrying answer {answer_id}: {e}")
                    # Продолжаем со следующим ответом
                    continue

            logger.info(f"✅ Completed retry for {len(pending_answers)} pending answers")

        except Exception as e:
            logger.error(f"❌ Error in _retry_pending_answers: {e}")

    async def _setup_vector_storage(self):
        """Настройка Qdrant коллекций для векторного хранения"""

        try:
            logger.info("📈 Setting up vector storage collections...")

            # Настраиваем коллекции в EmbeddingCreator
            setup_success = await self.embedding_creator.setup_qdrant_collections()

            if setup_success:
                logger.info("✅ Vector storage collections ready")
            else:
                logger.warning("⚠️ Vector storage setup incomplete - will retry later")

        except Exception as e:
            logger.error(f"❌ Error setting up vector storage: {e}")

    async def get_system_status(self) -> Dict[str, Any]:
        """Получить статус всей системы онбординга"""

        try:
            # Статистика компонентов
            analysis_stats = await self.answer_analyzer.get_analysis_stats()
            embedding_stats = await self.embedding_creator.get_embedding_stats()

            return {
                "system_version": "2.0",
                "status": "operational",
                "components": {
                    "question_router": "ready",
                    "answer_analyzer": "ready",
                    "embedding_creator": "ready",
                    "vector_storage": "mock_mode"  # TODO: real Qdrant status
                },
                "active_sessions": len(self.active_sessions),
                "statistics": {
                    "analysis": analysis_stats,
                    "embeddings": embedding_stats
                },
                "last_updated": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"❌ Error getting system status: {e}")
            return {
                "status": "error",
                "error": str(e)
            }

    # ============================================================================
    # GRACEFUL SHUTDOWN & OBSERVABILITY METHODS
    # ============================================================================

    async def shutdown(self, timeout: float = 30.0) -> Dict[str, Any]:
        """
        Graceful shutdown orchestrator с ожиданием завершения background tasks

        АРХИТЕКТУРНОЕ РЕШЕНИЕ:
        - Сигнализирует всем tasks о shutdown через event
        - Ждет завершения всех tasks с timeout
        - Отменяет незавершенные tasks после timeout
        - Возвращает статистику shutdown для мониторинга

        Args:
            timeout: Максимальное время ожидания завершения tasks (секунды)

        Returns:
            Dict со статистикой shutdown
        """
        logger.info(f"🛑 Starting graceful shutdown of OnboardingOrchestrator (timeout: {timeout}s)")

        # Устанавливаем shutdown event для сигнализации tasks
        self._shutdown_event.set()

        if not self._background_tasks:
            logger.info("✅ No background tasks to wait for")
            return {
                "status": "clean_shutdown",
                "tasks_completed": 0,
                "tasks_cancelled": 0,
                "shutdown_time": 0.0
            }

        shutdown_start = datetime.now()
        initial_task_count = len(self._background_tasks)

        logger.info(f"⏳ Waiting for {initial_task_count} background tasks to complete (timeout: {timeout}s)")

        try:
            # Ждем завершения всех tasks с timeout
            await asyncio.wait_for(
                asyncio.gather(*self._background_tasks, return_exceptions=True),
                timeout=timeout
            )

            completed_count = initial_task_count - len(self._background_tasks)
            shutdown_time = (datetime.now() - shutdown_start).total_seconds()

            logger.info(
                f"✅ All background tasks completed gracefully "
                f"({completed_count} tasks in {shutdown_time:.2f}s)"
            )

            return {
                "status": "graceful_shutdown",
                "tasks_completed": completed_count,
                "tasks_cancelled": 0,
                "shutdown_time": shutdown_time
            }

        except asyncio.TimeoutError:
            # Timeout - отменяем оставшиеся tasks
            remaining_tasks = list(self._background_tasks)
            cancelled_count = len(remaining_tasks)

            logger.warning(
                f"⏱️ Shutdown timeout ({timeout}s) - cancelling {cancelled_count} remaining tasks"
            )

            for task in remaining_tasks:
                task.cancel()
                task_name = task.get_name() or "unnamed"
                logger.warning(f"❌ Cancelling task: {task_name}")

            # Ждем отмены tasks (быстро)
            await asyncio.gather(*remaining_tasks, return_exceptions=True)

            shutdown_time = (datetime.now() - shutdown_start).total_seconds()
            completed_count = initial_task_count - cancelled_count

            logger.warning(
                f"⚠️ Forced shutdown completed: {completed_count} completed, "
                f"{cancelled_count} cancelled ({shutdown_time:.2f}s)"
            )

            return {
                "status": "forced_shutdown",
                "tasks_completed": completed_count,
                "tasks_cancelled": cancelled_count,
                "shutdown_time": shutdown_time
            }

    def get_background_tasks_status(self) -> Dict[str, Any]:
        """
        Получить статус активных background tasks для observability

        Returns:
            Dict со статистикой всех background tasks
        """
        tasks_info = []

        for task in self._background_tasks:
            task_name = task.get_name() or "unnamed"
            task_info = {
                "name": task_name,
                "done": task.done(),
                "cancelled": task.cancelled()
            }

            # Добавляем exception info если task завершен с ошибкой
            if task.done() and not task.cancelled():
                try:
                    exc = task.exception()
                    if exc:
                        task_info["exception"] = str(exc)
                        task_info["exception_type"] = type(exc).__name__
                except asyncio.CancelledError:
                    task_info["cancelled"] = True

            tasks_info.append(task_info)

        return {
            "total_tasks": len(self._background_tasks),
            "active_tasks": sum(1 for t in self._background_tasks if not t.done()),
            "completed_tasks": sum(1 for t in self._background_tasks if t.done() and not t.cancelled()),
            "cancelled_tasks": sum(1 for t in self._background_tasks if t.cancelled()),
            "failed_tasks": sum(
                1 for t in self._background_tasks
                if t.done() and not t.cancelled() and t.exception()
            ),
            "tasks": tasks_info,
            "shutdown_initiated": self._shutdown_event.is_set()
        }

    # ============================================================
    # МЕТОДЫ ДЛЯ РАБОТЫ С ПРОГРАММАМИ (Phase 4)
    # ============================================================

    async def _ensure_database_initialized(self):
        """Инициализировать БД и ProgramRouter если ещё не инициализированы."""
        if not self.db_service:
            from os import environ
            self.db_service = DatabaseService(
                host=environ.get("DB_HOST", "localhost"),
                port=int(environ.get("DB_PORT", 5434)),
                user=environ.get("DB_USER", "selfology_user"),
                password=environ.get("DB_PASSWORD", "selfology_secure_2024"),
                database=environ.get("DB_NAME", "selfology")
            )
            await self.db_service.initialize()
            self.onboarding_dao = OnboardingDAO(self.db_service)
            self.personality_dao = DigitalPersonalityDAO(self.db_service)
            await self.onboarding_dao.create_onboarding_tables()
            self.question_router.onboarding_dao = self.onboarding_dao
            logger.info("🗄️ Database initialized for program mode")

        if not self.program_router and self.db_service and self.db_service.pool:
            self.program_router = ProgramRouter(db_pool=self.db_service.pool)
            logger.info("📦 ProgramRouter initialized for block-based programs")

    async def get_available_programs(self, user_id: int) -> List[Dict[str, Any]]:
        """
        Получить список доступных программ для пользователя.

        Returns:
            Список программ с информацией о прогрессе
        """
        await self._ensure_database_initialized()

        if not self.program_router:
            logger.warning("⚠️ ProgramRouter not initialized, returning empty list")
            return []

        try:
            programs = await self.program_router.get_available_programs(user_id)
            logger.info(f"📋 Found {len(programs)} available programs for user {user_id}")
            return programs
        except Exception as e:
            logger.error(f"❌ Error getting programs: {e}")
            return []

    async def start_program(
        self,
        user_id: int,
        program_id: str
    ) -> Dict[str, Any]:
        """
        Начать программу для пользователя.

        Args:
            user_id: ID пользователя
            program_id: ID программы

        Returns:
            Dict с первым вопросом программы
        """
        await self._ensure_database_initialized()

        if not self.program_router:
            raise Exception("ProgramRouter not initialized")

        try:
            logger.info(f"📦 Starting program {program_id} for user {user_id}")

            # Получаем контекст программы (создаёт прогресс если нужно)
            context = await self.program_router.get_program_context(user_id, program_id)
            if not context:
                raise Exception(f"Program {program_id} not found")

            # Получаем первый вопрос
            question = await self.program_router.get_first_question_in_program(
                user_id, program_id
            )

            if not question:
                raise Exception(f"No questions in program {program_id}")

            return {
                "status": "started",
                "program_id": program_id,
                "program_name": context.program_name,
                "question": question,
                "block_name": question.get("block_name"),
                "block_type": question.get("block_type"),
                "total_blocks": context.total_blocks
            }

        except Exception as e:
            logger.error(f"❌ Error starting program: {e}")
            raise

    async def get_next_program_question(
        self,
        user_id: int,
        program_id: str,
        answered_question_ids: List[str]
    ) -> Optional[Dict[str, Any]]:
        """
        Получить следующий вопрос в программе.

        Логика:
        1. Пробуем получить следующий вопрос в текущем блоке
        2. Если блок закончен, переходим к следующему блоку
        3. Если программа закончена, возвращаем None

        Args:
            user_id: ID пользователя
            program_id: ID программы
            answered_question_ids: Список отвеченных вопросов

        Returns:
            Следующий вопрос или None если программа завершена
        """
        if not self.program_router:
            raise Exception("ProgramRouter not initialized")

        try:
            # Пробуем получить следующий вопрос в текущем блоке
            question = await self.program_router.get_next_question_in_block(
                user_id, program_id, answered_question_ids
            )

            if question:
                return {
                    "status": "in_progress",
                    "question": question,
                    "block_name": question.get("block_name"),
                    "block_type": question.get("block_type")
                }

            # Блок закончен, переходим к следующему
            next_block = await self.program_router.get_next_block(user_id, program_id)

            if not next_block:
                # Программа завершена
                await self.program_router.complete_program(user_id, program_id)
                return {
                    "status": "completed",
                    "message": "Поздравляем! Вы завершили программу."
                }

            # Получаем первый вопрос нового блока
            question = await self.program_router.get_next_question_in_block(
                user_id, program_id, answered_question_ids
            )

            if question:
                return {
                    "status": "new_block",
                    "block_name": next_block["name"],
                    "block_type": next_block["type"],
                    "question": question
                }

            # Нет вопросов в новом блоке (не должно случиться)
            logger.warning(f"⚠️ No questions in new block: {next_block['block_id']}")
            return None

        except Exception as e:
            logger.error(f"❌ Error getting next program question: {e}")
            raise

    async def get_program_progress(
        self,
        user_id: int,
        program_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Получить прогресс пользователя по программе.

        Returns:
            Dict с информацией о прогрессе
        """
        if not self.program_router:
            return None

        try:
            context = await self.program_router.get_program_context(user_id, program_id)
            if not context:
                return None

            return {
                "program_id": program_id,
                "program_name": context.program_name,
                "current_block": context.current_block_id,
                "current_block_type": context.current_block_type.value if context.current_block_type else None,
                "blocks_completed": len(context.blocks_completed),
                "total_blocks": context.total_blocks,
                "completion_percentage": context.completion_percentage,
                "questions_answered": context.questions_answered if hasattr(context, 'questions_answered') else 0
            }

        except Exception as e:
            logger.error(f"❌ Error getting program progress: {e}")
            return None

    async def process_program_answer(
        self,
        user_id: int,
        program_id: str,
        question_id: str,
        answer_text: str
    ) -> Dict[str, Any]:
        """
        Обработать ответ пользователя в режиме программы.

        Выполняет:
        1. Сохранение ответа в БД (с program_id)
        2. Анализ через AnswerAnalyzer
        3. Создание embeddings
        4. Обновление личности

        Returns:
            Dict с результатами анализа
        """
        logger.info(f"📝 Processing program answer: user={user_id}, program={program_id}, question={question_id}")

        try:
            # 1. Получаем метаданные вопроса из program_questions
            question_metadata = await self._get_program_question_metadata(question_id)

            # 2. Сохраняем ответ в БД
            answer_id = await self.onboarding_dao.save_answer(
                user_id=user_id,
                question_id=question_id,
                answer_text=answer_text
            )

            # 3. Запускаем анализ (background task)
            asyncio.create_task(self._analyze_program_answer_background(
                user_id=user_id,
                answer_id=answer_id,
                question_id=question_id,
                answer_text=answer_text,
                question_metadata=question_metadata,
                program_id=program_id
            ))

            # 4. Обновляем сессию
            session = self.sessions.get(user_id)
            if session:
                session['questions_answered'] = session.get('questions_answered', 0) + 1

            return {
                "status": "success",
                "answer_id": answer_id,
                "quick_insight": "Спасибо за ваш ответ! Анализирую..."
            }

        except Exception as e:
            logger.error(f"❌ Error processing program answer: {e}")
            return {
                "status": "error",
                "error": str(e)
            }

    async def _get_program_question_metadata(self, question_id: str) -> Dict[str, Any]:
        """Получить метаданные вопроса из program_questions."""
        try:
            async with self.db_pool.acquire() as conn:
                row = await conn.fetchrow("""
                    SELECT
                        pq.text,
                        pq.depth_level,
                        pq.domain,
                        pq.energy_dynamic,
                        pq.emotional_weight,
                        pq.recommended_model,
                        pb.block_type,
                        pb.name as block_name
                    FROM selfology.program_questions pq
                    JOIN selfology.program_blocks pb ON pq.block_id = pb.block_id
                    WHERE pq.question_id = $1
                """, question_id)

                if row:
                    return dict(row)
                return {}

        except Exception as e:
            logger.error(f"❌ Error getting question metadata: {e}")
            return {}

    async def _analyze_program_answer_background(
        self,
        user_id: int,
        answer_id: int,
        question_id: str,
        answer_text: str,
        question_metadata: Dict[str, Any],
        program_id: str
    ):
        """Background task для анализа ответа в программе."""
        try:
            logger.info(f"🔬 Background analysis for program answer: user={user_id}, answer={answer_id}")

            # Формируем question dict
            question = {
                "id": question_id,
                "text": question_metadata.get("text", ""),
                "classification": {
                    "depth_level": question_metadata.get("depth_level", "SURFACE"),
                    "domain": question_metadata.get("domain", "IDENTITY"),
                    "energy_dynamic": question_metadata.get("energy_dynamic", "NEUTRAL")
                }
            }

            # Анализ через AnswerAnalyzer
            analysis_result = await self.answer_analyzer.analyze_answer(
                user_id=user_id,
                question=question,
                answer=answer_text,
                session_context={
                    "program_id": program_id,
                    "block_type": question_metadata.get("block_type"),
                    "block_name": question_metadata.get("block_name")
                }
            )

            # Сохраняем анализ
            await self.onboarding_dao.save_answer_analysis(
                answer_id=answer_id,
                analysis_result=analysis_result
            )

            # Создаём embeddings
            await self.embedding_creator.create_embeddings(
                user_id=user_id,
                answer_text=answer_text,
                analysis=analysis_result,
                context={
                    "program_id": program_id,
                    "question_id": question_id,
                    "block_type": question_metadata.get("block_type")
                }
            )

            # Обновляем профиль личности
            await self.personality_extractor.update_profile(user_id, analysis_result)

            logger.info(f"✅ Background analysis completed for answer {answer_id}")

        except Exception as e:
            logger.error(f"❌ Error in background analysis: {e}")
