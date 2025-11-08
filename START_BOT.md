# Инструкция по запуску Selfology Bot (с Redis FSM)

## Быстрый старт

```bash
cd /home/ksnk/n8n-enterprise/projects/selfology
./run-local.sh
```

## Проверка статуса

### 1. Проверить что бот запущен
```bash
pgrep -f selfology_controller.py
# Должен вывести PID процесса
```

### 2. Посмотреть логи
```bash
tail -f logs/selfology.log | grep -E "FSM|Redis|instance|lock"
```

### 3. Проверить Redis lock
```bash
docker exec n8n-redis redis-cli -n 1 GET selfology:bot:instance_lock
# Должно показать текущий PID и время старта
```

## Остановка бота

### Graceful shutdown (рекомендуется)
```bash
# Ctrl+C в терминале где запущен бот
# ИЛИ отправить SIGTERM:
kill -TERM $(pgrep -f selfology_controller.py)
```

### Force kill (только в крайнем случае)
```bash
pkill -9 -f selfology_controller.py
```

## Troubleshooting

### Проблема: "Another bot instance is already running"

**Причина:** Lock не освобожден (crash предыдущего запуска)

**Решение:**
```bash
# 1. Убить все процессы
pkill -9 -f selfology_controller.py

# 2. Очистить lock вручную
docker exec n8n-redis redis-cli -n 1 DEL selfology:bot:instance_lock

# 3. Подождать 2-3 секунды
sleep 3

# 4. Запустить заново
./run-local.sh
```

### Проблема: "Redis connection refused"

**Причина:** Redis container не запущен или недоступен

**Решение:**
```bash
# Проверить статус контейнера
docker ps | grep n8n-redis

# Проверить доступность
nc -zv 172.18.0.8 6379

# Если не доступен - проверить IP:
docker inspect n8n-redis --format='{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}'

# Обновить .env.development с правильным IP
```

### Проблема: FSM states не сохраняются

**Диагностика:**
```bash
# 1. Проверить Redis FSM DB
docker exec n8n-redis redis-cli -n 1 KEYS "fsm:*"

# 2. Запустить тесты
source venv/bin/activate
python test_redis_fsm.py

# 3. Проверить логи на ошибки
grep -i "redis" logs/selfology.log | tail -20
```

## Мониторинг

### Real-time FSM state transitions
```bash
tail -f logs/selfology.log | grep "FSM State"
```

### Redis FSM keys
```bash
docker exec n8n-redis redis-cli -n 1 KEYS "*" | head -20
```

### Instance lock status
```bash
watch -n 1 'docker exec n8n-redis redis-cli -n 1 GET selfology:bot:instance_lock'
```

## Тестирование

### Автоматические тесты
```bash
source venv/bin/activate
python test_redis_fsm.py
```

**Должно вывести:**
```
Пройдено: 3/3
✅ ВСЕ ТЕСТЫ УСПЕШНО ПРОЙДЕНЫ!
```

### Ручное тестирование

1. Запустить бота
2. Отправить `/start` в Telegram
3. Начать онбординг `/onboarding`
4. Ответить на первый вопрос
5. **Перезапустить бота** (Ctrl+C + ./run-local.sh)
6. Отправить ответ на следующий вопрос
7. ✅ Бот должен продолжить с того же места (не сбросить прогресс)

## Полезные команды

### Очистить все FSM states (reset для всех пользователей)
```bash
docker exec n8n-redis redis-cli -n 1 FLUSHDB
```

### Посмотреть состояние конкретного пользователя
```bash
# Замените USER_ID на реальный ID
docker exec n8n-redis redis-cli -n 1 KEYS "*:USER_ID:*"
```

### Backup Redis FSM данных
```bash
docker exec n8n-redis redis-cli -n 1 --rdb /tmp/fsm_backup.rdb SAVE
```

## Архитектура (кратко)

```
Selfology Bot
    ↓
Redis DB=1 (FSM States)
    ↓
PostgreSQL (Persistent Data)
    ↓
Qdrant (Vectors)
```

**Критично:** 
- Redis DB=1 используется ТОЛЬКО для FSM
- Redis DB=0 используется для cache
- PostgreSQL для всех остальных данных

---

**Готово!** Бот должен работать стабильно без потери состояний.
