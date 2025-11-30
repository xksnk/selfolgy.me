#!/usr/bin/env python3
"""
Selfology Bot Controller - Простой управляющий файл

Архитектура:
- Bot Controller: только управление ботом и routing
- MessageService: только сообщения и шаблоны
- Services: бизнес логика (пока заглушки)

Чистая архитектура без сложных imports

АРХИТЕКТУРНЫЕ УЛУЧШЕНИЯ (October 2025):
- Graceful shutdown с ожиданием background tasks
- Proper integration с OnboardingOrchestrator shutdown
- Observability для мониторинга системы
"""

import asyncio
import json
import logging
import os
import sys
import signal
from datetime import datetime
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.redis import RedisStorage
import redis.asyncio as redis

# Добавляем путь для импорта MessageService и DatabaseService
sys.path.insert(0, str(Path(__file__).parent))

from selfology_bot.messages import get_message, get_keyboard, get_message_service
from selfology_bot.messages.human_names import HumanNames
from selfology_bot.database import DatabaseService, UserDAO, OnboardingDAO
# from selfology_bot.services.simple_onboarding import SimpleOnboardingService  # DISABLED
# from selfology_bot.services.onboarding import OnboardingOrchestrator  # DISABLED - old system
from selfology_bot.services.onboarding.orchestrator_v2 import OnboardingOrchestratorV2  # 🆕 v2 cluster system
from services.chat_coach import ChatCoachService  # 🔥 PHASE 2-3 ACTIVE!
# Components: Enhanced Router, Adaptive Style, Deep Questions, Micro Interventions, Confidence Calculator, Vector Storytelling
# All 6 Phase 2-3 components integrated and tested
from selfology_bot.monitoring import initialize_onboarding_monitoring  # 🆕 Monitoring System
from selfology_bot.bot.states import OnboardingStates, ChatStates  # 🔧 Extracted to module

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# FSM States moved to: selfology_bot/bot/states.py

# Конфигурация (из .env.development)
BOT_TOKEN = "8197893707:AAEbGC7r_4GGWXvgah-q-mLw5pp7YIxhK9g"

# Database config - selfology-postgres контейнер
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "5434"))
DB_USER = os.getenv("DB_USER", "selfology_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "selfology_secure_2024")
DB_NAME = os.getenv("DB_NAME", "selfology")
DB_SCHEMA = "selfology"

# Redis FSM Storage config
REDIS_FSM_HOST = os.getenv("REDIS_FSM_HOST", "localhost")
REDIS_FSM_PORT = int(os.getenv("REDIS_FSM_PORT", "6379"))
REDIS_FSM_DB = int(os.getenv("REDIS_FSM_DB", "1"))

# DEBUG конфигурация для отладки workflow
DEBUG_MESSAGES = True  # Показывать MESSAGE_ID в сообщениях для отладки
ADMIN_USER_ID = "98005572"  # ID администратора для admin команд

# Bot instance lock key for preventing duplicate instances
BOT_INSTANCE_LOCK_KEY = "selfology:bot:instance_lock"
BOT_INSTANCE_LOCK_TTL = 30  # seconds - will refresh periodically

class SelfologyController:
    """Простой контроллер Selfology бота"""

    def __init__(self):
        """
        Инициализация контроллера бота

        ВАЖНО: Redis FSM Storage используется для персистентности состояний
        между перезапусками и предотвращения конфликтов при множественных экземплярах
        """
        self.bot = Bot(token=BOT_TOKEN)

        # 🔴 КРИТИЧНО: RedisStorage вместо MemoryStorage для персистентности FSM состояний
        # Используем отдельную DB (1) для FSM, чтобы не конфликтовать с кешем (DB 0)
        redis_storage = RedisStorage.from_url(
            f"redis://{REDIS_FSM_HOST}:{REDIS_FSM_PORT}/{REDIS_FSM_DB}"
        )
        self.dp = Dispatcher(storage=redis_storage)
        self.messages = get_message_service(debug_mode=DEBUG_MESSAGES)

        # Redis client для instance locking
        self.redis_client: Optional[redis.Redis] = None
        self.instance_lock_task: Optional[asyncio.Task] = None
        self._shutdown_event = asyncio.Event()

        # Инициализация баз данных
        self.db_service = None
        self.user_dao = None
        self.onboarding_dao = None

        # Инициализация системы онбординга - ТОЛЬКО новая система
        # self.onboarding_service = None  # DISABLED - старый SimpleOnboardingService
        self.onboarding_orchestrator = OnboardingOrchestratorV2()  # 🆕 v2 cluster system

        # 🆕 Инициализация Chat Coach Service
        self.chat_coach = None  # Инициализируется после db_service

        # 🆕 Инициализация Monitoring System
        self.monitoring_system = None  # Инициализируется после db_service
        self.monitoring_task: Optional[asyncio.Task] = None

        # Регистрируем все handlers
        self._register_handlers()

        logger.info("🤖 Selfology Controller initialized")
        logger.info("🎨 MessageService integrated")
        logger.info("🗄 DatabaseService prepared")
        logger.info("🔴 Redis FSM Storage configured")
        logger.info("✅ Ready to start polling")

    async def _send_long_message(self, message: Message, text: str, parse_mode: str = 'HTML'):
        """
        Отправляет длинное сообщение, разбивая его на части если нужно

        Telegram лимит: 4096 символов
        Разбивает по параграфам чтобы не резать посередине предложения
        """
        MAX_LENGTH = 4000  # Оставляем запас

        if len(text) <= MAX_LENGTH:
            await message.answer(text, parse_mode=parse_mode)
            return

        # Разбиваем по параграфам
        parts = []
        current_part = ""

        # Сначала пробуем разбить по двойным переносам строк (параграфы)
        paragraphs = text.split('\n\n')

        for paragraph in paragraphs:
            # Если параграф сам по себе слишком длинный
            if len(paragraph) > MAX_LENGTH:
                # Разбиваем по одинарным переносам
                lines = paragraph.split('\n')
                for line in lines:
                    if len(current_part) + len(line) + 1 <= MAX_LENGTH:
                        current_part += line + '\n'
                    else:
                        if current_part:
                            parts.append(current_part.strip())
                        current_part = line + '\n'
            else:
                # Проверяем поместится ли параграф
                if len(current_part) + len(paragraph) + 2 <= MAX_LENGTH:
                    current_part += paragraph + '\n\n'
                else:
                    if current_part:
                        parts.append(current_part.strip())
                    current_part = paragraph + '\n\n'

        # Добавляем последнюю часть
        if current_part:
            parts.append(current_part.strip())

        # Отправляем все части
        for i, part in enumerate(parts):
            # Добавляем номер части если их больше 1
            if len(parts) > 1:
                part_indicator = f"\n\n<i>📄 Часть {i+1}/{len(parts)}</i>"
                await message.answer(part + part_indicator, parse_mode=parse_mode)
            else:
                await message.answer(part, parse_mode=parse_mode)

            # Небольшая задержка между сообщениями
            if i < len(parts) - 1:
                await asyncio.sleep(0.3)

    async def _log_state_change(self, handler, event, data):
        """
        Middleware для логирования FSM state transitions

        Логирует все изменения состояний для отладки и мониторинга
        """
        # Получаем user_id из event (поддерживаем Message и CallbackQuery)
        user_id = None
        if hasattr(event, 'from_user') and event.from_user:
            user_id = event.from_user.id

        state: FSMContext = data.get("state")
        if state:
            current_state = await state.get_state()

            # Логируем before handler
            if user_id:
                logger.debug(
                    f"🔄 FSM State [BEFORE]: user={user_id}, "
                    f"state={current_state or 'None'}, "
                    f"handler={handler.__name__ if hasattr(handler, '__name__') else 'unknown'}"
                )

        # Выполняем handler
        result = await handler(event, data)

        # Логируем after handler
        if state and user_id:
            new_state = await state.get_state()
            if new_state != current_state:
                logger.info(
                    f"✨ FSM State [CHANGED]: user={user_id}, "
                    f"{current_state or 'None'} → {new_state or 'None'}"
                )

        return result

    def _register_handlers(self):
        """Регистрация всех обработчиков"""

        # 🔄 Регистрируем middleware для логирования state transitions
        self.dp.message.middleware(self._log_state_change)
        self.dp.callback_query.middleware(self._log_state_change)
        logger.info("🔄 FSM state transition logging enabled")

        # Основные команды
        self.dp.message.register(self.cmd_start, CommandStart())
        self.dp.message.register(self.cmd_help, Command("help"))
        self.dp.message.register(self.cmd_profile, Command("profile"))
        self.dp.message.register(self.cmd_onboarding, Command("onboarding"))
        self.dp.message.register(self.cmd_onboarding_profile, Command("onboarding_profile"))  # 🆕 Детальный профиль онбординга
        self.dp.message.register(self.cmd_chat, Command("chat"))  # 🆕 AI Coach Chat

        # Admin команды для отладки
        self.dp.message.register(self.cmd_debug_on, Command("debug_on"))
        self.dp.message.register(self.cmd_debug_off, Command("debug_off"))
        self.dp.message.register(self.cmd_debug_status, Command("debug_status"))
        self.dp.message.register(self.cmd_reload_templates, Command("reload_templates"))

        # Callback обработчики
        self.dp.callback_query.register(self.callback_main_menu, F.data == "main_menu")
        self.dp.callback_query.register(self.callback_help, F.data == "help")
        self.dp.callback_query.register(self.callback_profile, F.data == "profile")

        # GDPR handlers
        self.dp.callback_query.register(self.callback_gdpr_details, F.data == "gdpr_details")
        self.dp.callback_query.register(self.callback_gdpr_accept, F.data == "gdpr_accept")
        self.dp.callback_query.register(self.callback_gdpr_decline, F.data == "gdpr_decline")

        # 🆕 Onboarding handlers (для новой системы)
        self.dp.message.register(
            self.handle_onboarding_answer,
            OnboardingStates.waiting_for_answer
        )

        # 🆕 Onboarding callback handlers
        self.dp.callback_query.register(self.callback_skip_question, F.data == "skip_question")
        self.dp.callback_query.register(self.callback_end_session, F.data == "end_session")
        self.dp.callback_query.register(self.callback_flag_question, F.data == "flag_question")
        self.dp.callback_query.register(self.callback_end_onboarding, F.data == "end_onboarding")
        self.dp.callback_query.register(self.callback_continue_onboarding, F.data == "continue_onboarding")
        self.dp.callback_query.register(self.callback_process_orphaned, F.data.startswith("process_orphaned:"))

        # 🆕 Блочная система программ - callback handlers
        self.dp.callback_query.register(self.callback_mode_auto, F.data == "mode_auto")
        self.dp.callback_query.register(self.callback_mode_program, F.data == "mode_program")
        self.dp.callback_query.register(self.callback_select_program, F.data.startswith("select_program:"))
        self.dp.callback_query.register(self.callback_back_to_mode_selection, F.data == "back_to_mode_selection")
        self.dp.callback_query.register(self.callback_continue_session, F.data == "continue_session")
        self.dp.callback_query.register(self.callback_continue_program_block, F.data == "continue_program_block")
        self.dp.callback_query.register(self.callback_pause_program, F.data == "pause_program")
        self.dp.callback_query.register(self.callback_skip_program_question, F.data == "skip_program_question")

        # 🆕 v2 кластерная система - дополнительные handlers
        self.dp.callback_query.register(self.callback_mode_finish, F.data == "mode_finish")
        self.dp.callback_query.register(self.callback_continue_next_cluster, F.data == "continue_next_cluster")
        self.dp.callback_query.register(self.callback_pause_cluster, F.data == "pause_cluster")
        self.dp.callback_query.register(self.callback_continue_cluster, F.data.startswith("continue_cluster:"))

        # 🆕 Обработчик выбора программы по номеру
        self.dp.message.register(
            self.handle_program_number_input,
            OnboardingStates.choosing_program
        )

        # 🆕 Program answer handler
        self.dp.message.register(
            self.handle_program_answer,
            OnboardingStates.waiting_program_answer
        )

        # 🆕 Chat handlers
        self.dp.callback_query.register(self.callback_start_chat, F.data == "start_chat")
        self.dp.message.register(self.handle_chat_message, ChatStates.active)

        # Feature handlers (заглушки)
        self.dp.callback_query.register(self.callback_coming_soon, F.data == "assessments")
        self.dp.callback_query.register(self.callback_coming_soon, F.data == "profile")
        self.dp.callback_query.register(self.callback_coming_soon, F.data == "goals")
        self.dp.callback_query.register(self.callback_coming_soon, F.data == "diary")
        self.dp.callback_query.register(self.callback_coming_soon, F.data == "settings")

        # Обработчик неизвестных команд
        self.dp.message.register(self.handle_unknown, F.text)

        logger.info("📋 All handlers registered")

    async def cmd_start(self, message: Message, state: FSMContext):
        """Команда /start - точка входа"""

        user_name = message.from_user.full_name or "Друг"
        telegram_id = str(message.from_user.id)
        logger.info(f"👤 User started: {user_name} (ID: {telegram_id})")

        # 🗄 Проверяем пользователя в базе данных selfology
        telegram_data = {
            'id': message.from_user.id,
            'username': message.from_user.username,
            'first_name': message.from_user.first_name,
            'last_name': message.from_user.last_name
        }

        user = await self.user_dao.get_or_create_user(telegram_data)

        # Проверяем статус пользователя (только GDPR согласие важно для /start)
        has_consent = user.get('consent', False)

        if not has_consent:
            # 🆕 Новый пользователь без согласия - показываем приветствие с GDPR
            text = self.messages.get_message('welcome', 'ru', 'onboarding')
            keyboard = self.messages.get_keyboard('gdpr_consent', 'ru')

            await message.answer(text, reply_markup=keyboard, parse_mode='HTML')
            await state.set_state(OnboardingStates.gdpr_consent)
        else:
            # ✅ Пользователь с согласием - показываем главное меню
            # onboarding_completed НЕ влияет на /start - это отдельный процесс через /onboarding
            await self._show_main_menu(message, user_name)

    async def cmd_help(self, message: Message):
        """Команда /help"""

        text = self.messages.get_message('help', 'ru', 'general')
        keyboard = self.messages.get_keyboard('back_to_menu', 'ru')

        await message.answer(text, reply_markup=keyboard, parse_mode='HTML')

    async def cmd_profile(self, message: Message):
        """Команда /profile - показать профиль пользователя"""

        telegram_id = str(message.from_user.id)
        logger.info(f"📊 Profile requested by user {telegram_id}")

        # Получаем данные профиля из базы данных
        profile_data = await self.user_dao.get_user_profile_data(telegram_id)

        if profile_data:
            text = self.messages.get_message('user_profile', 'ru', 'general', **profile_data)
            keyboard = self.messages.get_keyboard('profile_actions', 'ru')

            await message.answer(text, reply_markup=keyboard, parse_mode='HTML')
        else:
            # Пользователь не найден
            text = self.messages.get_message('access_denied', 'ru', 'errors',
                access_reason="Профиль не найден",
                action_suggestion="Пройдите регистрацию с помощью /start"
            )
            keyboard = self.messages.get_keyboard('back_to_menu', 'ru')

            await message.answer(text, reply_markup=keyboard, parse_mode='HTML')

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

    async def _show_main_menu(self, message: Message, user_name: str):
        """Показать главное меню в новом сообщении"""

        status_message = f"Добро пожаловать, {user_name}!"

        text = self.messages.get_message('main_menu', 'ru', 'general', status_message=status_message)
        keyboard = self.messages.get_keyboard('main_menu', 'ru')

        await message.answer(text, reply_markup=keyboard, parse_mode='HTML')

    async def _show_main_menu_callback(self, callback: CallbackQuery, user_name: str):
        """Показать главное меню через callback"""

        status_message = f"Добро пожаловать, {user_name}!"

        text = self.messages.get_message('main_menu', 'ru', 'general', status_message=status_message)
        keyboard = self.messages.get_keyboard('main_menu', 'ru')

        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode='HTML')

    async def _acquire_instance_lock(self) -> bool:
        """
        Получить блокировку для предотвращения множественных экземпляров бота

        Returns:
            True если блокировка получена, False если другой экземпляр уже запущен
        """
        try:
            # Создаем Redis клиент если еще не создан
            if not self.redis_client:
                self.redis_client = await redis.Redis(
                    host=REDIS_FSM_HOST,
                    port=REDIS_FSM_PORT,
                    db=REDIS_FSM_DB,
                    decode_responses=True
                )

            # Пытаемся установить блокировку с TTL
            # SET NX (only if Not eXists) с expiration
            lock_acquired = await self.redis_client.set(
                BOT_INSTANCE_LOCK_KEY,
                f"pid:{os.getpid()}:started:{datetime.now().isoformat()}",
                nx=True,
                ex=BOT_INSTANCE_LOCK_TTL
            )

            if lock_acquired:
                logger.info(f"✅ Bot instance lock acquired (PID: {os.getpid()})")
                return True
            else:
                # Проверяем кто держит блокировку
                existing_lock = await self.redis_client.get(BOT_INSTANCE_LOCK_KEY)
                logger.error(
                    f"❌ Another bot instance is already running!\n"
                    f"   Lock holder: {existing_lock}\n"
                    f"   Please stop other instances before starting a new one."
                )
                return False

        except Exception as e:
            logger.error(f"❌ Failed to acquire instance lock: {e}")
            return False

    async def _refresh_instance_lock(self):
        """
        Периодически обновлять блокировку экземпляра чтобы показать что бот активен
        """
        try:
            while not self._shutdown_event.is_set():
                # Обновляем TTL блокировки
                await self.redis_client.expire(BOT_INSTANCE_LOCK_KEY, BOT_INSTANCE_LOCK_TTL)
                logger.debug(f"🔄 Instance lock refreshed (TTL: {BOT_INSTANCE_LOCK_TTL}s)")

                # Ждем перед следующим обновлением (обновляем каждые 15 секунд)
                await asyncio.sleep(BOT_INSTANCE_LOCK_TTL // 2)

        except asyncio.CancelledError:
            logger.info("🛑 Instance lock refresh task cancelled")
        except Exception as e:
            logger.error(f"❌ Error refreshing instance lock: {e}")

    async def _release_instance_lock(self):
        """
        Освободить блокировку экземпляра при shutdown
        """
        try:
            if self.redis_client:
                await self.redis_client.delete(BOT_INSTANCE_LOCK_KEY)
                logger.info("✅ Bot instance lock released")
        except Exception as e:
            logger.error(f"❌ Error releasing instance lock: {e}")

    async def _setup_signal_handlers(self):
        """
        Настроить обработчики сигналов для graceful shutdown
        """
        loop = asyncio.get_event_loop()

        def signal_handler(sig):
            logger.info(f"🛑 Received signal {sig}, initiating graceful shutdown...")
            self._shutdown_event.set()

        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, lambda s=sig: signal_handler(s))

    async def start_polling(self):
        """Запуск бота с проверкой на дублирующие экземпляры"""

        try:
            # 🔒 КРИТИЧНО: Проверяем что нет других экземпляров
            lock_acquired = await self._acquire_instance_lock()
            if not lock_acquired:
                logger.error("🚫 Aborting startup - another instance is running")
                return

            # 🔄 Запускаем task для обновления блокировки
            self.instance_lock_task = asyncio.create_task(self._refresh_instance_lock())

            # 📡 Настраиваем signal handlers для graceful shutdown
            await self._setup_signal_handlers()

            # 🗄 Инициализация базы данных
            self.db_service = DatabaseService(
                host=DB_HOST,
                port=DB_PORT,
                user=DB_USER,
                password=DB_PASSWORD,
                database=DB_NAME,
                schema=DB_SCHEMA
            )
            db_initialized = await self.db_service.initialize()

            if not db_initialized:
                logger.error("❌ Failed to initialize database")
                await self._release_instance_lock()
                return

            # Создаем DAO объекты
            self.user_dao = UserDAO(self.db_service)
            self.onboarding_dao = OnboardingDAO(self.db_service)  # 🆕 NEW clean version

            # 🆕 Передаём DB pool в OrchestratorV2
            await self.onboarding_orchestrator.set_db_pool(self.db_service.pool)
            logger.info("🎯 OrchestratorV2 connected to database")

            # 🔥 PHASE 2-3 ACTIVE! Инициализируем Chat Coach Service
            self.chat_coach = ChatCoachService(self.db_service.pool)
            logger.info("🔥 ChatCoachService ACTIVE with all 6 Phase 2-3 components!")

            # 🆕 Инициализируем Monitoring System
            monitoring_enabled = os.getenv("MONITORING_ENABLED", "true").lower() == "true"
            if monitoring_enabled:
                admin_ids_str = os.getenv("MONITORING_ADMIN_IDS", "98005572")
                admin_ids = [int(id.strip()) for id in admin_ids_str.split(",") if id.strip()]

                self.monitoring_system = await initialize_onboarding_monitoring(
                    db_config={
                        "host": DB_HOST,
                        "port": DB_PORT,
                        "user": DB_USER,
                        "password": DB_PASSWORD,
                        "database": DB_NAME
                    },
                    bot_token=BOT_TOKEN,
                    admin_chat_ids=admin_ids,
                    enable_alerting=os.getenv("TELEGRAM_ALERTS_ENABLED", "true").lower() == "true",
                    enable_auto_retry=os.getenv("AUTO_RETRY_ENABLED", "true").lower() == "true"
                )
                logger.info("📊 Onboarding Monitoring System initialized")
            else:
                logger.info("📊 Monitoring System disabled (MONITORING_ENABLED=false)")

            # Создаем новые чистые таблицы онбординга
            await self.onboarding_dao.create_onboarding_tables()

            # Проверяем подключение к правильной схеме
            async with self.db_service.get_connection() as conn:
                schema = await conn.fetchval("SELECT current_schema()")

            # Проверяем MessageService
            available_locales = self.messages.get_available_locales()
            available_categories = self.messages.get_available_categories('ru')

            print("🚀 Selfology Bot Controller")
            print("=" * 40)
            print("✅ Simple architecture")
            print("✅ MessageService integrated")
            print(f"✅ Database connected to schema: {schema}")
            print(f"✅ Redis FSM Storage: {REDIS_FSM_HOST}:{REDIS_FSM_PORT}/{REDIS_FSM_DB}")
            print(f"✅ Instance lock: Active (PID: {os.getpid()})")
            print(f"✅ Available locales: {available_locales}")
            print(f"✅ Available categories: {available_categories}")
            print("🎨 Beautiful messages system active")
            print("🗄 Database operations ready")
            print("🔗 Ready for users!")
            print("=" * 40)

            logger.info("Starting Selfology Bot polling...")

            # 🆕 Запускаем Monitoring System как background task
            if self.monitoring_system:
                self.monitoring_task = asyncio.create_task(self.monitoring_system.start())
                logger.info("📊 Monitoring System started")

            # Запускаем polling с graceful shutdown через shutdown_event
            polling_task = asyncio.create_task(self.dp.start_polling(self.bot))

            # Ждем сигнала shutdown
            await self._shutdown_event.wait()

            # Graceful shutdown
            logger.info("🛑 Initiating graceful shutdown...")
            polling_task.cancel()

            try:
                await polling_task
            except asyncio.CancelledError:
                logger.info("✅ Polling task cancelled")

        except KeyboardInterrupt:
            logger.info("Bot stopped by user (Ctrl+C)")
        except Exception as e:
            logger.error(f"Bot error: {e}", exc_info=True)
            raise
        finally:
            # Всегда освобождаем ресурсы
            await self.stop()

    async def stop(self):
        """
        Graceful остановка бота с освобождением всех ресурсов

        АРХИТЕКТУРНЫЕ УЛУЧШЕНИЯ (October 2025):
        - Ждем завершения background tasks в OnboardingOrchestrator
        - Proper shutdown sequence с таймаутами
        - Observability статистики shutdown
        """
        logger.info("🛑 Stopping bot gracefully...")

        try:
            # ✅ 1. Останавливаем OnboardingOrchestrator background tasks
            if self.onboarding_orchestrator:
                logger.info("🔬 Shutting down OnboardingOrchestrator background tasks...")
                shutdown_stats = await self.onboarding_orchestrator.shutdown(timeout=30.0)

                logger.info(
                    f"📊 Orchestrator shutdown stats: "
                    f"status={shutdown_stats['status']}, "
                    f"completed={shutdown_stats['tasks_completed']}, "
                    f"cancelled={shutdown_stats['tasks_cancelled']}, "
                    f"time={shutdown_stats['shutdown_time']:.2f}s"
                )

            # ✅ 2. Останавливаем Monitoring System
            if self.monitoring_task and not self.monitoring_task.done():
                logger.info("📊 Shutting down Monitoring System...")
                self.monitoring_task.cancel()
                try:
                    await self.monitoring_task
                except asyncio.CancelledError:
                    pass
                logger.info("✅ Monitoring System stopped")

            # 3. Останавливаем task обновления блокировки
            if self.instance_lock_task and not self.instance_lock_task.done():
                self.instance_lock_task.cancel()
                try:
                    await self.instance_lock_task
                except asyncio.CancelledError:
                    pass
                logger.info("✅ Instance lock refresh task stopped")

            # 4. Освобождаем блокировку экземпляра
            await self._release_instance_lock()

            # 5. Закрываем Redis клиент
            if self.redis_client:
                await self.redis_client.close()
                logger.info("✅ Redis client closed")

            # 6. Закрываем Telegram bot session
            await self.bot.session.close()
            logger.info("✅ Bot session closed")

            # 7. Закрываем database service
            if self.db_service:
                await self.db_service.close()
                logger.info("✅ Database connection closed")

            logger.info("🎉 Bot stopped successfully")

        except Exception as e:
            logger.error(f"❌ Error during shutdown: {e}", exc_info=True)

    async def cmd_onboarding_profile(self, message: Message):
        """
        Команда /onboarding_profile - детальный профиль онбординга

        Запускает onboarding_profiler.py и показывает результат в Telegram
        """
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

        user_id = message.from_user.id
        logger.info(f"🔬 Onboarding profile requested by user {user_id}")

        # Отправляем сообщение что обрабатываем
        processing_msg = await message.answer("🔬 Анализирую ваш профиль онбординга...")

        try:
            import subprocess
            import re

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

                # Разбиваем по строкам для более точного контроля
                lines = clean_output.split('\n')
                parts = []
                current_part = ""

                for line in lines:
                    # Проверяем не превысит ли добавление строки лимит
                    if len(current_part) + len(line) + 1 > 3900:  # Оставляем запас для ``` и \n
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

                    # Если была только одна часть, добавляем клавиатуру отдельным сообщением
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
            await processing_msg.edit_text(
                "⏱ Таймаут: профилировщик работал слишком долго"
            )

        except Exception as e:
            await processing_msg.edit_text(
                f"❌ Ошибка: {str(e)[:200]}"
            )

    async def cmd_debug_on(self, message: Message):
        """Включить debug режим (только для админа)"""

        if str(message.from_user.id) != ADMIN_USER_ID:
            await message.answer("❌ Команда доступна только администратору")
            return

        global DEBUG_MESSAGES
        DEBUG_MESSAGES = True
        self.messages = get_message_service(debug_mode=True)

        await message.answer("🔧 <b>DEBUG режим ВКЛЮЧЕН</b>\n\nТеперь все сообщения будут содержать:\n• MESSAGE_ID\n• Имя файла шаблона\n\nДля отключения: /debug_off", parse_mode='HTML')
        logger.info("🔧 Debug mode ENABLED by admin")

    async def cmd_debug_off(self, message: Message):
        """Выключить debug режим (только для админа)"""

        if str(message.from_user.id) != ADMIN_USER_ID:
            await message.answer("❌ Команда доступна только администратору")
            return

        global DEBUG_MESSAGES
        DEBUG_MESSAGES = False
        self.messages = get_message_service(debug_mode=False)

        await message.answer("✅ <b>DEBUG режим ОТКЛЮЧЕН</b>\n\nСообщения теперь отображаются без отладочной информации.\n\nДля включения: /debug_on", parse_mode='HTML')
        logger.info("✅ Debug mode DISABLED by admin")

    async def cmd_debug_status(self, message: Message):
        """Статус debug режима (только для админа)"""

        if str(message.from_user.id) != ADMIN_USER_ID:
            await message.answer("❌ Команда доступна только администратору")
            return

        status = "ВКЛЮЧЕН" if DEBUG_MESSAGES else "ОТКЛЮЧЕН"
        emoji = "🔧" if DEBUG_MESSAGES else "✅"

        # Статистика сообщений
        available_locales = self.messages.get_available_locales()
        available_categories = self.messages.get_available_categories('ru')

        # ✅ Observability - статус background tasks
        tasks_status = self.onboarding_orchestrator.get_background_tasks_status()

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

    async def cmd_reload_templates(self, message: Message):
        """Перезагрузить шаблоны сообщений (только для админа)"""

        if str(message.from_user.id) != ADMIN_USER_ID:
            await message.answer("❌ Команда доступна только администратору")
            return

        try:
            # Перезагружаем шаблоны
            self.messages.reload_templates()

            # Получаем статистику после перезагрузки
            available_locales = self.messages.get_available_locales()
            available_categories = self.messages.get_available_categories('ru')

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
            error_text = f"❌ <b>Ошибка перезагрузки:</b>\n\n<code>{e}</code>\n\nПроверьте синтаксис JSON файлов."
            await message.answer(error_text, parse_mode='HTML')
            logger.error(f"❌ Template reload failed: {e}")


async def main():
    """Главная функция"""

    print(f"🚀 Starting Selfology Bot with HOT RELOAD - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    controller = SelfologyController()

    try:
        await controller.start_polling()
    finally:
        await controller.stop()


if __name__ == "__main__":
    asyncio.run(main())
