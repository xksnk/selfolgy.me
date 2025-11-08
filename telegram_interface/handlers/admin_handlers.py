"""
Admin Handlers - административные команды

Команды (только для админа):
- /debug_on - включить debug режим
- /debug_off - выключить debug режим
- /debug_status - статус debug режима  
- /reload_templates - перезагрузить шаблоны сообщений
- /onboarding_profile - детальный профиль онбординга пользователя
"""

import logging
import subprocess
import re
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from selfology_bot.messages import get_message_service

logger = logging.getLogger(__name__)

ADMIN_USER_ID = "98005572"
DEBUG_MESSAGES = False  # Global state


class AdminHandlers:
    """Обработчики административных команд"""

    @staticmethod
    async def cmd_debug_on(message: Message, messages_service_setter):
        """Включить debug режим (только для админа)"""
        if str(message.from_user.id) != ADMIN_USER_ID:
            await message.answer("❌ Команда доступна только администратору")
            return

        global DEBUG_MESSAGES
        DEBUG_MESSAGES = True
        messages_service_setter(get_message_service(debug_mode=True))

        await message.answer(
            "🔧 <b>DEBUG режим ВКЛЮЧЕН</b>\n\n"
            "Теперь все сообщения будут содержать:\n"
            "• MESSAGE_ID\n"
            "• Имя файла шаблона\n\n"
            "Для отключения: /debug_off",
            parse_mode='HTML'
        )
        logger.info("🔧 Debug mode ENABLED by admin")

    @staticmethod
    async def cmd_debug_off(message: Message, messages_service_setter):
        """Выключить debug режим (только для админа)"""
        if str(message.from_user.id) != ADMIN_USER_ID:
            await message.answer("❌ Команда доступна только администратору")
            return

        global DEBUG_MESSAGES
        DEBUG_MESSAGES = False
        messages_service_setter(get_message_service(debug_mode=False))

        await message.answer(
            "✅ <b>DEBUG режим ОТКЛЮЧЕН</b>\n\n"
            "Сообщения теперь отображаются без отладочной информации.\n\n"
            "Для включения: /debug_on",
            parse_mode='HTML'
        )
        logger.info("✅ Debug mode DISABLED by admin")

    @staticmethod
    async def cmd_debug_status(message: Message, messages, orchestrator):
        """Статус debug режима (только для админа)"""
        if str(message.from_user.id) != ADMIN_USER_ID:
            await message.answer("❌ Команда доступна только администратору")
            return

        status = "ВКЛЮЧЕН" if DEBUG_MESSAGES else "ОТКЛЮЧЕН"
        emoji = "🔧" if DEBUG_MESSAGES else "✅"

        # Статистика сообщений
        available_locales = messages.get_available_locales()
        available_categories = messages.get_available_categories('ru')

        # Observability - статус background tasks
        tasks_status = orchestrator.get_background_tasks_status()

        debug_text = f"""
{emoji} <b>DEBUG статус: {status}</b>

📊 <b>Статистика шаблонов:</b>
• Языки: {len(available_locales)} ({', '.join(available_locales)})
• Категории: {len(available_categories)} ({', '.join(available_categories)})

🔬 <b>Background Tasks (Orchestrator):</b>
• Всего tasks: {tasks_status['total_tasks']}
• Активных: {tasks_status['active_tasks']}
• Завершено: {tasks_status['completed_tasks']}
• Отменено: {tasks_status['cancelled_tasks']}
• С ошибками: {tasks_status['failed_tasks']}
• Shutdown: {'да' if tasks_status['shutdown_initiated'] else 'нет'}

🔧 <b>Управление:</b>
/debug_on - включить DEBUG режим
/debug_off - отключить DEBUG режим
/debug_status - этот статус

<i>DEBUG режим показывает MESSAGE_ID в каждом сообщении для удобной отладки workflow.</i>
        """

        await message.answer(debug_text, parse_mode='HTML')
        logger.info(f"📊 Debug status checked by admin: {status}")

    @staticmethod
    async def cmd_reload_templates(message: Message, messages):
        """Перезагрузить шаблоны сообщений (только для админа)"""
        if str(message.from_user.id) != ADMIN_USER_ID:
            await message.answer("❌ Команда доступна только администратору")
            return

        try:
            # Перезагружаем шаблоны
            messages.reload_templates()

            # Статистика после перезагрузки
            available_locales = messages.get_available_locales()
            available_categories = messages.get_available_categories('ru')

            reload_text = f"""
🔄 <b>Шаблоны перезагружены!</b>

📊 <b>Загружено:</b>
• Языки: {len(available_locales)} ({', '.join(available_locales)})
• Категории: {len(available_categories)} ({', '.join(available_categories)})

✅ Все изменения в JSON файлах теперь активны!

🔧 <b>Admin команды:</b>
/reload_templates - перезагрузить шаблоны
/debug_status - статус системы
            """

            await message.answer(reload_text, parse_mode='HTML')
            logger.info("🔄 Templates reloaded by admin")

        except Exception as e:
            await message.answer(f"❌ Ошибка перезагрузки шаблонов: {e}")
            logger.error(f"Error reloading templates: {e}")

    @staticmethod
    async def cmd_onboarding_profile(message: Message):
        """
        Команда /onboarding_profile - детальный профиль онбординга
        
        Запускает onboarding_profiler.py и показывает результат в Telegram
        """
        user_id = message.from_user.id
        logger.info(f"🔬 Onboarding profile requested by user {user_id}")

        # Отправляем сообщение что обрабатываем
        processing_msg = await message.answer("🔬 Анализирую ваш профиль онбординга...")

        try:
            # Запускаем профилировщик через venv
            result = subprocess.run(
                ["bash", "-c", f"source venv/bin/activate && python onboarding_profiler.py {user_id}"],
                capture_output=True,
                text=True,
                timeout=15,
                cwd="/home/ksnk/n8n-enterprise/projects/selfology"
            )

            if result.returncode == 0:
                # Профилировщик успешно выполнился
                output = result.stdout

                # Удаляем ANSI escape codes для чистого текста
                clean_output = re.sub(r'\x1b\[[0-9;]*m', '', output)

                # Разбиваем по строкам для контроля размера
                lines = clean_output.split('\n')
                parts = []
                current_part = ""

                for line in lines:
                    # Проверяем не превысит ли добавление строки лимит
                    if len(current_part) + len(line) + 1 > 3900:  # Оставляем запас
                        if current_part:
                            parts.append(current_part)
                        current_part = line + '\n'
                    else:
                        current_part += line + '\n'

                if current_part:
                    parts.append(current_part)

                # Создаем клавиатуру с кнопкой для обработки orphaned ответов
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(
                        text="🔄 Обработать пропущенные ответы",
                        callback_data=f"process_orphaned:{user_id}"
                    )]
                ])

                # Отправляем первую часть (редактируем processing_msg)
                if len(parts) > 0:
                    await processing_msg.edit_text(
                        f"```\n{parts[0]}```",
                        parse_mode="Markdown"
                    )

                    # Отправляем остальные части
                    for i, part in enumerate(parts[1:], 1):
                        # Добавляем клавиатуру только к последнему сообщению
                        reply_markup = keyboard if i == len(parts) - 1 else None
                        await message.answer(
                            f"```\n{part}```",
                            parse_mode="Markdown",
                            reply_markup=reply_markup
                        )

                    # Если была только одна часть, добавляем клавиатуру отдельно
                    if len(parts) == 1:
                        await message.answer(
                            "ℹ️ Используйте кнопку ниже для обработки ответов без AI анализа:",
                            reply_markup=keyboard
                        )
            else:
                # Ошибка выполнения
                error_text = result.stderr or "Unknown error"
                await processing_msg.edit_text(
                    f"❌ Ошибка при генерации профиля:\n```\n{error_text[:500]}```",
                    parse_mode="Markdown"
                )

        except subprocess.TimeoutExpired:
            await processing_msg.edit_text("⏱ Таймаут: профилировщик работал слишком долго")

        except Exception as e:
            await processing_msg.edit_text(f"❌ Ошибка: {str(e)[:200]}")
