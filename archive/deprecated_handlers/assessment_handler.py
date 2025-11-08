"""
Assessment Handler - Pure routing to Assessment Engine service
NO business logic - only routes requests to Assessment Engine
"""
import asyncpg
from aiogram import Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from ...services.assessment_engine import AssessmentEngine
from ...core.logging import telegram_logger


class AssessmentStates(StatesGroup):
    answering_question = State()


def setup_assessment_handlers(dp: Dispatcher, db_pool: asyncpg.Pool):
    """Setup assessment handlers - pure routing only"""
    
    # Initialize assessment engine
    assessment_engine = AssessmentEngine(db_pool)
    
    @dp.message(Command("assessment"))
    async def cmd_assessment(message: Message, state: FSMContext):
        """Route /assessment command to Assessment Engine"""
        
        telegram_logger.log_user_action("assessment_command", str(message.from_user.id))
        
        # Extract telegram user data
        telegram_data = {
            "username": message.from_user.username,
            "first_name": message.from_user.first_name,
            "last_name": message.from_user.last_name
        }
        
        # Route to Assessment Engine
        result = await assessment_engine.start_assessment(
            str(message.from_user.id), 
            telegram_data
        )
        
        if result.success:
            # Build response with next question
            if result.next_question:
                question_text = f"""
🧠 **Психологическая оценка**

**Вопрос:** {result.next_question['text']}

**Прогресс:** {result.data.get('questions_completed', 0)} ответов
**Этап:** {result.data.get('assessment_stage', 'начальный')}

Ответьте подробно текстовым сообщением.
                """
                
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="⏭️ Пропустить", callback_data="skip_question")],
                    [InlineKeyboardButton(text="📊 Статус", callback_data="assessment_status")]
                ])
                
                await message.answer(question_text, reply_markup=keyboard)
                await state.set_state(AssessmentStates.answering_question)
                await state.update_data(current_question_id=result.next_question['id'])
            
            else:
                await message.answer("❌ Нет доступных вопросов для оценки")
        
        else:
            await message.answer(f"❌ Ошибка запуска оценки: {result.message}")
    
    @dp.message(AssessmentStates.answering_question)
    async def handle_assessment_answer(message: Message, state: FSMContext):
        """Route assessment answer to Assessment Engine"""
        
        user_id = str(message.from_user.id)
        answer_text = message.text
        
        # Get current question ID from state
        state_data = await state.get_data()
        question_id = state_data.get('current_question_id')
        
        if not question_id:
            await message.answer("❌ Ошибка: не найден активный вопрос")
            return
        
        # Route to Assessment Engine
        result = await assessment_engine.process_answer(user_id, question_id, answer_text)
        
        if result.success:
            # Show analysis and next question
            analysis = result.data.get('analysis', {})
            
            response_text = f"""
✅ **Ответ принят и проанализирован**

📊 **Анализ:**
• Эмоциональное состояние: {analysis.get('emotional_state', 'нейтральное')}
• Уровень открытости: {analysis.get('openness_level', 0.0):.1f}/1.0
• Глубина размышлений: {analysis.get('depth_of_reflection', 0.0):.1f}/1.0

**Прогресс:** {result.data.get('questions_completed', 0)} ответов завершено
            """
            
            # Check if assessment complete
            if result.data.get('assessment_complete'):
                response_text += "\n\n🎉 **Оценка завершена!**\nВаш психологический профиль создан."
                
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="💬 Начать чат", callback_data="start_chat")],
                    [InlineKeyboardButton(text="📊 Мой профиль", callback_data="show_profile")]
                ])
                
                await message.answer(response_text, reply_markup=keyboard)
                await state.clear()
                
            elif result.next_question:
                # Continue with next question
                question_text = f"\n\n**Следующий вопрос:**\n{result.next_question['text']}"
                
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="⏭️ Следующий", callback_data="show_next_question")],
                    [InlineKeyboardButton(text="📊 Статус", callback_data="assessment_status")]
                ])
                
                await message.answer(response_text + question_text, reply_markup=keyboard)
                await state.update_data(current_question_id=result.next_question['id'])
                
            else:
                # No more questions
                await message.answer(response_text + "\n\n✨ Оценка завершена!")
                await state.clear()
        
        else:
            await message.answer(f"❌ Ошибка обработки ответа: {result.message}")
    
    @dp.callback_query(F.data == "assessment_status")
    async def show_assessment_status(callback: CallbackQuery):
        """Route status request to Assessment Engine"""
        
        user_id = str(callback.from_user.id)
        
        # Route to Assessment Engine
        result = await assessment_engine.get_assessment_status(user_id)
        
        if result.success:
            status_data = result.data
            stats = status_data.get('assessment_stats', {})
            
            status_text = f"""
📊 **Статус вашей оценки**

**Основные показатели:**
• Всего ответов: {stats.get('total_answers', 0)}
• Исследованных областей: {len(stats.get('domain_coverage', []))}
• Оценка завершена: {'✅ Да' if status_data.get('assessment_complete') else '❌ Нет'}

**Текущий этап:** {status_data.get('assessment_stage', 'не определен')}

**Доступность следующего вопроса:** {'✅ Да' if status_data.get('next_question_available') else '❌ Нет'}
            """
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Продолжить", callback_data="continue_assessment")],
                [InlineKeyboardButton(text="📈 Подробная статистика", callback_data="detailed_stats")]
            ])
            
            await callback.message.edit_text(status_text, reply_markup=keyboard)
        
        else:
            await callback.answer(f"Ошибка получения статуса: {result.message}")
    
    @dp.callback_query(F.data == "continue_assessment") 
    async def continue_assessment(callback: CallbackQuery, state: FSMContext):
        """Continue assessment with next question"""
        
        user_id = str(callback.from_user.id)
        
        # Get status with next question
        result = await assessment_engine.get_assessment_status(user_id)
        
        if result.success and result.next_question:
            question_text = f"""
🧠 **Продолжаем оценку**

**Вопрос:** {result.next_question['text']}

Ответьте подробно текстовым сообщением.
            """
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⏭️ Пропустить", callback_data="skip_question")],
                [InlineKeyboardButton(text="📊 Статус", callback_data="assessment_status")]
            ])
            
            await callback.message.edit_text(question_text, reply_markup=keyboard)
            await state.set_state(AssessmentStates.answering_question)
            await state.update_data(current_question_id=result.next_question['id'])
        
        else:
            await callback.answer("Нет доступных вопросов для продолжения")
    
    @dp.callback_query(F.data == "skip_question")
    async def skip_question(callback: CallbackQuery, state: FSMContext):
        """Skip current question"""
        
        # For now, just show status
        # In production might implement actual skip logic
        await show_assessment_status(callback)
    
    telegram_logger.info("Assessment handlers configured")