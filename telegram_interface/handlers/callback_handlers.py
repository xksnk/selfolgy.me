"""
Callback Handlers - обработчики callback кнопок

Callbacks:
- GDPR consent (accept/decline/details)
- Main menu navigation
- Coming soon features
- Continue/end onboarding
- Process orphaned answers
"""

import logging
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from selfology_bot.messages import get_message, get_keyboard

logger = logging.getLogger(__name__)


class CallbackHandlers:
    """Обработчики callback кнопок"""

    @staticmethod
    async def callback_gdpr_details(callback: CallbackQuery):
        """Показать детали GDPR"""
        text = get_message('gdpr_details', 'ru', 'gdpr')
        keyboard = get_keyboard('gdpr_details_back', 'ru')

        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode='HTML')
        await callback.answer()

    @staticmethod
    async def callback_gdpr_accept(callback: CallbackQuery, state: FSMContext, user_dao, show_main_menu_func):
        """Принять GDPR согласие"""
        telegram_id = str(callback.from_user.id)
        user_name = callback.from_user.full_name or "Друг"

        logger.info(f"✅ User {telegram_id} accepted GDPR")

        # Сохраняем согласие в БД
        await user_dao.update_user_consent(telegram_id, True)

        # Показываем главное меню
        await show_main_menu_func(callback, user_name)
        await callback.answer("✅ Согласие принято")
        await state.clear()

    @staticmethod
    async def callback_gdpr_decline(callback: CallbackQuery, state: FSMContext):
        """Отклонить GDPR согласие"""
        telegram_id = str(callback.from_user.id)
        logger.info(f"❌ User {telegram_id} declined GDPR")

        text = get_message('gdpr_declined', 'ru', 'gdpr')
        await callback.message.edit_text(text, parse_mode='HTML')
        await callback.answer("Согласие отклонено")
        await state.clear()

    @staticmethod
    async def callback_main_menu(callback: CallbackQuery, state: FSMContext, show_main_menu_func):
        """Вернуться в главное меню"""
        user_name = callback.from_user.full_name or "Друг"
        await show_main_menu_func(callback, user_name)
        await callback.answer()
        await state.clear()

    @staticmethod
    async def callback_help(callback: CallbackQuery, messages):
        """Показать справку"""
        text = messages.get_message('help', 'ru', 'general')
        keyboard = messages.get_keyboard('back_to_menu', 'ru')

        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode='HTML')
        await callback.answer()

    @staticmethod
    async def callback_profile(callback: CallbackQuery, user_dao, messages):
        """Показать профиль"""
        telegram_id = str(callback.from_user.id)
        logger.info(f"📊 Profile requested by user {telegram_id}")

        profile_data = await user_dao.get_user_profile_data(telegram_id)

        if profile_data:
            text = messages.get_message('user_profile', 'ru', 'general', **profile_data)
            keyboard = messages.get_keyboard('profile_actions', 'ru')

            await callback.message.edit_text(text, reply_markup=keyboard, parse_mode='HTML')
        else:
            text = messages.get_message('access_denied', 'ru', 'errors',
                access_reason="Профиль не найден",
                action_suggestion="Пройдите регистрацию с помощью /start"
            )
            keyboard = messages.get_keyboard('back_to_menu', 'ru')

            await callback.message.edit_text(text, reply_markup=keyboard, parse_mode='HTML')

        await callback.answer()

    @staticmethod
    async def callback_coming_soon(callback: CallbackQuery):
        """Заглушка для функций в разработке"""
        feature_map = {
            'assessments': 'Психологические оценки',
            'profile': 'Профиль пользователя',
            'goals': 'Цели и планы',
            'diary': 'Дневник наблюдений',
            'settings': 'Настройки'
        }

        feature_name = feature_map.get(callback.data, 'Эта функция')

        await callback.answer(
            f"🚧 {feature_name} скоро появится!\n\nМы работаем над этой функцией.",
            show_alert=True
        )

    @staticmethod
    async def callback_continue_onboarding(
        callback: CallbackQuery,
        state: FSMContext,
        orchestrator,
        messages,
        onboarding_states
    ):
        """Продолжить онбординг после завершения сессии"""
        from telegram_interface.utilities.question_display import show_onboarding_question

        telegram_id = str(callback.from_user.id)
        logger.info(f"▶️ Continue onboarding requested by user {telegram_id}")

        try:
            await callback.answer("▶️ Продолжаем онбординг")

            # Создаем новую сессию
            result = await orchestrator.start_onboarding(int(telegram_id))

            question = result['question']
            session_info = result['session_info']

            # Показываем первый вопрос новой сессии
            await show_onboarding_question(
                question, session_info, telegram_id, callback, messages, is_edit=True
            )
            await state.set_state(onboarding_states.waiting_for_answer)

        except Exception as e:
            logger.error(f"❌ Error continuing onboarding for {telegram_id}: {e}")
            await callback.answer("❌ Ошибка продолжения онбординга")

    @staticmethod
    async def callback_end_onboarding(callback: CallbackQuery, state: FSMContext, onboarding_dao):
        """Завершить процесс онбординга полностью"""
        telegram_id = str(callback.from_user.id)
        logger.info(f"🏁 End onboarding requested by user {telegram_id}")

        try:
            # Завершаем активную сессию
            active_session = await onboarding_dao.get_active_session(int(telegram_id))

            if active_session:
                session_id = active_session['id']
                await onboarding_dao.complete_session(session_id)

                questions_answered = active_session.get('questions_answered', 0)

                message_text = get_message(
                    'session_completed',
                    locale='ru',
                    category='onboarding',
                    questions_answered=questions_answered
                )
                keyboard = get_keyboard('session_completed', locale='ru')

                await callback.answer("🏁 Сессия завершена")
                await callback.message.edit_text(
                    message_text,
                    parse_mode='HTML',
                    reply_markup=keyboard
                )
            else:
                await callback.answer("❌ Нет активной сессии")

            await state.clear()

        except Exception as e:
            logger.error(f"❌ Error ending onboarding for {telegram_id}: {e}")
            await callback.answer("❌ Ошибка завершения онбординга")

    @staticmethod
    async def callback_process_orphaned(callback: CallbackQuery):
        """Обработать пропущенные ответы (вызывает external script)"""
        user_id_str = callback.data.split(":")[1]
        logger.info(f"🔄 Process orphaned answers requested for user {user_id_str}")

        await callback.answer("🔄 Запускаю обработку...")

        try:
            import subprocess

            # Запускаем скрипт обработки orphaned ответов
            result = subprocess.run(
                ["bash", "-c", f"source venv/bin/activate && python process_orphaned_answers.py {user_id_str}"],
                capture_output=True,
                text=True,
                timeout=30,
                cwd="/home/ksnk/n8n-enterprise/projects/selfology"
            )

            if result.returncode == 0:
                await callback.message.answer("✅ Обработка завершена успешно!")
            else:
                error_text = result.stderr[:200] if result.stderr else "Unknown error"
                await callback.message.answer(f"❌ Ошибка обработки:\n{error_text}")

        except subprocess.TimeoutExpired:
            await callback.message.answer("⏱ Таймаут: обработка заняла слишком много времени")

        except Exception as e:
            await callback.message.answer(f"❌ Ошибка: {str(e)[:200]}")
