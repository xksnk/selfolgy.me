# План Имплементации Оптимизации Selfology
## Для Согласования

**Дата**: 6 октября 2025
**Подготовлено**: Claude Code (backend-architect + ai-engineer)
**Статус**: Ожидает утверждения

---

## 📋 EXECUTIVE SUMMARY

**Цель**: Оптимизировать онбординг и векторизацию для быстрой и релевантной работы AI

**Ключевые улучшения**:
- ✅ QuestionRouter: 10ms → 2ms (5x быстрее)
- ✅ AI context: 280ms → <100ms (3x быстрее)
- ✅ Semantic search: ПОЧИНИТЬ (сейчас не работает)
- ✅ Embedding cost: -83%
- ✅ SQL аналитика Big Five: NEW

**Общее время**: 2-3 недели (зависит от параллельности)

---

## 🎯 ЗАДАЧИ ДЛЯ РЕАЛИЗАЦИИ

Разбито на **8 независимых задач** (можно делать параллельно).

---

### ⭐⭐ ЗАДАЧА 1: Fix Semantic Search (КРИТИЧНО!)
**Приоритет**: P0 (блокирует AI релевантность)
**Время**: 1-2 дня
**Параллельность**: Можно запускать независимо
**Риск**: Low

#### Проблема
Semantic search сейчас **НЕ РАБОТАЕТ**. Код сравнивает personality narratives (описания личности) с user messages (сообщения чата) в одном векторном пространстве. Это как сравнивать биографии с SMS - embedding spaces разные.

#### Что я сделаю
1. **Создам Qdrant коллекцию** `chat_messages` (1536D)
   - Запущу: `scripts/create_chat_messages_collection.py`
   - Конфигурация: COSINE distance, optimized для быстрого поиска

2. **Backfill existing messages**
   - Загружу последние 30 дней сообщений из PostgreSQL
   - Создам embeddings через OpenAI API
   - Сохраню в `chat_messages` коллекцию

3. **Обновлю код** `services/chat_coach.py`:
   ```python
   # БЫЛО (line 246-249):
   message_embedding = embed(user_message)
   similar = qdrant.search(
       collection="personality_evolution",  # ❌ НЕПРАВИЛЬНО
       vector=message_embedding
   )

   # СТАНЕТ:
   message_embedding = embed(user_message)
   similar = qdrant.search(
       collection="chat_messages",  # ✅ ПРАВИЛЬНО
       vector=message_embedding,
       filter={"user_id": user_id}
   )
   ```

4. **Обновлю** `data_access/user_dao.py`:
   - Добавлю метод `save_message_with_embedding()`
   - Каждое новое сообщение → автоматически создаем embedding

5. **Создам тесты**:
   - Unit test для embedding creation
   - Integration test для semantic search
   - Benchmark: latency должен быть <50ms

#### Критерии приемки
- [ ] Коллекция `chat_messages` создана в Qdrant
- [ ] Backfill завершен (все messages за 30 дней)
- [ ] Semantic search возвращает релевантные результаты
- [ ] Latency <50ms
- [ ] Tests проходят

#### Файлы которые изменю
- `services/chat_coach.py` (lines 204-273)
- `data_access/user_dao.py` (добавлю новый метод)
- `tests/test_semantic_search.py` (новый файл)

---

### ⭐ ЗАДАЧА 2: Questions → PostgreSQL
**Приоритет**: P1 (улучшает performance)
**Время**: 3-4 дня
**Параллельность**: Можно параллельно с Задачей 1
**Риск**: Low-Medium

#### Проблема
693 вопроса в JSON файле. Каждый раз QuestionRouter:
1. Загружает весь JSON (~516KB)
2. Сканирует in-memory для фильтров
3. Невозможна SQL аналитика (какие вопросы работают лучше?)

#### Что я сделаю
1. **Запущу SQL миграцию** `migrations/011_add_questions_table.sql`:
   - Создам таблицу `selfology.questions` с 17 колонками
   - Денормализую classification и psychology поля
   - Создам 13 индексов для быстрых фильтров
   - Добавлю triggers для auto-statistics

2. **Загружу данные** из JSON:
   ```bash
   python scripts/sync_questions_json_to_db.py --execute
   ```
   - Валидация перед загрузкой
   - Проверка дубликатов
   - Verification после загрузки

3. **Обновлю** `selfology_bot/services/onboarding/question_router.py`:
   ```python
   # БЫЛО:
   question = self.question_core.get_question(question_id)

   # СТАНЕТ:
   async with self.db.get_connection() as conn:
       question = await conn.fetchrow(
           "SELECT * FROM selfology.questions WHERE id = $1",
           question_id
       )
   ```

4. **Создам аналитические функции**:
   - `get_question_statistics()` - skip rate, completion time
   - `get_popular_questions()` - топ вопросы по domain
   - `get_problematic_questions()` - высокий skip rate

5. **A/B тест**:
   - Feature flag: `USE_DB_QUESTIONS`
   - 10% traffic → DB
   - 90% traffic → JSON
   - Сравню latency и error rate
   - Если OK → 100% DB

6. **Cleanup**:
   - Merge `questions_metadata` → `questions` (admin flags)
   - Update all foreign keys

#### Критерии приемки
- [ ] Таблица создана, 693 вопроса загружены
- [ ] QuestionRouter latency: <2ms (было 10ms)
- [ ] A/B тест показал 0 errors
- [ ] Аналитические функции работают
- [ ] 100% traffic переведен на DB

#### Файлы которые изменю
- `selfology_bot/services/onboarding/question_router.py` (core logic)
- `selfology_bot/database/onboarding_dao.py` (новые методы)
- `tests/test_question_router.py` (update tests)

---

### ⭐ ЗАДАЧА 3: Big Five Denormalization
**Приоритет**: P1 (новая функциональность)
**Время**: 4-5 дней
**Параллельность**: После Задачи 2 (нужна DB)
**Риск**: Medium

#### Проблема
Big Five traits хранятся в JSONB:
```sql
-- Это НЕ работает эффективно:
SELECT AVG((analysis_result->'personality_traits'->'big_five'->>'openness')::float)
FROM answer_analysis;
-- ❌ Slow, нет индексов, типы не те
```

#### Что я сделаю
1. **Запущу миграцию** `migrations/012_optimize_answer_analysis_bigfive.sql`:
   - Добавлю 5 колонок: `openness`, `conscientiousness`, `extraversion`, `agreeableness`, `neuroticism`
   - Тип: `NUMERIC(4,3)` (range 0.000-1.000)
   - Backfill из JSONB для existing records

2. **Обновлю** `selfology_bot/analysis/answer_analyzer.py`:
   ```python
   # При сохранении анализа
   await conn.execute("""
       INSERT INTO answer_analysis
       (answer_id, analysis_result, openness, conscientiousness, ...)
       VALUES ($1, $2, $3, $4, ...)
   """, answer_id, jsonb_result,
        traits['openness'], traits['conscientiousness'], ...)
   ```

3. **Создам SQL функции для аналитики**:
   ```sql
   -- Эволюция личности
   SELECT * FROM selfology.get_personality_evolution(user_id, days);

   -- Похожие пользователи
   SELECT * FROM selfology.find_similar_users(user_id, limit);

   -- Средние значения
   SELECT * FROM selfology.get_avg_big_five(user_ids);
   ```

4. **Создам dashboard endpoints**:
   - `/api/personality/evolution/{user_id}` - график Big Five за время
   - `/api/personality/similar/{user_id}` - похожие пользователи
   - `/api/analytics/big_five` - глобальная статистика

5. **Обновлю ChatCoach**:
   - Использовать SQL запросы для personality context
   - Вместо парсинга JSONB → прямые колонки

#### Критерии приемки
- [ ] Миграция выполнена, backfill успешен
- [ ] SQL запросы работают <20ms
- [ ] AnswerAnalyzer сохраняет в обе структуры (JSONB + колонки)
- [ ] Dashboard endpoints работают
- [ ] ChatCoach использует новые запросы

#### Файлы которые изменю
- `selfology_bot/analysis/answer_analyzer.py` (save logic)
- `selfology_bot/database/onboarding_dao.py` (новые аналитические методы)
- `services/chat_coach.py` (использование Big Five данных)
- `src/api/personality_routes.py` (новый файл - endpoints)

---

### ЗАДАЧА 4: Smart Context Assembly
**Приоритет**: P2 (performance)
**Время**: 2-3 дня
**Параллельность**: После Задачи 3
**Риск**: Low

#### Проблема
ChatCoach делает 5+ отдельных SQL запросов для context:
```python
session = await dao.get_active_session(user_id)       # 30ms
answers = await dao.get_session_answers(session_id)   # 40ms
personality = await dao.get_personality(user_id)      # 20ms
insights = await dao.get_insights(user_id)            # 30ms
stats = await dao.get_stats(user_id)                  # 20ms
# Total: ~150ms + network overhead
```

#### Что я сделаю
1. **Создам SQL функцию** `get_user_full_context()`:
   ```sql
   CREATE OR REPLACE FUNCTION selfology.get_user_full_context(
       p_user_id BIGINT
   ) RETURNS TABLE (
       -- Session info
       session_id INTEGER,
       session_status TEXT,
       questions_answered INTEGER,

       -- Recent answers (JSON array)
       recent_answers JSONB,

       -- Big Five (direct columns)
       avg_openness NUMERIC,
       avg_conscientiousness NUMERIC,
       -- ...

       -- Personality data
       personality_data JSONB,

       -- Statistics
       total_sessions INTEGER,
       total_answers INTEGER
   ) AS $$
   BEGIN
       RETURN QUERY
       WITH session_data AS (...),
            answer_data AS (...),
            big_five_data AS (...),
            personality_info AS (...),
            stats_data AS (...)
       SELECT * FROM ... JOIN ... JOIN ...;
   END;
   $$ LANGUAGE plpgsql;
   ```

2. **Обновлю** `services/chat_coach.py`:
   ```python
   # БЫЛО: 5 запросов
   session = await dao.get_active_session(user_id)
   answers = await dao.get_session_answers(session_id)
   # ...

   # СТАНЕТ: 1 запрос
   context = await dao.get_full_context(user_id)
   # Все данные в одном объекте
   ```

3. **Добавлю кэширование** (5 минут):
   ```python
   @cache(ttl=300)  # 5 minutes
   async def get_full_context(user_id):
       return await dao.get_full_context(user_id)
   ```

4. **Benchmark**:
   - Измерю latency до/после
   - Target: <50ms (было 150ms)

#### Критерии приемки
- [ ] SQL функция создана и протестирована
- [ ] ChatCoach использует новый метод
- [ ] Latency <50ms (3x improvement)
- [ ] Cache работает (hit rate >70%)
- [ ] Нет регрессии в функциональности

#### Файлы которые изменю
- `selfology_bot/database/onboarding_dao.py` (новый метод)
- `services/chat_coach.py` (упрощение context assembly)
- `core/cache.py` (новый файл - cache decorator)

---

### ЗАДАЧА 5: Multi-Vector Facets
**Приоритет**: P2 (optimization)
**Время**: 3-5 дней
**Параллельность**: После Задачи 1
**Риск**: Medium

#### Проблема
Сейчас 1 вектор на всю личность (1536D):
- Update требует пересчета всего вектора ($$)
- Нельзя искать только по "эмоциям" или только по "целям"
- Нет гранулярности

#### Что я сделаю
1. **Создам 6 Qdrant коллекций** (по 512D каждая):
   - `personality_identity` - "Кто я?"
   - `personality_emotions` - "Что чувствую?"
   - `personality_goals` - "Куда иду?"
   - `personality_barriers` - "Что мешает?"
   - `personality_skills` - "Что умею?"
   - `personality_relationships` - "Кто важен?"

2. **Обновлю** `selfology_bot/analysis/embedding_creator.py`:
   ```python
   async def create_personality_vectors(user_id, analysis_result):
       # Разделяю на 6 facets
       facets = extract_facets(analysis_result)

       # Создаю 6 embeddings параллельно
       embeddings = await asyncio.gather(
           embed(facets['identity']),
           embed(facets['emotions']),
           # ...
       )

       # Сохраняю в 6 коллекций
       await save_multi_vector(user_id, embeddings)
   ```

3. **Targeted search** в ChatCoach:
   ```python
   # Когда пользователь спрашивает про цели
   if query_about == "goals":
       results = await qdrant.search(
           collection="personality_goals",  # Только цели
           vector=embed(query)
       )
   ```

4. **Incremental updates**:
   ```python
   # Обновляем только измененный facet
   if answer_domain == "EMOTIONS":
       update_vector("personality_emotions")
       # Остальные 5 векторов не трогаем
   ```

#### Критерии приемки
- [ ] 6 коллекций созданы в Qdrant
- [ ] EmbeddingCreator создает multi-vector
- [ ] Targeted search работает
- [ ] Partial updates работают
- [ ] Cost reduction: 83% (измерено)

#### Файлы которые изменю
- `selfology_bot/analysis/embedding_creator.py` (core logic)
- `services/chat_coach.py` (targeted search)
- `data_access/vector_dao.py` (multi-vector operations)
- `scripts/migrate_to_multivector.py` (новый - миграция existing data)

---

### ЗАДАЧА 6: Incremental Embedding Updates
**Приоритет**: P3 (cost optimization)
**Время**: 2-3 дня
**Параллельность**: После Задачи 5
**Риск**: Medium

#### Проблема
При каждом новом ответе пересчитываем весь вектор:
```python
# 50 ответов → create embedding from all 50
embedding = embed(all_50_answers)  # Expensive!
```

#### Что я сделаю
1. **Weighted averaging** вместо full re-embedding:
   ```python
   async def update_embedding(user_id, new_answer):
       # Получаем старый вектор
       old_vector = await get_vector(user_id)

       # Создаем embedding только для нового ответа
       new_vector = await embed(new_answer)  # Cheap!

       # Weighted average (90% old + 10% new)
       updated_vector = 0.9 * old_vector + 0.1 * new_vector

       # Normalize
       updated_vector = normalize(updated_vector)

       return updated_vector
   ```

2. **Adaptive weighting**:
   - Первые 10 ответов: 50/50 (новое важнее)
   - 10-50 ответов: 80/20
   - 50+ ответов: 95/5 (стабилизация)

3. **Full recalc trigger**:
   - Каждые N ответов (например 50)
   - Или по требованию (если drift detection)

4. **Измерю cost savings**:
   - Before: $0.00002 per answer
   - After: $0.000002 per answer
   - Target: 90% reduction

#### Критерии приемки
- [ ] Incremental update работает
- [ ] Качество не деградировало (cosine similarity check)
- [ ] Cost reduction: 90%
- [ ] Full recalc срабатывает корректно

#### Файлы которые изменю
- `selfology_bot/analysis/embedding_creator.py` (incremental logic)
- `data_access/vector_dao.py` (get/update operations)
- `tests/test_incremental_embeddings.py` (новый файл)

---

### ЗАДАЧА 7: Monitoring & Metrics
**Приоритет**: P2 (observability)
**Время**: 2 дня
**Параллельность**: Можно параллельно с любой задачей
**Риск**: Low

#### Проблема
Нет visibility в performance и cost:
- Сколько стоят embeddings?
- Какой latency у semantic search?
- Cache hit rate?

#### Что я сделаю
1. **Создам metrics collection**:
   ```python
   # Prometheus metrics
   embedding_cost = Counter('embedding_cost_usd')
   semantic_search_latency = Histogram('semantic_search_ms')
   cache_hit_rate = Gauge('cache_hit_rate_percent')
   context_assembly_time = Histogram('context_assembly_ms')
   ```

2. **Dashboard** (Grafana или simple Flask):
   - Real-time metrics
   - Cost tracking
   - Performance graphs
   - Alerts (latency >100ms, cost spike)

3. **Logging**:
   ```python
   logger.info("semantic_search",
       user_id=user_id,
       latency_ms=latency,
       results_count=len(results),
       collection="chat_messages"
   )
   ```

4. **Weekly reports**:
   - Email summary: costs, performance, issues
   - Recommendations for optimization

#### Критерии приемки
- [ ] Metrics собираются
- [ ] Dashboard работает
- [ ] Alerts настроены
- [ ] Weekly report генерируется

#### Файлы которые изменю
- `core/metrics.py` (новый файл)
- `services/chat_coach.py` (добавить metrics)
- `selfology_bot/analysis/embedding_creator.py` (добавить metrics)
- `scripts/generate_weekly_report.py` (новый файл)

---

### ЗАДАЧА 8: Documentation & Tests
**Приоритет**: P2 (quality)
**Время**: 2-3 дня
**Параллельность**: На протяжении всех задач
**Риск**: Low

#### Что я сделаю
1. **Update CLAUDE.md**:
   - Новая архитектура
   - Примеры использования
   - Troubleshooting guide

2. **API Documentation**:
   - Swagger/OpenAPI для новых endpoints
   - Examples для каждого endpoint

3. **Tests** (target: 80% coverage):
   - Unit tests для каждой новой функции
   - Integration tests для critical paths
   - Performance tests (benchmarks)

4. **Migration guides**:
   - Для разработчиков
   - Rollback procedures
   - Troubleshooting

#### Критерии приемки
- [ ] CLAUDE.md обновлен
- [ ] API docs созданы
- [ ] Test coverage >80%
- [ ] Migration guides готовы

#### Файлы которые изменю/создам
- `CLAUDE.md` (update)
- `docs/API_REFERENCE.md` (новый)
- `docs/MIGRATION_GUIDE.md` (update)
- `tests/` (множество новых тестов)

---

## 🔄 ПАРАЛЛЕЛЬНОСТЬ И ЗАВИСИМОСТИ

### Можно запускать параллельно:

#### Блок A (Backend Focus)
- **Задача 2**: Questions → PostgreSQL
- **Задача 7**: Monitoring

#### Блок B (AI/Vectors Focus)
- **Задача 1**: Fix Semantic Search ⭐⭐ КРИТИЧНО
- **Задача 7**: Monitoring

#### Блок C (После Блока A и B)
- **Задача 3**: Big Five Denormalization (нужна Задача 2)
- **Задача 5**: Multi-Vector Facets (нужна Задача 1)

#### Блок D (После Блока C)
- **Задача 4**: Smart Context (нужна Задача 3)
- **Задача 6**: Incremental Updates (нужна Задача 5)

#### Блок E (Ongoing)
- **Задача 8**: Documentation (на протяжении всех задач)

### Граф зависимостей:

```
┌─────────────┐     ┌─────────────┐
│  Задача 1   │     │  Задача 2   │
│   Semantic  │     │  Questions  │
│   Search    │     │     → DB    │
└──────┬──────┘     └──────┬──────┘
       │                   │
       │                   ▼
       │            ┌─────────────┐
       │            │  Задача 3   │
       │            │  Big Five   │
       │            └──────┬──────┘
       │                   │
       ▼                   ▼
┌─────────────┐     ┌─────────────┐
│  Задача 5   │     │  Задача 4   │
│ Multi-Vector│     │   Context   │
└──────┬──────┘     └─────────────┘
       │
       ▼
┌─────────────┐
│  Задача 6   │
│ Incremental │
└─────────────┘

     ┌─────────────┐
     │  Задача 7   │  ← Можно параллельно
     │ Monitoring  │     с любой задачей
     └─────────────┘

     ┌─────────────┐
     │  Задача 8   │  ← Ongoing на
     │    Docs     │     протяжении всех
     └─────────────┘
```

---

## ⏱️ TIMELINE

### Вариант 1: Последовательное выполнение (1 человек)
**Общее время**: ~20 рабочих дней (4 недели)

- Week 1: Задачи 1, 2, 7
- Week 2: Задачи 3, 5
- Week 3: Задачи 4, 6
- Week 4: Задача 8, тестирование, deploy

### Вариант 2: Параллельное выполнение (2 человека)
**Общее время**: ~12 рабочих дней (2.5 недели)

**Person A (Backend focus)**:
- Week 1: Задачи 2, 7
- Week 2: Задача 3, 4

**Person B (AI/Vectors focus)**:
- Week 1: Задачи 1, 7
- Week 2: Задачи 5, 6

**Both**:
- Week 3: Задача 8, integration testing, deploy

### Вариант 3: Минимальный критичный путь (quick wins)
**Общее время**: ~5 рабочих дней (1 неделя)

- Day 1-2: **Задача 1** (Fix Semantic Search) ⭐⭐
- Day 3-4: **Задача 2** (Questions → DB)
- Day 5: Testing + Deploy

**Результат**: Semantic search работает + 5x быстрее QuestionRouter

---

## 💰 COST ESTIMATE

### Development Time
- Последовательно: 20 дней
- Параллельно: 12 дней
- Quick wins: 5 дней

### Infrastructure Cost (monthly)
- Qdrant: ~$0 (self-hosted)
- OpenAI API (embeddings):
  - Current: ~$50/month (693 questions × N users)
  - After optimization: ~$8/month (83% reduction)
  - **Savings**: $42/month

### Performance Gains (value)
- AI relevance: 70% → 90% (+20%)
- Context speed: 280ms → <100ms (3x faster)
- QuestionRouter: 10ms → 2ms (5x faster)
- **Пользовательский опыт**: значительно лучше

---

## ⚠️ РИСКИ

### Риск 1: Semantic search миграция
**Вероятность**: Medium
**Impact**: High
**Митигация**:
- Backfill script с retry logic
- Validation перед deploy
- Rollback plan (switch back to old collection)

### Риск 2: PostgreSQL performance
**Вероятность**: Low
**Impact**: Medium
**Митигация**:
- Benchmark до/после
- Query optimization
- Индексы на критичных полях

### Риск 3: Multi-vector качество
**Вероятность**: Medium
**Impact**: Medium
**Митигация**:
- A/B тест (старый vs новый подход)
- Cosine similarity validation
- Rollback к single vector если quality drop

### Риск 4: Cost spike
**Вероятность**: Low
**Impact**: Medium
**Митигация**:
- Rate limiting на embeddings
- Monitoring alerts
- Budget cap

---

## 📊 SUCCESS METRICS

### Performance
- [ ] QuestionRouter <2ms (target: 5x improvement)
- [ ] Context assembly <100ms (target: 3x improvement)
- [ ] Semantic search <50ms (target: working!)
- [ ] Cache hit rate >70%

### Cost
- [ ] Embedding cost -83% (target)
- [ ] Update cost -90% (target)

### Quality
- [ ] AI relevance >90% (user feedback)
- [ ] Context completeness >95%
- [ ] Semantic search accuracy >80%
- [ ] Zero regression in existing features

### Engineering
- [ ] Test coverage >80%
- [ ] Zero production incidents
- [ ] Documentation complete
- [ ] All migrations reversible

---

## 🚀 РЕКОМЕНДАЦИЯ

### Мой совет (Claude):

**START WITH ВАРИАНТ 3: Quick Wins (1 неделя)**

Почему:
1. ✅ **Задача 1** (Semantic Search) - КРИТИЧНО, сейчас не работает
2. ✅ **Задача 2** (Questions → DB) - быстрый win, 5x performance
3. ✅ Низкий риск, высокий impact
4. ✅ Можно оценить подход перед full commitment

**После Quick Wins**:
- Измерим результаты
- Если OK → продолжим с Задачами 3-6
- Если проблемы → пересмотрим план

### Alternative: Минимальный старт

Если хочешь протестировать подход еще быстрее:

**Только Задача 1** (2 дня):
- Fix semantic search
- Immediate impact на AI relevance
- Оцениваем качество результата

---

## ✅ CHECKLIST ДЛЯ УТВЕРЖДЕНИЯ

Пожалуйста, подтверди:

- [ ] **Согласен с общим планом** (8 задач)
- [ ] **Выбран вариант timeline**:
  - [ ] Вариант 1: Последовательно (4 недели)
  - [ ] Вариант 2: Параллельно (2.5 недели)
  - [ ] Вариант 3: Quick wins (1 неделя)
  - [ ] Alternative: Только Задача 1 (2 дня)

- [ ] **Приоритеты ОК**:
  - [ ] Задача 1 (Semantic Search) - P0 ⭐⭐
  - [ ] Задача 2 (Questions DB) - P1 ⭐
  - [ ] Задача 3 (Big Five) - P1 ⭐
  - [ ] Остальные задачи - P2/P3

- [ ] **Риски приемлемы**
- [ ] **Budget OK** (в основном dev time, API cost снизится)
- [ ] **Готов начать**

---

## 📝 ПОСЛЕ УТВЕРЖДЕНИЯ

Как только дашь зеленый свет:

1. Создам Git ветку: `feature/optimize-onboarding-architecture`
2. Начну с утвержденного варианта (рекомендую Вариант 3)
3. Буду отчитываться после каждой задачи
4. Создам PR для review перед merge

---

## ❓ ВОПРОСЫ ДЛЯ ОБСУЖДЕНИЯ

1. **Timeline**: Какой вариант предпочитаешь? (1/2/3 или Alternative)

2. **Приоритеты**: Согласен что Задача 1 - самая критичная?

3. **Ресурсы**: Будешь делать сам или нужна помощь? (можем параллелить)

4. **Testing**: Dev environment для тестов есть? Или делаем на production с feature flags?

5. **Backup**: Подтверди что есть backup БД перед миграциями

6. **Rollback**: Лимит времени для rollback если что-то пойдет не так?

---

**Жду твоего решения чтобы начать! 🚀**

*Claude Code, готов к работе*
