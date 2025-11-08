# TESTING STRATEGY - QUICK START

> Быстрый старт для тестирования Selfology microservices refactoring

---

## ЧТО СОЗДАНО

### 📚 Документация

1. **TESTING_STRATEGY.md** (основная стратегия)
   - Стратегия тестирования для всех 9 фаз
   - Event Bus, Onboarding, Analysis, Profile, Coach tests
   - Regression, Contract, Load, Chaos testing
   - Приоритизация по критичности (P0-P3)

2. **TESTING_CODE_EXAMPLES.md** (конкретные примеры)
   - 20+ полных примеров pytest кода
   - Unit, Integration, E2E, Contract tests
   - Event Bus, Onboarding, Analysis, Profile примеры
   - Load tests с Locust
   - Chaos tests для отказоустойчивости
   - Conftest и fixtures

3. **TESTING_IMPLEMENTATION_PLAN.md** (пошаговый план)
   - Детальный план на 9 недель
   - День за днём что писать
   - Сколько строк кода на каждую задачу
   - Команды для запуска
   - Критерии успеха

4. **scripts/validate_test_coverage.py** (автоматическая валидация)
   - Проверка coverage по компонентам
   - Валидация P0 тестов
   - Quality gates
   - Прогресс по фазам

---

## БЫСТРЫЙ СТАРТ

### Шаг 1: Установить зависимости

```bash
# Перейти в проект
cd /home/ksnk/n8n-enterprise/projects/selfology

# Активировать venv
source venv/bin/activate

# Установить testing зависимости
pip install pytest pytest-asyncio pytest-cov pytest-mock \
            factory-boy faker responses freezegun \
            pytest-benchmark locust
```

### Шаг 2: Создать структуру тестов

```bash
# Создать директории
mkdir -p tests/{event_bus,systems,e2e,load,chaos,production}/{unit,integration,contract}
mkdir -p tests/fixtures

# Скопировать примеры
# (из TESTING_CODE_EXAMPLES.md)
```

### Шаг 3: Настроить pytest

```bash
# Создать pytest.ini
cat > pytest.ini << 'EOF'
[pytest]
asyncio_mode = auto
testpaths = tests
python_files = test_*.py
addopts = --cov=. --cov-report=html --cov-report=term-missing --cov-fail-under=85
markers =
    unit: Unit tests
    integration: Integration tests
    e2e: End-to-end tests
    chaos: Chaos tests
EOF
```

### Шаг 4: Запустить валидацию

```bash
# Проверить текущий статус
./scripts/validate_test_coverage.py
```

---

## ФАЗЫ РЕФАКТОРИНГА

### Фаза 0: Event Bus (Неделя 1) - СЕЙЧАС

**Цель:** 95% coverage Event Bus

**Задачи:**
1. Event Publisher unit tests
2. Event Subscriber unit tests
3. Redis Streams integration tests
4. Contract tests для event schemas
5. Resilience tests (failover, retry)

**Файлы для создания:**
```
tests/event_bus/
├── unit/
│   ├── test_event_publisher.py       [250 строк]
│   ├── test_event_subscriber.py      [300 строк]
│   └── test_event_serialization.py   [200 строк]
├── integration/
│   ├── test_redis_streams.py         [400 строк]
│   └── test_consumer_groups.py       [250 строк]
├── contract/
│   └── test_event_schemas.py         [300 строк]
└── resilience/
    ├── test_redis_failover.py        [250 строк]
    └── test_message_retry.py         [200 строк]
```

**Команды:**
```bash
# Написать тесты (используя примеры из TESTING_CODE_EXAMPLES.md)

# Запустить
pytest tests/event_bus/ -v

# Проверить coverage
pytest tests/event_bus/ --cov=core.event_bus --cov-report=html

# Посмотреть отчет
open htmlcov/index.html
```

**Критерий успеха:**
- ✅ Все тесты зеленые
- ✅ Coverage >95%
- ✅ Integration tests с реальным Redis проходят
- ✅ Resilience tests подтверждают отказоустойчивость

---

### Фаза 1: Onboarding System (Неделя 2)

**Цель:** 85% coverage Onboarding

**Приоритетные тесты:**
1. QuestionRouter (Smart Mix алгоритм)
2. FatigueDetector
3. Event publication (QuestionAnsweredEvent, FatigueDetectedEvent)
4. E2E user journey

**Критичный тест:**
```python
def test_router_respects_energy_safety():
    """CRITICAL: Никогда HEAVY → HEAVY"""
    # Этот тест ОБЯЗАН проходить всегда
```

---

### Фаза 2: Analysis System (Неделя 3)

**Цель:** 90% coverage Analysis

**Приоритетные тесты:**
1. AnswerAnalyzer (instant <500ms, deep analysis)
2. TraitExtractor
3. Analysis Worker (event consumption, retry logic)
4. AI API contracts

**Performance benchmark:**
```python
def test_instant_analysis_is_fast():
    """Must be <500ms"""
    assert benchmark.stats.mean < 0.5
```

---

### Фаза 3-8: См. TESTING_IMPLEMENTATION_PLAN.md

---

## ПРИОРИТИЗАЦИЯ ТЕСТОВ

### P0 (КРИТИЧНЫЕ) - Блокируют работу

Эти тесты **ДОЛЖНЫ** проходить всегда:

1. ✅ Event Bus publish/subscribe работает
2. ✅ QuestionRouter не нарушает energy safety
3. ✅ Instant analysis <500ms
4. ✅ Profile updates не теряют данные
5. ✅ E2E user journey проходит

**Проверка:**
```bash
./scripts/validate_test_coverage.py
```

### P1 (ВАЖНЫЕ) - Блокируют релиз

1. FatigueDetector корректно работает
2. Coach персонализация использует профиль
3. Qdrant sync не теряет векторы
4. Regression tests - старый флоу работает
5. Load tests - система выдерживает нагрузку

### P2 (ЖЕЛАТЕЛЬНЫЕ)

1. Contract tests - API совместимость
2. Performance benchmarks - оптимизация
3. Chaos tests - resilience
4. Security tests - GDPR compliance

### P3 (Nice to have)

1. Visual regression - UI
2. Extended load tests - edge cases
3. Documentation tests - примеры в доках

---

## КОМАНДЫ

### Запуск тестов

```bash
# Все тесты
pytest

# Только unit (быстро)
pytest -m unit

# Integration (с Redis/DB)
pytest -m integration

# E2E (медленно)
pytest -m e2e --run-slow

# Chaos tests
pytest -m chaos --run-slow

# Конкретный файл
pytest tests/event_bus/unit/test_event_publisher.py -v

# Конкретный тест
pytest tests/event_bus/unit/test_event_publisher.py::TestEventPublisher::test_publish_simple_event -vv

# С coverage
pytest --cov=core --cov-report=html

# Параллельно (быстрее)
pytest -n 4

# Остановиться на первой ошибке
pytest -x

# Перезапустить только упавшие
pytest --lf
```

### Валидация и отчеты

```bash
# Полная валидация
./scripts/validate_test_coverage.py

# Coverage report
pytest --cov=. --cov-report=term-missing

# HTML coverage report
pytest --cov=. --cov-report=html
open htmlcov/index.html

# JSON для CI
pytest --cov=. --cov-report=json
```

### Load testing

```bash
# Запустить Locust
locust -f tests/load/locustfile.py --host=http://localhost:8000

# Headless (для CI)
locust -f tests/load/locustfile.py \
       --host=http://localhost:8000 \
       --users 100 \
       --spawn-rate 10 \
       --run-time 10m \
       --headless
```

### Benchmarks

```bash
# Performance benchmarks
pytest tests/load/test_performance_benchmarks.py --benchmark-only

# Compare benchmarks
pytest tests/load/test_performance_benchmarks.py --benchmark-compare
```

---

## МЕТРИКИ УСПЕХА

### Coverage Targets

| Компонент | Target | Current | Status |
|-----------|--------|---------|--------|
| Event Bus | 95% | 0% | ⏳ TODO |
| Onboarding | 85% | 20% | 🚧 In Progress |
| Analysis | 90% | 30% | 🚧 In Progress |
| Profile | 85% | 40% | 🚧 In Progress |
| Telegram | 80% | 50% | 🚧 In Progress |
| Coach | 90% | 25% | 🚧 In Progress |
| **Overall** | **>85%** | **~40%** | **⚠️ Gap: +45%** |

### Quality Gates

**Блокируют merge:**
- ❌ P0 tests failing
- ❌ Coverage drop >2%
- ❌ Performance regression >10%
- ❌ Lint errors

**Запустить проверку:**
```bash
./scripts/validate_test_coverage.py
```

---

## ПОМОЩЬ И ПОДДЕРЖКА

### Документы

1. **TESTING_STRATEGY.md** - полная стратегия тестирования
2. **TESTING_CODE_EXAMPLES.md** - 20+ примеров pytest кода
3. **TESTING_IMPLEMENTATION_PLAN.md** - пошаговый план на 9 недель
4. **TESTING_README.md** - этот файл (quick start)

### Структура документации

```
📚 Документация по тестированию
├── TESTING_STRATEGY.md          [Стратегия, типы тестов, приоритизация]
├── TESTING_CODE_EXAMPLES.md     [Конкретные примеры pytest кода]
├── TESTING_IMPLEMENTATION_PLAN.md [День-за-днём план имплементации]
└── TESTING_README.md            [Quick start guide]

🔧 Скрипты
├── scripts/validate_test_coverage.py  [Автоматическая валидация]

📊 Отчеты (генерируются)
├── htmlcov/                     [HTML coverage report]
├── coverage.json                [JSON coverage data]
└── pytest.log                   [Test execution log]
```

### Примеры из TESTING_CODE_EXAMPLES.md

**Event Bus Unit Test:**
```python
# tests/event_bus/unit/test_event_publisher.py
@pytest.mark.asyncio
async def test_publish_simple_event(event_bus):
    event = Event(event_type="test.event", payload={"message": "hello"})
    result = await event_bus.publish(event)
    assert result is True
```

**Contract Test:**
```python
# tests/event_bus/contract/test_event_schemas.py
def test_question_answered_event_schema():
    event = QuestionAnsweredEvent(
        user_id=123456,
        question_id="q_001",
        answer_text="My answer"
    )
    assert event.user_id == 123456
```

**E2E Test:**
```python
# tests/e2e/test_complete_user_journey.py
@pytest.mark.asyncio
async def test_full_onboarding_to_insight():
    """Complete flow: /start → questions → analysis → insight"""
    # User starts
    # Answers questions
    # Gets AI analysis
    # Profile updated
    # Coach generates insight
```

### Troubleshooting

**Tests не запускаются:**
```bash
# Проверить pytest установлен
pytest --version

# Установить зависимости
pip install -r requirements.txt
pip install pytest pytest-asyncio pytest-cov

# Проверить структуру
ls -la tests/
```

**Redis connection errors:**
```bash
# Проверить Redis запущен
docker ps | grep redis

# Запустить Redis
docker run -d -p 6379:6379 redis:7-alpine

# Проверить подключение
redis-cli ping
```

**Coverage низкий:**
```bash
# Посмотреть что не покрыто
pytest --cov=. --cov-report=term-missing

# HTML отчет для детального анализа
pytest --cov=. --cov-report=html
open htmlcov/index.html
```

---

## ROADMAP

### Сейчас (Неделя 1): Фаза 0 - Event Bus

1. ✅ Прочитать документацию
2. ⬜ Установить зависимости
3. ⬜ Создать структуру `/tests`
4. ⬜ Написать Event Bus tests (2650 строк)
5. ⬜ Достичь 95% coverage
6. ⬜ Запустить валидацию

### Дальше (Неделя 2): Фаза 1 - Onboarding

1. ⬜ QuestionRouter tests (400 строк)
2. ⬜ FatigueDetector tests (350 строк)
3. ⬜ Event publication tests (300 строк)
4. ⬜ E2E + Regression (400 строк)
5. ⬜ Достичь 85% coverage

### См. TESTING_IMPLEMENTATION_PLAN.md для полного roadmap

---

## CI/CD INTEGRATION

### GitHub Actions

```yaml
# .github/workflows/tests.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      redis:
        image: redis:7-alpine
      postgres:
        image: postgres:15

    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run tests
        run: pytest --cov=. --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

---

## КОНТАКТЫ

**Создано:** 2025-09-30
**Автор:** QA Team + AI Test Automation Expert
**Проект:** Selfology Microservices Refactoring

**Статус:** ✅ Ready to implement

**Первый шаг:** Фаза 0, День 1 - Event Bus Core Tests

**Команда для старта:**
```bash
./scripts/validate_test_coverage.py
```

---

## SUMMARY

✅ **Создана комплексная стратегия тестирования**
- 4 документа с полной стратегией, примерами, планом
- 20+ готовых примеров pytest кода
- Пошаговый план на 9 недель
- Автоматическая валидация

✅ **Приоритизация по критичности**
- P0: Event Bus, Energy Safety, Performance
- P1: FatigueDetector, Coach, Regression
- P2-P3: Optimization, Nice-to-have

✅ **Конкретные метрики успеха**
- Event Bus: 95% coverage
- Analysis: 90% coverage
- Overall: >85% coverage
- Load: 100 users, 1000 req/min

✅ **Готово к имплементации**
- Начать с Event Bus (Фаза 0)
- 2650 строк тестов за неделю
- Четкие критерии успеха
- Автоматическая валидация

**Вперед к 85% coverage! 🚀**
