"""Database connection management."""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.pool import NullPool

logger = logging.getLogger(__name__)

Base = declarative_base()


class DatabaseManager:
    """Database connection manager."""
    
    def __init__(self, database_url: str, echo: bool = False):
        self.database_url = database_url
        self.echo = echo
        self.engine = None
        self.session_factory = None
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize database connection."""
        if self._initialized:
            return
        
        try:
            self.engine = create_async_engine(
                self.database_url,
                echo=self.echo,
                pool_pre_ping=True,
                pool_recycle=300,
                poolclass=NullPool if "sqlite" in self.database_url else None,
                future=True
            )
            
            self.session_factory = async_sessionmaker(
                self.engine,
                class_=AsyncSession,
                expire_on_commit=False
            )
            
            # Test connection
            async with self.engine.begin() as conn:
                await conn.execute("SELECT 1")
            
            self._initialized = True
            logger.info("Database connection initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    async def create_tables(self) -> None:
        """Create database tables."""
        if not self._initialized:
            await self.initialize()
        
        try:
            async with self.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            
            logger.info("Database tables created successfully")
            
        except Exception as e:
            logger.error(f"Failed to create database tables: {e}")
            raise
    
    async def close(self) -> None:
        """Close database connection."""
        if self.engine:
            await self.engine.dispose()
            logger.info("Database connection closed")
    
    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get database session."""
        if not self._initialized:
            await self.initialize()
        
        async with self.session_factory() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()
    
    async def health_check(self) -> bool:
        """Check database health."""
        try:
            async with self.get_session() as session:
                await session.execute("SELECT 1")
            return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False


# Global database manager instance
_db_manager: DatabaseManager = None


def initialize_database(database_url: str, echo: bool = False) -> DatabaseManager:
    """Initialize global database manager."""
    global _db_manager
    _db_manager = DatabaseManager(database_url, echo)
    return _db_manager


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Get database session dependency."""
    if not _db_manager:
        raise RuntimeError("Database not initialized")
    
    async with _db_manager.get_session() as session:
        yield session


def get_database_manager() -> DatabaseManager:
    """Get database manager instance."""
    if not _db_manager:
        raise RuntimeError("Database not initialized")
    return _db_manager