"""
Menu and Chat Handlers Mixin - извлечено из selfology_controller.py

Содержит:
- Menu handlers (callback_main_menu, callback_help, callback_profile)
- GDPR handlers (callback_gdpr_*)
- Chat handlers (cmd_chat, handle_chat_message, etc)
"""

import logging
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from selfology_bot.bot.states import ChatStates

logger = logging.getLogger(__name__)


class MenuChatHandlersMixin:
    """
    Mixin для menu и chat handlers.
    
    Зависимости:
    - self.messages: MessageService
    - self.chat_coach: ChatCoachService
    """

    async def callback_main_menu(self, callback: CallbackQuery, state: FSMContext):
        """Главное меню"""

        user_name = callback.from_user.full_name or "Друг"
        await self._show_main_menu_callback(callback, user_name)
        await state.clear()

    async def callback_help(self, callback: CallbackQuery):
        """Help callback"""

        text = self.messages.get_message('help', 'ru', 'general')
        keyboard = self.messages.get_keyboard('back_to_menu', 'ru')

        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode='HTML')

    async def callback_profile(self, callback: CallbackQuery):
        """Profile callback - показать профиль через кнопку"""

        telegram_id = str(callback.from_user.id)
        logger.info(f"📊 Profile callback from user {telegram_id}")

        # Получаем данные профиля из базы данных
        profile_data = await self.user_dao.get_user_profile_data(telegram_id)

        if profile_data:
            text = self.messages.get_message('user_profile', 'ru', 'general', **profile_data)
            keyboard = self.messages.get_keyboard('profile_actions', 'ru')

            await callback.message.edit_text(text, reply_markup=keyboard, parse_mode='HTML')
        else:
            # Пользователь не найден
            text = self.messages.get_message('access_denied', 'ru', 'errors',
                access_reason="Профиль не найден",
                action_suggestion="Пройдите регистрацию с помощью /start"
            )
            keyboard = self.messages.get_keyboard('back_to_menu', 'ru')

            await callback.message.edit_text(text, reply_markup=keyboard, parse_mode='HTML')

    async def callback_gdpr_details(self, callback: CallbackQuery):
        """Подробности GDPR"""

        text = self.messages.get_message('gdpr_consent', 'ru', 'onboarding')
        keyboard = self.messages.get_keyboard('gdpr_consent', 'ru')

        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode='HTML')

    async def callback_gdpr_accept(self, callback: CallbackQuery, state: FSMContext):
        """Согласие на GDPR"""

        telegram_id = str(callback.from_user.id)
        logger.info(f"✅ User {telegram_id} accepted GDPR")

        # 🗄 Сохраняем согласие в базу данных selfology
        success = await self.user_dao.update_gdpr_consent(telegram_id, True)

        if success:
            text = self.messages.get_message('gdpr_accepted', 'ru', 'onboarding')
            keyboard = self.messages.get_keyboard('start_assessment', 'ru')

            await callback.message.edit_text(text, reply_markup=keyboard, parse_mode='HTML')
            await state.set_state(OnboardingStates.assessment_intro)
        else:
            # Ошибка сохранения
            text = self.messages.get_message('database_error', 'ru', 'errors')
            keyboard = self.messages.get_keyboard('error_actions', 'ru')

            await callback.message.edit_text(text, reply_markup=keyboard, parse_mode='HTML')

    async def callback_gdpr_decline(self, callback: CallbackQuery, state: FSMContext):
        """Отказ от GDPR"""

        user_id = callback.from_user.id
        logger.info(f"❌ User {user_id} declined GDPR")

        text = self.messages.get_message('gdpr_declined', 'ru', 'onboarding')
        keyboard = self.messages.get_keyboard('gdpr_declined', 'ru')

        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode='HTML')
        await state.clear()

    async def cmd_chat(self, message: Message, state: FSMContext):
        """Команда /chat - начать разговор с AI-коучем"""

        telegram_id = str(message.from_user.id)
        current_state = await state.get_state()
        logger.info(f"💬 Chat requested by user {telegram_id} (current_state: {current_state})")

        try:
            # Уведомление о переключении режима (если был в онбординге)
            if current_state == OnboardingStates.waiting_for_answer:
                switch_message = self.messages.get_message('context_switch_to_chat', 'ru', 'general')
                await message.answer(switch_message, parse_mode='HTML')

            # Очищаем старое состояние и устанавливаем новое
            await state.clear()

            # Стартуем чат сессию
            result = await self.chat_coach.start_chat_session(telegram_id)

            if result.success:
                await message.answer(result.response_text, parse_mode='HTML')
                await state.set_state(ChatStates.active)
                logger.info(f"✅ Chat session started for user {telegram_id}")
            else:
                error_text = f"❌ Не удалось начать чат: {result.message}"
                await message.answer(error_text)
                logger.error(f"Failed to start chat for user {telegram_id}: {result.message}")

        except Exception as e:
            logger.error(f"Error starting chat for user {telegram_id}: {e}", exc_info=True)
            await message.answer("❌ Произошла ошибка при запуске чата. Попробуйте позже.")

    async def callback_start_chat(self, callback: CallbackQuery, state: FSMContext):
        """Callback для кнопки 'Чат с AI-коучем'"""

        telegram_id = str(callback.from_user.id)
        logger.info(f"💬 Chat started via button by user {telegram_id}")

        try:
            # Стартуем чат сессию
            result = await self.chat_coach.start_chat_session(telegram_id)

            if result.success:
                await callback.message.edit_text(result.response_text, parse_mode='HTML')
                await state.set_state(ChatStates.active)
                logger.info(f"✅ Chat session started for user {telegram_id}")
            else:
                error_text = f"❌ Не удалось начать чат: {result.message}"
                await callback.message.edit_text(error_text)
                logger.error(f"Failed to start chat for user {telegram_id}: {result.message}")

        except Exception as e:
            logger.error(f"Error starting chat for user {telegram_id}: {e}", exc_info=True)
            await callback.answer("❌ Ошибка при запуске чата", show_alert=True)

    async def handle_chat_message(self, message: Message, state: FSMContext):
        """Обработчик сообщений в активном чате"""

        telegram_id = str(message.from_user.id)
        user_message = message.text

        logger.info(f"💬 Chat message from user {telegram_id}: {user_message[:50]}...")

        try:
            # Обрабатываем сообщение через Chat Coach
            result = await self.chat_coach.process_message(telegram_id, user_message)

            if result.success:
                response_text = result.response_text

                # Добавляем информацию об инсайтах если есть
                if result.insights_detected:
                    insights_info = f"\n\n💡 <i>Обнаружено инсайтов: {len(result.insights_detected)}</i>"
                    response_text += insights_info

                # Добавляем информацию об обновлении профиля
                if result.personality_updates:
                    updates_info = f"\n📈 <i>Профиль обновлен ({len(result.personality_updates)} характеристик)</i>"
                    response_text += updates_info

                # Разбиваем на части если превышает лимит Telegram (4096 символов)
                await self._send_long_message(message, response_text)
                logger.info(f"✅ Chat response sent to user {telegram_id} ({result.processing_time:.2f}s)")
            else:
                error_text = f"❌ Ошибка обработки: {result.message}"
                await message.answer(error_text)
                logger.error(f"Failed to process message for user {telegram_id}: {result.message}")

        except Exception as e:
            logger.error(f"Error processing chat message for user {telegram_id}: {e}", exc_info=True)
            await message.answer("❌ Произошла ошибка. Попробуйте еще раз.")

    async def callback_coming_soon(self, callback: CallbackQuery):
        """Заглушка для функций в разработке"""

        feature_map = {
            'assessments': 'Психологические оценки',
            'profile': 'Профиль пользователя',
            'goals': 'Цели и планы',
            'diary': 'Дневник наблюдений',
            'settings': 'Настройки'
        }

        feature_name = feature_map.get(callback.data, 'Эта функция')

        text = self.messages.get_message(
            'coming_soon', 'ru', 'general',
            feature_name=feature_name,
            expected_date="в ближайшие дни"
        )
        keyboard = self.messages.get_keyboard('back_to_menu', 'ru')

        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode='HTML')

    async def handle_unknown(self, message: Message, state: FSMContext):
        """
        Обработчик неизвестных команд

        ОПТИМИЗАЦИЯ: С Redis FSM состояния должны сохраняться между перезапусками,
        но оставляем fallback для надежности (проверка БД на активную сессию)
        """
        current_state = await state.get_state()
        telegram_id = message.from_user.id
        logger.warning(
            f"⚠️ Unknown command from user {telegram_id}: '{message.text[:50]}...' "
            f"(FSM state: {current_state})"
        )

        # SAFETY FALLBACK: Проверяем БД только если FSM state отсутствует
        # С Redis FSM это должно происходить редко, поэтому не влияет на производительность
        if not current_state:
            logger.debug(f"🔍 FSM state empty, checking database for active session...")

            try:
                active_session = await self.onboarding_dao.get_active_session(int(telegram_id))

                if active_session and active_session.get('status') == 'active':
                    logger.info(
                        f"🔄 [FALLBACK] Detected active onboarding session in DB for {telegram_id}, "
                        f"restoring FSM state"
                    )
                    # Восстанавливаем FSM состояние из БД
                    await state.set_state(OnboardingStates.waiting_for_answer)
                    # Обрабатываем как ответ на онбординг
                    await self.handle_onboarding_answer(message, state)
                    return

            except Exception as e:
                logger.error(f"❌ Error checking database fallback: {e}")

        # Показываем стандартное сообщение о неизвестной команде
        text = self.messages.get_message(
            'unknown_command', 'ru', 'errors',
            command=message.text
        )
        keyboard = self.messages.get_keyboard('back_to_menu', 'ru')

        await message.answer(text, reply_markup=keyboard, parse_mode='HTML')

