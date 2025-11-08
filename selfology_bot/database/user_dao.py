"""
User DAO - Операции с пользователями в схеме selfology

Работает ТОЛЬКО с:
- selfology.users - основная таблица пользователей
- GDPR согласие и базовые данные
- < 100ms операции для быстрого отклика
"""

import logging
from datetime import datetime
from typing import Dict, Optional, Any
import asyncpg

from .service import DatabaseService

logger = logging.getLogger(__name__)

class UserDAO:
    """Data Access Object для работы с пользователями"""
    
    def __init__(self, db_service: DatabaseService):
        self.db = db_service
    
    async def get_user_by_telegram_id(self, telegram_id: str) -> Optional[Dict[str, Any]]:
        """Быстрое получение пользователя по Telegram ID (< 100ms)"""
        
        query = """
        SELECT 
            id,
            user_id,
            telegram_id,
            telegram_username,
            name,
            tier,
            onboarding_completed,
            created_at,
            last_active,
            consent,
            preferred_name,
            consent_date
        FROM users 
        WHERE telegram_id = $1
        """
        
        try:
            row = await self.db.fetch_one(query, int(telegram_id))
            
            if row:
                # Конвертируем asyncpg.Record в dict
                user_data = dict(row)
                logger.debug(f"👤 User found: {telegram_id}")
                return user_data
            else:
                logger.debug(f"👤 User not found: {telegram_id}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error getting user {telegram_id}: {e}")
            return None
    
    async def create_user(self, telegram_data: Dict[str, Any]) -> Dict[str, Any]:
        """Создание нового пользователя"""
        
        telegram_id = int(telegram_data['id'])
        username = telegram_data.get('username')
        first_name = telegram_data.get('first_name', '')
        last_name = telegram_data.get('last_name', '')
        name = f"{first_name} {last_name}".strip() or username or "User"
        
        # Генерируем user_id (для совместимости с существующей схемой)
        user_id = f"tg_{telegram_id}"
        
        query = """
        INSERT INTO users (
            user_id,
            telegram_id,
            telegram_username,
            name,
            preferred_name,
            tier,
            onboarding_completed,
            consent,
            created_at,
            last_active
        ) VALUES (
            $1, $2, $3, $4, $5, $6, $7, $8, $9, $10
        )
        RETURNING *
        """
        
        now = datetime.now()  # Без timezone для совместимости с таблицей
        
        try:
            row = await self.db.fetch_one(
                query,
                user_id,
                telegram_id,
                username,
                name,
                first_name,  # preferred_name
                'free',      # tier
                False,       # onboarding_completed
                False,       # consent
                now,         # created_at
                now          # last_active
            )
            
            user_data = dict(row) if row else None
            logger.info(f"✅ User created: {telegram_id}")
            return user_data
            
        except Exception as e:
            logger.error(f"❌ Error creating user {telegram_id}: {e}")
            raise
    
    async def get_or_create_user(self, telegram_data: Dict[str, Any]) -> Dict[str, Any]:
        """Получить существующего или создать нового пользователя"""
        
        telegram_id = str(telegram_data['id'])
        
        # Сначала пытаемся найти существующего
        user = await self.get_user_by_telegram_id(telegram_id)
        
        if user:
            # Обновляем last_active
            await self.update_last_active(telegram_id)
            return user
        else:
            # Создаем нового пользователя
            return await self.create_user(telegram_data)
    
    async def update_gdpr_consent(self, telegram_id: str, consent: bool) -> bool:
        """Обновление GDPR согласия"""
        
        query = """
        UPDATE users 
        SET 
            consent = $2,
            consent_date = $3,
            last_active = $3
        WHERE telegram_id = $1
        RETURNING consent
        """
        
        now = datetime.now()  # Без timezone для совместимости с таблицей
        
        try:
            result = await self.db.execute_query(
                query,
                int(telegram_id),
                consent,
                now
            )
            
            logger.info(f"✅ GDPR consent updated for {telegram_id}: {consent}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error updating GDPR consent for {telegram_id}: {e}")
            return False
    
    async def update_onboarding_status(self, telegram_id: str, completed: bool) -> bool:
        """Обновление статуса онбординга"""
        
        query = """
        UPDATE users 
        SET 
            onboarding_completed = $2,
            last_active = $3
        WHERE telegram_id = $1
        """
        
        now = datetime.now()  # Без timezone для совместимости с таблицей
        
        try:
            await self.db.execute(
                query,
                int(telegram_id),
                completed,
                now
            )
            
            logger.info(f"✅ Onboarding status updated for {telegram_id}: {completed}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error updating onboarding status for {telegram_id}: {e}")
            return False
    
    async def update_last_active(self, telegram_id: str):
        """Обновление времени последней активности"""
        
        query = "UPDATE users SET last_active = $2 WHERE telegram_id = $1"
        
        try:
            await self.db.execute(
                query,
                int(telegram_id),
                datetime.now()
            )
            
        except Exception as e:
            logger.error(f"❌ Error updating last_active for {telegram_id}: {e}")
    
    async def get_user_stats(self, telegram_id: str) -> Dict[str, Any]:
        """Получение статистики пользователя для профиля"""
        
        query = """
        SELECT 
            created_at,
            last_active,
            onboarding_completed,
            tier,
            consent_date
        FROM users 
        WHERE telegram_id = $1
        """
        
        try:
            row = await self.db.fetch_one(query, int(telegram_id))
            
            if row:
                data = dict(row)
                
                # Вычисляем дополнительную статистику
                if data['created_at']:
                    days_with_us = (datetime.now() - data['created_at']).days
                    data['days_with_us'] = days_with_us
                
                return data
            
            return {}
            
        except Exception as e:
            logger.error(f"❌ Error getting user stats {telegram_id}: {e}")
            return {}
    
    async def get_user_profile_data(self, telegram_id: str) -> Optional[Dict[str, Any]]:
        """Получить данные профиля пользователя для отображения"""
        
        query = """
        SELECT 
            id,
            user_id,
            telegram_id,
            telegram_username,
            name,
            preferred_name,
            tier,
            onboarding_completed,
            consent,
            consent_date,
            created_at,
            last_active
        FROM users 
        WHERE telegram_id = $1
        """
        
        try:
            row = await self.db.fetch_one(query, int(telegram_id))
            
            if not row:
                logger.warning(f"👤 User profile not found: {telegram_id}")
                return None
            
            data = dict(row)
            
            # Форматируем данные для красивого отображения
            formatted_data = {
                'name': data.get('name') or data.get('preferred_name') or 'Не указано',
                'telegram_id': str(data.get('telegram_id', '')),
                'username': data.get('telegram_username') or 'Не указан',
                'tier': data.get('tier', 'free'),
                'tier_display': {'free': '🆓 Базовый', 'premium': '👑 Премиум', 'professional': '💎 Профессиональный'}.get(data.get('tier'), '🆓 Базовый'),
            }
            
            # Форматируем дату согласия GDPR
            if data.get('consent_date'):
                formatted_data['consent_date'] = data['consent_date'].strftime('📅 %d.%m.%Y в %H:%M')
                formatted_data['consent_status'] = '✅ Дано'
            else:
                formatted_data['consent_date'] = '❌ Не дано'
                formatted_data['consent_status'] = '❌ Не дано'
            
            # Вычисляем дни с нами
            if data.get('created_at'):
                days_with_us = (datetime.now() - data['created_at']).days
                formatted_data['days_with_us'] = days_with_us
                formatted_data['member_since'] = data['created_at'].strftime('📅 %d.%m.%Y')
            else:
                formatted_data['days_with_us'] = 0
                formatted_data['member_since'] = 'Неизвестно'
            
            # Статус онбординга
            if data.get('onboarding_completed'):
                formatted_data['onboarding_status'] = '✅ Завершен'
            else:
                formatted_data['onboarding_status'] = '⏳ В процессе'
            
            # Последняя активность
            if data.get('last_active'):
                formatted_data['last_active'] = data['last_active'].strftime('📅 %d.%m.%Y в %H:%M')
            else:
                formatted_data['last_active'] = 'Неизвестно'
            
            logger.debug(f"📊 Profile data formatted for user {telegram_id}")
            return formatted_data
            
        except Exception as e:
            logger.error(f"❌ Error getting user profile {telegram_id}: {e}")
            return None