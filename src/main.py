"""Main application entry point with Clean Architecture."""

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from aiogram import Bot, Dispatcher
from aiogram.webhook.aiohttp_server import SimpleRequestHandler

from .config import get_settings, get_container
from .monitoring import setup_logging, HealthCheckService
from .presentation.api import create_api_routes
from .presentation.telegram import create_telegram_handlers

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    
    # Startup
    settings = get_settings()
    setup_logging()
    
    logger.info("🚀 Starting Selfology Bot...")
    
    try:
        # Initialize dependency container
        container = get_container()
        await container.initialize()
        app.state.container = container
        
        # Initialize Telegram bot if configured
        if settings.telegram_bot_token:
            bot = Bot(token=settings.telegram_bot_token)
            dp = Dispatcher()
            
            # Register handlers
            create_telegram_handlers(dp, container)
            
            # Setup webhook or polling
            if settings.telegram_webhook_url:
                await bot.set_webhook(
                    url=f"{settings.telegram_webhook_url}/webhook",
                    allowed_updates=dp.resolve_used_update_types()
                )
                
                handler = SimpleRequestHandler(dispatcher=dp, bot=bot)
                handler.register(app, path="/webhook")
                logger.info("📡 Telegram webhook configured")
            else:
                async def start_polling():
                    await dp.start_polling(bot)
                
                asyncio.create_task(start_polling())
                logger.info("🔄 Telegram polling started")
            
            app.state.bot = bot
            app.state.dp = dp
        
        # Initialize health check service
        health_service = HealthCheckService(container)
        app.state.health_service = health_service
        
        # Run initial health check
        health = await health_service.get_health_status()
        logger.info(f"📊 System health: {health['status']}")
        
        logger.info("✅ Selfology Bot started successfully!")
        
        yield
        
    except Exception as e:
        logger.error(f"❌ Startup failed: {e}")
        raise
    
    # Shutdown
    logger.info("🛑 Shutting down Selfology Bot...")
    
    try:
        if hasattr(app.state, 'bot') and app.state.bot:
            await app.state.bot.session.close()
        
        if hasattr(app.state, 'container'):
            await app.state.container.close()
        
        logger.info("✅ Shutdown completed")
        
    except Exception as e:
        logger.error(f"❌ Shutdown error: {e}")


def create_app() -> FastAPI:
    """Create FastAPI application."""
    
    settings = get_settings()
    
    app = FastAPI(
        title="Selfology Bot API",
        description="AI Psychology Coach - Clean Architecture Implementation",
        version="2.0.0",
        debug=settings.debug,
        lifespan=lifespan
    )
    
    # Add API routes
    create_api_routes(app)
    
    return app


# Create application instance
app = create_app()


if __name__ == "__main__":
    import uvicorn
    
    settings = get_settings()
    
    uvicorn.run(
        "src.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )