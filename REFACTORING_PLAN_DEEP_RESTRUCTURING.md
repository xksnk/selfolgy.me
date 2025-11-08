# 🔧 Детальный План Глубокого Рефакторинга Selfology

**Дата создания**: 2025-11-08
**Ветка**: `claude/refactor-selfology-deep-restructuring-011CUuxS2PMJbZ38MdHBMUUR`
**Тип**: DEEP REFACTORING - Реструктуризация + разбиение монолитов

---

## 📊 ТЕКУЩЕЕ СОСТОЯНИЕ - КРИТИЧЕСКИЕ ПРОБЛЕМЫ

### 🔴 God Objects обнаружены:

| Файл | Строки | Методы | Проблема | Приоритет |
|------|--------|--------|----------|-----------|
| `selfology_controller.py` | 1572 | ~40 | Все handlers в одном классе | 🔥 P0 |
| `services/onboarding/orchestrator.py` | 1375 | ~25 | Монолитный оркестратор | 🔥 P0 |
| `database/onboarding_dao.py` | 1116 | 30+ | Смешивание 6 ответственностей | 🔥 P0 |
| `analysis/embedding_creator.py` | 1122 | ~19 | API + Storage + Strategy в одном | ⚠️ P1 |
| `analysis/answer_analyzer.py` | 939 | ~15 | Монолитный анализатор | ⚠️ P1 |
| `services/chat_coach.py` | 1296 | ~20 | Все Phase 2-3 в одном файле | ⚠️ P2 |

### ❌ Нарушения архитектурных правил:

```yaml
Превышение лимитов:
  - selfology_controller.py: 1572 строки (лимит 600 для AI)
  - orchestrator.py: 1375 строк (лимит 600 для AI)
  - onboarding_dao.py: 1116 строк (лимит 300)
  - embedding_creator.py: 1122 строки (лимит 300)
  - answer_analyzer.py: 939 строк (лимит 300)

Нарушение SRP (Single Responsibility):
  - OnboardingDAO: 6 разных доменов в одном классе
  - SelfologyController: handlers + lifecycle + helpers
  - EmbeddingCreator: API client + Vector DB + Updates

Циклические зависимости:
  - Возможны между services и database layers
```

---

## 🎯 СТРАТЕГИЯ РЕФАКТОРИНГА

### Фаза 1: Подготовка и анализ (СЕЙЧАС)
- ✅ Анализ размеров файлов
- ✅ Выявление God Objects
- ✅ Создание детального плана
- ⬜ Backup критических данных
- ⬜ Создание smoke tests

### Фаза 2: Разбиение Controller (P0 - КРИТИЧНО)
- ⬜ Извлечь handlers группами по доменам
- ⬜ Создать Handler Modules
- ⬜ Вынести lifecycle методы
- ⬜ Создать MessageManager
- ⬜ Упростить Controller до координатора

### Фаза 3: Разбиение Orchestrator (P0)
- ⬜ Отделить SessionManager
- ⬜ Вынести QuestionRouter integration
- ⬜ Создать AnalysisCoordinator
- ⬜ Изолировать BackgroundTaskRegistry

### Фаза 4: Разбиение DAO (P0)
- ⬜ SessionRepository
- ⬜ AnswerRepository
- ⬜ QuestionMetadataRepository
- ⬜ AnalysisRepository
- ⬜ ContextStoryRepository
- ⬜ VectorizationRepository

### Фаза 5: Разбиение Analysis (P1)
- ⬜ OpenAIEmbeddingClient
- ⬜ QdrantVectorStore
- ⬜ VectorUpdateStrategy
- ⬜ BreakthroughDetector

### Фаза 6: Оптимизация Chat Coach (P2)
- ⬜ Проверка интеграции 6 компонентов
- ⬜ Оптимизация без нарушения работы

### Фаза 7: Тестирование и валидация
- ⬜ Unit tests для каждого компонента
- ⬜ Integration tests
- ⬜ Smoke test с реальным ботом
- ⬜ Performance benchmarks

---

## 📐 ДЕТАЛЬНЫЕ ПЛАНЫ РАЗБИЕНИЯ

## 1. selfology_controller.py → Модульная структура

### Целевая архитектура:

```
telegram_interface/
├── controller.py                    # ≤150 строк - только координация
├── lifecycle/
│   ├── __init__.py
│   ├── bot_lifecycle.py            # start_polling, stop, signal handlers
│   ├── instance_lock.py            # Redis instance locking
│   └── health_check.py             # Health monitoring
├── handlers/
│   ├── __init__.py                 # Регистрация всех handlers
│   ├── command_handlers.py         # /start, /help, /profile
│   ├── onboarding_handlers.py      # Onboarding workflow
│   ├── chat_handlers.py            # AI Chat handlers
│   ├── admin_handlers.py           # Debug commands
│   └── callback_handlers.py        # Все callback handlers
├── middleware/
│   ├── __init__.py
│   ├── state_logger.py             # FSM state logging
│   └── error_handler.py            # Error handling middleware
└── utilities/
    ├── __init__.py
    ├── message_splitter.py         # _send_long_message
    └── menu_builder.py             # _show_main_menu helpers
```

### План разбиения (40 методов → 8 файлов):

```python
# controller.py (≤150 строк)
class SelfologyController:
    def __init__(self):
        """Только инициализация и композиция"""
        self.bot = Bot(token=BOT_TOKEN)
        self.dp = Dispatcher(...)
        self.lifecycle = BotLifecycle(self.bot, self.dp)
        self.handler_registry = HandlerRegistry(self.dp)

    async def start(self):
        """Единая точка входа"""
        await self.lifecycle.start_polling()

# lifecycle/bot_lifecycle.py (≤150 строк)
class BotLifecycle:
    async def start_polling(self):
        """Start bot with instance lock"""

    async def stop(self):
        """Graceful shutdown"""

    async def _setup_signal_handlers(self):
        """SIGINT/SIGTERM handlers"""

# lifecycle/instance_lock.py (≤100 строк)
class BotInstanceLock:
    async def acquire(self) -> bool:
        """Redis-based instance locking"""

    async def refresh(self):
        """Keep lock alive"""

    async def release(self):
        """Release lock on shutdown"""

# handlers/command_handlers.py (≤200 строк)
class CommandHandlers:
    @staticmethod
    async def cmd_start(message, state):
        """Handle /start"""

    @staticmethod
    async def cmd_help(message):
        """Handle /help"""

    @staticmethod
    async def cmd_profile(message):
        """Handle /profile"""

# handlers/onboarding_handlers.py (≤250 строк)
class OnboardingHandlers:
    @staticmethod
    async def cmd_onboarding(message, state):
        """Start onboarding"""

    @staticmethod
    async def handle_onboarding_answer(message, state):
        """Process user answer"""

    @staticmethod
    async def callback_skip_question(callback, state):
        """Skip question"""

# handlers/chat_handlers.py (≤150 строк)
class ChatHandlers:
    @staticmethod
    async def cmd_chat(message, state):
        """Start chat session"""

    @staticmethod
    async def handle_chat_message(message, state):
        """Process chat message"""

# handlers/admin_handlers.py (≤150 строк)
class AdminHandlers:
    @staticmethod
    async def cmd_debug_on(message):
        """Enable debug mode"""

    @staticmethod
    async def cmd_reload_templates(message):
        """Reload message templates"""

# handlers/__init__.py (≤100 строк)
def register_all_handlers(dp: Dispatcher):
    """Централизованная регистрация"""
    register_command_handlers(dp)
    register_onboarding_handlers(dp)
    register_chat_handlers(dp)
    register_admin_handlers(dp)
    register_callback_handlers(dp)
```

### Метрики после рефакторинга:

```yaml
До:
  - selfology_controller.py: 1572 строки, 40 методов

После:
  - controller.py: ~150 строк
  - bot_lifecycle.py: ~150 строк
  - instance_lock.py: ~100 строк
  - command_handlers.py: ~200 строк
  - onboarding_handlers.py: ~250 строк
  - chat_handlers.py: ~150 строк
  - admin_handlers.py: ~150 строк
  - callback_handlers.py: ~200 строк
  - middleware/state_logger.py: ~80 строк
  - utilities/message_splitter.py: ~60 строк
  - utilities/menu_builder.py: ~80 строк

  ИТОГО: ~1570 строк в 11 файлах
  МАКС ФАЙЛ: 250 строк ✅
```

---

## 2. onboarding_dao.py → Repository Pattern

### Целевая архитектура:

```
database/onboarding/
├── __init__.py
├── session_repository.py           # Сессии онбординга
├── answer_repository.py            # Ответы пользователей
├── question_metadata_repository.py # Флаги, одобрение вопросов
├── analysis_repository.py          # Результаты анализа
├── context_story_repository.py     # Context stories
└── vectorization_repository.py     # Статусы векторизации
```

### План разбиения (30 методов → 6 репозиториев):

```python
# session_repository.py (≤200 строк)
class OnboardingSessionRepository:
    async def get_active_session(self, user_id: int)
    async def get_session_by_id(self, session_id: int)
    async def start_session(self, user_id: int) -> int
    async def complete_session(self, session_id: int)
    async def increment_questions_asked(self, session_id: int)
    async def update_current_question(self, session_id: int, question_json_id: str)

# answer_repository.py (≤150 строк)
class UserAnswerRepository:
    async def save_user_answer(self, session_id: int, question_json_id: str, answer: str) -> int
    async def get_session_answers(self, session_id: int) -> List[Dict]
    async def get_user_total_answers(self, user_id: int) -> int
    async def get_user_answered_questions(self, user_id: int) -> List[str]

# question_metadata_repository.py (≤150 строк)
class QuestionMetadataRepository:
    async def auto_approve_question(self, json_id: str, ...)
    async def flag_question_for_admin(self, json_id: str, ...)
    async def get_unflagged_questions(self, domain: str = None) -> List[str]
    async def get_flagged_question_ids(self) -> set
    async def flag_question(self, question_id: str, ...) -> bool
    async def unflag_question(self, question_id: str) -> bool

# analysis_repository.py (≤200 строк)
class AnalysisRepository:
    async def save_analysis_result(self, ...)
    async def get_session_analysis_insights(self, session_id: int) -> List[Dict]
    async def save_context_story_analysis(self, ...)

# context_story_repository.py (≤150 строк)
class ContextStoryRepository:
    async def save_context_story(self, ...)
    async def get_user_context_stories(self, ...)
    async def search_context_stories(self, ...)
    async def deactivate_context_story(self, story_id: int)
    async def get_session_context_story(self, session_id: int)

# vectorization_repository.py (≤150 строк)
class VectorizationRepository:
    async def update_vectorization_status(self, ...)
    async def update_dp_update_status(self, ...)
    async def mark_background_task_completed(self, ...)
    async def increment_retry_count(self, ...)
```

### Координация через Facade:

```python
# database/onboarding/__init__.py
class OnboardingDataAccess:
    """Facade для координации репозиториев"""

    def __init__(self, db_service: DatabaseService):
        self.sessions = OnboardingSessionRepository(db_service)
        self.answers = UserAnswerRepository(db_service)
        self.questions = QuestionMetadataRepository(db_service)
        self.analysis = AnalysisRepository(db_service)
        self.stories = ContextStoryRepository(db_service)
        self.vectorization = VectorizationRepository(db_service)
```

---

## 3. orchestrator.py → Координатор + Сервисы

### Целевая архитектура:

```
services/onboarding/
├── orchestrator.py                 # ≤300 строк - только координация
├── session_manager.py              # Управление сессиями
├── question_router.py              # (уже существует)
├── fatigue_detector.py             # (уже существует)
├── session_reporter.py             # (уже существует)
├── analysis_coordinator.py         # Координация анализа
└── background_task_registry.py     # Управление background tasks
```

### План разбиения:

```python
# orchestrator.py (≤300 строк)
class OnboardingOrchestrator:
    """Координатор верхнего уровня"""

    def __init__(self):
        self.question_router = QuestionRouter(...)
        self.session_manager = SessionManager(...)
        self.analysis_coordinator = AnalysisCoordinator(...)
        self.fatigue_detector = FatigueDetector()
        self.task_registry = BackgroundTaskRegistry()

    async def start_session(self, user_id: int):
        """Начать онбординг"""

    async def process_answer(self, user_id: int, answer: str):
        """Обработать ответ"""

    async def get_next_question(self, user_id: int):
        """Получить следующий вопрос"""

# session_manager.py (≤200 строк)
class SessionManager:
    """Управление состоянием сессий"""

    async def create_session(self, user_id: int)
    async def get_session(self, user_id: int)
    async def update_session(self, session_id: int, data: dict)
    async def complete_session(self, session_id: int)

# analysis_coordinator.py (≤250 строк)
class AnalysisCoordinator:
    """Координирует анализ ответов"""

    def __init__(self):
        self.answer_analyzer = AnswerAnalyzer()
        self.embedding_creator = EmbeddingCreator()
        self.personality_extractor = PersonalityExtractor()

    async def analyze_answer(self, answer_id: int):
        """Запустить полный цикл анализа"""

# background_task_registry.py (≤150 строк)
class BackgroundTaskRegistry:
    """Отслеживание background tasks"""

    def register(self, task: asyncio.Task):
        """Зарегистрировать task"""

    async def wait_all(self):
        """Дождаться всех tasks"""

    async def cancel_all(self):
        """Отменить все tasks"""
```

---

## 4. embedding_creator.py → Разделение concerns

### Целевая архитектура:

```
analysis/embedding/
├── __init__.py
├── embedding_client.py             # OpenAI API client
├── vector_store.py                 # Qdrant operations
├── update_strategy.py              # Стратегии обновления
├── breakthrough_detector.py        # Определение breakthrough moments
└── embedding_service.py            # Координация
```

### План разбиения:

```python
# embedding_client.py (≤200 строк)
class OpenAIEmbeddingClient:
    """Работа с OpenAI Embeddings API"""

    async def create_embedding(self, text: str, dimensions: int) -> List[float]
    async def _call_with_retry(self, ...)
    async def _call_api(self, ...)

# vector_store.py (≤250 строк)
class QdrantVectorStore:
    """Операции с Qdrant"""

    async def setup_collections(self) -> bool
    async def store_vector(self, collection: str, ...)
    async def search_similar(self, vector: List[float], ...)
    async def get_collections_status(self) -> Dict

# update_strategy.py (≤200 строк)
class VectorUpdateStrategy:
    """Стратегии обновления векторов"""

    async def apply_update(self, strategy: str, ...)
    async def _incremental_update(self, ...)
    async def _full_replacement(self, ...)

# breakthrough_detector.py (≤150 строк)
class BreakthroughDetector:
    """Определение breakthrough moments"""

    async def detect_breakthrough(self, old_vector, new_vector) -> bool
    async def save_breakthrough_moment(self, ...)

# embedding_service.py (≤250 строк)
class EmbeddingService:
    """Координация всех операций"""

    def __init__(self):
        self.client = OpenAIEmbeddingClient()
        self.store = QdrantVectorStore()
        self.strategy = VectorUpdateStrategy()
        self.breakthrough = BreakthroughDetector()

    async def create_personality_vector(self, ...):
        """Полный цикл создания вектора"""
```

---

## 5. answer_analyzer.py → Разделение AI и Data

### Целевая архитектура:

```
analysis/answer/
├── __init__.py
├── ai_analyzer.py                  # AI анализ через OpenAI/Claude
├── personality_extractor.py        # Извлечение personality traits
├── insight_generator.py            # Генерация insights
└── analysis_service.py             # Координация
```

---

## 🚀 ПОРЯДОК ВЫПОЛНЕНИЯ (Step-by-Step)

### SPRINT 1: Controller Refactoring (P0) - 4-6 часов

1. **Создать новую структуру папок**
   ```bash
   mkdir -p telegram_interface/{lifecycle,handlers,middleware,utilities}
   ```

2. **Извлечь lifecycle методы**
   - Создать `lifecycle/bot_lifecycle.py`
   - Переместить `start_polling()`, `stop()`, `_setup_signal_handlers()`
   - Создать `lifecycle/instance_lock.py`
   - Переместить instance lock методы

3. **Извлечь handlers группами**
   - Создать `handlers/command_handlers.py`
   - Создать `handlers/onboarding_handlers.py`
   - Создать `handlers/chat_handlers.py`
   - Создать `handlers/admin_handlers.py`
   - Создать `handlers/callback_handlers.py`

4. **Извлечь utilities**
   - Создать `utilities/message_splitter.py` (_send_long_message)
   - Создать `utilities/menu_builder.py` (_show_main_menu)

5. **Создать упрощенный Controller**
   - Композиция всех компонентов
   - Регистрация handlers
   - Единая точка входа

6. **Обновить импорты везде**

7. **Запустить тесты**

### SPRINT 2: DAO Refactoring (P0) - 4-6 часов

1. **Создать структуру репозиториев**
   ```bash
   mkdir -p selfology_bot/database/onboarding
   ```

2. **Создать репозитории по доменам**
   - session_repository.py
   - answer_repository.py
   - question_metadata_repository.py
   - analysis_repository.py
   - context_story_repository.py
   - vectorization_repository.py

3. **Создать Facade**
   - OnboardingDataAccess в `__init__.py`

4. **Обновить все использования OnboardingDAO**

5. **Запустить тесты**

### SPRINT 3: Orchestrator Refactoring (P0) - 3-4 часа

1. **Создать новые сервисы**
   - session_manager.py
   - analysis_coordinator.py
   - background_task_registry.py

2. **Упростить orchestrator.py**
   - Делегировать логику в сервисы
   - Оставить только координацию

3. **Обновить импорты**

4. **Запустить тесты**

### SPRINT 4: Analysis Refactoring (P1) - 3-4 часа

1. **Разбить embedding_creator.py**
   - embedding_client.py
   - vector_store.py
   - update_strategy.py
   - breakthrough_detector.py
   - embedding_service.py (facade)

2. **Разбить answer_analyzer.py**
   - ai_analyzer.py
   - personality_extractor.py
   - insight_generator.py
   - analysis_service.py

3. **Обновить импорты**

4. **Запустить тесты**

### SPRINT 5: Integration Testing - 2-3 часа

1. **Unit tests для каждого компонента**

2. **Integration tests**

3. **Smoke test с реальным ботом**
   ```bash
   ./run-local.sh
   # Тестировать /start, /onboarding, /chat
   ```

4. **Performance benchmarks**

5. **Проверка метрик**

---

## ✅ КРИТЕРИИ УСПЕХА

### Метрики кода:

```yaml
Размеры файлов:
  - Все обычные файлы: ≤300 строк ✅
  - AI компоненты: ≤600 строк ✅
  - Максимум методов в классе: ≤10 ✅

Архитектура:
  - Нет God Objects ✅
  - Нет циклических зависимостей ✅
  - Single Responsibility соблюдено ✅
  - Repository pattern для DAO ✅

Производительность:
  - Response time стабилен ✅
  - Memory usage не вырос ✅
  - Все тесты проходят ✅
```

### Функциональность:

```yaml
Работоспособность:
  - /start работает ✅
  - /onboarding работает ✅
  - /chat работает ✅
  - Redis FSM сохраняется ✅
  - Instance lock работает ✅
  - Graceful shutdown работает ✅

Phase 2-3:
  - Все 6 компонентов работают ✅
  - AI роутинг работает ✅
  - Cost optimization сохранен ✅
```

---

## 🔒 БЕЗОПАСНОСТЬ И ОТКАТ

### Backup перед началом:

```bash
# Создать backup ветку
git checkout -b backup/before-deep-refactoring-$(date +%Y%m%d)
git push -u origin backup/before-deep-refactoring-$(date +%Y%m%d)

# Вернуться к рабочей ветке
git checkout claude/refactor-selfology-deep-restructuring-011CUuxS2PMJbZ38MdHBMUUR
```

### План отката:

```bash
# Если что-то пошло не так:
git reset --hard backup/before-deep-refactoring-20251108
git push --force-with-lease

# Восстановить бота
./run-local.sh
```

---

## 📋 ЧЕКЛИСТ ДЛЯ КАЖДОГО СПРИНТА

```yaml
Перед началом:
  ☐ Backup текущего состояния
  ☐ Создать feature ветку (если нужно)
  ☐ Smoke test - бот работает

Во время работы:
  ☐ Следовать правилам из REFACTORING_RULES_SELFOLOGY.md
  ☐ Соблюдать лимиты размеров файлов
  ☐ Коммитить после каждого логического шага
  ☐ Писать описательные commit messages

После завершения:
  ☐ Все импорты обновлены
  ☐ Все тесты проходят
  ☐ Smoke test - бот работает
  ☐ Метрики кода в норме
  ☐ Код review (если возможно)
  ☐ Commit и push
```

---

## 🎯 СЛЕДУЮЩИЙ ШАГ

**НАЧАТЬ SPRINT 1: Controller Refactoring**

1. Создать backup ветку
2. Создать структуру telegram_interface/
3. Извлечь lifecycle методы
4. Извлечь handlers
5. Создать упрощенный controller
6. Тестировать

**ВРЕМЯ**: 4-6 часов
**ПРИОРИТЕТ**: P0 - КРИТИЧНО
**РИСК**: Средний (много импортов нужно обновить)

---

**Автор**: Claude Code AI
**Дата**: 2025-11-08
**Версия**: 1.0.0
