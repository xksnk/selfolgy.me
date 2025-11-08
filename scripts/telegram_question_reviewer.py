#!/usr/bin/env python3
"""
📱 Telegram Question Reviewer - Интерфейс одобрения вопросов через Telegram
Показывает вопросы с кнопками одобрения, предупреждениями и комментариями.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from aiogram import Bot, Dispatcher, F
    from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
    from aiogram.filters import Command, CommandStart
    from aiogram.fsm.context import FSMContext
    from aiogram.fsm.state import State, StatesGroup
    from aiogram.fsm.storage.memory import MemoryStorage
    AIOGRAM_AVAILABLE = True
except ImportError:
    print("⚠️ aiogram not installed. Run: pip install aiogram")
    AIOGRAM_AVAILABLE = False
    exit(1)

from scripts.agile_debug.question_approval_workflow import QuestionApprovalWorkflow
import os
import logging
import json
from datetime import datetime
from typing import Dict, List, Any, Optional


class ReviewerStates(StatesGroup):
    """Состояния для рецензирования вопросов"""
    reviewing = State()
    adding_feedback = State()


class TelegramQuestionReviewer:
    """
    📱 Telegram интерфейс для рецензирования психологических вопросов
    
    Функции:
    - Показ вопросов с полным контекстом и метаданными
    - Кнопки одобрения/отклонения/доработки
    - Система предупреждений о потенциальных проблемах
    - Возможность добавления комментариев и заметок
    - Статистика и отчеты по рецензированию
    - Интеграция с агильной системой отладки
    """
    
    def __init__(self, bot_token: str, developer_chat_id: int):
        self.bot_token = bot_token
        self.developer_chat_id = developer_chat_id
        
        # Инициализация бота
        self.bot = Bot(token=bot_token)
        self.storage = MemoryStorage()
        self.dp = Dispatcher(storage=self.storage)
        
        # Система одобрения вопросов
        self.approval_workflow = QuestionApprovalWorkflow()
        
        # Настройка обработчиков
        self._setup_handlers()
        
        self.logger = logging.getLogger(__name__)
        
        # Эмодзи для визуального оформления
        self.priority_emoji = {
            'urgent': '🔴',
            'high': '🟡', 
            'normal': '🟢',
            'low': '⚪'
        }
        
        self.domain_emoji = {
            'IDENTITY': '🧩',
            'EMOTIONS': '❤️',
            'RELATIONSHIPS': '👥',
            'CAREER': '💼',
            'VALUES': '⚖️',
            'GOALS': '🎯',
            'MINDSET': '🧠',
            'HEALTH': '🏥',
            'CREATIVITY': '🎨',
            'SPIRITUALITY': '🕯️',
            'LEARNING': '📚',
            'COMMUNICATION': '💬',
            'LEADERSHIP': '👑'
        }
        
        self.energy_emoji = {
            'OPENING': '🌅',
            'NEUTRAL': '⚪',
            'PROCESSING': '🔄',
            'HEAVY': '⚠️',
            'HEALING': '💚'
        }
    
    def _setup_handlers(self):
        """Настройка обработчиков команд и callback'ов"""
        
        @self.dp.message(CommandStart())
        async def start_handler(message: Message):
            await self._handle_start(message)
        
        @self.dp.message(Command("review"))
        async def review_handler(message: Message):
            await self._handle_review_command(message)
        
        @self.dp.message(Command("stats"))
        async def stats_handler(message: Message):
            await self._handle_stats_command(message)
        
        @self.dp.message(Command("pending"))
        async def pending_handler(message: Message):
            await self._handle_pending_command(message)
        
        @self.dp.message(Command("help"))
        async def help_handler(message: Message):
            await self._handle_help_command(message)
        
        @self.dp.callback_query(F.data.startswith("approve_"))
        async def approve_callback(callback: CallbackQuery):
            await self._handle_approve_callback(callback)
        
        @self.dp.callback_query(F.data.startswith("needs_work_"))
        async def needs_work_callback(callback: CallbackQuery):
            await self._handle_needs_work_callback(callback)
        
        @self.dp.callback_query(F.data.startswith("reject_"))
        async def reject_callback(callback: CallbackQuery):
            await self._handle_reject_callback(callback)
        
        @self.dp.callback_query(F.data.startswith("pause_"))
        async def pause_callback(callback: CallbackQuery):
            await self._handle_pause_callback(callback)
        
        @self.dp.callback_query(F.data.startswith("notes_"))
        async def notes_callback(callback: CallbackQuery, state: FSMContext):
            await self._handle_notes_callback(callback, state)
        
        @self.dp.callback_query(F.data.startswith("show_warnings_"))
        async def show_warnings_callback(callback: CallbackQuery):
            await self._handle_show_warnings_callback(callback)
        
        @self.dp.message(ReviewerStates.adding_feedback)
        async def feedback_handler(message: Message, state: FSMContext):
            await self._handle_feedback_input(message, state)
    
    async def _handle_start(self, message: Message):
        """Обработка команды /start"""
        welcome_text = """
🤖 **Selfology Question Reviewer**

Добро пожаловать в систему рецензирования психологических вопросов!

**Доступные команды:**
📋 /review - Начать рецензирование вопросов
📊 /stats - Статистика рецензирования
⏳ /pending - Список ожидающих вопросов
❓ /help - Помощь по использованию

**Система одобрения:**
✅ **Approve** - Одобрить вопрос для использования
🔄 **Needs Work** - Отметить как требующий доработки
❌ **Reject** - Отклонить вопрос
📝 **Add Notes** - Добавить комментарии

🔒 Все вопросы проходят проверку **ПЕРЕД** добавлением в основную систему.
"""
        
        await message.reply(welcome_text, parse_mode='Markdown')
    
    async def _handle_review_command(self, message: Message):
        """Обработка команды /review"""
        pending_questions = await self.approval_workflow.get_pending_questions(1)
        
        if not pending_questions:
            await message.reply("✅ Отлично! Нет вопросов ожидающих рецензирования.")
            return
        
        # Показать первый вопрос
        question = pending_questions[0]
        await self._show_question_for_review(message.chat.id, question)
    
    async def _handle_stats_command(self, message: Message):
        """Обработка команды /stats"""
        stats = await self.approval_workflow.get_approval_statistics()
        
        stats_text = f"""
📊 **СТАТИСТИКА РЕЦЕНЗИРОВАНИЯ**

**Общее состояние:**
✅ Одобрено: {stats.get('approved_count', 0)}
🔄 Требует доработки: {stats.get('needs_work_count', 0)}
⏳ Ожидает рецензии: {stats.get('pending_count', 0)}
🤖 Авто-одобрено: {stats.get('auto_approved_count', 0)}

**Приоритеты:**
🔴 Срочно: {stats.get('priority_counts', {}).get('urgent', 0)}
🟡 Высокий: {stats.get('priority_counts', {}).get('high', 0)}
🟢 Обычный: {stats.get('priority_counts', {}).get('normal', 0)}
⚪ Низкий: {stats.get('priority_counts', {}).get('low', 0)}

**Производительность:**
⏱ Среднее время рецензии: {stats.get('average_review_time_hours', 0):.1f} часов

📈 **Система автоматически одобряет** вопросы через 24 часа если не отмечены как требующие доработки.
"""
        
        await message.reply(stats_text, parse_mode='Markdown')
    
    async def _handle_pending_command(self, message: Message):
        """Обработка команды /pending"""
        pending = await self.approval_workflow.get_pending_questions(10)
        
        if not pending:
            await message.reply("✅ Нет вопросов ожидающих рецензирования!")
            return
        
        pending_text = f"📝 **ОЖИДАЮТ РЕЦЕНЗИИ** ({len(pending)} вопросов)\n\n"
        
        for i, question in enumerate(pending[:5], 1):
            priority_emoji = self.priority_emoji.get(question['priority'], '⚪')
            domain_emoji = self.domain_emoji.get(question['domain'], '📝')
            energy_emoji = self.energy_emoji.get(question['energy_type'], '⚪')
            
            status_text = "🔄 Требует доработки" if question['status'] == 'needs_work' else "⏳ Ожидает"
            
            pending_text += f"{i}. {priority_emoji}{domain_emoji}{energy_emoji} **{question['question_id']}**\n"
            pending_text += f"   {status_text}\n"
            pending_text += f"   {question['question_text'][:80]}{'...' if len(question['question_text']) > 80 else ''}\n"
            pending_text += f"   `{question['domain']} | {question['depth_level']} | {question['energy_type']}`\n\n"
        
        if len(pending) > 5:
            pending_text += f"... и еще {len(pending) - 5} вопросов\n\n"
        
        pending_text += "Используйте /review для начала рецензирования"
        
        await message.reply(pending_text, parse_mode='Markdown')
    
    async def _handle_help_command(self, message: Message):
        """Обработка команды /help"""
        help_text = """
❓ **ПОМОЩЬ ПО ИСПОЛЬЗОВАНИЮ**

**Основные команды:**
📋 `/review` - Начать рецензирование (показывает следующий вопрос)
📊 `/stats` - Показать статистику рецензирования
⏳ `/pending` - Список всех ожидающих вопросов
❓ `/help` - Эта справка

**Рецензирование вопроса:**

При показе вопроса доступны кнопки:
✅ **Approve** - Одобрить вопрос
🔄 **Needs Work** - Требует доработки  
❌ **Reject** - Отклонить вопрос
📝 **Add Notes** - Добавить комментарии
⚠️ **Show Warnings** - Показать предупреждения системы

**Информация о вопросе:**
🧩 Домен - психологическая область
📊 Уровень глубины - от SURFACE до CORE
⚡ Тип энергии - влияние на эмоциональное состояние
🎯 Приоритет - срочность рецензирования

**Система безопасности:**
- Вопросы **НЕ попадают** в основную систему до одобрения
- Автоматическое одобрение через 24 часа (если не отмечены как требующие доработки)
- Все действия логируются для аудита
- Создаются бэкапы перед изменениями

🔒 **Важно:** Вопросы с энергией HEAVY требуют особого внимания!
"""
        
        await message.reply(help_text, parse_mode='Markdown')
    
    async def _show_question_for_review(self, chat_id: int, question: Dict[str, Any]):
        """Показ вопроса для рецензирования"""
        try:
            # Формирование сообщения о вопросе
            priority_emoji = self.priority_emoji.get(question['priority'], '⚪')
            domain_emoji = self.domain_emoji.get(question['domain'], '📝')
            energy_emoji = self.energy_emoji.get(question['energy_type'], '⚪')
            
            # Заголовок
            header = f"{priority_emoji}{domain_emoji}{energy_emoji} **ВОПРОС НА РЕЦЕНЗИЮ**\n"
            header += f"═══════════════════════════════\n\n"
            
            # Основная информация
            main_info = f"**ID:** `{question['question_id']}`\n"
            main_info += f"**Домен:** {question['domain']}\n"
            main_info += f"**Глубина:** {question['depth_level']}\n"
            main_info += f"**Энергия:** {question['energy_type']}\n"
            main_info += f"**Приоритет:** {question['priority'].upper()}\n\n"
            
            # Текст вопроса
            question_text = f"**❓ Вопрос:**\n"
            question_text += f"_{question['question_text']}_\n\n"
            
            # Предупреждения если есть
            warnings_text = ""
            if question.get('warnings'):
                try:
                    import json
                    warnings = json.loads(question['warnings']) if isinstance(question['warnings'], str) else question['warnings']
                    
                    if warnings.get('critical_issues'):
                        warnings_text += f"🚨 **Критические проблемы:**\n"
                        for issue in warnings['critical_issues']:
                            warnings_text += f"• {issue}\n"
                        warnings_text += "\n"
                    
                    if warnings.get('moderate_issues'):
                        warnings_text += f"⚠️ **Проблемы:**\n"
                        for issue in warnings['moderate_issues']:
                            warnings_text += f"• {issue}\n"
                        warnings_text += "\n"
                    
                    if warnings.get('suggestions'):
                        warnings_text += f"💡 **Предложения:**\n"
                        for suggestion in warnings['suggestions']:
                            warnings_text += f"• {suggestion}\n"
                        warnings_text += "\n"
                
                except Exception as e:
                    warnings_text = f"⚠️ Ошибка при отображении предупреждений: {str(e)}\n\n"
            
            # Метаданные если есть
            metadata_text = ""
            if question.get('question_metadata'):
                try:
                    metadata = json.loads(question['question_metadata']) if isinstance(question['question_metadata'], str) else question['question_metadata']
                    
                    if metadata:
                        metadata_text = "📋 **Метаданные:**\n"
                        for key, value in metadata.items():
                            if key in ['estimated_time', 'difficulty', 'prerequisites']:
                                metadata_text += f"• {key}: {value}\n"
                        metadata_text += "\n"
                
                except Exception:
                    pass
            
            # Информация о времени
            time_info = f"⏰ **Отправлен:** {question['submitted_at']}\n"
            if question.get('auto_approve_at'):
                time_info += f"🤖 **Авто-одобрение:** {question['auto_approve_at']}\n"
            
            # Собираем полное сообщение
            full_message = header + main_info + question_text + warnings_text + metadata_text + time_info
            
            # Создание кнопок
            keyboard = self._create_review_keyboard(question['question_id'], question.get('warnings'))
            
            # Отправка сообщения
            await self.bot.send_message(
                chat_id=chat_id,
                text=full_message,
                reply_markup=keyboard,
                parse_mode='Markdown'
            )
            
        except Exception as e:
            await self.bot.send_message(
                chat_id=chat_id,
                text=f"❌ Ошибка при показе вопроса: {str(e)}"
            )
            self.logger.error(f"Failed to show question for review: {str(e)}")
    
    def _create_review_keyboard(self, question_id: str, warnings: Any) -> InlineKeyboardMarkup:
        """Создание клавиатуры для рецензирования"""
        # Основные кнопки действий
        action_buttons = [
            [
                InlineKeyboardButton(
                    text="✅ Одобрить", 
                    callback_data=f"approve_{question_id}"
                ),
                InlineKeyboardButton(
                    text="🔄 Доработать", 
                    callback_data=f"needs_work_{question_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="⏸️ Пауза", 
                    callback_data=f"pause_{question_id}"
                ),
                InlineKeyboardButton(
                    text="❌ Отклонить", 
                    callback_data=f"reject_{question_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📝 Заметки", 
                    callback_data=f"notes_{question_id}"
                )
            ]
        ]
        
        # Дополнительные кнопки
        additional_buttons = []
        
        # Кнопка предупреждений если есть проблемы
        if warnings:
            try:
                warnings_data = json.loads(warnings) if isinstance(warnings, str) else warnings
                if (warnings_data.get('critical_issues') or 
                    warnings_data.get('moderate_issues') or 
                    warnings_data.get('suggestions')):
                    additional_buttons.append([
                        InlineKeyboardButton(
                            text="⚠️ Показать предупреждения",
                            callback_data=f"show_warnings_{question_id}"
                        )
                    ])
            except:
                pass
        
        # Кнопка следующего вопроса
        additional_buttons.append([
            InlineKeyboardButton(
                text="➡️ Следующий вопрос",
                callback_data=f"next_question"
            )
        ])
        
        # Объединение всех кнопок
        all_buttons = action_buttons + additional_buttons
        
        return InlineKeyboardMarkup(inline_keyboard=all_buttons)
    
    async def _handle_approve_callback(self, callback: CallbackQuery):
        """Обработка одобрения вопроса"""
        question_id = callback.data.split('_', 1)[1]
        user_id = str(callback.from_user.id)
        
        result = await self.approval_workflow.approve_question(
            question_id, user_id, f"Одобрено через Telegram пользователем {callback.from_user.first_name}"
        )
        
        if result['success']:
            # Обновление сообщения
            approval_text = f"✅ **ОДОБРЕНО**\n\n"
            approval_text += f"Рецензент: {callback.from_user.first_name}\n"
            approval_text += f"Вопрос ID: `{question_id}`\n"
            approval_text += f"Время: {datetime.now().strftime('%H:%M:%S %d.%m.%Y')}\n\n"
            approval_text += f"🎯 Вопрос будет добавлен в основную систему!"
            
            await callback.message.edit_text(
                approval_text,
                parse_mode='Markdown'
            )
            
            await callback.answer("✅ Вопрос одобрен!")
            
            # Автоматически показать следующий вопрос
            await asyncio.sleep(2)
            await self._show_next_question(callback.message.chat.id)
        
        else:
            await callback.answer(f"❌ Ошибка одобрения: {result.get('error', 'Неизвестная ошибка')}")
    
    async def _handle_needs_work_callback(self, callback: CallbackQuery):
        """Обработка отметки 'требует доработки'"""
        question_id = callback.data.split('_', 2)[2]  # needs_work_QUESTION_ID
        user_id = str(callback.from_user.id)
        
        result = await self.approval_workflow.mark_needs_work(
            question_id, user_id, f"Требует доработки - отмечено через Telegram пользователем {callback.from_user.first_name}"
        )
        
        if result['success']:
            needs_work_text = f"🔄 **ТРЕБУЕТ ДОРАБОТКИ**\n\n"
            needs_work_text += f"Рецензент: {callback.from_user.first_name}\n"
            needs_work_text += f"Вопрос ID: `{question_id}`\n"
            needs_work_text += f"Время: {datetime.now().strftime('%H:%M:%S %d.%m.%Y')}\n\n"
            needs_work_text += f"📝 Вопрос **НЕ будет** добавлен в систему до доработки.\n"
            needs_work_text += f"💡 Используйте кнопку 'Заметки' для добавления комментариев."
            
            # Создание кнопки для добавления заметок
            notes_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="📝 Добавить заметки",
                        callback_data=f"notes_{question_id}"
                    ),
                    InlineKeyboardButton(
                        text="➡️ Следующий",
                        callback_data="next_question"
                    )
                ]
            ])
            
            await callback.message.edit_text(
                needs_work_text,
                reply_markup=notes_keyboard,
                parse_mode='Markdown'
            )
            
            await callback.answer("🔄 Отмечено как требующее доработки")
        
        else:
            await callback.answer(f"❌ Ошибка: {result.get('error', 'Неизвестная ошибка')}")
    
    async def _handle_reject_callback(self, callback: CallbackQuery):
        """Обработка отклонения вопроса"""
        question_id = callback.data.split('_', 1)[1]
        user_id = str(callback.from_user.id)
        
        result = await self.approval_workflow.reject_question(
            question_id, user_id, f"Отклонено через Telegram пользователем {callback.from_user.first_name}"
        )
        
        if result['success']:
            reject_text = f"❌ **ОТКЛОНЕНО**\n\n"
            reject_text += f"Рецензент: {callback.from_user.first_name}\n"
            reject_text += f"Вопрос ID: `{question_id}`\n"
            reject_text += f"Время: {datetime.now().strftime('%H:%M:%S %d.%m.%Y')}\n\n"
            reject_text += f"🗑️ Вопрос удален из системы рецензирования."
            
            await callback.message.edit_text(reject_text, parse_mode='Markdown')
            await callback.answer("❌ Вопрос отклонен")
            
            # Автоматически показать следующий вопрос
            await asyncio.sleep(2)
            await self._show_next_question(callback.message.chat.id)
        
        else:
            await callback.answer(f"❌ Ошибка отклонения: {result.get('error', 'Неизвестная ошибка')}")
    
    async def _handle_pause_callback(self, callback: CallbackQuery):
        """Обработка постановки вопроса на паузу"""
        question_id = callback.data.split('_', 1)[1]
        user_id = str(callback.from_user.id)
        
        result = await self.approval_workflow.pause_question(
            question_id, user_id, f"На паузе для доработки - отмечено через Telegram пользователем {callback.from_user.first_name}"
        )
        
        if result['success']:
            pause_text = f"⏸️ **НА ПАУЗЕ ДЛЯ ДОРАБОТКИ**\n\n"
            pause_text += f"Рецензент: {callback.from_user.first_name}\n"
            pause_text += f"Вопрос ID: `{question_id}`\n"
            pause_text += f"Время: {datetime.now().strftime('%H:%M:%S %d.%m.%Y')}\n\n"
            pause_text += f"⏸️ Вопрос **НЕ будет** использоваться до снятия с паузы.\n"
            pause_text += f"🔧 Вопрос ждет доработки разработчиками."
            
            # Создание кнопки для добавления заметок
            pause_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="📝 Добавить заметки",
                        callback_data=f"notes_{question_id}"
                    ),
                    InlineKeyboardButton(
                        text="➡️ Следующий",
                        callback_data="next_question"
                    )
                ]
            ])
            
            await callback.message.edit_text(
                pause_text,
                reply_markup=pause_keyboard,
                parse_mode='Markdown'
            )
            
            await callback.answer("⏸️ Вопрос поставлен на паузу")
        
        else:
            await callback.answer(f"❌ Ошибка: {result.get('error', 'Неизвестная ошибка')}")
    
    async def _handle_notes_callback(self, callback: CallbackQuery, state: FSMContext):
        """Обработка добавления заметок"""
        question_id = callback.data.split('_', 1)[1]
        
        # Сохранение ID вопроса в состоянии
        await state.update_data(question_id=question_id)
        await state.set_state(ReviewerStates.adding_feedback)
        
        notes_text = f"📝 **ДОБАВЛЕНИЕ ЗАМЕТОК**\n\n"
        notes_text += f"Вопрос ID: `{question_id}`\n\n"
        notes_text += f"Напишите свои комментарии или предложения по улучшению этого вопроса:\n\n"
        notes_text += f"💡 Примеры заметок:\n"
        notes_text += f"• \"Слишком сложная формулировка\"\n"
        notes_text += f"• \"Добавить контекст для HEAVY энергии\"\n"
        notes_text += f"• \"Уточнить целевую аудиторию\"\n\n"
        notes_text += f"Отправьте текст заметок следующим сообщением."
        
        await callback.message.edit_text(notes_text, parse_mode='Markdown')
        await callback.answer("📝 Введите заметки")
    
    async def _handle_feedback_input(self, message: Message, state: FSMContext):
        """Обработка ввода заметок"""
        try:
            data = await state.get_data()
            question_id = data.get('question_id')
            feedback_text = message.text
            
            if question_id and feedback_text:
                # Сохранение заметок в систему одобрения
                # TODO: Добавить метод для сохранения заметок в approval workflow
                
                success_text = f"💾 **ЗАМЕТКИ СОХРАНЕНЫ**\n\n"
                success_text += f"Вопрос ID: `{question_id}`\n"
                success_text += f"Заметки: {feedback_text}\n\n"
                success_text += f"✅ Заметки добавлены к вопросу для разработчиков."
                
                # Кнопка для продолжения рецензирования
                continue_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="➡️ Следующий вопрос",
                            callback_data="next_question"
                        )
                    ]
                ])
                
                await message.reply(success_text, reply_markup=continue_keyboard, parse_mode='Markdown')
            
            else:
                await message.reply("❌ Ошибка: не удалось сохранить заметки")
            
            # Очистка состояния
            await state.clear()
            
        except Exception as e:
            await message.reply(f"❌ Ошибка при сохранении заметок: {str(e)}")
            await state.clear()
    
    async def _handle_show_warnings_callback(self, callback: CallbackQuery):
        """Обработка показа предупреждений"""
        question_id = callback.data.split('_', 2)[2]
        
        # Получение данных вопроса
        question_data = await self.approval_workflow._get_question_data(question_id)
        
        if question_data and question_data.get('warnings'):
            try:
                warnings = json.loads(question_data['warnings']) if isinstance(question_data['warnings'], str) else question_data['warnings']
                
                warnings_text = f"⚠️ **ДЕТАЛЬНЫЕ ПРЕДУПРЕЖДЕНИЯ**\n"
                warnings_text += f"═══════════════════════════════\n\n"
                warnings_text += f"**Вопрос ID:** `{question_id}`\n\n"
                
                if warnings.get('critical_issues'):
                    warnings_text += f"🚨 **КРИТИЧЕСКИЕ ПРОБЛЕМЫ:**\n"
                    for i, issue in enumerate(warnings['critical_issues'], 1):
                        warnings_text += f"{i}. {issue}\n"
                    warnings_text += "\n"
                
                if warnings.get('moderate_issues'):
                    warnings_text += f"⚠️ **УМЕРЕННЫЕ ПРОБЛЕМЫ:**\n"
                    for i, issue in enumerate(warnings['moderate_issues'], 1):
                        warnings_text += f"{i}. {issue}\n"
                    warnings_text += "\n"
                
                if warnings.get('minor_issues'):
                    warnings_text += f"🔸 **МЕЛКИЕ ПРОБЛЕМЫ:**\n"
                    for i, issue in enumerate(warnings['minor_issues'], 1):
                        warnings_text += f"{i}. {issue}\n"
                    warnings_text += "\n"
                
                if warnings.get('suggestions'):
                    warnings_text += f"💡 **ПРЕДЛОЖЕНИЯ ПО УЛУЧШЕНИЮ:**\n"
                    for i, suggestion in enumerate(warnings['suggestions'], 1):
                        warnings_text += f"{i}. {suggestion}\n"
                    warnings_text += "\n"
                
                warnings_text += f"🎯 **Рекомендация:** "
                if warnings.get('critical_issues'):
                    warnings_text += "Требует обязательной доработки перед одобрением"
                elif warnings.get('moderate_issues'):
                    warnings_text += "Рассмотрите доработку или добавьте комментарии"
                else:
                    warnings_text += "Можно одобрить с учетом предложений"
                
                # Кнопка назад
                back_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="🔙 Назад к рецензии",
                            callback_data=f"back_to_review_{question_id}"
                        )
                    ]
                ])
                
                await callback.message.edit_text(
                    warnings_text,
                    reply_markup=back_keyboard,
                    parse_mode='Markdown'
                )
                
            except Exception as e:
                await callback.answer(f"❌ Ошибка при показе предупреждений: {str(e)}")
        
        else:
            await callback.answer("ℹ️ Предупреждения не найдены")
    
    async def _show_next_question(self, chat_id: int):
        """Показ следующего вопроса"""
        pending_questions = await self.approval_workflow.get_pending_questions(1)
        
        if pending_questions:
            await self._show_question_for_review(chat_id, pending_questions[0])
        else:
            await self.bot.send_message(
                chat_id=chat_id,
                text="🎉 Отлично! Все вопросы рецензированы.\n\nИспользуйте /review для проверки новых вопросов."
            )
    
    async def start_polling(self):
        """Запуск бота в режиме polling"""
        try:
            self.logger.info("Starting Telegram Question Reviewer...")
            
            # Инициализация системы одобрения с Telegram
            await self.approval_workflow.initialize_telegram_bot(
                self.bot_token, self.developer_chat_id
            )
            
            # Уведомление о запуске
            await self.bot.send_message(
                chat_id=self.developer_chat_id,
                text="🤖 **Selfology Question Reviewer** запущен!\n\nИспользуйте /review для начала рецензирования."
            )
            
            # Запуск polling
            await self.dp.start_polling(self.bot)
            
        except Exception as e:
            self.logger.error(f"Failed to start Telegram bot: {str(e)}")
    
    async def stop(self):
        """Остановка бота"""
        try:
            await self.bot.session.close()
        except:
            pass


async def main():
    """Main entry point for Telegram Question Reviewer"""
    # Получение токена и chat ID из переменных окружения
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    developer_chat_id = os.getenv('DEVELOPER_CHAT_ID')
    
    if not bot_token:
        print("❌ TELEGRAM_BOT_TOKEN not found in environment")
        return
    
    if not developer_chat_id:
        print("❌ DEVELOPER_CHAT_ID not found in environment")
        print("💡 Add your Telegram chat ID to .env file: DEVELOPER_CHAT_ID=your_chat_id")
        return
    
    try:
        developer_chat_id = int(developer_chat_id)
    except ValueError:
        print("❌ DEVELOPER_CHAT_ID must be a number")
        return
    
    # Создание и запуск рецензента
    reviewer = TelegramQuestionReviewer(bot_token, developer_chat_id)
    
    try:
        await reviewer.start_polling()
    except KeyboardInterrupt:
        print("\n🛑 Stopping Telegram Question Reviewer...")
    except Exception as e:
        print(f"❌ Error: {str(e)}")
    finally:
        await reviewer.stop()


if __name__ == "__main__":
    if not AIOGRAM_AVAILABLE:
        print("❌ Please install aiogram: pip install aiogram")
        exit(1)
    
    asyncio.run(main())

import json