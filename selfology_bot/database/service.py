"""
Database Service - Подключение к схеме selfology

Отвечает ТОЛЬКО за:
- Connection pooling к PostgreSQL
- Подключение к правильной схеме selfology
- Базовые операции с соединением
"""

import asyncpg
import logging
from typing import Optional
from contextlib import asynccontextmanager

from core.error_collector import error_collector

logger = logging.getLogger(__name__)

class DatabaseService:
    """Сервис для работы с базой данных selfology"""
    
    def __init__(self, host: str, port: int, user: str, password: str, database: str, schema: str = 'selfology'):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database
        self.schema = schema
        self.pool: Optional[asyncpg.Pool] = None
        
        logger.info(f"DatabaseService initialized for {schema} schema")
    
    async def initialize(self, min_size: int = 5, max_size: int = 20):
        """Инициализация connection pool"""
        
        try:
            self.pool = await asyncpg.create_pool(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=self.database,
                server_settings={'search_path': self.schema},
                min_size=min_size,
                max_size=max_size,
                max_queries=50000,
                max_inactive_connection_lifetime=300,
                command_timeout=30
            )
            
            # Проверяем подключение к правильной схеме
            async with self.pool.acquire() as conn:
                schema = await conn.fetchval("SELECT current_schema()")
                logger.info(f"✅ Connected to database, current schema: {schema}")
                
                if schema != 'selfology':
                    logger.warning(f"⚠️ Expected 'selfology' schema, got '{schema}'")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize database pool: {e}")
            await error_collector.collect(
                error=e,
                service="DatabaseService",
                component="initialize",
                severity="critical"
            )
            return False
    
    @asynccontextmanager
    async def get_connection(self):
        """Получить соединение из пула"""
        
        if not self.pool:
            raise RuntimeError("Database pool not initialized")
        
        async with self.pool.acquire() as connection:
            try:
                yield connection
            except Exception as e:
                logger.error(f"Database operation error: {e}")
                await error_collector.collect(
                    error=e,
                    service="DatabaseService",
                    component="get_connection"
                )
                raise
    
    async def execute_query(self, query: str, *args):
        """Выполнить запрос"""
        
        async with self.get_connection() as conn:
            return await conn.fetchval(query, *args)
    
    async def fetch_one(self, query: str, *args):
        """Получить одну запись"""
        
        async with self.get_connection() as conn:
            return await conn.fetchrow(query, *args)
    
    async def fetch_all(self, query: str, *args):
        """Получить все записи"""
        
        async with self.get_connection() as conn:
            return await conn.fetch(query, *args)
    
    async def execute(self, query: str, *args):
        """Выполнить команду (INSERT/UPDATE/DELETE)"""
        
        async with self.get_connection() as conn:
            return await conn.execute(query, *args)
    
    async def close(self):
        """Закрытие пула соединений"""
        
        if self.pool:
            await self.pool.close()
            logger.info("Database pool closed")
    
    async def health_check(self) -> bool:
        """Проверка работоспособности БД"""
        
        try:
            async with self.get_connection() as conn:
                result = await conn.fetchval("SELECT 1")
                return result == 1
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False