#!/usr/bin/env python3
"""
Мониторинг онбординга в реальном времени
Показывает последние операции и их статус
"""

import asyncio
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List
import asyncpg
from dotenv import load_dotenv

load_dotenv()


class OnboardingMonitor:
    """Монитор работы системы онбординга"""

    def __init__(self):
        self.db_config = {
            "host": os.getenv("DB_HOST", "localhost"),
            "port": int(os.getenv("DB_PORT", 5432)),
            "user": os.getenv("DB_USER", "n8n"),
            "password": os.getenv("DB_PASSWORD", "sS67wM+1zMBRFHAW4kj9HwFl5J6+veo7Nirx0/I+oiU="),
            "database": os.getenv("DB_NAME", "n8n")
        }

    async def get_recent_answers(self, hours: int = 1, user_id: int = None) -> List[Dict]:
        """Получить недавние ответы и их статус обработки"""

        conn = await asyncpg.connect(**self.db_config)

        try:
            query = """
                SELECT
                    ua.id as answer_id,
                    os.user_id,
                    ua.question_json_id,
                    ua.answered_at,
                    ua.analysis_status,

                    -- AI анализ
                    aa.id as analysis_id,
                    aa.ai_model_used,
                    aa.processing_time_ms,
                    aa.processed_at,
                    aa.quality_score,
                    aa.confidence_score,

                    -- ✅ НОВЫЕ СТАТУСЫ ОБРАБОТКИ (Oct 2025)
                    aa.vectorization_status,
                    aa.vectorization_error,
                    aa.vectorization_completed_at,
                    aa.dp_update_status,
                    aa.dp_update_error,
                    aa.dp_update_completed_at,
                    aa.background_task_completed,
                    aa.background_task_duration_ms,
                    aa.retry_count,

                    -- Digital Personality (для проверки)
                    dp.last_updated as dp_updated_at,
                    dp.total_answers_analyzed as dp_total_answers,

                    -- Timestamps для расчета задержек
                    EXTRACT(EPOCH FROM (aa.processed_at - ua.answered_at)) as analysis_delay_sec,
                    EXTRACT(EPOCH FROM (dp.last_updated - aa.processed_at)) as dp_delay_sec

                FROM selfology.user_answers_new ua
                JOIN selfology.onboarding_sessions os ON ua.session_id = os.id
                LEFT JOIN selfology.answer_analysis aa ON aa.user_answer_id = ua.id
                LEFT JOIN selfology.digital_personality dp ON dp.user_id = os.user_id
                WHERE ua.answered_at > NOW() - INTERVAL '{hours} hours'
                {user_filter}
                ORDER BY ua.answered_at DESC
                LIMIT 50
            """.format(
                hours=hours,
                user_filter=f"AND os.user_id = {user_id}" if user_id else ""
            )

            rows = await conn.fetch(query)
            return [dict(row) for row in rows]

        finally:
            await conn.close()

    async def check_qdrant_updates(self, user_ids: List[int]) -> Dict:
        """Проверить обновления в Qdrant для списка пользователей"""

        import requests

        qdrant_updates = {}

        for user_id in user_ids:
            try:
                response = requests.post(
                    "http://localhost:6333/collections/personality_profiles/points/scroll",
                    json={
                        "filter": {"must": [{"key": "user_id", "match": {"value": user_id}}]},
                        "limit": 1,
                        "with_payload": True
                    },
                    timeout=2
                )

                if response.status_code == 200:
                    data = response.json()
                    points = data.get("result", {}).get("points", [])

                    if points:
                        payload = points[0].get("payload", {})
                        qdrant_updates[user_id] = {
                            "exists": True,
                            "updated_at": payload.get("updated_at"),
                            "vector_type": payload.get("vector_type"),
                            "quality_score": payload.get("quality_score")
                        }
                    else:
                        qdrant_updates[user_id] = {"exists": False}

            except Exception as e:
                qdrant_updates[user_id] = {"error": str(e)}

        return qdrant_updates

    def format_monitor_report(self, answers: List[Dict], qdrant_info: Dict) -> str:
        """Форматировать отчет мониторинга"""

        if not answers:
            return "📭 Нет новых ответов за указанный период"

        output = []
        output.append("=" * 75)
        output.append("🔍 МОНИТОРИНГ ОНБОРДИНГА")
        output.append("=" * 75)
        output.append(f"\n📊 Найдено ответов: {len(answers)}")
        output.append(f"⏰ Период: последние операции\n")

        # Группируем по пользователям
        users = {}
        for answer in answers:
            user_id = answer['user_id']
            if user_id not in users:
                users[user_id] = []
            users[user_id].append(answer)

        # Отчет по каждому пользователю
        for user_id, user_answers in users.items():
            output.append("─" * 75)
            output.append(f"👤 Пользователь: #{user_id} ({len(user_answers)} ответов)")
            output.append("")

            # Qdrant статус
            qdrant_status = qdrant_info.get(user_id, {})
            if qdrant_status.get("exists"):
                output.append(f"   ✅ Qdrant профиль: обновлен {qdrant_status.get('updated_at', 'N/A')}")
            elif qdrant_status.get("error"):
                output.append(f"   ❌ Qdrant: ошибка - {qdrant_status.get('error')}")
            else:
                output.append(f"   ⚠️  Qdrant профиль: не найден")

            output.append("")

            # Таблица ответов
            for i, answer in enumerate(user_answers, 1):
                answered_time = answer['answered_at'].strftime('%H:%M:%S')
                question = answer['question_json_id']

                # Статусы
                sql_ok = "✅"

                # ✅ AI анализ
                if answer['analysis_id']:
                    ai_ok = "✅"
                    model = answer['ai_model_used'] or "?"
                    delay = int(answer['analysis_delay_sec']) if answer['analysis_delay_sec'] else 0
                    quality = answer['quality_score'] or 0.0

                    # Определяем цвет по задержке
                    if delay < 5:
                        delay_mark = "🟢"
                    elif delay < 15:
                        delay_mark = "🟡"
                    else:
                        delay_mark = "🔴"
                else:
                    ai_ok = "❌"
                    model = "N/A"
                    delay = 0
                    quality = 0.0
                    delay_mark = "⚠️"

                # ✅ РЕАЛЬНЫЙ статус векторизации (из БД, не просто проверка данных)
                vectorization_status = answer.get('vectorization_status', 'pending')
                if vectorization_status == 'success':
                    qdrant_ok = "✅"
                elif vectorization_status == 'failed':
                    qdrant_ok = "❌"
                    error = answer.get('vectorization_error', 'Unknown error')[:30]
                    qdrant_ok += f"({error}...)" if len(error) == 30 else f"({error})"
                else:  # pending
                    qdrant_ok = "⏳"

                # ✅ РЕАЛЬНЫЙ статус обновления DP (из БД)
                dp_status = answer.get('dp_update_status', 'pending')
                if dp_status == 'success':
                    dp_ok = "✅"
                elif dp_status == 'failed':
                    dp_ok = "❌"
                    error = answer.get('dp_update_error', 'Unknown error')[:30]
                    dp_ok += f"({error}...)" if len(error) == 30 else f"({error})"
                else:  # pending
                    dp_ok = "⏳"

                # Retry информация
                retry_count = answer.get('retry_count') or 0
                retry_info = f" 🔄x{retry_count}" if retry_count > 0 else ""

                # Background task статус
                task_completed = answer.get('background_task_completed', False)
                task_duration = answer.get('background_task_duration_ms')
                task_info = ""
                if task_completed and task_duration:
                    task_info = f" ⚡{task_duration}ms"

                output.append(
                    f"   {i}. [{answered_time}] {question}: "
                    f"{sql_ok}SQL {ai_ok}AI({model}) {delay_mark}{delay}s "
                    f"{qdrant_ok}Qdrant {dp_ok}DP Q:{quality:.2f}{retry_info}{task_info}"
                )

            output.append("")

        # ✅ СВОДКА ПО РЕАЛЬНЫМ СТАТУСАМ ОБРАБОТКИ
        total = len(answers)
        with_analysis = sum(1 for a in answers if a['analysis_id'])

        # Статусы векторизации
        vectorization_success = sum(1 for a in answers if a.get('vectorization_status') == 'success')
        vectorization_failed = sum(1 for a in answers if a.get('vectorization_status') == 'failed')
        vectorization_pending = sum(1 for a in answers if a.get('vectorization_status') == 'pending')

        # Статусы DP
        dp_success = sum(1 for a in answers if a.get('dp_update_status') == 'success')
        dp_failed = sum(1 for a in answers if a.get('dp_update_status') == 'failed')
        dp_pending = sum(1 for a in answers if a.get('dp_update_status') == 'pending')

        # Background tasks
        tasks_completed = sum(1 for a in answers if a.get('background_task_completed'))
        tasks_failed = total - tasks_completed

        # Повторные попытки
        total_retries = sum((a.get('retry_count') or 0) for a in answers)

        output.append("─" * 75)
        output.append("📈 СВОДКА ПО ОБРАБОТКЕ:")
        output.append(f"   AI Анализ:          {with_analysis}/{total} ({int(with_analysis/total*100) if total > 0 else 0}%)")
        output.append(f"   Векторизация:       ✅{vectorization_success} ❌{vectorization_failed} ⏳{vectorization_pending}")
        output.append(f"   Digital Personality: ✅{dp_success} ❌{dp_failed} ⏳{dp_pending}")
        output.append(f"   Background Tasks:   ✅{tasks_completed} ❌{tasks_failed}")
        if total_retries > 0:
            output.append(f"   Повторные попытки:  🔄{total_retries}")

        # Медленные операции
        slow_operations = [a for a in answers if a['analysis_delay_sec'] and a['analysis_delay_sec'] > 10]
        if slow_operations:
            output.append("")
            output.append(f"⚠️  Медленных операций (>10s): {len(slow_operations)}")

        # ✅ Детализация ошибок векторизации
        vectorization_errors = [a for a in answers if a.get('vectorization_status') == 'failed']
        if vectorization_errors:
            output.append("")
            output.append(f"❌ Ошибки векторизации ({len(vectorization_errors)}):")
            for a in vectorization_errors[:3]:  # Показываем первые 3
                error = a.get('vectorization_error', 'Unknown')[:50]
                output.append(f"   - Answer #{a['answer_id']}: {error}...")

        # ✅ Детализация ошибок DP
        dp_errors = [a for a in answers if a.get('dp_update_status') == 'failed']
        if dp_errors:
            output.append("")
            output.append(f"❌ Ошибки Digital Personality ({len(dp_errors)}):")
            for a in dp_errors[:3]:  # Показываем первые 3
                error = a.get('dp_update_error', 'Unknown')[:50]
                output.append(f"   - Answer #{a['answer_id']}: {error}...")

        # Ошибки AI анализа
        failed = [a for a in answers if not a['analysis_id']]
        if failed:
            output.append("")
            output.append(f"❌ AI анализ не выполнен ({len(failed)}):")
            for a in failed[:5]:  # Показываем первые 5
                output.append(f"   - Answer #{a['answer_id']}: {a['question_json_id']}")

        output.append("=" * 75)

        return "\n".join(output)

    async def monitor(self, hours: int = 1, user_id: int = None, watch: bool = False):
        """Запустить мониторинг"""

        if watch:
            print("🔄 Режим real-time мониторинга (обновление каждые 10 сек)")
            print("   Нажмите Ctrl+C для выхода\n")

            try:
                while True:
                    # Очищаем экран
                    os.system('clear' if os.name != 'nt' else 'cls')

                    # Получаем данные
                    answers = await self.get_recent_answers(hours, user_id)

                    # Собираем user_ids для проверки Qdrant
                    user_ids = list(set(a['user_id'] for a in answers))
                    qdrant_info = await self.check_qdrant_updates(user_ids)

                    # Показываем отчет
                    report = self.format_monitor_report(answers, qdrant_info)
                    print(report)
                    print(f"\n⏰ Обновлено: {datetime.now().strftime('%H:%M:%S')}")

                    # Ждем
                    await asyncio.sleep(10)

            except KeyboardInterrupt:
                print("\n\n✋ Мониторинг остановлен")
        else:
            # Одноразовый отчет
            answers = await self.get_recent_answers(hours, user_id)
            user_ids = list(set(a['user_id'] for a in answers))
            qdrant_info = await self.check_qdrant_updates(user_ids)

            report = self.format_monitor_report(answers, qdrant_info)
            print(report)


async def main():
    """Точка входа"""

    import argparse

    parser = argparse.ArgumentParser(description="Мониторинг онбординга")
    parser.add_argument("--hours", type=int, default=1, help="Период в часах (default: 1)")
    parser.add_argument("--user", type=int, help="ID пользователя (опционально)")
    parser.add_argument("--watch", action="store_true", help="Real-time мониторинг")

    args = parser.parse_args()

    monitor = OnboardingMonitor()
    await monitor.monitor(hours=args.hours, user_id=args.user, watch=args.watch)


if __name__ == "__main__":
    asyncio.run(main())
