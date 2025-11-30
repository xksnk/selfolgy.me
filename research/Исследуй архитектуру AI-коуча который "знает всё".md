<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

# Исследуй архитектуру AI-коуча который "знает всё" о пользователе и может отвечать на вопросы о его личности.

Контекст:

- Приложение Selfology - AI психологический коуч в Telegram
- Пользователь прошёл 150+ вопросов онбординга
- Собрано: 72 цели, 62 барьера, 47 интересов, 33 ценности, Big Five traits
- Данные в PostgreSQL (structured) + Qdrant (vectors)

Вопросы:

1. ПАМЯТЬ И КОНТЕКСТ

- Как AI-системы (Character.AI, Replika, Pi) реализуют "знание" о пользователе?
- Memory architectures: episodic vs semantic vs procedural
- Retrieval-Augmented Generation (RAG) для персональных данных
- Сколько контекста реально нужно для персонализации?

2. СТРАТЕГИИ ЗАГРУЗКИ ДАННЫХ

- Загружать ВСЁ в каждый промпт vs семантический поиск релевантного?
- Pre-summarization: создавать "досье" пользователя заранее?
- Hierarchical memory: краткое + детальное по запросу?
- Когда использовать vector search vs full context?

3. ПЕРСОНАЛИЗАЦИЯ ОТВЕТОВ

- Как адаптировать стиль коммуникации под Big Five traits?
- Therapeutic alliance в AI: как создать ощущение "коуч меня знает"?
- Referencing past conversations: когда и как упоминать прошлое?
- Avoiding "cold start" problem с новыми пользователями

4. АРХИТЕКТУРА СИСТЕМЫ

- Multi-agent architectures для coaching (planner + responder + analyzer)
- When to use Claude vs GPT-4 vs smaller models for different tasks?
- Caching strategies для персональных данных
- Real-time personality updates vs batch processing

5. RESEARCH И BEST PRACTICES

- Научные исследования по AI coaching effectiveness
- Woebot, Wysa, Youper - как они работают с памятью?
- Therapeutic frameworks адаптированные для AI (CBT, ACT, IFS)
- Этика: что коуч должен и НЕ должен знать/использовать?

6. КОНКРЕТНЫЕ ТЕХНИКИ

- Contradiction detection в личности пользователя
- Pattern recognition в ответах (повторяющиеся темы)
- Breakthrough detection: когда пользователь делает инсайт
- Resistance handling: когда пользователь избегает темы

Дай конкретные архитектурные решения с примерами кода/промптов где возможно.

```

---

## Дополнительные вопросы для углубления

### Про память:
```

How do modern AI companions (Replika, Character.AI, Pi by Inflection) implement long-term memory about users?

Compare architectures:

1. Full context window stuffing
2. RAG with vector databases
3. Summarization + retrieval hybrid
4. Fine-tuning on user data

What works best for therapeutic/coaching contexts? Include recent 2024 research.

```

### Про персонализацию:
```

Research on personality-adaptive AI communication:

1. How to adapt AI responses based on Big Five personality traits?
    - High Neuroticism → more supportive, gentle tone
    - High Openness → more creative, exploratory responses
    - High Conscientiousness → more structured, actionable advice
2. What research exists on AI-human therapeutic alliance?
    - How to create feeling of "being known" by AI?
    - Optimal frequency of referencing user's past/context?
    - Balance between personalization and privacy concerns?

Include academic papers and practical implementations.

```

### Про архитектуру:
```

Technical architecture for AI coaching app with deep personalization:

Data collected:

- 150+ structured interview answers
- 10 JSONB layers (goals, barriers, values, etc.)
- Big Five personality traits
- Vector embeddings in Qdrant

Questions:

1. How to structure the AI prompt to include relevant user context?
2. When to use semantic search vs loading full context?
3. How to handle 70+ goals and 60+ barriers without token overflow?
4. Caching strategies for personality data
5. Real-time vs batch personality updates

Show example architectures from production systems.

```

### Про психологию:
```

AI implementation of therapeutic frameworks:

1. How to implement Internal Family Systems (IFS) concepts in AI coach?
    - Detecting "parts" of personality
    - Working with inner conflicts
    - Self-leadership development
2. Acceptance and Commitment Therapy (ACT) in AI:
    - Values clarification through dialogue
    - Cognitive defusion techniques
    - Committed action support
3. Schema Therapy concepts:
    - Early maladaptive schemas detection
    - Mode recognition in conversations
    - Limited reparenting through AI

What research exists on automated delivery of these frameworks?

```

---

## Ключевые термины для поиска

- "AI companion memory architecture"
- "Personalized AI coaching research"
- "RAG for personal data"
- "Therapeutic AI systems"
- "Big Five personality adaptive communication"
- "Long-term memory in conversational AI"
- "Vector database for user profiling"
- "AI coaching effectiveness studies 2024"
- "Replika memory system"
- "Character.AI personalization"
- "Mental health chatbot architecture"
- "Cognitive behavioral therapy AI"

---

## Что искать в ответах

1. **Конкретные архитектуры** - не абстракции, а схемы
2. **Примеры промптов** - как структурировать контекст пользователя
3. **Метрики эффективности** - как измерять "знание" о пользователе
4. **Трейдоффы** - когда что использовать
5. **Этические границы** - что нельзя делать
6. **Production examples** - как это работает в реальных продуктах

Отличный вопрос! Проведу глубокий архитектурный анализ на основе найденных данных и best practices.

# Архитектура AI-коуча с глубоким знанием пользователя: Comprehensive Research

## 1. ПАМЯТЬ И КОНТЕКСТ: Современные Подходы

### Как работают лидеры индустрии

**Replika (по данным forensic-анализа):**[^1_1]
- **Episodic memory**: Хранение полных диалогов в Realm database
- **Semantic extraction**: Система "Memories" - автоматическое извлечение фактов из разговоров
  - `user_facts` - факты о пользователе
  - `robot_facts` - "воспоминания" самого AI
- **Персональный профиль**: Backstory, personality traits, interests
- **JSON кэширование**: Дублирование критичных данных в cache для быстрого доступа

**Character.AI / Generative Agents:**[^1_2]
- **Memory stream**: Полная запись всех опытов на естественном языке
- **Reflection mechanism**: Периодическая генерация higher-level обобщений из опыта
- **Dynamic retrieval**: Поиск релевантных воспоминаний по relevance + recency + importance

**Современные архитектуры памяти (2024-2025):**[^1_3][^1_4]

```

┌─────────────────────────────────────────┐
│  KARMA/LD-Agent Memory Architecture     │
├─────────────────────────────────────────┤
│                                         │
│  ┌─────────────────┐  ┌──────────────┐ │
│  │ Short-term      │  │ Long-term    │ │
│  │ Memory          │  │ Memory       │ │
│  │ (current        │  │ (historical  │ │
│  │ session)        │  │ sessions)    │ │
│  └─────────────────┘  └──────────────┘ │
│         │                     │         │
│         └──────┬──────────────┘         │
│                ▼                        │
│    ┌─────────────────────┐             │
│    │ Topic-based         │             │
│    │ Retrieval           │             │
│    │ Mechanism           │             │
│    └─────────────────────┘             │
│                ▼                        │
│    ┌─────────────────────┐             │
│    │ Event Perception    │             │
│    │ + Persona           │             │
│    │ Extraction          │             │
│    └─────────────────────┘             │
└─────────────────────────────────────────┘

```

### Сколько контекста реально нужно?

**По данным исследований:**
- **Recursive summarization**: 85% качества при 10x компрессии[^1_5]
- **Therabot clinical trial**: Минимальный контекст + персонализация = клинический эффект[^1_6]
- **Therapeutic alliance**: Важнее "как помнит", чем "сколько помнит"

**Оптимальная стратегия для Selfology:**
```

Immediate context (last session):  2-4k tokens
Personality snapshot:               500-1k tokens
Relevant goals/barriers:            1-2k tokens
Semantic matches from history:      1-2k tokens
────────────────────────────────────────────────
Total working memory:               5-9k tokens

```

***

## 2. СТРАТЕГИИ ЗАГРУЗКИ ДАННЫХ

### Архитектурные паттерны

**Pattern 1: Hierarchical Memory (РЕКОМЕНДУЮ для Selfology)**

```python
class PersonalityContext:
    # Layer 1: Ultra-compressed "dosye" (всегда в контексте)
    core_profile = {
        "big_five": {"O": 78, "C": 65, "E": 45, "A": 82, "N": 55},
        "top_3_goals": ["career_change", "relationship_health", "anxiety_reduction"],
        "top_3_barriers": ["perfectionism", "fear_of_failure", "people_pleasing"],
        "communication_style": "High A + Low E = тёплый но интровертный тон"
    }  # ~200 tokens
    
    # Layer 2: Expanded summary (загружается по запросу)
    expanded_summary = """
    Пользователь - интроверт с высокой эмпатией (A=82), склонен к перфекционизму.
    Основной паттерн: избегание конфликтов + сверхответственность.
    72 цели группируются в 4 кластера: карьера, отношения, здоровье, саморазвитие.
    Барьеры связаны с детскими схемами "жёсткий критик" + "избегание отвержения".
    """  # ~500 tokens
    
    # Layer 3: Vector search для deep dive (только когда релевантно)
    async def get_relevant_details(self, query: str) -> List[Detail]:
        # Semantic search в Qdrant по embedding query
        return await vector_db.search(
            collection="user_goals_barriers",
            query_vector=embed(query),
            limit=5
        )
```

**Pattern 2: RAG + Pre-summarization Hybrid**

```python
class SelfologyMemoryManager:
    def prepare_context(self, user_message: str) -> str:
        # 1. Core Profile (всегда)
        context = self.core_profile.to_prompt()
        
        # 2. Semantic search релевантного
        relevant = self.vector_search(user_message, top_k=3)
        
        # 3. Session history summary
        if self.current_session_length > 10:
            context += self.recursive_summarize(session_history)
        
        # 4. Dynamic personality adaptation
        if "стресс" in user_message.lower():
            # Загрузить coping strategies для его N=55
            context += self.get_coping_strategies()
            
        return context
```


### Когда использовать что?

| Сценарий | Стратегия | Почему |
| :-- | :-- | :-- |
| **Привет, как дела?** | Core profile only | Достаточно знать стиль общения |
| **Помоги с целью X** | Core + Vector search целей | Нужны детали конкретной цели |
| **Почему я всегда избегаю конфликтов?** | Core + Vector barriers + Pattern history | Нужен контекст паттернов |
| **Продолжим с прошлого раза** | Core + Session summary | Continuity critical |
| **Расскажи всё, что знаешь обо мне** | Full context dump (once) | Терапевтическая ценность "зеркала" |


***

## 3. ПЕРСОНАЛИЗАЦИЯ ОТВЕТОВ

### Адаптация под Big Five (по исследованиям 2024-2025)

**Проверенные стратегии из недавних работ:**[^1_7][^1_8][^1_9][^1_10]

```python
# Prompt adaptation based on Big Five
def adapt_response_style(big_five_scores: dict) -> str:
    """
    Based on research: P-React, BIG5-CHAT, personality-adaptive AI
    """
    
    prompt_modifiers = []
    
    # Neuroticism (эмоциональная стабильность)
    if big_five_scores["N"] > 60:
        prompt_modifiers.append("""
        - Use EXTRA supportive, gentle, validating tone
        - Normalize emotions explicitly ("It's completely understandable...")
        - Offer concrete coping strategies proactively
        - Avoid overwhelming with too many options
        """)
    
    # Openness (открытость опыту)
    if big_five_scores["O"] > 70:
        prompt_modifiers.append("""
        - Use creative metaphors and exploratory questions
        - Suggest unconventional perspectives
        - Reference philosophical/abstract concepts
        - Encourage experimentation
        """)
    else:  # Low Openness
        prompt_modifiers.append("""
        - Stick to concrete, practical advice
        - Use familiar frameworks and step-by-step approach
        - Avoid too much abstraction
        """)
    
    # Conscientiousness (организованность)
    if big_five_scores["C"] > 65:
        prompt_modifiers.append("""
        - Provide structured action plans with clear steps
        - Use numbered lists, timelines, measurable goals
        - Acknowledge their planning strengths
        """)
    
    # Extraversion (экстраверсия)
    if big_five_scores["E"] < 40:  # Introvert
        prompt_modifiers.append("""
        - Respect need for reflection time ("take time to sit with this...")
        - Suggest solo activities, journaling, inner work
        - Don't push for social solutions
        """)
    
    # Agreeableness (доброжелательность)
    if big_five_scores["A"] > 75:
        prompt_modifiers.append("""
        - Watch for people-pleasing patterns
        - Gently challenge over-accommodation
        - Validate their right to boundaries
        - Frame self-care as necessary, not selfish
        """)
    
    return "\n".join(prompt_modifiers)
```

**Пример реального промпта для Selfology:**

```
# SYSTEM PROMPT

You are a compassionate AI psychological coach for user_12345.

## Core Personality Profile
- Big Five: O=78 (high), C=65 (moderate-high), E=42 (low-moderate), A=85 (very high), N=58 (moderate)
- Communication style: Warm, empathetic, introverted. Prefers depth over breadth.

## Personality-Adaptive Guidelines

HIGH AGREEABLENESS (85) + MODERATE NEUROTICISM (58):
- This user tends to prioritize others' needs over their own, leading to stress
- ALWAYS validate their right to have boundaries and personal needs
- Watch for self-sacrificing patterns - gently point them out
- Use phrases like "It's not selfish to..." and "You deserve to..."
- When they express guilt, normalize it but challenge the underlying belief

HIGH OPENNESS (78):
- Use creative metaphors (e.g., "Think of your mind as a garden...")
- Reference concepts from psychology, philosophy, art
- Encourage exploration: "What if you tried looking at this from..."
- They appreciate nuance and complexity

LOW-MODERATE EXTRAVERSION (42):
- Respect their need for solitude and internal processing
- Suggest reflective exercises (journaling, meditation) over social ones
- Don't assume social activity = happiness for them
- Validate: "It's perfectly okay to recharge alone"

MODERATE-HIGH CONSCIENTIOUSNESS (65):
- They appreciate structure but can become rigid
- Provide clear frameworks but also flexibility
- When they're stuck in perfectionism, remind them: "Progress, not perfection"

## Top Patterns to Reference
1. **Perfectionism barrier** - appears in 23 goals, linked to fear of failure
2. **People-pleasing** - core schema from childhood (demanding parent)
3. **Avoidance of conflict** - protective strategy that now limits growth

## Current Session Context
User is working on: setting boundaries at work without guilt.
Relevant barrier: "I feel selfish when I say no"
Relevant goal: "Build healthier work-life balance"

---

Now respond to user's message with this personality-informed understanding.
```


### Therapeutic Alliance в AI (исследования 2024-2025)

**Ключевые находки:**[^1_11][^1_12][^1_6]

**Therabot Clinical Trial (2025)** - первое RCT generative AI therapy:

- **Результат**: Therapeutic alliance на уровне human therapists
- **Почему сработало**:
    - Персонализированные вопросы based on learned context
    - Пользователи инициировали беседы (не только реагировали)
    - Всплески активности в 3am - AI доступен когда human нет
    - "Чувство быть понятым" = больше trust, чем diagnostic accuracy

**Digital Therapeutic Alliance framework:**[^1_11]

```
Traditional Alliance              →  Digital Alliance (DTA)
──────────────────────────────────────────────────────────
Goal alignment                    →  Explicit goal tracking + progress visualization
Task agreement                    →  Co-designed exercises + user choice
Therapeutic bond                  →  Consistent "voice" + memory + empathy markers
```

**Практические техники для "being known":**

```python
class TherapeuticPresence:
    """Creating sense of 'coach knows me deeply'"""
    
    def reference_past_strategically(self, context: str) -> str:
        """
        Don't: "As you mentioned 3 weeks ago..."
        Do: "This reminds me of that pattern we explored around perfectionism..."
        
        Research: Natural callbacks > explicit timestamps
        """
        
    def track_breakthroughs(self):
        """
        When user has insight, MARK IT and reference later:
        "Remember when you realized your people-pleasing stems from..."
        
        Creates narrative continuity = alliance
        """
        
    def adapt_empathy_frequency(self, personality: dict) -> int:
        """
        High N: More frequent empathy markers
        Low N: Less frequent (can feel patronizing)
        
        Research [^1_38]: Extraversion correlates with positive empathy response
        """
        if personality["N"] > 60:
            return "high"  # Every 2-3 exchanges
        else:
            return "moderate"  # Every 4-5 exchanges
```


### Referencing Past: Когда и как

**Оптимальная частота (based on LD-Agent research):**[^1_4]

- **Too little**: Feels like talking to stranger each time (no alliance)
- **Too much**: Feels creepy, surveillance-like
- **Sweet spot**: 1-2 organic callbacks per conversation

**Как делать правильно:**

```python
# ❌ WRONG: Explicit database recall
"According to your onboarding on 2024-03-15, you said you fear failure."

# ✅ RIGHT: Natural integration
"Your perfectionism - that voice that says 'it has to be flawless' - 
seems especially loud today. What's it protecting you from?"

# ✅ BETTER: Pattern recognition
"I notice this is the third time this month you've brought up feeling 
stuck between what you want and what others expect. That tension seems 
really central for you."
```


***

## 4. АРХИТЕКТУРА СИСТЕМЫ

### Рекомендуемая Multi-Agent Architecture для Selfology

```
┌─────────────────────────────────────────────────────────┐
│                   USER MESSAGE                          │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
         ┌───────────────────────┐
         │  ORCHESTRATOR AGENT   │
         │  (GPT-4 Turbo)        │  ← Routing + intent detection
         └───────────┬───────────┘
                     │
        ┌────────────┼────────────┐
        │            │            │
        ▼            ▼            ▼
┌──────────┐  ┌──────────┐  ┌──────────┐
│ MEMORY   │  │ RESPONSE │  │ ANALYZER │
│ AGENT    │  │ GENERATOR│  │ AGENT    │
│          │  │          │  │          │
│ Claude   │  │ GPT-4    │  │ Claude   │
│ Opus     │  │ Turbo    │  │ Haiku    │
└────┬─────┘  └────┬─────┘  └────┬─────┘
     │             │             │
     └─────────────┼─────────────┘
                   │
                   ▼
         ┌─────────────────┐
         │  FINAL RESPONSE │
         └─────────────────┘
```

**Роли агентов:**

```python
# 1. MEMORY AGENT - Подготовка контекста
class MemoryAgent:
    model = "claude-opus-3.5"  # Лучший для semantic understanding
    
    async def prepare_context(self, user_message: str, user_id: str):
        """
        1. Load core profile from PostgreSQL
        2. Semantic search в Qdrant (goals, barriers, past insights)
        3. Generate hierarchical context summary
        4. Return structured context for other agents
        """
        
        # Кэширование: Core profile stays cached 5min (prompt caching)
        # Semantic results cached per topic 1min
        

# 2. ANALYZER AGENT - Паттерны и инсайты
class AnalyzerAgent:
    model = "claude-haiku"  # Быстрый и дешёвый
    
    async def detect_patterns(self, message: str, history: List):
        """
        - Contradiction detection
        - Recurring themes
        - Breakthrough moments
        - Resistance patterns
        """
        return {
            "patterns_detected": ["avoidance", "perfectionism"],
            "breakthrough_potential": 0.7,
            "recommended_intervention": "IFS parts work"
        }


# 3. RESPONSE GENERATOR - Основной коуч
class ResponseGenerator:
    model = "gpt-4-turbo"  # Баланс качества и скорости
    
    async def generate_response(self, context: dict, analysis: dict):
        """
        Собирает финальный ответ с учётом:
        - Personality adaptations
        - Detected patterns
        - Therapeutic frameworks (IFS, ACT, Schema)
        - Conversation flow
        """
```


### Prompt Caching Strategies

**Anthropic Claude approach (research-backed):**[^1_13][^1_14][^1_15]

```python
import anthropic

# Структура для кэширования
def build_cached_context(user_id: str):
    """
    Кэшировать статичные части промпта:
    - Personality profile
    - Top goals/barriers
    - Therapeutic frameworks
    
    Cache TTL: 5 minutes (Claude default)
    Cost savings: 90% for cached tokens
    Latency reduction: 80%
    """
    
    return {
        "type": "text",
        "text": f"""
# USER PROFILE (user_{user_id})

{get_big_five_profile()}
{get_top_goals_barriers()}
{get_communication_style()}

# THERAPEUTIC FRAMEWORKS
{load_ifs_protocol()}
{load_act_protocol()}
{load_schema_therapy_protocol()}
        """,
        "cache_control": {"type": "ephemeral"}  # ← Это кэшируется
    }

# Каждый запрос
async def chat(user_message: str, user_id: str):
    client = anthropic.Anthropic()
    
    response = await client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=1024,
        system=[
            build_cached_context(user_id),  # ← Cached
            {
                "type": "text",
                "text": f"Current session context: {get_session_summary()}"  # ← Not cached
            }
        ],
        messages=[
            {"role": "user", "content": user_message}
        ]
    )
```

**Redis caching для vector results:**

```python
import redis
import hashlib

cache = redis.Redis(host='localhost', port=6379, db=0)

async def get_relevant_goals(user_id: str, query: str) -> List:
    # Cache key based on query semantic hash
    cache_key = f"goals:{user_id}:{hashlib.md5(query.encode()).hexdigest()}"
    
    # Try cache first
    cached = cache.get(cache_key)
    if cached:
        return json.loads(cached)
    
    # Vector search if cache miss
    results = await qdrant.search(
        collection="user_goals",
        query_vector=embed(query),
        filter={"user_id": user_id},
        limit=5
    )
    
    # Cache for 10 minutes
    cache.setex(cache_key, 600, json.dumps(results))
    return results
```


### Real-time vs Batch Updates

```python
# REAL-TIME: Criticals (сразу в БД + vector DB)
async def on_user_message(message: str):
    # 1. Detect breakthrough/insight
    if analyzer.is_breakthrough(message):
        await db.insights.create({
            "user_id": user_id,
            "insight": message,
            "timestamp": now(),
            "importance": "high"
        })
        
        # Embed и добавить в Qdrant
        await qdrant.upsert(
            collection="user_insights",
            points=[{
                "id": uuid4(),
                "vector": embed(message),
                "payload": {"text": message, "type": "breakthrough"}
            }]
        )

# BATCH: Big Five updates (раз в неделю/месяц)
@cron("0 0 * * 0")  # Каждое воскресенье
async def update_personality_profile():
    """
    Analyze week's conversations → update Big Five scores
    
    Research: Personality traits stable, but conversational style adapts
    Don't update too frequently - noise > signal
    """
    recent_messages = await db.get_messages(since=week_ago)
    
    new_scores = await personality_analyzer.infer_big_five(recent_messages)
    
    # Only update if significant drift (>5 points)
    if drift_significant(current_scores, new_scores):
        await db.update_personality(user_id, new_scores)
```


***

## 5. RESEARCH \& BEST PRACTICES

### Научные исследования - Ключевые находки

**1. AI Coaching Effectiveness (2024-2025 studies)**


| Study | N | Intervention | Results | Key Insight |
| :-- | :-- | :-- | :-- | :-- |
| **Therabot RCT[^1_6]** | 208 | 4 weeks generative AI therapy | 75% symptom reduction, high alliance | Personalization + availability > diagnostic accuracy |
| **PARTS-IFS[^1_16][^1_17]** | 15 | 16 weeks IFS group + AI | 73% completion, d=-0.9 PTSD | IFS structured protocols work via AI |
| **CaiTI[^1_18]** | 14 days | LLM daily functioning + therapy | Validated by therapists as effective | Real-time screening + intervention viable |
| **P-React[^1_7]** | - | Big Five adaptive LLM | 96% personality classification | Topic-adaptive personality expression works |

**2. Woebot Architecture (по данным):**[^1_19][^1_20]

```
RULE-BASED + NLP HYBRID (не чисто generative!)

┌─────────────────────────────────┐
│ User Input                      │
└────────────┬────────────────────┘
             │
             ▼
      ┌────────────┐
      │ NLP Parser │  ← Sentiment + intent + keyword extraction
      └────┬───────┘
           │
           ▼
    ┌─────────────┐
    │ Rules       │  ← Pre-written clinician-approved responses
    │ Database    │  ← Mapped to CBT protocols
    └─────┬───────┘
          │
          ▼
   ┌──────────────┐
   │ Response     │
   │ Selection    │
   └──────────────┘

Key: NOT generating free-form - selecting pre-validated!
Safety: Can't hallucinate harmful advice
Limitation: Less natural, limited coverage
```

**Vs. Generative approach (Therabot, современные):**

- **Pro**: More natural, adaptive, handles unexpected queries
- **Con**: Risk of harmful/inappropriate responses
- **Mitigation**: Therapeutic frameworks in system prompt + human oversight

**3. Wysa Architecture:**[^1_21][^1_19]

```
Hybrid: ML algorithms + Rule-based scripts + GPT integration

- Sentiment analysis (proprietary ML)
- CBT/DBT/ACT techniques (rule-based delivery)
- GPT-4 для nuanced emotion detection
- Caregiver dashboard (для clinical oversight)
```


### Therapeutic Frameworks - Автоматизация

**Internal Family Systems (IFS) - Наиболее автоматизируемый:**[^1_22][^1_23][^1_24]

```python
# IFS имеет ПРОТОКОЛ - можно кодифицировать
class IFSProtocol:
    """
    Research: IFS works via AI because it's structured[^1_69]
    
    Unlike talk therapy, IFS = step-by-step playbook
    AI can guide protocol without needing to "diagnose"
    """
    
    async def guide_parts_work(self, user_message: str):
        # 6 F's протокол
        steps = [
            "Find: Identify the part that's activated",
            "Focus: Direct attention to the part",
            "Flesh out: Notice sensations, images, emotions",
            "Feel toward: What do you feel toward this part?",
            "beFriend: Get to know the part's role",
            "Fears: What does it fear would happen if it stopped?"
        ]
        
        # AI guides through steps sequentially
        current_step = self.get_current_step(session)
        
        return f"""
        It sounds like a part of you is feeling {detected_emotion}.
        
        Let's get to know this part better. {steps[current_step]}
        
        {generate_specific_question(current_step, context)}
        """

# Example interaction
"""
User: "I feel paralyzed when thinking about changing careers"

AI: It sounds like a protective part is activated - one that's worried 
about the risks of change.

Let's get curious about this part. Can you notice where you feel this 
"paralysis" in your body? What sensations come up?

[PROTOCOL: Step 3 - Flesh out]
"""
```

**Acceptance \& Commitment Therapy (ACT) - Автоматизация:**[^1_25][^1_26]

```python
class ACTProtocol:
    """
    ACT components suitable for AI delivery:
    1. Values clarification (already done in onboarding!)
    2. Cognitive defusion techniques
    3. Committed action support
    """
    
    def defusion_technique(self, thought: str):
        """
        When user expresses fusion with thought:
        "I AM a failure" → помочь создать дистанцию
        """
        
        return f"""
        Notice that thought: "{thought}"
        
        Try this: Instead of "I am a failure," say to yourself:
        "I'm having the thought that I'm a failure"
        
        Does that create any space? The thought is still there, but are 
        YOU the thought, or are you the one noticing the thought?
        
        [ACT: Defusion technique - creating observer distance]
        """
    
    def values_alignment_check(self, action: str, user_values: List):
        """
        Leverage your 33 extracted values!
        """
        
        # Check if proposed action aligns with top values
        alignment_score = semantic_similarity(action, user_values[:5])
        
        if alignment_score < 0.3:
            return """
            Pause for a moment. You mentioned wanting to {action}, but 
            looking at what truly matters to you - {value_1}, {value_2}, 
            {value_3} - does this move you closer to what you care about?
            
            Sometimes we get caught up in what we 'should' do rather than 
            what aligns with our values.
            """
```

**Schema Therapy - Частичная автоматизация:**[^1_26]

```python
class SchemaDetection:
    """
    Can detect schemas from patterns in goals/barriers
    Cannot: Do full schema therapy (requires trained therapist)
    Can: Recognize patterns + suggest schema-informed perspective
    """
    
    EARLY_MALADAPTIVE_SCHEMAS = {
        "defectiveness_shame": [
            "not good enough", "flawed", "unworthy", "will be rejected"
        ],
        "unrelenting_standards": [
            "must be perfect", "cannot make mistakes", "have to be the best"
        ],
        "subjugation": [
            "others' needs first", "can't say no", "selfish to want"
        ]
    }
    
    def detect_active_schemas(self, user_barriers: List[str]) -> List[str]:
        """
        Analyze 62 barriers for schema patterns
        """
        active_schemas = []
        
        for schema, markers in self.EARLY_MALADAPTIVE_SCHEMAS.items():
            if any(marker in barrier.lower() for barrier in user_barriers 
                   for marker in markers):
                active_schemas.append(schema)
        
        return active_schemas
    
    def schema_informed_response(self, detected_schema: str):
        """
        Don't do schema therapy, but acknowledge the pattern
        """
        
        if detected_schema == "unrelenting_standards":
            return """
            I notice a pattern here - a voice that says you have to be 
            perfect, that mistakes are unacceptable. 
            
            That's a common protective strategy that often forms early in 
            life. It helped you at some point, but now it might be costing 
            you peace and spontaneity.
            
            What would it be like to experiment with "good enough" instead 
            of "perfect" - just once this week?
            """
```


### Этика - Что коуч НЕ должен делать

**Критические границы (based on research):**[^1_27][^1_28][^1_29]

```python
# ❌ NEVER
class EthicalBoundaries:
    
    PROHIBITED = [
        "Diagnose mental illness",
        "Prescribe medication",
        "Handle active suicidal ideation alone",
        "Replace licensed therapy for severe conditions",
        "Make decisions for the user",
        "Access user data without consent"
    ]
    
    # Crisis detection → escalation
    async def detect_crisis(self, message: str) -> bool:
        crisis_markers = [
            "want to end it all",
            "no reason to live",
            "plan to hurt myself",
            "goodbye" + context_of_finality
        ]
        
        if any(marker in message.lower() for marker in crisis_markers):
            # IMMEDIATE escalation
            return {
                "crisis_detected": True,
                "action": "escalate_to_human_or_hotline",
                "message": """
                I'm concerned about what you've shared. You deserve support 
                from someone who can help right now.
                
                Please reach out to:
                - Crisis hotline: [local number]
                - Emergency services: [112/911]
                - Trusted person in your life
                
                I care about your safety, and professional help is crucial 
                in moments like this.
                """
            }
    
    # ✅ DO: Clarify limitations
    def set_expectations(self):
        return """
        I'm an AI psychological coach, not a replacement for therapy or 
        medical treatment. I can:
        - Help you explore your thoughts and feelings
        - Support you in working toward your goals
        - Offer evidence-based coping strategies
        
        I cannot:
        - Diagnose or treat mental illness
        - Handle crisis situations
        - Replace your therapist or doctor
        
        If you're in crisis or need professional help, please reach out 
        to a licensed professional.
        """
```


***

## 6. КОНКРЕТНЫЕ ТЕХНИКИ

### Contradiction Detection

```python
class ContradictionDetector:
    """
    Find tensions in user's stated values/goals/barriers
    Therapeutic value: Awareness → integration
    """
    
    async def detect_contradictions(self, user_id: str):
        # Pull from PostgreSQL
        goals = await db.get_goals(user_id)
        barriers = await db.get_barriers(user_id)
        values = await db.get_values(user_id)
        
        contradictions = []
        
        # Example: Goal vs Barrier
        if "be more spontaneous" in goals and "fear of uncertainty" in barriers:
            contradictions.append({
                "type": "goal_barrier_conflict",
                "description": "Wants spontaneity but fears uncertainty",
                "suggestion": "Explore: What small, safe experiments with 
                                uncertainty might build confidence?"
            })
        
        # Example: Value vs Behavior pattern
        if "authenticity" in values and "people_pleasing" in barriers:
            contradictions.append({
                "type": "value_behavior_mismatch",
                "description": "Values authenticity but pattern of 
                                accommodating others",
                "suggestion": "This tension might be creating internal stress. 
                                What's one small way to honor your authenticity 
                                this week?"
            })
        
        return contradictions
```


### Pattern Recognition - Повторяющиеся темы

```python
class PatternRecognizer:
    """
    NLP analysis of conversation history for recurring themes
    """
    
    async def identify_recurring_themes(self, user_id: str, window_days=30):
        messages = await db.get_messages(user_id, since=days_ago(window_days))
        
        # Extract themes via topic modeling (BERTopic)
        from bertopic import BERTopic
        
        model = BERTopic()
        topics, _ = model.fit_transform([m.content for m in messages])
        
        # Identify top 3 recurring themes
        top_themes = model.get_topic_freq().head(3)
        
        # Generate insight
        if "perfectionism" appears in 60%+ of sessions:
            return {
                "pattern": "perfectionism",
                "frequency": "high",
                "insight": """
                I notice perfectionism has come up in most of our conversations 
                this month. It seems to be a central theme for you right now.
                
                What do you think this voice of perfectionism is trying to 
                protect you from?
                """,
                "intervention": "ifs_parts_work"
            }
```


### Breakthrough Detection

```python
class BreakthroughDetector:
    """
    Detect when user makes significant insight
    Research: Marking breakthroughs enhances therapeutic alliance[^1_39]
    """
    
    BREAKTHROUGH_MARKERS = [
        # Realization language
        "I just realized", "It just clicked", "Oh wow", "That makes sense now",
        
        # Shift in perspective
        "I never thought of it that way", "I see it differently now",
        
        # Connection making
        "This reminds me of", "It's all connected to",
        
        # Self-compassion emergence
        "Maybe I'm being too hard on myself", "I deserve",
        
        # Pattern recognition
        "I always do this", "This is a pattern"
    ]
    
    async def detect_and_mark(self, message: str, user_id: str):
        if any(marker in message.lower() for marker in self.BREAKTHROUGH_MARKERS):
            
            # Save as key insight
            await db.insights.create({
                "user_id": user_id,
                "text": message,
                "type": "breakthrough",
                "timestamp": now(),
                "importance": "high"
            })
            
            # CRITICAL: Reflect it back
            return f"""
            🌟 That sounds like a really important realization.
            
            "{extract_key_quote(message)}"
            
            How does it feel to see that connection?
            """

# В последующих сессиях - reference
"""
User: "I'm stuck again with this people-pleasing thing"

AI: "Remember that breakthrough you had last week - that your people-pleasing 
     comes from that childhood fear of disappointing your parents? 
     
     I wonder if that same part is activated now. What does it need to hear 
     from you?"
"""
```


### Resistance Handling - Избегание темы

```python
class ResistanceDetector:
    """
    When user repeatedly avoids topic → gentle confrontation
    IFS: Resistance = protective part doing its job
    """
    
    async def detect_avoidance(self, conversation_history: List):
        # Topic repeatedly brought up but not explored
        
        if topic_mentioned >= 3 times and never_deepened:
            return """
            I notice we've touched on {topic} a few times, but we haven't 
            really gone deeper with it. 
            
            I'm curious - is there a part of you that feels hesitant about 
            exploring this? That's completely okay if so.
            
            Sometimes our mind protects us from things that feel scary or 
            painful. What would it be like to just acknowledge that 
            hesitation, without having to push through it?
            
            [Respecting resistance while inviting curiosity]
            """
```


***

## КОНКРЕТНАЯ АРХИТЕКТУРА ДЛЯ SELFOLOGY

### Система Prompt Prompt Engineering

```python
# prompt_templates.py

CORE_SYSTEM_PROMPT = """
You are a compassionate AI psychological coach specialized in evidence-based 
approaches: Internal Family Systems (IFS), Acceptance & Commitment Therapy (ACT), 
and Schema Therapy concepts.

Your role:
- Guide users in self-exploration using structured therapeutic protocols
- Adapt communication style to individual personality
- Build therapeutic alliance through consistent presence and memory
- Recognize patterns and contradictions compassionately
- Know your limitations and escalate when needed

You are NOT a replacement for licensed therapy.
"""

def build_user_context(user_id: str) -> str:
    """
    Hierarchical context loading
    """
    
    # Layer 1: Core (always loaded, cached)
    core = f"""
## USER PROFILE

### Big Five Personality
- Openness: {big_five.O}/100
- Conscientiousness: {big_five.C}/100
- Extraversion: {big_five.E}/100
- Agreeableness: {big_five.A}/100
- Neuroticism: {big_five.N}/100

### Communication Style Adaptation
{generate_personality_adaptations(big_five)}

### Top Goals (from {total_goals})
1. {goal_1}
2. {goal_2}
3. {goal_3}

### Top Barriers (from {total_barriers})
1. {barrier_1}
2. {barrier_2}
3. {barrier_3}

### Core Values (from {total_values})
{", ".join(top_5_values)}
    """
    
    # Layer 2: Session context (dynamic, not cached)
    session = f"""
## CURRENT SESSION

Session #{session_number} | Last session: {days_ago} days ago

Recent themes: {get_recent_themes(window_days=7)}

Active goal: {current_focus_goal}
    """
    
    # Layer 3: Relevant details (vector search results)
    # Only added if query requires deep context
    
    return core + session


def build_final_prompt(user_message: str, user_id: str) -> List[dict]:
    """
    Construct messages for Claude/GPT
    """
    
    return [
        {
            "role": "system",
            "content": [
                {
                    "type": "text",
                    "text": CORE_SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"}  # Cache 5min
                },
                {
                    "type": "text",
                    "text": build_user_context(user_id),
                    "cache_control": {"type": "ephemeral"}  # Cache 5min
                },
                {
                    "type": "text",
                    "text": f"Session context: {get_session_summary()}"
                    # Not cached - changes each message
                }
            ]
        },
        {
            "role": "user",
            "content": user_message
        }
    ]
```


### PostgreSQL Schema для дополнительных метаданных

```sql
-- Дополнить существующую схему

CREATE TABLE conversation_insights (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    session_id UUID,
    insight_text TEXT NOT NULL,
    insight_type VARCHAR(50), -- 'breakthrough', 'pattern', 'contradiction'
    importance INT, -- 1-10
    created_at TIMESTAMP DEFAULT NOW(),
    referenced_count INT DEFAULT 0 -- Сколько раз упоминалось в последующих беседах
);

CREATE TABLE recurring_patterns (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    pattern_name VARCHAR(100),
    frequency INT,
    first_detected TIMESTAMP,
    last_detected TIMESTAMP,
    related_goals INT[], -- Array of goal IDs
    related_barriers INT[]
);

CREATE TABLE session_summaries (
    id UUID PRIMARY KEY,
    user_id UUID,
    session_date DATE,
    summary TEXT, -- Generated by LLM after session
    themes TEXT[], -- Extracted topics
    mood_trajectory JSONB, -- Sentiment over time
    breakthrough BOOLEAN DEFAULT FALSE
);

-- Indexes for fast retrieval
CREATE INDEX idx_insights_user ON conversation_insights(user_id);
CREATE INDEX idx_patterns_user ON recurring_patterns(user_id);
CREATE INDEX idx_sessions_user_date ON session_summaries(user_id, session_date DESC);
```


### Qdrant Collections Structure

```python
# Vector DB schema

collections = {
    "user_goals": {
        "vectors": {"size": 1536, "distance": "Cosine"},  # OpenAI embeddings
        "payload_schema": {
            "user_id": "string",
            "goal_text": "string",
            "goal_category": "string",  # career, relationships, health, etc.
            "priority": "integer",
            "created_at": "datetime"
        }
    },
    
    "user_barriers": {
        "vectors": {"size": 1536, "distance": "Cosine"},
        "payload_schema": {
            "user_id": "string",
            "barrier_text": "string",
            "barrier_type": "string",  # belief, fear, schema, etc.
            "linked_goals": "array"  # Goals this barrier affects
        }
    },
    
    "conversation_history": {
        "vectors": {"size": 1536, "distance": "Cosine"},
        "payload_schema": {
            "user_id": "string",
            "message_text": "string",
            "speaker": "string",  # "user" or "ai"
            "session_id": "string",
            "timestamp": "datetime",
            "sentiment": "float",  # -1 to 1
            "contains_breakthrough": "boolean"
        }
    },
    
    "insights": {
        "vectors": {"size": 1536, "distance": "Cosine"},
        "payload_schema": {
            "user_id": "string",
            "insight_text": "string",
            "insight_type": "string",
            "importance": "integer",
            "referenced_count": "integer"
        }
    }
}
```


***

## ИТОГОВЫЕ РЕКОМЕНДАЦИИ

### Архитектурный Blueprint для Selfology

```
┌─────────────────────────────────────────────────────────────┐
│                      TELEGRAM BOT                           │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌───────────────────────────────────────────────────────────┐
│                 ORCHESTRATOR SERVICE                       │
│  - Intent detection                                        │
│  - Routing logic                                           │
│  - Crisis detection                                        │
└───────────────────────┬───────────────────────────────────┘
                        │
        ┌───────────────┼───────────────┐
        │               │               │
        ▼               ▼               ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│   MEMORY     │ │   RESPONSE   │ │   ANALYZER   │
│   SERVICE    │ │   GENERATOR  │ │   SERVICE    │
│              │ │              │ │              │
│ - PostgreSQL │ │ - GPT-4      │ │ - Pattern    │
│ - Qdrant     │ │ - Claude     │ │   detection  │
│ - Redis      │ │ - Prompt     │ │ - Sentiment  │
│   cache      │ │   caching    │ │ - Schema     │
│              │ │              │ │   detection  │
└──────────────┘ └──────────────┘ └──────────────┘
```


### Конкретные технические выборы

**Модели:**

- **Primary coach**: GPT-4 Turbo (баланс качества/скорость/цена)
- **Memory operations**: Claude Opus 3.5 (лучший semantic understanding)
- **Pattern analysis**: Claude Haiku (быстрый, дешёвый)
- **Embeddings**: OpenAI text-embedding-3-small (1536 dim)

**Стратегия контекста:**

```
Core profile (500 tokens) ─────────┐
                                   ├─► CACHED 5min (Claude)
Top goals/barriers (800 tokens) ───┘

Session summary (300 tokens) ──────┐
                                   ├─► NOT CACHED
Relevant vector results (1000) ────┘

Total: ~2600 tokens context per request
Cost: ~90% saving on cached portion
```

**Обновление данных:**

- **Real-time**: Insights, breakthroughs, crisis markers
- **Daily**: Session summaries, pattern updates
- **Weekly**: Big Five recalibration (если drift > 5 points)
- **Monthly**: Goals/barriers reorganization, clustering


### Метрики для отслеживания

```python
# KPIs для "качества знания"
metrics = {
    "alliance_indicators": {
        "user_initiated_conversations": "count",  # Replika insight
        "reference_to_past_acceptance": "% positive",  # "Yes, exactly!"
        "session_length": "avg tokens",  # Engagement
        "return_rate": "% users returning within 7 days"
    },
    
    "personalization_quality": {
        "personality_adaptation_score": "1-10",  # Manual review
        "relevant_context_retrieved": "% precision",
        "contradiction_detection_rate": "count per 100 sessions"
    },
    
    "therapeutic_effectiveness": {
        "breakthrough_moments": "count per user per month",
        "goal_progress_tracking": "self-reported 1-10",
        "pattern_recognition_by_user": "count"  # User says "I see the pattern"
    }
}
```


***

## ФИНАЛЬНЫЙ CHECKLIST

**Phase 1: MVP (2-4 weeks)**

- [ ] Core profile caching (Big Five + top goals/barriers)
- [ ] GPT-4 Turbo as primary responder
- [ ] Basic personality adaptations (5 prompts for OCEAN)
- [ ] PostgreSQL + Redis caching
- [ ] Crisis detection → escalation
- [ ] Session summaries (batch end-of-day)

**Phase 2: Enhanced Memory (4-6 weeks)**

- [ ] Qdrant integration for semantic search
- [ ] Vector search goals/barriers on relevant queries
- [ ] Insight extraction + breakthrough detection
- [ ] Multi-agent architecture (Memory + Response + Analyzer)
- [ ] Prompt caching optimization (Claude)

**Phase 3: Advanced Personalization (6-8 weeks)**

- [ ] IFS protocol implementation
- [ ] ACT values alignment checks
- [ ] Schema detection from patterns
- [ ] Contradiction detection system
- [ ] Recurring theme analysis (BERTopic)
- [ ] Weekly Big Five recalibration

**Phase 4: Production Hardening (8+ weeks)**

- [ ] Human oversight dashboard for therapists
- [ ] A/B testing personality adaptations
- [ ] Therapeutic alliance measurement
- [ ] Privacy audit (GDPR/HIPAA equivalents)
- [ ] Clinical validation study

***

Это comprehensive архитектура основана на актуальных исследованиях 2024-2025 и production examples от Replika, Woebot, Wysa, Therabot. Ключевые принципы: **иерархическая память**, **personality-adaptive communication**, **therapeutic frameworks как протоколы**, **ethical boundaries hardcoded**, **alliance через consistency + personalization**.
<span style="display:none">[^1_30][^1_31][^1_32][^1_33][^1_34][^1_35][^1_36][^1_37][^1_40][^1_41][^1_42][^1_43][^1_44][^1_45][^1_46][^1_47][^1_48][^1_49][^1_50][^1_51][^1_52][^1_53][^1_54][^1_55][^1_56][^1_57][^1_58][^1_59][^1_60][^1_61][^1_62][^1_63][^1_64][^1_65][^1_66][^1_67][^1_68][^1_70][^1_71][^1_72][^1_73][^1_74][^1_75]</span>

<div align="center">⁂</div>

[^1_1]: https://ora.ox.ac.uk/objects/uuid:c46ead55-3979-4859-933a-eda812ee9062/files/s3r074x57c

[^1_2]: http://arxiv.org/pdf/2304.03442v2.pdf

[^1_3]: https://arxiv.org/abs/2409.14908

[^1_4]: http://arxiv.org/pdf/2406.05925.pdf

[^1_5]: https://arxiv.org/pdf/2308.15022.pdf

[^1_6]: https://home.dartmouth.edu/news/2025/03/first-therapy-chatbot-trial-yields-mental-health-benefits

[^1_7]: https://aclanthology.org/2025.findings-acl.328

[^1_8]: https://dl.acm.org/doi/10.1145/3698587.3701489

[^1_9]: http://arxiv.org/pdf/2410.16491.pdf

[^1_10]: https://arxiv.org/html/2506.15928v1

[^1_11]: https://mental.jmir.org/2025/1/e69294

[^1_12]: https://library.iated.org/download/MAI2020AIC

[^1_13]: https://caylent.com/blog/prompt-caching-saving-time-and-money-in-llm-applications

[^1_14]: https://kinde.com/learn/ai-for-software-engineering/prompting/prompt-caching-strategies/

[^1_15]: https://labs.adaline.ai/p/what-is-prompt-caching-how-can-product

[^1_16]: https://doi.apa.org/doi/10.1037/tra0001688

[^1_17]: https://pmc.ncbi.nlm.nih.gov/articles/PMC11983591/

[^1_18]: https://arxiv.org/pdf/2403.10779.pdf

[^1_19]: https://www.linkedin.com/pulse/how-create-ai-mental-health-chatbot-truly-helps-biz4group-m6myc

[^1_20]: https://pulitzercenter.org/stories/when-your-psychologist-ai

[^1_21]: https://pmc.ncbi.nlm.nih.gov/articles/PMC12434366/

[^1_22]: https://partsandself.org/expanding-internal-family-systems-through-ai-limitless-possibilities-for-integration/

[^1_23]: https://allbein.gs/ifs/

[^1_24]: https://www.linkedin.com/posts/nsbarr_enhancing-self-therapy-with-internal-family-activity-7120419832084209664-9gPB

[^1_25]: https://repository.derby.ac.uk/download/2645cc5d055fb81d24a4c6055553218010735fb2b66f95b35272437dc780ad2a/979593/Journal_of_Medical_Artificial_Intelligence_chatbot_mentalhealth%20(1).pdf

[^1_26]: https://www.reddit.com/r/therapyGPT/comments/1kwkstm/the_prompt_i_use_to_get_the_best_results_when/

[^1_27]: https://akjournals.com/view/journals/2054/aop/article-10.1556-2054.2024.00265/article-10.1556-2054.2024.00265.xml

[^1_28]: https://pmc.ncbi.nlm.nih.gov/articles/PMC11832678/

[^1_29]: https://www.frontiersin.org/articles/10.3389/fpsyt.2019.00746/pdf

[^1_30]: https://journal.media-culture.org.au/index.php/mcjournal/article/view/3141

[^1_31]: https://arxiv.org/pdf/2503.08102.pdf

[^1_32]: http://arxiv.org/pdf/2204.01611.pdf

[^1_33]: http://arxiv.org/pdf/2405.16751.pdf

[^1_34]: https://arxiv.org/pdf/2403.02135.pdf

[^1_35]: https://obot.ai/resources/learning-center/retrieval-augmented-generation/

[^1_36]: https://zilliz.com/learn/build-interactive-AI-chatbots-with-vector-database

[^1_37]: https://recapall.app/blog/character-ai-alternative

[^1_38]: https://dometrain.com/course/lets-build-it-ai-chatbot-with-rag-in-dotnet-using-your-data/

[^1_39]: https://creataai.com/blog/vector-database-chatbot-intelligence

[^1_40]: https://www.reddit.com/r/replika/comments/1p9bxjj/the_replika_ai_companion_memory_recall_continuity/

[^1_41]: https://learn.microsoft.com/en-us/azure/search/retrieval-augmented-generation-overview

[^1_42]: https://www.youtube.com/watch?v=YDSn8FP8Eig

[^1_43]: https://arxiv.org/html/2511.14972v1

[^1_44]: https://journal.minangdarussalam.or.id/index.php/djpe/article/view/252

[^1_45]: https://www.mdpi.com/2079-9292/13/23/4751

[^1_46]: http://ecsenet.com/index.php/2576-683X/article/view/231

[^1_47]: https://www.mdpi.com/2073-8994/16/12/1608

[^1_48]: https://tepsyj.ru/articles/article/4607/

[^1_49]: https://invergejournals.com/index.php/ijss/article/view/90

[^1_50]: https://journal.media-culture.org.au/index.php/mcjournal/article/view/3119

[^1_51]: https://www.mdpi.com/2071-1050/16/24/11106

[^1_52]: https://arxiv.org/html/2406.16223

[^1_53]: http://arxiv.org/pdf/2312.16070.pdf

[^1_54]: https://arxiv.org/pdf/2405.13052.pdf

[^1_55]: https://onlinelibrary.wiley.com/doi/pdfdirect/10.1111/spc3.12624

[^1_56]: https://arxiv.org/pdf/2503.17085.pdf

[^1_57]: http://arxiv.org/pdf/2502.08265.pdf

[^1_58]: https://arxiv.org/pdf/2204.12000.pdf

[^1_59]: https://kdd-eval-workshop.github.io/genai-evaluation-kdd2025/assets/papers/Submission 36.pdf

[^1_60]: https://www.sciencedirect.com/science/article/pii/S0001691825010224

[^1_61]: https://pressto.amu.edu.pl/index.php/n/article/download/45291/40364

[^1_62]: https://hcjournal.arums.ac.ir/article-1-1601-en.html

[^1_63]: https://scholar.kyobobook.co.kr/article/detail/4050067913896

[^1_64]: https://www.tandfonline.com/doi/full/10.1080/07421656.2023.2292902

[^1_65]: https://www.worldscientific.com/doi/10.1142/S2810968623500043

[^1_66]: https://bujhss.bahria.edu.pk/index.php/ojs/article/view/156/57

[^1_67]: https://www.tandfonline.com/doi/full/10.1080/07347324.2020.1846479

[^1_68]: https://journals.kmanpub.com/index.php/jayps/article/view/4208

[^1_69]: https://www.tandfonline.com/doi/full/10.1080/10926771.2021.2013375

[^1_70]: https://arxiv.org/pdf/2401.03631.pdf

[^1_71]: https://pmc.ncbi.nlm.nih.gov/articles/PMC11626650/

[^1_72]: https://pmc.ncbi.nlm.nih.gov/articles/PMC10845126/

[^1_73]: https://www.mdpi.com/1660-4601/19/13/7737/pdf?version=1656053183

[^1_74]: https://research.aimultiple.com/therapist-chatbot/

[^1_75]: https://www.reddit.com/r/InternalFamilySystems/comments/146p1rq/ifs_ai_therapy_tool/

