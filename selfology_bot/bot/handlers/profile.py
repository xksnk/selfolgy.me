"""
Handler for /profile command - показывает детальный профиль онбординга
"""

from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
import asyncio
import subprocess

from ...database.service import DatabaseService
from ...database.onboarding_dao import OnboardingDAO

router = Router()


@router.message(Command("profile"))
async def cmd_profile(message: Message):
    """
    Показать детальный профиль онбординга пользователя

    Запускает onboarding_profiler.py и отправляет результат в Telegram
    """

    user_id = message.from_user.id

    # Отправляем сообщение что обрабатываем
    processing_msg = await message.answer("🔬 Анализирую ваш профиль онбординга...")

    try:
        # Запускаем профилировщик
        result = subprocess.run(
            ["python", "onboarding_profiler.py", str(user_id)],
            capture_output=True,
            text=True,
            timeout=10,
            cwd="/home/ksnk/n8n-enterprise/projects/selfology"
        )

        if result.returncode == 0:
            # Профилировщик успешно выполнился
            output = result.stdout

            # Удаляем ANSI escape codes для чистого текста
            import re
            clean_output = re.sub(r'\x1b\[[0-9;]*m', '', output)

            # Telegram message limit - 4096 chars
            if len(clean_output) > 4000:
                # Разбиваем на части
                parts = []
                current_part = ""

                for line in clean_output.split('\n'):
                    if len(current_part) + len(line) + 1 > 4000:
                        parts.append(current_part)
                        current_part = line + '\n'
                    else:
                        current_part += line + '\n'

                if current_part:
                    parts.append(current_part)

                # Отправляем первую часть (редактируем processing_msg)
                await processing_msg.edit_text(
                    f"```\n{parts[0]}\n```",
                    parse_mode="Markdown"
                )

                # Отправляем остальные части
                for part in parts[1:]:
                    await message.answer(
                        f"```\n{part}\n```",
                        parse_mode="Markdown"
                    )
            else:
                # Отправляем в одном сообщении
                await processing_msg.edit_text(
                    f"```\n{clean_output}\n```",
                    parse_mode="Markdown"
                )
        else:
            # Ошибка выполнения
            error_text = result.stderr or "Unknown error"
            await processing_msg.edit_text(
                f"❌ Ошибка при генерации профиля:\n```\n{error_text[:500]}\n```",
                parse_mode="Markdown"
            )

    except subprocess.TimeoutExpired:
        await processing_msg.edit_text(
            "⏱ Таймаут: профилировщик работал слишком долго"
        )

    except Exception as e:
        await processing_msg.edit_text(
            f"❌ Ошибка: {str(e)[:200]}"
        )


@router.message(Command("debug"))
async def cmd_debug(message: Message):
    """
    Быстрая диагностика - только ключевые метрики
    """

    user_id = message.from_user.id

    try:
        # Инициализируем DAO
        db_service = DatabaseService()
        await db_service.init()
        onboarding_dao = OnboardingDAO(db_service)

        # Получаем активную сессию
        from sqlalchemy import text
        async with db_service.get_connection() as conn:
            result = await conn.fetchrow("""
                SELECT
                    id, status,
                    questions_asked, questions_answered,
                    started_at
                FROM selfology.onboarding_sessions
                WHERE user_id = $1 AND status = 'active'
                ORDER BY started_at DESC
                LIMIT 1
            """, user_id)

            if not result:
                await message.answer("ℹ️ Нет активной сессии онбординга")
                return

            # Подсчитываем ответы
            answers_result = await conn.fetchrow("""
                SELECT COUNT(*) as total,
                       SUM(CASE WHEN analysis_status = 'analyzed' THEN 1 ELSE 0 END) as analyzed
                FROM selfology.user_answers_new
                WHERE session_id = $1
            """, result['id'])

            # Формируем отчет
            debug_text = f"""
🔍 <b>Быстрая диагностика</b>

📋 <b>Сессия #{result['id']}</b>
   • Статус: {result['status']}
   • Вопросов задано: {result['questions_asked']}
   • Ответов дано: {result['questions_answered']}
   • Старт: {result['started_at'].strftime('%d.%m.%Y %H:%M')}

💬 <b>Ответы:</b>
   • Всего: {answers_result['total'] or 0}
   • Проанализировано: {answers_result['analyzed'] or 0}
   • Ожидают: {(answers_result['total'] or 0) - (answers_result['analyzed'] or 0)}

💡 Используйте /profile для детального отчета
"""

            await message.answer(debug_text, parse_mode="HTML")

    except Exception as e:
        await message.answer(f"❌ Ошибка: {str(e)[:200]}")
