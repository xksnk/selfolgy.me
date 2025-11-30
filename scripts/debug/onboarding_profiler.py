#!/usr/bin/env python3
"""
🔬 Selfology Onboarding Profiler v2.0
Комплексная диагностика цифровой личности пользователя

АРХИТЕКТУРА ОТЧЕТА:
1. 📊 Статистика онбординга (первым блоком)
2. 💬 Детальный отчет по вопросам
3. 📈 Векторная память пользователя (Qdrant)
4. 🔄 Активная сессия (кратко)
"""

import asyncio
import json
import requests
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker


class OnboardingProfiler:
    """Профилировщик системы онбординга с фокусом на цифровую личность"""

    # Константы форматирования (для Telegram)
    DIVIDER_MAIN = "=" * 44  # Основной разделитель тем
    DIVIDER_SUB = "━" * 44   # Разделитель подтем
    MAX_WIDTH = 44           # Максимальная ширина строки

    def __init__(self):
        self.DATABASE_URL = "postgresql+asyncpg://n8n:sS67wM+1zMBRFHAW4kj9HwFl5J6+veo7Nirx0/I+oiU=@localhost:5432/n8n"
        self.engine = create_async_engine(self.DATABASE_URL, echo=False)
        self.async_session = sessionmaker(self.engine, class_=AsyncSession, expire_on_commit=False)
        self.qdrant_url = "http://localhost:6333"

    async def get_all_user_answers(self, user_id: int) -> List[Dict[str, Any]]:
        """
        Получить ВСЕ ответы пользователя за все время

        ВКЛЮЧАЕТ:
        - Обычные ответы из user_answers_new
        - Context stories из user_context_stories

        Returns:
            List of answers with analysis info + processing statuses
        """
        async with self.async_session() as session:
            result = await session.execute(text("""
                -- Обычные ответы (берем ПОСЛЕДНИЙ анализ для каждого ответа)
                SELECT
                    ua.id as answer_id,
                    ua.session_id,
                    ua.question_json_id,
                    ua.raw_answer,
                    ua.answer_length,
                    ua.answered_at,
                    ua.analysis_status,
                    aa.id as analysis_id,
                    aa.ai_model_used,
                    aa.processing_time_ms,
                    aa.quality_score,
                    aa.confidence_score,
                    aa.raw_ai_response,
                    aa.vectorization_status,
                    aa.vectorization_error,
                    aa.dp_update_status,
                    aa.dp_update_error,
                    aa.background_task_completed,
                    aa.background_task_duration_ms,
                    aa.retry_count,
                    'answer' as item_type
                FROM selfology.user_answers_new ua
                JOIN selfology.onboarding_sessions os ON ua.session_id = os.id
                LEFT JOIN LATERAL (
                    SELECT * FROM selfology.answer_analysis
                    WHERE user_answer_id = ua.id
                    ORDER BY id DESC
                    LIMIT 1
                ) aa ON true
                WHERE os.user_id = :user_id

                UNION ALL

                -- Context stories (берем ПОСЛЕДНИЙ анализ для каждого story)
                SELECT
                    cs.id as answer_id,
                    cs.session_id,
                    'system_context_story' as question_json_id,
                    cs.story_text as raw_answer,
                    LENGTH(cs.story_text) as answer_length,
                    cs.created_at as answered_at,
                    'completed' as analysis_status,
                    aa.id as analysis_id,
                    aa.ai_model_used,
                    aa.processing_time_ms,
                    aa.quality_score,
                    aa.confidence_score,
                    aa.raw_ai_response,
                    aa.vectorization_status,
                    aa.vectorization_error,
                    aa.dp_update_status,
                    aa.dp_update_error,
                    aa.background_task_completed,
                    aa.background_task_duration_ms,
                    aa.retry_count,
                    'story' as item_type
                FROM selfology.user_context_stories cs
                LEFT JOIN LATERAL (
                    SELECT * FROM selfology.answer_analysis
                    WHERE context_story_id = cs.id
                    ORDER BY id DESC
                    LIMIT 1
                ) aa ON true
                WHERE cs.user_id = :user_id AND cs.is_active = true

                ORDER BY answered_at ASC
            """), {"user_id": user_id})

            answers = []
            for row in result:
                answers.append({
                    "answer_id": row[0],
                    "session_id": row[1],
                    "question_json_id": row[2],
                    "raw_answer": row[3],
                    "answer_length": row[4],
                    "answered_at": row[5],
                    "analysis_status": row[6],
                    "analysis_id": row[7],
                    "ai_model_used": row[8],
                    "processing_time_ms": row[9],
                    "quality_score": row[10],
                    "confidence_score": row[11],
                    "raw_ai_response": row[12],
                    "vectorization_status": row[13],
                    "vectorization_error": row[14],
                    "dp_update_status": row[15],
                    "dp_update_error": row[16],
                    "background_task_completed": row[17],
                    "background_task_duration_ms": row[18],
                    "retry_count": row[19],
                    "item_type": row[20]  # 'answer' или 'story'
                })

            return answers

    async def get_digital_personality(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Получить digital personality пользователя"""
        async with self.async_session() as session:
            result = await session.execute(text("""
                SELECT
                    identity, interests, goals, barriers,
                    relationships, values, current_state,
                    skills, experiences, health,
                    total_answers_analyzed,
                    completeness_score,
                    last_updated
                FROM selfology.digital_personality
                WHERE user_id = :user_id
            """), {"user_id": user_id})

            row = result.fetchone()
            if not row:
                return None

            return {
                "identity": row[0],
                "interests": row[1],
                "goals": row[2],
                "barriers": row[3],
                "relationships": row[4],
                "values": row[5],
                "current_state": row[6],
                "skills": row[7],
                "experiences": row[8],
                "health": row[9],
                "total_answers_analyzed": row[10],
                "completeness_score": row[11],
                "last_updated": row[12]
            }

    async def get_active_session(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Получить активную сессию пользователя"""
        async with self.async_session() as session:
            result = await session.execute(text("""
                SELECT
                    id, status, questions_asked, questions_answered,
                    last_strategy, domains_covered, heavy_count,
                    started_at
                FROM selfology.onboarding_sessions
                WHERE user_id = :user_id AND status = 'active'
                ORDER BY started_at DESC
                LIMIT 1
            """), {"user_id": user_id})

            row = result.fetchone()
            if not row:
                return None

            return {
                "id": row[0],
                "status": row[1],
                "questions_asked": row[2],
                "questions_answered": row[3],
                "last_strategy": row[4],
                "domains_covered": row[5] or [],
                "heavy_count": row[6],
                "started_at": row[7]
            }

    async def get_recent_sessions(self, user_id: int, limit: int = 2) -> List[Dict[str, Any]]:
        """Получить последние N сессий пользователя (включая активную)"""
        async with self.async_session() as session:
            result = await session.execute(text("""
                SELECT
                    id, status, questions_asked, questions_answered,
                    started_at
                FROM selfology.onboarding_sessions
                WHERE user_id = :user_id
                ORDER BY started_at DESC
                LIMIT :limit
            """), {"user_id": user_id, "limit": limit})

            sessions = []
            for row in result:
                sessions.append({
                    "id": row[0],
                    "status": row[1],
                    "questions_asked": row[2],
                    "questions_answered": row[3],
                    "started_at": row[4]
                })
            return sessions

    def check_qdrant_vectors(self, user_id: int) -> Dict[str, Any]:
        """
        Проверить векторы пользователя в Qdrant

        Returns:
            Dict с информацией по каждой коллекции
        """
        collections_info = {}
        target_collections = [
            "personality_evolution",
            "personality_profiles",
            "quick_match"
        ]

        try:
            for collection_name in target_collections:
                try:
                    # Scroll через все точки с фильтром по user_id
                    response = requests.post(
                        f"{self.qdrant_url}/collections/{collection_name}/points/scroll",
                        json={
                            "filter": {
                                "must": [
                                    {"key": "user_id", "match": {"value": user_id}}
                                ]
                            },
                            "limit": 1000,
                            "with_payload": True
                        },
                        timeout=5
                    )

                    if response.status_code == 200:
                        data = response.json()
                        points = data.get("result", {}).get("points", [])

                        # Получаем последний timestamp
                        last_update = None
                        if points:
                            timestamps = [
                                p.get("payload", {}).get("timestamp")
                                for p in points
                                if p.get("payload", {}).get("timestamp")
                            ]
                            if timestamps:
                                last_update = max(timestamps)

                        collections_info[collection_name] = {
                            "count": len(points),
                            "last_update": last_update,
                            "status": "ok"
                        }
                    else:
                        collections_info[collection_name] = {
                            "count": 0,
                            "status": f"error_{response.status_code}"
                        }

                except Exception as e:
                    collections_info[collection_name] = {
                        "count": 0,
                        "status": f"error: {str(e)}"
                    }

        except Exception as e:
            # Общая ошибка Qdrant
            for col in target_collections:
                collections_info[col] = {
                    "count": 0,
                    "status": "qdrant_unavailable"
                }

        return collections_info

    def format_statistics_section(
        self,
        user_id: int,
        answers: List[Dict],
        personality: Optional[Dict],
        qdrant_info: Dict
    ) -> str:
        """Форматировать секцию статистики"""

        total_answers = len(answers)
        analyzed_count = sum(1 for a in answers if a['analysis_id'] is not None)

        # Проверяем наличие профиля в Qdrant (у пользователя 1 агрегированный профиль)
        qdrant_profile_exists = qdrant_info.get("personality_profiles", {}).get("count", 0) > 0
        qdrant_last_update = qdrant_info.get("personality_profiles", {}).get("last_update")

        # Проверяем digital personality (тоже 1 агрегированный профиль)
        dp_exists = personality is not None
        dp_last_update = personality.get("last_updated") if personality else None

        # Процент заполнения личности
        completeness = int(personality.get("completeness_score", 0) * 100) if personality else 0

        output = []
        output.append(self.DIVIDER_MAIN)
        output.append("📊 СТАТИСТИКА ОНБОРДИНГА")
        output.append(self.DIVIDER_MAIN)
        output.append("")
        output.append(f"Пользователь: #{user_id}")
        output.append(f"Всего ответов: {total_answers}")
        output.append("")
        output.append(self.DIVIDER_SUB)
        output.append("ЭТАПЫ ОБРАБОТКИ:")
        output.append(self.DIVIDER_SUB)

        # Этапы
        output.append(f"✅ Сохранено в SQL:      {total_answers} ответов")

        ai_pct = int(analyzed_count / total_answers * 100) if total_answers > 0 else 0
        output.append(f"{'✅' if ai_pct == 100 else '⚠️'} AI Анализ:            {analyzed_count} / {total_answers} ({ai_pct}%)")

        # Векторизация - показываем статус профиля
        if qdrant_profile_exists:
            update_info = f" (обновлен: {qdrant_last_update})" if qdrant_last_update else ""
            output.append(f"✅ Профиль в Qdrant:    создан{update_info}")
        else:
            output.append(f"❌ Профиль в Qdrant:    не создан")

        # Digital Personality - показываем статус профиля
        if dp_exists:
            update_info = f" (обновлена: {dp_last_update.strftime('%Y-%m-%d %H:%M')})" if dp_last_update else ""
            output.append(f"✅ Digital Personality: создана{update_info}")
        else:
            output.append(f"❌ Digital Personality: не создана")

        # Digital Personality секция
        if personality:
            output.append("")
            output.append(self.DIVIDER_SUB)
            output.append("ЦИФРОВАЯ ЛИЧНОСТЬ:")
            output.append(self.DIVIDER_SUB)
            output.append(f"Completeness: {completeness}%")

            last_update = personality.get("last_updated")
            if last_update:
                output.append(f"Последнее обновление: {last_update.strftime('%Y-%m-%d %H:%M')}")

            output.append("")
            output.append("Заполненные слои:")

            # Проверяем каждый слой
            layers = [
                ("identity", "личность"),
                ("interests", "интересы"),
                ("goals", "цели"),
                ("barriers", "барьеры"),
                ("relationships", "отношения"),
                ("values", "ценности"),
                ("current_state", "текущее состояние"),
                ("skills", "навыки"),
                ("experiences", "опыт"),
                ("health", "здоровье")
            ]

            for layer_key, layer_name in layers:
                layer_data = personality.get(layer_key, [])
                if isinstance(layer_data, list):
                    count = len(layer_data)
                elif isinstance(layer_data, dict):
                    count = len(layer_data)
                else:
                    count = 0

                status = "✅" if count > 0 else "❌"
                output.append(f"  {status} {layer_name}: {count} параметров")
        else:
            output.append("")
            output.append("⚠️ Digital Personality не создана")

        return "\n".join(output)

    def format_answers_section(self, answers: List[Dict], qdrant_info: Dict, recent_session_ids: List[int]) -> str:
        """
        Форматировать секцию детального отчета по вопросам

        Показывает только:
        - Ответы из последних 2 сессий (текущая + предыдущая)
        - Ответы с ошибками (из любых сессий)
        """

        # Фильтруем ответы
        filtered_answers = []
        for answer in answers:
            # Проверяем наличие ошибок
            has_error = (
                answer.get('vectorization_status') == 'failed' or
                answer.get('dp_update_status') == 'failed' or
                answer.get('vectorization_error') or
                answer.get('dp_update_error')
            )

            # Включаем если из последних 2 сессий ИЛИ есть ошибка
            if answer['session_id'] in recent_session_ids or has_error:
                filtered_answers.append(answer)

        output = []
        output.append("")
        output.append(self.DIVIDER_MAIN)
        output.append("💬 ДЕТАЛЬНЫЙ ОТЧЕТ ПО ВОПРОСАМ")
        output.append(self.DIVIDER_MAIN)

        if not filtered_answers:
            output.append("")
            output.append("Нет ответов для отображения")
            output.append("")
            return "\n".join(output)

        output.append(f"")
        output.append(f"Показано: {len(filtered_answers)} из {len(answers)} ответов")
        output.append(f"(последние 2 сессии + ответы с ошибками)")
        output.append("")

        for i, answer in enumerate(filtered_answers, 1):
            # ✅ РЕАЛЬНЫЕ СТАТУСЫ из БД (не проверка данных, а реальное выполнение)
            sql_status = "✅"
            ai_status = "✅" if answer['analysis_id'] else "❌"

            # Векторизация - используем РЕАЛЬНЫЙ статус из БД
            vectorization_status = answer.get('vectorization_status', 'pending')
            if vectorization_status == 'success':
                qdrant_status = "✅"
            elif vectorization_status == 'failed':
                qdrant_status = "❌"
            else:  # pending
                qdrant_status = "⏳"

            # DP update - используем РЕАЛЬНЫЙ статус из БД
            dp_status_value = answer.get('dp_update_status', 'pending')
            if dp_status_value == 'success':
                dp_status = "✅"
            elif dp_status_value == 'failed':
                dp_status = "❌"
            else:  # pending
                dp_status = "⏳"

            # Background task статус
            task_completed = answer.get('background_task_completed', False)
            task_mark = "⚡" if task_completed else "⏳"

            # Retry count
            retry_count = answer.get('retry_count') or 0
            retry_mark = f" 🔄x{retry_count}" if retry_count > 0 else ""

            # Добавляем [STORY] префикс для context stories
            item_prefix = "[STORY] " if answer.get('item_type') == 'story' else ""
            output.append(f"#{i}  {item_prefix}{answer['question_json_id']}  {sql_status}SQL {ai_status}AI {qdrant_status}Qdrant {dp_status}Личность {task_mark}{retry_mark}")

            # Дополнительная информация
            if answer['analysis_id']:
                model = answer['ai_model_used'] or "unknown"
                time_ms = answer['processing_time_ms'] or 0
                quality = answer['quality_score'] or 0.0
                confidence = answer['confidence_score'] or 0.0
                task_duration = answer.get('background_task_duration_ms')

                # Основная информация об анализе
                task_info = f", Task:{task_duration}ms" if task_duration else ""
                output.append(f"    Анализ: {model} ({time_ms}ms{task_info}, Q:{quality:.2f}, C:{confidence:.2f})")

                # ✅ Показываем ошибки, если есть
                vec_error = answer.get('vectorization_error')
                if vec_error:
                    short_error = vec_error[:50] + "..." if len(vec_error) > 50 else vec_error
                    output.append(f"    ❌ Векторизация: {short_error}")

                dp_error = answer.get('dp_update_error')
                if dp_error:
                    short_error = dp_error[:50] + "..." if len(dp_error) > 50 else dp_error
                    output.append(f"    ❌ DP Update: {short_error}")

                # Влияние на личность (из raw_ai_response)
                if answer['raw_ai_response']:
                    try:
                        ai_response = answer['raw_ai_response']
                        if isinstance(ai_response, str):
                            ai_response = json.loads(ai_response)

                        personality_summary = ai_response.get("personality_summary", {})
                        if personality_summary:
                            affected_layers = [k for k, v in personality_summary.items() if v]
                            if affected_layers:
                                layers_str = ", ".join(affected_layers[:3])  # Первые 3
                                output.append(f"    Влияние: {layers_str}")
                    except:
                        pass
            else:
                output.append(f"    Статус: AI анализ pending")

            output.append("")  # Пустая строка между вопросами

        return "\n".join(output)

    def format_qdrant_section(self, user_id: int, qdrant_info: Dict, answers_count: int = 0) -> str:
        """Форматировать секцию Qdrant векторной памяти"""

        output = []
        output.append(self.DIVIDER_MAIN)
        output.append("📈 ВЕКТОРНАЯ ПАМЯТЬ ПОЛЬЗОВАТЕЛЯ (Qdrant)")
        output.append(self.DIVIDER_MAIN)
        output.append("")

        collections = [
            ("personality_evolution", "3072D", "глубокий анализ"),
            ("personality_profiles", "1536D", "повседневное общение"),
            ("quick_match", "512D", "быстрый поиск")
        ]

        counts = []

        for col_name, dimension, purpose in collections:
            col_info = qdrant_info.get(col_name, {})
            count = col_info.get("count", 0)
            status = col_info.get("status", "unknown")

            counts.append(count)

            output.append(f"{col_name} ({dimension}):")
            output.append(f"  Векторов: {count}")
            output.append(f"  Назначение: {purpose}")

            if col_info.get("last_update"):
                output.append(f"  Последний: {col_info['last_update']}")

            if status != "ok":
                output.append(f"  ⚠️ Статус: {status}")

            output.append("")

        # ✅ Проверка синхронизации с учетом архитектуры:
        # personality_evolution: 2 вектора на ответ (evolution_point + breakthrough_snapshot)
        # personality_profiles: 1 агрегированный профиль
        # quick_match: 1 агрегированный профиль
        output.append(self.DIVIDER_SUB)

        expected_evolution = answers_count * 2  # 2 вектора на ответ
        expected_profile = 1 if answers_count > 0 else 0
        expected_match = 1 if answers_count > 0 else 0

        is_synced = (
            counts[0] == expected_evolution and
            counts[1] == expected_profile and
            counts[2] == expected_match
        )

        if is_synced:
            output.append(f"✅ Коллекции синхронизированы [{counts[0]}, {counts[1]}, {counts[2]}]")
            output.append(f"   Ожидалось: [{expected_evolution}, {expected_profile}, {expected_match}] для {answers_count} ответов")
        else:
            output.append("⚠️ Коллекции не синхронизированы!")
            output.append(f"   Текущее: [{counts[0]}, {counts[1]}, {counts[2]}]")
            output.append(f"   Ожидалось: [{expected_evolution}, {expected_profile}, {expected_match}] для {answers_count} ответов")

        return "\n".join(output)

    def format_session_section(self, session: Optional[Dict]) -> str:
        """Форматировать секцию активной сессии"""

        output = []
        output.append("")
        output.append(self.DIVIDER_MAIN)
        output.append("🔄 АКТИВНАЯ СЕССИЯ")
        output.append(self.DIVIDER_MAIN)
        output.append("")

        if not session:
            output.append("❌ Нет активной сессии")
            return "\n".join(output)

        output.append(f"Session ID: {session['id']}")
        output.append(f"Статус: {session['status']}")

        strategy = session.get('last_strategy', 'Not set')
        output.append(f"Стратегия: {strategy}")

        answered = session.get('questions_answered', 0)
        target_questions = 20  # Целевое количество вопросов за сессию
        output.append(f"Прогресс: {answered} / {target_questions} вопросов ({int(answered/target_questions*100) if answered <= target_questions else 100}%)")

        domains = session.get('domains_covered', [])
        if domains:
            output.append(f"Домены: {', '.join(domains)} ({len(domains)}/13)")

        heavy = session.get('heavy_count', 0)
        output.append(f"Heavy вопросов: {heavy}")

        # Длительность сессии
        started = session.get('started_at')
        if started:
            duration = datetime.now() - started
            hours = int(duration.total_seconds() / 3600)
            minutes = int((duration.total_seconds() % 3600) / 60)
            output.append(f"Длительность: {hours}ч {minutes}мин")

        return "\n".join(output)

    async def profile_user(self, user_id: int) -> str:
        """
        Полное профилирование пользователя

        Returns:
            Отформатированный текстовый отчет
        """

        # Собираем все данные
        answers = await self.get_all_user_answers(user_id)
        personality = await self.get_digital_personality(user_id)
        session = await self.get_active_session(user_id)
        recent_sessions = await self.get_recent_sessions(user_id, limit=2)
        qdrant_info = self.check_qdrant_vectors(user_id)

        # Извлекаем ID последних 2 сессий для фильтрации
        recent_session_ids = [s['id'] for s in recent_sessions]

        # Добавляем информацию о digital personality в qdrant_info для детального отчета
        qdrant_info["dp_exists"] = personality is not None

        # Формируем секции
        sections = []

        # 1. Статистика (первым)
        sections.append(self.format_statistics_section(user_id, answers, personality, qdrant_info))

        # 2. Детальный отчет по вопросам (только последние 2 сессии + ошибки)
        if answers:
            sections.append(self.format_answers_section(answers, qdrant_info, recent_session_ids))

        # 3. Qdrant векторная память
        sections.append(self.format_qdrant_section(user_id, qdrant_info, len(answers)))

        # 4. Активная сессия (в конце)
        sections.append(self.format_session_section(session))

        # Собираем все вместе
        full_report = "\n".join(sections)

        return full_report


async def main():
    """Main entry point"""
    import sys

    user_id = 98005572  # Default user

    if len(sys.argv) > 1:
        try:
            user_id = int(sys.argv[1])
        except ValueError:
            print(f"❌ Invalid user_id: {sys.argv[1]}")
            sys.exit(1)

    profiler = OnboardingProfiler()
    report = await profiler.profile_user(user_id)

    # Выводим отчет
    print(report)


if __name__ == "__main__":
    asyncio.run(main())
