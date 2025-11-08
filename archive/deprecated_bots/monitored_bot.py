#!/usr/bin/env python3
"""
Monitored Selfology Telegram Bot with comprehensive logging and error handling.
"""

import asyncio
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# Import logging and monitoring system
from selfology_bot.core.logging import LoggerMixin, get_logger, bot_logger, user_logger
from selfology_bot.core.error_handling import (
    handle_errors, ErrorCode, error_tracker, 
    SelfologyException, UserError
)
from selfology_bot.core.monitoring import (
    track_user_action, track_performance, increment_counter,
    metrics_collector, bot_analytics, performance_monitor
)

# Bot configuration
BOT_TOKEN = "8197893707:AAEbGC7r_4GGWXvgah-q-mLw5pp7YIxhK9g"

# States
class UserStates(StatesGroup):
    waiting_for_consent = State()
    onboarding = State()
    chatting = State()

# Simple user storage (in memory for testing)
users_db = {}


class MonitoredBot(LoggerMixin):
    """
    Main bot class with integrated logging and monitoring.
    """
    
    def __init__(self):
        self.bot = Bot(token=BOT_TOKEN)
        self.dp = Dispatcher(storage=MemoryStorage())
        self.register_handlers()
        self.start_time = datetime.now(timezone.utc)
        
        bot_logger.info("Bot initialized", extra={
            'context': {'bot_id': self.bot.id, 'start_time': self.start_time.isoformat()}
        })
    
    def register_handlers(self):
        """Register all bot handlers"""
        self.dp.message.register(self.cmd_start, CommandStart())
        self.dp.message.register(self.cmd_help, Command("help"))
        self.dp.message.register(self.handle_chat_message, UserStates.chatting)
        
        self.dp.callback_query.register(self.consent_accepted, F.data == "consent_yes")
        self.dp.callback_query.register(self.consent_declined, F.data == "consent_no")
        self.dp.callback_query.register(self.show_consent_details, F.data == "consent_details")
        self.dp.callback_query.register(self.start_assessment, F.data == "start_assessment")
        self.dp.callback_query.register(self.handle_assessment_answer, F.data.startswith("answer_"))
        self.dp.callback_query.register(self.start_chat, F.data == "start_chat")
        self.dp.callback_query.register(self.show_profile, F.data == "show_profile")
    
    @handle_errors(ErrorCode.BOT_UPDATE_ERROR, "Ошибка обработки команды /start")
    async def cmd_start(self, message: Message, state: FSMContext):
        """Handle /start command with comprehensive logging"""
        
        start_time = time.time()
        user_id = message.from_user.id
        user_name = message.from_user.first_name or "Friend"
        
        try:
            # Track user action
            track_user_action(user_id, "start_command", 
                            username=message.from_user.username,
                            first_name=user_name)
            
            # Log user action
            self.log_user_action("start_command", user_id, user_name, 
                               chat_id=message.chat.id)
            
            # Check if user exists
            if user_id not in users_db:
                # New user
                users_db[user_id] = {
                    "id": user_id,
                    "name": user_name,
                    "username": message.from_user.username,
                    "consent": False,
                    "onboarded": False,
                    "first_seen": datetime.now(timezone.utc).isoformat()
                }
                
                increment_counter("new_users")
                self.log_user_action("new_user_registered", user_id, user_name)
                
                await self.show_gdpr_consent(message, state)
            else:
                # Existing user
                increment_counter("returning_users")
                self.log_user_action("returning_user", user_id, user_name)
                
                await self.show_main_menu(message, state)
            
            # Track performance
            response_time = time.time() - start_time
            track_performance("start_command_response_time", response_time,
                            user_id=str(user_id))
            
        except Exception as e:
            # Log error with context
            self.log_error("START_COMMAND_ERROR", f"Error in start command: {e}",
                         user_id=user_id, username=user_name)
            raise
    
    async def show_gdpr_consent(self, message: Message, state: FSMContext):
        """Show GDPR consent form"""
        
        user_id = message.from_user.id
        
        consent_text = f"""
🌟 Добро пожаловать в Selfology!

Привет! Я — ваш персональный AI-коуч для глубокого самопознания. 

🎯 **Что я умею:**
✅ Психологический анализ личности (Big Five)
✅ Персонализированные инсайты и советы
✅ Умный дневник с выявлением паттернов
✅ Трекинг целей и прогресса

🔒 **Обработка данных:**
Для работы мне нужно обрабатывать ваши сообщения и ответы на тесты. 
Все данные хранятся безопасно и используются только для персонализации.

Согласны на обработку данных?
        """
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Согласен", callback_data="consent_yes")],
            [InlineKeyboardButton(text="❌ Не согласен", callback_data="consent_no")],
            [InlineKeyboardButton(text="📋 Подробнее", callback_data="consent_details")]
        ])
        
        await message.answer(consent_text, reply_markup=keyboard)
        await state.set_state(UserStates.waiting_for_consent)
        
        # Log consent form shown
        self.log_user_action("gdpr_consent_shown", user_id, 
                           context={"message_length": len(consent_text)})
    
    @handle_errors(ErrorCode.USER_INPUT_INVALID, "Ошибка обработки согласия")
    async def consent_accepted(self, callback: types.CallbackQuery, state: FSMContext):
        """Handle consent acceptance with logging"""
        
        user_id = callback.from_user.id
        users_db[user_id]["consent"] = True
        users_db[user_id]["consent_timestamp"] = datetime.now(timezone.utc).isoformat()
        
        # Track consent acceptance
        track_user_action(user_id, "gdpr_consent_accepted")
        self.log_user_action("gdpr_consent_accepted", user_id)
        increment_counter("gdpr_consents_accepted")
        
        welcome_text = """
🎉 Отлично! Добро пожаловать в Selfology!

Давайте начнем ваше путешествие самопознания. 

**Первый шаг** — пройти быструю психологическую оценку (5-7 минут):
• Определим ваши основные личностные черты
• Выявим жизненные ценности и приоритеты  
• Настроим персонализированные рекомендации

После этого вы сможете:
💬 Общаться со мной как с личным коучем
📊 Получать инсайты о себе
🎯 Отслеживать прогресс по целям
        """
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🚀 Начать оценку", callback_data="start_assessment")],
            [InlineKeyboardButton(text="💬 Просто поговорить", callback_data="start_chat")]
        ])
        
        await callback.message.edit_text(welcome_text, reply_markup=keyboard)
        await state.set_state(UserStates.onboarding)
    
    @handle_errors(ErrorCode.USER_INPUT_INVALID, "Ошибка отказа от согласия")
    async def consent_declined(self, callback: types.CallbackQuery, state: FSMContext):
        """Handle consent decline"""
        
        user_id = callback.from_user.id
        
        # Track consent decline
        track_user_action(user_id, "gdpr_consent_declined")
        self.log_user_action("gdpr_consent_declined", user_id)
        increment_counter("gdpr_consents_declined")
        
        decline_text = """
😔 Понимаю ваши опасения по поводу конфиденциальности.

К сожалению, без согласия на обработку данных я не смогу предоставить персонализированный коучинг.

Если передумаете, просто нажмите /start снова.

Берегите себя! 👋
        """
        
        await callback.message.edit_text(decline_text)
        await state.clear()
    
    async def show_consent_details(self, callback: types.CallbackQuery):
        """Show detailed consent information"""
        
        user_id = callback.from_user.id
        track_user_action(user_id, "gdpr_details_viewed")
        
        details_text = """
📋 **Подробная информация о обработке данных**

**Какие данные обрабатываются:**
• Telegram ID и имя пользователя
• Ответы на психологические тесты
• Сообщения в чате для анализа контекста
• Аналитические данные о прогрессе

**Как данные защищены:**
🔒 Шифрование при передаче и хранении
🏠 Данные не покидают наши серверы
🚫 Никогда не передаем третьим лицам
♻️ Можете удалить в любой момент

**Цель обработки:**
Предоставление персонализированного AI-коучинга для вашего развития

**Ваши права:**
• Просмотр всех данных (команда /export)
• Удаление данных (команда /delete)
• Отзыв согласия в любой момент

Полная политика: https://selfology.me/privacy
        """
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Принять", callback_data="consent_yes")],
            [InlineKeyboardButton(text="❌ Отклонить", callback_data="consent_no")]
        ])
        
        await callback.message.edit_text(details_text, reply_markup=keyboard)
    
    @handle_errors(ErrorCode.USER_INPUT_INVALID, "Ошибка начала оценки")
    async def start_assessment(self, callback: types.CallbackQuery, state: FSMContext):
        """Start psychological assessment with monitoring"""
        
        user_id = callback.from_user.id
        start_time = time.time()
        
        track_user_action(user_id, "assessment_started")
        self.log_user_action("assessment_started", user_id)
        increment_counter("assessments_started")
        
        assessment_text = """
🧠 **Психологическая оценка личности**

Сейчас я задам вам несколько вопросов, чтобы понять:
• Ваши основные черты личности (Big Five)
• Жизненные ценности и приоритеты
• Текущие цели и мотивацию

Это займет 5-7 минут и поможет мне давать вам более точные советы.

**Первый вопрос:**
Насколько вы согласны с утверждением: "Я часто экспериментирую с новыми идеями и подходами"
        """
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💯 Полностью согласен", callback_data="answer_5")],
            [InlineKeyboardButton(text="✅ Скорее согласен", callback_data="answer_4")],
            [InlineKeyboardButton(text="🤔 Нейтрально", callback_data="answer_3")],
            [InlineKeyboardButton(text="❌ Скорее не согласен", callback_data="answer_2")],
            [InlineKeyboardButton(text="🚫 Совершенно не согласен", callback_data="answer_1")]
        ])
        
        await callback.message.edit_text(assessment_text, reply_markup=keyboard)
        
        # Track response time
        response_time = time.time() - start_time
        track_performance("assessment_display_time", response_time, user_id=str(user_id))
    
    @handle_errors(ErrorCode.USER_INPUT_INVALID, "Ошибка обработки ответа")
    async def handle_assessment_answer(self, callback: types.CallbackQuery, state: FSMContext):
        """Handle assessment answer with detailed logging"""
        
        user_id = callback.from_user.id
        score = int(callback.data.split("_")[1])
        
        # Track answer
        track_user_action(user_id, "assessment_answer_given", 
                        score=score, question="openness_1")
        
        # Log detailed answer
        self.log_user_action("assessment_answer", user_id,
                           context={
                               "question": "openness_experiment", 
                               "score": score,
                               "answer_timestamp": datetime.now(timezone.utc).isoformat()
                           })
        
        # For demo - show completion
        completion_text = f"""
🎉 **Оценка завершена!**

Спасибо за ответы! Я проанализировал ваш профиль.

**Ваша оценка открытости к новому опыту:** {score}/5

📊 **Анализ личности:**
{self._generate_personality_analysis(score)}

На основе ваших ответов я буду давать персонализированные рекомендации.

**Что дальше?**
💬 Можете задать любой вопрос или поделиться тем, что вас беспокоит
📊 Посмотреть полный профиль: /profile
🎯 Настроить цели: /goals

Просто напишите мне что угодно, и я отвечу с учетом вашей личности!
        """
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💬 Начать чат", callback_data="start_chat")],
            [InlineKeyboardButton(text="📊 Мой профиль", callback_data="show_profile")]
        ])
        
        # Mark user as onboarded
        users_db[user_id]["onboarded"] = True
        users_db[user_id]["assessment_completed"] = datetime.now(timezone.utc).isoformat()
        users_db[user_id]["openness_score"] = score
        
        # Track completion
        track_user_action(user_id, "assessment_completed", final_score=score)
        increment_counter("assessments_completed")
        
        await callback.message.edit_text(completion_text, reply_markup=keyboard)
        await state.set_state(UserStates.chatting)
    
    def _generate_personality_analysis(self, openness_score: int) -> str:
        """Generate personality analysis based on score"""
        
        if openness_score >= 4:
            return """
🎨 **Высокая открытость к опыту**
Вы креативная личность, которая любит новые идеи и нестандартные решения. 
Вам подойдут эксперименты с новыми подходами к решению задач.
            """.strip()
        elif openness_score <= 2:
            return """
📋 **Предпочтение проверенных решений**
Вы цените стабильность и проверенные методы. 
Вам подойдет постепенное внедрение небольших изменений.
            """.strip()
        else:
            return """
⚖️ **Сбалансированный подход**
Вы можете как экспериментировать, так и использовать проверенные решения.
Вам подойдет гибкий подход в зависимости от ситуации.
            """.strip()
    
    @handle_errors(ErrorCode.USER_INPUT_INVALID, "Ошибка активации чата")
    async def start_chat(self, callback: types.CallbackQuery, state: FSMContext):
        """Start chat mode with logging"""
        
        user_id = callback.from_user.id
        track_user_action(user_id, "chat_mode_activated")
        
        chat_text = """
💬 **Режим чата активирован**

Теперь можете писать мне любые сообщения! 

Я буду отвечать с учетом вашего психологического профиля и помогать:
• Разобрать сложные ситуации  
• Найти решения проблем
• Лучше понять себя и свои реакции
• Достичь поставленных целей

**Примеры вопросов:**
"Как мне лучше справляться со стрессом?"
"Почему я откладываю важные дела?"
"Как улучшить отношения с коллегами?"

Просто напишите что угодно! 👇
        """
        
        await callback.message.edit_text(chat_text)
        await state.set_state(UserStates.chatting)
    
    async def show_main_menu(self, message: Message, state: FSMContext):
        """Show main menu for existing users"""
        
        user_id = message.from_user.id
        user_name = users_db[user_id]["name"]
        
        track_user_action(user_id, "main_menu_shown")
        
        menu_text = f"""
🏠 **Главное меню**

Привет, {user_name}! Рад видеть вас снова.

Что хотите сделать?
        """
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💬 Продолжить чат", callback_data="start_chat")],
            [InlineKeyboardButton(text="📊 Мой профиль", callback_data="show_profile")],
            [InlineKeyboardButton(text="🎯 Мои цели", callback_data="show_goals")],
            [InlineKeyboardButton(text="📝 Дневник", callback_data="daily_checkin")],
            [InlineKeyboardButton(text="⚙️ Настройки", callback_data="settings")]
        ])
        
        await message.answer(menu_text, reply_markup=keyboard)
        await state.set_state(UserStates.chatting)
    
    @handle_errors(ErrorCode.USER_INPUT_INVALID, "Ошибка обработки сообщения")
    async def handle_chat_message(self, message: Message, state: FSMContext):
        """Handle chat messages with comprehensive logging"""
        
        user_id = message.from_user.id
        user_text = message.text
        start_time = time.time()
        
        # Track message
        track_user_action(user_id, "chat_message_sent", 
                        message_length=len(user_text),
                        message_type="text")
        
        # Log message with analysis
        self.log_user_action("chat_message_received", user_id,
                           context={
                               "message_length": len(user_text),
                               "has_question_marks": "?" in user_text,
                               "message_words": len(user_text.split()),
                               "timestamp": datetime.now(timezone.utc).isoformat()
                           })
        
        # Simulate AI processing time
        await asyncio.sleep(0.5)
        
        # Generate response with user's personality context
        user_profile = users_db.get(user_id, {})
        openness_score = user_profile.get("openness_score", 3)
        
        response = self._generate_ai_response(user_text, openness_score, user_id)
        
        # Track AI response
        response_time = time.time() - start_time
        track_performance("ai_response_time", response_time, 
                        user_id=str(user_id), message_length=len(user_text))
        
        # Log AI interaction
        self.log_ai_interaction("simulated_ai", 
                              tokens=len(user_text.split()) + len(response.split()),
                              cost=0.001,  # Simulated cost
                              response_time=response_time,
                              user_id=user_id)
        
        increment_counter("chat_messages_processed")
        
        await message.answer(response)
    
    def _generate_ai_response(self, user_message: str, openness_score: int, user_id: int) -> str:
        """Generate AI-like response based on user's personality"""
        
        # Simple keyword-based responses personalized by openness score
        user_message_lower = user_message.lower()
        
        base_response = ""
        
        if any(word in user_message_lower for word in ["стресс", "переживаю", "волнуюсь"]):
            if openness_score >= 4:
                base_response = """
🎨 **Творческий подход к стрессу**

Учитывая вашу открытость к новому, попробуйте необычные техники релаксации:
• Медитативное рисование или музыка
• Смена обстановки - работа в кафе или парке  
• Эксперименты с дыхательными практиками

Ваш креативный ум найдет нестандартные решения!
                """.strip()
            else:
                base_response = """
📋 **Структурированный подход к стрессу**

Рекомендую проверенные методы:
• Планирование дня с четкими приоритетами
• Регулярные физические упражнения
• Техника глубокого дыхания 4-7-8

Постепенность и системность - ваши союзники!
                """.strip()
        
        elif any(word in user_message_lower for word in ["цель", "мотивация", "достижение"]):
            if openness_score >= 4:
                base_response = """
🚀 **Творческое целеполагание**

Попробуйте новые подходы к достижению целей:
• Визуализация через mood board
• Гамификация процесса с наградами
• Поиск неожиданных путей к результату

Ваша креативность поможет найти уникальный путь!
                """.strip()
            else:
                base_response = """
🎯 **Структурированное достижение целей**

Используйте SMART-подход:
• Specific - конкретная формулировка
• Measurable - измеримые показатели
• Achievable - реалистичность
• Relevant - соответствие ценностям
• Time-bound - четкие сроки
                """.strip()
        
        else:
            # Generic response
            base_response = f"""
🤖 **AI Коуч отвечает:**

Спасибо за ваш вопрос: "{user_message[:100]}{'...' if len(user_message) > 100 else ''}"

Я анализирую ваше сообщение с учетом вашего психологического профиля (открытость: {openness_score}/5)...

*[Здесь будет настоящий AI-анализ через Claude/GPT]*

**Мой совет:**
Попробуйте разложить эту ситуацию на более мелкие части и подумать, какие из них вы можете контролировать.
            """.strip()
        
        # Add personalized signature
        signature = f"\n\n💡 *Совет основан на вашем профиле открытости ({openness_score}/5)*\n\nЕсть еще вопросы? Продолжайте писать! 💬"
        
        return base_response + signature
    
    @handle_errors(ErrorCode.BOT_UPDATE_ERROR, "Ошибка команды помощи")
    async def cmd_help(self, message: Message):
        """Show help with logging"""
        
        user_id = message.from_user.id
        track_user_action(user_id, "help_command")
        
        help_text = """
🆘 **Помощь по Selfology Bot**

**Основные команды:**
/start - Главное меню
/help - Эта справка
/profile - Мой психологический профиль  
/goals - Управление целями
/export - Экспорт всех данных

**Возможности:**
🧠 Психологический анализ личности
💬 Персонализированный AI-коучинг
📊 Трекинг прогресса и инсайты
🎯 Управление целями

**Статистика бота:**
👥 Всего пользователей: {len(users_db)}
💬 Сообщений обработано: {metrics_collector.counters.get('chat_messages_processed', 0)}
🧠 Оценок завершено: {metrics_collector.counters.get('assessments_completed', 0)}

**Поддержка:** @selfology_support
**Сайт:** https://selfology.me
        """
        
        await message.answer(help_text)
    
    async def show_profile(self, callback: types.CallbackQuery):
        """Show user profile with logged data"""
        
        user_id = callback.from_user.id
        user_data = users_db.get(user_id, {})
        
        track_user_action(user_id, "profile_viewed")
        
        profile_text = f"""
📊 **Ваш психологический профиль**

**Основные черты личности:**
🎨 Открытость к опыту: {user_data.get('openness_score', 'Не определено')}/5
📋 Добросовестность: Оценка не пройдена
👥 Экстраверсия: Оценка не пройдена
🤝 Доброжелательность: Оценка не пройдена
😰 Эмоциональная нестабильность: Оценка не пройдена

**Информация об аккаунте:**
📅 Дата регистрации: {user_data.get('first_seen', 'Неизвестно')[:10]}
✅ Согласие GDPR: {'Да' if user_data.get('consent') else 'Нет'}
🎓 Онбординг: {'Завершен' if user_data.get('onboarded') else 'Не завершен'}

**Активность:**
💬 Статус: Активный пользователь
🔄 Последний визит: Сейчас

Хотите пройти полную оценку? /start
        """
        
        await callback.message.edit_text(profile_text)
    
    async def start_monitoring(self):
        """Start monitoring tasks"""
        try:
            # Start performance monitor in background
            asyncio.create_task(performance_monitor.start_monitoring())
            bot_logger.info("Monitoring system started")
        except Exception as e:
            self.log_error("MONITORING_START_ERROR", f"Failed to start monitoring: {e}")
    
    async def run(self):
        """Run the bot with monitoring"""
        
        try:
            # Start monitoring
            await self.start_monitoring()
            
            # Log bot startup
            bot_logger.info("Bot starting up", extra={
                'context': {
                    'bot_token_length': len(BOT_TOKEN),
                    'handlers_registered': len(self.dp.observers) if hasattr(self.dp, 'observers') else 0,
                    'start_time': self.start_time.isoformat()
                }
            })
            
            print("🚀 Starting Monitored Selfology Bot...")
            print(f"✅ Bot token configured ({len(BOT_TOKEN)} characters)")
            print(f"🔗 Bot username: @SelfologyMeCoachBot")
            print(f"📊 Monitoring system: Active")
            print(f"📝 Logging system: Active")
            print(f"🎯 Ready for users!")
            
            increment_counter("bot_restarts")
            
            # Start polling
            await self.dp.start_polling(self.bot)
            
        except KeyboardInterrupt:
            bot_logger.info("Bot shutdown requested by user")
            print("\n🛑 Bot stopped by user")
        except Exception as e:
            self.log_error("BOT_STARTUP_ERROR", f"Critical bot error: {e}")
            bot_logger.critical(f"Bot crashed: {e}", exc_info=True)
            raise
        finally:
            # Cleanup
            await self.bot.session.close()
            
            # Log final stats
            final_stats = {
                'uptime_seconds': (datetime.now(timezone.utc) - self.start_time).total_seconds(),
                'total_users': len(users_db),
                'total_errors': error_tracker.get_error_stats()['total_errors'],
                'messages_processed': metrics_collector.counters.get('chat_messages_processed', 0)
            }
            
            bot_logger.info("Bot shutdown completed", extra={'context': final_stats})
            print(f"📊 Final stats: {final_stats}")


async def main():
    """Main entry point"""
    
    # Create logs directory
    Path("logs").mkdir(exist_ok=True)
    
    try:
        bot = MonitoredBot()
        await bot.run()
    except Exception as e:
        error_logger = get_logger('selfology.errors')
        error_logger.critical(f"Fatal error in main: {e}", exc_info=True)
        print(f"💥 Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())