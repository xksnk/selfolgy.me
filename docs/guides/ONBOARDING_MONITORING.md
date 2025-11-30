# Onboarding Pipeline Monitoring System

Comprehensive monitoring system для отслеживания всего пути пользователя от Telegram ответа до обновления Digital Personality.

## Содержание

- [Архитектура](#архитектура)
- [Что отслеживается](#что-отслеживается)
- [Установка и настройка](#установка-и-настройка)
- [Использование](#использование)
- [Алерты и уведомления](#алерты-и-уведомления)
- [Автоматические ретраи](#автоматические-ретраи)
- [API и интеграции](#api-и-интеграции)

## Архитектура

Система мониторинга состоит из трех основных компонентов:

```
┌─────────────────────────────────────────────────────────────┐
│               OnboardingMonitoringSystem                     │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────────┐  ┌──────────────────┐  ┌────────────┐│
│  │ Pipeline Monitor │  │ Telegram Alerter │  │ Auto-Retry ││
│  ├──────────────────┤  ├──────────────────┤  ├────────────┤│
│  │ • Real-time      │  │ • Smart grouping │  │ • Exp back ││
│  │   tracking       │  │ • Rate limiting  │  │ • Recover  ││
│  │ • Metrics        │  │ • Severity       │  │   errors   ││
│  │ • Health checks  │  │   levels         │  │ • Stats    ││
│  └──────────────────┘  └──────────────────┘  └────────────┘│
└─────────────────────────────────────────────────────────────┘
```

### Pipeline Monitor

Отслеживает каждый этап обработки ответа:

1. **Telegram → SQL**: Сохранение ответа в БД
2. **SQL → AI Analysis**: Глубокий анализ через AI
3. **AI → Vectorization**: Создание embeddings в Qdrant
4. **Vectorization → DP Update**: Обновление Digital Personality

### Telegram Alerter

Отправляет критические уведомления админу в Telegram:

- **Rate Limiting**: Не спамит, группирует похожие алерты
- **Severity Levels**: warning, error, critical
- **Smart Grouping**: Объединяет похожие алерты за период
- **Formatted Messages**: Красивые сообщения с эмодзи

### Auto-Retry Manager

Автоматически перезапускает failed операции:

- **Exponential Backoff**: 1min → 5min → 15min → 30min
- **Smart Recovery**: Только для исправимых ошибок
- **Max Retries**: Configurable limit (default: 3)
- **Success Tracking**: Метрики успешности ретраев

## Что отслеживается

### Метрики производительности

```python
{
    'timing': {
        'sql_save_ms': 50,           # Время сохранения в БД
        'ai_analysis_ms': 3500,      # Время AI анализа
        'vectorization_ms': 1200,    # Время создания векторов
        'dp_update_ms': 800,         # Время обновления DP
        'total_pipeline_ms': 5550    # Полное время обработки
    },
    'success_rates': {
        'ai_analysis': '100.0%',
        'vectorization': '98.5%',
        'dp_update': '99.2%'
    },
    'queue_depth': {
        'pending_analyses': 2,
        'pending_vectorizations': 1,
        'pending_dp_updates': 0
    },
    'errors': {
        'ai_errors': 0,
        'vectorization_errors': 3,
        'dp_update_errors': 1
    }
}
```

### Типы алертов

1. **error** - Ошибка обработки
2. **slow_processing** - Медленная обработка (>15 сек)
3. **stuck_task** - Зависший background task (>5 мин)
4. **high_failure_rate** - Высокий процент ошибок (>20%)
5. **service_unhealthy** - Проблемы с сервисами (Qdrant, PostgreSQL, OpenAI)
6. **stuck_processing** - Pending статус долго висит (>5 мин)

### Health Checks

Проверяет доступность всех сервисов:

- **PostgreSQL**: Connection, response time, active connections
- **Qdrant**: API availability, collections status
- **OpenAI API**: API availability, rate limits
- **Redis**: Connection (если используется)

## Установка и настройка

### 1. Конфигурация в .env

```bash
# Telegram Alerts
TELEGRAM_ALERTS_ENABLED=true
TELEGRAM_ALERTS_MIN_SEVERITY=warning  # warning, error, critical
MONITORING_ADMIN_IDS=98005572         # Comma-separated

# Alert Rate Limiting
ALERT_MAX_PER_TYPE=5           # Max alerts of same type per window
ALERT_WINDOW_MINUTES=60        # Time window for rate limiting
ALERT_GROUP_WINDOW=60          # Seconds to group similar alerts

# Performance Thresholds
ONBOARDING_SLOW_THRESHOLD_MS=15000    # 15 seconds
ONBOARDING_STUCK_THRESHOLD_SEC=300    # 5 minutes
ONBOARDING_FAILURE_THRESHOLD=0.2      # 20%

# Auto-Retry Configuration
AUTO_RETRY_ENABLED=true
AUTO_RETRY_MAX_ATTEMPTS=3
```

### 2. Интеграция в код

#### В selfology_controller.py или main.py:

```python
from selfology_bot.monitoring import initialize_onboarding_monitoring
import os

# Инициализация при старте бота
async def startup():
    # ... existing startup code ...

    # Initialize monitoring
    db_config = {
        "host": os.getenv("DB_HOST"),
        "port": int(os.getenv("DB_PORT", 5432)),
        "user": os.getenv("DB_USER"),
        "password": os.getenv("DB_PASSWORD"),
        "database": os.getenv("DB_NAME")
    }

    monitoring = await initialize_onboarding_monitoring(
        db_config=db_config,
        bot_token=os.getenv("BOT_TOKEN"),
        admin_chat_ids=[int(id) for id in os.getenv("MONITORING_ADMIN_IDS").split(",")],
        enable_alerting=os.getenv("TELEGRAM_ALERTS_ENABLED", "true").lower() == "true",
        enable_auto_retry=os.getenv("AUTO_RETRY_ENABLED", "true").lower() == "true"
    )

    # Start monitoring in background
    asyncio.create_task(monitoring.start())

    logger.info("Onboarding monitoring started")

# Shutdown
async def shutdown():
    from selfology_bot.monitoring import get_monitoring_system

    monitoring = get_monitoring_system()
    if monitoring:
        await monitoring.stop()
```

## Использование

### CLI инструмент

```bash
# Текущий статус pipeline
python scripts/onboarding_monitoring_cli.py status

# Текущие метрики производительности
python scripts/onboarding_monitoring_cli.py metrics

# Ошибки за последние 6 часов
python scripts/onboarding_monitoring_cli.py errors --hours 6

# Проверка здоровья сервисов
python scripts/onboarding_monitoring_cli.py health

# Статистика ретраев
python scripts/onboarding_monitoring_cli.py retry-stats

# Сводка за 24 часа
python scripts/onboarding_monitoring_cli.py summary --hours 24

# Запустить мониторинг (standalone)
python scripts/onboarding_monitoring_cli.py start

# JSON вывод (для интеграций)
python scripts/onboarding_monitoring_cli.py json
```

### Программный доступ

```python
from selfology_bot.monitoring import get_monitoring_system

# Получить систему мониторинга
monitoring = get_monitoring_system()

# Получить текущие метрики
metrics = await monitoring.get_current_metrics()

# Получить статус pipeline для конкретного пользователя
status = await monitoring.get_pipeline_status(user_id=98005572)

# Получить недавние ошибки
errors = await monitoring.get_recent_errors(hours=6)

# Проверить здоровье сервисов
health = await monitoring.check_services_health()

# Получить сводку метрик
summary = await monitoring.get_metrics_summary(hours=24)

# Получить статистику ретраев
retry_stats = await monitoring.get_retry_stats()
```

## Алерты и уведомления

### Пример Telegram алерта

```
🚨 Selfology Alert 🐌

Type: Slow Processing
Severity: WARNING

Message:
Slow background processing: 18500ms

Details:
• analysis_id: 123
• answer_id: 456
• user_id: 98005572
• ai_time_ms: 3200
• background_time_ms: 18500

Time: 2025-10-03 15:30:42 UTC
```

### Группированный алерт

```
🚨 Selfology Alerts (5) ❌

Type: Vectorization Error
Max Severity: ERROR

Recent occurrences:

1. Vectorization failed: Connection timeout
   user_id=98005572, answer_id=123

2. Vectorization failed: Connection timeout
   user_id=98005573, answer_id=124

3. Vectorization failed: Connection timeout
   user_id=98005574, answer_id=125

... and 2 more similar alerts

Time: 2025-10-03 15:30:42 UTC
```

### Настройка минимального severity

Чтобы получать только критичные алерты:

```bash
TELEGRAM_ALERTS_MIN_SEVERITY=critical
```

Уровни severity:
- **warning**: Медленная обработка, degraded сервисы
- **error**: Ошибки векторизации, DP updates
- **critical**: Полная недоступность сервисов, зависшие задачи

## Автоматические ретраи

### Логика работы

1. **Обнаружение failed операций** каждую минуту
2. **Exponential backoff**: Задержка между попытками увеличивается
   - 1 попытка: через 1 минуту
   - 2 попытка: через 5 минут
   - 3 попытка: через 15 минут
   - 4 попытка: через 30 минут

3. **Smart recovery**: Анализ ошибки
   - **Recoverable**: Network timeouts, service unavailable, rate limits
   - **Non-recoverable**: Invalid data, authorization errors

4. **Max retries**: После 3 неудачных попыток - прекращаем ретраить

### Мониторинг ретраев

```python
# Получить статистику
retry_stats = await monitoring.get_retry_stats()

# Результат:
{
    'total_retries': 47,
    'successful_retries': 42,
    'failed_retries': 5,
    'success_rate': 89.4
}
```

### Ручной ретрай

Для ручного запуска ретрая используйте существующие скрипты:

```bash
# Reprocess single answer
python scripts/reprocess_single_answer.py 123

# Reprocess missing vectors
python reprocess_missing_vectors.py
```

## API и интеграции

### Webhook интеграция

Можно настроить webhook для получения алертов:

```python
from selfology_bot.monitoring import get_onboarding_monitor

monitor = get_onboarding_monitor()

async def webhook_callback(alert):
    # Отправить в ваш webhook
    async with httpx.AsyncClient() as client:
        await client.post(
            "https://your-webhook.com/alerts",
            json=alert.to_dict()
        )

monitor.register_alert_callback(webhook_callback)
```

### Prometheus метрики

Можно экспортировать метрики в Prometheus format:

```python
from selfology_bot.monitoring import get_monitoring_system

monitoring = get_monitoring_system()
metrics = await monitoring.get_current_metrics()

# Convert to Prometheus format
prometheus_metrics = f"""
# HELP onboarding_ai_analysis_ms Average AI analysis time
# TYPE onboarding_ai_analysis_ms gauge
onboarding_ai_analysis_ms {metrics['timing']['ai_analysis_ms']}

# HELP onboarding_vectorization_success_rate Vectorization success rate
# TYPE onboarding_vectorization_success_rate gauge
onboarding_vectorization_success_rate {float(metrics['success_rates']['vectorization'].rstrip('%'))/100}
"""
```

### Grafana Dashboard

Можно создать Grafana dashboard используя PostgreSQL datasource:

```sql
-- Метрики за последний час
SELECT
    DATE_TRUNC('minute', aa.processed_at) as time,
    AVG(aa.processing_time_ms) as ai_time,
    AVG(aa.background_task_duration_ms) as total_time,
    COUNT(*) FILTER (WHERE aa.vectorization_status = 'success') as vec_success,
    COUNT(*) FILTER (WHERE aa.vectorization_status = 'failed') as vec_failed
FROM selfology.answer_analysis aa
WHERE aa.processed_at > NOW() - INTERVAL '1 hour'
GROUP BY DATE_TRUNC('minute', aa.processed_at)
ORDER BY time
```

## Troubleshooting

### Алерты не приходят в Telegram

1. Проверьте конфигурацию:
```bash
echo $TELEGRAM_ALERTS_ENABLED
echo $MONITORING_ADMIN_IDS
```

2. Проверьте что бот может отправлять сообщения админу:
```python
from aiogram import Bot

bot = Bot(token=os.getenv("BOT_TOKEN"))
await bot.send_message(98005572, "Test alert")
```

3. Проверьте severity level:
```bash
# Если установлен critical - warning и error алерты не придут
TELEGRAM_ALERTS_MIN_SEVERITY=warning
```

### Ретраи не работают

1. Проверьте что AUTO_RETRY_ENABLED=true
2. Проверьте что не превышен MAX_RETRIES:
```sql
SELECT * FROM selfology.answer_analysis
WHERE retry_count >= 3 AND vectorization_status = 'failed';
```

3. Проверьте логи на наличие ошибок:
```bash
grep "AutoRetryManager" logs/selfology.log
```

### Медленная обработка

Если видите алерты о медленной обработке:

1. Проверьте загрузку AI API:
```bash
python scripts/onboarding_monitoring_cli.py health
```

2. Проверьте очереди:
```bash
python scripts/onboarding_monitoring_cli.py metrics
```

3. Проверьте системные ресурсы:
```bash
htop  # CPU и память
```

## Дополнительная информация

- **Existing monitoring**: Интегрируется с существующей системой в `core/monitoring_orchestrator.py`
- **Logging**: Использует существующую систему логирования `selfology_bot/core/logging.py`
- **Database schema**: Использует существующие таблицы с полями для статусов обработки
- **Минимальный overhead**: Все проверки асинхронные, не блокируют основной поток

## Best Practices

1. **Мониторинг в production**: Обязательно включайте все компоненты
2. **Severity levels**: Используйте `warning` для development, `error` для production
3. **Daily summaries**: Настройте отправку ежедневной сводки:
```python
# В cron или scheduler
monitoring = get_monitoring_system()
await monitoring.send_daily_summary()
```

4. **Regular checks**: Периодически проверяйте здоровье сервисов:
```bash
# Добавьте в cron
*/5 * * * * python scripts/onboarding_monitoring_cli.py health
```

5. **Alert fatigue**: Настройте rate limiting чтобы не перегружать админа алертами

## Support

Для вопросов и предложений:
- GitHub Issues: [selfology/issues](https://github.com/...)
- Telegram: @admin
