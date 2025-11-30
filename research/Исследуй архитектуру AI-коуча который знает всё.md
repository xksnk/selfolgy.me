# Исследуй архитектуру AI-коуча который "знает всё" о пользователе

## Контекст

Приложение **Selfology** - AI психологический коуч в Telegram.

**Что собрано о пользователе:**
- 150+ ответов на вопросы онбординга
- 72 цели (с типом и приоритетом)
- 62 барьера (с типом и влиянием)
- 47 интересов
- 33 ценности
- Big Five personality traits
- Последние эмоциональные состояния

**Технический стек:**
- PostgreSQL (structured data, JSONB)
- Qdrant (vector embeddings)
- Claude/GPT-4 для генерации

**Главный вопрос:** Как сделать коуча который ДЕЙСТВИТЕЛЬНО знает пользователя и отвечает персонализированно?

---

## 1. ПАМЯТЬ И КОНТЕКСТ

### Как современные AI companions реализуют "знание" о пользователе?

**Replika:**
- Episodic memory: хранит конкретные разговоры
- Semantic memory: извлекает факты ("у пользователя есть кот")
- Memory diary: ежедневные summaries
- Retrieval: ищет релевантные воспоминания по контексту

**Character.AI:**
- Definition + Description (статичный контекст)
- Conversation history (скользящее окно)
- Long-term memory через summarization
- No persistent memory между сессиями (privacy)

**Pi by Inflection:**
- "Memory" feature - явное сохранение фактов
- User может редактировать что Pi помнит
- Structured facts + conversational context

### Memory Architectures

```
┌─────────────────────────────────────────────────────────┐
│                    MEMORY TYPES                          │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  EPISODIC MEMORY          SEMANTIC MEMORY               │
│  ─────────────────       ─────────────────              │
│  Конкретные события      Обобщённые факты               │
│  "Вчера ты сказал..."    "Ты журналист"                 │
│  Temporal, detailed      Atemporal, abstract            │
│  High storage cost       Compact                        │
│                                                          │
│  PROCEDURAL MEMORY       WORKING MEMORY                 │
│  ─────────────────       ─────────────────              │
│  Как общаться с user     Текущий контекст               │
│  Паттерны поведения      Последние N сообщений          │
│  Стиль коммуникации      Active reasoning               │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

### RAG для персональных данных

**Retrieval-Augmented Generation подход:**

```python
# Псевдокод RAG для персональных данных

async def get_relevant_context(user_id: int, user_message: str) -> str:
    """
    Вместо загрузки ВСЕГО - ищем релевантное.
    """

    # 1. Embed текущее сообщение
    query_embedding = embed(user_message)

    # 2. Поиск в разных коллекциях
    relevant_goals = qdrant.search(
        collection="user_goals",
        query_vector=query_embedding,
        filter={"user_id": user_id},
        limit=5
    )

    relevant_barriers = qdrant.search(
        collection="user_barriers",
        query_vector=query_embedding,
        filter={"user_id": user_id},
        limit=5
    )

    relevant_answers = qdrant.search(
        collection="user_answers",
        query_vector=query_embedding,
        filter={"user_id": user_id},
        limit=3
    )

    # 3. Формируем контекст
    context = f"""
    Релевантные цели пользователя:
    {format_goals(relevant_goals)}

    Релевантные барьеры:
    {format_barriers(relevant_barriers)}

    Похожие прошлые ответы:
    {format_answers(relevant_answers)}
    """

    return context
```

**Преимущества RAG:**
- Экономия токенов (не грузим всё)
- Релевантность (только нужное)
- Масштабируемость (работает с любым объёмом данных)

**Недостатки RAG:**
- Может пропустить важное (если embedding не нашёл)
- Latency (дополнительный запрос к vector DB)
- Complexity (нужно поддерживать индексы)

---

## 2. СТРАТЕГИИ ЗАГРУЗКИ ДАННЫХ

### Стратегия A: Full Context Stuffing

```
Загружаем ВСЁ в каждый промпт:
- Все 72 цели
- Все 62 барьера
- Все интересы, ценности
- Последние 20 ответов

Плюсы: AI видит полную картину
Минусы: 10K+ токенов на контекст, дорого
```

### Стратегия B: Pre-summarization (Досье)

```python
# Создаём "досье" заранее, обновляем после новых ответов

class UserDossier:
    """
    AI-сгенерированное резюме личности.
    Обновляется после каждых 5 новых ответов.
    """

    summary: str  # 500-1000 токенов

    # Пример:
    """
    ДОСЬЕ ПОЛЬЗОВАТЕЛЯ:

    Журналист, 30+, не работает. Ведёт текстовые блоги.

    ГЛАВНЫЕ ЦЕЛИ:
    - Создать медиа компанию с позитивным взглядом на мир
    - Найти идеальных друзей, проводить время каждые выходные
    - Финансовая стабильность через блоги

    ГЛАВНЫЕ БАРЬЕРЫ:
    - Внутренний конфликт: "хочу страдать" vs желание радости
    - Не может ценить хорошее (защитный механизм?)
    - Тревога, страх неопределённости

    ПАТТЕРНЫ:
    - Говорит о тревоге часто (5 из 10 последних ответов)
    - Амбивалентность к успеху
    - Ищет направление в жизни

    КЛЮЧЕВЫЕ ПРОТИВОРЕЧИЯ:
    - Цель "спокойствие" vs барьер "хочу страдать"
    - Хочет друзей vs избегает людей
    """
```

**Промпт для генерации досье:**

```
Проанализируй данные о пользователе и создай психологическое досье.

ДАННЫЕ:
{all_goals}
{all_barriers}
{all_values}
{recent_answers}

ФОРМАТ ДОСЬЕ:
1. КТО (демография, профессия, ситуация) - 2 предложения
2. ГЛАВНЫЕ ЦЕЛИ (топ-3 с объяснением почему важны)
3. ГЛАВНЫЕ БАРЬЕРЫ (топ-3 с гипотезой о причинах)
4. ПАТТЕРНЫ (что повторяется в ответах)
5. ПРОТИВОРЕЧИЯ (где цели конфликтуют с барьерами)
6. ГИПОТЕЗА (психологическая динамика одним абзацем)

Будь конкретен, используй цитаты из ответов пользователя.
Максимум 500 слов.
```

### Стратегия C: Hierarchical Memory

```
УРОВЕНЬ 1: Core Identity (всегда в промпте)
├── Big Five traits
├── Главная цель жизни
├── Главный барьер
└── Текущая ситуация (1-2 предложения)

УРОВЕНЬ 2: Domain-Specific (загружается по контексту)
├── Если про работу → goals/barriers про карьеру
├── Если про отношения → relationships data
├── Если про эмоции → emotional patterns
└── Semantic search определяет домен

УРОВЕНЬ 3: Episodic (по запросу)
├── Конкретные прошлые ответы
├── История разговоров
└── Временные паттерны
```

### Стратегия D: Hybrid (Рекомендуемая)

```python
async def build_context(user_id: int, message: str) -> str:
    """
    Гибридный подход:
    1. Всегда: Core Identity (досье)
    2. + Semantic search для релевантного
    3. + Последние 3 сообщения
    """

    # 1. Загружаем досье (кэшированное)
    dossier = await get_cached_dossier(user_id)  # ~500 tokens

    # 2. Ищем релевантное
    relevant = await semantic_search(user_id, message)  # ~300 tokens

    # 3. Последние сообщения
    recent = await get_recent_messages(user_id, limit=3)  # ~200 tokens

    # Итого: ~1000 tokens контекста вместо 10K+

    return f"""
    === ДОСЬЕ ===
    {dossier}

    === РЕЛЕВАНТНОЕ ===
    {relevant}

    === ПОСЛЕДНИЕ СООБЩЕНИЯ ===
    {recent}
    """
```

---

## 3. ПЕРСОНАЛИЗАЦИЯ ОТВЕТОВ

### Адаптация под Big Five

```python
def adapt_response_style(big_five: dict) -> dict:
    """
    Настройки стиля общения под Big Five.
    """

    style = {}

    # OPENNESS (0-1)
    if big_five['openness'] > 0.7:
        style['approach'] = 'creative, exploratory'
        style['questions'] = 'open-ended, philosophical'
        style['language'] = 'metaphors, abstract concepts'
    else:
        style['approach'] = 'practical, concrete'
        style['questions'] = 'specific, actionable'
        style['language'] = 'clear, direct'

    # CONSCIENTIOUSNESS
    if big_five['conscientiousness'] > 0.7:
        style['structure'] = 'step-by-step, organized'
        style['format'] = 'lists, timelines, plans'
    else:
        style['structure'] = 'flexible, flow-based'
        style['format'] = 'narrative, conversational'

    # EXTRAVERSION
    if big_five['extraversion'] > 0.7:
        style['energy'] = 'enthusiastic, expressive'
        style['length'] = 'longer, more detailed'
    else:
        style['energy'] = 'calm, measured'
        style['length'] = 'concise, space for reflection'

    # AGREEABLENESS
    if big_five['agreeableness'] > 0.7:
        style['tone'] = 'warm, supportive, validating'
        style['challenge'] = 'gentle, indirect'
    else:
        style['tone'] = 'direct, honest'
        style['challenge'] = 'straightforward'

    # NEUROTICISM
    if big_five['neuroticism'] > 0.7:
        style['safety'] = 'high - more reassurance'
        style['pacing'] = 'slower, check-ins'
        style['depth'] = 'careful progression'
    else:
        style['safety'] = 'standard'
        style['pacing'] = 'normal'
        style['depth'] = 'can go deeper faster'

    return style
```

### Создание ощущения "Коуч меня знает"

**Техники:**

1. **Explicit References**
```
"Ты говорил, что хочешь создать медиа компанию - как это связано с текущей ситуацией?"
```

2. **Pattern Acknowledgment**
```
"Замечаю, что тема тревоги появляется часто. Это важный сигнал."
```

3. **Contradiction Surfacing**
```
"Интересно: ты хочешь спокойствия, но сам говоришь что 'хочешь страдать'. Что за этим стоит?"
```

4. **Progress Tracking**
```
"Неделю назад ты был в таком же состоянии, но потом нашёл выход. Что тогда помогло?"
```

5. **Value Alignment**
```
"Это решение соответствует твоей ценности 'позитивный взгляд на мир'?"
```

### Промпт для персонализированного ответа

```
Ты AI-коуч. Отвечай пользователю КАК БУДТО ТЫ ЕГО ХОРОШО ЗНАЕШЬ.

ПРАВИЛА:
1. УПОМИНАЙ конкретные факты из досье (цели, барьеры, ценности)
2. СВЯЗЫВАЙ текущее сообщение с паттернами пользователя
3. ИСПОЛЬЗУЙ стиль общения адаптированный под его Big Five
4. ЗАДАВАЙ вопросы которые показывают знание контекста
5. НЕ притворяйся что знаешь больше чем в досье

ДОСЬЕ:
{dossier}

СТИЛЬ ОБЩЕНИЯ:
{style_instructions}

СООБЩЕНИЕ ПОЛЬЗОВАТЕЛЯ:
{message}

Ответь 2-3 предложениями. Обязательно свяжи с чем-то из досье.
```

---

## 4. АРХИТЕКТУРА СИСТЕМЫ

### Multi-Agent Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    USER MESSAGE                          │
└─────────────────────────┬───────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│                 CONTEXT BUILDER                          │
│  ─────────────────────────────────────────────────────  │
│  1. Load cached dossier                                  │
│  2. Semantic search for relevant data                    │
│  3. Get recent conversation history                      │
│  4. Build unified context                                │
└─────────────────────────┬───────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│                 MESSAGE ANALYZER                         │
│  ─────────────────────────────────────────────────────  │
│  - Detect intent (question, sharing, resistance)         │
│  - Identify emotional state                              │
│  - Classify domain (work, relationships, emotions)       │
│  - Check for crisis signals                              │
│  Model: GPT-4o-mini (fast, cheap)                       │
└─────────────────────────┬───────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│                 RESPONSE GENERATOR                       │
│  ─────────────────────────────────────────────────────  │
│  - Generate personalized response                        │
│  - Apply Big Five style adaptation                       │
│  - Include relevant references to user data              │
│  Model: Claude Sonnet (quality) or GPT-4o (balance)     │
└─────────────────────────┬───────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│              PERSONALITY UPDATER (async)                 │
│  ─────────────────────────────────────────────────────  │
│  - Extract new facts from conversation                   │
│  - Update digital personality                            │
│  - Refresh dossier if needed                            │
│  - Store in PostgreSQL + Qdrant                         │
│  Model: GPT-4o-mini (background task)                   │
└─────────────────────────────────────────────────────────┘
```

### Model Routing

```python
def select_model(task: str, complexity: str) -> str:
    """
    Выбор модели под задачу.
    """

    routing = {
        # Быстрые простые задачи → Mini
        'intent_detection': 'gpt-4o-mini',
        'emotion_detection': 'gpt-4o-mini',
        'fact_extraction': 'gpt-4o-mini',

        # Качественные ответы → Sonnet/GPT-4o
        'coaching_response': 'claude-sonnet' if complexity == 'high' else 'gpt-4o',
        'dossier_generation': 'claude-sonnet',
        'contradiction_analysis': 'claude-sonnet',

        # Кризисные ситуации → лучшая модель
        'crisis_response': 'claude-sonnet',
    }

    return routing.get(task, 'gpt-4o')
```

### Caching Strategy

```python
CACHE_CONFIG = {
    'user_dossier': {
        'ttl': 3600,  # 1 час
        'invalidate_on': 'new_answer',
        'storage': 'redis'
    },

    'personality_profile': {
        'ttl': 86400,  # 24 часа
        'invalidate_on': '5_new_answers',
        'storage': 'redis'
    },

    'recent_context': {
        'ttl': 300,  # 5 минут
        'invalidate_on': 'new_message',
        'storage': 'memory'
    },

    'vector_embeddings': {
        'ttl': None,  # Permanent
        'invalidate_on': 'answer_update',
        'storage': 'qdrant'
    }
}
```

---

## 5. RESEARCH И BEST PRACTICES

### Что говорят исследования

**Therapeutic Alliance в AI (2023-2024):**
- Alliance quality предсказывает 26% variance в outcomes
- AI может достигать 0.7+ alliance score (сравнимо с людьми)
- Ключевые факторы: consistency, personalization, empathy

**Memory Impact (Character.AI research):**
- Users с persistent memory: +40% engagement
- "Feeling known" коррелирует с satisfaction (r=0.72)
- Optimal memory references: 1-2 per conversation

**Woebot (CBT-based):**
- Structured approach + personalization
- Uses "mood check-ins" для tracking
- NO long-term memory (privacy focus)
- Effectiveness: comparable to human-delivered CBT

**Wysa (ACT + CBT):**
- Anonymous by design
- Pattern detection без persistent identity
- Crisis detection система
- India-focused, 500M+ conversations

### Этические границы

```
✅ МОЖНО:
- Помнить факты которые пользователь явно сообщил
- Отслеживать паттерны для помощи
- Персонализировать стиль общения
- Напоминать о прогрессе и инсайтах

⚠️ ОСТОРОЖНО:
- Упоминать чувствительные темы без контекста
- Делать выводы которые пользователь не подтвердил
- Хранить данные без consent

❌ НЕЛЬЗЯ:
- Ставить диагнозы
- Заменять профессиональную помощь в кризисе
- Использовать данные для manipulation
- Шерить данные с третьими лицами
```

---

## 6. КОНКРЕТНЫЕ ТЕХНИКИ

### Contradiction Detection

```python
async def detect_contradictions(user_id: int) -> list:
    """
    Находит противоречия в данных пользователя.
    """

    goals = await get_user_goals(user_id)
    barriers = await get_user_barriers(user_id)
    values = await get_user_values(user_id)

    prompt = f"""
    Проанализируй данные пользователя и найди ПРОТИВОРЕЧИЯ.

    ЦЕЛИ: {goals}
    БАРЬЕРЫ: {barriers}
    ЦЕННОСТИ: {values}

    Найди случаи где:
    1. Цель противоречит барьеру (хочет X, но сам себе мешает)
    2. Ценность противоречит поведению
    3. Две цели конфликтуют друг с другом

    Формат ответа:
    [
        {{"type": "goal_barrier", "goal": "...", "barrier": "...", "insight": "..."}},
        ...
    ]
    """

    contradictions = await llm.generate(prompt)
    return contradictions
```

### Pattern Recognition

```python
async def analyze_patterns(user_id: int) -> dict:
    """
    Анализ паттернов в ответах пользователя.
    """

    answers = await get_all_answers(user_id)

    prompt = f"""
    Проанализируй 150 ответов пользователя и выяви ПАТТЕРНЫ:

    {answers}

    Найди:
    1. ПОВТОРЯЮЩИЕСЯ ТЕМЫ (что упоминается 3+ раз)
    2. ЭМОЦИОНАЛЬНЫЕ ПАТТЕРНЫ (какие эмоции преобладают)
    3. ВРЕМЕННЫЕ ПАТТЕРНЫ (что меняется со временем)
    4. ИЗБЕГАЕМЫЕ ТЕМЫ (о чём НЕ говорит)
    5. ЗАЩИТНЫЕ МЕХАНИЗМЫ (рационализация, отрицание, etc.)

    Формат:
    {{
        "recurring_themes": [...],
        "emotional_patterns": [...],
        "temporal_changes": [...],
        "avoided_topics": [...],
        "defense_mechanisms": [...]
    }}
    """

    return await llm.generate(prompt)
```

### Breakthrough Detection

```python
async def detect_breakthrough(
    user_id: int,
    current_message: str,
    history: list
) -> Optional[dict]:
    """
    Детектирует момент инсайта/прорыва.
    """

    indicators = []

    # 1. Linguistic markers
    insight_markers = [
        'я понял', 'осознал', 'вижу теперь', 'раньше не замечал',
        'связь между', 'на самом деле', 'это объясняет'
    ]
    if any(m in current_message.lower() for m in insight_markers):
        indicators.append('linguistic_marker')

    # 2. Emotional shift
    current_emotion = await detect_emotion(current_message)
    prev_emotions = [await detect_emotion(m) for m in history[-5:]]
    if current_emotion != mode(prev_emotions):
        indicators.append('emotional_shift')

    # 3. Self-reference increase
    self_words = ['я', 'мне', 'меня', 'мой']
    self_ratio = sum(current_message.lower().count(w) for w in self_words) / len(current_message.split())
    if self_ratio > 0.15:  # High self-focus
        indicators.append('self_focus')

    # 4. Connection to past
    if references_past_answer(current_message, history):
        indicators.append('past_connection')

    if len(indicators) >= 2:
        return {
            'detected': True,
            'indicators': indicators,
            'message': current_message,
            'recommended_response': 'validate and deepen'
        }

    return None
```

### Resistance Handling

```python
async def handle_resistance(
    user_id: int,
    message: str,
    session: SessionState
) -> ChatResponse:
    """
    Обработка сопротивления пользователя.
    """

    resistance_type = detect_resistance_type(message)

    responses = {
        'avoidance': {
            # "Не хочу об этом"
            'response': "Понимаю, это непростая тема. Можем вернуться к ней позже, когда будешь готов.",
            'action': 'offer_alternative_topic'
        },

        'intellectualization': {
            # Уход в теорию вместо чувств
            'response': "Это интересный анализ. А что ты ЧУВСТВУЕШЬ по этому поводу?",
            'action': 'redirect_to_emotions'
        },

        'minimization': {
            # "Это не важно"
            'response': "Ты говоришь что не важно, но ты об этом заговорил. Может, всё-таки что-то есть?",
            'action': 'gentle_challenge'
        },

        'deflection': {
            # Смена темы
            'response': "Заметил что мы переключились. Хочешь вернуться к тому, о чём говорили?",
            'action': 'acknowledge_and_offer_choice'
        }
    }

    strategy = responses.get(resistance_type, responses['avoidance'])

    return ChatResponse(
        message=strategy['response'],
        action=strategy['action'],
        resistance_detected=True
    )
```

---

## 7. ИТОГОВАЯ АРХИТЕКТУРА ДЛЯ SELFOLOGY

### Рекомендуемый подход

```
┌─────────────────────────────────────────────────────────┐
│                    DATA LAYER                            │
├─────────────────────────────────────────────────────────┤
│  PostgreSQL:                                             │
│  ├── digital_personality (10 JSONB layers)              │
│  ├── user_answers_v2 (raw answers)                      │
│  └── user_dossier (AI-generated summary)  ← NEW         │
│                                                          │
│  Qdrant:                                                 │
│  ├── goals_vectors (72 goals embedded)                  │
│  ├── barriers_vectors (62 barriers embedded)            │
│  └── answers_vectors (all answers embedded)             │
│                                                          │
│  Redis:                                                  │
│  ├── dossier_cache (1 hour TTL)                         │
│  └── session_context (5 min TTL)                        │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│                 KNOWLEDGE LAYER                          │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  UserDossierService:                                     │
│  ├── generate_dossier(user_id) → 500 word summary       │
│  ├── update_dossier(user_id, new_data)                  │
│  └── get_cached_dossier(user_id)                        │
│                                                          │
│  SemanticSearchService:                                  │
│  ├── find_relevant_goals(query)                         │
│  ├── find_relevant_barriers(query)                      │
│  └── find_similar_answers(query)                        │
│                                                          │
│  PatternAnalyzer:                                        │
│  ├── detect_contradictions(user_id)                     │
│  ├── analyze_patterns(user_id)                          │
│  └── track_changes(user_id)                             │
│                                                          │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│                  COACH LAYER                             │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ContextBuilder:                                         │
│  ├── build_full_context(user_id, message)               │
│  │   ├── dossier (always)                               │
│  │   ├── relevant_data (semantic search)                │
│  │   └── recent_messages (last 3)                       │
│  └── ~1000 tokens total                                 │
│                                                          │
│  ResponseGenerator:                                      │
│  ├── generate_response(context, message)                │
│  ├── apply_style(big_five_profile)                      │
│  └── include_personal_references()                      │
│                                                          │
│  InsightDetector:                                        │
│  ├── detect_breakthrough(message)                       │
│  ├── detect_resistance(message)                         │
│  └── detect_crisis(message)                             │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

### Ключевые метрики успеха

| Метрика | Цель | Как измерять |
|---------|------|--------------|
| "Feeling Known" | >4/5 | User survey после сессии |
| Personal Reference Rate | 1-2 per response | Auto-detect in responses |
| Context Relevance | >80% | Compare retrieved vs used |
| Response Time | <3s | Latency tracking |
| Token Efficiency | <2K per turn | Usage monitoring |

---

## 8. NEXT STEPS ДЛЯ SELFOLOGY

1. **Создать UserDossierService**
   - AI-генерация резюме личности
   - Кэширование в Redis
   - Обновление после новых ответов

2. **Добавить Semantic Search**
   - Проиндексировать goals/barriers в Qdrant
   - Поиск релевантного по контексту сообщения

3. **Обновить промпт коуча**
   - Включить досье
   - Добавить style instructions по Big Five
   - Требовать personal references

4. **Добавить Pattern Analyzer**
   - Детекция противоречий
   - Отслеживание паттернов
   - Breakthrough detection

5. **Тестирование**
   - A/B: старый vs новый подход
   - Метрика "feeling known"
   - User interviews
