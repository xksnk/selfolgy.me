# REFACTORING_RULES_SELFOLOGY.md
# Детальные правила глубокого рефакторинга для Selfology AI Psychology Coach

## 📋 МЕТАИНФОРМАЦИЯ

**Проект**: Selfology.me - AI Psychology Coach Telegram Bot
**Архитектура**: Clean Architecture + микросервисы + event-driven
**Стек**: Python/FastAPI/aiogram/PostgreSQL/Redis/Qdrant
**Уровень рефакторинга**: ГЛУБОКИЙ (реструктуризация + разбиение на микросервисы)
**Дата создания**: 2025-11-08

---

## 🎯 ЦЕЛИ РЕФАКТОРИНГА

### Первичные цели (КРИТИЧНО):
1. **Разбить монолитные файлы** >300 строк на атомарные компоненты
2. **Исправить архитектурные нарушения** Clean Architecture
3. **Устранить дублирование кода** (DRY principle)
4. **Синхронизировать async/await** паттерны

### Вторичные цели (ВАЖНО):
5. Оптимизировать AI роутинг для экономии 75%+ на API
6. Улучшить производительность Telegram FSM через Redis
7. Стандартизировать работу с векторными БД
8. Внедрить event-driven коммуникацию между сервисами

---

## 🚨 КРИТИЧЕСКИЕ ПРАВИЛА - НАРУШЕНИЕ = СТОП

### AI-АДАПТИВНОЕ ПРАВИЛО РАЗМЕРА ФАЙЛОВ

```yaml
ОБЫЧНЫЙ КОД (handlers, services, models):
  Атомарная функция:  ≤ 50 строк
  Атом (core/):       ≤ 150 строк
  Молекула (modules/): ≤ 250 строк
  Организм (features/): ≤ 300 строк

AI КОМПОНЕНТЫ (prompts, chains, routers):
  Промпт-функция:     ≤ 100 строк  # Промпты длиннее
  AI Атом:            ≤ 300 строк  # Контекст важнее
  AI Молекула:        ≤ 500 строк  # Цепочки вызовов
  AI Организм:        ≤ 600 строк  # Полный pipeline

ЕСЛИ файл превышает лимит:
  1. ОСТАНОВИТЬ добавление кода
  2. СОЗДАТЬ план разбиения
  3. ВЫПОЛНИТЬ разбиение
  4. ПРОДОЛЖИТЬ только после разбиения
```

### ПРАВИЛО АСИНХРОННОСТИ

```python
# ❌ ЗАПРЕЩЕНО - смешивание sync/async
class MixedService:
    def get_data(self):  # sync
        return self.db.query()

    async def process(self):  # async
        data = self.get_data()  # БАГ!

# ✅ ПРАВИЛЬНО - единообразная асинхронность
class AsyncService:
    async def get_data(self):
        return await self.db.query()

    async def process(self):
        data = await self.get_data()

# Правило: ВСЕ методы в классе либо sync, либо async
# Исключение: @property и __init__ могут быть sync
```

### ПРАВИЛО ЗАВИСИМОСТЕЙ

```yaml
МАКСИМАЛЬНОЕ количество импортов:
  core/:      0 импортов из проекта (только stdlib + libs)
  modules/:   ≤ 3 импорта из core/
  features/:  ≤ 5 импортов из core/ + modules/
  services/:  ≤ 7 импортов total

ЗАПРЕЩЕНО:
  - Циклические импорты
  - Импорт из верхнего уровня в нижний
  - Прямой импорт между features
```

---

## 📂 РЕФАКТОРИНГ СТРУКТУРЫ ПРОЕКТА

### Текущая структура → Целевая структура

```bash
# БЫЛО: Монолитная структура
selfology_bot/
├── bot/handlers/        # 929 строк в одном файле!
├── ai/router.py        # Весь роутинг в одном месте
└── services/           # Смешанная бизнес-логика

# СТАЛО: Микросервисная архитектура
selfology/
├── core/               # Чистые функции без зависимостей
│   ├── algorithms/     # AI роутинг, скоринг
│   ├── validators/     # Валидация данных
│   └── transformers/   # Преобразование форматов
│
├── infrastructure/     # Внешние зависимости
│   ├── telegram/      # aiogram, FSM, handlers
│   ├── database/      # SQLAlchemy, migrations
│   ├── cache/         # Redis клиенты
│   ├── vectors/       # Qdrant операции
│   └── ai_clients/    # OpenAI, Claude APIs
│
├── domain/            # Бизнес-логика
│   ├── psychology/    # Психологические модели
│   ├── assessment/    # Оценка состояния
│   ├── coaching/      # Коучинг логика
│   └── questions/     # Вопросы и программы
│
├── application/       # Use cases
│   ├── onboarding/    # Онбординг пользователя
│   ├── chat_session/  # Сессии общения
│   ├── analysis/      # Анализ ответов
│   └── reporting/     # Отчеты и метрики
│
└── presentation/      # API и интерфейсы
    ├── telegram_bot/  # Telegram entry point
    ├── rest_api/      # FastAPI endpoints
    └── admin_panel/   # Админка
```

---

## 🤖 СПЕЦИАЛЬНЫЕ ПРАВИЛА ДЛЯ AI КОМПОНЕНТОВ

### 1. Рефакторинг AI Router

```python
# ❌ АНТИПАТТЕРН: Монолитный роутер
class AIRouter:
    def route(self, message, user, context, history, ...):
        # 500+ строк if/elif логики
        if crisis:
            return "claude"
        elif emotional:
            if user.tier == "premium":
                return "gpt-4"
        # ... еще 50 условий

# ✅ ПАТТЕРН: Стратегия + Цепочка ответственности
class RouterStrategy(ABC):
    @abstractmethod
    async def can_handle(self, context: RouterContext) -> bool:
        pass

    @abstractmethod
    async def select_model(self, context: RouterContext) -> str:
        pass

class CrisisRouter(RouterStrategy):
    async def can_handle(self, context):
        return context.is_crisis or context.depth_level == "SHADOW"

    async def select_model(self, context):
        return "claude-sonnet-3.5"

class EmotionalRouter(RouterStrategy):
    async def can_handle(self, context):
        return context.emotional_intensity > 0.7

    async def select_model(self, context):
        if context.user.tier == "premium":
            return "gpt-4"
        return "gpt-4o-mini"

# Композитный роутер
class AIRouterChain:
    def __init__(self):
        self.strategies = [
            CrisisRouter(),      # Приоритет 1
            EmotionalRouter(),   # Приоритет 2
            DefaultRouter()      # Fallback
        ]

    async def route(self, context: RouterContext) -> str:
        for strategy in self.strategies:
            if await strategy.can_handle(context):
                return await strategy.select_model(context)
```

### 2. Рефакторинг Промптов

```python
# ❌ АНТИПАТТЕРН: Промпты в коде
async def generate_response(user_message):
    prompt = f"""
    You are a psychological coach...
    {500 строк промпта}
    User said: {user_message}
    """

# ✅ ПАТТЕРН: Промпт-билдер + Шаблоны
class PromptTemplate:
    def __init__(self, template_path: str):
        self.template = load_template(template_path)
        self.sections = {}

    def add_section(self, name: str, content: str):
        self.sections[name] = content
        return self

    def build(self, **kwargs) -> str:
        return self.template.format(
            sections=self.sections,
            **kwargs
        )

class PsychologyPromptBuilder:
    def __init__(self):
        self.base = PromptTemplate("prompts/psychology_base.md")

    def for_crisis(self, context):
        return self.base\
            .add_section("safety", load("prompts/crisis_safety.md"))\
            .add_section("tone", "empathetic and supportive")\
            .build(context=context)

    def for_coaching(self, context):
        return self.base\
            .add_section("methods", load("prompts/coaching_methods.md"))\
            .add_section("tone", "professional and encouraging")\
            .build(context=context)
```

### 3. Рефакторинг AI Pipeline

```python
# ❌ АНТИПАТТЕРН: Процедурный pipeline
async def process_message(message):
    # 1000+ строк последовательной обработки
    embedding = create_embedding(message)
    similar = search_similar(embedding)
    context = build_context(similar)
    model = select_model(context)
    prompt = create_prompt(context)
    response = call_api(model, prompt)
    # ... еще 20 шагов

# ✅ ПАТТЕРН: Pipeline with Steps
class PipelineStep(ABC):
    @abstractmethod
    async def execute(self, data: PipelineData) -> PipelineData:
        pass

class EmbeddingStep(PipelineStep):
    async def execute(self, data):
        data.embedding = await self.embedder.create(data.message)
        return data

class SimilaritySearchStep(PipelineStep):
    async def execute(self, data):
        data.similar_states = await self.qdrant.search(
            embedding=data.embedding,
            limit=5
        )
        return data

class AIResponsePipeline:
    def __init__(self):
        self.steps = [
            EmbeddingStep(),
            SimilaritySearchStep(),
            ContextBuildingStep(),
            ModelSelectionStep(),
            PromptGenerationStep(),
            APICallStep(),
            ResponseValidationStep()
        ]

    async def process(self, message: str) -> str:
        data = PipelineData(message=message)

        for step in self.steps:
            try:
                data = await step.execute(data)
                logger.info(f"✅ {step.__class__.__name__} completed")
            except Exception as e:
                logger.error(f"❌ {step.__class__.__name__} failed: {e}")
                data = await self.handle_failure(step, data, e)

        return data.final_response
```

---

## 💬 СПЕЦИАЛЬНЫЕ ПРАВИЛА ДЛЯ TELEGRAM FSM

### 1. Рефакторинг Handlers

```python
# ❌ АНТИПАТТЕРН: Монолитный handler
@dp.message_handler(state="*")
async def mega_handler(message, state):
    # 500+ строк if/elif для разных состояний
    current_state = await state.get_state()
    if current_state == "onboarding":
        # 100 строк логики
    elif current_state == "chat":
        # 200 строк логики

# ✅ ПАТТЕРН: Отдельные handlers по состояниям
class OnboardingHandlers:
    @staticmethod
    async def handle_start(message: Message, state: FSMContext):
        # Максимум 50 строк
        await OnboardingService.start_session(message.from_user.id)
        await state.set_state(OnboardingStates.consent)
        await message.answer("Добро пожаловать!", reply_markup=consent_kb())

    @staticmethod
    async def handle_consent(callback: CallbackQuery, state: FSMContext):
        # Четкая единственная ответственность
        if callback.data == "agree":
            await state.set_state(OnboardingStates.questions)
            await OnboardingService.send_first_question(callback.from_user.id)

# Регистрация handlers группами
def register_onboarding_handlers(dp: Dispatcher):
    dp.register_message_handler(
        OnboardingHandlers.handle_start,
        commands=["start"],
        state="*"
    )
    dp.register_callback_query_handler(
        OnboardingHandlers.handle_consent,
        state=OnboardingStates.consent
    )
```

### 2. Рефакторинг FSM States

```python
# ❌ АНТИПАТТЕРН: Строковые состояния
await state.set_state("onboarding_question_1")
await state.set_state("onboarding_question_2")

# ✅ ПАТТЕРН: Типизированные состояния
class OnboardingStates(StatesGroup):
    consent = State()
    questions = State()
    analysis = State()
    complete = State()

class SessionStates(StatesGroup):
    idle = State()
    active_chat = State()
    awaiting_response = State()
    processing = State()

# Использование с метаданными
async def set_question_state(state: FSMContext, question_id: int):
    await state.set_state(OnboardingStates.questions)
    await state.update_data(
        current_question_id=question_id,
        started_at=datetime.now()
    )
```

### 3. Рефакторинг Redis Storage

```python
# ❌ АНТИПАТТЕРН: Прямая работа с Redis
async def save_user_data(user_id, data):
    redis_key = f"user:{user_id}:data"
    await redis.set(redis_key, json.dumps(data))

# ✅ ПАТТЕРН: Абстракция storage
class UserStateStorage:
    def __init__(self, redis_pool):
        self.redis = redis_pool
        self.prefix = "selfology:states"
        self.ttl = 86400  # 24 часа

    async def save_state(self, user_id: int, state: UserState):
        key = f"{self.prefix}:{user_id}"
        data = state.model_dump_json()  # Pydantic model
        await self.redis.setex(key, self.ttl, data)

    async def get_state(self, user_id: int) -> Optional[UserState]:
        key = f"{self.prefix}:{user_id}"
        data = await self.redis.get(key)
        if data:
            return UserState.model_validate_json(data)
        return None

    async def extend_ttl(self, user_id: int):
        key = f"{self.prefix}:{user_id}"
        await self.redis.expire(key, self.ttl)
```

---

## 🗄️ СПЕЦИАЛЬНЫЕ ПРАВИЛА ДЛЯ БАЗ ДАННЫХ

### 1. Рефакторинг SQLAlchemy Models

```python
# ❌ АНТИПАТТЕРН: God Model
class User(Base):
    __tablename__ = "users"
    # 50+ полей в одной таблице
    id = Column(Integer)
    telegram_id = Column(BigInteger)
    name = Column(String)
    # ... профиль
    big_five_o = Column(Float)
    big_five_c = Column(Float)
    # ... настройки
    notifications = Column(Boolean)
    language = Column(String)
    # ... статистика
    messages_count = Column(Integer)
    last_activity = Column(DateTime)

# ✅ ПАТТЕРН: Разделение по доменам
class User(Base):
    __tablename__ = "users"
    __table_args__ = {'schema': 'selfology'}

    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Отношения
    profile = relationship("UserProfile", back_populates="user", uselist=False)
    settings = relationship("UserSettings", back_populates="user", uselist=False)
    personality = relationship("UserPersonality", back_populates="user", uselist=False)

class UserProfile(Base):
    __tablename__ = "user_profiles"
    __table_args__ = {'schema': 'selfology'}

    user_id = Column(Integer, ForeignKey("selfology.users.id"))
    name = Column(String)
    age = Column(Integer)
    timezone = Column(String)

class UserPersonality(Base):
    __tablename__ = "user_personalities"
    __table_args__ = {'schema': 'selfology'}

    user_id = Column(Integer, ForeignKey("selfology.users.id"))
    big_five = Column(JSON)  # {"O": 0.7, "C": 0.8, ...}
    vector_693d = Column(ARRAY(Float))  # PostgreSQL array
```

### 2. Рефакторинг DAO Pattern

```python
# ❌ АНТИПАТТЕРН: Бизнес-логика в DAO
class UserDAO:
    async def create_user_and_send_welcome(self, telegram_id):
        # Смешивание слоев!
        user = User(telegram_id=telegram_id)
        session.add(user)
        await session.commit()

        # Бизнес-логика не должна быть здесь
        await telegram_bot.send_message(telegram_id, "Welcome!")
        await analytics.track("user_created", user.id)

# ✅ ПАТТЕРН: Чистый DAO + Service Layer
class UserRepository:
    """Только работа с БД"""
    async def create(self, telegram_id: int) -> User:
        async with self.session() as session:
            user = User(telegram_id=telegram_id)
            session.add(user)
            await session.commit()
            await session.refresh(user)
            return user

    async def find_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        async with self.session() as session:
            stmt = select(User).where(User.telegram_id == telegram_id)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

class UserService:
    """Бизнес-логика"""
    def __init__(self, repo: UserRepository, notifier: NotificationService):
        self.repo = repo
        self.notifier = notifier

    async def register_new_user(self, telegram_id: int) -> User:
        # Проверка существования
        existing = await self.repo.find_by_telegram_id(telegram_id)
        if existing:
            raise UserAlreadyExistsError()

        # Создание
        user = await self.repo.create(telegram_id)

        # Побочные эффекты через events
        await self.notifier.send_welcome(user)
        await EventBus.publish(UserCreatedEvent(user))

        return user
```

---

## 🔮 СПЕЦИАЛЬНЫЕ ПРАВИЛА ДЛЯ ВЕКТОРНЫХ БД

### 1. Рефакторинг Qdrant Operations

```python
# ❌ АНТИПАТТЕРН: Прямые вызовы Qdrant
async def save_embedding(user_id, text):
    embedding = openai.embeddings.create(input=text)
    qdrant_client.upsert(
        collection_name="embeddings",
        points=[{
            "id": str(uuid4()),
            "vector": embedding,
            "payload": {"user_id": user_id, "text": text}
        }]
    )

# ✅ ПАТТЕРН: Абстракция векторного хранилища
class VectorDocument:
    id: str
    vector: List[float]
    metadata: Dict[str, Any]

class VectorStore(ABC):
    @abstractmethod
    async def upsert(self, documents: List[VectorDocument]) -> None:
        pass

    @abstractmethod
    async def search(self, vector: List[float], limit: int) -> List[VectorDocument]:
        pass

class QdrantVectorStore(VectorStore):
    def __init__(self, client, collection: str):
        self.client = client
        self.collection = collection

    async def upsert(self, documents: List[VectorDocument]) -> None:
        points = [
            PointStruct(
                id=doc.id,
                vector=doc.vector,
                payload=doc.metadata
            )
            for doc in documents
        ]
        await self.client.upsert(
            collection_name=self.collection,
            points=points
        )

    async def search(self, vector: List[float], limit: int) -> List[VectorDocument]:
        results = await self.client.search(
            collection_name=self.collection,
            query_vector=vector,
            limit=limit
        )
        return [self._to_document(r) for r in results]

class PersonalityVectorService:
    def __init__(self, embedder: Embedder, store: VectorStore):
        self.embedder = embedder
        self.store = store

    async def save_user_state(self, user_id: int, text: str):
        # Создание embedding
        vector = await self.embedder.create_embedding(text)

        # Подготовка документа
        doc = VectorDocument(
            id=f"user:{user_id}:state:{uuid4()}",
            vector=vector,
            metadata={
                "user_id": user_id,
                "text": text,
                "timestamp": datetime.utcnow(),
                "type": "emotional_state"
            }
        )

        # Сохранение
        await self.store.upsert([doc])
```

---

## 🔄 ПРОЦЕСС РЕФАКТОРИНГА - ПОШАГОВЫЙ ПЛАН

### ФАЗА 1: Анализ и подготовка (2-3 часа)

```bash
# 1. Создать ветку рефакторинга
git checkout -b refactor/deep-restructuring

# 2. Проанализировать размеры файлов
find . -name "*.py" -exec wc -l {} \; | sort -rn | head -20

# 3. Найти дублирование кода
# Использовать инструменты: pylint --duplicate-code
# Или: radon cc -s -a selfology_bot/

# 4. Создать карту зависимостей
# pydeps selfology_bot --max-bacon 2 --pylib False

# 5. Backup критических файлов
cp -r selfology_bot/ selfology_bot_backup_$(date +%Y%m%d)/
```

### ФАЗА 2: Разбиение монолитов (4-6 часов)

```python
# Приоритет разбиения:
1. selfology_controller.py (если >300 строк)
2. bot/handlers/*.py (929 строк!)
3. services/chat_coach.py
4. ai/router.py
5. services/intelligent_questioning.py

# Для каждого файла:
1. Определить домены/ответственности
2. Создать новые модули
3. Переместить код
4. Обновить импорты
5. Запустить тесты
```

### ФАЗА 3: Архитектурные улучшения (6-8 часов)

```yaml
Порядок работы:
  1_Слой_Core:
    - Выделить чистые функции
    - Убрать все зависимости
    - Добавить type hints

  2_Слой_Infrastructure:
    - Абстрагировать внешние сервисы
    - Создать адаптеры для API
    - Внедрить dependency injection

  3_Слой_Domain:
    - Выделить бизнес-логику
    - Создать domain models
    - Определить domain events

  4_Слой_Application:
    - Создать use cases
    - Внедрить command/query separation
    - Добавить валидацию
```

### ФАЗА 4: Оптимизация специфичных компонентов (4-6 часов)

```python
# AI компоненты
- Разбить промпты на templates/
- Создать PromptBuilder
- Выделить стратегии роутинга

# Telegram FSM
- Разделить handlers по файлам
- Типизировать states
- Создать middleware для логирования

# База данных
- Разбить God Models
- Внедрить Repository pattern
- Добавить миграции для новой структуры

# Векторы
- Абстрагировать Qdrant
- Создать VectorStore interface
- Добавить кэширование embeddings
```

### ФАЗА 5: Тестирование и валидация (2-3 часа)

```bash
# 1. Запустить существующие тесты
pytest tests/ -v

# 2. Проверить покрытие
pytest --cov=selfology_bot tests/

# 3. Интеграционные тесты
python tests/test_phase2_3_integration.py

# 4. Smoke test бота
python simple_bot.py

# 5. Проверить метрики
python scripts/selfology_manager.py status
```

---

## 📊 МЕТРИКИ И ЧЕКЛИСТЫ

### Чеклист готовности к production

```yaml
Структура кода:
  ☐ Все файлы ≤ установленных лимитов
  ☐ Нет циклических импортов
  ☐ Clean Architecture соблюдена
  ☐ Нет God Objects/God Models

Асинхронность:
  ☐ Единообразные async/await паттерны
  ☐ Нет блокирующих операций в async
  ☐ Proper error handling в async
  ☐ Graceful shutdown реализован

AI компоненты:
  ☐ Промпты вынесены в templates
  ☐ Роутинг через стратегии
  ☐ Cost optimization ≥75%
  ☐ Fallback механизмы работают

База данных:
  ☐ Схема selfology используется
  ☐ Repository pattern внедрен
  ☐ Миграции актуальны
  ☐ Индексы оптимизированы

Производительность:
  ☐ Response time <500ms (instant feedback)
  ☐ Memory usage стабильно
  ☐ Redis cache работает
  ☐ Векторный поиск <20ms
```

### Метрики качества кода

```python
# Целевые показатели после рефакторинга
METRICS = {
    "max_file_lines": {
        "regular": 300,
        "ai_components": 600
    },
    "max_function_lines": {
        "regular": 50,
        "ai_prompts": 100
    },
    "max_class_methods": 10,
    "max_imports_per_file": 15,
    "code_duplication": "< 5%",
    "test_coverage": "> 80%",
    "cyclomatic_complexity": "< 10",
    "maintainability_index": "> 70"
}

# Команды для проверки
"""
# Сложность кода
radon cc selfology_bot/ -s -n C

# Maintainability Index
radon mi selfology_bot/ -s

# Дублирование
pylint selfology_bot/ --disable=all --enable=duplicate-code

# Покрытие тестами
pytest --cov=selfology_bot --cov-report=term-missing
"""
```

---

## ⚠️ КРИТИЧЕСКИЕ АНТИПАТТЕРНЫ ПРОЕКТА

### 1. НЕ разбивать Phase 2-3 компоненты

```python
# ⚠️ ВНИМАНИЕ: 6 компонентов Phase 2-3 взаимосвязаны!
# НЕ разбивать их произвольно

# Сохранить целостность:
coach/components/
├── enhanced_ai_router.py      # Связан с confidence_calculator
├── adaptive_communication.py  # Использует Big Five из vector_storytelling
├── deep_question_generator.py # Зависит от user personality
├── micro_interventions.py     # Работает с adaptive_communication
├── confidence_calculator.py   # Нужен всем компонентам
└── vector_storytelling.py     # База для остальных

# При рефакторинге Phase 2-3:
1. Рефакторить ВСЕ 6 компонентов вместе
2. Сохранить интерфейсы между ними
3. Не нарушать ChatCoachService orchestration
```

### 2. НЕ трогать критическую инфраструктуру

```yaml
НЕ ИЗМЕНЯТЬ без крайней необходимости:
  - Redis FSM Storage (DB=1) # Состояния пользователей!
  - Instance Lock механизм    # Защита от дублирования
  - selfology схема в PostgreSQL # Продакшн данные
  - Qdrant collections structure # Векторы пользователей

Если нужны изменения:
  1. Создать миграцию
  2. Протестировать на копии данных
  3. Иметь план отката
  4. Делать в maintenance window
```

### 3. НЕ упрощать AI роутинг

```python
# ❌ НЕ ДЕЛАТЬ: Упрощение ценой функциональности
def simple_router(message):
    return "gpt-4o-mini"  # Дешево но тупо

# ✅ СОХРАНИТЬ: Интеллектуальный роутинг
# Даже если код сложный - это core value!
# Crisis → Claude (дорого но критично)
# Emotional → GPT-4 (баланс)
# Simple → GPT-4o-mini (экономия)
```

---

## 🚀 БЫСТРЫЙ СТАРТ РЕФАКТОРИНГА

```bash
# Команда для Claude Code Web:

1. Начни с анализа:
   - Найди файлы >300 строк
   - Определи God Objects
   - Найди дублирование кода

2. Создай план разбиения для каждого большого файла

3. Выполни рефакторинг в порядке приоритета:
   - bot/handlers/ (критично!)
   - services/chat_coach.py
   - ai/router.py

4. После каждого изменения запускай:
   pytest tests/ --tb=short

5. В конце проверь метрики:
   radon cc selfology_bot/ -n C
```

---

## 📝 ФИНАЛЬНЫЕ ЗАМЕЧАНИЯ

1. **Рефакторинг - это марафон, не спринт**. Разбей на этапы.

2. **Тестируй после каждого значимого изменения**. Не накапливай изменения.

3. **Документируй изменения** в CHANGELOG.md

4. **Используй feature flags** для постепенного внедрения

5. **Мониторь метрики** до и после рефакторинга

6. **Помни про пользователей** - бот должен работать во время рефакторинга

---

**Автор**: Senior Refactoring Architect
**Версия**: 1.0.0
**Последнее обновление**: 2025-11-08

# При возникновении вопросов обращайся к основному CLAUDE.md