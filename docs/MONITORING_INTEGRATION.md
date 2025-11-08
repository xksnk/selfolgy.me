# Integration Guide: Onboarding Monitoring System

Пошаговая инструкция по интеграции системы мониторинга в существующий код бота.

## Quick Start

```bash
# 1. Test monitoring system
python test_monitoring_system.py

# 2. Use CLI tool
python scripts/onboarding_monitoring_cli.py status
python scripts/onboarding_monitoring_cli.py metrics
python scripts/onboarding_monitoring_cli.py health

# 3. Run standalone monitoring
python scripts/onboarding_monitoring_cli.py start
```

## Integration into selfology_controller.py

### Option 1: Full Integration (Recommended)

Добавьте в `selfology_controller.py`:

```python
# === At the top with other imports ===
from selfology_bot.monitoring import (
    initialize_onboarding_monitoring,
    get_monitoring_system
)

# === In startup function ===
async def startup():
    """Startup sequence"""
    logger.info("Starting Selfology Bot...")

    # ... existing startup code ...

    # Initialize onboarding monitoring
    try:
        db_config = {
            "host": os.getenv("DB_HOST", "localhost"),
            "port": int(os.getenv("DB_PORT", 5432)),
            "user": os.getenv("DB_USER", "n8n"),
            "password": os.getenv("DB_PASSWORD"),
            "database": os.getenv("DB_NAME", "n8n")
        }

        admin_ids_str = os.getenv("MONITORING_ADMIN_IDS", os.getenv("ADMIN_USER_ID", "98005572"))
        admin_chat_ids = [int(id.strip()) for id in admin_ids_str.split(",")]

        monitoring = await initialize_onboarding_monitoring(
            db_config=db_config,
            bot_token=os.getenv("BOT_TOKEN"),
            admin_chat_ids=admin_chat_ids,
            enable_alerting=os.getenv("TELEGRAM_ALERTS_ENABLED", "true").lower() == "true",
            enable_auto_retry=os.getenv("AUTO_RETRY_ENABLED", "true").lower() == "true"
        )

        # Start monitoring in background
        asyncio.create_task(monitoring.start())

        logger.info("✓ Onboarding monitoring started")

    except Exception as e:
        logger.error(f"Failed to start monitoring: {e}")
        # Continue without monitoring (non-critical)

    # ... rest of startup ...

# === In shutdown function ===
async def shutdown():
    """Shutdown sequence"""
    logger.info("Shutting down Selfology Bot...")

    # Stop monitoring
    try:
        monitoring = get_monitoring_system()
        if monitoring:
            await monitoring.stop()
            logger.info("✓ Monitoring stopped")
    except Exception as e:
        logger.error(f"Error stopping monitoring: {e}")

    # ... rest of shutdown ...

# === Optional: Add monitoring endpoint ===
@app.get("/monitoring/metrics")
async def get_monitoring_metrics():
    """Get current monitoring metrics"""
    monitoring = get_monitoring_system()
    if not monitoring:
        return {"error": "Monitoring not initialized"}

    metrics = await monitoring.get_current_metrics()
    return metrics

@app.get("/monitoring/health")
async def get_monitoring_health():
    """Get services health status"""
    monitoring = get_monitoring_system()
    if not monitoring:
        return {"error": "Monitoring not initialized"}

    health = await monitoring.check_services_health()
    return health
```

### Option 2: Standalone Monitoring Process

Если хотите запустить мониторинг отдельным процессом:

```bash
# Start bot
./run-local.sh

# In another terminal: Start monitoring
python scripts/onboarding_monitoring_cli.py start
```

Преимущества:
- Изоляция: мониторинг не влияет на бота
- Простота: не нужно менять код бота
- Масштабируемость: можно запускать на отдельном сервере

Недостатки:
- Дополнительный процесс для управления
- Нет интеграции с lifecycle бота

## Integration into Orchestrator (Optional)

Если хотите логировать каждый этап прямо в orchestrator:

```python
# In orchestrator.py, add monitoring hooks

from selfology_bot.monitoring import get_onboarding_monitor

async def _deep_analysis_pipeline(self, user_id, question_id, answer, ...):
    """Deep analysis pipeline with monitoring"""

    # Get monitor
    monitor = get_onboarding_monitor()

    # ... existing code ...

    # After successful vectorization
    if vector_success and monitor:
        # Monitor already updates via database
        # But can add custom logging here
        pass

    # After successful DP update
    if dp_update_success and monitor:
        # Monitor already updates via database
        pass
```

**Note**: Мониторинг уже отслеживает все через БД, дополнительные хуки не обязательны.

## Verifying Integration

### 1. Check Logs

```bash
# Should see monitoring startup
grep "Onboarding monitoring" logs/selfology.log

# Should see monitoring activity
grep "OnboardingPipelineMonitor\|AutoRetryManager\|TelegramAlerter" logs/selfology.log
```

### 2. Check Telegram Alerts

Send a test message to your bot and answer a question. If there are any errors, you should receive alerts in Telegram.

### 3. Check CLI

```bash
# Should show active monitoring
python scripts/onboarding_monitoring_cli.py status

# Should show metrics
python scripts/onboarding_monitoring_cli.py metrics
```

### 4. Check Database

```sql
-- Check if statuses are being tracked
SELECT
    vectorization_status,
    dp_update_status,
    background_task_completed,
    retry_count
FROM selfology.answer_analysis
ORDER BY processed_at DESC
LIMIT 10;
```

## Configuration Tips

### Development Environment

```bash
# More verbose alerts
TELEGRAM_ALERTS_MIN_SEVERITY=warning
ALERT_MAX_PER_TYPE=10

# More aggressive thresholds
ONBOARDING_SLOW_THRESHOLD_MS=10000  # 10 seconds
ONBOARDING_STUCK_THRESHOLD_SEC=180  # 3 minutes
```

### Production Environment

```bash
# Less noise
TELEGRAM_ALERTS_MIN_SEVERITY=error
ALERT_MAX_PER_TYPE=3

# Normal thresholds
ONBOARDING_SLOW_THRESHOLD_MS=15000  # 15 seconds
ONBOARDING_STUCK_THRESHOLD_SEC=300  # 5 minutes
```

### Disable Components Selectively

```bash
# Disable Telegram alerts (keep metrics + auto-retry)
TELEGRAM_ALERTS_ENABLED=false

# Disable auto-retry (keep monitoring + alerts)
AUTO_RETRY_ENABLED=false

# Run monitoring-only (no alerts, no retry)
TELEGRAM_ALERTS_ENABLED=false
AUTO_RETRY_ENABLED=false
```

## Troubleshooting

### Monitoring not starting

1. Check imports:
```python
from selfology_bot.monitoring import initialize_onboarding_monitoring
```

2. Check environment variables:
```bash
env | grep -E "(BOT_TOKEN|DB_|MONITORING_)"
```

3. Check database connection:
```bash
python -c "import asyncpg; import asyncio; asyncio.run(asyncpg.connect(host='localhost', user='n8n', password='...', database='n8n'))"
```

### Alerts not sending

1. Check bot token:
```python
from aiogram import Bot
bot = Bot(token="YOUR_TOKEN")
await bot.get_me()  # Should return bot info
```

2. Check admin can receive messages:
```python
await bot.send_message(98005572, "Test")
```

3. Check severity level:
```bash
# If critical - only critical alerts sent
echo $TELEGRAM_ALERTS_MIN_SEVERITY
```

### Auto-retry not working

1. Check enabled:
```bash
echo $AUTO_RETRY_ENABLED
```

2. Check retry counts in DB:
```sql
SELECT retry_count, COUNT(*)
FROM selfology.answer_analysis
WHERE vectorization_status = 'failed'
GROUP BY retry_count;
```

3. Check logs:
```bash
grep "AutoRetryManager\|Retrying" logs/selfology.log
```

## Performance Impact

Система мониторинга спроектирована для минимального impact на производительность:

- **Database queries**: Batched, run every 10-60 seconds
- **Alerting**: Async, non-blocking
- **Health checks**: Parallel, with timeouts
- **Memory**: <50MB overhead
- **CPU**: <5% additional load

Если видите проблемы с производительностью:

1. Увеличьте интервалы проверок:
```python
# В onboarding_monitor.py
await asyncio.sleep(60)  # Вместо 10
```

2. Отключите некоторые компоненты:
```bash
AUTO_RETRY_ENABLED=false  # Если не нужен
```

3. Используйте standalone процесс вместо интеграции

## Next Steps

После интеграции:

1. **Setup Daily Summaries**:
```python
# Add to cron or scheduler
from selfology_bot.monitoring import get_monitoring_system

async def daily_summary():
    monitoring = get_monitoring_system()
    await monitoring.send_daily_summary()

# Schedule for 9:00 AM
```

2. **Setup Grafana Dashboard**: См. `ONBOARDING_MONITORING.md`

3. **Configure Webhooks**: Для интеграции с другими системами

4. **Tune Thresholds**: Based on your actual performance

## Support

Если возникли проблемы:

1. Проверьте документацию: `docs/ONBOARDING_MONITORING.md`
2. Запустите тест: `python test_monitoring_system.py`
3. Проверьте логи: `logs/selfology.log`
4. Используйте CLI для debugging: `python scripts/onboarding_monitoring_cli.py --help`
