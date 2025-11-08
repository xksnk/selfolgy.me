"""
Profile Handler - Pure routing to User Profile service
NO business logic - only routes requests to User Profile Service
"""
import asyncpg
from aiogram import Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
import json

from ...services.user_profile_service import UserProfileService
from ...core.logging import telegram_logger


def setup_profile_handlers(dp: Dispatcher, db_pool: asyncpg.Pool):
    """Setup profile handlers - pure routing only"""
    
    # Initialize profile service
    profile_service = UserProfileService(db_pool)
    
    @dp.message(Command("profile"))
    async def cmd_profile(message: Message):
        """Route /profile command to User Profile Service"""
        
        user_id = str(message.from_user.id)
        telegram_logger.log_user_action("profile_command", user_id)
        
        # Route to User Profile Service
        result = await profile_service.get_profile(user_id, include_insights=True)
        
        if result.success:
            profile_data = result.profile_data
            basic_info = profile_data.get('basic_info', {})
            personality_analysis = profile_data.get('personality_analysis', {})
            completeness = profile_data.get('profile_completeness', {})
            
            profile_text = f"""
👤 **Ваш профиль в Selfology**

**📋 Основная информация:**
• Имя: {basic_info.get('first_name', 'Не указано')}
• Статус: {'✅ Активный' if basic_info.get('gdpr_consent') else '❌ Ограниченный'}
• Онбординг: {'✅ Завершен' if basic_info.get('onboarding_completed') else '🔄 В процессе'}

**📊 Полнота профиля:** {completeness.get('completeness_score', 0.0):.1%}
**Уровень:** {get_completeness_description(completeness.get('completeness_level', 'basic'))}

**🧠 Анализ личности:**
{format_personality_analysis(personality_analysis)}

**💡 Инсайты:** {len(profile_data.get('insights', []))} доступно

⏱️ *Обработано за {result.processing_time:.2f}с*
            """
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🧠 Детальный анализ", callback_data="detailed_personality")],
                [InlineKeyboardButton(text="💡 Показать инсайты", callback_data="show_insights")],
                [InlineKeyboardButton(text="📈 Развитие личности", callback_data="personality_development")],
                [InlineKeyboardButton(text="📤 Экспорт данных", callback_data="export_profile")]
            ])
            
            await message.answer(profile_text, reply_markup=keyboard)
            
            # Show recommendations if available
            if result.recommendations:
                rec_text = "🎯 **Рекомендации:**\n" + '\n'.join([f"• {rec}" for rec in result.recommendations[:3]])
                await message.answer(rec_text)
        
        else:
            await message.answer(f"❌ Ошибка загрузки профиля: {result.message}")
    
    @dp.callback_query(F.data == "detailed_personality")
    async def show_detailed_personality(callback: CallbackQuery):
        """Route to detailed personality analysis"""
        
        user_id = str(callback.from_user.id)
        
        # Route to User Profile Service
        result = await profile_service.get_profile(user_id, include_insights=True)
        
        if result.success:
            personality_analysis = result.profile_data.get('personality_analysis', {})
            
            if personality_analysis.get('available'):
                big_five = personality_analysis.get('big_five', {})
                values_analysis = personality_analysis.get('values', {})
                
                detailed_text = f"""
🧠 **Детальный анализ личности**

**🎭 Модель "Большая Пятерка":**
{format_big_five_detailed(big_five.get('traits', {}))}

**💎 Ваши ценности:**
{format_values_analysis(values_analysis)}

**🎯 Тип личности:** {personality_analysis.get('personality_type', 'Не определен')}

**📊 Уверенность в анализе:** {personality_analysis.get('confidence_score', 0.0):.1%}

**🎨 Краткая характеристика:**
{big_five.get('personality_summary', 'Анализ недоступен')}
                """
                
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔄 Обновить анализ", callback_data="update_personality")],
                    [InlineKeyboardButton(text="👥 Похожие профили", callback_data="similar_profiles")]
                ])
                
                await callback.message.edit_text(detailed_text, reply_markup=keyboard)
            
            else:
                await callback.message.edit_text("""
🧠 **Анализ личности недоступен**

Для создания детального анализа необходимо:
• Пройти психологическое анкетирование
• Ответить минимум на 10 вопросов

Начните с команды /assessment
                """)
        
        else:
            await callback.answer(f"Ошибка: {result.message}")
    
    @dp.callback_query(F.data == "show_insights")
    async def show_profile_insights(callback: CallbackQuery):
        """Route to profile insights"""
        
        user_id = str(callback.from_user.id)
        
        result = await profile_service.get_profile(user_id, include_insights=True)
        
        if result.success:
            insights = result.profile_data.get('insights', [])
            
            if insights:
                insights_text = "💡 **Ваши персональные инсайты:**\n\n"
                
                for i, insight in enumerate(insights[:5], 1):
                    insights_text += f"**{i}. {insight.get('title', 'Инсайт')}**\n"
                    insights_text += f"{insight.get('description', 'Описание недоступно')}\n"
                    insights_text += f"*Уверенность: {insight.get('confidence', 0.0):.1%}*\n\n"
                
                if len(insights) > 5:
                    insights_text += f"... еще {len(insights) - 5} инсайтов доступно"
            
            else:
                insights_text = """
💡 **Инсайты пока недоступны**

Инсайты генерируются по мере:
• Прохождения анкетирования
• Активного общения с AI-коучем
• Накопления данных о вашей личности

Продолжайте использовать Selfology!
                """
            
            await callback.message.edit_text(insights_text)
        
        else:
            await callback.answer(f"Ошибка: {result.message}")
    
    @dp.callback_query(F.data == "personality_development")
    async def show_personality_development(callback: CallbackQuery):
        """Route to personality development analysis"""
        
        user_id = str(callback.from_user.id)
        
        # Route to User Profile Service for development analysis
        result = await profile_service.analyze_personality_development(user_id, days=90)
        
        if result.success:
            development_data = result.profile_data
            trends = development_data.get('development_trends', {})
            insights = development_data.get('insights', {})
            
            development_text = f"""
📈 **Анализ развития личности (90 дней)**

**📊 Период анализа:** {development_data.get('analysis_period_days')} дней
**Точек данных:** {development_data.get('data_points')}

**🎯 Тренды развития:**
• Общий тренд: {trends.get('trend_analysis', 'не определен')}
• Стабильность: {trends.get('stability_score', 0.0):.1%}
• Стадия развития: {trends.get('development_stage', 'неизвестно')}

**🌱 Области роста:**
{format_growth_areas(trends.get('growth_areas', []))}

**💡 Ключевые инсайты:**
{format_key_insights(insights.get('key_insights', []))}

⏱️ *Обработано за {result.processing_time:.2f}с*
            """
            
            if result.recommendations:
                development_text += f"\n\n🎯 **Рекомендации по развитию:**\n"
                development_text += '\n'.join([f"• {rec}" for rec in result.recommendations[:3]])
            
            await callback.message.edit_text(development_text)
        
        else:
            if "Insufficient data" in result.message:
                await callback.message.edit_text("""
📈 **Анализ развития недоступен**

Для анализа развития личности нужно:
• Минимум 2 точки данных за период
• Активное использование системы
• Регулярные обновления профиля

Продолжайте пользоваться Selfology, и анализ станет доступен!
                """)
            else:
                await callback.answer(f"Ошибка анализа: {result.message}")
    
    @dp.callback_query(F.data == "export_profile")
    async def export_user_profile(callback: CallbackQuery):
        """Route to profile export (GDPR compliance)"""
        
        user_id = str(callback.from_user.id)
        
        await callback.answer("📤 Подготавливаю экспорт данных...")
        
        # Route to User Profile Service for export
        result = await profile_service.export_profile_data(user_id)
        
        if result.success:
            export_data = result.profile_data
            export_info = export_data.get('export_info', {})
            
            export_summary = f"""
📤 **Экспорт данных завершен**

**📋 Информация об экспорте:**
• Пользователь: {export_info.get('user_id', 'неизвестен')}
• Дата экспорта: {export_info.get('exported_at', 'неизвестно')}
• Версия экспорта: {export_info.get('export_version', '1.0')}

**📊 Экспортированные данные:**
• Профиль пользователя: ✅
• Векторы личности: {len(export_data.get('personality_vectors', []))} записей
• История чатов: {len(export_data.get('chat_history', []))} сообщений
• Инсайты: {len(export_data.get('insights', []))} записей
• Лог активности: {len(export_data.get('activity_log', []))} событий

**🔐 GDPR соответствие:**
• Политика хранения данных: учтена
• Права на удаление: сохранены
• Портируемость данных: обеспечена

⏱️ *Обработано за {result.processing_time:.2f}с*

*Данные подготовлены для экспорта. В реальной системе здесь был бы файл для скачивания.*
            """
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🗑️ Удалить все данные", callback_data="delete_profile_confirm")],
                [InlineKeyboardButton(text="🔄 Повторить экспорт", callback_data="export_profile")]
            ])
            
            await callback.message.edit_text(export_summary, reply_markup=keyboard)
        
        else:
            await callback.answer(f"Ошибка экспорта: {result.message}")
    
    @dp.callback_query(F.data == "delete_profile_confirm")
    async def confirm_profile_deletion(callback: CallbackQuery):
        """Confirm profile deletion"""
        
        confirm_text = """
⚠️ **ВНИМАНИЕ: Удаление всех данных**

Это действие удалит ВСЕ ваши данные из Selfology:
• Профиль пользователя
• Все ответы на вопросы
• Историю чатов
• Векторы личности
• Все инсайты и аналитику

**Это действие необратимо!**

Вы уверены, что хотите продолжить?
        """
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🗑️ Да, удалить ВСЕ", callback_data="delete_profile_final")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_deletion")]
        ])
        
        await callback.message.edit_text(confirm_text, reply_markup=keyboard)
    
    @dp.callback_query(F.data == "delete_profile_final")
    async def delete_user_profile_final(callback: CallbackQuery):
        """Final profile deletion"""
        
        user_id = str(callback.from_user.id)
        
        await callback.answer("🗑️ Удаляю все данные...")
        
        # Route to User Profile Service for deletion
        result = await profile_service.delete_profile(user_id)
        
        if result.success:
            deletion_data = result.profile_data
            
            final_text = f"""
✅ **Данные успешно удалены**

**📊 Результат удаления:**
• Пользователь: {'✅ Удален' if deletion_data.get('user_deleted') else '❌ Ошибка'}
• Векторная база: {'✅ Очищена' if deletion_data.get('vector_deleted') else '❌ Ошибка'}
• Время удаления: {deletion_data.get('deletion_timestamp', 'неизвестно')}

Все ваши данные были полностью удалены из системы Selfology в соответствии с требованиями GDPR.

До свидания! Если захотите вернуться, просто нажмите /start для создания нового профиля.

⏱️ *Обработано за {result.processing_time:.2f}с*
            """
            
            await callback.message.edit_text(final_text)
        
        else:
            await callback.answer(f"Ошибка удаления: {result.message}")
    
    @dp.callback_query(F.data == "cancel_deletion")
    async def cancel_profile_deletion(callback: CallbackQuery):
        """Cancel profile deletion"""
        
        await callback.message.edit_text("✅ Удаление отменено. Ваши данные в безопасности.")
    
    telegram_logger.info("Profile handlers configured")


def get_completeness_description(level: str) -> str:
    """Get completeness level description"""
    
    descriptions = {
        "excellent": "🌟 Превосходный",
        "good": "👍 Хороший", 
        "moderate": "📈 Средний",
        "basic": "🔰 Базовый"
    }
    
    return descriptions.get(level, level)


def format_personality_analysis(personality_analysis: dict) -> str:
    """Format personality analysis for display"""
    
    if not personality_analysis.get('available'):
        return "❌ Анализ недоступен (пройдите анкетирование)"
    
    personality_type = personality_analysis.get('personality_type', 'Не определен')
    confidence = personality_analysis.get('confidence_score', 0.0)
    
    return f"• Тип: {personality_type}\n• Уверенность: {confidence:.1%}"


def format_big_five_detailed(traits: dict) -> str:
    """Format Big Five traits in detail"""
    
    if not traits:
        return "• Данные недоступны"
    
    trait_names = {
        'openness': '🎨 Открытость',
        'conscientiousness': '📋 Добросовестность',
        'extraversion': '👥 Экстраверсия',
        'agreeableness': '🤝 Доброжелательность',
        'neuroticism': '😰 Нейротизм'
    }
    
    lines = []
    for trait, trait_info in traits.items():
        name = trait_names.get(trait, trait)
        score = trait_info.get('score', 0.0)
        level = trait_info.get('level', 'неизвестно')
        
        lines.append(f"• {name}: {score:.1%} ({level})")
    
    return '\n'.join(lines)


def format_values_analysis(values_analysis: dict) -> str:
    """Format values analysis"""
    
    if not values_analysis.get('available'):
        return "• Анализ ценностей недоступен"
    
    top_values = values_analysis.get('top_values', [])
    
    if not top_values:
        return "• Ценности не определены"
    
    lines = []
    for value_info in top_values:
        value = value_info.get('value', 'неизвестно')
        score = value_info.get('score', 0.0)
        
        lines.append(f"• {value.title()}: {score:.1%}")
    
    return '\n'.join(lines)


def format_growth_areas(growth_areas: list) -> str:
    """Format growth areas"""
    
    if not growth_areas:
        return "• Области роста определяются"
    
    return '\n'.join([f"• {area.title()}" for area in growth_areas[:3]])


def format_key_insights(key_insights: list) -> str:
    """Format key insights"""
    
    if not key_insights:
        return "• Инсайты накапливаются"
    
    return '\n'.join([f"• {insight}" for insight in key_insights[:3]])