"""
OnboardingOrchestrator v2 - Простой оркестратор для кластерной системы.

Три режима:
1. SMART_AI - автоматический подбор кластеров
2. PROGRAM - пользователь выбирает программу
3. FINISH_CLUSTERS - завершить незаконченные кластеры

Источник вопросов: JSON (через ClusterRouter)
Хранение ответов: PostgreSQL (user_answers_v2, user_cluster_progress)
"""

import logging
import asyncpg
from typing import Dict, List, Any, Optional
from datetime import datetime
from enum import Enum

from .cluster_router import ClusterRouter, OnboardingMode

logger = logging.getLogger(__name__)


class OnboardingOrchestratorV2:
    """
    Простой оркестратор онбординга.

    Ответственность:
    - Управление режимами онбординга
    - Координация между ClusterRouter и БД
    - Отслеживание прогресса пользователя
    """

    def __init__(self, db_pool: asyncpg.Pool = None):
        """
        Инициализация оркестратора.

        Args:
            db_pool: Пул подключений к PostgreSQL
        """
        self.db_pool = db_pool
        self.cluster_router = ClusterRouter()

        # Кеш активных сессий (для быстрого доступа)
        self._sessions: Dict[int, Dict] = {}

        logger.info("🎯 OnboardingOrchestratorV2 initialized")

    async def set_db_pool(self, pool: asyncpg.Pool):
        """Установить пул БД (если не передан в конструктор)"""
        self.db_pool = pool

    # =========================================================================
    # ПОЛУЧЕНИЕ ДАННЫХ
    # =========================================================================

    def get_all_programs(self) -> List[Dict[str, Any]]:
        """Получить список всех программ"""
        return self.cluster_router.get_all_programs()

    def get_program(self, program_id: str) -> Optional[Dict[str, Any]]:
        """Получить информацию о программе"""
        return self.cluster_router.get_program(program_id)

    # =========================================================================
    # СТАРТ ОНБОРДИНГА
    # =========================================================================

    async def start_smart_mode(self, user_id: int) -> Dict[str, Any]:
        """
        Начать умный режим - AI выбирает кластеры.

        Returns:
            Dict с первым кластером и вопросом
        """
        logger.info(f"🎯 Starting SMART mode for user {user_id}")

        # Получаем пройденные кластеры
        completed = await self._get_completed_clusters(user_id)

        # Выбираем следующий кластер
        next_cluster = self.cluster_router.get_next_smart_cluster(completed)

        if not next_cluster:
            return {
                "status": "all_completed",
                "message": "Поздравляем! Вы прошли все кластеры."
            }

        # Начинаем кластер
        return await self._start_cluster(
            user_id=user_id,
            cluster_id=next_cluster['cluster_id'],
            mode=OnboardingMode.SMART_AI
        )

    async def start_program_mode(self, user_id: int, program_id: str) -> Dict[str, Any]:
        """
        Начать режим программы - пользователь выбрал конкретную программу.

        Args:
            user_id: ID пользователя
            program_id: ID выбранной программы

        Returns:
            Dict с первым кластером и вопросом
        """
        logger.info(f"📚 Starting PROGRAM mode for user {user_id}, program {program_id}")

        # Получаем первый кластер программы
        first_cluster = self.cluster_router.get_first_cluster_in_program(program_id)

        if not first_cluster:
            return {
                "status": "error",
                "message": "Программа не найдена или пуста"
            }

        # Начинаем кластер
        return await self._start_cluster(
            user_id=user_id,
            cluster_id=first_cluster['id'],
            mode=OnboardingMode.PROGRAM,
            program_id=program_id
        )

    async def get_unfinished_clusters(self, user_id: int) -> List[Dict[str, Any]]:
        """
        Получить список незаконченных кластеров.

        Returns:
            Список незаконченных кластеров с информацией о прогрессе
        """
        if not self.db_pool:
            return []

        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT cluster_id, program_id, questions_answered, total_questions, started_at
                FROM selfology.user_cluster_progress
                WHERE user_id = $1 AND status = 'in_progress' AND questions_answered > 0
                ORDER BY started_at DESC
            """, user_id)

        result = []
        for row in rows:
            cluster = self.cluster_router.get_cluster(row['cluster_id'])
            if cluster:
                result.append({
                    'cluster_id': row['cluster_id'],
                    'cluster_name': cluster['name'],
                    'program_name': cluster['program_name'],
                    'questions_answered': row['questions_answered'],
                    'total_questions': row['total_questions'],
                    'started_at': row['started_at']
                })

        return result

    async def continue_cluster(self, user_id: int, cluster_id: str) -> Dict[str, Any]:
        """
        Продолжить незаконченный кластер.

        Args:
            user_id: ID пользователя
            cluster_id: ID кластера для продолжения

        Returns:
            Dict со следующим вопросом
        """
        logger.info(f"▶️ Continuing cluster {cluster_id} for user {user_id}")

        # Получаем отвеченные вопросы в этом кластере
        answered = await self._get_answered_questions_in_cluster(user_id, cluster_id)

        # Получаем следующий вопрос
        next_question = self.cluster_router.get_question_in_cluster(cluster_id, answered)

        if not next_question:
            # Кластер уже завершён
            await self._complete_cluster(user_id, cluster_id)
            return {
                "status": "cluster_completed",
                "message": "Кластер уже завершён"
            }

        # Сохраняем в сессию
        self._sessions[user_id] = {
            'mode': OnboardingMode.FINISH_CLUSTERS,
            'cluster_id': cluster_id,
            'current_question': next_question
        }

        cluster = self.cluster_router.get_cluster(cluster_id)

        return {
            "status": "continue",
            "cluster_name": cluster['name'] if cluster else "",
            "program_name": cluster['program_name'] if cluster else "",
            "question": next_question,
            "progress": f"{len(answered)}/{len(cluster['questions'])}" if cluster else ""
        }

    # =========================================================================
    # ОБРАБОТКА ОТВЕТОВ
    # =========================================================================

    async def process_answer(
        self,
        user_id: int,
        question_id: str,
        answer_text: str
    ) -> Dict[str, Any]:
        """
        Обработать ответ пользователя.

        Args:
            user_id: ID пользователя
            question_id: ID вопроса
            answer_text: Текст ответа

        Returns:
            Dict со следующим вопросом или статусом завершения
        """
        logger.info(f"💬 Processing answer from user {user_id} for question {question_id}")

        # Получаем сессию
        session = self._sessions.get(user_id)
        if not session:
            return {"status": "error", "message": "Нет активной сессии"}

        cluster_id = session['cluster_id']

        # Сохраняем ответ в БД
        await self._save_answer(user_id, cluster_id, question_id, answer_text)

        # Обновляем прогресс кластера
        await self._increment_cluster_progress(user_id, cluster_id)

        # Получаем отвеченные вопросы
        answered = await self._get_answered_questions_in_cluster(user_id, cluster_id)

        # Проверяем, завершён ли кластер
        if self.cluster_router.is_cluster_completed(cluster_id, answered):
            return await self._handle_cluster_completed(user_id, session)

        # Получаем следующий вопрос
        next_question = self.cluster_router.get_question_in_cluster(cluster_id, answered)

        if not next_question:
            return await self._handle_cluster_completed(user_id, session)

        # Обновляем сессию
        session['current_question'] = next_question

        cluster = self.cluster_router.get_cluster(cluster_id)

        return {
            "status": "next_question",
            "question": next_question,
            "progress": f"{len(answered)}/{len(cluster['questions'])}" if cluster else ""
        }

    # =========================================================================
    # ВНУТРЕННИЕ МЕТОДЫ
    # =========================================================================

    async def _start_cluster(
        self,
        user_id: int,
        cluster_id: str,
        mode: OnboardingMode,
        program_id: str = None
    ) -> Dict[str, Any]:
        """Начать новый кластер"""

        cluster = self.cluster_router.get_cluster(cluster_id)
        if not cluster:
            return {"status": "error", "message": "Кластер не найден"}

        # Создаём запись прогресса
        await self._create_cluster_progress(
            user_id=user_id,
            cluster_id=cluster_id,
            program_id=program_id or cluster['program_id'],
            total_questions=len(cluster['questions'])
        )

        # Получаем первый вопрос
        first_question = self.cluster_router.get_question_in_cluster(cluster_id, [])

        if not first_question:
            return {"status": "error", "message": "В кластере нет вопросов"}

        # Сохраняем сессию
        self._sessions[user_id] = {
            'mode': mode,
            'cluster_id': cluster_id,
            'program_id': program_id or cluster['program_id'],
            'current_question': first_question
        }

        return {
            "status": "started",
            "cluster_id": cluster_id,
            "cluster_name": cluster['name'],
            "program_name": cluster['program_name'],
            "total_questions": len(cluster['questions']),
            "question": first_question
        }

    async def _handle_cluster_completed(
        self,
        user_id: int,
        session: Dict
    ) -> Dict[str, Any]:
        """Обработать завершение кластера"""

        cluster_id = session['cluster_id']
        mode = session['mode']
        program_id = session.get('program_id')

        # Отмечаем кластер завершённым
        await self._complete_cluster(user_id, cluster_id)

        cluster = self.cluster_router.get_cluster(cluster_id)

        result = {
            "status": "cluster_completed",
            "cluster_name": cluster['name'] if cluster else "",
            "message": "🎉 Кластер завершён!"
        }

        # Определяем следующий шаг в зависимости от режима
        if mode == OnboardingMode.SMART_AI:
            # Умный режим - выбираем следующий кластер автоматически
            completed = await self._get_completed_clusters(user_id)
            next_cluster = self.cluster_router.get_next_smart_cluster(completed)

            if next_cluster:
                result["next_cluster"] = next_cluster
                result["has_next"] = True
            else:
                result["has_next"] = False
                result["message"] = "🎉 Поздравляем! Все кластеры пройдены!"

        elif mode == OnboardingMode.PROGRAM:
            # Режим программы - следующий кластер в программе
            next_cluster = self.cluster_router.get_next_cluster_in_program(program_id, cluster_id)

            if next_cluster:
                result["next_cluster"] = {
                    "cluster_id": next_cluster['id'],
                    "cluster_name": next_cluster['name'],
                    "questions_count": len(next_cluster['questions'])
                }
                result["has_next"] = True
            else:
                result["has_next"] = False
                result["program_completed"] = True
                result["message"] = "🎉 Поздравляем! Программа завершена!"

        else:
            # Режим завершения - проверяем остались ли ещё незаконченные
            unfinished = await self.get_unfinished_clusters(user_id)
            result["has_next"] = len(unfinished) > 0
            result["unfinished_count"] = len(unfinished)

        # Очищаем сессию
        self._sessions.pop(user_id, None)

        return result

    # =========================================================================
    # РАБОТА С БД
    # =========================================================================

    async def _save_answer(
        self,
        user_id: int,
        cluster_id: str,
        question_id: str,
        answer_text: str
    ):
        """Сохранить ответ в БД"""
        if not self.db_pool:
            logger.warning("⚠️ No DB pool - answer not saved")
            return

        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO selfology.user_answers_v2
                (user_id, cluster_id, question_id, answer_text)
                VALUES ($1, $2, $3, $4)
            """, user_id, cluster_id, question_id, answer_text)

        logger.info(f"💾 Answer saved: user={user_id}, question={question_id}")

    async def _get_answered_questions_in_cluster(
        self,
        user_id: int,
        cluster_id: str
    ) -> List[str]:
        """Получить список отвеченных вопросов в кластере"""
        if not self.db_pool:
            return []

        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT question_id FROM selfology.user_answers_v2
                WHERE user_id = $1 AND cluster_id = $2
            """, user_id, cluster_id)

        return [row['question_id'] for row in rows]

    async def _get_completed_clusters(self, user_id: int) -> List[str]:
        """Получить список пройденных кластеров"""
        if not self.db_pool:
            return []

        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT cluster_id FROM selfology.user_cluster_progress
                WHERE user_id = $1 AND status = 'completed'
            """, user_id)

        return [row['cluster_id'] for row in rows]

    async def _create_cluster_progress(
        self,
        user_id: int,
        cluster_id: str,
        program_id: str,
        total_questions: int
    ):
        """Создать запись прогресса по кластеру"""
        if not self.db_pool:
            return

        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO selfology.user_cluster_progress
                (user_id, cluster_id, program_id, total_questions, status)
                VALUES ($1, $2, $3, $4, 'in_progress')
                ON CONFLICT (user_id, cluster_id) DO UPDATE
                SET status = 'in_progress', started_at = NOW()
            """, user_id, cluster_id, program_id, total_questions)

    async def _increment_cluster_progress(self, user_id: int, cluster_id: str):
        """Увеличить счётчик отвеченных вопросов"""
        if not self.db_pool:
            return

        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                UPDATE selfology.user_cluster_progress
                SET questions_answered = questions_answered + 1
                WHERE user_id = $1 AND cluster_id = $2
            """, user_id, cluster_id)

    async def _complete_cluster(self, user_id: int, cluster_id: str):
        """Отметить кластер как завершённый"""
        if not self.db_pool:
            return

        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                UPDATE selfology.user_cluster_progress
                SET status = 'completed', completed_at = NOW()
                WHERE user_id = $1 AND cluster_id = $2
            """, user_id, cluster_id)

        logger.info(f"✅ Cluster {cluster_id} completed for user {user_id}")

    # =========================================================================
    # УТИЛИТЫ
    # =========================================================================

    def get_current_session(self, user_id: int) -> Optional[Dict]:
        """Получить текущую сессию пользователя"""
        return self._sessions.get(user_id)

    def clear_session(self, user_id: int):
        """Очистить сессию пользователя"""
        self._sessions.pop(user_id, None)

    def get_stats(self) -> Dict[str, Any]:
        """Статистика системы"""
        return {
            "active_sessions": len(self._sessions),
            "router_stats": self.cluster_router.get_stats()
        }

    async def shutdown(self, timeout: float = 30.0) -> Dict[str, Any]:
        """
        Graceful shutdown оркестратора.

        Args:
            timeout: Таймаут ожидания в секундах

        Returns:
            Статистика на момент остановки (формат совместим с контроллером)
        """
        import time
        start_time = time.time()

        # Очищаем сессии
        sessions_count = len(self._sessions)
        self._sessions.clear()

        shutdown_time = time.time() - start_time

        logger.info(f"🛑 OnboardingOrchestratorV2 shutdown complete. Cleared {sessions_count} sessions.")

        # Формат совместимый с selfology_controller.py
        return {
            "status": "completed",
            "tasks_completed": sessions_count,
            "tasks_cancelled": 0,
            "shutdown_time": shutdown_time
        }
