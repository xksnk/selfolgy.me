# План миграции: Оптимизация архитектуры хранения данных

**Цель:** Улучшить производительность и queryability без breaking changes
**Срок:** 2-3 недели (постепенная миграция)
**Риск:** Низкий-Средний (параллельная работа старой и новой системы)

---

## Фазы миграции

### PHASE 1: Questions в PostgreSQL (3-4 дня)

**Цель:** Переместить вопросы из JSON в БД для быстрых запросов

#### Шаг 1.1: Создать таблицу (30 минут)
```bash
# Запустить миграцию
psql -h localhost -U postgres -d n8n < migrations/011_add_questions_table.sql

# Проверить
psql -h localhost -U postgres -d n8n -c "SELECT COUNT(*) FROM selfology.questions;"
# Expected: 0 (пустая таблица)
```

#### Шаг 1.2: Загрузить данные из JSON (1 час)
```bash
# Валидация (dry run)
python scripts/sync_questions_json_to_db.py --validate

# Реальная загрузка
python scripts/sync_questions_json_to_db.py --execute

# Проверка
python scripts/sync_questions_json_to_db.py --verify
# Expected: 693 questions loaded
```

#### Шаг 1.3: Обновить QuestionRouter (2 дня)
```python
# selfology_bot/services/onboarding/question_router.py

# BEFORE (читает из JSON)
candidates = self.core.search_questions(
    domain=["IDENTITY"],
    min_safety=3
)

# AFTER (читает из PostgreSQL)
async def _search_questions_db(self, filters):
    rows = await self.db.fetch("""
        SELECT * FROM selfology.search_questions(
            p_domains := $1,
            p_min_safety := $2,
            p_exclude_ids := $3
        )
    """, filters['domains'], filters['min_safety'], filters['exclude_ids'])

    return [dict(row) for row in rows]
```

#### Шаг 1.4: A/B тестирование (1 день)
- 10% пользователей → PostgreSQL
- 90% пользователей → JSON (старый метод)
- Сравнить производительность и корректность
- Если OK → 100% на PostgreSQL

#### Результат Phase 1:
- ✅ Вопросы в PostgreSQL
- ✅ QuestionRouter использует SQL
- ✅ JSON файл сохранен для версионирования
- 📈 Производительность: ~2ms вместо ~10ms

---

### PHASE 2: Backward compatibility cleanup (1 день)

**Цель:** Убрать дублирование questions_metadata

#### Шаг 2.1: Объединить флаги
```sql
-- Скопировать флаги из questions_metadata в questions
UPDATE selfology.questions q
SET
    is_flagged = qm.needs_work,
    flag_reason = qm.admin_notes,
    flagged_at = NOW()
FROM selfology.questions_metadata qm
WHERE q.question_id = qm.json_question_id
  AND qm.needs_work = true;
```

#### Шаг 2.2: Deprecated questions_metadata
```sql
-- Переименовать таблицу (не удалять сразу!)
ALTER TABLE selfology.questions_metadata
RENAME TO _deprecated_questions_metadata;

-- Оставить на 1 месяц для rollback
```

---

### PHASE 3: Big Five денормализация (4-5 дней)

**Цель:** Извлечь Big Five из JSONB для SQL аналитики

#### Шаг 3.1: Создать колонки и индексы (1 час)
```bash
# Запустить миграцию
psql -h localhost -U postgres -d n8n < migrations/012_optimize_answer_analysis_bigfive.sql
```

#### Шаг 3.2: Backfill данных (1 час)
```sql
-- Автоматически в миграции 012
-- Извлекает Big Five из JSONB в отдельные колонки
```

#### Шаг 3.3: Обновить AnswerAnalyzer (2 дня)
```python
# selfology_bot/analysis/answer_analyzer.py

# BEFORE (сохраняет всё в JSONB)
analysis_result = {
    "trait_scores": {
        "big_five": {
            "openness": 0.75,
            "conscientiousness": 0.65,
            ...
        }
    }
}

# AFTER (сохраняет Big Five отдельно)
await conn.execute("""
    INSERT INTO selfology.answer_analysis (
        user_answer_id,
        openness, conscientiousness, extraversion, agreeableness, neuroticism,
        extended_traits  -- остальные traits в JSONB
    ) VALUES ($1, $2, $3, $4, $5, $6, $7)
""",
    answer_id,
    big_five['openness'],
    big_five['conscientiousness'],
    big_five['extraversion'],
    big_five['agreeableness'],
    big_five['neuroticism'],
    json.dumps(extended_traits)
)
```

#### Шаг 3.4: Создать аналитические endpoints (1 день)
```python
# Новые API endpoints для аналитики
@router.get("/api/v1/users/{user_id}/personality-profile")
async def get_personality_profile(user_id: int):
    """Личностный профиль с Big Five"""

@router.get("/api/v1/users/{user_id}/personality-evolution")
async def get_personality_evolution(user_id: int):
    """Эволюция личности за время онбординга"""

@router.get("/api/v1/analytics/personality-archetypes")
async def get_personality_archetypes():
    """Кластеризация пользователей"""
```

#### Результат Phase 3:
- ✅ Big Five в отдельных колонках
- ✅ SQL аналитика работает
- ✅ Материализованное представление для дашбордов
- 📈 Новые возможности: эволюция личности, похожие пользователи, архетипы

---

### PHASE 4: VIEW и функции для AI Coach (2-3 дня)

**Цель:** Оптимизировать получение контекста для AI

#### Шаг 4.1: Использовать full_answer_context VIEW
```python
# orchestrator.py - BEFORE
session = await onboarding_dao.get_active_session(user_id)
answers = await onboarding_dao.get_session_answers(session_id)
analyses = await get_analyses(answer_ids)
personality = await personality_dao.get_personality(user_id)
# 4-5 запросов, ~150ms

# orchestrator.py - AFTER
context = await db.fetchrow("""
    SELECT
        session_id, questions_answered,
        recent_answers,  -- JSONB array
        avg_openness, avg_conscientiousness, ...,
        personality_data
    FROM selfology.get_user_full_context($1)
""", user_id)
# 1 запрос, ~50ms
```

#### Шаг 4.2: Обновить ChatCoachService
```python
# services/chat_coach.py

async def get_context_for_ai(self, user_id: int) -> str:
    """Построить контекст для AI Coach"""

    # Получить полный контекст одним запросом
    ctx = await self.db.fetchrow(
        "SELECT * FROM selfology.get_user_full_context($1)",
        user_id
    )

    # Big Five уже доступны как числа!
    personality_summary = f"""
    Личность пользователя:
    - Openness: {ctx['avg_openness']:.2f} (любознательность, креативность)
    - Conscientiousness: {ctx['avg_conscientiousness']:.2f} (организованность)
    - Extraversion: {ctx['avg_extraversion']:.2f} (социальность)
    - Agreeableness: {ctx['avg_agreeableness']:.2f} (доброжелательность)
    - Neuroticism: {ctx['avg_neuroticism']:.2f} (эмоциональная стабильность)
    """

    return personality_summary
```

#### Результат Phase 4:
- ✅ AI Coach получает контекст за 1 запрос
- ✅ Latency: 150ms → 50ms (3x улучшение)
- ✅ Код проще и читабельнее

---

### PHASE 5: Мониторинг и оптимизация (ongoing)

#### Шаг 5.1: Настроить auto-refresh материализованных представлений
```bash
# Добавить в crontab
0 * * * * psql -h localhost -U postgres -d n8n -c "REFRESH MATERIALIZED VIEW CONCURRENTLY selfology.user_personality_summary;"
```

#### Шаг 5.2: Мониторинг производительности
```sql
-- Анализ медленных запросов
SELECT * FROM pg_stat_statements
WHERE query LIKE '%selfology%'
ORDER BY mean_exec_time DESC
LIMIT 20;

-- Использование индексов
SELECT
    schemaname, tablename, indexname,
    idx_scan, idx_tup_read, idx_tup_fetch
FROM pg_stat_user_indexes
WHERE schemaname = 'selfology'
ORDER BY idx_scan DESC;
```

#### Шаг 5.3: VACUUM и ANALYZE
```sql
-- Регулярное обслуживание
VACUUM ANALYZE selfology.questions;
VACUUM ANALYZE selfology.answer_analysis;
VACUUM ANALYZE selfology.digital_personality;
```

---

## Rollback план

### Если что-то пошло не так в Phase 1:
```python
# Вернуться к JSON-based QuestionRouter
# Код уже есть в архиве, просто переключить флаг

USE_DB_QUESTIONS = False  # в config.py
```

### Если что-то пошло не так в Phase 3:
```python
# Big Five всё ещё доступны в JSONB (extended_traits)
# Можно читать оттуда

big_five = analysis['extended_traits']['big_five']
```

---

## Метрики успеха

### Производительность

| Операция | До | После | Улучшение |
|----------|-----|-------|-----------|
| Поиск вопроса | 10ms | 2ms | 5x |
| Полный контекст AI | 150ms | 50ms | 3x |
| Аналитика Big Five | Невозможно | 20ms | ∞ |
| Поиск похожих users | Только Qdrant | 30ms SQL | Новая функция |

### Queryability

- ✅ SQL агрегации по Big Five
- ✅ Personality evolution timeline
- ✅ Question usage statistics
- ✅ User personality archetypes
- ✅ Similar users recommendations

### Гибкость

- ✅ JSON файл сохранен для версионирования
- ✅ JSONB для extended traits (эксперименты)
- ✅ Backward compatibility maintained
- ✅ Rollback возможен на каждом этапе

---

## Чеклист миграции

### Pre-migration
- [ ] Backup базы данных
- [ ] Проверить версию PostgreSQL (>= 12)
- [ ] Проверить доступное место на диске
- [ ] Создать ветку `feature/optimize-data-storage`

### Phase 1
- [ ] Запустить миграцию 011
- [ ] Загрузить вопросы из JSON
- [ ] Проверить 693 questions в БД
- [ ] Обновить QuestionRouter
- [ ] A/B тест 10% пользователей
- [ ] Deploy 100% пользователей

### Phase 2
- [ ] Скопировать флаги из questions_metadata
- [ ] Переименовать deprecated таблицу
- [ ] Проверить работу админских флагов

### Phase 3
- [ ] Запустить миграцию 012
- [ ] Проверить backfill Big Five
- [ ] Обновить AnswerAnalyzer
- [ ] Создать аналитические endpoints
- [ ] Тестирование SQL queries

### Phase 4
- [ ] Обновить orchestrator
- [ ] Обновить ChatCoachService
- [ ] Benchmark производительности
- [ ] Deploy

### Phase 5
- [ ] Настроить cron для REFRESH
- [ ] Настроить мониторинг
- [ ] Документация для команды

---

## Поддержка и вопросы

**Контакты:**
- Backend Architect Team
- Slack: #selfology-dev
- Docs: `/docs/DATA_STORAGE_ARCHITECTURE_ANALYSIS.md`

**Полезные ссылки:**
- Миграции: `/migrations/011_*.sql`, `/migrations/012_*.sql`
- Примеры кода: `/examples/optimized_data_access_patterns.py`
- Sync script: `/scripts/sync_questions_json_to_db.py`
