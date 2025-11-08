# ПЛАН ИМПЛЕМЕНТАЦИИ ТЕСТОВ SELFOLOGY
## От текущих 40% до целевых 85% покрытия

> Конкретный пошаговый план имплементации тестов для каждой из 9 фаз рефакторинга

---

## ТЕКУЩИЙ СТАТУС

### Существующие тесты
```
selfology_bot/soul_architect/tests/
├── test_models.py       - Soul Architect models (ЕСТЬ)
├── test_scorer.py       - Scoring logic (ЕСТЬ)
└── __init__.py

test_refactored_system.py - Partial integration test (ЕСТЬ)
```

**Текущее покрытие:** ~40%

**Цель:** >85%

**Gap:** 45% - нужно добавить ~6000 строк тестов

---

## ПРИОРИТИЗАЦИЯ: ЧТО ПИСАТЬ ПЕРВЫМ

### P0: КРИТИЧНО - Блокирует дальнейшую работу

1. **Event Bus Tests** (Фаза 0)
   - Без этого вся event-driven архитектура не заработает
   - Время: 2-3 дня
   - Строк кода: ~800

2. **Database Migration Tests**
   - Убедиться, что миграции не ломают данные
   - Время: 1 день
   - Строк кода: ~200

3. **Basic E2E Smoke Test**
   - Простейший флоу работает
   - Время: 0.5 дня
   - Строк кода: ~150

### P1: ВАЖНО - Нужно для каждой фазы

4. **System Integration Tests**
   - По мере выделения каждой системы
   - Время: 1 день на систему
   - Строк кода: ~400 на систему

5. **Contract Tests**
   - Гарантия совместимости событий
   - Время: 2 дня
   - Строк кода: ~600

### P2: ЖЕЛАТЕЛЬНО - Качество и надежность

6. **Load Tests**
   - Проверка производительности
   - Время: 2 дня
   - Строк кода: ~300

7. **Chaos Tests**
   - Отказоустойчивость
   - Время: 2 дня
   - Строк кода: ~400

---

## ФАЗА 0: EVENT BUS (НЕДЕЛЯ 1)

### Цель: 95% покрытие Event Bus

#### День 1: Setup + Core Event Bus Tests

**Задачи:**
1. Создать структуру `/tests`
2. Настроить `pytest.ini`
3. Написать `conftest.py`
4. Unit tests для Event Publisher

**Файлы:**
```
tests/
├── conftest.py                                    [200 строк]
├── pytest.ini                                     [50 строк]
├── fixtures/
│   └── factories.py                              [300 строк]
└── event_bus/
    └── unit/
        └── test_event_publisher.py               [250 строк]
```

**Команды:**
```bash
# Создать структуру
mkdir -p tests/event_bus/{unit,integration,contract,resilience}
mkdir -p tests/fixtures

# Установить зависимости
pip install pytest pytest-asyncio pytest-cov pytest-mock factory-boy faker

# Создать pytest.ini
cat > pytest.ini << 'EOF'
[pytest]
asyncio_mode = auto
testpaths = tests
python_files = test_*.py
addopts = --cov=core --cov-report=html --cov-report=term-missing
EOF

# Запустить
pytest tests/event_bus/unit/ -v
```

**Критерий успеха:**
- Все тесты зеленые
- Coverage Event Publisher >90%

---

#### День 2: Event Subscriber + Redis Integration

**Задачи:**
1. Unit tests для Event Subscriber
2. Integration tests с реальным Redis
3. Consumer groups

**Файлы:**
```
tests/event_bus/
├── unit/
│   └── test_event_subscriber.py                  [300 строк]
└── integration/
    └── test_redis_streams.py                     [400 строк]
```

**Команды:**
```bash
# Убедиться, что Redis запущен
docker ps | grep redis

# Запустить integration тесты
pytest tests/event_bus/integration/ -v -m integration

# Проверить coverage
pytest tests/event_bus/ --cov=core.event_bus --cov-report=html
```

**Критерий успеха:**
- Integration tests проходят с реальным Redis
- Нет race conditions
- Coverage Event Subscriber >90%

---

#### День 3: Event Schemas + Contract Tests

**Задачи:**
1. Contract tests для всех event schemas
2. Backward compatibility тесты
3. Schema validation

**Файлы:**
```
tests/event_bus/contract/
├── test_event_schemas.py                         [300 строк]
└── test_backward_compatibility.py                [200 строк]

contracts/
└── schemas/
    ├── question_answered_v1.yaml
    ├── analysis_completed_v1.yaml
    └── profile_updated_v1.yaml
```

**Команды:**
```bash
# Запустить contract tests
pytest tests/event_bus/contract/ -v

# Проверить все schemas валидны
python scripts/validate_event_schemas.py
```

**Критерий успеха:**
- Все события сериализуются/десериализуются
- Backward compatibility подтверждена

---

#### День 4: Resilience Tests

**Задачи:**
1. Redis failover тесты
2. Network issues simulation
3. Message retry logic

**Файлы:**
```
tests/event_bus/resilience/
├── test_redis_failover.py                        [250 строк]
├── test_network_issues.py                        [200 строк]
└── test_message_retry.py                         [200 строк]
```

**Команды:**
```bash
# Запустить resilience tests
pytest tests/event_bus/resilience/ -v --run-slow

# Симулировать network issues (с toxiproxy)
docker run -d --name toxiproxy -p 8474:8474 -p 6380:6380 shopify/toxiproxy
pytest tests/event_bus/resilience/test_network_issues.py
```

**Критерий успеха:**
- Система переживает Redis restart
- Messages не теряются
- Retry logic работает

---

### Итоги Фазы 0

**Написано тестов:** ~2650 строк
**Coverage Event Bus:** >95%
**Время:** 4 дня
**Статус:** ✅ Event Bus готов для production

---

## ФАЗА 1: ONBOARDING SYSTEM (НЕДЕЛЯ 2)

### Цель: 85% покрытие Onboarding

#### День 1: QuestionRouter Tests

**Задачи:**
1. Unit tests для Smart Mix алгоритма
2. Все 4 стратегии (ENTRY, EXPLORATION, DEEPENING, BALANCING)
3. Energy safety rules

**Файлы:**
```
tests/systems/onboarding/unit/
└── test_question_router.py                       [400 строк]
```

**Критичные тесты:**
```python
def test_entry_strategy_selects_surface_questions()
def test_exploration_strategy_broadens_domains()
def test_deepening_strategy_increases_depth()
def test_balancing_strategy_avoids_heavy_after_heavy()
def test_router_respects_energy_safety()  # CRITICAL!
```

**Команды:**
```bash
pytest tests/systems/onboarding/unit/test_question_router.py -v
pytest tests/systems/onboarding/unit/test_question_router.py::TestQuestionRouter::test_router_respects_energy_safety -vv
```

**Критерий успеха:**
- Никогда HEAVY → HEAVY
- Smart Mix работает корректно
- Coverage QuestionRouter >90%

---

#### День 2: FatigueDetector Tests

**Задачи:**
1. Fatigue calculation logic
2. Различные индикаторы усталости
3. Care messages

**Файлы:**
```
tests/systems/onboarding/unit/
└── test_fatigue_detector.py                      [350 строк]
```

**Критичные тесты:**
```python
def test_no_fatigue_at_start()
def test_fatigue_from_long_session()
def test_fatigue_from_slowing_responses()
def test_fatigue_from_decreasing_quality()
def test_suggested_pause_duration()
```

**Команды:**
```bash
pytest tests/systems/onboarding/unit/test_fatigue_detector.py -v
```

**Критерий успеха:**
- Fatigue detection работает
- Паузы предлагаются вовремя
- Coverage FatigueDetector >85%

---

#### День 3: Event Publication Tests

**Задачи:**
1. Integration tests публикации событий
2. QuestionAnsweredEvent
3. FatigueDetectedEvent

**Файлы:**
```
tests/systems/onboarding/integration/
└── test_onboarding_events.py                     [300 строк]
```

**Команды:**
```bash
pytest tests/systems/onboarding/integration/ -v -m integration
```

**Критерий успеха:**
- События публикуются при каждом ответе
- Payload корректный
- Integration с Event Bus работает

---

#### День 4: E2E Onboarding Flow

**Задачи:**
1. E2E тест полного онбординга
2. User journey от /start до 10 вопросов
3. Regression тест старого флоу

**Файлы:**
```
tests/systems/onboarding/e2e/
└── test_onboarding_flow.py                       [250 строк]

tests/regression/
└── test_existing_onboarding.py                   [150 строк]
```

**Команды:**
```bash
pytest tests/systems/onboarding/e2e/ -v --run-slow
pytest tests/regression/test_existing_onboarding.py -v
```

**Критерий успеха:**
- E2E тест проходит
- Старый /start флоу работает
- Нет regression

---

### Итоги Фазы 1

**Написано тестов:** ~1450 строк
**Coverage Onboarding:** >85%
**Время:** 4 дня
**Статус:** ✅ Onboarding System готов

---

## ФАЗА 2: ANALYSIS SYSTEM (НЕДЕЛЯ 3)

### Цель: 90% покрытие Analysis (критично для AI)

#### День 1-2: AnswerAnalyzer Tests

**Задачи:**
1. Instant analysis (<500ms)
2. Deep analysis
3. Trait extraction

**Файлы:**
```
tests/systems/analysis/unit/
├── test_answer_analyzer.py                       [450 строк]
└── test_trait_extractor.py                       [300 строк]
```

**Критичные тесты:**
```python
def test_instant_analysis_is_fast()              # <500ms!
def test_deep_analysis_extracts_detailed_traits()
def test_trait_extraction_for_big_five()
def test_analyzer_handles_short_answers()
def test_analyzer_detects_emotional_content()
```

**Команды:**
```bash
pytest tests/systems/analysis/unit/ -v
pytest tests/systems/analysis/unit/test_answer_analyzer.py::TestAnswerAnalyzer::test_instant_analysis_is_fast --benchmark
```

**Критерий успеха:**
- Instant analysis <500ms
- Deep analysis >85% accuracy (manual review)
- Coverage >90%

---

#### День 3: Analysis Worker Tests

**Задачи:**
1. Event consumption
2. Async processing
3. Retry logic

**Файлы:**
```
tests/systems/analysis/integration/
└── test_analysis_worker.py                       [500 строк]
```

**Критичные тесты:**
```python
def test_worker_processes_question_answered_event()
def test_worker_publishes_analysis_completed()
def test_worker_retry_on_failure()               # CRITICAL!
def test_worker_handles_queue_backlog()
```

**Команды:**
```bash
pytest tests/systems/analysis/integration/ -v -m integration --run-slow
```

**Критерий успеха:**
- Worker обрабатывает события
- Retry работает
- Queue не переполняется

---

#### День 4: AI API Contract Tests

**Задачи:**
1. Claude API mocking
2. GPT-4 API mocking
3. Fallback logic

**Файлы:**
```
tests/systems/analysis/contracts/
└── test_ai_api_contracts.py                      [300 строк]
```

**Команды:**
```bash
pytest tests/systems/analysis/contracts/ -v
```

**Критерий успеха:**
- AI APIs корректно используются
- Fallback работает
- Cost optimization соблюден

---

### Итоги Фазы 2

**Написано тестов:** ~1550 строк
**Coverage Analysis:** >90%
**Время:** 4 дня
**Статус:** ✅ Analysis System готов

---

## ФАЗА 3: PROFILE SYSTEM (НЕДЕЛЯ 4)

### Цель: 85% покрытие Profile System

#### День 1-2: Soul Architect Tests

**Задачи:**
1. Multilayer personality model
2. 693D vector generation
3. Trait history

**Файлы:**
```
tests/systems/profile/unit/
├── test_soul_architect.py                        [400 строк]
└── test_personality_vector.py                    [250 строк]
```

**Команды:**
```bash
pytest tests/systems/profile/unit/ -v
```

**Критерий успеха:**
- 693D vector корректен
- История отслеживается
- Coverage >85%

---

#### День 3: Profile Event Tests

**Задачи:**
1. Слушает AnalysisCompletedEvent
2. Публикует ProfileUpdatedEvent
3. Qdrant sync

**Файлы:**
```
tests/systems/profile/integration/
├── test_profile_events.py                        [350 строк]
└── test_qdrant_sync.py                          [250 строк]
```

**Команды:**
```bash
pytest tests/systems/profile/integration/ -v -m integration
```

**Критерий успеха:**
- События обрабатываются
- Qdrant обновляется
- Нет data loss

---

#### День 4: Database Migration Tests

**Задачи:**
1. Soul Architect миграция
2. Data integrity
3. Performance

**Файлы:**
```
tests/migrations/
└── test_soul_architect_migration.py              [200 строк]
```

**Команды:**
```bash
pytest tests/migrations/ -v
# Также ручная проверка:
alembic upgrade head
psql -U postgres -d n8n_test -c "\dt selfology.*"
```

**Критерий успеха:**
- Миграция создала таблицы
- Индексы работают
- Данные не потеряны

---

### Итоги Фазы 3

**Написано тестов:** ~1450 строк
**Coverage Profile:** >85%
**Время:** 4 дня
**Статус:** ✅ Profile System готов

---

## ФАЗА 4-5: TELEGRAM & COACH (НЕДЕЛИ 5-6)

### Telegram System (85% coverage)

**Тесты:**
```
tests/systems/telegram/
├── unit/
│   ├── test_fsm_states.py                       [250 строк]
│   └── test_message_routing.py                  [200 строк]
├── integration/
│   └── test_telegram_events.py                  [300 строк]
└── e2e/
    └── test_bot_interaction.py                  [250 строк]
```

**Время:** 3 дня
**Coverage:** >85%

---

### Coach System (90% coverage)

**Тесты:**
```
tests/systems/coach/
├── unit/
│   ├── test_personalization.py                  [300 строк]
│   └── test_insight_generation.py               [250 строк]
├── integration/
│   └── test_coach_events.py                     [300 строк]
└── ai/
    └── test_coach_quality.py                    [200 строк]
```

**Время:** 3 дня
**Coverage:** >90%

---

## ФАЗА 6: ИНТЕГРАЦИЯ (НЕДЕЛЯ 7)

### E2E Tests для всех систем

**Задачи:**
1. Complete user journey
2. All systems working together
3. Data consistency

**Файлы:**
```
tests/e2e/
├── test_complete_user_journey.py                [500 строк]
├── test_system_integration.py                   [400 строк]
└── test_data_consistency.py                     [300 строк]
```

**Критичный тест:**
```python
async def test_full_onboarding_to_insight():
    """
    /start → onboarding → 100 questions → AI analysis →
    profile update → coach generates insight
    """
    # Полный user journey
    pass
```

**Команды:**
```bash
pytest tests/e2e/ -v --run-slow
```

**Критерий успеха:**
- E2E тест проходит от начала до конца
- Все события доставляются
- Данные консистентны

**Время:** 4 дня
**Coverage E2E:** >80%

---

## ФАЗА 7: PERFORMANCE & CHAOS (НЕДЕЛЯ 8)

### Load Tests

**Файлы:**
```
tests/load/
├── locustfile.py                                [300 строк]
├── test_performance_benchmarks.py               [250 строк]
└── scenarios/
    ├── normal_load.py                           [150 строк]
    ├── peak_load.py                             [150 строк]
    └── stress_test.py                           [150 строк]
```

**Команды:**
```bash
# Запустить Locust
locust -f tests/load/locustfile.py --host=http://localhost:8000

# Или headless
locust -f tests/load/locustfile.py --host=http://localhost:8000 \
       --users 100 --spawn-rate 10 --run-time 10m --headless

# Benchmarks
pytest tests/load/test_performance_benchmarks.py --benchmark-only
```

**Критерий успеха:**
- 100 одновременных пользователей
- 1000 запросов/минуту
- Response time <500ms (p95)

**Время:** 2 дня

---

### Chaos Tests

**Файлы:**
```
tests/chaos/
├── test_worker_failure.py                       [300 строк]
├── test_redis_failure.py                        [300 строк]
├── test_db_timeout.py                           [250 строк]
└── test_network_partition.py                    [200 строк]
```

**Команды:**
```bash
pytest tests/chaos/ -v --run-slow -m chaos
```

**Критерий успеха:**
- Система переживает сбои
- Graceful degradation
- No data loss

**Время:** 2 дня

---

## ФАЗА 8: PRODUCTION (НЕДЕЛЯ 9)

### Smoke Tests + Monitoring

**Файлы:**
```
tests/production/
├── test_smoke.py                                [150 строк]
├── test_monitoring.py                           [150 строк]
└── test_rollback.py                             [100 строк]
```

**Команды:**
```bash
# Production smoke test
pytest tests/production/test_smoke.py -v --env=production

# Monitoring check
pytest tests/production/test_monitoring.py -v
```

**Критерий успеха:**
- Smoke test проходит на production
- Мониторинг работает
- Rollback plan готов

**Время:** 1 день

---

## SUMMARY: ИТОГОВАЯ СТАТИСТИКА

### Написано тестов по фазам

| Фаза | Компонент | Строк кода | Время | Coverage |
|------|-----------|------------|-------|----------|
| 0 | Event Bus | 2,650 | 4 дня | 95% |
| 1 | Onboarding | 1,450 | 4 дня | 85% |
| 2 | Analysis | 1,550 | 4 дня | 90% |
| 3 | Profile | 1,450 | 4 дня | 85% |
| 4 | Telegram | 1,000 | 3 дня | 80% |
| 5 | Coach | 1,050 | 3 дня | 90% |
| 6 | E2E Integration | 1,200 | 4 дня | 80% |
| 7 | Load + Chaos | 1,650 | 4 дня | - |
| 8 | Production | 400 | 1 день | - |
| **ИТОГО** | **Все системы** | **12,400** | **31 день** | **>85%** |

---

## ROADMAP: КОГДА ЧТО ПИСАТЬ

### Неделя 1 (Фаза 0): EVENT BUS
- **День 1:** Setup + Event Publisher (450 строк)
- **День 2:** Event Subscriber + Redis Integration (700 строк)
- **День 3:** Contract Tests (500 строк)
- **День 4:** Resilience Tests (650 строк)
- **День 5:** Документация + ревью

### Неделя 2 (Фаза 1): ONBOARDING
- **День 1:** QuestionRouter (400 строк)
- **День 2:** FatigueDetector (350 строк)
- **День 3:** Event Publication (300 строк)
- **День 4:** E2E + Regression (400 строк)
- **День 5:** Bugfixes

### Неделя 3 (Фаза 2): ANALYSIS
- **День 1-2:** AnswerAnalyzer (750 строк)
- **День 3:** Analysis Worker (500 строк)
- **День 4:** AI API Contracts (300 строк)
- **День 5:** Performance tuning

### Неделя 4 (Фаза 3): PROFILE
- **День 1-2:** Soul Architect (650 строк)
- **День 3:** Profile Events (600 строк)
- **День 4:** Migration Tests (200 строк)
- **День 5:** Qdrant integration review

### Неделя 5 (Фаза 4): TELEGRAM
- **День 1-2:** FSM + Routing (450 строк)
- **День 3:** Event Integration (300 строк)
- **День 4:** E2E Bot Tests (250 строк)

### Неделя 6 (Фаза 5): COACH
- **День 1-2:** Personalization (550 строк)
- **День 3:** Coach Events (300 строк)
- **День 4:** Quality Tests (200 строк)

### Неделя 7 (Фаза 6): INTEGRATION
- **День 1-2:** Complete User Journey (500 строк)
- **День 3:** System Integration (400 строк)
- **День 4:** Data Consistency (300 строк)
- **День 5:** Full system review

### Неделя 8 (Фаза 7): PERFORMANCE
- **День 1-2:** Load Tests (850 строк)
- **День 3-4:** Chaos Tests (800 строк)
- **День 5:** Analysis & optimization

### Неделя 9 (Фаза 8): PRODUCTION
- **День 1:** Smoke + Monitoring Tests (400 строк)
- **День 2-5:** Production deployment + final validation

---

## ИНСТРУМЕНТЫ И SETUP

### Необходимые пакеты

```bash
# Core testing
pip install pytest==7.4.3
pip install pytest-asyncio==0.21.1
pip install pytest-cov==4.1.0
pip install pytest-mock==3.12.0
pip install pytest-timeout==2.2.0
pip install pytest-xdist==3.5.0

# Fixtures & mocking
pip install factory-boy==3.3.0
pip install faker==22.0.0
pip install responses==0.24.1
pip install freezegun==1.4.0

# Performance testing
pip install pytest-benchmark==4.0.0
pip install locust==2.19.1

# Chaos testing
pip install chaos-toolkit==1.17.0

# Coverage reporting
pip install coverage==7.4.0
pip install pytest-html==4.1.1
```

### CI/CD Pipeline

```yaml
# .github/workflows/tests.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

      redis:
        image: redis:7-alpine
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r requirements-test.txt

      - name: Run unit tests
        run: pytest tests/ -m unit --cov=. --cov-report=xml

      - name: Run integration tests
        run: pytest tests/ -m integration

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml
```

---

## МЕТРИКИ УСПЕХА

### Coverage Targets по компонентам

| Компонент | Target | Current | Gap |
|-----------|--------|---------|-----|
| Event Bus | 95% | 0% | +95% |
| Onboarding | 85% | 20% | +65% |
| Analysis | 90% | 30% | +60% |
| Profile | 85% | 40% | +45% |
| Telegram | 80% | 50% | +30% |
| Coach | 90% | 25% | +65% |
| **Overall** | **>85%** | **40%** | **+45%** |

### Quality Gates

**Блокируют merge в main:**
- ❌ Coverage drop >2%
- ❌ P0 tests failing
- ❌ Performance regression >10%
- ❌ Lint errors
- ❌ Security vulnerabilities

**Warning (не блокируют):**
- ⚠️ P1 tests failing
- ⚠️ Coverage drop <2%
- ⚠️ Performance regression <10%

---

## NEXT STEPS

### Немедленные действия (сегодня)

1. ✅ Прочитать TESTING_STRATEGY.md
2. ✅ Прочитать TESTING_CODE_EXAMPLES.md
3. ⬜ Установить pytest и зависимости
4. ⬜ Создать структуру `/tests`
5. ⬜ Скопировать `conftest.py` и `pytest.ini`

### Завтра (День 1 Фазы 0)

1. ⬜ Написать `test_event_publisher.py`
2. ⬜ Запустить первые тесты
3. ⬜ Настроить coverage reporting
4. ⬜ Commit + push

### Эта неделя (Фаза 0)

1. ⬜ Завершить Event Bus test suite
2. ⬜ Достичь 95% coverage
3. ⬜ Запустить Event Bus в production
4. ⬜ Начать Фазу 1

---

## КОНТАКТЫ И ПОДДЕРЖКА

**Документация:**
- Стратегия: `/TESTING_STRATEGY.md`
- Примеры кода: `/TESTING_CODE_EXAMPLES.md`
- План имплементации: `/TESTING_IMPLEMENTATION_PLAN.md` (этот файл)

**Команды:**
```bash
# Запустить все тесты
pytest

# Только быстрые
pytest -m unit

# С coverage
pytest --cov=. --cov-report=html

# Конкретная фаза
pytest tests/event_bus/

# CI mode
pytest -v --cov=. --cov-report=xml --cov-fail-under=85
```

**Мониторинг прогресса:**
```bash
# Текущий coverage
pytest --cov=. --cov-report=term-missing

# Coverage по компонентам
pytest --cov=core --cov=systems --cov-report=term

# HTML отчет
pytest --cov=. --cov-report=html
open htmlcov/index.html
```

---

**Создано:** 2025-09-30
**Автор:** QA Team + AI Test Automation Expert
**Статус:** Ready to implement
**Первый шаг:** Фаза 0, День 1 - Event Bus Core Tests
