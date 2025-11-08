# Проверка состояния системы

Выполни полную проверку состояния Selfology:

## 1. Статус контейнеров
```bash
docker ps --filter "name=selfology" --filter "name=n8n-postgres" --filter "name=qdrant"
```

## 2. Статус базы данных
```bash
docker exec -it n8n-postgres psql -U postgres -d n8n -c "\dt selfology.*"
```

## 3. Логи бота (последние 50 строк)
```bash
tail -50 logs/selfology.log
```

## 4. Последние ошибки
```bash
tail -20 logs/errors/errors.log
```

## 5. Тесты (быстрая проверка)
```bash
source venv/bin/activate && pytest tests/unit/core/ -v --tb=short
```

Покажи результаты и выяви проблемы, если есть.
