"""
State Logger Middleware - логирование FSM state transitions

Middleware для отслеживания всех изменений состояний FSM.
Полезно для отладки и мониторинга пользовательских потоков.
"""

import logging
from typing import Callable, Dict, Any, Awaitable

from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

logger = logging.getLogger(__name__)


class StateLoggerMiddleware(BaseMiddleware):
    """
    Middleware для логирования FSM state transitions
    
    Логирует:
    - Текущее состояние до выполнения handler
    - Новое состояние после выполнения handler
    - Изменения состояний
    """

    async def __call__(
        self,
        handler: Callable[[Message | CallbackQuery, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:
        """
        Обработать событие с логированием state transitions
        
        Args:
            handler: Handler функция
            event: Message или CallbackQuery
            data: Дополнительные данные (включая FSMContext)
        
        Returns:
            Результат выполнения handler
        """
        # Получаем user_id из event
        user_id = None
        if hasattr(event, 'from_user') and event.from_user:
            user_id = event.from_user.id

        state: FSMContext = data.get("state")
        current_state = None
        
        if state:
            current_state = await state.get_state()

            # Логируем BEFORE handler
            if user_id:
                handler_name = handler.__name__ if hasattr(handler, '__name__') else 'unknown'
                logger.debug(
                    f"🔄 FSM State [BEFORE]: user={user_id}, "
                    f"state={current_state or 'None'}, "
                    f"handler={handler_name}"
                )

        # Выполняем handler
        result = await handler(event, data)

        # Логируем AFTER handler
        if state and user_id:
            new_state = await state.get_state()
            if new_state != current_state:
                logger.info(
                    f"✨ FSM State [CHANGED]: user={user_id}, "
                    f"{current_state or 'None'} → {new_state or 'None'}"
                )

        return result
