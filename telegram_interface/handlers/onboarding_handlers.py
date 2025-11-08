"""
Onboarding Handlers - обработчики процесса онбординга

Команды:
- /onboarding - запуск/продолжение онбординга
- handle_onboarding_answer - обработка ответов пользователя
- callback_skip_question - пропуск вопроса
- callback_end_session - завершение сессии
- callback_flag_question - пометка вопроса (admin)
"""

import logging
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from selfology_bot.messages import get_message, get_keyboard
from telegram_interface.utilities.question_display import show_onboarding_question

logger = logging.getLogger(__name__)

ADMIN_USER_ID = "98005572"


class OnboardingHandlers:
    """Обработчики процесса онбординга"""

    @staticmethod
    async def cmd_onboarding(
        message: Message,
        state: FSMContext,
        orchestrator,
        messages,
        onboarding_states,
        chat_states
    ):
        """Команда /onboarding - запуск/продолжение онбординга"""
        telegram_id = str(message.from_user.id)
        current_state = await state.get_state()
        logger.info(f"🧠 Onboarding requested by user {telegram_id} (current_state: {current_state})")

        try:
            # Проверяем активную сессию
            session = await orchestrator.restore_session_from_db(int(telegram_id))

            if session:
                # Продолжаем существующую сессию
                logger.info(f"▶️ Continuing existing session for user {telegram_id}")
                result = await orchestrator.get_next_question(
                    int(telegram_id),
                    {"question_number": session.get('question_number', 1)}
                )
            else:
                # Создаём новую сессию
                logger.info(f"🚀 Starting NEW session for user {telegram_id}")
                result = await orchestrator.start_onboarding(int(telegram_id))

            # Уведомление о переключении режима (если был в чате)
            if current_state == chat_states.active:
                session_info = result.get('session_info', {})
                switch_message = messages.get_message(
                    'context_switch_to_onboarding', 'ru', 'general',
                    question_number=session_info.get('question_number', 1),
                    total_questions=session_info.get('total_questions', 20)
                )
                await message.answer(switch_message, parse_mode='HTML')

            # Очищаем старое состояние
            await state.clear()

            question = result['question']
            session_info = result['session_info']

            # Показываем вопрос
            await show_onboarding_question(
                question, session_info, telegram_id, message, messages
            )
            await state.set_state(onboarding_states.waiting_for_answer)

        except Exception as e:
            logger.error(f"❌ Error starting onboarding for {telegram_id}: {e}")
            await message.answer(f"❌ Ошибка запуска онбординга: {e}", parse_mode='HTML')

    @staticmethod
    async def handle_onboarding_answer(
        message: Message,
        state: FSMContext,
        orchestrator,
        messages,
        onboarding_states
    ):
        """Обработка ответа пользователя в процессе онбординга"""
        telegram_id = str(message.from_user.id)
        user_answer = message.text

        current_state = await state.get_state()
        logger.info(f"💬 Received answer from user {telegram_id}: {len(user_answer)} chars (state: {current_state})")

        try:
            # Получаем текущую сессию
            session = orchestrator.get_session(int(telegram_id))

            # Если нет в памяти, восстанавливаем из БД
            if not session:
                logger.info(f"🔄 Restoring session from DB for user {telegram_id}")
                session = await orchestrator.restore_session_from_db(int(telegram_id))

            if not session or not session.get('current_question'):
                logger.error(f"❌ No active session for user {telegram_id}")
                await message.answer("❌ Ошибка: нет активной сессии. Начните с /onboarding", parse_mode='HTML')
                return

            current_question_id = session['current_question']['id']
            logger.info(f"📝 Processing answer for question {current_question_id}")

            # Обрабатываем ответ
            result = await orchestrator.process_user_answer(
                int(telegram_id), current_question_id, user_answer
            )

            # Мгновенный фидбек
            quick_insight = result.get("quick_insight", "Принимаю ваш ответ ✅")
            await message.answer(
                f"{quick_insight}\n\n⚡ <i>Анализирую ваш ответ глубже...</i>",
                parse_mode='HTML'
            )

            # Получаем следующий вопрос
            next_result = await orchestrator.get_next_question(
                int(telegram_id), {"question_number": 2}
            )

            if next_result["status"] == "continue":
                # Показываем следующий вопрос
                next_question = next_result["question"]
                session_info = next_result["session_info"]

                await show_onboarding_question(
                    next_question, session_info, telegram_id, message, messages
                )
                await state.set_state(onboarding_states.waiting_for_answer)

            else:
                # Онбординг завершен
                from selfology_bot.database import OnboardingDAO
                onboarding_dao = orchestrator.onboarding_dao
                active_session = await onboarding_dao.get_active_session(int(telegram_id))
                questions_answered = active_session.get('questions_answered', 0) if active_session else 0

                message_text = get_message(
                    'session_completed',
                    locale='ru',
                    category='onboarding',
                    questions_answered=questions_answered
                )
                keyboard = get_keyboard('session_completed', locale='ru')

                await message.answer(message_text, parse_mode='HTML', reply_markup=keyboard)
                await state.set_state(onboarding_states.onboarding_complete)

        except Exception as e:
            logger.error(f"❌ Error processing answer from {telegram_id}: {e}")
            await message.answer(f"❌ Ошибка обработки ответа: {e}", parse_mode='HTML')

    @staticmethod
    async def callback_skip_question(
        callback: CallbackQuery,
        state: FSMContext,
        orchestrator,
        messages,
        onboarding_states
    ):
        """Пропустить текущий вопрос"""
        telegram_id = str(callback.from_user.id)
        logger.info(f"⏭️ Skip question requested by user {telegram_id}")

        try:
            await callback.answer("⏭️ Вопрос пропущен")

            # Записываем факт пропуска
            session = orchestrator.get_session(int(telegram_id))
            if session and session.get("current_question"):
                current_question_id = session["current_question"]["id"]
                await orchestrator.record_skipped_question(int(telegram_id), current_question_id)

            # Следующий вопрос
            next_result = await orchestrator.get_next_question(
                int(telegram_id), {"question_number": 2}
            )

            if next_result["status"] == "continue":
                next_question = next_result["question"]
                session_info = next_result["session_info"]

                await show_onboarding_question(
                    next_question, session_info, telegram_id, callback, messages, is_edit=True
                )
                await state.set_state(onboarding_states.waiting_for_answer)
            else:
                # Онбординг завершен
                onboarding_dao = orchestrator.onboarding_dao
                active_session = await onboarding_dao.get_active_session(int(telegram_id))
                questions_answered = active_session.get('questions_answered', 0) if active_session else 0

                message_text = get_message(
                    'session_completed',
                    locale='ru',
                    category='onboarding',
                    questions_answered=questions_answered
                )
                keyboard = get_keyboard('session_completed', locale='ru')

                await callback.message.edit_text(message_text, parse_mode='HTML', reply_markup=keyboard)
                await state.clear()

        except Exception as e:
            logger.error(f"❌ Error skipping question for {telegram_id}: {e}")
            await callback.answer("❌ Ошибка пропуска вопроса")

    @staticmethod
    async def callback_end_session(
        callback: CallbackQuery,
        state: FSMContext,
        orchestrator,
        onboarding_states
    ):
        """Завершить сессию онбординга"""
        telegram_id = str(callback.from_user.id)
        logger.info(f"🏁 End session requested by user {telegram_id}")

        try:
            await callback.answer("🏁 Сессия завершена")

            # Завершаем через Orchestrator
            completion_result = await orchestrator.complete_onboarding(int(telegram_id))
            questions_answered = completion_result.get('questions_answered', 0)

            # Отправляем отчет если есть
            report_digest = completion_result.get('report_digest')
            if report_digest:
                logger.info(f"📊 Sending session report to user {telegram_id}")
                await callback.message.answer(report_digest, parse_mode='HTML')

            message_text = get_message(
                'session_completed',
                locale='ru',
                category='onboarding',
                questions_answered=questions_answered
            )
            keyboard = get_keyboard('session_completed', locale='ru')

            await callback.message.edit_text(message_text, parse_mode='HTML', reply_markup=keyboard)
            await state.set_state(onboarding_states.onboarding_complete)

        except Exception as e:
            logger.error(f"❌ Error ending session for {telegram_id}: {e}")
            await callback.answer("❌ Ошибка завершения сессии")

    @staticmethod
    async def callback_flag_question(
        callback: CallbackQuery,
        state: FSMContext,
        orchestrator,
        skip_question_handler
    ):
        """Пометить вопрос на доработку (только админ)"""
        telegram_id = str(callback.from_user.id)

        # Проверка прав админа
        if telegram_id != ADMIN_USER_ID:
            await callback.answer("❌ Недостаточно прав")
            return

        logger.info(f"🚧 Flag question requested by admin {telegram_id}")

        try:
            # Получаем текущий вопрос
            session = orchestrator.get_session(int(telegram_id))

            if not session or not session.get('current_question'):
                await callback.answer("❌ Нет активного вопроса")
                return

            current_question_id = session['current_question']['id']
            current_question_text = session['current_question']['text'][:60]

            # Помечаем в БД
            reason = f"Admin flagged via Telegram: {current_question_text}..."
            success = await orchestrator.onboarding_dao.flag_question(
                question_id=current_question_id,
                reason=reason,
                admin_id=int(telegram_id)
            )

            if success:
                logger.info(f"🚧 Admin marked question {current_question_id} for review")
                await callback.answer(f"✅ Вопрос {current_question_id} помечен на доработку")
            else:
                await callback.answer(f"⚠️ Ошибка сохранения флага")

            # Переходим к следующему вопросу
            await skip_question_handler(callback, state, orchestrator, None, None)

        except Exception as e:
            logger.error(f"❌ Error flagging question for admin {telegram_id}: {e}")
            await callback.answer("❌ Ошибка пометки вопроса")
