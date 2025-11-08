# TESTING DOCUMENTATION INDEX

> Навигация по документации тестирования Selfology

---

## БЫСТРЫЙ СТАРТ

**Новичок?** Начни здесь:
1. Прочитай [TESTING_STRATEGY_SUMMARY.md](TESTING_STRATEGY_SUMMARY.md) (5 минут)
2. Открой [TESTING_CODE_EXAMPLES.md](TESTING_CODE_EXAMPLES.md) (примеры)
3. Следуй [TESTING_README.md](TESTING_README.md) (quick start)

**Готов писать тесты?**
1. Открой [TESTING_IMPLEMENTATION_PLAN.md](TESTING_IMPLEMENTATION_PLAN.md)
2. Найди текущую фазу
3. Копируй примеры из [TESTING_CODE_EXAMPLES.md](TESTING_CODE_EXAMPLES.md)
4. Запускай `./scripts/validate_test_coverage.py`

---

## ДОКУМЕНТЫ

### 📖 Основная документация

#### 1. TESTING_STRATEGY_SUMMARY.md
- **Что:** Executive summary всей стратегии
- **Для кого:** Менеджеры, tech leads
- **Размер:** 741 строка
- **Читать:** 10 минут
- **Содержит:** Обзор стратегии, ключевые компоненты, метрики, roadmap

[Открыть TESTING_STRATEGY_SUMMARY.md](TESTING_STRATEGY_SUMMARY.md)

---

#### 2. TESTING_STRATEGY.md
- **Что:** Детальная стратегия тестирования
- **Для кого:** QA engineers, разработчики
- **Размер:** 741 строка
- **Читать:** 20 минут
- **Содержит:**
  - Стратегия по каждой из 9 фаз
  - Event Bus test suite
  - Regression testing стратегия
  - Contract testing подход
  - Performance & Load testing
  - Chaos engineering
  - Приоритизация тестов (P0-P3)
  - Инфраструктура и инструменты

[Открыть TESTING_STRATEGY.md](TESTING_STRATEGY.md)

---

#### 3. TESTING_CODE_EXAMPLES.md
- **Что:** Готовые примеры pytest кода
- **Для кого:** Разработчики, пишущие тесты
- **Размер:** 2499 строк
- **Читать:** Как справочник
- **Содержит:**
  - 21 полный пример pytest кода
  - Event Bus tests (Publisher, Subscriber, Redis)
  - Onboarding tests (QuestionRouter, FatigueDetector)
  - Analysis tests (Analyzer, Worker, AI APIs)
  - Profile tests (Soul Architect, Events)
  - Contract tests (Producer, Consumer)
  - Load tests (Locust)
  - Chaos tests (Worker failure, Redis failure)
  - E2E tests (Complete user journey)
  - Fixtures и conftest.py

[Открыть TESTING_CODE_EXAMPLES.md](TESTING_CODE_EXAMPLES.md)

---

#### 4. TESTING_IMPLEMENTATION_PLAN.md
- **Что:** Пошаговый план имплементации
- **Для кого:** Команда, делающая рефакторинг
- **Размер:** 1009 строк
- **Читать:** Как roadmap
- **Содержит:**
  - Детальный план на 9 недель (31 рабочий день)
  - День за днём что писать
  - Сколько строк кода на каждую задачу
  - Команды для запуска и валидации
  - Критерии успеха для каждой фазы
  - Timeline и roadmap
  - Coverage targets по компонентам

[Открыть TESTING_IMPLEMENTATION_PLAN.md](TESTING_IMPLEMENTATION_PLAN.md)

---

#### 5. TESTING_README.md
- **Что:** Quick start guide
- **Для кого:** Все
- **Размер:** 548 строк
- **Читать:** 10 минут
- **Содержит:**
  - Быстрый старт
  - Установка зависимостей
  - Команды для запуска тестов
  - Troubleshooting
  - Roadmap
  - CI/CD integration

[Открыть TESTING_README.md](TESTING_README.md)

---

### 🔧 Инструменты

#### scripts/validate_test_coverage.py
- **Что:** Автоматическая валидация coverage
- **Язык:** Python (343 строки)
- **Использование:** `./scripts/validate_test_coverage.py`
- **Функции:**
  - Проверка P0 тестов
  - Coverage по компонентам
  - Quality gates
  - Прогресс по фазам
  - Цветной отчет в терминале

[Открыть scripts/validate_test_coverage.py](scripts/validate_test_coverage.py)

---

## НАВИГАЦИЯ ПО ЗАДАЧАМ

### Я хочу...

#### ...понять общую стратегию
→ Читай: [TESTING_STRATEGY_SUMMARY.md](TESTING_STRATEGY_SUMMARY.md)

#### ...написать Event Bus тесты
→ Открой: [TESTING_CODE_EXAMPLES.md](TESTING_CODE_EXAMPLES.md) (секция "Event Bus Tests")
→ Следуй: [TESTING_IMPLEMENTATION_PLAN.md](TESTING_IMPLEMENTATION_PLAN.md) (Фаза 0)

#### ...написать Onboarding тесты
→ Открой: [TESTING_CODE_EXAMPLES.md](TESTING_CODE_EXAMPLES.md) (секция "Onboarding System Tests")
→ Следуй: [TESTING_IMPLEMENTATION_PLAN.md](TESTING_IMPLEMENTATION_PLAN.md) (Фаза 1)

#### ...настроить pytest
→ Читай: [TESTING_README.md](TESTING_README.md) (секция "Быстрый старт")
→ Копируй: conftest.py из [TESTING_CODE_EXAMPLES.md](TESTING_CODE_EXAMPLES.md)

#### ...запустить тесты
→ Команды: [TESTING_README.md](TESTING_README.md) (секция "Команды")
```bash
pytest
pytest -m unit
pytest --cov=. --cov-report=html
```

#### ...проверить прогресс
→ Запусти: `./scripts/validate_test_coverage.py`

#### ...написать Load tests
→ Открой: [TESTING_CODE_EXAMPLES.md](TESTING_CODE_EXAMPLES.md) (секция "Load Tests")

#### ...написать Chaos tests
→ Открой: [TESTING_CODE_EXAMPLES.md](TESTING_CODE_EXAMPLES.md) (секция "Chaos Tests")

#### ...узнать, что писать сегодня
→ Открой: [TESTING_IMPLEMENTATION_PLAN.md](TESTING_IMPLEMENTATION_PLAN.md)
→ Найди текущую неделю и день

#### ...понять приоритеты
→ Читай: [TESTING_STRATEGY.md](TESTING_STRATEGY.md) (секция "Приоритизация тестов")
→ P0: Блокирующие
→ P1: Критичные
→ P2-P3: Важные, Nice to have

---

## СТРУКТУРА ПРОЕКТА

```
selfology/
├── TESTING_STRATEGY_SUMMARY.md      # Executive summary
├── TESTING_STRATEGY.md              # Полная стратегия
├── TESTING_CODE_EXAMPLES.md         # Примеры кода
├── TESTING_IMPLEMENTATION_PLAN.md   # Пошаговый план
├── TESTING_README.md                # Quick start
├── TESTING_INDEX.md                 # Этот файл
│
├── scripts/
│   └── validate_test_coverage.py    # Автоматическая валидация
│
└── tests/                           # (создать)
    ├── conftest.py
    ├── pytest.ini
    ├── fixtures/
    │   └── factories.py
    ├── event_bus/
    │   ├── unit/
    │   ├── integration/
    │   ├── contract/
    │   └── resilience/
    ├── systems/
    │   ├── onboarding/
    │   ├── analysis/
    │   ├── profile/
    │   ├── telegram/
    │   └── coach/
    ├── e2e/
    ├── load/
    ├── chaos/
    └── production/
```

---

## WORKFLOW

### Типичный рабочий процесс

#### 1. Узнать, что делать
```bash
# Открыть план
cat TESTING_IMPLEMENTATION_PLAN.md | grep "Неделя 1"
```

#### 2. Посмотреть пример
```bash
# Открыть примеры
cat TESTING_CODE_EXAMPLES.md | grep -A 50 "test_event_publisher"
```

#### 3. Скопировать и адаптировать
```bash
# Создать файл
mkdir -p tests/event_bus/unit
cp TESTING_CODE_EXAMPLES.md tests/event_bus/unit/test_event_publisher.py
# Редактировать...
```

#### 4. Запустить
```bash
pytest tests/event_bus/unit/test_event_publisher.py -v
```

#### 5. Проверить coverage
```bash
pytest tests/event_bus/ --cov=core.event_bus --cov-report=html
open htmlcov/index.html
```

#### 6. Валидация
```bash
./scripts/validate_test_coverage.py
```

#### 7. Commit
```bash
git add tests/
git commit -m "Add Event Bus unit tests"
git push
```

---

## МЕТРИКИ И KPI

### Coverage Targets

| Компонент | Current | Target | Status |
|-----------|---------|--------|--------|
| Event Bus | 0% | 95% | ⏳ TODO |
| Onboarding | 20% | 85% | 🚧 In Progress |
| Analysis | 30% | 90% | 🚧 In Progress |
| Profile | 40% | 85% | 🚧 In Progress |
| Telegram | 50% | 80% | 🚧 In Progress |
| Coach | 25% | 90% | 🚧 In Progress |
| **Overall** | **~40%** | **>85%** | **⚠️ Gap: +45%** |

### Timeline

| Фаза | Компонент | Срок | Status |
|------|-----------|------|--------|
| 0 | Event Bus | Неделя 1 | ⏳ TODO |
| 1 | Onboarding | Неделя 2 | ⏳ TODO |
| 2 | Analysis | Неделя 3 | ⏳ TODO |
| 3 | Profile | Неделя 4 | ⏳ TODO |
| 4 | Telegram | Неделя 5 | ⏳ TODO |
| 5 | Coach | Неделя 6 | ⏳ TODO |
| 6 | Integration | Неделя 7 | ⏳ TODO |
| 7 | Performance | Неделя 8 | ⏳ TODO |
| 8 | Production | Неделя 9 | ⏳ TODO |

---

## КОМАНДЫ ШПАРГАЛКА

### Запуск тестов
```bash
# Все тесты
pytest

# Unit только
pytest -m unit

# Integration
pytest -m integration

# E2E
pytest -m e2e --run-slow

# Chaos
pytest -m chaos --run-slow

# С coverage
pytest --cov=. --cov-report=html

# Параллельно
pytest -n 4

# Конкретный тест
pytest tests/event_bus/unit/test_event_publisher.py::TestEventPublisher::test_publish_simple_event -vv
```

### Валидация
```bash
# Проверить прогресс
./scripts/validate_test_coverage.py

# Coverage report
pytest --cov=. --cov-report=term-missing

# HTML report
pytest --cov=. --cov-report=html
open htmlcov/index.html
```

### Load testing
```bash
# Locust UI
locust -f tests/load/locustfile.py --host=http://localhost:8000

# Headless
locust -f tests/load/locustfile.py --host=http://localhost:8000 \
       --users 100 --spawn-rate 10 --run-time 10m --headless
```

---

## HELP

### Нужна помощь?

**Не понимаю, с чего начать:**
→ Читай: [TESTING_README.md](TESTING_README.md)

**Не знаю, как писать тесты:**
→ Копируй примеры из: [TESTING_CODE_EXAMPLES.md](TESTING_CODE_EXAMPLES.md)

**Не понимаю стратегию:**
→ Читай: [TESTING_STRATEGY_SUMMARY.md](TESTING_STRATEGY_SUMMARY.md)

**Нужен план на сегодня:**
→ Открой: [TESTING_IMPLEMENTATION_PLAN.md](TESTING_IMPLEMENTATION_PLAN.md)

**Тесты не запускаются:**
→ Troubleshooting: [TESTING_README.md](TESTING_README.md) (секция "Troubleshooting")

**Coverage низкий:**
→ Запусти: `pytest --cov=. --cov-report=term-missing`
→ Посмотри: что не покрыто
→ Напиши: тесты для uncovered кода

---

## СТАТИСТИКА

### Созданная документация

| Файл | Размер | Строк | Назначение |
|------|--------|-------|------------|
| TESTING_STRATEGY_SUMMARY.md | 28KB | 741 | Executive summary |
| TESTING_STRATEGY.md | 21KB | 741 | Полная стратегия |
| TESTING_CODE_EXAMPLES.md | 73KB | 2499 | Примеры кода |
| TESTING_IMPLEMENTATION_PLAN.md | 26KB | 1009 | Пошаговый план |
| TESTING_README.md | 15KB | 548 | Quick start |
| TESTING_INDEX.md | 8KB | 300 | Навигация |
| validate_test_coverage.py | 12KB | 343 | Валидация |
| **ИТОГО** | **183KB** | **6181** | **Полная стратегия** |

### Примеры кода

- **21 готовый пример** pytest тестов
- **Все типы:** Unit, Integration, E2E, Contract, Load, Chaos
- **Все системы:** Event Bus, Onboarding, Analysis, Profile, Coach
- **Копируй и используй**

### План работ

- **9 фаз** рефакторинга
- **31 рабочий день** детального плана
- **12,400 строк** тестов написать
- **45% coverage** нужно добавить (40% → 85%)

---

## NEXT STEPS

### 1. Прочитай summary
```bash
cat TESTING_STRATEGY_SUMMARY.md | less
```

### 2. Установи зависимости
```bash
pip install pytest pytest-asyncio pytest-cov
```

### 3. Создай структуру
```bash
mkdir -p tests/event_bus/unit
```

### 4. Скопируй первый пример
```bash
# Из TESTING_CODE_EXAMPLES.md
# Секция "Event Bus Tests"
# test_event_publisher.py
```

### 5. Запусти
```bash
pytest tests/event_bus/unit/test_event_publisher.py -v
```

### 6. Валидация
```bash
./scripts/validate_test_coverage.py
```

---

## ССЫЛКИ

### Документация
- [TESTING_STRATEGY_SUMMARY.md](TESTING_STRATEGY_SUMMARY.md) - Executive summary
- [TESTING_STRATEGY.md](TESTING_STRATEGY.md) - Полная стратегия
- [TESTING_CODE_EXAMPLES.md](TESTING_CODE_EXAMPLES.md) - Примеры кода
- [TESTING_IMPLEMENTATION_PLAN.md](TESTING_IMPLEMENTATION_PLAN.md) - Пошаговый план
- [TESTING_README.md](TESTING_README.md) - Quick start

### Инструменты
- [scripts/validate_test_coverage.py](scripts/validate_test_coverage.py) - Валидация

### Внешние ресурсы
- [Pytest Documentation](https://docs.pytest.org/)
- [Locust Documentation](https://docs.locust.io/)
- [Factory Boy](https://factoryboy.readthedocs.io/)

---

**Создано:** 2025-09-30
**Проект:** Selfology Microservices Refactoring
**Статус:** ✅ Complete & Ready

**К работе! 🚀**
