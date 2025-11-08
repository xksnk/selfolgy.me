"""
Statistics Handler - Pure routing to Statistics service
NO business logic - only routes requests to Statistics Service
"""
import asyncpg
from aiogram import Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup

from ...services.statistics_service import StatisticsService
from ...core.logging import telegram_logger


def setup_stats_handlers(dp: Dispatcher, db_pool: asyncpg.Pool):
    """Setup statistics handlers - pure routing only"""
    
    # Initialize statistics service
    stats_service = StatisticsService(db_pool)
    
    @dp.message(Command("stats"))
    async def cmd_stats(message: Message):
        """Route /stats command to Statistics Service"""
        
        user_id = str(message.from_user.id)
        telegram_logger.log_user_action("stats_command", user_id)
        
        # Route to Statistics Service
        result = await stats_service.get_user_statistics(user_id, include_detailed=False)
        
        if result.success:
            stats_data = result.data
            
            # Format basic statistics
            basic_stats = stats_data.get('assessment', {})
            chat_stats = stats_data.get('chat_activity', {})
            engagement = stats_data.get('engagement', {})
            
            stats_text = f"""
📊 **Ваша статистика**

**🧠 Психологическая оценка:**
• Всего ответов: {basic_stats.get('total_answers', 0)}
• Средняя уверенность: {basic_stats.get('avg_confidence', 0.0):.1%}
• Дней активности: {basic_stats.get('active_days', 0)}

**💬 Общение с AI:**
• Всего сообщений: {chat_stats.get('total_messages', 0)}
• Ваших сообщений: {chat_stats.get('user_messages', 0)}
• Ответов AI: {chat_stats.get('ai_responses', 0)}

**📈 Вовлеченность:**
• Общий балл: {engagement.get('engagement_score', 0.0):.1%}
• Активность в чате: {engagement.get('message_engagement', 0.0):.1%}
• Прогресс в оценке: {engagement.get('assessment_engagement', 0.0):.1%}

⏱️ *Обработано за {result.processing_time:.2f}с*
            """
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📊 Подробная статистика", callback_data="detailed_stats")],
                [InlineKeyboardButton(text="📈 Анализ развития", callback_data="development_stats")],
                [InlineKeyboardButton(text="🌐 Системная статистика", callback_data="system_stats")]
            ])
            
            await message.answer(stats_text, reply_markup=keyboard)
        
        else:
            await message.answer(f"❌ Ошибка получения статистики: {result.message}")
    
    @dp.callback_query(F.data == "detailed_stats")
    async def show_detailed_stats(callback: CallbackQuery):
        """Route to detailed statistics"""
        
        user_id = str(callback.from_user.id)
        
        # Route to Statistics Service with detailed flag
        result = await stats_service.get_user_statistics(user_id, include_detailed=True)
        
        if result.success:
            stats_data = result.data
            domain_analysis = stats_data.get('domain_analysis', {})
            personality_insights = stats_data.get('personality_insights', {})
            
            detailed_text = f"""
📊 **Подробная статистика**

**🗺️ Исследованные области:**
{format_domain_coverage(domain_analysis.get('explored_domains', []))}

**🎯 Покрытие областей:** {domain_analysis.get('domain_coverage', 0.0):.1%}

**🧠 Личностный анализ:**
• Профиль доступен: {'✅' if personality_insights.get('available') else '❌'}
• Тип личности: {personality_insights.get('personality_type', 'не определен')}
• Уверенность в профиле: {personality_insights.get('confidence_score', 0.0):.1%}

**📈 Временная активность:**
• Период анализа: 30 дней
• Активных дней: {len(stats_data.get('activity_timeline', []))}

⚡ *Кеш: {'попадание' if result.cache_hit else 'промах'}*
            """
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Обновить", callback_data="refresh_stats")],
                [InlineKeyboardButton(text="📤 Экспорт данных", callback_data="export_profile")]
            ])
            
            await callback.message.edit_text(detailed_text, reply_markup=keyboard)
        
        else:
            await callback.answer(f"Ошибка: {result.message}")
    
    @dp.callback_query(F.data == "development_stats")
    async def show_development_stats(callback: CallbackQuery):
        """Route to development analysis"""
        
        user_id = str(callback.from_user.id)
        
        # Route to engagement analysis
        result = await stats_service.get_engagement_analysis(days=90)
        
        if result.success:
            engagement_data = result.data
            
            dev_text = f"""
📈 **Анализ развития (90 дней)**

**📊 Активность по дням:**
• Период: {engagement_data.get('period_days')} дней
• Анализируемых дней: {len(engagement_data.get('daily_active_users', []))}

**💬 Активность в сообщениях:**
• Общая динамика: {'📈 Рост' if len(engagement_data.get('message_activity', [])) > 0 else '📉 Данных мало'}

**🧠 Прогресс в оценке:**
• Динамика ответов: {'📈 Активность' if len(engagement_data.get('assessment_activity', [])) > 0 else '📊 Стабильность'}

**🎯 Показатели удержания:**
• Оценки вовлеченности: доступны
• Паттерны активности: анализируются

⏱️ *Обработано за {result.processing_time:.2f}с*
            """
            
            await callback.message.edit_text(dev_text)
        
        else:
            await callback.answer(f"Ошибка анализа развития: {result.message}")
    
    @dp.callback_query(F.data == "system_stats")
    async def show_system_stats(callback: CallbackQuery):
        """Route to system overview"""
        
        # Route to Statistics Service for system overview
        result = await stats_service.get_system_overview()
        
        if result.success:
            system_data = result.data
            user_stats = system_data.get('user_statistics', {})
            system_health = system_data.get('system_health', {})
            
            system_text = f"""
🌐 **Системная статистика**

**👥 Пользователи:**
• Всего пользователей: {user_stats.get('basic_stats', {}).get('total_users', 0)}
• Активны сегодня: {user_stats.get('basic_stats', {}).get('active_daily', 0)}
• Завершили онбординг: {user_stats.get('basic_stats', {}).get('completed_users', 0)}

**🔧 Здоровье системы:**
• Общее состояние: {system_health.get('overall_health', 0.0):.1%}
• Статус: {system_health.get('status', 'unknown').upper()}
• Размер БД: {system_health.get('database_size_mb', 0)} МБ

**📊 Производительность:**
• Среднее время ответа: {system_data.get('performance', {}).get('average_response_time_ms', 0)}мс
• Успешность API: {system_data.get('performance', {}).get('api_success_rate', 0.0):.1%}

**📈 Рост системы:**
• Тренд: {system_data.get('growth_metrics', {}).get('growth_trend', 'неизвестен')}

⚡ *Кеш: {'попадание' if result.cache_hit else 'промах'}*
            """
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Обновить", callback_data="refresh_system_stats")],
                [InlineKeyboardButton(text="📊 Аналитика областей", callback_data="domain_analytics")]
            ])
            
            await callback.message.edit_text(system_text, reply_markup=keyboard)
        
        else:
            await callback.answer(f"Ошибка системной статистики: {result.message}")
    
    @dp.callback_query(F.data == "domain_analytics")
    async def show_domain_analytics(callback: CallbackQuery):
        """Route to domain analytics"""
        
        # Route to Statistics Service for domain analytics
        result = await stats_service.get_domain_analytics()
        
        if result.success:
            domain_data = result.data
            coverage = domain_data.get('domain_coverage', [])
            
            domain_text = f"""
🗺️ **Аналитика психологических областей**

**📊 Покрытие областей:**
{format_domain_coverage_stats(coverage[:5])}

**👥 Паттерны исследования:**
• Пользователей с 5+ ответами: {len(domain_data.get('user_exploration_patterns', []))}
• Средняя глубина исследования: высокая

**📈 Эффективность областей:**
• Анализируемый период: 30 дней
• Качество завершения: высокое

⏱️ *Обработано за {result.processing_time:.2f}с*
            """
            
            await callback.message.edit_text(domain_text)
        
        else:
            await callback.answer(f"Ошибка аналитики областей: {result.message}")
    
    @dp.callback_query(F.data == "refresh_stats")
    async def refresh_stats(callback: CallbackQuery):
        """Refresh statistics (force cache miss)"""
        
        await callback.answer("🔄 Обновляю статистику...")
        
        # Re-trigger detailed stats (this will be a cache miss)
        await show_detailed_stats(callback)
    
    @dp.callback_query(F.data == "refresh_system_stats")
    async def refresh_system_stats(callback: CallbackQuery):
        """Refresh system statistics"""
        
        await callback.answer("🔄 Обновляю системную статистику...")
        await show_system_stats(callback)


def format_domain_coverage(explored_domains: list) -> str:
    """Format domain coverage for display"""
    
    if not explored_domains:
        return "• Пока нет исследованных областей"
    
    domain_names = {
        'IDENTITY': '🧠 Идентичность',
        'EMOTIONS': '❤️ Эмоции', 
        'RELATIONSHIPS': '👥 Отношения',
        'WORK': '💼 Работа',
        'HEALTH': '💪 Здоровье',
        'CREATIVITY': '🎨 Творчество',
        'FUTURE': '🔮 Будущее',
        'LIFESTYLE': '🏡 Образ жизни'
    }
    
    lines = []
    for domain_info in explored_domains[:5]:  # Top 5
        if isinstance(domain_info, dict):
            domain = domain_info.get('domain', 'UNKNOWN')
            count = domain_info.get('question_count', 0)
        else:
            domain = str(domain_info)
            count = 1
        
        name = domain_names.get(domain, domain)
        lines.append(f"• {name}: {count} ответов")
    
    if len(explored_domains) > 5:
        lines.append(f"• ... еще {len(explored_domains) - 5} областей")
    
    return '\n'.join(lines)


def format_domain_coverage_stats(coverage_data: list) -> str:
    """Format domain coverage statistics"""
    
    if not coverage_data:
        return "• Нет данных по областям"
    
    lines = []
    for domain_info in coverage_data:
        domain = domain_info.get('domain', 'UNKNOWN')
        total_answers = domain_info.get('total_answers', 0)
        unique_users = domain_info.get('unique_users', 0)
        
        lines.append(f"• {domain}: {total_answers} ответов от {unique_users} пользователей")
    
    return '\n'.join(lines)


# Configure logging
telegram_logger.info("Statistics handlers configured")