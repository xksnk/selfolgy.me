"""
Chat Handlers - обработчики AI чата

Команды:
- /chat - начать разговор с AI-коучем
- callback_start_chat - кнопка запуска чата
- handle_chat_message - обработка сообщений в активном чате
"""

import logging
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from telegram_interface.utilities.message_splitter import send_long_message

logger = logging.getLogger(__name__)


class ChatHandlers:
    """Обработчики AI чата"""

    @staticmethod
    async def cmd_chat(
        message: Message,
        state: FSMContext,
        chat_coach,
        messages,
        onboarding_states,
        chat_states
    ):
        """Команда /chat - начать разговор с AI-коучем"""
        telegram_id = str(message.from_user.id)
        current_state = await state.get_state()
        logger.info(f"💬 Chat requested by user {telegram_id} (current_state: {current_state})")

        try:
            # Уведомление о переключении режима (если был в онбординге)
            if current_state == onboarding_states.waiting_for_answer:
                switch_message = messages.get_message('context_switch_to_chat', 'ru', 'general')
                await message.answer(switch_message, parse_mode='HTML')

            # Очищаем старое состояние
            await state.clear()

            # Стартуем чат сессию
            result = await chat_coach.start_chat_session(telegram_id)

            if result.success:
                await message.answer(result.response_text, parse_mode='HTML')
                await state.set_state(chat_states.active)
                logger.info(f"✅ Chat session started for user {telegram_id}")
            else:
                error_text = f"❌ Не удалось начать чат: {result.message}"
                await message.answer(error_text)
                logger.error(f"Failed to start chat for user {telegram_id}: {result.message}")

        except Exception as e:
            logger.error(f"Error starting chat for user {telegram_id}: {e}", exc_info=True)
            await message.answer("❌ Произошла ошибка при запуске чата. Попробуйте позже.")

    @staticmethod
    async def callback_start_chat(
        callback: CallbackQuery,
        state: FSMContext,
        chat_coach,
        chat_states
    ):
        """Callback для кнопки 'Чат с AI-коучем'"""
        telegram_id = str(callback.from_user.id)
        logger.info(f"💬 Chat started via button by user {telegram_id}")

        try:
            # Стартуем чат сессию
            result = await chat_coach.start_chat_session(telegram_id)

            if result.success:
                await callback.message.edit_text(result.response_text, parse_mode='HTML')
                await state.set_state(chat_states.active)
                logger.info(f"✅ Chat session started for user {telegram_id}")
            else:
                error_text = f"❌ Не удалось начать чат: {result.message}"
                await callback.message.edit_text(error_text)
                logger.error(f"Failed to start chat for user {telegram_id}: {result.message}")

        except Exception as e:
            logger.error(f"Error starting chat for user {telegram_id}: {e}", exc_info=True)
            await callback.answer("❌ Ошибка при запуске чата", show_alert=True)

    @staticmethod
    async def handle_chat_message(
        message: Message,
        state: FSMContext,
        chat_coach
    ):
        """Обработчик сообщений в активном чате"""
        telegram_id = str(message.from_user.id)
        user_message = message.text

        logger.info(f"💬 Chat message from user {telegram_id}: {user_message[:50]}...")

        try:
            # Обрабатываем через Chat Coach
            result = await chat_coach.process_message(telegram_id, user_message)

            if result.success:
                response_text = result.response_text

                # Добавляем информацию об инсайтах
                if result.insights_detected:
                    insights_info = f"\n\n💡 <i>Обнаружено инсайтов: {len(result.insights_detected)}</i>"
                    response_text += insights_info

                # Информация об обновлении профиля
                if result.personality_updates:
                    updates_info = f"\n📈 <i>Профиль обновлен ({len(result.personality_updates)} характеристик)</i>"
                    response_text += updates_info

                # Разбиваем на части если длинное
                await send_long_message(message, response_text)
                logger.info(f"✅ Chat response sent to user {telegram_id} ({result.processing_time:.2f}s)")
            else:
                error_text = f"❌ Ошибка обработки: {result.message}"
                await message.answer(error_text)
                logger.error(f"Failed to process message for user {telegram_id}: {result.message}")

        except Exception as e:
            logger.error(f"Error processing chat message for user {telegram_id}: {e}", exc_info=True)
            await message.answer("❌ Произошла ошибка. Попробуйте еще раз.")
