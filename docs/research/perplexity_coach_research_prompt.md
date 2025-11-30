# Промпт для исследования в Perplexity

## Основной запрос

```
Исследуй архитектуру AI-коуча который "знает всё" о пользователе и может отвечать на вопросы о его личности.

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
