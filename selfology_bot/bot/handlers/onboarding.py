"""
Onboarding Handlers Mixin - извлечено из selfology_controller.py

Этот mixin содержит все handlers для онбординга:
- cmd_onboarding: команда /onboarding
- handle_onboarding_answer: обработка ответов
- callback_*: все callback handlers для кнопок
"""

import logging
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

from selfology_bot.bot.states import OnboardingStates
from selfology_bot.messages.human_names import HumanNames

logger = logging.getLogger(__name__)

# Admin user ID для проверки доступа к debug функциям
ADMIN_USER_ID = "98005572"


class OnboardingHandlersMixin:
    """
    Mixin класс с handlers для онбординга.
    
    Зависимости (должны быть в основном классе):
    - self.messages: MessageService
    - self.onboarding_orchestrator: OnboardingOrchestratorV2
    - self.onboarding_dao: OnboardingDAO
    """

    async def _show_onboarding_question(self, question: dict, session_info: dict, telegram_id: str,
                                        target, is_edit: bool = False):
        """Универсальная функция для показа вопроса онбординга с правильными шаблонами и клавиатурой

        Args:
            question: Объект вопроса из JSON
            session_info: Информация о сессии (question_number, total_questions, etc)
            telegram_id: ID пользователя
            target: Message или CallbackQuery объект для ответа
            is_edit: True если нужно edit_text, False если answer
        """
        is_admin = str(telegram_id) == "98005572"

        # Человечные названия для debug (только админу)
        classification = question.get('classification', {})
        domain_human = HumanNames.get_domain_human(classification.get('domain', ''))
        depth_human = HumanNames.get_depth_human(classification.get('depth_level', ''))
        energy_human = HumanNames.get_energy_human(classification.get('energy_dynamic', ''))

        # Debug лог для проверки метаданных
        if is_admin:
            logger.debug(f"🔍 Question metadata for {question['id']}: domain={classification.get('domain')}, depth={classification.get('depth_level')}, energy={classification.get('energy_dynamic')}")

        # Извлекаем elaborations если есть
        elaborations = question.get('elaborations', {})
        elaboration_content = elaborations.get('content', '')
        elaboration_type = elaborations.get('type', '')
        elaboration_priority = elaborations.get('priority', '')
        elaboration_icon = HumanNames.get_elaboration_icon(elaboration_type) if elaboration_type else ''

        text = self.messages.get_message('onboarding_question', 'ru', 'onboarding',
            question_number=session_info['question_number'],
            total_questions=session_info['total_questions'],
            total_lifetime=session_info.get('total_lifetime', 0),
            question_text=question['text'],
            question_id=question['id'],
            is_admin=is_admin,
            domain_human=domain_human,
            depth_human=depth_human,
            energy_human=energy_human,
            elaboration_content=elaboration_content,
            elaboration_type=elaboration_type,
            elaboration_priority=elaboration_priority,
            elaboration_icon=elaboration_icon
        )

        # Кнопки в зависимости от роли пользователя
        keyboard_name = "admin_answer_buttons" if is_admin else "onboarding_answer_buttons"
        keyboard = self.messages.get_keyboard(keyboard_name, 'ru')

        if is_edit:
            await target.message.edit_text(text, reply_markup=keyboard, parse_mode='HTML')
        else:
            await target.answer(text, reply_markup=keyboard, parse_mode='HTML')

    async def _show_cluster_question(
        self,
        question: dict,
        cluster_name: str,
        program_name: str,
        progress: str,
        target,
        is_edit: bool = False
    ):
        """Показать вопрос кластера (v2 система)

        Args:
            question: Объект вопроса из ClusterRouter
            cluster_name: Название текущего кластера
            program_name: Название программы
            progress: Строка прогресса "2/5"
            target: Message или CallbackQuery объект
            is_edit: True если edit_text, False если answer
        """
        # Формируем текст вопроса
        text = (
            f"📚 <b>{program_name}</b>\n"
            f"📦 {cluster_name} ({progress})\n"
            f"{'─' * 30}\n\n"
            f"💭 {question['text']}"
        )

        # Кнопки управления
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="⏸ Пауза", callback_data="pause_cluster"),
                InlineKeyboardButton(text="⏭ Пропустить", callback_data="skip_question")
            ]
        ])

        if is_edit:
            await target.message.edit_text(text, reply_markup=keyboard, parse_mode='HTML')
        else:
            await target.answer(text, reply_markup=keyboard, parse_mode='HTML')

    async def cmd_onboarding(self, message: Message, state: FSMContext):
        """Команда /onboarding - запуск процесса знакомства (v2 кластерная система)

        Три режима:
        - Авто: AI выбирает кластеры для быстрого построения цифрового отпечатка
        - Программа: пользователь выбирает программу из 29 доступных
        - Закончить: завершить незаконченные кластеры
        """

        telegram_id = str(message.from_user.id)
        current_state = await state.get_state()
        logger.info(f"🧠 Onboarding requested by user {telegram_id} (current_state: {current_state})")

        try:
            # Уведомление о переключении режима (если был в чате)
            if current_state == ChatStates.active:
                switch_message = self.messages.get_message('context_switch_to_onboarding', 'ru', 'general')
                await message.answer(switch_message, parse_mode='HTML')

            # Проверяем незаконченные кластеры (v2)
            unfinished = await self.onboarding_orchestrator.get_unfinished_clusters(int(telegram_id))

            if unfinished:
                # Есть незавершённые кластеры - показываем третий режим
                unfinished_text = "\n".join([
                    f"• {c['cluster_name']} ({c['questions_answered']}/{c['total_questions']})"
                    for c in unfinished[:3]
                ])

                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔄 Закончить кластеры", callback_data="mode_finish")],
                    [InlineKeyboardButton(text="🎯 Авто-подбор", callback_data="mode_auto")],
                    [InlineKeyboardButton(text="📚 Выбрать программу", callback_data="mode_program")]
                ])

                await message.answer(
                    f"📋 <b>У вас есть незавершённые кластеры:</b>\n\n"
                    f"{unfinished_text}\n\n"
                    f"Закончить их или начать новое?",
                    reply_markup=keyboard,
                    parse_mode='HTML'
                )
            else:
                # Нет незавершённых - выбор режима
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🎯 Авто-подбор", callback_data="mode_auto")],
                    [InlineKeyboardButton(text="📚 Выбрать программу", callback_data="mode_program")]
                ])

                await message.answer(
                    "🧠 <b>Как вы хотите начать?</b>\n\n"
                    "🎯 <b>Авто-подбор</b> — AI выберет вопросы для построения вашего профиля\n\n"
                    "📚 <b>Программа</b> — выбрать одну из 29 программ",
                    reply_markup=keyboard,
                    parse_mode='HTML'
                )

            await state.set_state(OnboardingStates.choosing_mode)

        except Exception as e:
            logger.error(f"❌ Error in cmd_onboarding for {telegram_id}: {e}")
            await message.answer(f"❌ Ошибка: {e}", parse_mode='HTML')

    async def handle_onboarding_answer(self, message: Message, state: FSMContext):
        """Обработка ответа пользователя в процессе онбординга (v2 - кластерная система)"""

        telegram_id = str(message.from_user.id)
        user_answer = message.text

        current_state = await state.get_state()
        logger.info(f"💬 Received answer from user {telegram_id}: {len(user_answer)} chars (state: {current_state})")

        try:
            # Получаем сессию из orchestrator
            session = self.onboarding_orchestrator.get_current_session(int(telegram_id))

            if not session or not session.get('current_question'):
                logger.error(f"❌ No active session for user {telegram_id}")
                await message.answer("❌ Нет активной сессии. Начните с /onboarding", parse_mode='HTML')
                return

            current_question = session['current_question']
            question_id = current_question['id']
            logger.info(f"📝 Processing answer for question {question_id}")

            # Обрабатываем ответ (v2)
            result = await self.onboarding_orchestrator.process_answer(
                user_id=int(telegram_id),
                question_id=question_id,
                answer_text=user_answer
            )

            status = result.get('status')

            if status == 'next_question':
                # Показываем следующий вопрос в кластере
                next_question = result['question']
                data = await state.get_data()

                # Получаем информацию о кластере из session
                session = self.onboarding_orchestrator.get_current_session(int(telegram_id))
                cluster = self.onboarding_orchestrator.cluster_router.get_cluster(data.get('cluster_id', ''))

                await self._show_cluster_question(
                    question=next_question,
                    cluster_name=cluster['name'] if cluster else '',
                    program_name=cluster['program_name'] if cluster else '',
                    progress=result.get('progress', ''),
                    target=message,
                    is_edit=False
                )
                await state.set_state(OnboardingStates.waiting_for_answer)

            elif status == 'cluster_completed':
                # Кластер завершён
                cluster_name = result.get('cluster_name', 'Кластер')

                if result.get('has_next'):
                    # Есть следующий кластер
                    next_cluster = result.get('next_cluster', {})
                    keyboard = InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="▶️ Продолжить", callback_data="continue_next_cluster")],
                        [InlineKeyboardButton(text="⏸ Пауза", callback_data="pause_onboarding")]
                    ])

                    await message.answer(
                        f"🎉 <b>Кластер «{cluster_name}» завершён!</b>\n\n"
                        f"Следующий: <b>{next_cluster.get('cluster_name', 'Следующий блок')}</b>\n"
                        f"Вопросов: {next_cluster.get('questions_count', '?')}",
                        parse_mode='HTML',
                        reply_markup=keyboard
                    )
                    # Сохраняем next_cluster в state
                    await state.update_data(next_cluster=next_cluster)
                else:
                    # Все кластеры пройдены или программа завершена
                    msg = result.get('message', '🎉 Все вопросы пройдены!')
                    keyboard = InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="📚 Выбрать программу", callback_data="mode_program")],
                        [InlineKeyboardButton(text="💬 Начать чат", callback_data="start_chat")]
                    ])
                    await message.answer(msg, parse_mode='HTML', reply_markup=keyboard)

                await state.set_state(OnboardingStates.onboarding_complete)

            else:
                # Ошибка
                await message.answer(f"❌ {result.get('message', 'Ошибка')}", parse_mode='HTML')

        except Exception as e:
            logger.error(f"❌ Error processing answer from {telegram_id}: {e}")
            await message.answer(f"❌ Ошибка: {e}", parse_mode='HTML')

    async def callback_skip_question(self, callback: CallbackQuery, state: FSMContext):
        """Пропустить текущий вопрос"""

        telegram_id = str(callback.from_user.id)
        logger.info(f"⏭️ Skip question requested by user {telegram_id}")

        try:
            await callback.answer("⏭️ Вопрос пропущен")

            # ✅ Записываем факт пропуска в историю (для FatigueDetector)
            session = self.onboarding_orchestrator.get_session(int(telegram_id))
            if session and session.get("current_question"):
                current_question_id = session["current_question"]["id"]
                await self.onboarding_orchestrator.record_skipped_question(
                    int(telegram_id),
                    current_question_id
                )

            # Получаем следующий вопрос
            next_result = await self.onboarding_orchestrator.get_next_question(
                int(telegram_id), {"question_number": 2}
            )

            if next_result["status"] == "continue":
                next_question = next_result["question"]
                session_info = next_result["session_info"]

                # Используем универсальную функцию (is_edit=True для кнопок)
                await self._show_onboarding_question(next_question, session_info, telegram_id, callback, is_edit=True)
                await state.set_state(OnboardingStates.waiting_for_answer)
            else:
                # Онбординг завершен - получаем информацию о сессии
                active_session = await self.onboarding_dao.get_active_session(int(telegram_id))
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

    async def callback_end_session(self, callback: CallbackQuery, state: FSMContext):
        """Завершить сессию онбординга"""

        telegram_id = str(callback.from_user.id)
        logger.info(f"🏁 End session requested by user {telegram_id}")

        try:
            await callback.answer("🏁 Сессия завершена")

            # Завершаем через OnboardingOrchestrator
            completion_result = await self.onboarding_orchestrator.complete_onboarding(int(telegram_id))

            # Получаем количество ответов из результата
            questions_answered = completion_result.get('questions_answered', 0)

            # 📊 Отправляем отчет о сессии если он был сгенерирован
            report_digest = completion_result.get('report_digest')
            if report_digest:
                logger.info(f"📊 Sending session report digest to user {telegram_id}")
                await callback.message.answer(report_digest, parse_mode='HTML')

            message_text = get_message(
                'session_completed',
                locale='ru',
                category='onboarding',
                questions_answered=questions_answered
            )
            keyboard = get_keyboard('session_completed', locale='ru')

            await callback.message.edit_text(message_text, parse_mode='HTML', reply_markup=keyboard)
            await state.set_state(OnboardingStates.onboarding_complete)

        except Exception as e:
            logger.error(f"❌ Error ending session for {telegram_id}: {e}")
            await callback.answer("❌ Ошибка завершения сессии")

    async def callback_flag_question(self, callback: CallbackQuery, state: FSMContext):
        """Пометить вопрос на доработку (только админ)"""

        telegram_id = str(callback.from_user.id)

        # Проверяем что это админ
        if telegram_id != "98005572":
            await callback.answer("❌ Недостаточно прав")
            return

        logger.info(f"🚧 Flag question requested by admin {telegram_id}")

        try:
            # Получаем текущий вопрос из активной сессии в памяти Orchestrator
            session = self.onboarding_orchestrator.get_session(int(telegram_id))

            if not session or not session.get('current_question'):
                await callback.answer("❌ Нет активного вопроса")
                return

            current_question_id = session['current_question']['id']
            current_question_text = session['current_question']['text'][:60]

            # Помечаем вопрос в БД (best practice: Database as Single Source of Truth)
            reason = f"Admin flagged via Telegram: {current_question_text}..."
            success = await self.onboarding_orchestrator.onboarding_dao.flag_question(
                question_id=current_question_id,
                reason=reason,
                admin_id=int(telegram_id)
            )

            if success:
                logger.info(f"🚧 Admin marked question {current_question_id} for review in database")
                await callback.answer(f"✅ Вопрос {current_question_id} помечен на доработку")
            else:
                await callback.answer(f"⚠️ Ошибка сохранения флага для {current_question_id}")

            # Переходим к следующему вопросу
            await self.callback_skip_question(callback, state)

        except Exception as e:
            logger.error(f"❌ Error flagging question for admin {telegram_id}: {e}")
            await callback.answer("❌ Ошибка пометки вопроса")

    async def callback_end_onboarding(self, callback: CallbackQuery, state: FSMContext):
        """Завершить процесс онбординга полностью"""

        telegram_id = str(callback.from_user.id)
        logger.info(f"🏁 End onboarding requested by user {telegram_id}")

        try:
            # Завершаем активную сессию
            active_session = await self.onboarding_dao.get_active_session(int(telegram_id))

            if active_session:
                session_id = active_session['id']
                await self.onboarding_dao.complete_session(session_id)

                questions_answered = active_session.get('questions_answered', 0)

                # Используем новый шаблон и клавиатуру
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

    async def callback_continue_onboarding(self, callback: CallbackQuery, state: FSMContext):
        """Продолжить онбординг после завершения сессии"""

        telegram_id = str(callback.from_user.id)
        logger.info(f"▶️ Continue onboarding requested by user {telegram_id}")

        try:
            await callback.answer("▶️ Продолжаем онбординг")

            # Запускаем новую сессию онбординга
            next_result = await self.onboarding_orchestrator.get_next_question(
                int(telegram_id), {"question_number": 1}
            )

            if next_result["status"] == "continue":
                next_question = next_result["question"]
                session_info = next_result["session_info"]

                # Показываем следующий вопрос
                await self._show_onboarding_question(next_question, session_info, telegram_id, callback, is_edit=True)
                await state.set_state(OnboardingStates.waiting_for_answer)
            else:
                await callback.message.edit_text(
                    "✨ Все вопросы пройдены! Спасибо за участие.",
                    parse_mode='HTML'
                )
                await state.clear()

        except Exception as e:
            logger.error(f"❌ Error continuing onboarding for {telegram_id}: {e}")
            await callback.answer("❌ Ошибка продолжения онбординга")

    # ═══════════════════════════════════════════════════════════════════════════
    # 🆕 БЛОЧНАЯ СИСТЕМА ПРОГРАММ - callback handlers
    # ═══════════════════════════════════════════════════════════════════════════

    async def callback_mode_auto(self, callback: CallbackQuery, state: FSMContext):
        """Авто-режим - умный подбор кластеров для построения цифрового отпечатка"""

        telegram_id = str(callback.from_user.id)
        logger.info(f"🎯 Auto mode selected by user {telegram_id}")

        try:
            await callback.answer("🎯 Авто-режим активирован")

            # Запускаем умный режим (v2)
            result = await self.onboarding_orchestrator.start_smart_mode(int(telegram_id))

            if result.get('status') == 'all_completed':
                await callback.message.edit_text(
                    "🎉 Поздравляем! Вы прошли все кластеры.",
                    parse_mode='HTML'
                )
                return

            # Сохраняем режим в state
            await state.update_data(onboarding_mode='smart_ai', cluster_id=result['cluster_id'])

            # Показываем первый вопрос кластера
            await self._show_cluster_question(
                question=result['question'],
                cluster_name=result['cluster_name'],
                program_name=result['program_name'],
                progress=f"1/{result['total_questions']}",
                target=callback,
                is_edit=True
            )
            await state.set_state(OnboardingStates.waiting_for_answer)

        except Exception as e:
            logger.error(f"❌ Error starting auto mode for {telegram_id}: {e}")
            await callback.answer(f"❌ Ошибка: {e}", show_alert=True)

    async def callback_mode_program(self, callback: CallbackQuery, state: FSMContext):
        """Режим программ - показываем список доступных программ"""

        telegram_id = str(callback.from_user.id)
        logger.info(f"📚 Program mode selected by user {telegram_id}")

        try:
            await callback.answer("📚 Загружаю программы...")

            # Получаем список программ (v2 - из JSON)
            programs = self.onboarding_orchestrator.get_all_programs()

            if not programs:
                await callback.message.edit_text(
                    "❌ Программы не найдены. Попробуйте позже.",
                    parse_mode='HTML'
                )
                return

            # Формируем нумерованный список всех программ
            program_list = []
            for i, p in enumerate(programs, 1):
                blocks_info = f"{p.get('blocks_count', '?')} блоков, {p.get('questions_count', '?')} вопросов"
                program_list.append(f"{i:02d}. {p['name']} ({blocks_info})")

            # Сохраняем программы в state для выбора по номеру
            programs_map = {str(i): p['id'] for i, p in enumerate(programs, 1)}
            await state.update_data(programs_map=programs_map)

            # Кнопка "Назад"
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_mode_selection")]
            ])

            await callback.message.edit_text(
                f"📚 <b>Выберите программу</b>\n\n"
                f"Введите номер программы (1-{len(programs)}):\n\n"
                + "\n".join(program_list),
                reply_markup=keyboard,
                parse_mode='HTML'
            )
            await state.set_state(OnboardingStates.choosing_program)

        except Exception as e:
            logger.error(f"❌ Error loading programs for {telegram_id}: {e}")
            await callback.answer(f"❌ Ошибка: {e}", show_alert=True)

    async def callback_select_program(self, callback: CallbackQuery, state: FSMContext):
        """Выбрана конкретная программа - начинаем её"""

        telegram_id = str(callback.from_user.id)
        program_id = callback.data.split(":")[1]
        logger.info(f"📚 Program {program_id} selected by user {telegram_id}")

        try:
            await callback.answer("🚀 Запускаю программу...")

            # Запускаем программу
            result = await self.onboarding_orchestrator.start_program(
                int(telegram_id), program_id
            )

            if not result or 'question' not in result:
                await callback.message.edit_text(
                    "❌ Не удалось запустить программу. Попробуйте другую.",
                    parse_mode='HTML'
                )
                return

            # Сохраняем program_id в state
            await state.update_data(program_id=program_id, onboarding_mode='program')

            question = result['question']
            block_info = result.get('block_info', {})
            program_name = result.get('program_name', 'Программа')

            # Показываем первый вопрос программы
            await self._show_program_question(
                question=question,
                block_info=block_info,
                program_name=program_name,
                target=callback,
                is_edit=True
            )
            await state.set_state(OnboardingStates.waiting_program_answer)

        except Exception as e:
            logger.error(f"❌ Error starting program {program_id} for {telegram_id}: {e}")
            await callback.answer(f"❌ Ошибка: {e}", show_alert=True)

    async def handle_program_number_input(self, message: Message, state: FSMContext):
        """Обработка ввода номера программы"""
        telegram_id = str(message.from_user.id)
        user_input = message.text.strip()

        # Получаем карту программ из state
        data = await state.get_data()
        programs_map = data.get('programs_map', {})

        if not programs_map:
            await message.answer("❌ Список программ устарел. Выберите заново через /onboarding")
            return

        # Проверяем что введён номер
        if user_input not in programs_map:
            await message.answer(
                f"❌ Введите номер от 1 до {len(programs_map)}",
                parse_mode='HTML'
            )
            return

        program_id = programs_map[user_input]
        logger.info(f"📚 Program {program_id} selected by number {user_input} for user {telegram_id}")

        try:
            # Запускаем программу (v2)
            result = await self.onboarding_orchestrator.start_program_mode(
                int(telegram_id), program_id
            )

            if result.get('status') == 'error':
                await message.answer(f"❌ {result.get('message', 'Ошибка запуска программы')}")
                return

            # Сохраняем в state
            await state.update_data(
                program_id=program_id,
                cluster_id=result['cluster_id'],
                onboarding_mode='program'
            )

            # Показываем первый вопрос кластера
            await self._show_cluster_question(
                question=result['question'],
                cluster_name=result['cluster_name'],
                program_name=result['program_name'],
                progress=f"1/{result['total_questions']}",
                target=message,
                is_edit=False
            )
            await state.set_state(OnboardingStates.waiting_for_answer)

        except Exception as e:
            logger.error(f"❌ Error starting program {program_id} for {telegram_id}: {e}")
            await message.answer(f"❌ Ошибка: {e}")

