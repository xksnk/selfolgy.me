"""
Telegram Alerting System for Onboarding Pipeline

Отправляет критические алерты админу в Telegram:
- Ошибки векторизации
- Ошибки обновления DP
- Медленная обработка
- Зависшие background tasks
- Недоступность сервисов
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta, timezone
from collections import defaultdict
import os

try:
    from aiogram import Bot
    from aiogram.types import ParseMode
    AIOGRAM_AVAILABLE = True
except ImportError:
    AIOGRAM_AVAILABLE = False

logger = logging.getLogger(__name__)


class TelegramAlerter:
    """
    Система алертинга через Telegram

    Features:
    - Rate limiting (не спамит админа)
    - Alert grouping (группирует похожие алерты)
    - Severity levels (warning/error/critical)
    - Formatted messages с эмодзи
    - Configurable через .env
    """

    def __init__(self, bot_token: str, admin_chat_ids: List[int]):
        self.bot_token = bot_token
        self.admin_chat_ids = admin_chat_ids
        self.bot: Optional[Bot] = None

        # Alert throttling (не более N алертов типа X в период Y)
        self.alert_counts = defaultdict(lambda: {'count': 0, 'last_reset': datetime.now(timezone.utc)})
        self.max_alerts_per_type = int(os.getenv('ALERT_MAX_PER_TYPE', 5))
        self.alert_window_minutes = int(os.getenv('ALERT_WINDOW_MINUTES', 60))

        # Alert grouping (группируем похожие за период)
        self.pending_alerts = defaultdict(list)
        self.group_window_seconds = int(os.getenv('ALERT_GROUP_WINDOW', 60))

        # Configuration
        self.enabled = os.getenv('TELEGRAM_ALERTS_ENABLED', 'true').lower() == 'true'
        self.min_severity = os.getenv('TELEGRAM_ALERTS_MIN_SEVERITY', 'warning')  # warning, error, critical

        if not AIOGRAM_AVAILABLE:
            logger.warning("aiogram not available - Telegram alerts disabled")
            self.enabled = False

        if self.enabled and AIOGRAM_AVAILABLE:
            self.bot = Bot(token=bot_token)
            logger.info(f"Telegram alerter initialized for {len(admin_chat_ids)} admins")

    async def send_alert(self, alert_type: str, severity: str, message: str, details: Dict[str, Any]):
        """
        Отправить алерт

        Args:
            alert_type: Тип алерта (error, slow_processing, stuck_task, etc)
            severity: Уровень серьезности (warning, error, critical)
            message: Основное сообщение
            details: Детали для отображения
        """
        if not self.enabled:
            return

        # Проверяем минимальный severity
        severity_order = {'warning': 0, 'error': 1, 'critical': 2}
        if severity_order.get(severity, 0) < severity_order.get(self.min_severity, 0):
            return

        # Проверяем rate limiting
        if not self._should_send_alert(alert_type):
            logger.debug(f"Alert throttled: {alert_type}")
            return

        # Добавляем в группировку
        self.pending_alerts[alert_type].append({
            'severity': severity,
            'message': message,
            'details': details,
            'timestamp': datetime.now(timezone.utc)
        })

        # Если набралось достаточно или прошло время - отправляем
        await self._maybe_flush_alerts(alert_type)

    async def _maybe_flush_alerts(self, alert_type: str):
        """Отправить накопленные алерты если пора"""
        alerts = self.pending_alerts[alert_type]

        if not alerts:
            return

        # Отправляем если:
        # 1. Прошло достаточно времени с первого алерта
        # 2. Или накопилось много алертов
        first_alert_time = alerts[0]['timestamp']
        time_since_first = (datetime.now(timezone.utc) - first_alert_time).total_seconds()

        should_flush = (
            time_since_first >= self.group_window_seconds or
            len(alerts) >= 5  # Группируем максимум 5 алертов
        )

        if should_flush:
            await self._send_grouped_alerts(alert_type, alerts)
            self.pending_alerts[alert_type].clear()

    async def _send_grouped_alerts(self, alert_type: str, alerts: List[Dict[str, Any]]):
        """Отправить сгруппированные алерты"""
        if not alerts:
            return

        # Формируем сообщение
        message = self._format_grouped_message(alert_type, alerts)

        # Отправляем всем админам
        for admin_id in self.admin_chat_ids:
            try:
                await self.bot.send_message(
                    chat_id=admin_id,
                    text=message,
                    parse_mode=ParseMode.HTML,
                    disable_web_page_preview=True
                )
                logger.info(f"Alert sent to admin {admin_id}")
            except Exception as e:
                logger.error(f"Failed to send alert to admin {admin_id}: {e}")

    def _format_grouped_message(self, alert_type: str, alerts: List[Dict[str, Any]]) -> str:
        """Форматировать сгруппированное сообщение"""
        # Emoji mapping
        severity_emoji = {
            'warning': '⚠️',
            'error': '❌',
            'critical': '🚨'
        }

        type_emoji = {
            'error': '❌',
            'slow_processing': '🐌',
            'stuck_task': '⏰',
            'high_failure_rate': '📉',
            'service_unhealthy': '🔴',
            'stuck_processing': '⏸️'
        }

        # Определяем максимальный severity
        max_severity = 'warning'
        for alert in alerts:
            if alert['severity'] == 'critical':
                max_severity = 'critical'
                break
            elif alert['severity'] == 'error' and max_severity == 'warning':
                max_severity = 'error'

        # Заголовок
        emoji = type_emoji.get(alert_type, '⚡')
        severity_indicator = severity_emoji.get(max_severity, '')

        if len(alerts) == 1:
            lines = [
                f"{severity_indicator} <b>Selfology Alert</b> {emoji}",
                f"",
                f"<b>Type:</b> {alert_type.replace('_', ' ').title()}",
                f"<b>Severity:</b> {alerts[0]['severity'].upper()}",
                f"",
                f"<b>Message:</b>",
                f"{alerts[0]['message']}",
            ]

            # Детали
            details = alerts[0]['details']
            if details:
                lines.append("")
                lines.append("<b>Details:</b>")
                for key, value in details.items():
                    lines.append(f"• {key}: {value}")

        else:
            # Группированное сообщение
            lines = [
                f"{severity_indicator} <b>Selfology Alerts ({len(alerts)})</b> {emoji}",
                f"",
                f"<b>Type:</b> {alert_type.replace('_', ' ').title()}",
                f"<b>Max Severity:</b> {max_severity.upper()}",
                f"",
                f"<b>Recent occurrences:</b>",
            ]

            # Показываем первые 3 алерта детально
            for i, alert in enumerate(alerts[:3], 1):
                lines.append(f"")
                lines.append(f"<b>{i}.</b> {alert['message']}")

                # Краткие детали
                details = alert['details']
                important_keys = ['user_id', 'answer_id', 'analysis_id', 'minutes_stuck', 'success_rate']
                important_details = {k: v for k, v in details.items() if k in important_keys}

                if important_details:
                    details_str = ", ".join(f"{k}={v}" for k, v in important_details.items())
                    lines.append(f"  <i>{details_str}</i>")

            # Если больше 3 - показываем счетчик
            if len(alerts) > 3:
                lines.append(f"")
                lines.append(f"<i>... and {len(alerts) - 3} more similar alerts</i>")

        # Timestamp
        lines.append("")
        lines.append(f"<i>Time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}</i>")

        return "\n".join(lines)

    def _should_send_alert(self, alert_type: str) -> bool:
        """Проверка rate limiting"""
        now = datetime.now(timezone.utc)
        state = self.alert_counts[alert_type]

        # Сброс счетчика если прошло окно
        time_since_reset = (now - state['last_reset']).total_seconds() / 60
        if time_since_reset >= self.alert_window_minutes:
            state['count'] = 0
            state['last_reset'] = now

        # Проверяем лимит
        if state['count'] >= self.max_alerts_per_type:
            return False

        state['count'] += 1
        return True

    async def send_daily_summary(self, metrics_summary: Dict[str, Any]):
        """Отправить ежедневную сводку"""
        if not self.enabled:
            return

        message = self._format_daily_summary(metrics_summary)

        for admin_id in self.admin_chat_ids:
            try:
                await self.bot.send_message(
                    chat_id=admin_id,
                    text=message,
                    parse_mode=ParseMode.HTML
                )
            except Exception as e:
                logger.error(f"Failed to send daily summary to admin {admin_id}: {e}")

    def _format_daily_summary(self, metrics: Dict[str, Any]) -> str:
        """Форматировать ежедневную сводку"""
        lines = [
            "📊 <b>Selfology Daily Report</b>",
            "",
            f"<b>Period:</b> Last 24 hours",
            "",
            "<b>Performance:</b>",
        ]

        timing = metrics.get('timing', {})
        lines.append(f"• Avg AI analysis: {timing.get('avg_ai_analysis_ms', 0):.0f}ms")
        lines.append(f"• Avg total pipeline: {timing.get('avg_total_pipeline_ms', 0):.0f}ms")
        lines.append(f"• Max pipeline time: {timing.get('max_pipeline_ms', 0):.0f}ms")

        lines.append("")
        lines.append("<b>Success Rates:</b>")

        success_rates = metrics.get('success_rates', {})
        lines.append(f"• AI Analysis: {success_rates.get('ai_analysis', 0):.1f}%")
        lines.append(f"• Vectorization: {success_rates.get('vectorization', 0):.1f}%")
        lines.append(f"• DP Update: {success_rates.get('dp_update', 0):.1f}%")

        lines.append("")
        lines.append("<b>Issues:</b>")

        totals = metrics.get('totals', {})
        lines.append(f"• Total retries: {totals.get('retries', 0)}")
        lines.append(f"• Total errors: {totals.get('errors', 0)}")

        lines.append("")
        lines.append(f"<i>{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}</i>")

        return "\n".join(lines)

    async def send_health_alert(self, service: str, status: str, details: Dict[str, Any]):
        """Отправить алерт о проблемах со здоровьем сервиса"""
        if not self.enabled:
            return

        emoji_map = {
            'postgresql': '🐘',
            'qdrant': '🔍',
            'openai': '🤖',
            'redis': '📦'
        }

        emoji = emoji_map.get(service, '⚙️')

        message = [
            f"🔴 <b>Service Health Alert</b> {emoji}",
            "",
            f"<b>Service:</b> {service}",
            f"<b>Status:</b> {status.upper()}",
            "",
            "<b>Details:</b>"
        ]

        for key, value in details.items():
            message.append(f"• {key}: {value}")

        message.append("")
        message.append(f"<i>{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}</i>")

        text = "\n".join(message)

        for admin_id in self.admin_chat_ids:
            try:
                await self.bot.send_message(
                    chat_id=admin_id,
                    text=text,
                    parse_mode=ParseMode.HTML
                )
            except Exception as e:
                logger.error(f"Failed to send health alert to admin {admin_id}: {e}")

    async def flush_pending_alerts(self):
        """Принудительно отправить все накопленные алерты"""
        for alert_type in list(self.pending_alerts.keys()):
            alerts = self.pending_alerts[alert_type]
            if alerts:
                await self._send_grouped_alerts(alert_type, alerts)
                self.pending_alerts[alert_type].clear()

    async def close(self):
        """Закрыть соединение"""
        # Отправляем все накопленные алерты
        await self.flush_pending_alerts()

        if self.bot:
            session = await self.bot.get_session()
            if session:
                await session.close()


# Global alerter instance
_telegram_alerter: Optional[TelegramAlerter] = None


def initialize_telegram_alerter(bot_token: str, admin_chat_ids: List[int]) -> TelegramAlerter:
    """Инициализация глобального alerter"""
    global _telegram_alerter
    _telegram_alerter = TelegramAlerter(bot_token, admin_chat_ids)
    return _telegram_alerter


def get_telegram_alerter() -> Optional[TelegramAlerter]:
    """Получить глобальный экземпляр alerter"""
    return _telegram_alerter
