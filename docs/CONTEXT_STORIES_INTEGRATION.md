# Context Stories Integration Guide

## Обзор решения

Архитектурное решение для хранения произвольных рассказов пользователя ("Расскажите о себе то, что считаете важным...") в системе онбординга.

### Принципы дизайна

1. **Отдельная таблица** `user_context_stories` - семантически другой тип данных
2. **Переиспользование инфраструктуры** - анализ через `answer_analysis` с `context_story_id`
3. **Полнотекстовый поиск** - PostgreSQL GIN-индекс + tsvector для русского языка
4. **Гибкость** - поддержка разных типов контекста (не только онбординг)

---

## 1. SQL Schema

### Таблица `user_context_stories`

```sql
CREATE TABLE selfology.user_context_stories (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    session_id INTEGER REFERENCES selfology.onboarding_sessions(id) ON DELETE SET NULL,

    -- Story content
    story_text TEXT NOT NULL,
    story_length INTEGER NOT NULL,

    -- Categorization
    story_type VARCHAR(30) DEFAULT 'onboarding_intro',  -- onboarding_intro, crisis_context, goal_setting
    story_source VARCHAR(20) DEFAULT 'user_input',      -- user_input, bot_prompted, admin_added

    -- Metadata
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE,

    -- Full-text search vector (Russian language)
    search_vector tsvector,

    -- Additional metadata
    metadata JSONB DEFAULT '{}'
);
```

**Ключевые особенности:**
- `session_id` - опциональная связь с сессией онбординга (ON DELETE SET NULL)
- `story_type` - расширяемая категоризация (можно добавить новые типы)
- `search_vector` - автоматически обновляется триггером для полнотекстового поиска
- `metadata` - гибкий JSONB для дополнительных данных

### Расширение таблицы `answer_analysis`

```sql
ALTER TABLE selfology.answer_analysis
ADD COLUMN context_story_id INTEGER REFERENCES selfology.user_context_stories(id) ON DELETE CASCADE;

-- Constraint: либо user_answer_id, либо context_story_id
ALTER TABLE selfology.answer_analysis
ADD CONSTRAINT check_analysis_source
CHECK (
    (user_answer_id IS NOT NULL AND context_story_id IS NULL) OR
    (user_answer_id IS NULL AND context_story_id IS NOT NULL)
);
```

**Зачем:** Переиспользуем всю инфраструктуру анализа (trait_scores, emotional_state, векторизация, etc.)

### View для удобного доступа

```sql
CREATE OR REPLACE VIEW selfology.context_stories_with_analysis AS
SELECT
    cs.id as story_id,
    cs.user_id,
    cs.session_id,
    cs.story_text,
    cs.story_type,
    cs.created_at,
    aa.psychological_insights,
    aa.trait_scores,
    aa.emotional_state,
    aa.quality_score,
    aa.vectorization_status,
    aa.dp_update_status
FROM selfology.user_context_stories cs
LEFT JOIN selfology.answer_analysis aa ON aa.context_story_id = cs.id
WHERE cs.is_active = true
ORDER BY cs.created_at DESC;
```

### Полнотекстовый поиск

```sql
-- Функция для поиска с relevance scoring
CREATE FUNCTION selfology.search_user_context_stories(
    p_user_id INTEGER,
    p_search_query TEXT,
    p_limit INTEGER DEFAULT 10
)
RETURNS TABLE (
    story_id INTEGER,
    story_text TEXT,
    story_type VARCHAR(30),
    created_at TIMESTAMP,
    relevance REAL
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        cs.id,
        cs.story_text,
        cs.story_type,
        cs.created_at,
        ts_rank(cs.search_vector, plainto_tsquery('russian', p_search_query)) AS relevance
    FROM selfology.user_context_stories cs
    WHERE cs.user_id = p_user_id
        AND cs.is_active = true
        AND cs.search_vector @@ plainto_tsquery('russian', p_search_query)
    ORDER BY relevance DESC, cs.created_at DESC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;
```

---

## 2. API Methods в OnboardingDAO

### Сохранение контекстной истории

```python
async def save_context_story(
    self,
    user_id: int,
    session_id: Optional[int],
    story_text: str,
    story_type: str = 'onboarding_intro',
    story_source: str = 'user_input',
    metadata: Optional[Dict[str, Any]] = None
) -> int:
    """
    Сохранить контекстную историю пользователя

    Returns:
        ID созданной записи истории
    """
```

**Использование:**
```python
story_id = await onboarding_dao.save_context_story(
    user_id=123,
    session_id=session['id'],
    story_text="Я работаю психологом уже 5 лет...",
    story_type='onboarding_intro',
    metadata={'prompted_at_question': 3}
)
```

### Сохранение анализа контекстной истории

```python
async def save_context_story_analysis(
    self,
    context_story_id: int,
    analysis_result: Dict[str, Any]
) -> int:
    """
    Сохранить AI анализ контекстной истории

    Переиспользует всю инфраструктуру answer_analysis

    Returns:
        ID созданной записи анализа
    """
```

**Использование:**
```python
# Анализируем через AnswerAnalyzer (как обычный ответ)
analysis_result = await answer_analyzer.analyze_answer(
    question_data={'text': 'Расскажите о себе...', 'domain': 'IDENTITY'},
    user_answer=story_text,
    user_context={'user_id': user_id, 'session_id': session_id}
)

# Сохраняем с привязкой к context_story_id
analysis_id = await onboarding_dao.save_context_story_analysis(
    context_story_id=story_id,
    analysis_result=analysis_result
)
```

### Получение историй пользователя

```python
async def get_user_context_stories(
    self,
    user_id: int,
    story_type: Optional[str] = None,
    limit: int = 10,
    include_analysis: bool = True
) -> List[Dict[str, Any]]:
    """
    Получить контекстные истории пользователя

    Args:
        include_analysis: Включить результаты AI анализа
    """
```

**Использование:**
```python
# Все истории с анализом
stories = await onboarding_dao.get_user_context_stories(
    user_id=123,
    include_analysis=True
)

# Только истории из онбординга
onboarding_stories = await onboarding_dao.get_user_context_stories(
    user_id=123,
    story_type='onboarding_intro'
)
```

### Полнотекстовый поиск

```python
async def search_context_stories(
    self,
    user_id: int,
    search_query: str,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """
    Полнотекстовый поиск по контекстным историям

    Returns:
        Список с relevance score
    """
```

**Использование:**
```python
# Поиск по ключевым словам
results = await onboarding_dao.search_context_stories(
    user_id=123,
    search_query='работа стресс'
)

for result in results:
    print(f"Story {result['story_id']}: relevance={result['relevance']}")
```

### Получение истории для сессии

```python
async def get_session_context_story(
    self,
    session_id: int
) -> Optional[Dict[str, Any]]:
    """
    Получить контекстную историю для сессии онбординга
    """
```

---

## 3. Интеграция в поток онбординга

### Шаг 1: Показать вопрос между вопросами 1-5

```python
# В OnboardingOrchestrator
async def handle_user_answer(self, user_id: int, answer_text: str):
    session = await self.dao.get_active_session(user_id)

    # Проверяем, нужно ли показать контекстный вопрос
    if session['questions_answered'] == 2:  # После 2-го вопроса
        # Проверяем, не задавали ли уже
        existing_story = await self.dao.get_session_context_story(session['id'])

        if not existing_story:
            # Показываем специальный вопрос
            await self.show_context_story_prompt(user_id, session['id'])
            return

    # Обычная логика онбординга
    # ...
```

### Шаг 2: Обработка ответа на контекстный вопрос

```python
async def handle_context_story_answer(
    self,
    user_id: int,
    session_id: int,
    story_text: str
):
    """Обработка произвольного рассказа пользователя"""

    # 1. Сохраняем историю
    story_id = await self.dao.save_context_story(
        user_id=user_id,
        session_id=session_id,
        story_text=story_text,
        story_type='onboarding_intro',
        story_source='bot_prompted'
    )

    # 2. Отправляем мгновенный фидбек
    await self.send_instant_feedback(user_id, "Спасибо, я вас услышал...")

    # 3. Запускаем фоновый анализ (как для обычных ответов)
    asyncio.create_task(
        self._analyze_context_story_background(
            story_id=story_id,
            user_id=user_id,
            story_text=story_text
        )
    )

    # 4. Продолжаем онбординг
    await self.continue_onboarding(user_id)
```

### Шаг 3: Фоновый анализ (переиспользуем AnswerAnalyzer)

```python
async def _analyze_context_story_background(
    self,
    story_id: int,
    user_id: int,
    story_text: str
):
    """Фоновый AI анализ контекстной истории"""

    try:
        # Используем AnswerAnalyzer как для обычных ответов
        analysis_result = await self.answer_analyzer.analyze_answer(
            question_data={
                'id': 'context_intro',
                'text': 'Расскажите о себе то, что считаете важным для меня как для вашего коуча',
                'domain': 'IDENTITY',
                'depth_level': 'CONSCIOUS',
                'energy': 'NEUTRAL'
            },
            user_answer=story_text,
            user_context={
                'user_id': user_id,
                'session_id': None,  # Не нужен для контекстных историй
                'previous_answers': []
            }
        )

        # Сохраняем анализ
        analysis_id = await self.dao.save_context_story_analysis(
            context_story_id=story_id,
            analysis_result=analysis_result
        )

        # Векторизация (через EmbeddingCreator)
        await self._vectorize_context_story(story_id, analysis_id, story_text, analysis_result)

        # Обновление Digital Personality
        await self._update_dp_from_context_story(user_id, analysis_result)

        logger.info(f"✅ Context story {story_id} analyzed and integrated")

    except Exception as e:
        logger.error(f"❌ Error analyzing context story {story_id}: {e}")
```

### Шаг 4: Векторизация (переиспользуем EmbeddingCreator)

```python
async def _vectorize_context_story(
    self,
    story_id: int,
    analysis_id: int,
    story_text: str,
    analysis_result: Dict[str, Any]
):
    """Векторизация контекстной истории в Qdrant"""

    try:
        # Используем EmbeddingCreator как для обычных ответов
        await self.embedding_creator.create_and_store_embeddings(
            user_id=user_id,
            content_type='context_story',  # Новый тип контента
            content_id=story_id,
            text_content=story_text,
            metadata={
                'story_type': 'onboarding_intro',
                'analysis_id': analysis_id,
                'emotional_state': analysis_result['psychological_analysis']['emotional_assessment']['primary'],
                'trait_scores': analysis_result['personality_traits']
            }
        )

        # Обновляем статус векторизации
        await self.dao.update_vectorization_status(
            analysis_id=analysis_id,
            status='success'
        )

    except Exception as e:
        await self.dao.update_vectorization_status(
            analysis_id=analysis_id,
            status='failed',
            error=str(e)
        )
```

---

## 4. Использование в Digital Personality

### Включение контекстных историй в профиль личности

```python
# В DigitalPersonalityDAO
async def get_user_full_context(self, user_id: int) -> Dict[str, Any]:
    """Получить полный контекст пользователя для AI анализа"""

    # Обычные ответы на вопросы
    answers = await self.get_user_answers_with_analysis(user_id)

    # Контекстные истории
    stories = await self.onboarding_dao.get_user_context_stories(
        user_id=user_id,
        include_analysis=True
    )

    return {
        'structured_answers': answers,  # Ответы на конкретные вопросы
        'context_stories': stories,     # Произвольные рассказы
        'combined_insights': self._merge_insights(answers, stories)
    }
```

### Поиск релевантного контекста для коучинга

```python
async def find_relevant_context_for_question(
    self,
    user_id: int,
    current_topic: str
) -> List[Dict[str, Any]]:
    """Найти релевантные истории пользователя по теме"""

    # Полнотекстовый поиск по контекстным историям
    relevant_stories = await self.onboarding_dao.search_context_stories(
        user_id=user_id,
        search_query=current_topic,
        limit=3
    )

    return relevant_stories
```

---

## 5. Примеры использования в Telegram боте

### Обработчик контекстного вопроса

```python
# В handlers/onboarding.py
@router.message(OnboardingStates.WAITING_CONTEXT_STORY)
async def handle_context_story(message: types.Message, state: FSMContext):
    """Обработка произвольного рассказа пользователя"""

    user_id = message.from_user.id
    story_text = message.text

    # Получаем активную сессию
    session = await onboarding_dao.get_active_session(user_id)

    # Валидация длины
    if len(story_text) < 20:
        await message.answer(
            "Расскажите немного подробнее - это поможет мне лучше понять вас 🙏"
        )
        return

    # Обрабатываем через orchestrator
    await orchestrator.handle_context_story_answer(
        user_id=user_id,
        session_id=session['id'],
        story_text=story_text
    )

    # Переходим к следующему вопросу
    await state.set_state(OnboardingStates.ANSWERING_QUESTIONS)
```

### Текст вопроса в шаблоне

```json
// templates/ru/onboarding.json
{
  "context_story_prompt": {
    "text": "Расскажите о себе то, что считаете важным для меня как для вашего коуча.\n\nЭто может быть всё что угодно - ваша история, текущая ситуация, мечты, переживания... Я слушаю 🤍",
    "placeholder": "Напишите свободно, как на душе...",
    "skip_text": "Пропустить (не рекомендуется)"
  }
}
```

---

## 6. Мониторинг и статистика

### Отслеживание использования

```python
async def get_context_stories_stats(self) -> Dict[str, Any]:
    """Статистика по контекстным историям"""

    async with self.db.get_connection() as conn:
        stats = await conn.fetchrow("""
            SELECT
                COUNT(*) as total_stories,
                COUNT(DISTINCT user_id) as users_with_stories,
                AVG(story_length) as avg_length,
                COUNT(*) FILTER (WHERE is_active = true) as active_stories,
                COUNT(aa.id) as analyzed_stories,
                COUNT(aa.id) FILTER (WHERE aa.vectorization_status = 'success') as vectorized_stories
            FROM user_context_stories cs
            LEFT JOIN answer_analysis aa ON aa.context_story_id = cs.id
        """)

        return dict(stats)
```

---

## 7. Миграция

### Применение миграции

```bash
# Подключиться к PostgreSQL
docker exec -it n8n-postgres psql -U postgres -d n8n

# Применить миграцию
\i /path/to/migrations/create_user_context_stories.sql

# Проверить созданные объекты
\dt selfology.user_context_stories
\d selfology.answer_analysis
\dv selfology.context_stories_with_analysis
```

### Rollback (если нужно)

```sql
-- Удалить view
DROP VIEW IF EXISTS selfology.context_stories_with_analysis;

-- Удалить функцию поиска
DROP FUNCTION IF EXISTS selfology.search_user_context_stories;

-- Удалить триггер и функцию
DROP TRIGGER IF EXISTS trigger_update_context_story_search_vector ON selfology.user_context_stories;
DROP FUNCTION IF EXISTS selfology.update_context_story_search_vector;

-- Удалить constraint из answer_analysis
ALTER TABLE selfology.answer_analysis DROP CONSTRAINT IF EXISTS check_analysis_source;

-- Удалить колонку
ALTER TABLE selfology.answer_analysis DROP COLUMN IF EXISTS context_story_id;

-- Удалить таблицу
DROP TABLE IF EXISTS selfology.user_context_stories CASCADE;
```

---

## 8. Best Practices

### Когда показывать контекстный вопрос

1. **После 2-3 вопросов** - пользователь уже вовлечён
2. **Один раз на сессию** - не перегружаем
3. **Опциональный skip** - не всем комфортно делиться сразу
4. **Без ограничения длины** - пусть пишут сколько хотят

### Обработка длинных текстов

```python
# Разбивка на chunks для векторизации
if len(story_text) > 3000:  # OpenAI embedding limit
    chunks = split_into_chunks(story_text, max_length=2000)
    for chunk in chunks:
        await embedding_creator.create_embeddings(chunk)
```

### Privacy

```python
# Контекстные истории - самые личные данные
# Особое внимание к безопасности:

# 1. Логирование без содержимого
logger.info(f"Context story {story_id} saved (length: {len(story_text)})")
# НЕ: logger.info(f"Story text: {story_text}")

# 2. Деактивация вместо удаления (для audit trail)
await dao.deactivate_context_story(story_id)

# 3. Шифрование в будущем (опционально)
# encrypted_text = encrypt(story_text, user_key)
```

---

## Summary

**Что получили:**

1. ✅ Отдельная таблица `user_context_stories` для произвольных рассказов
2. ✅ Переиспользование всей инфраструктуры `answer_analysis`
3. ✅ Полнотекстовый поиск с русским языком через PostgreSQL GIN
4. ✅ 8 методов API в `OnboardingDAO` для работы с историями
5. ✅ Интеграция с AnswerAnalyzer, EmbeddingCreator, Digital Personality
6. ✅ View и функции для удобного доступа
7. ✅ Мягкое удаление и audit trail

**Файлы:**
- `/home/ksnk/n8n-enterprise/projects/selfology/migrations/create_user_context_stories.sql` - SQL миграция
- `/home/ksnk/n8n-enterprise/projects/selfology/selfology_bot/database/onboarding_dao.py` - обновлённый DAO с методами
- `/home/ksnk/n8n-enterprise/projects/selfology/docs/CONTEXT_STORIES_INTEGRATION.md` - эта документация
