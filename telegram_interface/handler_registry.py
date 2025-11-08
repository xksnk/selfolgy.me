"""
Handler Registry - регистрация всех обработчиков бота

Отвечает за:
- Регистрацию handlers с dependency injection
- Связывание handlers с командами и состояниями
- Middleware регистрацию
"""

import logging
from functools import partial
from aiogram import Dispatcher, F
from aiogram.filters import CommandStart, Command

from .handlers import (
    CommandHandlers,
    OnboardingHandlers,
    ChatHandlers,
    AdminHandlers,
    CallbackHandlers
)
from .middleware import StateLoggerMiddleware
from .states import OnboardingStates, ChatStates
from .utilities import show_main_menu, show_main_menu_callback

logger = logging.getLogger(__name__)


class HandlerRegistry:
    """
    Регистратор всех обработчиков бота
    
    Использует dependency injection для передачи зависимостей в handlers.
    """

    def __init__(
        self,
        dp: Dispatcher,
        user_dao,
        onboarding_dao,
        orchestrator,
        chat_coach,
        messages
    ):
        """
        Args:
            dp: Aiogram Dispatcher
            user_dao: User DAO для работы с пользователями
            onboarding_dao: Onboarding DAO
            orchestrator: OnboardingOrchestrator
            chat_coach: ChatCoachService
            messages: MessageService
        """
        self.dp = dp
        self.user_dao = user_dao
        self.onboarding_dao = onboarding_dao
        self.orchestrator = orchestrator
        self.chat_coach = chat_coach
        self.messages = messages

    def register_all(self):
        """Регистрация всех handlers и middleware"""
        logger.info("🔧 Registering all handlers...")

        # 1. Register middleware
        self._register_middleware()

        # 2. Register command handlers
        self._register_command_handlers()

        # 3. Register onboarding handlers
        self._register_onboarding_handlers()

        # 4. Register chat handlers
        self._register_chat_handlers()

        # 5. Register admin handlers
        self._register_admin_handlers()

        # 6. Register callback handlers
        self._register_callback_handlers()

        # 7. Register fallback handler
        self._register_fallback_handlers()

        logger.info("✅ All handlers registered successfully")

    def _register_middleware(self):
        """Регистрация middleware"""
        # FSM state transition logging
        self.dp.message.middleware(StateLoggerMiddleware())
        self.dp.callback_query.middleware(StateLoggerMiddleware())
        logger.info("🔄 Middleware registered: StateLoggerMiddleware")

    def _register_command_handlers(self):
        """Регистрация базовых команд"""
        # Helper для show_main_menu
        show_menu_func = partial(show_main_menu, messages=self.messages)

        # /start
        self.dp.message.register(
            partial(
                CommandHandlers.cmd_start,
                user_dao=self.user_dao,
                messages=self.messages,
                onboarding_states=OnboardingStates,
                show_main_menu_func=show_menu_func
            ),
            CommandStart()
        )

        # /help
        self.dp.message.register(
            partial(CommandHandlers.cmd_help, messages=self.messages),
            Command("help")
        )

        # /profile
        self.dp.message.register(
            partial(
                CommandHandlers.cmd_profile,
                user_dao=self.user_dao,
                messages=self.messages
            ),
            Command("profile")
        )

        logger.info("📝 Command handlers registered: /start, /help, /profile")

    def _register_onboarding_handlers(self):
        """Регистрация onboarding handlers"""
        # /onboarding
        self.dp.message.register(
            partial(
                OnboardingHandlers.cmd_onboarding,
                orchestrator=self.orchestrator,
                messages=self.messages,
                onboarding_states=OnboardingStates,
                chat_states=ChatStates
            ),
            Command("onboarding")
        )

        # Handle onboarding answer
        self.dp.message.register(
            partial(
                OnboardingHandlers.handle_onboarding_answer,
                orchestrator=self.orchestrator,
                messages=self.messages,
                onboarding_states=OnboardingStates
            ),
            OnboardingStates.waiting_for_answer
        )

        # Callback: skip question
        self.dp.callback_query.register(
            partial(
                OnboardingHandlers.callback_skip_question,
                orchestrator=self.orchestrator,
                messages=self.messages,
                onboarding_states=OnboardingStates
            ),
            F.data == "skip_question"
        )

        # Callback: end session
        self.dp.callback_query.register(
            partial(
                OnboardingHandlers.callback_end_session,
                orchestrator=self.orchestrator,
                onboarding_states=OnboardingStates
            ),
            F.data == "end_session"
        )

        # Callback: flag question (admin only)
        self.dp.callback_query.register(
            partial(
                OnboardingHandlers.callback_flag_question,
                orchestrator=self.orchestrator,
                skip_question_handler=OnboardingHandlers.callback_skip_question
            ),
            F.data == "flag_question"
        )

        logger.info("🧠 Onboarding handlers registered")

    def _register_chat_handlers(self):
        """Регистрация chat handlers"""
        # /chat
        self.dp.message.register(
            partial(
                ChatHandlers.cmd_chat,
                chat_coach=self.chat_coach,
                messages=self.messages,
                onboarding_states=OnboardingStates,
                chat_states=ChatStates
            ),
            Command("chat")
        )

        # Callback: start chat
        self.dp.callback_query.register(
            partial(
                ChatHandlers.callback_start_chat,
                chat_coach=self.chat_coach,
                chat_states=ChatStates
            ),
            F.data == "start_chat"
        )

        # Handle chat message
        self.dp.message.register(
            partial(
                ChatHandlers.handle_chat_message,
                chat_coach=self.chat_coach
            ),
            ChatStates.active
        )

        logger.info("💬 Chat handlers registered")

    def _register_admin_handlers(self):
        """Регистрация admin handlers"""
        # Create setter for message service
        def set_messages(new_messages):
            self.messages = new_messages

        # /debug_on
        self.dp.message.register(
            partial(
                AdminHandlers.cmd_debug_on,
                messages_service_setter=set_messages
            ),
            Command("debug_on")
        )

        # /debug_off
        self.dp.message.register(
            partial(
                AdminHandlers.cmd_debug_off,
                messages_service_setter=set_messages
            ),
            Command("debug_off")
        )

        # /debug_status
        self.dp.message.register(
            partial(
                AdminHandlers.cmd_debug_status,
                messages=self.messages,
                orchestrator=self.orchestrator
            ),
            Command("debug_status")
        )

        # /reload_templates
        self.dp.message.register(
            partial(
                AdminHandlers.cmd_reload_templates,
                messages=self.messages
            ),
            Command("reload_templates")
        )

        # /onboarding_profile
        self.dp.message.register(
            AdminHandlers.cmd_onboarding_profile,
            Command("onboarding_profile")
        )

        logger.info("🔧 Admin handlers registered")

    def _register_callback_handlers(self):
        """Регистрация callback handlers"""
        # Helper для show_main_menu
        show_menu_callback_func = partial(show_main_menu_callback, messages=self.messages)

        # GDPR callbacks
        self.dp.callback_query.register(
            CallbackHandlers.callback_gdpr_details,
            F.data == "gdpr_details"
        )

        self.dp.callback_query.register(
            partial(
                CallbackHandlers.callback_gdpr_accept,
                user_dao=self.user_dao,
                show_main_menu_func=show_menu_callback_func
            ),
            F.data == "gdpr_accept"
        )

        self.dp.callback_query.register(
            CallbackHandlers.callback_gdpr_decline,
            F.data == "gdpr_decline"
        )

        # Navigation callbacks
        self.dp.callback_query.register(
            partial(
                CallbackHandlers.callback_main_menu,
                show_main_menu_func=show_menu_callback_func
            ),
            F.data == "main_menu"
        )

        self.dp.callback_query.register(
            partial(CallbackHandlers.callback_help, messages=self.messages),
            F.data == "help"
        )

        self.dp.callback_query.register(
            partial(
                CallbackHandlers.callback_profile,
                user_dao=self.user_dao,
                messages=self.messages
            ),
            F.data == "profile"
        )

        # Coming soon features
        for feature in ['assessments', 'profile', 'goals', 'diary', 'settings']:
            self.dp.callback_query.register(
                CallbackHandlers.callback_coming_soon,
                F.data == feature
            )

        # Onboarding continuation
        self.dp.callback_query.register(
            partial(
                CallbackHandlers.callback_continue_onboarding,
                orchestrator=self.orchestrator,
                messages=self.messages,
                onboarding_states=OnboardingStates
            ),
            F.data == "continue_onboarding"
        )

        self.dp.callback_query.register(
            partial(
                CallbackHandlers.callback_end_onboarding,
                onboarding_dao=self.onboarding_dao
            ),
            F.data == "end_onboarding"
        )

        # Process orphaned answers
        self.dp.callback_query.register(
            CallbackHandlers.callback_process_orphaned,
            F.data.startswith("process_orphaned:")
        )

        logger.info("🔘 Callback handlers registered")

    def _register_fallback_handlers(self):
        """Регистрация fallback handlers для неизвестных команд"""
        async def handle_unknown(message, state):
            """Handle unknown messages"""
            await message.answer(
                "🤔 Я не понял эту команду. Используйте /help для списка доступных команд."
            )

        self.dp.message.register(handle_unknown, F.text)
        logger.info("❓ Fallback handler registered")
