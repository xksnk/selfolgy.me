# Onboarding Pipeline Monitoring System

**Real-time мониторинг всего пути пользователя от Telegram до Digital Personality**

## Quick Start

```bash
# Test system
python test_monitoring_system.py

# Use CLI
python scripts/onboarding_monitoring_cli.py status
python scripts/onboarding_monitoring_cli.py metrics
python scripts/onboarding_monitoring_cli.py health

# Start standalone monitoring
python scripts/onboarding_monitoring_cli.py start
```

## Architecture

```
┌─────────────────────────────────────────┐
│   OnboardingMonitoringSystem            │
├─────────────────────────────────────────┤
│                                          │
│  Pipeline Monitor → Telegram Alerter    │
│         ↓                                │
│  Auto-Retry Manager                      │
│                                          │
└─────────────────────────────────────────┘
         ↓          ↓          ↓
    PostgreSQL   Qdrant   OpenAI API
```

## Components

### 1. Pipeline Monitor (`onboarding_monitor.py`)

Отслеживает все этапы обработки:

- **Telegram → SQL**: Сохранение ответа
- **SQL → AI Analysis**: Deep analysis pipeline
- **AI → Vectorization**: Qdrant embeddings
- **Vectorization → DP Update**: Digital Personality

**Features**:
- Real-time metrics collection
- Performance tracking
- Error detection
- Queue depth monitoring
- Health checks

### 2. Telegram Alerter (`telegram_alerting.py`)

Отправляет алерты админу:

- **Smart Grouping**: Группирует похожие алерты
- **Rate Limiting**: Предотвращает спам
- **Severity Levels**: warning, error, critical
- **Formatted Messages**: Красивые сообщения с эмодзи

### 3. Auto-Retry Manager (`auto_retry.py`)

Автоматически исправляет ошибки:

- **Exponential Backoff**: 1min → 5min → 15min → 30min
- **Smart Recovery**: Только recoverable ошибки
- **Max Retries**: Configurable limit
- **Success Tracking**: Метрики успешности

## Configuration

Add to `.env`:

```bash
# Telegram Alerts
TELEGRAM_ALERTS_ENABLED=true
TELEGRAM_ALERTS_MIN_SEVERITY=warning
MONITORING_ADMIN_IDS=98005572

# Performance Thresholds
ONBOARDING_SLOW_THRESHOLD_MS=15000
ONBOARDING_STUCK_THRESHOLD_SEC=300
ONBOARDING_FAILURE_THRESHOLD=0.2

# Auto-Retry
AUTO_RETRY_ENABLED=true
AUTO_RETRY_MAX_ATTEMPTS=3
```

## Usage

### Python API

```python
from selfology_bot.monitoring import initialize_onboarding_monitoring

# Initialize
monitoring = await initialize_onboarding_monitoring(
    db_config=db_config,
    bot_token=bot_token,
    admin_chat_ids=[98005572]
)

# Start monitoring
await monitoring.start()

# Get metrics
metrics = await monitoring.get_current_metrics()

# Get status
status = await monitoring.get_pipeline_status(user_id=98005572)

# Check health
health = await monitoring.check_services_health()

# Stop
await monitoring.stop()
```

### CLI Tool

```bash
# Status
python scripts/onboarding_monitoring_cli.py status [--user USER_ID]

# Metrics
python scripts/onboarding_monitoring_cli.py metrics

# Errors
python scripts/onboarding_monitoring_cli.py errors [--hours HOURS]

# Health
python scripts/onboarding_monitoring_cli.py health

# Retry Stats
python scripts/onboarding_monitoring_cli.py retry-stats

# Summary
python scripts/onboarding_monitoring_cli.py summary [--hours HOURS]

# JSON Output
python scripts/onboarding_monitoring_cli.py json
```

## Integration

### Into selfology_controller.py

```python
# At startup
from selfology_bot.monitoring import initialize_onboarding_monitoring

monitoring = await initialize_onboarding_monitoring(...)
asyncio.create_task(monitoring.start())

# At shutdown
monitoring = get_monitoring_system()
await monitoring.stop()
```

See `docs/MONITORING_INTEGRATION.md` for detailed guide.

## Monitoring Data

### Metrics

```json
{
    "timing": {
        "ai_analysis_ms": 3500,
        "total_pipeline_ms": 5550
    },
    "success_rates": {
        "ai_analysis": "100.0%",
        "vectorization": "98.5%",
        "dp_update": "99.2%"
    },
    "queue_depth": {
        "pending_vectorizations": 1,
        "pending_dp_updates": 0
    },
    "errors": {
        "vectorization_errors": 3,
        "dp_update_errors": 1
    }
}
```

### Alert Types

- `error` - Processing error
- `slow_processing` - >15 seconds
- `stuck_task` - >5 minutes
- `high_failure_rate` - >20%
- `service_unhealthy` - Service down
- `stuck_processing` - Pending >5 minutes

### Health Status

- `postgresql` - Database health
- `qdrant` - Vector DB health
- `openai` - AI API health

## Files

```
selfology_bot/monitoring/
├── __init__.py              # Main system
├── onboarding_monitor.py    # Pipeline monitor
├── telegram_alerting.py     # Telegram alerts
├── auto_retry.py            # Auto-retry manager
└── README.md                # This file

scripts/
└── onboarding_monitoring_cli.py  # CLI tool

docs/
├── ONBOARDING_MONITORING.md      # Full documentation
└── MONITORING_INTEGRATION.md     # Integration guide

test_monitoring_system.py    # Test script
```

## Performance

- **Memory**: <50MB overhead
- **CPU**: <5% additional load
- **Database**: Batched queries every 10-60s
- **Non-blocking**: All operations async

## Documentation

- **Full Docs**: `docs/ONBOARDING_MONITORING.md`
- **Integration**: `docs/MONITORING_INTEGRATION.md`
- **CLI Help**: `python scripts/onboarding_monitoring_cli.py --help`

## Features

✓ Real-time pipeline tracking
✓ Telegram alerts with smart grouping
✓ Automatic error recovery
✓ Performance metrics
✓ Health checks for all services
✓ Configurable thresholds
✓ Rate limiting
✓ Exponential backoff
✓ CLI tool
✓ Python API
✓ Minimal performance impact
✓ Easy integration

## Requirements

- Python 3.10+
- asyncpg
- httpx
- aiogram (for alerts)
- Existing Selfology bot infrastructure

## Testing

```bash
# Run test script
python test_monitoring_system.py

# Should output:
# ✓ Monitoring system initialized
# ✓ Metrics collected
# ✓ Pipeline status retrieved
# ✓ Health checks completed
# ✓ Errors retrieved
# ✓ Retry stats retrieved
# ✓ Metrics summary retrieved
# ✓ Test alert sent
```

## Troubleshooting

### Alerts not sending

1. Check `TELEGRAM_ALERTS_ENABLED=true`
2. Check bot token
3. Check admin can receive messages
4. Check severity level

### Monitoring not starting

1. Check database connection
2. Check imports
3. Check environment variables
4. See `docs/MONITORING_INTEGRATION.md`

### Auto-retry not working

1. Check `AUTO_RETRY_ENABLED=true`
2. Check retry counts in DB
3. Check logs for errors

## Support

For issues and questions:
- Check documentation in `docs/`
- Run test script
- Check logs in `logs/selfology.log`
- Use CLI for debugging

## License

Part of Selfology Bot project.
