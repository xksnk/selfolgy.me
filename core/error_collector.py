"""
Централизованный сборщик ошибок и активности для Selfology

Собирает:
- logs/errors.jsonl - ошибки для исправления
- logs/activity.jsonl - активность для анализа flow

Claude читает эти файлы чтобы понять что происходит и что нужно исправить.

Usage:
    from core.error_collector import error_collector, collect_errors

    # Инициализация (один раз при старте)
    await error_collector.initialize()

    # Сбор ошибки
    await error_collector.collect(
        error=exception,
        service="VectorService",
        component="embedding",
        user_id=12345,
        context={"answer_id": 100}
    )

    # Трекинг активности
    await error_collector.track(
        event_type="user_action",
        action="command_start",
        service="Telegram",
        user_id=12345,
        details={"command": "/start"}
    )
"""

import asyncio
import logging
import traceback
import functools
import json
import os
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timezone
from contextlib import asynccontextmanager
from pathlib import Path

logger = logging.getLogger(__name__)


class ErrorCollector:
    """
    Централизованный сборщик ошибок

    Пишет все ошибки в logs/errors.jsonl для анализа Claude.
    Добавляет контекст: service, component, user_id, stack trace.
    """

    def __init__(self):
        self.initialized = False
        self.errors_file: Optional[Path] = None
        self.activity_file: Optional[Path] = None

        # Статистика ошибок по сервисам
        self.error_stats: Dict[str, Dict[str, int]] = {}

        # Статистика активности
        self.activity_stats: Dict[str, int] = {}

        # Маппинг severity по типам ошибок
        self.severity_mapping = {
            # Critical - требует немедленного внимания
            'ConnectionError': 'critical',
            'DatabaseError': 'critical',
            'AuthenticationError': 'critical',

            # Error - важно, но не критично
            'ValueError': 'error',
            'KeyError': 'error',
            'TypeError': 'error',
            'APIError': 'error',
            'TimeoutError': 'error',

            # Warning - информационно
            'Warning': 'warning',
            'DeprecationWarning': 'warning',
        }

        # Игнорируемые ошибки
        self.ignored_errors = {
            'CancelledError',  # Нормальное завершение task
            'KeyboardInterrupt',  # Ручная остановка
        }

    async def initialize(self, log_dir: str = "logs"):
        """
        Инициализация - создаём файлы для ошибок и активности

        Args:
            log_dir: Директория для логов
        """
        if self.initialized:
            return

        # Создаём директорию если нет
        log_path = Path(log_dir)
        log_path.mkdir(parents=True, exist_ok=True)

        # Файл для ошибок
        self.errors_file = log_path / "errors.jsonl"

        # Файл для активности
        self.activity_file = log_path / "activity.jsonl"

        self.initialized = True
        logger.info(f"ErrorCollector initialized - errors: {self.errors_file}, activity: {self.activity_file}")

    async def collect(
        self,
        error: Exception,
        service: str,
        component: str,
        user_id: Optional[int] = None,
        context: Optional[Dict[str, Any]] = None,
        severity: Optional[str] = None
    ):
        """
        Собрать и отправить ошибку

        Args:
            error: Исключение
            service: Название сервиса (ChatCoachService, AnswerAnalyzer, etc)
            component: Компонент внутри сервиса (ai_router, embedding, etc)
            user_id: ID пользователя (если есть)
            context: Дополнительный контекст
            severity: Переопределение severity (warning/error/critical)
        """
        error_type = type(error).__name__

        # Проверяем игнорируемые ошибки
        if error_type in self.ignored_errors:
            return

        # Определяем severity
        if severity is None:
            severity = self.severity_mapping.get(error_type, 'error')

        # Обновляем статистику
        if service not in self.error_stats:
            self.error_stats[service] = {}
        if component not in self.error_stats[service]:
            self.error_stats[service][component] = 0
        self.error_stats[service][component] += 1

        # Формируем alert_type
        alert_type = f"{service.lower()}_{component.lower()}_error"

        # Формируем сообщение
        message = f"{error_type}: {str(error)}"

        # Формируем детали
        details = {
            'service': service,
            'component': component,
            'error_type': error_type,
        }

        if user_id:
            details['user_id'] = user_id

        if context:
            details.update(context)

        # Добавляем stack trace для critical/error
        if severity in ('critical', 'error'):
            tb = traceback.format_exc()
            # Берём последние 3 строки stack trace
            tb_lines = tb.strip().split('\n')
            if len(tb_lines) > 3:
                details['traceback'] = '\n'.join(tb_lines[-3:])

        # Логируем
        log_msg = f"[{service}/{component}] {error_type}: {error}"
        if user_id:
            log_msg = f"[user={user_id}] {log_msg}"

        if severity == 'critical':
            logger.critical(log_msg)
        elif severity == 'error':
            logger.error(log_msg)
        else:
            logger.warning(log_msg)

        # Пишем в файл для Claude
        if self.errors_file and self.initialized:
            try:
                error_record = {
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'severity': severity,
                    'service': service,
                    'component': component,
                    'error_type': error_type,
                    'message': str(error),
                    'user_id': user_id,
                    'context': context,
                    'traceback': details.get('traceback')
                }

                with open(self.errors_file, 'a', encoding='utf-8') as f:
                    f.write(json.dumps(error_record, ensure_ascii=False) + '\n')

            except Exception as e:
                logger.error(f"Failed to write error to file: {e}")

    async def track(
        self,
        event_type: str,
        action: str,
        service: str,
        user_id: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
        flow_id: Optional[str] = None
    ):
        """
        Трекинг активности для Claude Code анализа

        Args:
            event_type: Тип события (user_action, bot_response, db_operation, ai_call, vector_search)
            action: Конкретное действие (command_start, save_answer, analyze_answer)
            service: Название сервиса
            user_id: ID пользователя
            details: Дополнительные детали
            flow_id: ID для связывания событий в один flow (например session_id)
        """
        if not self.initialized or not self.activity_file:
            return

        # Обновляем статистику
        if event_type not in self.activity_stats:
            self.activity_stats[event_type] = 0
        self.activity_stats[event_type] += 1

        # Формируем запись
        activity_record = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'event_type': event_type,
            'action': action,
            'service': service,
            'user_id': user_id,
            'details': details or {},
            'flow_id': flow_id
        }

        # Пишем в файл
        try:
            with open(self.activity_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(activity_record, ensure_ascii=False) + '\n')
        except Exception as e:
            logger.error(f"Failed to write activity to file: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """Получить статистику ошибок и активности"""
        total_errors = sum(
            sum(components.values())
            for components in self.error_stats.values()
        )

        total_activity = sum(self.activity_stats.values())

        return {
            'total_errors': total_errors,
            'errors_by_service': self.error_stats,
            'total_activity': total_activity,
            'activity_by_type': self.activity_stats,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }

    def reset_stats(self):
        """Сбросить статистику"""
        self.error_stats = {}
        self.activity_stats = {}

    @asynccontextmanager
    async def context(
        self,
        service: str,
        component: str,
        user_id: Optional[int] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        """
        Контекстный менеджер для сбора ошибок

        Usage:
            async with error_collector.context("ChatCoach", "router", user_id=123):
                result = await process()
        """
        try:
            yield
        except Exception as e:
            await self.collect(
                error=e,
                service=service,
                component=component,
                user_id=user_id,
                context=context
            )
            raise


# Глобальный экземпляр
error_collector = ErrorCollector()


def collect_errors(
    service: str,
    component: str,
    user_id_param: Optional[str] = 'user_id',
    reraise: bool = True
):
    """
    Декоратор для автоматического сбора ошибок

    Args:
        service: Название сервиса
        component: Компонент
        user_id_param: Имя параметра с user_id в функции (None чтобы отключить)
        reraise: Пробрасывать исключение дальше

    Usage:
        @collect_errors(service="ChatCoachService", component="ai_router")
        async def generate_response(user_id: int, message: str):
            ...
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Извлекаем user_id из аргументов
            user_id = None
            if user_id_param:
                user_id = kwargs.get(user_id_param)
                # Проверяем позиционные аргументы
                if user_id is None and args:
                    # Получаем имена параметров функции
                    import inspect
                    sig = inspect.signature(func)
                    params = list(sig.parameters.keys())
                    if user_id_param in params:
                        idx = params.index(user_id_param)
                        if idx < len(args):
                            user_id = args[idx]

            try:
                return await func(*args, **kwargs)
            except Exception as e:
                # Формируем контекст из аргументов
                context = {}
                if args:
                    context['args_count'] = len(args)
                if kwargs:
                    # Добавляем безопасные ключи
                    safe_keys = ['answer_id', 'session_id', 'message_id', 'collection_name']
                    for key in safe_keys:
                        if key in kwargs:
                            context[key] = kwargs[key]

                await error_collector.collect(
                    error=e,
                    service=service,
                    component=component,
                    user_id=user_id,
                    context=context if context else None
                )

                if reraise:
                    raise

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            # Для синхронных функций создаём event loop
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # Синхронный сбор - просто логируем
                logger.error(f"[{service}/{component}] {type(e).__name__}: {e}")
                if reraise:
                    raise

        # Выбираем wrapper в зависимости от типа функции
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


async def initialize_error_collector(log_dir: str = "logs"):
    """
    Инициализация глобального error collector

    Вызывать один раз при старте приложения.
    Ошибки пишутся в {log_dir}/errors.jsonl
    """
    await error_collector.initialize(log_dir)
    return error_collector


def get_error_collector() -> ErrorCollector:
    """Получить глобальный экземпляр"""
    return error_collector
