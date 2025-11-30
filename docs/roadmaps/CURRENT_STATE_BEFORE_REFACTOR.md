# Текущее состояние Selfology (до рефакторинга)

**Дата:** 2024-11-30
**Backup branch:** `backup/pre-major-refactor-2024-11-30`

## Статистика "помойки"

```
Python файлов:     330
Строк кода:        117,162
Top-level папок:   27 (!)
```

## Самые большие файлы (проблемные монолиты)

| Файл | Строк | Проблема |
|------|-------|----------|
| `selfology_controller.py` | 2,403 | Главный монолит, всё в одном |
| `orchestrator.py` | 1,735 | Онбординг, слишком большой |
| `chat_coach.py` | 1,327 | Старый Phase 2-3 коуч |
| `embedding_creator.py` | 1,128 | Создание векторов |
| `onboarding_dao.py` | 1,116 | Data access, можно разбить |

## Структура (хаос)

### 27 top-level папок:
```
АКТИВНЫЕ (используются):
├── selfology_bot/        # Основной код бота
├── services/             # Дублирует selfology_bot/services (!)
├── intelligent_question_core/  # Вопросы и программы
├── scripts/              # Утилиты
├── tests/                # Тесты (хаотично)
├── telegram_interface/   # Telegram handlers
└── data_access/          # DAO (дублирует selfology_bot/database)

МУСОР / АРХИВ:
├── archive/              # Deprecated боты (5+ версий)
├── backups/              # Старые бэкапы внутри репо (!)
├── examples/             # Примеры (не нужны)
├── review/               # Что-то для review
├── coach/                # Пустая/старая
├── core/                 # Дублирует selfology_bot/core
├── systems/              # Непонятно что
└── src/                  # Старый FastAPI (не используется?)

ИНФРАСТРУКТУРА:
├── alembic/              # Миграции
├── migrations/           # Ещё миграции (дубль?)
├── deployment/           # Docker и т.д.
├── logs/                 # Логи (не должны быть в git)
├── venv/                 # Virtual env (в .gitignore?)
├── static/               # Статика
├── prompts/              # Промпты для AI
├── research/             # Исследования
├── docs/                 # Документация
├── data/                 # Данные
└── exports/              # Экспорты
```

## selfology_bot/ внутренняя структура

```
selfology_bot/
├── ai/                   # AI роутер (работает)
├── analysis/             # Анализ ответов (работает)
├── bot/                  # Telegram handlers (старые?)
├── coach/                # Phase 2-3 компоненты
├── core/                 # Config, logging
├── database/             # DAO слой (используется)
├── db/                   # Ещё database (дубль!)
├── messages/             # Шаблоны сообщений
├── models/               # SQLAlchemy модели
├── monitoring/           # Мониторинг
├── services/             # Бизнес-логика
│   ├── onboarding/       # Онбординг v2 (используется)
│   └── chat/             # MVP чат (новый, не интегрирован)
└── soul_architect/       # Что-то старое?
```

## Что РАБОТАЕТ сейчас

### 1. Telegram бот
- **Entry point:** `selfology_controller.py`
- **Запуск:** `./run-local.sh`
- Обрабатывает: /start, /onboarding, сообщения

### 2. Онбординг v2
- `selfology_bot/services/onboarding/orchestrator_v2.py`
- `cluster_router.py` - загружает программы из JSON
- Работает: выбор программы → вопросы → анализ ответов

### 3. Digital Personality
- БД таблица: `selfology.digital_personality`
- 10 JSONB слоёв: identity, goals, barriers, values...
- Данные: 72 цели, 62 барьера, 47 интересов

### 4. Qdrant векторы
- Коллекции: personality_profiles, user_answers
- Работает embedding через OpenAI

## Что НЕ РАБОТАЕТ / НЕ ИНТЕГРИРОВАНО

### 1. Chat MVP (новый)
- `selfology_bot/services/chat/` - создан, но не подключён к боту
- UserDossierService, DossierValidator - готовы, не используются

### 2. Phase 2-3 Coach
- `services/chat_coach.py` - 1327 строк, частично работает
- Дублирует функционал chat MVP

### 3. FastAPI
- `src/main.py` - есть, но бот работает через polling
- Webhooks не настроены

## Дублирование кода (главная проблема)

| Оригинал | Дубль | Описание |
|----------|-------|----------|
| `selfology_bot/services/` | `services/` | Бизнес-логика |
| `selfology_bot/database/` | `data_access/` | DAO |
| `selfology_bot/core/` | `core/` | Конфиги |
| `selfology_bot/db/` | `selfology_bot/database/` | Внутри selfology_bot |
| `alembic/` | `migrations/` | Миграции |

## База данных

### Схема: `selfology`
```sql
-- Основные таблицы (используются):
digital_personality      -- 10 JSONB слоёв личности
personality_profile      -- Big Five traits
user_answers_v2          -- Ответы на вопросы
onboarding_sessions      -- Сессии онбординга

-- Старые/неиспользуемые:
users                    -- Старая таблица?
answer_analysis          -- Пустая
cognitive_distortions    -- Пустая
```

## Что нужно сделать при рефакторинге

### 1. УДАЛИТЬ
- [ ] `archive/` - 5 deprecated ботов
- [ ] `backups/` - не нужно в git
- [ ] `examples/` - не нужно
- [ ] Дубли папок (core/, services/, data_access/)
- [ ] `logs/` из git

### 2. ОБЪЕДИНИТЬ
- [ ] `services/chat_coach.py` + `selfology_bot/services/chat/` → один модуль
- [ ] `data_access/` + `selfology_bot/database/` → один DAO слой
- [ ] Все миграции в одно место

### 3. РАЗБИТЬ МОНОЛИТЫ
- [ ] `selfology_controller.py` (2403 строк) → отдельные модули
- [ ] `orchestrator.py` (1735 строк) → меньшие классы

### 4. СТРУКТУРИРОВАТЬ
```
selfology/
├── bot/                  # Telegram interface
├── core/                 # Config, logging, database
├── services/             # Business logic
│   ├── onboarding/       # Онбординг
│   ├── coach/            # AI коуч
│   └── personality/      # Работа с личностью
├── data/                 # Questions, programs (JSON)
├── migrations/           # Alembic
└── tests/                # Pytest
```

## Команды для проверки

```bash
# Запуск бота
./run-local.sh

# Тесты MVP чата
python tests/test_chat_mvp.py

# Проверка импортов
python -c "from selfology_bot.services.chat import ChatMVP; print('OK')"
```

---

**Вывод:** Проект вырос хаотично, много legacy кода. Нужен серьёзный рефакторинг для дальнейшего развития.
