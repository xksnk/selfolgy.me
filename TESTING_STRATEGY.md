# СТРАТЕГИЯ ТЕСТИРОВАНИЯ SELFOLOGY
## Рефакторинг монолита в микросервисы (9 недель)

**Цель:** Достичь покрытия >85% при переходе с 40% без простоев в критической системе психологического AI коуча

**Критичность:** ВЫСОКАЯ - психологический AI коуч, работает с чувствительными данными пользователей

---

## СОДЕРЖАНИЕ

1. [Стратегия по фазам](#стратегия-по-фазам)
2. [Event Bus Test Suite](#event-bus-test-suite)
3. [Regression Testing](#regression-testing)
4. [Contract Testing](#contract-testing)
5. [Performance & Load Testing](#performance--load-testing)
6. [Chaos Engineering](#chaos-engineering)
7. [Приоритизация тестов](#приоритизация-тестов)
8. [Инфраструктура тестирования](#инфраструктура-тестирования)

---

## СТРАТЕГИЯ ПО ФАЗАМ

### ФАЗА 0: Подготовка (Неделя 1) - Event Bus Foundation

**Цель покрытия:** 95% для Event Bus (критический компонент)

#### Типы тестов:

1. **Unit Tests** - Event Bus Core
   - Publish/Subscribe механизмы
   - Сериализация событий
   - Error handling

2. **Integration Tests** - Redis Streams
   - Подключение к Redis
   - Consumer groups
   - Message delivery гарантии

3. **Contract Tests** - Event Schemas
   - Валидация payload
   - Backward compatibility
   - Schema versioning

**Минимальный набор для безопасной работы:**
- Publish успешно отправляет событие
- Subscribe получает событие
- Обработка ошибок не роняет систему
- Redis недоступен - graceful degradation

**Критерий успеха:** Все тесты зеленые + manual smoke test событий

---

### ФАЗА 1: Onboarding System (Неделя 2)

**Цель покрытия:** 85% для Onboarding

#### Типы тестов:

1. **Unit Tests** - Business Logic
   - QuestionRouter (Smart Mix алгоритм)
   - FatigueDetector логика
   - Session state management

2. **Integration Tests** - Event Publication
   - Публикация `QuestionAnsweredEvent`
   - Публикация `FatigueDetectedEvent`
   - Event Bus интеграция

3. **E2E Tests** - User Journey
   - /onboarding → первый вопрос → ответ → следующий вопрос
   - Усталость триггерит предложение паузы

**Минимальный набор:**
- QuestionRouter выбирает правильные вопросы по Smart Mix
- FatigueDetector корректно детектирует усталость
- События публикуются при каждом ответе
- Данные корректно сохраняются в БД

**Regression Check:**
- Старый /start флоу продолжает работать
- Существующие пользователи не сломаны

---

### ФАЗА 2: Analysis System (Неделя 3)

**Цель покрытия:** 90% для Analysis (AI критично)

#### Типы тестов:

1. **Unit Tests** - Analysis Logic
   - TraitExtractor извлечение черт
   - AIModelRouter выбор модели
   - Двухфазный анализ (instant + deep)

2. **Integration Tests** - Event Consumption
   - Worker слушает `QuestionAnsweredEvent`
   - Публикует `AnalysisCompletedEvent`
   - Redis queue processing

3. **Contract Tests** - AI API
   - Claude API contract
   - GPT-4 API contract
   - Fallback на GPT-4o-mini

4. **Performance Tests**
   - Instant analysis <500ms
   - Deep analysis <10s
   - Queue не переполняется

**Минимальный набор:**
- Worker обрабатывает события из очереди
- AI анализ возвращает корректные черты
- Retry logic при ошибках API
- Graceful degradation если AI недоступен

**Regression Check:**
- Существующие анализы продолжают работать
- Векторы в Qdrant обновляются корректно

---

### ФАЗА 3: Profile System (Неделя 4)

**Цель покрытия:** 85% для Profile System

#### Типы тестов:

1. **Unit Tests** - Soul Architect
   - Multilayer personality model (693D)
   - TraitHistory отслеживание
   - UniqueSignature генерация

2. **Integration Tests** - Event Consumption
   - Слушает `AnalysisCompletedEvent`
   - Обновляет черты в БД
   - Публикует `ProfileUpdatedEvent`

3. **Database Tests** - Alembic Migrations
   - Миграция создала таблицы
   - personality_profiles, trait_history, unique_signatures
   - Индексы работают эффективно

4. **Vector Tests** - Qdrant Integration
   - 3 уровня векторов (512D/1536D/3072D)
   - Semantic search работает
   - Update не теряет данные

**Минимальный набор:**
- Профили сохраняются корректно
- История изменений отслеживается
- События обрабатываются асинхронно
- Qdrant sync работает

**Regression Check:**
- Существующие профили мигрируют без потерь
- Старые Soul Architect данные доступны

---

### ФАЗА 4: Telegram System (Неделя 5)

**Цель покрытия:** 80% для Telegram Gateway

#### Типы тестов:

1. **Unit Tests** - Gateway Logic
   - FSM state transitions
   - Message routing
   - Command handlers

2. **Integration Tests** - Event Gateway
   - Публикует `UserStartedEvent`, `UserSentAnswerEvent`
   - Слушает `ShowQuestionEvent`, `ShowInsightEvent`
   - FSM синхронизирован с событиями

3. **E2E Tests** - Bot Interaction
   - Mock Telegram API
   - Полный user journey
   - Button callbacks

**Минимальный набор:**
- Бот принимает сообщения
- FSM корректно меняет состояния
- События отправляются на другие системы
- Ответы отображаются пользователю

**Regression Check:**
- Все существующие команды работают
- Старые пользователи не сломаны

---

### ФАЗА 5: Coach System (Неделя 6)

**Цель покрытия:** 90% для Coach (критичная AI система)

#### Типы тестов:

1. **Unit Tests** - Coach Logic
   - Персонализация по профилю
   - Инсайт-генерация
   - Стиль общения адаптация

2. **Integration Tests** - Profile Integration
   - Слушает `ProfileUpdatedEvent`
   - Загружает векторный контекст из Qdrant
   - Публикует `InsightGeneratedEvent`

3. **AI Tests** - Coach Quality
   - Инсайты релевантны профилю
   - Тон соответствует пользователю
   - Безопасность (no harmful content)

**Минимальный набор:**
- Coach использует актуальный профиль
- Инсайты генерируются корректно
- Персонализация работает
- Сохранение в БД

**Regression Check:**
- Старые чат-сессии доступны
- Quality метрики не ухудшились

---

### ФАЗА 6: Интеграция (Неделя 7)

**Цель покрытия:** 85% для E2E флоу

#### Типы тестов:

1. **E2E Tests** - Complete User Journey
   - /start → онбординг → анализ → профиль → коуч → инсайт
   - 100 вопросов полный цикл
   - Fatigue detection срабатывает

2. **Integration Tests** - System Boundaries
   - Все системы общаются через события
   - Нет прямых вызовов между системами
   - Async обработка не теряет данные

3. **Smoke Tests** - Production-like
   - Реальные данные (anonymized)
   - Полные AI вызовы
   - Qdrant с реальными векторами

**Минимальный набор:**
- E2E тест от начала до конца проходит
- Все события доставляются
- Данные консистентны между системами
- Мониторинг показывает здоровье

**Regression Check:**
- Все критические флоу работают
- Performance не ухудшился

---

### ФАЗА 7: Тестирование (Неделя 8)

**Цель:** Stress testing + Chaos engineering

#### Типы тестов:

1. **Load Tests** - Performance
   - 100 одновременных пользователей
   - 1000 запросов/минуту
   - Redis queue не переполняется

2. **Stress Tests** - Breaking Point
   - Где система ломается?
   - Graceful degradation?
   - Recovery после перегрузки

3. **Chaos Tests** - Failure Scenarios
   - Kill Analysis Worker
   - Disconnect Redis
   - Database timeout
   - AI API unavailable

4. **Security Tests** - GDPR Compliance
   - SQL injection защита
   - Rate limiting
   - Data encryption

**Минимальный набор:**
- Система выдерживает целевую нагрузку
- Fault tolerance работает
- Security checks пройдены

---

### ФАЗА 8: Production Deployment (Неделя 9)

**Цель:** Smoke tests + Monitoring

#### Типы тестов:

1. **Smoke Tests** - Production
   - Все системы запущены
   - Health checks зеленые
   - Критические флоу работают

2. **Monitoring Tests** - Observability
   - Метрики собираются
   - Алерты настроены
   - Логи структурированы

3. **Rollback Tests** - Safety Net
   - Rollback работает
   - Данные не теряются
   - Downtime минимален

**Минимальный набор:**
- Production smoke test проходит
- Мониторинг работает
- Rollback план протестирован

---

## EVENT BUS TEST SUITE

### Структура тестов Event Bus

```
tests/
├── event_bus/
│   ├── unit/
│   │   ├── test_event_publisher.py
│   │   ├── test_event_subscriber.py
│   │   ├── test_event_serialization.py
│   │   └── test_error_handling.py
│   ├── integration/
│   │   ├── test_redis_streams.py
│   │   ├── test_consumer_groups.py
│   │   └── test_event_delivery.py
│   ├── contract/
│   │   ├── test_event_schemas.py
│   │   └── test_backward_compatibility.py
│   └── resilience/
│       ├── test_redis_failover.py
│       ├── test_network_issues.py
│       └── test_message_retry.py
```

### Примеры тестов - см. секцию ниже с кодом

---

## REGRESSION TESTING

### Стратегия Regression Testing

**Цель:** Убедиться, что при выделении систем ничего не сломалось

#### 1. Snapshot Testing для критических флоу

```python
# tests/regression/test_user_journey_snapshots.py
```

Критические точки для snapshot:
- Формат вопросов пользователю
- Структура AI анализа
- Формат профиля
- Структура инсайтов

#### 2. Database Migration Testing

```python
# tests/regression/test_migrations.py
```

Проверки:
- Данные не потеряны
- Foreign keys не сломаны
- Индексы работают
- Performance не ухудшился

#### 3. API Compatibility Testing

```python
# tests/regression/test_api_compatibility.py
```

Гарантии:
- Старые клиенты продолжают работать
- Новые поля опциональны
- Backward compatible changes

#### 4. Visual Regression для Telegram

```python
# tests/regression/test_telegram_ui.py
```

Проверки:
- Кнопки отображаются
- Форматирование сохранено
- Эмодзи на месте

---

## CONTRACT TESTING

### Event Contract Testing

**Философия:** Events - это контракт между системами

#### Producer Contract Tests

```python
# tests/contracts/producers/test_onboarding_events.py
```

Проверяет:
- Onboarding публикует правильные события
- Schema событий соответствует контракту
- Все обязательные поля присутствуют

#### Consumer Contract Tests

```python
# tests/contracts/consumers/test_analysis_consumes.py
```

Проверяет:
- Analysis корректно обрабатывает события
- Не падает на неожиданные поля
- Graceful degradation

#### Schema Registry

```yaml
# contracts/events/question_answered_event.yaml
```

Версионирование схем:
- v1, v2, v3...
- Breaking changes require new version
- Deprecated fields marked

---

## PERFORMANCE & LOAD TESTING

### Load Testing Setup

**Инструменты:** Locust + pytest-benchmark

#### Сценарий 1: Нормальная нагрузка

```python
# tests/load/test_normal_load.py
```

Параметры:
- 100 одновременных пользователей
- 1000 запросов/минуту
- Продолжительность: 10 минут

Метрики:
- Response time <500ms (p95)
- Error rate <0.1%
- Queue depth <100

#### Сценарий 2: Пиковая нагрузка

```python
# tests/load/test_peak_load.py
```

Параметры:
- 300 одновременных пользователей
- 3000 запросов/минуту
- Продолжительность: 5 минут

Метрики:
- Response time <1s (p95)
- Error rate <1%
- Graceful degradation

#### Сценарий 3: Stress Testing

```python
# tests/load/test_stress.py
```

Параметры:
- Постепенное увеличение до breakdown
- Найти breaking point
- Recovery time после снижения

---

## CHAOS ENGINEERING

### Chaos Testing Scenarios

**Философия:** Убить компоненты и посмотреть, что сломается

#### Сценарий 1: Kill Analysis Worker

```python
# tests/chaos/test_worker_failure.py
```

Последствия:
- Анализы останавливаются
- Очередь растет
- НО: пользователь продолжает работать
- Recovery: новый worker подхватывает очередь

#### Сценарий 2: Disconnect Redis

```python
# tests/chaos/test_redis_failure.py
```

Последствия:
- События не доставляются
- Circuit breaker срабатывает
- Fallback на direct calls
- Recovery: события из dead letter queue

#### Сценарий 3: Database Timeout

```python
# tests/chaos/test_db_timeout.py
```

Последствия:
- Write operations failят
- Retry logic срабатывает
- Eventual consistency
- Recovery: retried operations succeed

#### Сценарий 4: AI API Unavailable

```python
# tests/chaos/test_ai_failure.py
```

Последствия:
- Fallback на более простую модель
- Degraded experience
- Пользователь получает базовый ответ
- Recovery: нормальная работа восстанавливается

#### Сценарий 5: Network Partition

```python
# tests/chaos/test_network_partition.py
```

Последствия:
- Системы не видят друг друга
- Eventual consistency
- No data loss
- Recovery: sync после восстановления

---

## ПРИОРИТИЗАЦИЯ ТЕСТОВ

### Критичность тестов

#### P0 (Блокирующие) - ДОЛЖНЫ ПРОХОДИТЬ всегда

1. **Event Bus publish/subscribe** - без этого система не работает
2. **QuestionRouter Smart Mix** - ядро онбординга
3. **AI анализ trait extraction** - критичная функциональность
4. **Profile update events** - данные пользователя
5. **E2E user journey** - основной флоу

#### P1 (Критичные) - блокируют релиз

1. **FatigueDetector** - UX quality
2. **Coach персонализация** - core feature
3. **Qdrant vector sync** - данные пользователя
4. **Regression tests** - ничего не сломалось
5. **Load tests** - система выдерживает нагрузку

#### P2 (Важные) - желательно чинить быстро

1. **Contract tests** - API compatibility
2. **Performance benchmarks** - оптимизация
3. **Chaos tests** - resilience
4. **Security tests** - compliance

#### P3 (Nice to have) - можно отложить

1. **Visual regression** - UI косметика
2. **Extended load tests** - edge cases
3. **Documentation tests** - примеры в доках

---

## ИНФРАСТРУКТУРА ТЕСТИРОВАНИЯ

### CI/CD Pipeline

```yaml
# .github/workflows/tests.yml
```

Стадии:
1. **Fast Tests** (2 min): Unit tests + lint
2. **Integration Tests** (5 min): DB + Redis + Event Bus
3. **E2E Tests** (10 min): Full user journey
4. **Performance Tests** (15 min): Load + stress
5. **Chaos Tests** (10 min): Failure scenarios

### Test Environments

1. **Local Dev** - docker-compose с моками
2. **CI** - GitHub Actions с real services
3. **Staging** - production-like с anonymized data
4. **Production** - smoke tests only

### Test Data Management

```python
# tests/fixtures/factories.py
```

Factories:
- UserFactory
- QuestionFactory
- AnswerFactory
- ProfileFactory
- EventFactory

### Mocking Strategy

1. **AI APIs** - всегда mock в unit tests
2. **Redis** - real в integration, mock в unit
3. **Database** - real с test schema
4. **Telegram API** - всегда mock
5. **Qdrant** - real с test collection

---

## МЕТРИКИ УСПЕХА

### Coverage Targets

- **Overall:** >85%
- **Event Bus:** >95%
- **Analysis System:** >90%
- **Coach System:** >90%
- **Profile System:** >85%
- **Onboarding:** >85%
- **Telegram Gateway:** >80%

### Performance Targets

- **Unit tests:** <30s все вместе
- **Integration tests:** <5min все вместе
- **E2E tests:** <15min все вместе
- **Full CI pipeline:** <30min

### Quality Gates

Блокируют merge:
- Coverage drop >2%
- P0 tests failing
- Performance regression >10%
- Lint errors

---

## ИНСТРУМЕНТЫ

### Testing Framework

```bash
pytest==7.4.3
pytest-asyncio==0.21.1
pytest-cov==4.1.0
pytest-mock==3.12.0
pytest-benchmark==4.0.0
pytest-timeout==2.2.0
pytest-xdist==3.5.0  # parallel execution
```

### Load Testing

```bash
locust==2.19.1
pytest-benchmark==4.0.0
```

### Mocking & Fixtures

```bash
factory-boy==3.3.0
faker==22.0.0
responses==0.24.1  # HTTP mocking
freezegun==1.4.0  # time mocking
```

### Coverage & Reporting

```bash
coverage==7.4.0
pytest-html==4.1.1
pytest-json-report==1.5.0
```

### Chaos Testing

```bash
chaos-toolkit==1.17.0
toxiproxy==2.5.0  # network simulation
```

---

## NEXT STEPS

### Неделя 1 (Фаза 0) - Immediate Actions

1. Создать `/tests` структуру
2. Настроить pytest с async support
3. Написать Event Bus test suite (см. примеры кода ниже)
4. Настроить CI pipeline
5. Установить coverage baseline

### Code Examples - см. следующий файл

---

**Владелец:** QA Team + DevOps
**Reviewers:** Все разработчики
**Обновлено:** 2025-09-30
**Следующий review:** После каждой фазы
