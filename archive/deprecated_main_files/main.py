import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from aiogram import Bot, Dispatcher
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web

from selfology_bot.core.config import settings
from selfology_bot.core.database import init_db
from selfology_bot.bot.handlers import start, assessment
from selfology_bot.ai.clients import ai_client_manager


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_db()
    logger.info("Database initialized")
    
    # Initialize bot
    bot = Bot(token=settings.telegram_bot_token)
    dp = Dispatcher()
    
    # Register handlers
    dp.include_router(start.router)
    # dp.include_router(chat.router)
    # dp.include_router(assessment.router)
    
    # Set up webhook or polling
    if settings.telegram_webhook_url:
        # Webhook mode for production
        await bot.set_webhook(
            url=f"{settings.telegram_webhook_url}/webhook",
            allowed_updates=dp.resolve_used_update_types()
        )
        logger.info(f"Webhook set to {settings.telegram_webhook_url}/webhook")
        
        # Create webhook handler
        handler = SimpleRequestHandler(dispatcher=dp, bot=bot)
        handler.register(app, path="/webhook")
    else:
        # Polling mode for development
        async def start_polling():
            await dp.start_polling(bot)
        
        asyncio.create_task(start_polling())
        logger.info("Bot started in polling mode")
    
    app.state.bot = bot
    app.state.dp = dp
    
    # Health check AI services
    ai_status = await ai_client_manager.health_check()
    logger.info(f"AI services status: {ai_status}")
    
    yield
    
    # Shutdown
    await bot.session.close()
    logger.info("Bot session closed")


# Create FastAPI app
app = FastAPI(
    title="Selfology Bot API",
    description="AI Psychology Coach - FastAPI + Telegram Bot",
    version="0.1.0",
    lifespan=lifespan
)


@app.get("/")
async def root():
    return {
        "message": "Selfology Bot API is running",
        "version": "0.1.0",
        "bot_username": settings.telegram_bot_token.split(":")[0] if settings.telegram_bot_token else None
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        ai_status = await ai_client_manager.health_check()
        return {
            "status": "healthy",
            "ai_services": ai_status,
            "database": "connected"  # TODO: Add actual DB health check
        }
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


@app.post("/n8n/webhook")
async def n8n_webhook(data: dict):
    """Endpoint for n8n webhook integration"""
    logger.info(f"Received n8n webhook: {data}")
    
    # Process n8n webhook data
    # This will be used for complex workflows integration
    
    return {"status": "received", "data": data}


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="info" if settings.debug else "warning"
    )