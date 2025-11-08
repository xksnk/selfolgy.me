# Global Answer Counter Implementation

## Описание

Система автоматического подсчёта **общего количества ответов пользователя** за всё время (не только в рамках текущей сессии).

## Архитектура (v2 - Нормализованная)

### База данных

**Таблица `user_stats` (нормализованная структура):**
```sql
CREATE TABLE selfology.user_stats (
    user_id INTEGER PRIMARY KEY,
    total_answers_lifetime INTEGER DEFAULT 0 NOT NULL,
    first_answer_at TIMESTAMP,
    updated_at TIMESTAMP DEFAULT NOW() NOT NULL
);
```

**Триггер (автоматическое обновление):**
```sql
CREATE TRIGGER update_user_stats_trigger
AFTER INSERT ON selfology.user_answers_new
FOR EACH ROW
EXECUTE FUNCTION selfology.update_user_stats_on_answer();
```

### Почему отдельная таблица?

**Старая архитектура (v1) - ПРОБЛЕМЫ:**
- ❌ `total_answers_lifetime` хранился в каждой сессии
- ❌ Дублирование: значение повторялось 10+ раз для одного пользователя
- ❌ Нарушение нормализации БД

**Новая архитектура (v2) - РЕШЕНИЕ:**
- ✅ Одна запись на пользователя (нормализация)
- ✅ Single Source of Truth
- ✅ Логически правильно: статистика принадлежит пользователю, а не сессии
- ✅ Можно добавлять новые метрики без изменения sessions

### Как это работает

1. **При сохранении ответа:**
   - Ответ записывается в `user_answers_new`
   - Триггер срабатывает автоматически
   - Триггер обновляет/создаёт запись в `user_stats` для пользователя
   - Инкрементирует `total_answers_lifetime` (+1)

2. **Преимущества:**
   - ✅ Полностью автоматическое обновление
   - ✅ Всегда актуальные данные
   - ✅ Не требует изменений в бизнес-логике
   - ✅ Нормализованная структура БД
   - ✅ Легко добавлять новую статистику

## Использование

### OnboardingDAO

**Получить активную сессию (с глобальным счётчиком):**
```python
session = await onboarding_dao.get_active_session(user_id)
total_answers = session['total_answers_lifetime']  # Из user_stats через JOIN
session_answers = session['questions_answered']    # Из текущей сессии
```

**Получить только глобальный счётчик:**
```python
total = await onboarding_dao.get_user_total_answers(user_id)
```

**Получить полную статистику пользователя:**
```python
stats = await onboarding_dao.get_user_stats(user_id)
# {
#     'user_id': 98005572,
#     'total_answers_lifetime': 9,
#     'first_answer_at': datetime(...),
#     'updated_at': datetime(...)
# }
```

## Пример

Пользователь `98005572`:
- Имеет 11 сессий
- Всего ответил на **9 вопросов** за всё время
- В текущей сессии: `questions_answered = 1`

**Таблица user_stats (нормализованная):**
```sql
SELECT * FROM selfology.user_stats WHERE user_id = 98005572;

 user_id  | total_answers_lifetime |   first_answer_at    |     updated_at
----------+------------------------+----------------------+-------------------
 98005572 |                      9 | 2025-09-09 10:46:38  | 2025-10-01 16:08:14
```

**Сессии (без дублирования):**
```sql
SELECT id, questions_answered
FROM selfology.onboarding_sessions
WHERE user_id = 98005572
ORDER BY started_at DESC LIMIT 3;

 id | questions_answered
----+--------------------
 11 |                  1
 10 |                  0
  9 |                  0
```

## Миграции

**v1 (старая, с дублированием):**
- Файл: `alembic/versions/003_add_global_answer_counter_trigger.py`
- Дата: 2025-10-01
- Статус: DEPRECATED

**v2 (правильная, нормализованная):**
- Файл: `alembic/versions/004_create_user_stats_table.py`
- Дата: 2025-10-01
- Статус: **ACTIVE** ✅

## Технические детали

**Структура данных:**
- Таблица `user_stats`: одна запись на пользователя
- При первом ответе: создаётся запись с `total_answers_lifetime = 1`
- При последующих: инкрементируется счётчик

**Производительность:**
- Индексы:
  - `user_stats_pkey` (PRIMARY KEY на user_id)
  - `idx_user_stats_total_answers` (для сортировки по активности)
  - `idx_user_stats_first_answer` (для когортного анализа)
- Триггер работает только при INSERT (не при UPDATE/DELETE)
- Обновление происходит в рамках одной транзакции
- LEFT JOIN в `get_active_session()` для совместимости с новыми пользователями

**Обратная совместимость:**
- Поле `total_answers_lifetime` оставлено в `onboarding_sessions` для плавного перехода
- Можно удалить после полного перехода на user_stats

## Откат (если потребуется)

```bash
# Alembic downgrade
alembic downgrade -1

# Или вручную через SQL
docker exec n8n-postgres psql -U n8n -d n8n << 'EOF'
DROP TRIGGER IF EXISTS update_user_stats_trigger ON selfology.user_answers_new;
DROP FUNCTION IF EXISTS selfology.update_user_stats_on_answer();
DROP INDEX IF EXISTS selfology.idx_user_stats_total_answers;
DROP INDEX IF EXISTS selfology.idx_user_stats_first_answer;
DROP TABLE IF EXISTS selfology.user_stats;
EOF
```

## История изменений

**2025-10-01 16:00** - v1: Создан триггер с дублированием в sessions
**2025-10-01 16:10** - v2: Рефакторинг - создана нормализованная таблица user_stats ✅
