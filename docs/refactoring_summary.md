# Рефакторинг: Нормализация хранения статистики пользователя

## Проблема

Поле `total_answers_lifetime` было размещено в таблице `onboarding_sessions`, что приводило к:

1. **Дублированию данных**: Одно значение хранилось во всех сессиях пользователя
2. **Нарушению нормализации**: Характеристика пользователя находилась в таблице сессий
3. **Логической несвязности**: Глобальный счётчик не является свойством сессии

### Пример проблемы:

```sql
-- Пользователь 98005572 имел 11 сессий
-- Значение 9 дублировалось 11 раз!

SELECT id, total_answers_lifetime
FROM onboarding_sessions
WHERE user_id = 98005572;

 id | total_answers_lifetime
----+-----------------------
 11 |                     9  ← дубликат
 10 |                     9  ← дубликат
  9 |                     9  ← дубликат
  8 |                     9  ← дубликат
...
```

## Решение

Создана отдельная таблица `user_stats` для хранения статистики пользователя.

### Архитектура

```
user_stats (новая таблица)
├── user_id (PK)
├── total_answers_lifetime  ← единственное место хранения
├── first_answer_at         ← для аналитики
└── updated_at              ← служебное поле
```

### Преимущества:

✅ **Нормализованная структура** - одна запись на пользователя
✅ **Single Source of Truth** - единственное место хранения
✅ **Логически правильно** - статистика принадлежит пользователю
✅ **Расширяемость** - легко добавлять новые метрики
✅ **Производительность** - меньше дублирования = меньше места

## Реализация

### 1. Создание таблицы

```sql
CREATE TABLE selfology.user_stats (
    user_id INTEGER PRIMARY KEY,
    total_answers_lifetime INTEGER DEFAULT 0 NOT NULL,
    first_answer_at TIMESTAMP,
    updated_at TIMESTAMP DEFAULT NOW() NOT NULL
);
```

### 2. Триггер для автоматического обновления

```sql
CREATE TRIGGER update_user_stats_trigger
AFTER INSERT ON selfology.user_answers_new
FOR EACH ROW
EXECUTE FUNCTION selfology.update_user_stats_on_answer();
```

### 3. Миграция существующих данных

```sql
INSERT INTO selfology.user_stats (user_id, total_answers_lifetime, first_answer_at)
SELECT
    os.user_id,
    COUNT(ua.id) as total_answers,
    MIN(ua.answered_at) as first_answer
FROM selfology.onboarding_sessions os
LEFT JOIN selfology.user_answers_new ua ON ua.session_id = os.id
GROUP BY os.user_id;
```

### 4. Обновление DAO

```python
# Новый метод для получения полной статистики
async def get_user_stats(self, user_id: int) -> Optional[Dict[str, Any]]:
    """Получить статистику пользователя из user_stats"""
    # ...

# Обновлённый метод с JOIN к user_stats
async def get_active_session(self, user_id: int) -> Optional[Dict[str, Any]]:
    """Активная сессия + статистика через LEFT JOIN"""
    # ...
```

## Результат

### До рефакторинга:

```sql
-- 11 записей с дублированием
SELECT COUNT(*), SUM(CASE WHEN total_answers_lifetime = 9 THEN 1 ELSE 0 END)
FROM onboarding_sessions
WHERE user_id = 98005572;

 count | sum
-------+-----
    11 |  11  ← одно значение хранится 11 раз!
```

### После рефакторинга:

```sql
-- 1 запись без дублирования
SELECT * FROM user_stats WHERE user_id = 98005572;

 user_id  | total_answers_lifetime | first_answer_at
----------+------------------------+-----------------
 98005572 |                      9 | 2025-09-09...

-- Сессии больше не хранят дублирующиеся данные
```

## Файлы изменений

### Миграции:
- `alembic/versions/003_add_global_answer_counter_trigger.py` - DEPRECATED
- `alembic/versions/004_create_user_stats_table.py` - **ACTIVE**

### Код:
- `selfology_bot/database/onboarding_dao.py`:
  - `get_user_stats()` - новый метод
  - `get_user_total_answers()` - обновлён (теперь из user_stats)
  - `get_active_session()` - обновлён (LEFT JOIN к user_stats)
  - `save_user_answer()` - без изменений (триггер работает автоматически)

### Документация:
- `docs/global_answer_counter.md` - обновлена
- `docs/refactoring_summary.md` - создана

## SQL для проверки

```sql
-- Проверить структуру
\d selfology.user_stats

-- Проверить данные для конкретного пользователя
SELECT * FROM selfology.user_stats WHERE user_id = 98005572;

-- Проверить что триггер работает
SELECT user_id, total_answers_lifetime, updated_at
FROM selfology.user_stats
ORDER BY updated_at DESC LIMIT 5;

-- Сравнить с реальным количеством ответов
SELECT
    us.user_id,
    us.total_answers_lifetime as stored_count,
    COUNT(ua.id) as actual_count
FROM selfology.user_stats us
LEFT JOIN selfology.onboarding_sessions os ON os.user_id = us.user_id
LEFT JOIN selfology.user_answers_new ua ON ua.session_id = os.id
GROUP BY us.user_id, us.total_answers_lifetime
HAVING us.total_answers_lifetime != COUNT(ua.id);
-- Должен вернуть 0 строк (полное совпадение)
```

## Обратная совместимость

**Старое поле сохранено** в таблице `onboarding_sessions` для плавного перехода:
- Можно удалить после полного тестирования
- Сейчас не используется в коде
- Не обновляется (старый триггер удалён)

**Удаление старого поля (опционально):**
```sql
ALTER TABLE selfology.onboarding_sessions
DROP COLUMN IF EXISTS total_answers_lifetime;
```

## Дата: 2025-10-01

**Статус:** ✅ Успешно применено в production
