# АРХИТЕКТУРНЫЙ ПЛАН РАЗДЕЛЕНИЯ SELFOLOGY НА НЕЗАВИСИМЫЕ СИСТЕМЫ

## СОДЕРЖАНИЕ
1. [Текущая Проблема](#текущая-проблема)
2. [Целевая Архитектура](#целевая-архитектура)
3. [Bounded Contexts (Границы Систем)](#bounded-contexts-границы-систем)
4. [Детальный План Разделения](#детальный-план-разделения)
5. [Владение Данными](#владение-данными)
6. [План Миграции](#план-миграции)

---

## ТЕКУЩАЯ ПРОБЛЕМА

### Диагностика Монолита

**Симптомы:**
- При изменении онбординга ломается система анализа
- Невозможно протестировать Telegram бот отдельно
- База данных смешивает данные разных доменов
- Изменение одного сервиса требует перезапуска всей системы

**Корневая Причина:**
Нарушение принципа **Single Responsibility** и отсутствие четких **Bounded Contexts**.

```
ТЕКУЩАЯ СТРУКТУРА (ПРОБЛЕМНАЯ):
┌─────────────────────────────────────────────────────┐
│                 МОНОЛИТНЫЙ БОТ                      │
│  selfology_controller.py (720 строк)               │
│  ├── Telegram handlers                             │
│  ├── Онбординг логика                              │
│  ├── Анализ ответов                                │
│  ├── Работа с векторами                            │
│  ├── Управление профилями                          │
│  └── Мониторинг и логирование                     │
└─────────────────────────────────────────────────────┘
             ↓ (все связано со всем)
┌─────────────────────────────────────────────────────┐
│            ЕДИНАЯ БАЗА ДАННЫХ                       │
│  - users (общие данные)                            │
│  - onboarding_sessions (онбординг)                 │
│  - user_answers_new (онбординг)                    │
│  - answer_analysis (анализ)                        │
│  - personality_profiles (профили)                  │
│  - trait_history (эволюция)                        │
│  - questions_metadata (вопросы)                    │
└─────────────────────────────────────────────────────┘
```

**Проблемы:**
1. **Tight Coupling** - все системы знают друг о друге
2. **Shared Database** - изменение схемы ломает все системы
3. **No Fault Isolation** - падение одной части роняет весь бот
4. **Difficult Testing** - невозможно тестировать компоненты изолированно

---

## ЦЕЛЕВАЯ АРХИТЕКТУРА

### Принципы Разделения

**1. Domain-Driven Design (DDD)**
- Каждая система = отдельный **Bounded Context**
- Явные границы и интерфейсы
- Собственные модели данных

**2. Микросервисная Архитектура (Lite)**
- Независимые модули внутри монорепозитория
- Асинхронная коммуникация через Events/Messages
- Каждый модуль может стать отдельным сервисом

**3. Event-Driven Architecture**
- Системы общаются через события
- Слабая связанность (loose coupling)
- Возможность масштабирования

```
ЦЕЛЕВАЯ АРХИТЕКТУРА:
┌──────────────────────────────────────────────────────────────────┐
│                      API GATEWAY LAYER                           │
│              (selfology_controller.py - упрощен)                │
│                    Только роутинг команд                         │
└──────────────────────────────────────────────────────────────────┘
                          ↓ (Events/Commands)
┌─────────────┬─────────────┬─────────────┬─────────────┬─────────┐
│  TELEGRAM   │  ONBOARDING │   ANALYSIS  │   PROFILE   │  COACH  │
│   SYSTEM    │   SYSTEM    │   SYSTEM    │   SYSTEM    │ SYSTEM  │
│             │             │             │             │         │
│ - Commands  │ - Questions │ - Answer    │ - Soul      │ - Chat  │
│ - Messages  │ - Router    │   Analysis  │   Architect │ - AI    │
│ - FSM       │ - Sessions  │ - Traits    │ - Evolution │ - Ctx   │
│             │ - Fatigue   │ - Vectors   │             │         │
└─────┬───────┴──────┬──────┴──────┬──────┴──────┬──────┴────┬────┘
      ↓              ↓             ↓             ↓           ↓
┌─────────────┬─────────────┬─────────────┬─────────────┬─────────┐
│  telegram_  │ onboarding_ │ analysis_   │ profiles_   │ coach_  │
│  events DB  │ sessions DB │ results DB  │ store DB    │ conv DB │
└─────────────┴─────────────┴─────────────┴─────────────┴─────────┘
```

### Преимущества Новой Архитектуры

**Изоляция Отказов:**
```python
# Если падает система анализа:
if analysis_system.is_down():
    # Онбординг продолжает работать
    # Анализ будет выполнен позже из очереди
    event_queue.push(AnalysisRequestedEvent(answer_id))
```

**Независимое Тестирование:**
```python
# Тест только онбординга БЕЗ других систем
@pytest.mark.unit
async def test_onboarding_question_selection():
    onboarding = OnboardingSystem(mock_db)
    question = await onboarding.get_next_question(user_id=123)
    assert question.domain == "IDENTITY"
```

**Независимое Развертывание:**
```bash
# Обновить только систему анализа
cd systems/analysis_system
docker build -t analysis:v2.0 .
docker-compose up -d analysis  # Остальные системы не затронуты
```

---

## BOUNDED CONTEXTS (ГРАНИЦЫ СИСТЕМ)

### 1. TELEGRAM INTERFACE SYSTEM

**Ответственность:**
- Прием команд от пользователя через Telegram
- Управление FSM состояниями
- Форматирование ответов (шаблоны)
- Валидация входных данных

**НЕ отвечает за:**
- Бизнес-логику онбординга/анализа/профилей
- Хранение сессий (только FSM state)
- AI обработку

**API:**
```python
class TelegramSystem:
    async def handle_start_command(user_id: int) -> None
    async def handle_text_message(user_id: int, text: str) -> None
    async def send_message(user_id: int, message: Message) -> None
    async def get_user_state(user_id: int) -> FSMState
```

**События (publishes):**
```python
UserStartedEvent(user_id, telegram_data)
UserSentAnswerEvent(user_id, answer_text, question_id)
UserRequestedProfileEvent(user_id)
```

**События (subscribes):**
```python
ShowQuestionEvent(user_id, question_data)
ShowInsightEvent(user_id, insight)
ShowProfileEvent(user_id, profile_data)
```

**Данные (владеет):**
```sql
-- telegram_users (минимум для работы бота)
CREATE TABLE telegram_users (
    telegram_id BIGINT PRIMARY KEY,
    username VARCHAR(255),
    first_name VARCHAR(255),
    last_name VARCHAR(255),
    language_code VARCHAR(10),
    created_at TIMESTAMP DEFAULT NOW()
);

-- telegram_fsm_states (состояния FSM)
CREATE TABLE telegram_fsm_states (
    telegram_id BIGINT PRIMARY KEY,
    state VARCHAR(50),
    state_data JSONB,
    updated_at TIMESTAMP DEFAULT NOW()
);
```

---

### 2. ONBOARDING SYSTEM

**Ответственность:**
- Умный выбор вопросов (Smart Mix алгоритм)
- Управление сессиями онбординга
- Детекция усталости пользователя
- Энергетический баланс (HEAVY → HEALING)

**НЕ отвечает за:**
- Анализ ответов (делегирует Analysis System)
- Создание профилей (делегирует Profile System)
- Отправку сообщений (делегирует Telegram System)

**API:**
```python
class OnboardingSystem:
    async def start_onboarding(user_id: int) -> Session
    async def get_next_question(session_id: str) -> Question
    async def record_answer(session_id: str, answer: str) -> None
    async def check_fatigue(session_id: str) -> FatigueLevel
    async def complete_onboarding(session_id: str) -> Summary
```

**События (publishes):**
```python
OnboardingStartedEvent(user_id, session_id)
QuestionAnsweredEvent(session_id, question_id, answer)
FatigueDetectedEvent(session_id, level)
OnboardingCompletedEvent(session_id, answers_count)
```

**События (subscribes):**
```python
UserStartedEvent(user_id)  # От Telegram
AnalysisCompletedEvent(answer_id, traits)  # От Analysis
```

**Данные (владеет):**
```sql
-- onboarding_sessions (управление сессиями)
CREATE TABLE onboarding_sessions (
    session_id UUID PRIMARY KEY,
    user_id INTEGER NOT NULL,  -- Ссылка на внешнюю систему
    status VARCHAR(20),
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    questions_asked INTEGER,
    current_strategy VARCHAR(20),
    fatigue_level FLOAT
);

-- session_answers (ответы в контексте сессии)
CREATE TABLE session_answers (
    id SERIAL PRIMARY KEY,
    session_id UUID REFERENCES onboarding_sessions(session_id),
    question_id VARCHAR(10),
    raw_answer TEXT,
    answered_at TIMESTAMP
);

-- questions_metadata (метаданные вопросов)
CREATE TABLE questions_metadata (
    question_id VARCHAR(10) PRIMARY KEY,
    domain VARCHAR(20),
    depth_level VARCHAR(15),
    energy VARCHAR(15),
    is_flagged BOOLEAN DEFAULT false,
    flagged_reason TEXT
);
```

---

### 3. ANALYSIS SYSTEM

**Ответственность:**
- Глубокий AI анализ ответов
- Извлечение черт личности (trait extraction)
- Создание векторных представлений
- Роутинг между AI моделями (Claude/GPT-4/GPT-4o-mini)

**НЕ отвечает за:**
- Сохранение профилей (делегирует Profile System)
- Выбор следующего вопроса (делегирует Onboarding)
- Показ результатов пользователю (делегирует Telegram)

**API:**
```python
class AnalysisSystem:
    async def analyze_answer(
        answer_id: str,
        question_data: dict,
        answer_text: str,
        context: dict
    ) -> AnalysisResult

    async def extract_traits(analysis: AnalysisResult) -> Traits
    async def create_embedding(text: str) -> Vector
    async def get_analysis_status(answer_id: str) -> Status
```

**События (publishes):**
```python
AnalysisStartedEvent(answer_id)
AnalysisCompletedEvent(answer_id, traits, insights)
TraitsExtractedEvent(answer_id, big_five, dynamics)
VectorCreatedEvent(answer_id, vector_id)
CrisisDetectedEvent(answer_id, severity)  # Критично!
```

**События (subscribes):**
```python
QuestionAnsweredEvent(session_id, question_id, answer)
ReanalysisRequestedEvent(answer_id, reason)
```

**Данные (владеет):**
```sql
-- analysis_queue (очередь на анализ)
CREATE TABLE analysis_queue (
    id SERIAL PRIMARY KEY,
    answer_id INTEGER UNIQUE,
    priority INTEGER DEFAULT 0,
    status VARCHAR(20),
    attempts INTEGER DEFAULT 0,
    created_at TIMESTAMP,
    processed_at TIMESTAMP
);

-- analysis_results (результаты анализа)
CREATE TABLE analysis_results (
    id SERIAL PRIMARY KEY,
    answer_id INTEGER UNIQUE,
    analysis_version VARCHAR(10),

    -- AI анализ
    psychological_insights JSONB,
    emotional_state VARCHAR(30),

    -- Метаданные обработки
    ai_model_used VARCHAR(30),
    processing_time_ms INTEGER,
    confidence_score FLOAT,

    -- Специальные ситуации
    special_situation VARCHAR(20),  -- crisis, breakthrough

    processed_at TIMESTAMP
);

-- extracted_traits (извлеченные черты)
CREATE TABLE extracted_traits (
    id SERIAL PRIMARY KEY,
    analysis_id INTEGER REFERENCES analysis_results(id),

    -- Big Five
    openness FLOAT,
    conscientiousness FLOAT,
    extraversion FLOAT,
    agreeableness FLOAT,
    neuroticism FLOAT,

    -- Динамические черты
    resilience FLOAT,
    authenticity FLOAT,
    growth_mindset FLOAT,

    -- Метаданные
    confidence_scores JSONB,
    extracted_at TIMESTAMP
);

-- vector_storage_refs (ссылки на Qdrant)
CREATE TABLE vector_storage_refs (
    id SERIAL PRIMARY KEY,
    analysis_id INTEGER REFERENCES analysis_results(id),
    vector_id UUID UNIQUE,
    collection_name VARCHAR(50),
    dimensions INTEGER,
    created_at TIMESTAMP
);
```

---

### 4. PROFILE SYSTEM (Soul Architect)

**Ответственность:**
- Создание и управление многослойными профилями
- Эволюция черт личности во времени
- Трекинг изменений (trait history)
- Построение психологического портрета

**НЕ отвечает за:**
- Анализ ответов (получает traits от Analysis)
- Онбординг (получает события о завершении)
- Рекомендации для коучинга (предоставляет данные Coach System)

**API:**
```python
class ProfileSystem:
    async def create_profile(user_id: int) -> ProfileId
    async def update_traits(profile_id: str, traits: dict) -> None
    async def get_profile(user_id: int) -> PersonalityProfile
    async def get_evolution(user_id: int, days: int) -> Evolution
    async def merge_analysis(profile_id: str, analysis: AnalysisResult) -> None
```

**События (publishes):**
```python
ProfileCreatedEvent(user_id, profile_id)
ProfileUpdatedEvent(profile_id, changed_traits)
TraitEvolvedEvent(profile_id, trait_name, old_value, new_value)
MilestoneReachedEvent(profile_id, milestone_type)
```

**События (subscribes):**
```python
OnboardingCompletedEvent(session_id)  # Создать начальный профиль
TraitsExtractedEvent(answer_id, traits)  # Обновить профиль
AnalysisCompletedEvent(answer_id)  # Интегрировать анализ
```

**Данные (владеет):**
```sql
-- personality_profiles (многослойные профили)
CREATE TABLE personality_profiles (
    profile_id UUID PRIMARY KEY,
    user_id INTEGER UNIQUE NOT NULL,

    -- Профиль как JSONB (все слои)
    profile_data JSONB NOT NULL,

    -- Метаданные
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    version INTEGER DEFAULT 1
);

-- trait_history (эволюция черт)
CREATE TABLE trait_history (
    id SERIAL PRIMARY KEY,
    profile_id UUID REFERENCES personality_profiles(profile_id),

    trait_category VARCHAR(50),  -- big_five, core_dynamics
    trait_name VARCHAR(50),

    old_value FLOAT,
    new_value FLOAT,
    confidence FLOAT,

    trigger VARCHAR(100),  -- что вызвало изменение
    timestamp TIMESTAMP
);

-- profile_milestones (важные моменты)
CREATE TABLE profile_milestones (
    id SERIAL PRIMARY KEY,
    profile_id UUID REFERENCES personality_profiles(profile_id),

    milestone_type VARCHAR(50),  -- breakthrough, crisis_resolved
    description TEXT,
    significance_score FLOAT,

    created_at TIMESTAMP
);
```

---

### 5. COACH SYSTEM (AI Коучинг)

**Ответственность:**
- Персонализированные диалоги с AI
- Контекстные рекомендации на основе профиля
- Управление чат-сессиями
- Генерация инсайтов

**НЕ отвечает за:**
- Обновление профиля (делегирует Profile System)
- Анализ глубоких ответов (делегирует Analysis System)
- Онбординг (отдельная система)

**API:**
```python
class CoachSystem:
    async def start_chat_session(user_id: int) -> SessionId
    async def process_message(session_id: str, message: str) -> Response
    async def get_recommendations(user_id: int) -> List[Recommendation]
    async def generate_insight(user_id: int, context: dict) -> Insight
```

**События (publishes):**
```python
ChatSessionStartedEvent(user_id, session_id)
MessageProcessedEvent(session_id, message_id, response)
InsightGeneratedEvent(user_id, insight)
RecommendationCreatedEvent(user_id, recommendation)
```

**События (subscribes):**
```python
ProfileUpdatedEvent(profile_id)  # Обновить контекст
MilestoneReachedEvent(profile_id)  # Поздравить пользователя
CrisisDetectedEvent(answer_id)  # Предложить поддержку
```

**Данные (владеет):**
```sql
-- chat_sessions (сессии коучинга)
CREATE TABLE chat_sessions (
    session_id UUID PRIMARY KEY,
    user_id INTEGER NOT NULL,

    started_at TIMESTAMP,
    last_activity TIMESTAMP,
    status VARCHAR(20),

    -- Контекст сессии
    session_context JSONB
);

-- chat_messages (сообщения)
CREATE TABLE chat_messages (
    id SERIAL PRIMARY KEY,
    session_id UUID REFERENCES chat_sessions(session_id),

    role VARCHAR(20),  -- user, assistant
    content TEXT,

    -- AI метаданные
    model_used VARCHAR(30),
    tokens_used INTEGER,

    created_at TIMESTAMP
);

-- generated_insights (сгенерированные инсайты)
CREATE TABLE generated_insights (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,

    insight_type VARCHAR(50),
    content TEXT,
    relevance_score FLOAT,

    source VARCHAR(50),  -- chat, analysis, milestone
    created_at TIMESTAMP
);

-- recommendations (рекомендации)
CREATE TABLE recommendations (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,

    recommendation_type VARCHAR(50),
    title TEXT,
    description TEXT,
    priority INTEGER,

    status VARCHAR(20),  -- pending, accepted, dismissed
    created_at TIMESTAMP
);
```

---

### 6. MONITORING SYSTEM (Наблюдение)

**Ответственность:**
- Сбор метрик всех систем
- Логирование событий
- Алерты при проблемах
- Dashboard для мониторинга

**НЕ отвечает за:**
- Бизнес-логику
- Обработку событий (только логирует)

**API:**
```python
class MonitoringSystem:
    async def log_event(event: Event) -> None
    async def track_metric(metric_name: str, value: float) -> None
    async def get_system_health() -> HealthStatus
    async def get_metrics(timeframe: str) -> Metrics
```

**Данные (владеет):**
```sql
-- system_events (все события в системе)
CREATE TABLE system_events (
    id BIGSERIAL PRIMARY KEY,
    event_type VARCHAR(100),
    system_name VARCHAR(50),

    event_data JSONB,

    user_id INTEGER,
    session_id UUID,

    created_at TIMESTAMP,

    -- Партиционирование по дате
    PARTITION BY RANGE (created_at)
);

-- system_metrics (метрики производительности)
CREATE TABLE system_metrics (
    id SERIAL PRIMARY KEY,
    metric_name VARCHAR(100),
    system_name VARCHAR(50),

    value FLOAT,

    timestamp TIMESTAMP,

    -- Партиционирование по дате
    PARTITION BY RANGE (timestamp)
);
```

---

## ДЕТАЛЬНЫЙ ПЛАН РАЗДЕЛЕНИЯ

### ЭТАП 1: ПОДГОТОВКА (1-2 дня)

**1.1. Создать Event Bus**
```python
# core/events/event_bus.py
class EventBus:
    """Центральная шина событий для асинхронной коммуникации"""

    def __init__(self):
        self.subscribers = defaultdict(list)

    async def publish(self, event: Event) -> None:
        """Опубликовать событие"""
        for handler in self.subscribers[event.type]:
            await handler(event)

    def subscribe(self, event_type: str, handler: Callable) -> None:
        """Подписаться на тип события"""
        self.subscribers[event_type].append(handler)

# core/events/base.py
@dataclass
class Event:
    """Базовый класс события"""
    event_id: str
    event_type: str
    timestamp: datetime
    source_system: str
    data: dict
```

**1.2. Определить Domain Events**
```python
# systems/onboarding/events.py
@dataclass
class OnboardingStartedEvent(Event):
    user_id: int
    session_id: str

@dataclass
class QuestionAnsweredEvent(Event):
    session_id: str
    question_id: str
    answer_text: str
```

**1.3. Создать System Interfaces**
```python
# systems/base.py
class BaseSystem(ABC):
    """Базовый класс для всех систем"""

    def __init__(self, event_bus: EventBus, db_pool: asyncpg.Pool):
        self.event_bus = event_bus
        self.db = db_pool
        self._register_handlers()

    @abstractmethod
    def _register_handlers(self) -> None:
        """Зарегистрировать обработчики событий"""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Проверка здоровья системы"""
        pass
```

---

### ЭТАП 2: ИЗВЛЕЧЕНИЕ СИСТЕМ (3-5 дней)

**2.1. Извлечь Onboarding System**
```bash
mkdir -p systems/onboarding_system
cd systems/onboarding_system
```

```python
# systems/onboarding_system/service.py
class OnboardingSystem(BaseSystem):
    """Независимая система онбординга"""

    def __init__(self, event_bus: EventBus, db_pool: asyncpg.Pool):
        super().__init__(event_bus, db_pool)
        self.question_router = QuestionRouter()
        self.fatigue_detector = FatigueDetector()

    def _register_handlers(self):
        # Подписываемся на события от других систем
        self.event_bus.subscribe(
            "UserStartedEvent",
            self.handle_user_started
        )
        self.event_bus.subscribe(
            "AnalysisCompletedEvent",
            self.handle_analysis_completed
        )

    async def handle_user_started(self, event: UserStartedEvent):
        """Обработчик: пользователь начал работу"""
        session = await self.start_onboarding(event.user_id)

        # Публикуем событие
        await self.event_bus.publish(OnboardingStartedEvent(
            user_id=event.user_id,
            session_id=session.session_id
        ))

        # Выбираем первый вопрос
        question = await self.get_next_question(session.session_id)

        # Публикуем событие для Telegram System
        await self.event_bus.publish(ShowQuestionEvent(
            user_id=event.user_id,
            question_data=question
        ))
```

**2.2. Извлечь Analysis System**
```python
# systems/analysis_system/service.py
class AnalysisSystem(BaseSystem):
    """Независимая система анализа"""

    def __init__(self, event_bus: EventBus, db_pool: asyncpg.Pool):
        super().__init__(event_bus, db_pool)
        self.answer_analyzer = AnswerAnalyzer()
        self.trait_extractor = TraitExtractor()
        self.embedding_creator = EmbeddingCreator()

        # Очередь для асинхронной обработки
        self.analysis_queue = asyncio.Queue()

        # Запускаем воркер
        asyncio.create_task(self._process_queue())

    def _register_handlers(self):
        self.event_bus.subscribe(
            "QuestionAnsweredEvent",
            self.handle_question_answered
        )

    async def handle_question_answered(self, event: QuestionAnsweredEvent):
        """Обработчик: пользователь ответил на вопрос"""

        # Добавляем в очередь (не блокируем)
        await self.analysis_queue.put({
            'session_id': event.session_id,
            'question_id': event.question_id,
            'answer_text': event.answer_text
        })

        # Мгновенный ответ пользователю
        await self.event_bus.publish(QuickFeedbackEvent(
            session_id=event.session_id,
            feedback="Спасибо за ответ! Анализирую..."
        ))

    async def _process_queue(self):
        """Воркер для обработки очереди анализа"""
        while True:
            item = await self.analysis_queue.get()

            try:
                # Глубокий анализ (2-10 секунд)
                result = await self.answer_analyzer.analyze_answer(
                    question_id=item['question_id'],
                    answer_text=item['answer_text']
                )

                # Извлекаем черты
                traits = await self.trait_extractor.extract_traits(result)

                # Создаем вектор
                vector_id = await self.embedding_creator.create_embedding(result)

                # Публикуем событие завершения
                await self.event_bus.publish(AnalysisCompletedEvent(
                    session_id=item['session_id'],
                    question_id=item['question_id'],
                    traits=traits,
                    insights=result.insights,
                    vector_id=vector_id
                ))

            except Exception as e:
                logger.error(f"Analysis failed: {e}")
                # Публикуем событие ошибки
                await self.event_bus.publish(AnalysisFailedEvent(
                    session_id=item['session_id'],
                    error=str(e)
                ))

            finally:
                self.analysis_queue.task_done()
```

**2.3. Извлечь Profile System**
```python
# systems/profile_system/service.py
class ProfileSystem(BaseSystem):
    """Независимая система профилей (Soul Architect)"""

    def __init__(self, event_bus: EventBus, db_pool: asyncpg.Pool):
        super().__init__(event_bus, db_pool)
        self.profile_builder = ProfileBuilder()
        self.trait_scorer = TraitScorer()
        self.evolution_tracker = EvolutionTracker()

    def _register_handlers(self):
        self.event_bus.subscribe(
            "OnboardingCompletedEvent",
            self.handle_onboarding_completed
        )
        self.event_bus.subscribe(
            "TraitsExtractedEvent",
            self.handle_traits_extracted
        )

    async def handle_onboarding_completed(self, event: OnboardingCompletedEvent):
        """Создать начальный профиль после завершения онбординга"""

        # Получаем все ответы сессии
        answers = await self._get_session_answers(event.session_id)

        # Получаем все анализы
        analyses = await self._get_session_analyses(event.session_id)

        # Создаем профиль
        profile = await self.create_profile_from_analyses(
            user_id=event.user_id,
            analyses=analyses
        )

        # Публикуем событие
        await self.event_bus.publish(ProfileCreatedEvent(
            user_id=event.user_id,
            profile_id=profile.profile_id
        ))

    async def handle_traits_extracted(self, event: TraitsExtractedEvent):
        """Обновить профиль новыми чертами"""

        # Получаем текущий профиль
        profile = await self.get_profile(user_id=event.user_id)

        # Обновляем черты
        for trait_name, trait_value in event.traits.items():
            await self.update_trait(
                profile_id=profile.profile_id,
                trait_name=trait_name,
                value=trait_value
            )

        # Публикуем событие
        await self.event_bus.publish(ProfileUpdatedEvent(
            profile_id=profile.profile_id,
            changed_traits=list(event.traits.keys())
        ))
```

**2.4. Извлечь Telegram System**
```python
# systems/telegram_system/service.py
class TelegramSystem(BaseSystem):
    """Независимая система Telegram интерфейса"""

    def __init__(
        self,
        event_bus: EventBus,
        db_pool: asyncpg.Pool,
        bot_token: str
    ):
        super().__init__(event_bus, db_pool)

        self.bot = Bot(token=bot_token)
        self.dp = Dispatcher(storage=MemoryStorage())
        self.messages = MessageService()

        self._register_telegram_handlers()

    def _register_handlers(self):
        """Регистрация обработчиков событий от других систем"""
        self.event_bus.subscribe(
            "ShowQuestionEvent",
            self.handle_show_question
        )
        self.event_bus.subscribe(
            "ShowProfileEvent",
            self.handle_show_profile
        )
        self.event_bus.subscribe(
            "ShowInsightEvent",
            self.handle_show_insight
        )

    def _register_telegram_handlers(self):
        """Регистрация обработчиков команд Telegram"""
        self.dp.message.register(self.cmd_start, CommandStart())
        self.dp.message.register(self.cmd_profile, Command("profile"))
        self.dp.message.register(
            self.handle_text_message,
            F.text,
            OnboardingStates.waiting_for_answer
        )

    async def cmd_start(self, message: Message, state: FSMContext):
        """Команда /start - только роутинг"""

        # Публикуем событие в Event Bus
        await self.event_bus.publish(UserStartedEvent(
            user_id=message.from_user.id,
            telegram_data={
                'username': message.from_user.username,
                'first_name': message.from_user.first_name,
                'last_name': message.from_user.last_name
            }
        ))

        # Устанавливаем состояние FSM
        await state.set_state(OnboardingStates.gdpr_consent)

    async def handle_text_message(self, message: Message, state: FSMContext):
        """Обработка текстовых сообщений - только роутинг"""

        # Получаем контекст FSM
        data = await state.get_data()

        if data.get('current_question_id'):
            # Публикуем событие ответа
            await self.event_bus.publish(QuestionAnsweredEvent(
                session_id=data['session_id'],
                question_id=data['current_question_id'],
                answer_text=message.text
            ))

    async def handle_show_question(self, event: ShowQuestionEvent):
        """Обработчик события: показать вопрос пользователю"""

        # Форматируем сообщение
        text = self.messages.format_question(
            question_data=event.question_data
        )

        keyboard = self.messages.get_keyboard('onboarding_controls')

        # Отправляем пользователю
        await self.bot.send_message(
            chat_id=event.user_id,
            text=text,
            reply_markup=keyboard
        )
```

**2.5. Извлечь Coach System**
```python
# systems/coach_system/service.py
class CoachSystem(BaseSystem):
    """Независимая система AI коучинга"""

    def __init__(self, event_bus: EventBus, db_pool: asyncpg.Pool):
        super().__init__(event_bus, db_pool)
        self.ai_router = AIModelRouter()
        self.context_builder = ContextBuilder()

    def _register_handlers(self):
        self.event_bus.subscribe(
            "ChatMessageReceivedEvent",
            self.handle_chat_message
        )
        self.event_bus.subscribe(
            "ProfileUpdatedEvent",
            self.handle_profile_updated
        )

    async def handle_chat_message(self, event: ChatMessageReceivedEvent):
        """Обработать сообщение в чате"""

        # Получаем контекст пользователя
        context = await self.context_builder.build_context(
            user_id=event.user_id
        )

        # Генерируем ответ с учетом профиля
        response = await self.ai_router.generate_response(
            message=event.message,
            context=context
        )

        # Публикуем событие ответа
        await self.event_bus.publish(ChatResponseGeneratedEvent(
            user_id=event.user_id,
            session_id=event.session_id,
            response=response
        ))
```

---

### ЭТАП 3: МИГРАЦИЯ БАЗ ДАННЫХ (2-3 дня)

**3.1. Разделение схем**
```sql
-- Создать отдельные схемы для каждой системы
CREATE SCHEMA telegram_system;
CREATE SCHEMA onboarding_system;
CREATE SCHEMA analysis_system;
CREATE SCHEMA profile_system;
CREATE SCHEMA coach_system;

-- Мигрировать таблицы
-- Пример: перенести onboarding_sessions в onboarding_system schema
ALTER TABLE selfology.onboarding_sessions
    SET SCHEMA onboarding_system;

ALTER TABLE selfology.user_answers_new
    SET SCHEMA onboarding_system;

-- Profile System
ALTER TABLE selfology.personality_profiles
    SET SCHEMA profile_system;

ALTER TABLE selfology.trait_history
    SET SCHEMA profile_system;

-- Analysis System
ALTER TABLE selfology.answer_analysis
    SET SCHEMA analysis_system;
```

**3.2. Создать связи через Events**
```sql
-- Вместо прямых foreign key используем event tracking
CREATE TABLE onboarding_system.external_events (
    id SERIAL PRIMARY KEY,
    event_type VARCHAR(100),
    event_data JSONB,
    source_system VARCHAR(50),
    processed BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Индексы для быстрой обработки
CREATE INDEX idx_external_events_type
    ON onboarding_system.external_events(event_type);

CREATE INDEX idx_external_events_unprocessed
    ON onboarding_system.external_events(processed)
    WHERE processed = false;
```

---

### ЭТАП 4: ИНТЕГРАЦИЯ (2-3 дня)

**4.1. Обновить Controller**
```python
# selfology_controller.py (теперь только Gateway)
class SelfologyController:
    """API Gateway - только роутинг к системам"""

    def __init__(self):
        # Инициализируем Event Bus
        self.event_bus = EventBus()

        # Инициализируем БД пулы для каждой системы
        self.db_pools = await self._create_db_pools()

        # Инициализируем системы
        self.telegram_system = TelegramSystem(
            self.event_bus,
            self.db_pools['telegram'],
            BOT_TOKEN
        )

        self.onboarding_system = OnboardingSystem(
            self.event_bus,
            self.db_pools['onboarding']
        )

        self.analysis_system = AnalysisSystem(
            self.event_bus,
            self.db_pools['analysis']
        )

        self.profile_system = ProfileSystem(
            self.event_bus,
            self.db_pools['profile']
        )

        self.coach_system = CoachSystem(
            self.event_bus,
            self.db_pools['coach']
        )

        logger.info("All systems initialized and connected via Event Bus")

    async def _create_db_pools(self):
        """Создать отдельные connection pools для каждой системы"""
        return {
            'telegram': await asyncpg.create_pool(
                dsn=f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}",
                command_timeout=60,
                max_size=10,
                search_path='telegram_system'
            ),
            'onboarding': await asyncpg.create_pool(
                dsn=f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}",
                command_timeout=60,
                max_size=20,
                search_path='onboarding_system'
            ),
            # ... остальные пулы
        }

    async def start(self):
        """Запустить все системы"""

        # Проверяем здоровье всех систем
        health_checks = await asyncio.gather(
            self.telegram_system.health_check(),
            self.onboarding_system.health_check(),
            self.analysis_system.health_check(),
            self.profile_system.health_check(),
            self.coach_system.health_check()
        )

        if not all(health_checks):
            logger.error("Some systems failed health check")
            return False

        # Запускаем Telegram polling
        await self.telegram_system.start_polling()
```

---

## ВЛАДЕНИЕ ДАННЫМИ

### Принцип: "Каждая Система Владеет Своими Данными"

**Telegram System:**
- `telegram_users` - пользователи Telegram
- `telegram_fsm_states` - FSM состояния

**Onboarding System:**
- `onboarding_sessions` - сессии онбординга
- `session_answers` - ответы пользователей
- `questions_metadata` - метаданные вопросов

**Analysis System:**
- `analysis_queue` - очередь на анализ
- `analysis_results` - результаты AI анализа
- `extracted_traits` - извлеченные черты
- `vector_storage_refs` - ссылки на Qdrant

**Profile System:**
- `personality_profiles` - многослойные профили
- `trait_history` - история изменений черт
- `profile_milestones` - важные события

**Coach System:**
- `chat_sessions` - сессии коучинга
- `chat_messages` - сообщения
- `generated_insights` - инсайты
- `recommendations` - рекомендации

### Доступ к Данным Других Систем

**НЕЛЬЗЯ:** Прямой доступ к таблицам другой системы
```python
# ПЛОХО - прямой SELECT из чужой схемы
async def get_user_profile(user_id):
    return await db.fetchrow("""
        SELECT * FROM profile_system.personality_profiles
        WHERE user_id = $1
    """, user_id)
```

**МОЖНО:** Запрос через Event или API
```python
# ХОРОШО - запрос через Event Bus
async def get_user_profile(user_id):
    response = await self.event_bus.request(
        ProfileRequestedEvent(user_id=user_id)
    )
    return response.profile_data

# ХОРОШО - через прямой API (синхронный вызов)
async def get_user_profile(user_id):
    return await self.profile_system.get_profile(user_id)
```

### Shared Data (Общие Данные)

Некоторые данные нужны всем системам. Решение: **Shared Read-Only Views**

```sql
-- Создаем read-only view для общего доступа
CREATE SCHEMA shared;

CREATE VIEW shared.users_basic AS
SELECT
    telegram_id,
    username,
    first_name,
    created_at
FROM telegram_system.telegram_users;

-- Все системы могут читать, но не могут изменять
GRANT SELECT ON shared.users_basic TO onboarding_system_role;
GRANT SELECT ON shared.users_basic TO analysis_system_role;
GRANT SELECT ON shared.users_basic TO profile_system_role;
```

---

## ПЛАН МИГРАЦИИ

### Фаза 0: Подготовка (Неделя 1)
- [ ] Создать Event Bus инфраструктуру
- [ ] Определить все Domain Events
- [ ] Создать базовые интерфейсы систем
- [ ] Настроить CI/CD для тестирования изолированных систем

### Фаза 1: Извлечение Onboarding (Неделя 2)
- [ ] Создать `systems/onboarding_system/`
- [ ] Перенести QuestionRouter, FatigueDetector
- [ ] Создать OnboardingSystem с Event handlers
- [ ] Написать unit тесты
- [ ] Мигрировать схему БД: `onboarding_system`

### Фаза 2: Извлечение Analysis (Неделя 3)
- [ ] Создать `systems/analysis_system/`
- [ ] Перенести AnswerAnalyzer, TraitExtractor
- [ ] Создать асинхронную очередь обработки
- [ ] Написать unit тесты
- [ ] Мигрировать схему БД: `analysis_system`

### Фаза 3: Извлечение Profile (Неделя 4)
- [ ] Создать `systems/profile_system/`
- [ ] Перенести Soul Architect компоненты
- [ ] Интегрировать с Analysis через Events
- [ ] Написать unit тесты
- [ ] Мигрировать схему БД: `profile_system`

### Фаза 4: Извлечение Telegram (Неделя 5)
- [ ] Создать `systems/telegram_system/`
- [ ] Упростить `selfology_controller.py` до Gateway
- [ ] Перенести все FSM handlers
- [ ] Написать интеграционные тесты
- [ ] Мигрировать схему БД: `telegram_system`

### Фаза 5: Извлечение Coach (Неделя 6)
- [ ] Создать `systems/coach_system/`
- [ ] Перенести chat и AI components
- [ ] Интегрировать с Profile через Events
- [ ] Написать unit тесты
- [ ] Мигрировать схему БД: `coach_system`

### Фаза 6: Интеграция и Тестирование (Неделя 7-8)
- [ ] Полные интеграционные тесты всех систем
- [ ] Load testing (проверка изоляции отказов)
- [ ] Chaos engineering (отключать системы и проверять resilience)
- [ ] Performance optimization
- [ ] Документация архитектуры

### Фаза 7: Развертывание (Неделя 9)
- [ ] Постепенное развертывание (canary deployment)
- [ ] Мониторинг метрик
- [ ] Rollback plan
- [ ] Production validation

---

## ПРЕИМУЩЕСТВА НОВОЙ АРХИТЕКТУРЫ

### 1. Изоляция Отказов
```python
# Если Analysis System падает:
# - Onboarding продолжает работать
# - Ответы сохраняются в очередь
# - Анализ выполнится когда система восстановится

@retry(max_attempts=3, backoff=exponential)
async def process_analysis(answer_id):
    try:
        result = await analysis_system.analyze(answer_id)
    except AnalysisSystemDown:
        # Добавляем в очередь для retry
        await analysis_queue.push(answer_id, priority=HIGH)
        # Пользователь все равно получает ответ
        return {"status": "queued"}
```

### 2. Независимое Масштабирование
```yaml
# docker-compose.scale.yml
version: '3.8'
services:
  telegram_system:
    replicas: 2  # Telegram нужно 2 инстанса

  onboarding_system:
    replicas: 3  # Онбординг более загружен

  analysis_system:
    replicas: 5  # Анализ - самое тяжелое
    resources:
      limits:
        cpus: '2.0'
        memory: 4G

  profile_system:
    replicas: 2
```

### 3. Независимое Тестирование
```python
# tests/unit/test_onboarding_system.py
@pytest.mark.unit
async def test_question_selection_without_analysis():
    """Можем тестировать онбординг без системы анализа"""

    # Mock Event Bus
    event_bus = MockEventBus()

    # Mock DB (только onboarding schema)
    db = await create_test_db(schema='onboarding_system')

    # Создаем ТОЛЬКО onboarding system
    onboarding = OnboardingSystem(event_bus, db)

    # Тестируем изолированно
    session = await onboarding.start_onboarding(user_id=123)
    question = await onboarding.get_next_question(session.session_id)

    assert question is not None
    assert question['domain'] in CORE_DOMAINS
```

### 4. Безопасное Развертывание
```bash
# Обновить только Analysis System без downtime

# 1. Развернуть новую версию параллельно
docker-compose up -d analysis_system_v2

# 2. Переключить Event Bus на новую версию
kubectl set image deployment/analysis analysis=analysis:v2.0

# 3. Старая версия дообработает очередь и выключится
docker-compose stop analysis_system_v1

# Все остальные системы продолжают работать без перерыва
```

---

## ЗАКЛЮЧЕНИЕ

Эта архитектура решает ключевые проблемы:

1. **Модульность**: Каждая система - независимый модуль с четкими границами
2. **Изоляция**: Падение одной системы не ломает другие
3. **Тестируемость**: Каждую систему можно тестировать изолированно
4. **Масштабируемость**: Можно масштабировать только нагруженные системы
5. **Maintainability**: Изменения в одной системе не ломают другие

**Следующий Шаг:** Начать с Фазы 0 - создание Event Bus и определение Domain Events.
