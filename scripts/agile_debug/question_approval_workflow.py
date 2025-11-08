"""
✅ Question Approval Workflow - Система одобрения вопросов с Telegram интеграцией
Обеспечивает качественный контроль всех психологических вопросов перед добавлением в систему.
"""

import asyncio
import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Set
from enum import Enum
import logging

# Telegram Bot Integration
try:
    from aiogram import Bot, Dispatcher, types
    from aiogram.filters import Command
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False
    print("⚠️ Telegram integration not available. Install aiogram for full functionality.")


class QuestionStatus(Enum):
    """Статусы вопросов в системе одобрения"""
    PENDING_REVIEW = "pending_review"        # Ожидает рассмотрения
    APPROVED = "approved"                    # Одобрен
    NEEDS_WORK = "needs_work"               # Требует доработки  
    REJECTED = "rejected"                    # Отклонен
    AUTO_APPROVED = "auto_approved"         # Автоматически одобрен
    PAUSED = "paused"                       # На паузе для доработки
    ANSWERED_APPROVED = "answered_approved" # Одобрен через ответ пользователя


class QuestionPriority(Enum):
    """Приоритеты вопросов для рассмотрения"""
    URGENT = "urgent"           # Критически важный
    HIGH = "high"              # Высокий приоритет
    NORMAL = "normal"          # Обычный приоритет
    LOW = "low"                # Низкий приоритет


class QuestionApprovalWorkflow:
    """
    🎯 Система одобрения вопросов с полной интеграцией
    
    Функции:
    - Хранение вопросов на рассмотрение (SQLite)
    - Telegram интеграция с кнопками одобрения
    - Автоматическое одобрение неотмеченных вопросов
    - Система комментариев и предупреждений
    - Блокировка добавления в основные БД до одобрения
    """
    
    def __init__(self):
        self.approval_db_path = Path('data/question_approval.db')
        self.approval_db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Telegram bot configuration
        self.telegram_bot = None
        self.developer_chat_id = None  # ID разработчика для уведомлений
        
        # Настройка базы данных одобрения
        self._setup_approval_database()
        
        # Настройка логирования
        self.logger = logging.getLogger(__name__)
        
        # Автоматическое одобрение после N часов без действий
        self.auto_approve_hours = 24
    
    def _setup_approval_database(self):
        """Настройка базы данных для хранения вопросов на одобрение"""
        conn = sqlite3.connect(self.approval_db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS question_approvals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question_id TEXT UNIQUE NOT NULL,
                question_text TEXT NOT NULL,
                question_metadata TEXT,
                domain TEXT,
                depth_level TEXT,
                energy_type TEXT,
                status TEXT NOT NULL DEFAULT 'pending_review',
                priority TEXT NOT NULL DEFAULT 'normal',
                submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                reviewed_at TIMESTAMP,
                reviewer_id TEXT,
                developer_feedback TEXT,
                developer_notes TEXT,
                warnings TEXT,
                telegram_message_id INTEGER,
                auto_approve_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS approval_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question_id TEXT NOT NULL,
                action TEXT NOT NULL,
                previous_status TEXT,
                new_status TEXT,
                reviewer_id TEXT,
                feedback TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_status ON question_approvals(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_priority ON question_approvals(priority)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_submitted_at ON question_approvals(submitted_at)")
        
        conn.commit()
        conn.close()
    
    async def initialize_telegram_bot(self, bot_token: str, developer_chat_id: int):
        """Инициализация Telegram бота для одобрения вопросов"""
        if not TELEGRAM_AVAILABLE:
            self.logger.error("Telegram integration not available")
            return False
        
        try:
            self.telegram_bot = Bot(token=bot_token)
            self.developer_chat_id = developer_chat_id
            
            # Настройка обработчиков команд
            dp = Dispatcher()
            
            # Команда для получения списка вопросов на рассмотрение
            @dp.message(Command("pending_questions"))
            async def show_pending_questions(message: types.Message):
                await self._handle_pending_questions_command(message)
            
            # Команда для получения статистики
            @dp.message(Command("approval_stats"))
            async def show_approval_stats(message: types.Message):
                await self._handle_approval_stats_command(message)
            
            # Обработчик нажатий на кнопки
            @dp.callback_query()
            async def handle_approval_callback(callback: CallbackQuery):
                await self._handle_approval_callback(callback)
            
            self.dispatcher = dp
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Telegram bot: {str(e)}")
            return False
    
    async def submit_question_for_approval(self, question_data: Dict[str, Any], 
                                         priority: QuestionPriority = QuestionPriority.NORMAL) -> Dict[str, Any]:
        """
        Отправка вопроса на одобрение
        
        Args:
            question_data: Данные вопроса (id, text, metadata, etc.)
            priority: Приоритет рассмотрения
        
        Returns:
            Результат отправки на рассмотрение
        """
        try:
            question_id = question_data.get('id')
            question_text = question_data.get('question', '')
            metadata = json.dumps(question_data.get('metadata', {}))
            
            # Проверка на дублирование
            if await self._question_already_exists(question_id):
                return {
                    'success': False,
                    'error': 'Question already in approval system',
                    'question_id': question_id
                }
            
            # Анализ вопроса на потенциальные проблемы
            warnings = await self._analyze_question_warnings(question_data)
            
            # Установка времени автоматического одобрения
            auto_approve_at = datetime.now() + timedelta(hours=self.auto_approve_hours)
            
            # Определение приоритета на основе анализа
            if warnings.get('critical_issues'):
                priority = QuestionPriority.URGENT
            elif warnings.get('moderate_issues'):
                priority = QuestionPriority.HIGH
            
            # Сохранение в БД одобрения
            conn = sqlite3.connect(self.approval_db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO question_approvals 
                (question_id, question_text, question_metadata, domain, depth_level, 
                 energy_type, priority, warnings, auto_approve_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                question_id,
                question_text,
                metadata,
                question_data.get('domain'),
                question_data.get('depth_level'),
                question_data.get('energy_type'),
                priority.value,
                json.dumps(warnings),
                auto_approve_at.isoformat()
            ))
            
            conn.commit()
            conn.close()
            
            # Отправка уведомления в Telegram
            telegram_message_id = None
            if self.telegram_bot and self.developer_chat_id:
                telegram_message_id = await self._send_telegram_approval_request(
                    question_id, question_data, priority, warnings
                )
            
            # Обновление message_id в БД
            if telegram_message_id:
                await self._update_telegram_message_id(question_id, telegram_message_id)
            
            # Запись в историю
            await self._log_approval_action(
                question_id, 'submitted', None, QuestionStatus.PENDING_REVIEW.value, 
                'system', f"Submitted with priority: {priority.value}"
            )
            
            return {
                'success': True,
                'question_id': question_id,
                'priority': priority.value,
                'auto_approve_at': auto_approve_at.isoformat(),
                'warnings': warnings,
                'telegram_message_id': telegram_message_id
            }
            
        except Exception as e:
            self.logger.error(f"Failed to submit question for approval: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'question_id': question_data.get('id')
            }
    
    async def _analyze_question_warnings(self, question_data: Dict[str, Any]) -> Dict[str, Any]:
        """Анализ вопроса на потенциальные проблемы"""
        warnings = {
            'critical_issues': [],
            'moderate_issues': [],
            'minor_issues': [],
            'suggestions': []
        }
        
        question_text = question_data.get('question', '').lower()
        
        # Критические проблемы
        if len(question_text) < 10:
            warnings['critical_issues'].append("Question too short")
        
        if not question_text.endswith('?'):
            warnings['critical_issues'].append("Question doesn't end with '?'")
        
        # Проверка на сложные/травматичные темы
        sensitive_keywords = ['смерть', 'суицид', 'травма', 'насилие', 'депрессия']
        if any(keyword in question_text for keyword in sensitive_keywords):
            warnings['critical_issues'].append("Contains sensitive/traumatic content")
        
        # Умеренные проблемы
        if len(question_text) > 200:
            warnings['moderate_issues'].append("Question might be too long")
        
        if question_data.get('energy_type') == 'HEAVY':
            warnings['moderate_issues'].append("Heavy energy type - ensure proper context")
        
        # Незначительные проблемы
        if not question_data.get('metadata', {}).get('estimated_time'):
            warnings['minor_issues'].append("Missing estimated response time")
        
        # Предложения
        if question_data.get('depth_level') in ['SHADOW', 'CORE']:
            warnings['suggestions'].append("Consider adding trust level prerequisites")
        
        return warnings
    
    async def _send_telegram_approval_request(self, question_id: str, question_data: Dict[str, Any], 
                                            priority: QuestionPriority, warnings: Dict[str, Any]) -> Optional[int]:
        """Отправка запроса на одобрение в Telegram"""
        if not self.telegram_bot or not self.developer_chat_id:
            return None
        
        try:
            # Формирование сообщения
            priority_emoji = {
                QuestionPriority.URGENT: "🔴",
                QuestionPriority.HIGH: "🟡", 
                QuestionPriority.NORMAL: "🟢",
                QuestionPriority.LOW: "⚪"
            }
            
            message_text = f"""
{priority_emoji[priority]} **QUESTION APPROVAL REQUEST**

**ID:** `{question_id}`
**Domain:** {question_data.get('domain', 'Unknown')}
**Depth:** {question_data.get('depth_level', 'Unknown')}
**Energy:** {question_data.get('energy_type', 'Unknown')}
**Priority:** {priority.value.upper()}

**Question:**
{question_data.get('question', 'No text')}
"""
            
            # Добавление предупреждений
            if warnings.get('critical_issues'):
                message_text += f"\n🚨 **Critical Issues:** {', '.join(warnings['critical_issues'])}"
            
            if warnings.get('moderate_issues'):
                message_text += f"\n⚠️ **Issues:** {', '.join(warnings['moderate_issues'])}"
            
            if warnings.get('suggestions'):
                message_text += f"\n💡 **Suggestions:** {', '.join(warnings['suggestions'])}"
            
            # Создание кнопок одобрения
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="✅ Approve", callback_data=f"approve_{question_id}"),
                    InlineKeyboardButton(text="🔄 Needs Work", callback_data=f"needs_work_{question_id}")
                ],
                [
                    InlineKeyboardButton(text="❌ Reject", callback_data=f"reject_{question_id}"),
                    InlineKeyboardButton(text="📝 Add Notes", callback_data=f"notes_{question_id}")
                ]
            ])
            
            # Отправка сообщения
            message = await self.telegram_bot.send_message(
                chat_id=self.developer_chat_id,
                text=message_text,
                reply_markup=keyboard,
                parse_mode='Markdown'
            )
            
            return message.message_id
            
        except Exception as e:
            self.logger.error(f"Failed to send Telegram approval request: {str(e)}")
            return None
    
    async def _handle_approval_callback(self, callback: CallbackQuery):
        """Обработка нажатий на кнопки одобрения в Telegram"""
        try:
            data_parts = callback.data.split('_', 1)
            action = data_parts[0]
            question_id = data_parts[1] if len(data_parts) > 1 else None
            
            if not question_id:
                await callback.answer("Invalid callback data")
                return
            
            user_id = str(callback.from_user.id)
            
            # Обработка разных действий
            if action == "approve":
                result = await self.approve_question(question_id, user_id, "Approved via Telegram")
                
                if result['success']:
                    # Обновление сообщения
                    new_text = f"✅ **APPROVED** by {callback.from_user.first_name}\n\nQuestion ID: `{question_id}`"
                    await callback.message.edit_text(new_text, parse_mode='Markdown')
                    await callback.answer("Question approved! ✅")
                else:
                    await callback.answer(f"Failed to approve: {result.get('error', 'Unknown error')}")
            
            elif action == "needs_work":
                result = await self.mark_needs_work(question_id, user_id, "Marked as needs work via Telegram")
                
                if result['success']:
                    new_text = f"🔄 **NEEDS WORK** - marked by {callback.from_user.first_name}\n\nQuestion ID: `{question_id}`"
                    await callback.message.edit_text(new_text, parse_mode='Markdown')
                    await callback.answer("Question marked as needs work 🔄")
                else:
                    await callback.answer(f"Failed to mark: {result.get('error', 'Unknown error')}")
            
            elif action == "reject":
                result = await self.reject_question(question_id, user_id, "Rejected via Telegram")
                
                if result['success']:
                    new_text = f"❌ **REJECTED** by {callback.from_user.first_name}\n\nQuestion ID: `{question_id}`"
                    await callback.message.edit_text(new_text, parse_mode='Markdown')
                    await callback.answer("Question rejected ❌")
                else:
                    await callback.answer(f"Failed to reject: {result.get('error', 'Unknown error')}")
            
            elif action == "notes":
                # Для заметок нужна отдельная обработка
                await callback.answer("Please use the /add_notes command with question ID")
            
        except Exception as e:
            self.logger.error(f"Failed to handle approval callback: {str(e)}")
            await callback.answer("An error occurred while processing your request")
    
    async def approve_question(self, question_id: str, reviewer_id: str, feedback: str = None) -> Dict[str, Any]:
        """Одобрение вопроса"""
        return await self._update_question_status(
            question_id, QuestionStatus.APPROVED, reviewer_id, feedback
        )
    
    async def mark_needs_work(self, question_id: str, reviewer_id: str, feedback: str = None) -> Dict[str, Any]:
        """Отметка вопроса как требующего доработки"""
        return await self._update_question_status(
            question_id, QuestionStatus.NEEDS_WORK, reviewer_id, feedback
        )
    
    async def reject_question(self, question_id: str, reviewer_id: str, feedback: str = None) -> Dict[str, Any]:
        """Отклонение вопроса"""
        return await self._update_question_status(
            question_id, QuestionStatus.REJECTED, reviewer_id, feedback
        )
    
    async def pause_question(self, question_id: str, reviewer_id: str, feedback: str = None) -> Dict[str, Any]:
        """Постановка вопроса на паузу для доработки"""
        return await self._update_question_status(
            question_id, QuestionStatus.PAUSED, reviewer_id, feedback
        )
    
    async def approve_answered_question(self, question_id: str, user_id: str) -> Dict[str, Any]:
        """Автоматическое одобрение вопроса через ответ пользователя"""
        return await self._update_question_status(
            question_id, QuestionStatus.ANSWERED_APPROVED, f"user_{user_id}", 
            f"Auto-approved: user {user_id} provided answer"
        )
    
    async def _update_question_status(self, question_id: str, new_status: QuestionStatus, 
                                    reviewer_id: str, feedback: str = None) -> Dict[str, Any]:
        """Обновление статуса вопроса"""
        try:
            conn = sqlite3.connect(self.approval_db_path)
            cursor = conn.cursor()
            
            # Получение текущего статуса
            cursor.execute(
                "SELECT status FROM question_approvals WHERE question_id = ?",
                (question_id,)
            )
            result = cursor.fetchone()
            
            if not result:
                conn.close()
                return {'success': False, 'error': 'Question not found'}
            
            old_status = result[0]
            
            # Обновление статуса
            cursor.execute("""
                UPDATE question_approvals 
                SET status = ?, reviewed_at = CURRENT_TIMESTAMP, 
                    reviewer_id = ?, developer_feedback = ?, updated_at = CURRENT_TIMESTAMP
                WHERE question_id = ?
            """, (new_status.value, reviewer_id, feedback, question_id))
            
            conn.commit()
            conn.close()
            
            # Запись в историю
            await self._log_approval_action(
                question_id, 'status_update', old_status, new_status.value, reviewer_id, feedback
            )
            
            # Дополнительные действия при одобрении
            if new_status == QuestionStatus.APPROVED:
                await self._process_approved_question(question_id)
            
            return {
                'success': True,
                'question_id': question_id,
                'old_status': old_status,
                'new_status': new_status.value,
                'reviewer_id': reviewer_id
            }
            
        except Exception as e:
            self.logger.error(f"Failed to update question status: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    async def _process_approved_question(self, question_id: str):
        """Обработка одобренного вопроса - добавление в основную систему"""
        try:
            # Получение данных одобренного вопроса
            question_data = await self._get_question_data(question_id)
            
            if question_data:
                # Здесь будет интеграция с основной системой вопросов
                # Добавление в векторную БД и PostgreSQL
                await self._add_to_main_system(question_data)
                
                self.logger.info(f"Question {question_id} added to main system after approval")
        
        except Exception as e:
            self.logger.error(f"Failed to process approved question {question_id}: {str(e)}")
    
    async def _add_to_main_system(self, question_data: Dict[str, Any]):
        """Добавление одобренного вопроса в основную систему"""
        # TODO: Интеграция с основной системой вопросов
        # Это будет подключение к:
        # 1. intelligent_question_core/data/selfology_intelligent_core.json
        # 2. Qdrant векторной БД  
        # 3. PostgreSQL основной БД
        pass
    
    async def run_auto_approval_cycle(self) -> Dict[str, Any]:
        """Запуск цикла автоматического одобрения просроченных вопросов"""
        try:
            conn = sqlite3.connect(self.approval_db_path)
            cursor = conn.cursor()
            
            # Поиск вопросов для автоматического одобрения
            cursor.execute("""
                SELECT question_id, question_text FROM question_approvals 
                WHERE status = ? AND auto_approve_at <= CURRENT_TIMESTAMP
            """, (QuestionStatus.PENDING_REVIEW.value,))
            
            auto_approve_candidates = cursor.fetchall()
            conn.close()
            
            auto_approved = []
            
            for question_id, question_text in auto_approve_candidates:
                # Проверка отсутствия критических проблем
                question_data = await self._get_question_data(question_id)
                warnings = json.loads(question_data.get('warnings', '{}'))
                
                # Автоодобрение только если нет критических проблем
                if not warnings.get('critical_issues'):
                    result = await self._update_question_status(
                        question_id, QuestionStatus.AUTO_APPROVED, 'system', 
                        'Automatically approved after review period'
                    )
                    
                    if result['success']:
                        auto_approved.append({
                            'question_id': question_id,
                            'question_text': question_text[:100] + '...' if len(question_text) > 100 else question_text
                        })
            
            return {
                'success': True,
                'auto_approved_count': len(auto_approved),
                'auto_approved_questions': auto_approved
            }
            
        except Exception as e:
            self.logger.error(f"Failed to run auto approval cycle: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    async def get_pending_questions(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Получение списка вопросов ожидающих рассмотрения"""
        try:
            conn = sqlite3.connect(self.approval_db_path)
            conn.row_factory = sqlite3.Row  # Для доступа по имени колонки
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM question_approvals 
                WHERE status IN (?, ?) 
                ORDER BY 
                    CASE priority 
                        WHEN 'urgent' THEN 1 
                        WHEN 'high' THEN 2 
                        WHEN 'normal' THEN 3 
                        WHEN 'low' THEN 4 
                    END,
                    submitted_at DESC
                LIMIT ?
            """, (QuestionStatus.PENDING_REVIEW.value, QuestionStatus.NEEDS_WORK.value, limit))
            
            questions = []
            for row in cursor.fetchall():
                question_dict = dict(row)
                
                # Парсинг JSON полей
                if question_dict['question_metadata']:
                    question_dict['question_metadata'] = json.loads(question_dict['question_metadata'])
                if question_dict['warnings']:
                    question_dict['warnings'] = json.loads(question_dict['warnings'])
                
                questions.append(question_dict)
            
            conn.close()
            return questions
            
        except Exception as e:
            self.logger.error(f"Failed to get pending questions: {str(e)}")
            return []
    
    async def get_approval_statistics(self) -> Dict[str, Any]:
        """Получение статистики одобрения вопросов"""
        try:
            conn = sqlite3.connect(self.approval_db_path)
            cursor = conn.cursor()
            
            # Общая статистика по статусам
            cursor.execute("""
                SELECT status, COUNT(*) as count 
                FROM question_approvals 
                GROUP BY status
            """)
            status_counts = {row[0]: row[1] for row in cursor.fetchall()}
            
            # Статистика по приоритетам
            cursor.execute("""
                SELECT priority, COUNT(*) as count 
                FROM question_approvals 
                GROUP BY priority
            """)
            priority_counts = {row[0]: row[1] for row in cursor.fetchall()}
            
            # Статистика за последние 7 дней
            cursor.execute("""
                SELECT DATE(submitted_at) as date, COUNT(*) as count
                FROM question_approvals 
                WHERE submitted_at >= DATE('now', '-7 days')
                GROUP BY DATE(submitted_at)
                ORDER BY date
            """)
            daily_submissions = {row[0]: row[1] for row in cursor.fetchall()}
            
            # Средняя время рассмотрения
            cursor.execute("""
                SELECT AVG(JULIANDAY(reviewed_at) - JULIANDAY(submitted_at)) * 24 as avg_hours
                FROM question_approvals 
                WHERE reviewed_at IS NOT NULL
            """)
            avg_review_time = cursor.fetchone()[0] or 0
            
            conn.close()
            
            return {
                'status_counts': status_counts,
                'priority_counts': priority_counts,
                'daily_submissions': daily_submissions,
                'average_review_time_hours': round(avg_review_time, 2),
                'pending_count': status_counts.get(QuestionStatus.PENDING_REVIEW.value, 0),
                'needs_work_count': status_counts.get(QuestionStatus.NEEDS_WORK.value, 0),
                'approved_count': status_counts.get(QuestionStatus.APPROVED.value, 0),
                'auto_approved_count': status_counts.get(QuestionStatus.AUTO_APPROVED.value, 0)
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get approval statistics: {str(e)}")
            return {}
    
    async def run_approval_cycle(self) -> Dict[str, Any]:
        """Запуск полного цикла одобрения вопросов"""
        cycle_results = {
            'timestamp': datetime.now().isoformat(),
            'auto_approval_results': {},
            'pending_questions': [],
            'statistics': {},
            'processed_questions': []
        }
        
        # Запуск автоматического одобрения
        cycle_results['auto_approval_results'] = await self.run_auto_approval_cycle()
        
        # Получение текущих ожидающих вопросов
        cycle_results['pending_questions'] = await self.get_pending_questions()
        
        # Получение статистики
        cycle_results['statistics'] = await self.get_approval_statistics()
        
        # Подсчет обработанных вопросов
        auto_approved = cycle_results['auto_approval_results'].get('auto_approved_count', 0)
        cycle_results['processed_questions'] = [
            {'action': 'auto_approved', 'count': auto_approved}
        ]
        
        return cycle_results
    
    async def process_telegram_feedback(self, user_id: int, question_id: str, 
                                      action: str, feedback: Optional[str] = None) -> Dict[str, Any]:
        """Обработка обратной связи из Telegram"""
        reviewer_id = str(user_id)
        
        if action == 'approve':
            return await self.approve_question(question_id, reviewer_id, feedback)
        elif action == 'needs_work':
            return await self.mark_needs_work(question_id, reviewer_id, feedback)
        elif action == 'reject':
            return await self.reject_question(question_id, reviewer_id, feedback)
        else:
            return {'success': False, 'error': f'Unknown action: {action}'}
    
    async def check_pending_approvals(self) -> Dict[str, Any]:
        """Проверка количества ожидающих одобрения вопросов"""
        try:
            conn = sqlite3.connect(self.approval_db_path)
            cursor = conn.cursor()
            
            # Подсчет по приоритетам
            cursor.execute("""
                SELECT priority, COUNT(*) as count
                FROM question_approvals 
                WHERE status IN (?, ?)
                GROUP BY priority
            """, (QuestionStatus.PENDING_REVIEW.value, QuestionStatus.NEEDS_WORK.value))
            
            priority_counts = {}
            total_pending = 0
            
            for priority, count in cursor.fetchall():
                priority_counts[priority] = count
                total_pending += count
                
            # Подсчет срочных (просроченных)
            cursor.execute("""
                SELECT COUNT(*) FROM question_approvals 
                WHERE status = ? AND auto_approve_at <= CURRENT_TIMESTAMP
            """, (QuestionStatus.PENDING_REVIEW.value,))
            
            overdue_count = cursor.fetchone()[0]
            
            conn.close()
            
            return {
                'total_pending': total_pending,
                'priority_breakdown': priority_counts,
                'overdue_count': overdue_count,
                'urgent_approvals': priority_counts.get('urgent', 0) + overdue_count
            }
            
        except Exception as e:
            self.logger.error(f"Failed to check pending approvals: {str(e)}")
            return {'total_pending': 0, 'urgent_approvals': 0}
    
    async def _question_already_exists(self, question_id: str) -> bool:
        """Проверка существования вопроса в системе одобрения"""
        try:
            conn = sqlite3.connect(self.approval_db_path)
            cursor = conn.cursor()
            
            cursor.execute(
                "SELECT 1 FROM question_approvals WHERE question_id = ?",
                (question_id,)
            )
            
            exists = cursor.fetchone() is not None
            conn.close()
            
            return exists
            
        except Exception as e:
            self.logger.error(f"Failed to check question existence: {str(e)}")
            return False
    
    async def _get_question_data(self, question_id: str) -> Optional[Dict[str, Any]]:
        """Получение данных вопроса"""
        try:
            conn = sqlite3.connect(self.approval_db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute(
                "SELECT * FROM question_approvals WHERE question_id = ?",
                (question_id,)
            )
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                question_dict = dict(result)
                
                # Парсинг JSON полей
                if question_dict['question_metadata']:
                    question_dict['question_metadata'] = json.loads(question_dict['question_metadata'])
                if question_dict['warnings']:
                    question_dict['warnings'] = json.loads(question_dict['warnings'])
                
                return question_dict
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to get question data: {str(e)}")
            return None
    
    async def _update_telegram_message_id(self, question_id: str, message_id: int):
        """Обновление ID Telegram сообщения"""
        try:
            conn = sqlite3.connect(self.approval_db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE question_approvals 
                SET telegram_message_id = ?, updated_at = CURRENT_TIMESTAMP
                WHERE question_id = ?
            """, (message_id, question_id))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            self.logger.error(f"Failed to update telegram message ID: {str(e)}")
    
    async def _log_approval_action(self, question_id: str, action: str, previous_status: str, 
                                 new_status: str, reviewer_id: str, feedback: str = None):
        """Логирование действий в системе одобрения"""
        try:
            conn = sqlite3.connect(self.approval_db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO approval_history 
                (question_id, action, previous_status, new_status, reviewer_id, feedback)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (question_id, action, previous_status, new_status, reviewer_id, feedback))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            self.logger.error(f"Failed to log approval action: {str(e)}")
    
    async def _handle_pending_questions_command(self, message: types.Message):
        """Обработка команды получения ожидающих вопросов"""
        pending = await self.get_pending_questions(10)  # Top 10
        
        if not pending:
            await message.reply("No questions pending approval! ✅")
            return
        
        response = f"📝 **PENDING QUESTIONS** ({len(pending)})\n\n"
        
        for i, question in enumerate(pending[:5], 1):  # Show first 5
            status_emoji = "🔄" if question['status'] == 'needs_work' else "⏳"
            priority_emoji = {"urgent": "🔴", "high": "🟡", "normal": "🟢", "low": "⚪"}.get(question['priority'], "⚪")
            
            response += f"{i}. {status_emoji}{priority_emoji} `{question['question_id']}`\n"
            response += f"   {question['question_text'][:80]}...\n"
            response += f"   Domain: {question['domain']} | Priority: {question['priority']}\n\n"
        
        if len(pending) > 5:
            response += f"... and {len(pending) - 5} more questions\n"
        
        response += "\nUse inline buttons or /approve_question <id> to process"
        
        await message.reply(response, parse_mode='Markdown')
    
    async def _handle_approval_stats_command(self, message: types.Message):
        """Обработка команды получения статистики"""
        stats = await self.get_approval_statistics()
        
        if not stats:
            await message.reply("Unable to retrieve statistics")
            return
        
        response = f"""📊 **APPROVAL STATISTICS**

**Status Distribution:**
✅ Approved: {stats.get('approved_count', 0)}
🔄 Needs Work: {stats.get('needs_work_count', 0)}
⏳ Pending: {stats.get('pending_count', 0)}
🤖 Auto-approved: {stats.get('auto_approved_count', 0)}

**Priority Distribution:**
🔴 Urgent: {stats.get('priority_counts', {}).get('urgent', 0)}
🟡 High: {stats.get('priority_counts', {}).get('high', 0)}
🟢 Normal: {stats.get('priority_counts', {}).get('normal', 0)}
⚪ Low: {stats.get('priority_counts', {}).get('low', 0)}

**Performance:**
⏱ Avg Review Time: {stats.get('average_review_time_hours', 0):.1f} hours
"""
        
        await message.reply(response, parse_mode='Markdown')


# CLI interface для управления системой одобрения вопросов
async def main():
    """CLI интерфейс для системы одобрения вопросов"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Question Approval Workflow System")
    parser.add_argument('action', choices=['pending', 'stats', 'approve', 'reject', 'auto-approve'])
    parser.add_argument('--question-id', help='Question ID for approval actions')
    parser.add_argument('--feedback', help='Feedback for approval actions')
    parser.add_argument('--limit', type=int, default=10, help='Limit for listing questions')
    
    args = parser.parse_args()
    
    workflow = QuestionApprovalWorkflow()
    
    if args.action == 'pending':
        questions = await workflow.get_pending_questions(args.limit)
        print(f"\n📝 PENDING QUESTIONS ({len(questions)}):")
        print("=" * 50)
        
        for question in questions:
            print(f"ID: {question['question_id']}")
            print(f"Priority: {question['priority']} | Status: {question['status']}")
            print(f"Text: {question['question_text'][:100]}...")
            print(f"Domain: {question['domain']} | Energy: {question['energy_type']}")
            print(f"Submitted: {question['submitted_at']}")
            print("-" * 30)
    
    elif args.action == 'stats':
        stats = await workflow.get_approval_statistics()
        print(f"\n📊 APPROVAL STATISTICS:")
        print("=" * 30)
        print(f"Pending: {stats.get('pending_count', 0)}")
        print(f"Approved: {stats.get('approved_count', 0)}")
        print(f"Needs Work: {stats.get('needs_work_count', 0)}")
        print(f"Auto-approved: {stats.get('auto_approved_count', 0)}")
        print(f"Avg Review Time: {stats.get('average_review_time_hours', 0):.1f}h")
    
    elif args.action == 'auto-approve':
        result = await workflow.run_auto_approval_cycle()
        print(f"\n🤖 AUTO-APPROVAL CYCLE:")
        print(f"Auto-approved: {result.get('auto_approved_count', 0)} questions")
    
    elif args.action in ['approve', 'reject']:
        if not args.question_id:
            print("❌ --question-id required for approval actions")
            return
        
        if args.action == 'approve':
            result = await workflow.approve_question(args.question_id, 'cli_user', args.feedback)
        else:
            result = await workflow.reject_question(args.question_id, 'cli_user', args.feedback)
        
        if result['success']:
            print(f"✅ Question {args.question_id} {args.action}d successfully")
        else:
            print(f"❌ Failed to {args.action} question: {result.get('error')}")


if __name__ == "__main__":
    asyncio.run(main())