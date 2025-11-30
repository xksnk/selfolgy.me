"""
Program Flow Handlers Mixin - извлечено из selfology_controller.py

Этот mixin содержит handlers для работы с программами:
- callback_mode_finish: завершение выбора режима
- callback_continue_cluster: продолжение кластера
- handle_program_answer: обработка ответов в программах
- И другие handlers программного flow
"""

import logging
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

from selfology_bot.bot.states import OnboardingStates

logger = logging.getLogger(__name__)


class ProgramHandlersMixin:
    """
    Mixin класс с handlers для программ.
    
    Зависимости (должны быть в основном классе):
    - self.messages: MessageService
    - self.onboarding_orchestrator: OnboardingOrchestratorV2
    """

    async def callback_back_to_mode_selection(self, callback: CallbackQuery, state: FSMContext):
        """Вернуться к выбору режима"""

        telegram_id = str(callback.from_user.id)
        logger.info(f"◀️ Back to mode selection by user {telegram_id}")

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🎯 Авто-подбор", callback_data="mode_auto")],
            [InlineKeyboardButton(text="📚 Выбрать программу", callback_data="mode_program")]
        ])

        await callback.message.edit_text(
            "🧠 <b>Как вы хотите начать знакомство?</b>\n\n"
            "🎯 <b>Авто-подбор</b> — AI выберет вопросы для быстрого построения вашего профиля\n\n"
            "📚 <b>Программа</b> — структурированный путь по конкретной теме",
            reply_markup=keyboard,
            parse_mode='HTML'
        )
        await state.set_state(OnboardingStates.choosing_mode)

    # =========================================================================
    # 🆕 V2 CLUSTER SYSTEM - handlers
    # =========================================================================

    async def callback_mode_finish(self, callback: CallbackQuery, state: FSMContext):
        """Режим завершения незаконченных кластеров"""

        telegram_id = str(callback.from_user.id)
        logger.info(f"🔄 Finish mode selected by user {telegram_id}")

        try:
            await callback.answer("🔄 Загружаю незаконченные кластеры...")

            # Получаем список незаконченных кластеров
            unfinished = await self.onboarding_orchestrator.get_unfinished_clusters(int(telegram_id))

            if not unfinished:
                await callback.message.edit_text(
                    "✅ У вас нет незаконченных кластеров!",
                    parse_mode='HTML'
                )
                return

            # Формируем список кнопок для каждого кластера
            buttons = []
            for c in unfinished:
                buttons.append([InlineKeyboardButton(
                    text=f"📦 {c['cluster_name']} ({c['questions_answered']}/{c['total_questions']})",
                    callback_data=f"continue_cluster:{c['cluster_id']}"
                )])

            buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_mode_selection")])

            await callback.message.edit_text(
                "📋 <b>Выберите кластер для продолжения:</b>",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
                parse_mode='HTML'
            )

        except Exception as e:
            logger.error(f"❌ Error in mode_finish for {telegram_id}: {e}")
            await callback.answer(f"❌ Ошибка: {e}", show_alert=True)

    async def callback_continue_cluster(self, callback: CallbackQuery, state: FSMContext):
        """Продолжить выбранный незаконченный кластер"""

        telegram_id = str(callback.from_user.id)
        cluster_id = callback.data.split(":")[1]
        logger.info(f"▶️ Continue cluster {cluster_id} by user {telegram_id}")

        try:
            await callback.answer("▶️ Продолжаю...")

            # Продолжаем кластер
            result = await self.onboarding_orchestrator.continue_cluster(int(telegram_id), cluster_id)

            if result.get('status') == 'cluster_completed':
                await callback.message.edit_text(
                    "✅ Этот кластер уже завершён!",
                    parse_mode='HTML'
                )
                return

            # Сохраняем в state
            await state.update_data(
                cluster_id=cluster_id,
                onboarding_mode='finish'
            )

            # Показываем вопрос
            await self._show_cluster_question(
                question=result['question'],
                cluster_name=result['cluster_name'],
                program_name=result['program_name'],
                progress=result['progress'],
                target=callback,
                is_edit=True
            )
            await state.set_state(OnboardingStates.waiting_for_answer)

        except Exception as e:
            logger.error(f"❌ Error continuing cluster for {telegram_id}: {e}")
            await callback.answer(f"❌ Ошибка: {e}", show_alert=True)

    async def callback_continue_next_cluster(self, callback: CallbackQuery, state: FSMContext):
        """Продолжить со следующим кластером"""

        telegram_id = str(callback.from_user.id)
        logger.info(f"▶️ Continue to next cluster by user {telegram_id}")

        try:
            await callback.answer("▶️ Продолжаю...")

            # Получаем next_cluster из state
            data = await state.get_data()
            next_cluster = data.get('next_cluster', {})
            mode = data.get('onboarding_mode', 'smart_ai')

            if not next_cluster:
                await callback.message.edit_text("❌ Нет информации о следующем кластере", parse_mode='HTML')
                return

            cluster_id = next_cluster.get('cluster_id')

            # Запускаем кластер в зависимости от режима
            if mode == 'program':
                program_id = data.get('program_id')
                result = await self.onboarding_orchestrator.start_program_mode(int(telegram_id), program_id)
            else:
                result = await self.onboarding_orchestrator.start_smart_mode(int(telegram_id))

            if result.get('status') == 'error':
                await callback.message.edit_text(f"❌ {result.get('message')}", parse_mode='HTML')
                return

            # Сохраняем в state
            await state.update_data(cluster_id=result['cluster_id'])

            # Показываем первый вопрос
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
            logger.error(f"❌ Error continuing to next cluster for {telegram_id}: {e}")
            await callback.answer(f"❌ Ошибка: {e}", show_alert=True)

    async def callback_pause_cluster(self, callback: CallbackQuery, state: FSMContext):
        """Поставить кластер на паузу"""

        telegram_id = str(callback.from_user.id)
        logger.info(f"⏸ Pause cluster by user {telegram_id}")

        try:
            await callback.answer("⏸ Пауза")

            # Очищаем сессию в orchestrator
            self.onboarding_orchestrator.clear_session(int(telegram_id))

            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="▶️ Продолжить", callback_data="mode_finish")],
                [InlineKeyboardButton(text="💬 Чат с коучем", callback_data="start_chat")]
            ])

            await callback.message.edit_text(
                "⏸ <b>Сессия на паузе</b>\n\n"
                "Вы можете продолжить позже. Ваш прогресс сохранён.",
                reply_markup=keyboard,
                parse_mode='HTML'
            )
            await state.set_state(OnboardingStates.onboarding_paused)

        except Exception as e:
            logger.error(f"❌ Error pausing cluster for {telegram_id}: {e}")
            await callback.answer(f"❌ Ошибка: {e}", show_alert=True)

    async def callback_continue_session(self, callback: CallbackQuery, state: FSMContext):
        """Продолжить существующую сессию"""

        telegram_id = str(callback.from_user.id)
        logger.info(f"▶️ Continue existing session by user {telegram_id}")

        try:
            await callback.answer("▶️ Продолжаю сессию...")

            # Восстанавливаем сессию
            session = await self.onboarding_orchestrator.restore_session_from_db(int(telegram_id))

            if not session:
                await callback.message.edit_text(
                    "❌ Сессия не найдена. Начните новую.",
                    parse_mode='HTML'
                )
                return

            # Определяем режим сессии
            session_type = session.get('session_type', 'auto')

            if session_type == 'program':
                # Продолжаем программу
                program_id = session.get('program_id')
                result = await self.onboarding_orchestrator.get_next_program_question(
                    int(telegram_id), program_id
                )
                if result and 'question' in result:
                    await state.update_data(program_id=program_id, onboarding_mode='program')
                    await self._show_program_question(
                        question=result['question'],
                        block_info=result.get('block_info', {}),
                        program_name=result.get('program_name', ''),
                        target=callback,
                        is_edit=True
                    )
                    await state.set_state(OnboardingStates.waiting_program_answer)
                else:
                    await callback.message.edit_text(
                        "✅ Программа завершена!",
                        parse_mode='HTML'
                    )
            else:
                # Продолжаем авто-режим
                result = await self.onboarding_orchestrator.get_next_question(
                    int(telegram_id),
                    {"question_number": session.get('question_number', 1)}
                )

                if result['status'] == 'continue':
                    await self._show_onboarding_question(
                        result['question'],
                        result['session_info'],
                        telegram_id,
                        callback,
                        is_edit=True
                    )
                    await state.set_state(OnboardingStates.waiting_for_answer)
                else:
                    await callback.message.edit_text(
                        "✅ Все вопросы пройдены!",
                        parse_mode='HTML'
                    )

        except Exception as e:
            logger.error(f"❌ Error continuing session for {telegram_id}: {e}")
            await callback.answer(f"❌ Ошибка: {e}", show_alert=True)

    async def _show_program_question(
        self,
        question: dict,
        block_info: dict,
        program_name: str,
        target,
        is_edit: bool = False
    ):
        """Показать вопрос из программы с информацией о блоке"""

        telegram_id = str(target.from_user.id)
        is_admin = telegram_id == "98005572"

        # Формируем информацию о блоке
        block_name = block_info.get('name', 'Блок')
        block_type = block_info.get('type', 'Foundation')
        block_emoji = {"Foundation": "🌱", "Exploration": "🔍", "Integration": "🎯"}.get(block_type, "📦")
        question_num = block_info.get('question_num', 1)
        total_in_block = block_info.get('total_in_block', '?')

        # Формируем текст вопроса
        text = (
            f"📚 <b>{program_name}</b>\n"
            f"{block_emoji} <i>{block_name}</i> • Вопрос {question_num}/{total_in_block}\n"
            f"{'─' * 25}\n\n"
            f"{question.get('text', question)}\n"
        )

        # Добавляем debug info для админа
        if is_admin:
            q_id = question.get('id', question.get('question_id', '?'))
            text += f"\n\n<code>🔧 ID: {q_id}</code>"

        # Кнопки
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="⏭ Пропустить", callback_data="skip_program_question"),
                InlineKeyboardButton(text="⏸ Пауза", callback_data="pause_program")
            ]
        ])

        if is_edit:
            await target.message.edit_text(text, reply_markup=keyboard, parse_mode='HTML')
        else:
            await target.answer(text, reply_markup=keyboard, parse_mode='HTML')

    async def handle_program_answer(self, message: Message, state: FSMContext):
        """Обработка ответа в режиме программы"""

        telegram_id = str(message.from_user.id)
        user_answer = message.text

        logger.info(f"💬 Program answer from user {telegram_id}: {len(user_answer)} chars")

        try:
            # Получаем данные из state
            state_data = await state.get_data()
            program_id = state_data.get('program_id')

            if not program_id:
                await message.answer("❌ Ошибка: программа не выбрана. Начните /onboarding заново.")
                return

            # Получаем текущий вопрос из сессии
            session = self.onboarding_orchestrator.get_session(int(telegram_id))
            if not session or not session.get('current_question'):
                session = await self.onboarding_orchestrator.restore_session_from_db(int(telegram_id))

            if not session or not session.get('current_question'):
                await message.answer("❌ Ошибка: нет активной сессии. Начните /onboarding заново.")
                return

            current_question_id = session['current_question'].get('id') or session['current_question'].get('question_id')

            # Показываем мгновенный фидбек
            await message.answer("✅ Принято! Анализирую ваш ответ...", parse_mode='HTML')

            # Обрабатываем ответ через Orchestrator
            result = await self.onboarding_orchestrator.process_program_answer(
                user_id=int(telegram_id),
                program_id=program_id,
                question_id=current_question_id,
                answer_text=user_answer
            )

            # Получаем следующий вопрос
            next_result = await self.onboarding_orchestrator.get_next_program_question(
                int(telegram_id), program_id
            )

            if next_result and next_result.get('status') == 'continue':
                # Показываем следующий вопрос
                await self._show_program_question(
                    question=next_result['question'],
                    block_info=next_result.get('block_info', {}),
                    program_name=next_result.get('program_name', ''),
                    target=message,
                    is_edit=False
                )
                await state.set_state(OnboardingStates.waiting_program_answer)

            elif next_result and next_result.get('status') == 'block_complete':
                # Блок завершён - показываем переход
                await self._show_block_transition(
                    user_id=int(telegram_id),
                    program_id=program_id,
                    next_block=next_result.get('next_block'),
                    target=message
                )
                await state.set_state(OnboardingStates.block_transition)

            else:
                # Программа завершена
                await self._complete_program_flow(
                    user_id=int(telegram_id),
                    program_id=program_id,
                    target=message
                )
                await state.clear()

        except Exception as e:
            logger.error(f"❌ Error processing program answer from {telegram_id}: {e}")
            await message.answer(f"❌ Ошибка: {e}", parse_mode='HTML')

    async def _show_block_transition(self, user_id: int, program_id: str, next_block: dict, target):
        """Показать сообщение о переходе к следующему блоку"""

        if not next_block:
            # Программа завершена
            return await self._complete_program_flow(user_id, program_id, target)

        block_emoji = {"Foundation": "🌱", "Exploration": "🔍", "Integration": "🎯"}.get(
            next_block.get('type', ''), "📦"
        )

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="▶️ Продолжить", callback_data="continue_program_block")],
            [InlineKeyboardButton(text="⏸ Пауза", callback_data="pause_program")]
        ])

        await target.answer(
            f"✅ <b>Блок завершён!</b>\n\n"
            f"Следующий блок:\n"
            f"{block_emoji} <b>{next_block.get('name', 'Блок')}</b>\n"
            f"<i>{next_block.get('description', '')}</i>\n\n"
            f"Вопросов: {next_block.get('questions_count', '?')}",
            reply_markup=keyboard,
            parse_mode='HTML'
        )

    async def _complete_program_flow(self, user_id: int, program_id: str, target):
        """Завершить программу и показать итоги"""

        # Получаем статистику программы
        progress = await self.onboarding_orchestrator.get_program_progress(user_id, program_id)

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📚 Другая программа", callback_data="mode_program")],
            [InlineKeyboardButton(text="💬 Чат с коучем", callback_data="start_chat")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
        ])

        questions_answered = progress.get('questions_answered', 0) if progress else 0
        program_name = progress.get('program_name', 'Программа') if progress else 'Программа'

        await target.answer(
            f"🎉 <b>Поздравляем!</b>\n\n"
            f"Вы завершили программу «{program_name}»!\n\n"
            f"📊 <b>Статистика:</b>\n"
            f"• Вопросов отвечено: {questions_answered}\n\n"
            f"Что дальше?",
            reply_markup=keyboard,
            parse_mode='HTML'
        )

    async def callback_continue_program_block(self, callback: CallbackQuery, state: FSMContext):
        """Продолжить программу после перехода блока"""

        telegram_id = str(callback.from_user.id)
        logger.info(f"▶️ Continue program block by user {telegram_id}")

        try:
            state_data = await state.get_data()
            program_id = state_data.get('program_id')

            if not program_id:
                await callback.answer("❌ Программа не найдена", show_alert=True)
                return

            # Получаем следующий вопрос
            result = await self.onboarding_orchestrator.get_next_program_question(
                int(telegram_id), program_id
            )

            if result and result.get('status') == 'continue':
                await self._show_program_question(
                    question=result['question'],
                    block_info=result.get('block_info', {}),
                    program_name=result.get('program_name', ''),
                    target=callback,
                    is_edit=True
                )
                await state.set_state(OnboardingStates.waiting_program_answer)
            else:
                await self._complete_program_flow(int(telegram_id), program_id, callback.message)
                await state.clear()

        except Exception as e:
            logger.error(f"❌ Error continuing program block for {telegram_id}: {e}")
            await callback.answer(f"❌ Ошибка: {e}", show_alert=True)

    async def callback_pause_program(self, callback: CallbackQuery, state: FSMContext):
        """Поставить программу на паузу"""

        telegram_id = str(callback.from_user.id)
        logger.info(f"⏸ Program paused by user {telegram_id}")

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="▶️ Продолжить", callback_data="continue_session")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
        ])

        await callback.message.edit_text(
            "⏸ <b>Программа на паузе</b>\n\n"
            "Ваш прогресс сохранён. Вы можете продолжить в любое время через /onboarding.",
            reply_markup=keyboard,
            parse_mode='HTML'
        )
        await state.set_state(OnboardingStates.onboarding_paused)

    async def callback_skip_program_question(self, callback: CallbackQuery, state: FSMContext):
        """Пропустить вопрос в программе"""

        telegram_id = str(callback.from_user.id)
        logger.info(f"⏭ Skip program question by user {telegram_id}")

        try:
            await callback.answer("⏭ Вопрос пропущен")

            state_data = await state.get_data()
            program_id = state_data.get('program_id')

            # Записываем пропуск
            session = self.onboarding_orchestrator.get_session(int(telegram_id))
            if session and session.get('current_question'):
                await self.onboarding_orchestrator.record_skipped_question(
                    int(telegram_id),
                    session['current_question'].get('id') or session['current_question'].get('question_id')
                )

            # Получаем следующий вопрос
            result = await self.onboarding_orchestrator.get_next_program_question(
                int(telegram_id), program_id
            )

            if result and result.get('status') == 'continue':
                await self._show_program_question(
                    question=result['question'],
                    block_info=result.get('block_info', {}),
                    program_name=result.get('program_name', ''),
                    target=callback,
                    is_edit=True
                )
            elif result and result.get('status') == 'block_complete':
                await self._show_block_transition(
                    user_id=int(telegram_id),
                    program_id=program_id,
                    next_block=result.get('next_block'),
                    target=callback.message
                )
                await state.set_state(OnboardingStates.block_transition)
            else:
                await self._complete_program_flow(int(telegram_id), program_id, callback.message)
                await state.clear()

        except Exception as e:
            logger.error(f"❌ Error skipping program question for {telegram_id}: {e}")
            await callback.answer(f"❌ Ошибка: {e}", show_alert=True)

    # ═══════════════════════════════════════════════════════════════════════════

    async def callback_process_orphaned(self, callback: CallbackQuery):
        """Обработать orphaned ответы (без AI анализа)"""

        # Извлекаем user_id из callback_data
        user_id = int(callback.data.split(":")[1])

        # Проверка прав: только для своих ответов или админа
        if callback.from_user.id != user_id and str(callback.from_user.id) != ADMIN_USER_ID:
            await callback.answer("❌ Вы можете обрабатывать только свои ответы", show_alert=True)
            return

        logger.info(f"🔄 Processing orphaned answers requested for user {user_id}")

        try:
            await callback.answer("🔄 Запускаю обработку...")

            # Отправляем сообщение о начале обработки
            status_msg = await callback.message.answer("🔄 Обрабатываю пропущенные ответы...\n\nЭто может занять несколько минут.")

            import subprocess

            # Запускаем скрипт обработки orphaned ответов
            result = subprocess.run(
                ["bash", "-c", f"source venv/bin/activate && python process_orphaned_answers.py --user {user_id}"],
                capture_output=True,
                text=True,
                timeout=300,  # 5 минут максимум
                cwd="/home/ksnk/n8n-enterprise/projects/selfology"
            )

            if result.returncode == 0:
                # Парсим результат для извлечения статистики
                import re
                output = result.stdout

                # Ищем статистику
                found_match = re.search(r'Найдено:\s+(\d+)', output)
                processed_match = re.search(r'Обработано:\s+(\d+)', output)
                failed_match = re.search(r'Ошибок:\s+(\d+)', output)

                found = found_match.group(1) if found_match else "?"
                processed = processed_match.group(1) if processed_match else "?"
                failed = failed_match.group(1) if failed_match else "?"

                if found == "0":
                    await status_msg.edit_text("✅ Все ответы уже обработаны!\n\nНет пропущенных ответов для обработки.")
                else:
                    await status_msg.edit_text(
                        f"✅ Обработка завершена!\n\n"
                        f"📊 Статистика:\n"
                        f"  • Найдено: {found}\n"
                        f"  • Обработано: {processed}\n"
                        f"  • Ошибок: {failed}\n\n"
                        f"Используйте /onboarding_profile для просмотра обновленного профиля."
                    )
            else:
                error_text = result.stderr or "Unknown error"
                await status_msg.edit_text(
                    f"❌ Ошибка при обработке:\n```\n{error_text[:500]}```",
                    parse_mode="Markdown"
                )

        except subprocess.TimeoutExpired:
            await status_msg.edit_text("⏱ Таймаут: обработка заняла слишком много времени (>5 минут)")

        except Exception as e:
            logger.error(f"❌ Error processing orphaned answers: {e}")
            await callback.message.answer(f"❌ Ошибка: {str(e)[:200]}")

