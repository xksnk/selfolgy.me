# План рефакторинга Selfology

## Философия
- Максимум 600 строк на файл
- Только работающий код в основной ветке
- Всё остальное - в "зазеркалье" (archive)
- Git хранит историю - можно восстановить любой файл

---

## ФАЗА 1: Зазеркалье (архивация мусора)

### Стратегия
```
НЕ удаляем, а ПЕРЕМЕЩАЕМ в _archive/
Git сохраняет историю - можно достать через:
  git show HEAD~1:path/to/file.py
```

### Что перемещаем в _archive/

#### 1.1 Явный мусор
```
archive/           → _archive/old_bots/
backups/           → _archive/old_backups/
examples/          → _archive/examples/
```

#### 1.2 Неиспользуемые системы
```
src/               → _archive/old_fastapi/     # Старая FastAPI архитектура
systems/           → _archive/old_systems/     # Альтернативная абстракция
```

#### 1.3 Root-файлы (скрипты)
```
*.py (кроме selfology_controller.py) → scripts/debug/ или scripts/legacy/
```

#### 1.4 Дублирующиеся папки
```
core/              → оставить selfology_bot/core/
coach/             → объединить с selfology_bot/coach/
```

### Что ОСТАВЛЯЕМ
```
selfology_controller.py    # Entry point
selfology_bot/             # Основной код
services/                  # Пока оставить (используется)
data_access/               # Пока оставить (используется)
intelligent_question_core/ # Вопросы и программы
scripts/                   # Утилиты (почистить)
tests/                     # Тесты (структурировать)
docs/                      # Документация
alembic/                   # Миграции
templates/                 # Шаблоны сообщений
prompts/                   # AI промпты
```

---

## ФАЗА 2: Чистка MD файлов

### 2.1 Структура документации
```
docs/
├── architecture/          # Архитектура системы
│   ├── OVERVIEW.md       # Общий обзор
│   ├── CHAT_COACH.md     # Архитектура чата
│   └── DATABASE.md       # Схема БД
├── guides/                # Руководства
│   ├── SETUP.md          # Установка
│   ├── DEVELOPMENT.md    # Разработка
│   └── DEPLOYMENT.md     # Деплой
├── research/              # Исследования (переместить из research/)
│   └── ...
├── roadmaps/              # Планы развития
│   └── ...
└── INDEX.md               # Индекс всех файлов с описаниями
```

### 2.2 Создать INDEX.md
```markdown
# Индекс документации

## Архитектура
- [OVERVIEW.md](architecture/OVERVIEW.md) - Общая архитектура системы
- [CHAT_COACH.md](architecture/CHAT_COACH.md) - AI коуч с досье
...

## Исследования
- [AI_COACH_RESEARCH.md](research/...) - Исследование архитектур AI-коучей
...
```

### 2.3 Правила для MD файлов
- Удалить временные/черновики
- Переименовать на английском (транслит)
- Один файл = одна тема
- Добавить даты создания/обновления

---

## ФАЗА 3: Рефакторинг кода

### 3.1 Правило 600 строк
Файлы > 600 строк разбить:

| Файл | Строк | План разбиения |
|------|-------|----------------|
| `selfology_controller.py` | 2,403 | → bot/, handlers/, states/ |
| `orchestrator.py` | 1,735 | → orchestrator/, question_flow/, analysis_flow/ |
| `chat_coach.py` | 1,327 | → coach/response/, coach/context/, coach/style/ |
| `embedding_creator.py` | 1,128 | → embeddings/creator, embeddings/storage |
| `onboarding_dao.py` | 1,116 | → dao/sessions, dao/answers, dao/personality |

### 3.2 Целевая структура
```
selfology/
├── bot/                      # Telegram бот
│   ├── __init__.py
│   ├── app.py               # Инициализация aiogram
│   ├── handlers/            # Обработчики команд
│   │   ├── start.py
│   │   ├── onboarding.py
│   │   └── chat.py
│   ├── states/              # FSM состояния
│   └── middlewares/         # Middleware
│
├── core/                     # Ядро
│   ├── config.py            # Конфигурация
│   ├── database.py          # Подключение к БД
│   ├── redis.py             # Redis клиент
│   └── logging.py           # Логирование
│
├── services/                 # Бизнес-логика
│   ├── onboarding/          # Онбординг
│   │   ├── orchestrator.py  # < 600 строк
│   │   ├── question_router.py
│   │   └── analysis.py
│   ├── coach/               # AI коуч
│   │   ├── chat.py
│   │   ├── dossier.py
│   │   └── validator.py
│   └── personality/         # Работа с личностью
│       ├── extractor.py
│       └── embeddings.py
│
├── data/                     # Данные
│   ├── questions/           # JSON с вопросами
│   └── programs/            # Программы
│
├── dao/                      # Data Access Objects
│   ├── user.py
│   ├── session.py
│   ├── answer.py
│   └── personality.py
│
├── migrations/               # Alembic
├── tests/                    # Pytest
└── scripts/                  # Утилиты
```

---

## ФАЗА 4: Что ещё нужно учесть

### 4.1 База данных
- [ ] Удалить неиспользуемые таблицы
- [ ] Проверить индексы
- [ ] Документировать схему

### 4.2 Зависимости
- [ ] Почистить requirements.txt от неиспользуемых пакетов
- [ ] Разделить на prod/dev зависимости

### 4.3 Конфигурация
- [ ] Объединить все .env переменные в один файл
- [ ] Удалить дублирующиеся конфиги

### 4.4 Тесты
- [ ] Структурировать по модулям
- [ ] Добавить pytest.ini
- [ ] Настроить coverage

### 4.5 Git
- [ ] Обновить .gitignore (logs/, __pycache__/, .env)
- [ ] Добавить pre-commit hooks (black, ruff)

### 4.6 Docker
- [ ] Обновить Dockerfile
- [ ] Проверить docker-compose

### 4.7 CI/CD
- [ ] GitHub Actions для тестов
- [ ] Автодеплой

---

## Порядок выполнения

### День 1: Зазеркалье
1. [ ] Создать _archive/ структуру
2. [ ] Переместить archive/, backups/, examples/
3. [ ] Переместить src/, systems/
4. [ ] Переместить root *.py в scripts/
5. [ ] Коммит: "refactor: move unused code to _archive"

### День 2: Документация
1. [ ] Создать структуру docs/
2. [ ] Переместить и переименовать MD файлы
3. [ ] Создать INDEX.md
4. [ ] Удалить дубли и мусор
5. [ ] Коммит: "docs: reorganize documentation"

### День 3-5: Рефакторинг кода
1. [ ] Разбить selfology_controller.py
2. [ ] Разбить orchestrator.py
3. [ ] Объединить дублирующиеся модули
4. [ ] Проверить что всё работает
5. [ ] Коммиты по модулям

### День 6: Финализация
1. [ ] Почистить requirements.txt
2. [ ] Обновить .gitignore
3. [ ] Обновить CLAUDE.md
4. [ ] Финальное тестирование

---

## Команды для восстановления из Git

Если понадобится файл из архива:
```bash
# Посмотреть историю файла
git log --follow -- path/to/old/file.py

# Восстановить файл из конкретного коммита
git show COMMIT_HASH:path/to/old/file.py > restored_file.py

# Восстановить из предыдущего коммита
git checkout HEAD~1 -- path/to/file.py
```

---

## Критерии успеха

- [ ] Ни один файл > 600 строк
- [ ] Нет дублирующихся папок
- [ ] Все MD файлы каталогизированы
- [ ] INDEX.md со всеми ссылками
- [ ] Бот запускается и работает
- [ ] Тесты проходят
- [ ] .gitignore актуален

---

**Backup branch:** `backup/pre-major-refactor-2024-11-30`
**Дата создания плана:** 2024-11-30
