# ROADMAP: Переход на блочную структуру программ

## Обзор изменений

**Цель:** Полная переработка системы онбординга с переходом от хаотичного выбора вопросов к структурированным программам с блоками.

**Масштаб:** ~1000-1200 строк нового кода, 5 новых таблиц БД, новый JSON формат.

---

## ФАЗА 0: Подготовка и планирование

### 0.1 Анализ текущей системы ✅
- [x] Исследование всех затронутых компонентов
- [x] Карта зависимостей между модулями
- [x] Список всех метаданных вопросов (17 параметров)
- [x] Схема текущих таблиц БД

### 0.2 Архитектурные решения
- [x] 3-уровневая иерархия: Программа → Блок → Вопрос
- [x] 9 критичных метаданных (убрать 2: insight_potential, batch_compatible)
- [x] Типы блоков: Foundation / Exploration / Integration
- [x] Наследование метаданных: блок → вопросы

### Затронутые компоненты:

| Компонент | Файл | Изменения |
|-----------|------|-----------|
| Question Core | `intelligent_question_core/` | Новый JSON формат |
| QuestionRouter | `services/onboarding/question_router.py` | Блочная логика |
| Orchestrator | `services/onboarding/orchestrator.py` | Управление программами |
| OnboardingDAO | `database/onboarding_dao.py` | Новые таблицы |
| AnswerAnalyzer | `analysis/answer_analyzer.py` | program_context |
| FatigueDetector | `services/onboarding/fatigue_detector.py` | Пороги по блокам |
| EmbeddingCreator | `analysis/embedding_creator.py` | program_id в векторах |

---

## ФАЗА 1: Парсинг и создание новой структуры данных

### 1.1 Парсинг файла методолога
**Входной файл:** `research/Ты методолог по дизайну рефлексивных опросников..md`

**Задачи:**
- [ ] Написать парсер markdown → JSON
- [ ] Извлечь все программы (38 шт)
- [ ] Извлечь блоки внутри программ
- [ ] Извлечь вопросы с позициями
- [ ] Сохранить метки 📖/🤖

**Выходной формат:**
```json
{
  "programs": [
    {
      "id": "program_life_reflection",
      "name": "Подумать о жизни",
      "description": "Глубокие вопросы о смысле...",
      "status": "ready",
      "priority": 0,
      "estimated_duration_min": 30,
      "blocks": [
        {
          "id": "block_1",
          "name": "Здесь и сейчас",
          "type": "Foundation",
          "sequence": 1,
          "block_metadata": {
            "base_journey_stage": "ENTRY",
            "base_depth_range": ["SURFACE", "CONSCIOUS"],
            "base_energy_dynamic": "OPENING",
            "base_safety_minimum": 4
          },
          "questions": [
            {
              "id": "q_life_b1_q1",
              "position": 1,
              "text": "Опиши своё состояние прямо сейчас тремя словами",
              "format": "ai_only"
            }
          ]
        }
      ]
    }
  ]
}
```

### 1.2 Генерация метаданных для вопросов
**Задачи:**
- [ ] Правила по позиции в блоке (complexity, energy_dynamic)
- [ ] AI-генерация для сложных параметров (emotional_weight, safety_level)
- [ ] Наследование от block_metadata
- [ ] Вычисление domain из текста (embedding)
- [ ] Флаг needs_human_review для confidence < 0.75

### 1.3 Создание нового Question Core
**Выходной файл:** `intelligent_question_core/data/selfology_programs_v2.json`

**Структура:**
```json
{
  "version": "2.0",
  "generated_at": "2024-11-29T12:00:00Z",
  "metadata": {
    "total_programs": 38,
    "total_blocks": 200,
    "total_questions": 500
  },
  "programs": [...],
  "indexes": {
    "by_program": {},
    "by_block": {},
    "by_domain": {},
    "by_depth": {}
  }
}
```

---

## ФАЗА 2: Миграция базы данных

### 2.1 Новые таблицы

```sql
-- Программы
CREATE TABLE selfology.onboarding_programs (
  id SERIAL PRIMARY KEY,
  program_id VARCHAR(50) UNIQUE NOT NULL,
  name VARCHAR(100) NOT NULL,
  description TEXT,
  status VARCHAR(20) DEFAULT 'active',
  priority INTEGER DEFAULT 0,
  estimated_duration_min INTEGER,
  therapeutic_approach TEXT[],
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- Блоки программ
CREATE TABLE selfology.program_blocks (
  id SERIAL PRIMARY KEY,
  block_id VARCHAR(50) UNIQUE NOT NULL,
  program_id VARCHAR(50) REFERENCES selfology.onboarding_programs(program_id),
  name VARCHAR(100) NOT NULL,
  block_type VARCHAR(20) NOT NULL, -- Foundation, Exploration, Integration
  sequence INTEGER NOT NULL,
  base_journey_stage VARCHAR(20),
  base_depth_range VARCHAR(50),
  base_energy_dynamic VARCHAR(20),
  base_safety_minimum INTEGER,
  estimated_duration_min INTEGER,
  created_at TIMESTAMP DEFAULT NOW()
);

-- Вопросы программ (связь с JSON)
CREATE TABLE selfology.program_questions (
  id SERIAL PRIMARY KEY,
  question_id VARCHAR(50) UNIQUE NOT NULL,
  block_id VARCHAR(50) REFERENCES selfology.program_blocks(block_id),
  program_id VARCHAR(50) REFERENCES selfology.onboarding_programs(program_id),
  position INTEGER NOT NULL,
  text TEXT NOT NULL,
  format VARCHAR(20), -- book_only, ai_only, both
  -- Метаданные (финальные после наследования)
  journey_stage VARCHAR(20),
  depth_level VARCHAR(20),
  domain VARCHAR(30),
  energy_dynamic VARCHAR(20),
  complexity INTEGER,
  emotional_weight INTEGER,
  safety_level INTEGER,
  trust_requirement INTEGER,
  recommended_model VARCHAR(30),
  requires_context BOOLEAN,
  -- Валидация
  confidence_score FLOAT,
  needs_human_review BOOLEAN DEFAULT false,
  reviewed_by VARCHAR(50),
  reviewed_at TIMESTAMP,
  created_at TIMESTAMP DEFAULT NOW()
);

-- Прогресс пользователя по программам
CREATE TABLE selfology.user_program_progress (
  id SERIAL PRIMARY KEY,
  user_id INTEGER NOT NULL,
  program_id VARCHAR(50) REFERENCES selfology.onboarding_programs(program_id),
  session_id INTEGER REFERENCES selfology.onboarding_sessions(id),
  current_block_id VARCHAR(50),
  blocks_completed VARCHAR(50)[],
  blocks_skipped VARCHAR(50)[],
  questions_answered INTEGER DEFAULT 0,
  completion_percentage INTEGER DEFAULT 0,
  status VARCHAR(20) DEFAULT 'active', -- active, completed, paused, abandoned
  started_at TIMESTAMP DEFAULT NOW(),
  completed_at TIMESTAMP,
  updated_at TIMESTAMP DEFAULT NOW()
);

-- Индексы
CREATE INDEX idx_blocks_program ON selfology.program_blocks(program_id);
CREATE INDEX idx_questions_block ON selfology.program_questions(block_id);
CREATE INDEX idx_questions_program ON selfology.program_questions(program_id);
CREATE INDEX idx_progress_user ON selfology.user_program_progress(user_id);
CREATE INDEX idx_progress_session ON selfology.user_program_progress(session_id);
```

### 2.2 Обновление существующих таблиц

```sql
-- Добавить в onboarding_sessions
ALTER TABLE selfology.onboarding_sessions
ADD COLUMN current_program_id VARCHAR(50),
ADD COLUMN current_block_id VARCHAR(50),
ADD COLUMN program_progress_id INTEGER;

-- Добавить в questions_metadata (если используется)
ALTER TABLE selfology.questions_metadata
ADD COLUMN program_id VARCHAR(50),
ADD COLUMN block_id VARCHAR(50),
ADD COLUMN position_in_block INTEGER;
```

### 2.3 Скрипт миграции
- [ ] Создать `scripts/migrations/001_programs_structure.sql`
- [ ] Тестовый запуск на копии БД
- [ ] Rollback скрипт

---

## ФАЗА 3: Генератор метаданных

### 3.1 Правила по позиции
**Файл:** `intelligent_question_core/metadata_generator.py`

```python
POSITION_RULES = {
    "Foundation": {
        1: {"complexity": 1, "emotional_weight": 1, "energy_dynamic": "OPENING"},
        2: {"complexity": 2, "emotional_weight": 1, "energy_dynamic": "OPENING"},
        3: {"complexity": 2, "emotional_weight": 2, "energy_dynamic": "NEUTRAL"},
    },
    "Exploration": {
        1: {"complexity": 2, "emotional_weight": 2, "energy_dynamic": "NEUTRAL"},
        2: {"complexity": 3, "emotional_weight": 3, "energy_dynamic": "PROCESSING"},
        3: {"complexity": 3, "emotional_weight": 3, "energy_dynamic": "PROCESSING"},
        4: {"complexity": 4, "emotional_weight": 4, "energy_dynamic": "HEAVY"},
        5: {"complexity": 4, "emotional_weight": 4, "energy_dynamic": "HEAVY"},
        6: {"complexity": 3, "emotional_weight": 3, "energy_dynamic": "HEALING"},
    },
    "Integration": {
        1: {"complexity": 4, "emotional_weight": 3, "energy_dynamic": "PROCESSING"},
        2: {"complexity": 4, "emotional_weight": 3, "energy_dynamic": "HEALING"},
        3: {"complexity": 3, "emotional_weight": 2, "energy_dynamic": "HEALING"},
    }
}
```

### 3.2 AI-генерация для сложных параметров
**Промпт для Claude:**
- Анализ emotional_weight по тексту
- Определение safety_level
- Извлечение domain
- Confidence score

### 3.3 Финальный pipeline
```
1. Загрузить вопрос + блок
2. Применить правила позиции → базовые метаданные
3. Наследовать от block_metadata
4. Если confidence < 0.75 → AI анализ
5. Вычислить domain (embedding)
6. Пометить needs_human_review если нужно
7. Сохранить final_metadata
```

---

## ФАЗА 4: Переработка Question Router

### 4.1 Новая логика выбора
**Файл:** `selfology_bot/services/onboarding/question_router.py`

**Изменения:**
- [ ] Добавить `ProgramContext` dataclass
- [ ] Новый метод `select_question_from_block()`
- [ ] Проверка `can_proceed_to_next_block()`
- [ ] Валидация последовательности Foundation → Exploration → Integration
- [ ] Fallback на старую логику для legacy сессий

### 4.2 Новые методы

```python
class QuestionRouter:
    async def select_first_question_in_program(
        self, user_id: int, program_id: str
    ) -> Optional[Dict]:
        """Первый вопрос первого блока программы"""

    async def select_next_question_in_block(
        self, user_id: int, program_context: ProgramContext
    ) -> Optional[Dict]:
        """Следующий вопрос в текущем блоке"""

    async def can_proceed_to_next_block(
        self, user_id: int, program_context: ProgramContext
    ) -> bool:
        """Можно ли перейти к следующему блоку"""

    async def get_next_block(
        self, program_context: ProgramContext
    ) -> Optional[Dict]:
        """Получить следующий блок (с учетом типа)"""
```

### 4.3 Интеграция со старой логикой
- Smart Mix работает ВНУТРИ блока
- Между блоками — строгая последовательность
- Foundation обязателен перед Exploration

---

## ФАЗА 5: Обновление Orchestrator

### 5.1 Управление программами
**Файл:** `selfology_bot/services/onboarding/orchestrator.py`

**Новые методы:**
```python
async def start_program(self, user_id: int, program_id: str) -> Dict:
    """Начать новую программу"""

async def get_program_progress(self, user_id: int, program_id: str) -> Dict:
    """Прогресс по программе"""

async def complete_block(self, user_id: int, block_id: str) -> Dict:
    """Завершить блок, перейти к следующему"""

async def pause_program(self, user_id: int) -> Dict:
    """Приостановить программу"""

async def resume_program(self, user_id: int) -> Dict:
    """Продолжить программу"""
```

### 5.2 Изменения в process_user_answer
- Обновлять `program_progress`
- Проверять завершение блока
- Триггерить переход к следующему блоку

### 5.3 Изменения в get_next_question
- Учитывать `current_block_id`
- Проверять `blocks_completed`
- Вызывать `question_router.select_next_question_in_block()`

---

## ФАЗА 6: Экспорт в книгу/PDF

### 6.1 Скрипт экспорта
**Файл:** `scripts/export_programs_book.py`

**Форматы:**
- Markdown (для ревью)
- HTML (для веб)
- PDF (для печати)

**Структура книги:**
```
# Selfology: Книга рефлексии

## Программа 1: Подумать о жизни

### Часть 1: Здесь и сейчас

1. Опиши своё состояние прямо сейчас тремя словами
   _______________________________________________

2. Как обычно выглядит твоё утро?
   _______________________________________________
   _______________________________________________

### Часть 2: Люди рядом
...
```

### 6.2 Опции экспорта
- [ ] Только 📖 вопросы (для книги)
- [ ] Только 🤖 вопросы (для AI)
- [ ] Все вопросы (полный формат)
- [ ] С метаданными (для разработки)
- [ ] Без метаданных (для пользователей)

---

## ФАЗА 7: Тестирование и валидация

### 7.1 Unit тесты
- [ ] Парсер markdown → JSON
- [ ] Генератор метаданных
- [ ] Question Router (блочная логика)
- [ ] Orchestrator (управление программами)

### 7.2 Integration тесты
- [ ] Полный цикл: start_program → questions → complete
- [ ] Переход между блоками
- [ ] Сохранение/восстановление прогресса
- [ ] Миграция старых сессий

### 7.3 Валидация психологом
- [ ] Проверка emotional_weight для sensitivity > 3
- [ ] Проверка safety_level для trauma вопросов
- [ ] Проверка последовательности в блоках
- [ ] Approval всех 38 программ

### 7.4 A/B тестирование
- [ ] Сравнение: блочная vs random логика
- [ ] Метрики: completion rate, engagement, insights

---

## КРИТИЧЕСКИЕ ЗАВИСИМОСТИ

```
ФАЗА 1 (Парсинг)
    ↓
ФАЗА 2 (БД) ←─────────────────┐
    ↓                         │
ФАЗА 3 (Метаданные) ──────────┤
    ↓                         │
ФАЗА 4 (Router) ──────────────┤
    ↓                         │
ФАЗА 5 (Orchestrator) ────────┘
    ↓
ФАЗА 6 (Экспорт) [параллельно с 4-5]
    ↓
ФАЗА 7 (Тесты) [после всего]
```

---

## ОЦЕНКА ВРЕМЕНИ

| Фаза | Задачи | Оценка |
|------|--------|--------|
| 0 | Подготовка | ✅ Готово |
| 1 | Парсинг + структура | 2-3 часа |
| 2 | Миграция БД | 1-2 часа |
| 3 | Генератор метаданных | 2-3 часа |
| 4 | Question Router | 3-4 часа |
| 5 | Orchestrator | 2-3 часа |
| 6 | Экспорт книги | 1-2 часа |
| 7 | Тестирование | 2-3 часа |
| **Итого** | | **13-20 часов** |

---

## ROLLBACK ПЛАН

В случае проблем:
1. Восстановить из `backup/pre-programs-refactor-2024-11-29`
2. Откатить миграции БД
3. Вернуть старый Question Core JSON

---

## МОНИТОРИНГ ПОСЛЕ ДЕПЛОЯ

- [ ] Логи ошибок в Router
- [ ] Completion rate по программам
- [ ] Время на блок vs старая система
- [ ] Фидбек пользователей
