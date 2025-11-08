# Анализ архитектуры хранения данных онбординга Selfology

**Дата анализа:** 2025-10-06
**Аналитик:** Backend Architect
**Статус проекта:** Production (Phase 2-3 активна)

---

## Executive Summary

Текущая архитектура представляет собой **грамотный гибридный подход** (JSON + PostgreSQL + Qdrant), который хорошо справляется с задачами, но имеет потенциал для оптимизации производительности запросов и целостности данных.

**Ключевые выводы:**
- ✅ **Не требуется полная перестройка** - базовая архитектура здорова
- ⚠️ **Рекомендуется постепенная оптимизация** в 3 этапа
- 🎯 **Приоритет:** улучшить queryability без потери гибкости
- 📊 **ROI:** ~3x ускорение сложных запросов, проще аналитика

---

## 1. Вопросы в JSON vs PostgreSQL

### Текущее состояние

**Файл:** `intelligent_question_core/data/enhanced_questions.json` (516KB, 693 вопроса)

```json
{
  "id": "q_001",
  "text": "Чем вы гордитесь больше всего?",
  "classification": {
    "journey_stage": "EXPLORING",
    "depth_level": "CONSCIOUS",
    "domain": "IDENTITY",
    "energy_dynamic": "HEAVY"
  },
  "psychology": {
    "complexity": 3,
    "emotional_weight": 4,
    "insight_potential": 3,
    "safety_level": 2,
    "trust_requirement": 3
  },
  "processing_hints": {
    "recommended_model": "claude-3.5-sonnet",
    "batch_compatible": true
  }
}
```

**PostgreSQL:** только `questions_metadata` с admin флагами

### Анализ производительности

| Метрика | JSON | PostgreSQL |
|---------|------|------------|
| Загрузка всех вопросов | ~5-10ms (парсинг 516KB) | ~2-3ms (SELECT 693 rows) |
| Поиск по критериям | O(n) сканирование | O(log n) с индексами |
| Фильтрация (domain, depth, energy) | В памяти после загрузки | SQL с индексами |
| Memory footprint | 516KB на каждый процесс | Shared в PostgreSQL |
| Изменение вопроса | Пересоздание JSON файла | UPDATE одной строки |
| Версионирование | Git + файл | Audit log + миграции |

### Рекомендация: **ГИБРИДНЫЙ ПОДХОД v2.0**

**Решение:** Переместить вопросы в PostgreSQL, но сохранить JSON для deployments и версионирования.

#### Почему это правильно:

1. **Производительность:** Индексы PostgreSQL дают 3-5x ускорение для сложных фильтров
2. **Аналитика:** SQL запросы типа "какие вопросы чаще всего пропускают" станут простыми
3. **Целостность:** Foreign keys между questions ↔ user_answers
4. **Масштабируемость:** 693 вопроса → 5000+ вопросов в будущем

#### Предлагаемая схема:

```sql
-- НОВАЯ ТАБЛИЦА: selfology.questions
CREATE TABLE IF NOT EXISTS selfology.questions (
    id SERIAL PRIMARY KEY,

    -- Идентификация
    question_id VARCHAR(20) UNIQUE NOT NULL,  -- "q_001", "q_002"
    text TEXT NOT NULL,
    source_system VARCHAR(50) DEFAULT 'onboarding_v7',

    -- Классификация (денормализовано для быстрых запросов)
    journey_stage VARCHAR(20) NOT NULL,       -- EXPLORING, DEEPENING, etc.
    depth_level VARCHAR(20) NOT NULL,         -- SURFACE, CONSCIOUS, SHADOW, etc.
    domain VARCHAR(30) NOT NULL,              -- IDENTITY, EMOTIONS, RELATIONSHIPS, etc.
    energy_dynamic VARCHAR(20) NOT NULL,      -- OPENING, NEUTRAL, HEAVY, HEALING

    -- Психологические метрики (числовые для агрегаций!)
    complexity SMALLINT CHECK (complexity BETWEEN 1 AND 5),
    emotional_weight SMALLINT CHECK (emotional_weight BETWEEN 1 AND 5),
    insight_potential SMALLINT CHECK (insight_potential BETWEEN 1 AND 5),
    safety_level SMALLINT CHECK (safety_level BETWEEN 1 AND 5),
    trust_requirement SMALLINT CHECK (trust_requirement BETWEEN 1 AND 5),

    -- Processing hints (редко меняется, можно JSONB)
    processing_hints JSONB DEFAULT '{}'::jsonb,

    -- Metadata (гибкость для будущих расширений)
    metadata JSONB DEFAULT '{}'::jsonb,

    -- Связи с другими вопросами
    connections VARCHAR(20)[] DEFAULT '{}',   -- Array of question_ids

    -- Административные флаги (из questions_metadata)
    is_flagged BOOLEAN DEFAULT false,
    flagged_by_admin VARCHAR(50),
    flag_reason TEXT,
    flagged_at TIMESTAMP,

    -- Статистика использования (аналитика!)
    times_asked INTEGER DEFAULT 0,
    times_skipped INTEGER DEFAULT 0,
    avg_answer_length INTEGER,
    last_used_at TIMESTAMP,

    -- Активность
    is_active BOOLEAN DEFAULT true,

    -- Audit
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- ИНДЕКСЫ для быстрых запросов
CREATE INDEX idx_questions_domain ON selfology.questions(domain);
CREATE INDEX idx_questions_depth ON selfology.questions(depth_level);
CREATE INDEX idx_questions_energy ON selfology.questions(energy_dynamic);
CREATE INDEX idx_questions_safety ON selfology.questions(safety_level);
CREATE INDEX idx_questions_active ON selfology.questions(is_active) WHERE is_active = true;
CREATE INDEX idx_questions_flagged ON selfology.questions(is_flagged) WHERE is_flagged = false;

-- Composite индекс для Smart Mix алгоритма (QuestionRouter)
CREATE INDEX idx_questions_routing ON selfology.questions(
    domain, depth_level, energy_dynamic, safety_level
) WHERE is_active = true AND is_flagged = false;

-- GIN индекс для поиска по connections
CREATE INDEX idx_questions_connections ON selfology.questions USING GIN(connections);

-- Полнотекстовый поиск по вопросам (для админки)
CREATE INDEX idx_questions_text_search ON selfology.questions
USING GIN(to_tsvector('russian', text));
```

#### Триггер для статистики:

```sql
-- Автоматическое обновление статистики при создании ответа
CREATE OR REPLACE FUNCTION selfology.update_question_stats()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE selfology.questions
    SET
        times_asked = times_asked + 1,
        last_used_at = NOW()
    WHERE question_id = NEW.question_json_id;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_question_stats
    AFTER INSERT ON selfology.user_answers_new
    FOR EACH ROW
    EXECUTE FUNCTION selfology.update_question_stats();
```

#### Как сохранить гибкость метаданных:

1. **JSONB поле `metadata`** для экспериментальных полей
2. **Миграции Alembic** для добавления новых колонок
3. **JSON-файл остается source of truth** для версионирования
4. **Sync script** для загрузки из JSON в PostgreSQL

---

## 2. Анализ в JSONB vs нормализованные таблицы

### Текущее состояние

**Таблица:** `answer_analysis` хранит ВСЕ в JSONB:

```sql
answer_analysis (
    id SERIAL PRIMARY KEY,
    user_answer_id INTEGER,

    -- ВСЁ в JSONB
    trait_scores JSONB,          -- Big Five + traits
    emotional_state VARCHAR(30),
    quality_score FLOAT,
    confidence_score FLOAT,

    -- Еще больше JSONB
    raw_ai_response JSONB,
    next_question_hints JSONB
)
```

**Проблема:** Нельзя сделать SQL запросы типа:
```sql
-- Это НЕ работает эффективно:
SELECT AVG((trait_scores->>'big_five'->>'openness')::float)
FROM answer_analysis;
```

### Trade-offs: JSONB vs Нормализация

| Критерий | JSONB | Нормализованные таблицы |
|----------|-------|-------------------------|
| **Гибкость схемы** | ⭐⭐⭐⭐⭐ Добавлять поля легко | ⭐⭐ Требует миграций |
| **SQL запросы** | ⭐⭐ Громоздкие, медленные | ⭐⭐⭐⭐⭐ Простые, быстрые |
| **Индексы** | ⭐⭐⭐ GIN индексы, но сложные | ⭐⭐⭐⭐⭐ B-tree, эффективные |
| **Агрегации** | ⭐⭐ Парсинг JSON на лету | ⭐⭐⭐⭐⭐ Нативные SUM/AVG |
| **Disk space** | ⭐⭐⭐⭐ Компактно | ⭐⭐⭐ Больше строк/таблиц |
| **Type safety** | ⭐⭐ Всё text внутри | ⭐⭐⭐⭐⭐ Типы на уровне БД |

### Рекомендация: **ГИБРИДНЫЙ ПОДХОД (горячие данные + архив)**

**Стратегия:** Денормализовать часто используемые поля, остальное в JSONB.

#### Оптимизированная схема `answer_analysis`:

```sql
CREATE TABLE IF NOT EXISTS selfology.answer_analysis (
    id SERIAL PRIMARY KEY,
    user_answer_id INTEGER REFERENCES selfology.user_answers_new(id) ON DELETE CASCADE,

    -- ============================================================
    -- ДЕНОРМАЛИЗОВАННЫЕ ПОЛЯ (для быстрых SQL запросов)
    -- ============================================================

    -- Big Five Traits (часто используется для аналитики и AI)
    openness NUMERIC(4,3) CHECK (openness BETWEEN 0 AND 1),           -- 0.000 - 1.000
    conscientiousness NUMERIC(4,3) CHECK (conscientiousness BETWEEN 0 AND 1),
    extraversion NUMERIC(4,3) CHECK (extraversion BETWEEN 0 AND 1),
    agreeableness NUMERIC(4,3) CHECK (agreeableness BETWEEN 0 AND 1),
    neuroticism NUMERIC(4,3) CHECK (neuroticism BETWEEN 0 AND 1),

    -- Качество и уверенность (для фильтрации)
    quality_score NUMERIC(3,2) CHECK (quality_score BETWEEN 0 AND 1),
    confidence_score NUMERIC(3,2) CHECK (confidence_score BETWEEN 0 AND 1),

    -- Эмоциональное состояние (для роутинга)
    emotional_state VARCHAR(30),     -- joy, sadness, anxiety, peace, etc.
    fatigue_level NUMERIC(3,2),      -- 0.00 - 1.00

    -- Специальные ситуации (для alerts)
    special_situation VARCHAR(20),   -- crisis, breakthrough, resistance, NULL
    is_milestone BOOLEAN DEFAULT false,

    -- ============================================================
    -- JSONB ПОЛЯ (для гибкости и редко используемых данных)
    -- ============================================================

    -- Дополнительные traits (динамические, адаптивные, domain-specific)
    extended_traits JSONB DEFAULT '{}'::jsonb,

    -- Психологические инсайты (полный AI анализ)
    psychological_insights TEXT,

    -- Рекомендации для следующего вопроса
    next_question_hints JSONB DEFAULT '{}'::jsonb,

    -- Raw AI response (для debug и reprocessing)
    raw_ai_response JSONB,

    -- ============================================================
    -- МЕТАДАННЫЕ
    -- ============================================================

    analysis_version VARCHAR(10) NOT NULL DEFAULT '2.0',
    ai_model_used VARCHAR(30),
    processing_time_ms INTEGER,
    processed_at TIMESTAMP DEFAULT NOW(),

    -- Статусы векторизации
    vectorization_status VARCHAR(20) DEFAULT 'pending',
    dp_update_status VARCHAR(20) DEFAULT 'pending',

    -- Debug и compression
    debug_priority SMALLINT DEFAULT 0,
    can_be_compressed BOOLEAN DEFAULT true
);

-- ИНДЕКСЫ для аналитики Big Five
CREATE INDEX idx_analysis_openness ON selfology.answer_analysis(openness);
CREATE INDEX idx_analysis_conscientiousness ON selfology.answer_analysis(conscientiousness);
CREATE INDEX idx_analysis_extraversion ON selfology.answer_analysis(extraversion);
CREATE INDEX idx_analysis_agreeableness ON selfology.answer_analysis(agreeableness);
CREATE INDEX idx_analysis_neuroticism ON selfology.answer_analysis(neuroticism);

-- Composite index для поиска личности
CREATE INDEX idx_analysis_personality_profile ON selfology.answer_analysis(
    openness, conscientiousness, extraversion, agreeableness, neuroticism
);

-- Индексы для фильтрации
CREATE INDEX idx_analysis_quality ON selfology.answer_analysis(quality_score)
WHERE quality_score >= 0.7;

CREATE INDEX idx_analysis_special ON selfology.answer_analysis(special_situation)
WHERE special_situation IS NOT NULL;

-- GIN индекс для extended_traits
CREATE INDEX idx_analysis_extended_traits ON selfology.answer_analysis
USING GIN(extended_traits);
```

#### Почему этот подход лучше:

✅ **Big Five отдельно** - это стабильные метрики, по ним делают аналитику
✅ **SQL агрегации работают:**
```sql
-- Эволюция Openness пользователя за время онбординга
SELECT
    ua.answered_at::date,
    AVG(aa.openness) as avg_openness
FROM selfology.answer_analysis aa
JOIN selfology.user_answers_new ua ON ua.id = aa.user_answer_id
WHERE ua.session_id = 123
GROUP BY ua.answered_at::date
ORDER BY ua.answered_at::date;
```

✅ **Extended traits в JSONB** - гибкость для экспериментов
✅ **Компромисс:** 5 колонок vs 100% гибкость

---

## 3. Digital Personality: JSONB vs Нормализация

### Текущее состояние

**Таблица:** `digital_personality` - 10 JSONB слоев

```sql
digital_personality (
    user_id INTEGER PRIMARY KEY,

    -- 10 JSONB слоев
    identity JSONB,
    interests JSONB,
    goals JSONB,
    barriers JSONB,
    relationships JSONB,
    values JSONB,
    current_state JSONB,
    skills JSONB,
    experiences JSONB,
    health JSONB
)
```

### Рекомендация: **ОСТАВИТЬ КАК ЕСТЬ + Улучшить структуру JSONB**

**Почему JSONB здесь правильнее:**

1. **Неструктурированные данные:** interests могут быть ["рисование", "coding", "путешествия"]
2. **Редкие изменения:** обновляется каждые N ответов, не каждый запрос
3. **Векторный поиск в Qdrant:** primary search layer, PostgreSQL - backup
4. **Гибкость AI:** разные пользователи → разные insights

#### Оптимизация: Стандартизировать структуру JSONB

```sql
-- КОММЕНТАРИЙ: Стандартная структура для всех JSONB слоев
COMMENT ON COLUMN selfology.digital_personality.interests IS
'Standard structure: {
    "version": "2.0",
    "updated_at": "2025-10-06T12:00:00",
    "source_answers": [123, 456, 789],
    "confidence": 0.85,
    "items": [
        {
            "name": "Программирование",
            "category": "hobby",
            "intensity": 0.9,
            "first_mentioned": "2025-09-01",
            "last_mentioned": "2025-10-06",
            "evidence": ["answer_123", "answer_456"]
        }
    ]
}';
```

#### Добавить материализованное представление для аналитики:

```sql
-- VIEW для быстрого доступа к ключевым метрикам
CREATE MATERIALIZED VIEW selfology.personality_summary AS
SELECT
    user_id,

    -- Подсчет элементов в каждом слое
    jsonb_array_length(COALESCE(interests->'items', '[]'::jsonb)) as interests_count,
    jsonb_array_length(COALESCE(goals->'items', '[]'::jsonb)) as goals_count,
    jsonb_array_length(COALESCE(barriers->'items', '[]'::jsonb)) as barriers_count,
    jsonb_array_length(COALESCE(skills->'items', '[]'::jsonb)) as skills_count,

    -- Средняя уверенность
    (
        COALESCE((interests->>'confidence')::numeric, 0) +
        COALESCE((goals->>'confidence')::numeric, 0) +
        COALESCE((barriers->>'confidence')::numeric, 0)
    ) / 3.0 as avg_confidence,

    -- Completeness
    completeness_score,
    total_answers_analyzed,
    last_updated

FROM selfology.digital_personality;

-- Refresh каждый час
CREATE UNIQUE INDEX ON selfology.personality_summary(user_id);
```

---

## 4. Связь вопрос-ответ-анализ

### Текущее состояние

```
questions (JSON)
    ↓ (question_json_id - STRING)
user_answers_new
    ↓ (answer_id - INTEGER FK)
answer_analysis
```

**Проблема:** Нет прямой связи вопрос → анализ

### Рекомендация: **Добавить Foreign Key после миграции вопросов в PostgreSQL**

```sql
-- После миграции questions в PostgreSQL:

-- 1. Добавить FK в user_answers_new
ALTER TABLE selfology.user_answers_new
ADD COLUMN question_id INTEGER REFERENCES selfology.questions(id);

-- 2. Создать индекс
CREATE INDEX idx_answers_question_fk ON selfology.user_answers_new(question_id);

-- 3. Backfill данных
UPDATE selfology.user_answers_new ua
SET question_id = q.id
FROM selfology.questions q
WHERE ua.question_json_id = q.question_id;

-- 4. Сделать NOT NULL после backfill
ALTER TABLE selfology.user_answers_new
ALTER COLUMN question_id SET NOT NULL;

-- 5. Deprecated поле можно оставить для обратной совместимости
-- question_json_id - сделать nullable в будущем
```

#### VIEW для полного контекста:

```sql
CREATE OR REPLACE VIEW selfology.full_answer_context AS
SELECT
    -- User answer
    ua.id as answer_id,
    ua.session_id,
    ua.raw_answer,
    ua.answered_at,

    -- Question details
    q.question_id,
    q.text as question_text,
    q.domain,
    q.depth_level,
    q.energy_dynamic,
    q.complexity,
    q.emotional_weight,

    -- Analysis results
    aa.openness,
    aa.conscientiousness,
    aa.extraversion,
    aa.agreeableness,
    aa.neuroticism,
    aa.quality_score,
    aa.confidence_score,
    aa.emotional_state,
    aa.special_situation,
    aa.psychological_insights,

    -- Session context
    os.user_id,
    os.questions_answered,
    os.started_at as session_started

FROM selfology.user_answers_new ua
JOIN selfology.questions q ON q.id = ua.question_id
LEFT JOIN selfology.answer_analysis aa ON aa.user_answer_id = ua.id
LEFT JOIN selfology.onboarding_sessions os ON os.id = ua.session_id;

-- Использование:
-- SELECT * FROM selfology.full_answer_context WHERE user_id = 123 ORDER BY answered_at;
```

---

## 5. Производительность запросов

### Критические запросы системы

#### 5.1. Получение полного контекста для AI Coach

**Текущий подход:** Множественные запросы

```python
# orchestrator.py - сейчас делает 4-5 запросов
session = await onboarding_dao.get_active_session(user_id)
answers = await onboarding_dao.get_session_answers(session_id)
personality = await personality_dao.get_personality(user_id)
vectors = await qdrant_client.search(...)
```

**Оптимизация:** Один запрос с JOIN

```sql
-- Создать функцию для получения полного контекста
CREATE OR REPLACE FUNCTION selfology.get_user_full_context(p_user_id INTEGER)
RETURNS TABLE (
    -- Session
    session_id INTEGER,
    questions_answered INTEGER,
    session_started TIMESTAMP,

    -- Recent answers (last 10)
    recent_answers JSONB,

    -- Analysis summary
    avg_openness NUMERIC,
    avg_conscientiousness NUMERIC,
    avg_extraversion NUMERIC,
    avg_agreeableness NUMERIC,
    avg_neuroticism NUMERIC,

    -- Personality layers
    personality_data JSONB,

    -- Stats
    total_answers_lifetime INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        os.id as session_id,
        os.questions_answered,
        os.started_at as session_started,

        -- Recent answers as JSONB array
        (
            SELECT jsonb_agg(
                jsonb_build_object(
                    'question_text', q.text,
                    'answer', ua.raw_answer,
                    'answered_at', ua.answered_at,
                    'domain', q.domain
                )
                ORDER BY ua.answered_at DESC
            )
            FROM selfology.user_answers_new ua
            JOIN selfology.questions q ON q.id = ua.question_id
            WHERE ua.session_id = os.id
            LIMIT 10
        ) as recent_answers,

        -- Average Big Five from all analyses
        (
            SELECT AVG(aa.openness)
            FROM selfology.answer_analysis aa
            JOIN selfology.user_answers_new ua ON ua.id = aa.user_answer_id
            WHERE ua.session_id = os.id
        ) as avg_openness,

        (
            SELECT AVG(aa.conscientiousness)
            FROM selfology.answer_analysis aa
            JOIN selfology.user_answers_new ua ON ua.id = aa.user_answer_id
            WHERE ua.session_id = os.id
        ) as avg_conscientiousness,

        (
            SELECT AVG(aa.extraversion)
            FROM selfology.answer_analysis aa
            JOIN selfology.user_answers_new ua ON ua.id = aa.user_answer_id
            WHERE ua.session_id = os.id
        ) as avg_extraversion,

        (
            SELECT AVG(aa.agreeableness)
            FROM selfology.answer_analysis aa
            JOIN selfology.user_answers_new ua ON ua.id = aa.user_answer_id
            WHERE ua.session_id = os.id
        ) as avg_agreeableness,

        (
            SELECT AVG(aa.neuroticism)
            FROM selfology.answer_analysis aa
            JOIN selfology.user_answers_new ua ON ua.id = aa.user_answer_id
            WHERE ua.session_id = os.id
        ) as avg_neuroticism,

        -- Personality layers
        jsonb_build_object(
            'identity', dp.identity,
            'interests', dp.interests,
            'goals', dp.goals,
            'barriers', dp.barriers,
            'values', dp.values
        ) as personality_data,

        -- Total lifetime answers
        us.total_answers_lifetime

    FROM selfology.onboarding_sessions os
    LEFT JOIN selfology.digital_personality dp ON dp.user_id = os.user_id
    LEFT JOIN selfology.user_stats us ON us.user_id = os.user_id
    WHERE os.user_id = p_user_id
      AND os.status = 'active'
    LIMIT 1;
END;
$$ LANGUAGE plpgsql;
```

**Использование в коде:**

```python
# orchestrator.py - AFTER optimization
context = await db.fetchrow(
    "SELECT * FROM selfology.get_user_full_context($1)",
    user_id
)

# Теперь 1 запрос вместо 5!
```

#### 5.2. QuestionRouter - поиск следующего вопроса

**Текущий подход:** Загрузка всех 693 вопросов из JSON в память

**Оптимизация:** SQL с индексами

```sql
-- question_router.py сможет использовать:
SELECT
    question_id, text,
    domain, depth_level, energy_dynamic,
    complexity, safety_level, trust_requirement
FROM selfology.questions
WHERE is_active = true
  AND is_flagged = false
  AND domain = ANY($1)              -- ['IDENTITY', 'EMOTIONS']
  AND depth_level = $2               -- 'CONSCIOUS'
  AND energy_dynamic != 'HEAVY'
  AND safety_level >= $3             -- 3
  AND question_id NOT IN (           -- Already answered
      SELECT q.question_id
      FROM selfology.user_answers_new ua
      JOIN selfology.questions q ON q.id = ua.question_id
      WHERE ua.session_id = $4
  )
ORDER BY RANDOM()  -- or smart weighting
LIMIT 20;

-- С индексом idx_questions_routing это будет ~0.5ms
```

#### 5.3. Аналитика: эволюция личности

```sql
-- Как менялся Openness пользователя за время онбординга
SELECT
    date_trunc('day', ua.answered_at) as date,
    AVG(aa.openness) as avg_openness,
    STDDEV(aa.openness) as variance,
    COUNT(*) as answers_count
FROM selfology.answer_analysis aa
JOIN selfology.user_answers_new ua ON ua.id = aa.user_answer_id
WHERE ua.session_id = 123
GROUP BY date_trunc('day', ua.answered_at)
ORDER BY date;
```

### Дополнительные индексы

```sql
-- Для поиска похожих пользователей по Big Five
CREATE INDEX idx_analysis_similarity ON selfology.answer_analysis(
    openness, conscientiousness, extraversion
) WHERE quality_score >= 0.7;

-- Для timeline queries
CREATE INDEX idx_answers_timeline ON selfology.user_answers_new(
    session_id, answered_at
);

-- Для поиска кризисных ситуаций
CREATE INDEX idx_analysis_crisis ON selfology.answer_analysis(
    special_situation, processed_at
) WHERE special_situation IN ('crisis', 'breakthrough');
```

---

## 6. План миграции

### Стратегия: Постепенная миграция без downtime

#### PHASE 1: Добавить таблицу questions (параллельно с JSON)

**Срок:** 1-2 дня разработки + тестирование
**Риск:** Низкий (не трогаем существующий код)

```bash
# 1. Создать Alembic миграцию
alembic revision -m "add_questions_table"

# 2. В миграции создать таблицу + индексы (см. схему выше)

# 3. Создать sync script
python scripts/sync_questions_json_to_db.py

# 4. Запустить миграцию
alembic upgrade head
```

**Validation:** Оба источника работают параллельно

#### PHASE 2: Обновить QuestionRouter использовать PostgreSQL

**Срок:** 1 день разработки
**Риск:** Средний (меняем логику роутинга)

```python
# question_router.py - BEFORE
candidates = self.core.search_questions(
    domain=["IDENTITY", "EMOTIONS"],
    min_safety=3
)

# question_router.py - AFTER
async def _search_questions_db(
    self,
    domains: List[str],
    depth_level: str,
    min_safety: int,
    exclude_ids: List[str]
) -> List[Dict]:
    """Search questions from PostgreSQL with indexes"""

    query = """
        SELECT
            question_id, text,
            domain, depth_level, energy_dynamic,
            complexity, emotional_weight, safety_level, trust_requirement,
            processing_hints, metadata
        FROM selfology.questions
        WHERE is_active = true
          AND is_flagged = false
          AND domain = ANY($1)
          AND depth_level = $2
          AND safety_level >= $3
          AND question_id != ALL($4)
        ORDER BY RANDOM()
        LIMIT 50
    """

    rows = await self.db.fetch(
        query,
        domains,
        depth_level,
        min_safety,
        exclude_ids
    )

    return [dict(row) for row in rows]
```

**Validation:** A/B test - 10% пользователей на новый метод

#### PHASE 3: Оптимизировать answer_analysis (Big Five отдельно)

**Срок:** 2-3 дня разработки
**Риск:** Средний (миграция данных)

```sql
-- Alembic migration
ALTER TABLE selfology.answer_analysis
ADD COLUMN openness NUMERIC(4,3),
ADD COLUMN conscientiousness NUMERIC(4,3),
ADD COLUMN extraversion NUMERIC(4,3),
ADD COLUMN agreeableness NUMERIC(4,3),
ADD COLUMN neuroticism NUMERIC(4,3);

-- Backfill data
UPDATE selfology.answer_analysis
SET
    openness = (trait_scores->'big_five'->>'openness')::numeric,
    conscientiousness = (trait_scores->'big_five'->>'conscientiousness')::numeric,
    extraversion = (trait_scores->'big_five'->>'extraversion')::numeric,
    agreeableness = (trait_scores->'big_five'->>'agreeableness')::numeric,
    neuroticism = (trait_scores->'big_five'->>'neuroticism')::numeric
WHERE trait_scores IS NOT NULL;

-- Create indexes
CREATE INDEX idx_analysis_openness ON selfology.answer_analysis(openness);
-- ... etc
```

**Validation:** Сравнить результаты SQL vs JSONB queries

#### PHASE 4: Создать VIEW и функции для быстрого доступа

**Срок:** 1 день
**Риск:** Низкий (только добавляем, не меняем)

- `full_answer_context` VIEW
- `get_user_full_context()` функция
- `personality_summary` materialized view

---

## 7. Метрики успеха

### До оптимизации (текущее)

| Операция | Время | Запросов к БД |
|----------|-------|---------------|
| Получить контекст для AI | ~150ms | 5 запросов |
| Найти следующий вопрос | ~10ms | 0 (JSON в памяти) |
| Аналитика Big Five | Невозможно | N/A |
| Поиск похожих пользователей | Только Qdrant | 0 |

### После оптимизации (целевые)

| Операция | Время | Запросов к БД |
|----------|-------|---------------|
| Получить контекст для AI | ~50ms | 1 запрос |
| Найти следующий вопрос | ~2ms | 1 запрос с индексом |
| Аналитика Big Five | ~20ms | 1 SQL агрегация |
| Поиск похожих пользователей | ~30ms | 1 SQL + Qdrant |

**Ожидаемое улучшение:** 2-3x ускорение сложных операций

---

## 8. Рекомендации по приоритетам

### HIGH PRIORITY (сделать в первую очередь)

1. **Миграция questions в PostgreSQL**
   - Причина: упростит аналитику и масштабирование
   - ROI: высокий (будет полезно сразу)
   - Риск: низкий (параллельно с JSON)

2. **Денормализация Big Five в answer_analysis**
   - Причина: нужна аналитика сейчас
   - ROI: средний (SQL запросы работают)
   - Риск: средний (миграция данных)

3. **VIEW для полного контекста (`full_answer_context`)**
   - Причина: упростит код в orchestrator
   - ROI: средний (читабельность кода)
   - Риск: низкий (только добавление)

### MEDIUM PRIORITY (можно отложить на 1-2 месяца)

4. **Функция `get_user_full_context()`**
   - Причина: оптимизация производительности
   - ROI: средний (50ms → 20ms)
   - Риск: низкий

5. **Материализованное представление `personality_summary`**
   - Причина: аналитика и дашборды
   - ROI: низкий (пока мало пользователей)
   - Риск: низкий

### LOW PRIORITY (nice to have)

6. **Полнотекстовый поиск по вопросам**
   - Причина: удобство для админов
   - ROI: низкий
   - Риск: низкий

---

## 9. Альтернативные подходы (не рекомендуемые)

### ❌ Вариант 1: Все в JSONB

**Pros:** Максимальная гибкость
**Cons:** SQL запросы становятся кошмаром, производительность падает

### ❌ Вариант 2: Полная нормализация

**Pros:** SQL запросы идеальны
**Cons:** Слишком много таблиц, медленные JOIN, потеря гибкости

**Пример:**
```
trait_scores (id, answer_id, trait_name, trait_value)
```
Это создаст 5+ строк на каждый анализ, JOIN будет медленным.

### ❌ Вариант 3: MongoDB вместо PostgreSQL

**Pros:** JSON-native, гибкость схемы
**Cons:** Нет ACID транзакций, сложнее аналитика, новая инфраструктура

---

## 10. Заключение

### Резюме рекомендаций

✅ **Questions:** Переместить в PostgreSQL (PHASE 1-2)
✅ **Answer Analysis:** Денормализовать Big Five (PHASE 3)
✅ **Digital Personality:** Оставить JSONB + стандартизировать структуру
✅ **Связи:** Добавить FK после миграции questions
✅ **Производительность:** VIEW и функции для сложных запросов

### Ключевые принципы

1. **Гибридный подход:** Стабильные данные → колонки, динамические → JSONB
2. **Постепенная миграция:** Без downtime, A/B тестирование
3. **Индексы везде:** WHERE, JOIN, ORDER BY - все должно быть быстрым
4. **Аналитика важна:** SQL должен работать для бизнес-метрик

### Next Steps

```bash
# 1. Создать ветку
git checkout -b feature/optimize-data-storage

# 2. PHASE 1: Миграция questions
alembic revision -m "add_questions_table"
# Редактировать миграцию (см. схему выше)
alembic upgrade head

# 3. Sync script
python scripts/sync_questions_json_to_db.py --validate

# 4. Тестирование
pytest tests/test_questions_db.py

# 5. Deploy постепенно
# Сначала миграция БД, потом код
```

---

**Контакты для вопросов:**
Backend Architect Team
Дата последнего обновления: 2025-10-06
