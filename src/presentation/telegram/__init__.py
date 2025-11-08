"""Telegram presentation layer."""

from aiogram import Dispatcher

def create_telegram_handlers(dp: Dispatcher, container) -> None:
    """Create Telegram bot handlers."""
    
    @dp.message()
    async def echo_handler(message):
        # Placeholder - would use use cases from container
        await message.answer("Hello! This is the new Clean Architecture version.")
    
    # Additional handlers would be implemented here
    pass