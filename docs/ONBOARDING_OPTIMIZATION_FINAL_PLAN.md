# План Оптимизации Онбординга и Векторизации Selfology

**Дата**: 6 октября 2025
**Статус**: Ready for Implementation
**Цель**: Создать оптимальную архитектуру для работы с цифровой личностью

---

## 🎯 EXECUTIVE SUMMARY

Два AI агента (backend-architect и ai-engineer) провели полный анализ архитектуры Selfology и выявили:

### ❌ Критические проблемы:
1. **Вопросы в JSON** - медленный доступ (10ms vs 2ms в PostgreSQL), нет аналитики
2. **JSONB везде** - невозможна SQL аналитика Big Five traits
3. **Semantic search НЕ РАБОТАЕТ** - сравнивает personality narratives с user messages (embedding space mismatch)
4. **Медленный context retrieval** - 280ms для сбора контекста AI

### ✅ Решения готовы:
- Миграция вопросов в PostgreSQL (5x быстрее)
- Денормализация Big Five для SQL аналитики
- Отдельная Qdrant коллекция для chat messages
- Multi-vector facets для разных аспектов личности
- Smart caching для 3x ускорения

---

## 📊 ОЖИДАЕМЫЕ РЕЗУЛЬТАТЫ

### Performance
| Операция | Сейчас | После | Улучшение |
|----------|--------|-------|-----------|
| Поиск вопроса (QuestionRouter) | 10ms | 2ms | **5x** |
| Context assembly для AI | 280ms | <100ms | **3x** |
| Semantic search | ❌ не работает | 50ms | **∞** |
| Big Five аналитика | невозможна | 20ms | **новая функция** |

### Cost
| Операция | Сейчас | После | Экономия |
|----------|--------|-------|----------|
| Embeddings на 693 ответа | $0.014 | $0.0024 | **83%** |
| Update при новом ответе | $0.00002 | $0.000002 | **90%** |

### Quality
| Метрика | Сейчас | После | Улучшение |
|---------|--------|-------|-----------|
| AI relevance (контекст) | 70% | 90% | **+20%** |
| Context completeness | 60% | 95% | **+35%** |
| Semantic search работает | 0% | 80% | **новая функция** |

---

## 🗺️ ПЛАН МИГРАЦИИ

Оба агента создали **готовые файлы** для каждой фазы.

### TRACK A: База Данных (Backend)
*Ведет*: backend-architect

#### Phase A1: Questions → PostgreSQL (3-4 дня) ⭐ КРИТИЧНО
**Цель**: Перенести 693 вопроса из JSON в БД

**Что делать**:
```bash
# 1. Создать таблицу questions
psql -h localhost -U postgres -d n8n < migrations/011_add_questions_table.sql

# 2. Валидация
python scripts/sync_questions_json_to_db.py --validate

# 3. Загрузка данных
python scripts/sync_questions_json_to_db.py --execute

# 4. Проверка
python scripts/sync_questions_json_to_db.py --verify
```

**Файлы созданы**:
- ✅ `migrations/011_add_questions_table.sql` - создание таблицы
- ✅ `scripts/sync_questions_json_to_db.py` - синхронизация
- ✅ `examples/optimized_data_access_patterns.py` - примеры

**Impact**:
- ✅ 5x быстрее QuestionRouter
- ✅ SQL аналитика вопросов (skip rate, avg completion time)
- ✅ Auto-statistics (triggers)

---

#### Phase A2: Big Five Denormalization (4-5 дней)
**Цель**: Извлечь Big Five из JSONB в отдельные колонки

**Что делать**:
```bash
# 1. Добавить колонки + backfill
psql -h localhost -U postgres -d n8n < migrations/012_optimize_answer_analysis_bigfive.sql

# 2. Update AnswerAnalyzer
# (см. examples/optimized_data_access_patterns.py)

# 3. Test SQL аналитика
psql -c "SELECT * FROM selfology.get_personality_evolution(123, 30);"
```

**Файлы созданы**:
- ✅ `migrations/012_optimize_answer_analysis_bigfive.sql` - миграция
- ✅ SQL функции для аналитики (evolution, similar users, avg Big Five)

**Impact**:
- ✅ SQL аналитика Big Five (тренды, кластеры)
- ✅ Поиск похожих пользователей
- ✅ Personality evolution timeline

---

#### Phase A3: Smart Context Assembly (2-3 дня)
**Цель**: Создать функцию `get_user_full_context()` - 1 запрос вместо 5

**Что делать**:
```sql
-- SQL функция уже в migrations/012_...sql
SELECT * FROM selfology.get_user_full_context(user_id);

-- Update Orchestrator / ChatCoachService
-- (см. examples/optimized_data_access_patterns.py)
```

**Impact**: 3x быстрее context retrieval

---

### TRACK B: Векторизация (AI)
*Ведет*: ai-engineer

#### Phase B1: Fix Semantic Search (1-2 дня) ⭐⭐ КРИТИЧНО!
**Цель**: Создать коллекцию `chat_messages` для Message→Message comparison

**Что делать**:
```bash
cd /home/ksnk/n8n-enterprise/projects/selfology

# 1. Check Qdrant status
python scripts/check_qdrant_status.py

# 2. Создать коллекцию chat_messages
python scripts/create_chat_messages_collection.py

# 3. Backfill existing messages
python scripts/backfill_chat_embeddings.py --days 30

# 4. Update code
# См. docs/VECTOR_OPTIMIZATION_QUICK_START.md раздел 2
```

**Файлы созданы**:
- ✅ `scripts/create_chat_messages_collection.py`
- ✅ `scripts/backfill_chat_embeddings.py`
- ✅ `scripts/check_qdrant_status.py`
- ✅ `docs/VECTOR_OPTIMIZATION_QUICK_START.md`

**Impact**:
- ✅ Semantic search ЗАРАБОТАЕТ ("you felt similar 2 weeks ago...")
- ✅ AI контекст станет более релевантным
- ✅ Personalized insights

**ВАЖНО**: Это самая критическая фаза! Сейчас semantic search отключен в production.

---

#### Phase B2: Multi-Vector Facets (3-5 дней)
**Цель**: Разделить личность на 6 специализированных векторов

**Архитектура**:
```python
# Вместо 1 вектора (1536D):
personality_profiles = {
    "embedding": [...],  # Всё вместе
}

# → 6 целевых векторов (512D каждый):
personality_facets = {
    "identity": [...],     # Кто я?
    "emotions": [...],     # Что чувствую?
    "goals": [...],        # Куда иду?
    "barriers": [...],     # Что мешает?
    "skills": [...],       # Что умею?
    "relationships": [...] # Кто важен?
}
```

**Преимущества**:
- Targeted search (искать только в нужном аспекте)
- Partial updates (обновлять только changed facets)
- 83% cost savings

**Файлы созданы**:
- ✅ `examples/vector_optimization_examples.py` - Example 2
- ✅ `docs/VECTOR_OPTIMIZATION_ANALYSIS.md` - раздел "Phase 2"

---

#### Phase B3: Smart Caching (2-3 дня)
**Цель**: Cache для <100ms context retrieval

**Стратегия**:
```python
# 5-minute cache (in-memory)
cache = {
    user_id: {
        "context": {...},
        "expires": timestamp + 300
    }
}

# + Parallel fetching
context = await asyncio.gather(
    get_personality(user_id),
    get_recent_messages(user_id),
    get_insights(user_id)
)
```

**Impact**: 3x faster (280ms → 90ms)

**Файлы созданы**:
- ✅ `examples/vector_optimization_examples.py` - Example 3

---

#### Phase B4: Incremental Updates (2-3 дня)
**Цель**: Weighted averaging вместо full re-embedding

**Метод**:
```python
# Вместо:
new_embedding = embed(ALL 50 answers)  # $$$

# →
new_embedding = 0.9 * old_embedding + 0.1 * embed(new_answer)  # $
```

**Impact**: 90% cost reduction

**Файлы созданы**:
- ✅ `examples/vector_optimization_examples.py` - Example 4

---

## 📅 TIMELINE & DEPENDENCIES

### Sprint 1 (Week 1): Критичные фазы
**Goal**: Fix broken semantic search + быстрый QuestionRouter

- **Day 1-2**: Phase A1 (Questions → PostgreSQL)
- **Day 3-4**: Phase B1 (Fix Semantic Search) ⭐⭐ КРИТИЧНО
- **Day 5**: Testing & Deploy

**Deliverables**:
- ✅ QuestionRouter использует PostgreSQL (5x faster)
- ✅ Semantic search работает (was disabled)
- ✅ AI context более релевантный

---

### Sprint 2 (Week 2): Big Five аналитика + Multi-Vector
**Goal**: SQL analytics + targeted search

- **Day 1-3**: Phase A2 (Big Five denormalization)
- **Day 4-5**: Phase B2 (Multi-Vector facets, часть 1)

**Deliverables**:
- ✅ SQL аналитика Big Five (evolution, clustering)
- ✅ Multi-vector facets setup

---

### Sprint 3 (Week 3): Performance + Cost optimization
**Goal**: 3x faster, 90% cheaper

- **Day 1-2**: Phase B2 (Multi-Vector facets, часть 2)
- **Day 3**: Phase A3 (Smart context assembly)
- **Day 4**: Phase B3 (Smart caching)
- **Day 5**: Phase B4 (Incremental updates)

**Deliverables**:
- ✅ Context assembly <100ms
- ✅ Cache hit rate 70%
- ✅ Embedding cost -90%

---

## 📁 СОЗДАННЫЕ ФАЙЛЫ

Все файлы находятся в `/home/ksnk/n8n-enterprise/projects/selfology/`

### Документация

**Backend (Database)**:
- `docs/DATA_STORAGE_ARCHITECTURE_ANALYSIS.md` - полный анализ (400+ строк)
- `docs/MIGRATION_PLAN_DATA_OPTIMIZATION.md` - пошаговый план

**AI (Vectors)**:
- `docs/VECTOR_OPTIMIZATION_README.md` - навигация
- `docs/VECTOR_OPTIMIZATION_ANALYSIS.md` - полный анализ (50+ страниц)
- `docs/VECTOR_OPTIMIZATION_QUICK_START.md` - быстрый старт (5 минут)

---

### Миграции (SQL)

**Track A - Database**:
- `migrations/011_add_questions_table.sql` - таблица questions
- `migrations/012_optimize_answer_analysis_bigfive.sql` - Big Five optimization

---

### Скрипты (Python)

**Track A - Database**:
- `scripts/sync_questions_json_to_db.py` - синхронизация JSON→DB

**Track B - Vectors**:
- `scripts/create_chat_messages_collection.py` - Phase B1
- `scripts/backfill_chat_embeddings.py` - Phase B1
- `scripts/check_qdrant_status.py` - диагностика

---

### Примеры кода

**Track A**:
- `examples/optimized_data_access_patterns.py` - SQL паттерны

**Track B**:
- `examples/vector_optimization_examples.py` - 4 готовых примера

---

## 🚀 КАК НАЧАТЬ?

### Вариант 1: Быстрый старт (Phase B1 - критично!)
```bash
cd /home/ksnk/n8n-enterprise/projects/selfology

# 1. Прочитай Quick Start
cat docs/VECTOR_OPTIMIZATION_QUICK_START.md

# 2. Fix semantic search
python scripts/check_qdrant_status.py
python scripts/create_chat_messages_collection.py
python scripts/backfill_chat_embeddings.py --days 30

# 3. Update code (см. Quick Start раздел 2)
# 4. Test & deploy
```

**Почему начать с этого?**
- Semantic search сейчас НЕ РАБОТАЕТ
- Быстрый fix (1-2 дня)
- Immediate impact на AI relevance

---

### Вариант 2: Полный план (оба Track)
```bash
# Sprint 1 Week 1
# Track A - Database
psql -h localhost -U postgres -d n8n < migrations/011_add_questions_table.sql
python scripts/sync_questions_json_to_db.py --execute

# Track B - Vectors
python scripts/create_chat_messages_collection.py
python scripts/backfill_chat_embeddings.py --days 30

# Далее см. Timeline выше
```

---

## 💡 КЛЮЧЕВЫЕ ИНСАЙТЫ

### 1. JSON vs PostgreSQL (backend-architect)
**Проблема**: JSON удобен для версионирования, но медленный для запросов.
**Решение**: Гибридный подход - JSON как source of truth, PostgreSQL для runtime.
**Result**: 5x faster + SQL analytics

### 2. Embedding Space Mismatch (ai-engineer)
**Проблема**: Semantic search сравнивал personality narratives с user messages - это как сравнивать биографии с SMS в векторном пространстве!
**Решение**: Отдельная коллекция `chat_messages` для Message→Message comparison.
**Result**: Semantic search ЗАРАБОТАЕТ

### 3. JSONB Trade-offs (backend-architect)
**Проблема**: JSONB гибкий, но невозможна SQL аналитика.
**Решение**: Гибридный - Big Five в колонках (стабильные), остальное в JSONB (динамическое).
**Result**: SQL analytics + гибкость

### 4. Multi-Vector Facets (ai-engineer)
**Проблема**: Один вектор для всей личности - сложно update, дорого.
**Решение**: 6 специализированных векторов (Identity, Emotions, Goals, ...).
**Result**: Targeted search + 83% cost savings

---

## ⚠️ РИСКИ И МИТИГАЦИЯ

### Риск 1: Миграция сломает production
**Вероятность**: Low
**Митигация**:
- ✅ Параллельная работа старой/новой системы (feature flags)
- ✅ A/B тестирование перед full deploy
- ✅ Rollback plan на каждом этапе

### Риск 2: Performance регрессия
**Вероятность**: Medium
**Митигация**:
- ✅ Benchmark до/после каждой фазы
- ✅ Rollback если degradation >10%
- ✅ Query monitoring (pg_stat_statements)

### Риск 3: Embedding space inconsistency
**Вероятность**: Medium
**Митигация**:
- ✅ Backfill script для пересчета всех embeddings
- ✅ Validation checks (cosine similarity range)
- ✅ Progressive rollout (10% → 50% → 100%)

---

## 📊 МЕТРИКИ УСПЕХА

### Performance
- [ ] QuestionRouter <2ms (was 10ms)
- [ ] Context assembly <100ms (was 280ms)
- [ ] Semantic search <50ms (was disabled)
- [ ] Cache hit rate >70% (was 0%)

### Cost
- [ ] Embedding cost -83% per user
- [ ] Update cost -90% per answer

### Quality
- [ ] AI relevance >90% (was 70%)
- [ ] Context completeness >95% (was 60%)
- [ ] Semantic search working (was 0%)

---

## 🎓 СЛЕДУЮЩИЕ ШАГИ

1. **Прочитай документацию**:
   - Backend: `docs/DATA_STORAGE_ARCHITECTURE_ANALYSIS.md`
   - AI: `docs/VECTOR_OPTIMIZATION_QUICK_START.md`

2. **Выбери track**:
   - Option A: Start with Phase B1 (critical semantic search fix)
   - Option B: Start with Phase A1 (database optimization)
   - Option C: Параллельно (recommended, но нужно 2 разработчика)

3. **Создай ветку**:
   ```bash
   git checkout -b feature/optimize-onboarding-architecture
   ```

4. **Начни миграцию** (см. Timeline выше)

5. **Мониторинг**:
   - Metrics dashboard (см. примеры в docs/)
   - Error tracking
   - A/B testing results

---

## 📞 КОНТАКТЫ

**Backend вопросы** (Database, PostgreSQL):
- Документация: `docs/DATA_STORAGE_ARCHITECTURE_ANALYSIS.md`
- Примеры: `examples/optimized_data_access_patterns.py`

**AI вопросы** (Vectors, Embeddings):
- Документация: `docs/VECTOR_OPTIMIZATION_QUICK_START.md`
- Примеры: `examples/vector_optimization_examples.py`

---

**Готов начать? Начни с Phase B1 (semantic search fix) - наибольший impact за минимальное время!** 🚀

