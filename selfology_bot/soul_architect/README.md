# Soul Architect - Многослойная система моделирования личности

**Версия:** 1.0.0
**Статус:** Production Ready
**Архитектура:** Изолированная модульная система

---

## Обзор

**Soul Architect** - это изолированная система для создания и управления многослойными психологическими профилями пользователей. Система построена на принципах чистой архитектуры и полностью изолирована от других компонентов Selfology.

### Ключевые возможности

- **5-слойная модель личности**: Big Five, Core Dynamics, Adaptive Traits, Domain Affinities, Unique Signature
- **Гибридная scoring система**: Confidence, variance, percentile, направление изменений
- **Отслеживание эволюции**: История изменений черт во времени
- **Простой API**: 5 основных методов для работы с профилями
- **Полная изоляция**: Минимальные зависимости, легко тестировать

---

## Архитектура

### Структура модуля

```
soul_architect/
├── __init__.py              # Публичный API
├── models.py                # Pydantic модели для всех слоев
├── config.py                # Конфигурация системы
├── service.py               # SoulArchitectService - главный API
├── trait_scorer.py          # Scoring система для черт
├── profile_builder.py       # Построение профилей
├── evolution_tracker.py     # Отслеживание изменений
├── README.md                # Документация
└── tests/
    ├── __init__.py
    ├── test_models.py
    └── test_scorer.py
```

### Многослойная модель личности

```python
PersonalityProfile = {
    # ФУНДАМЕНТ - Big Five (медленно меняется)
    "big_five": {
        "openness": TraitAssessment,
        "conscientiousness": TraitAssessment,
        "extraversion": TraitAssessment,
        "agreeableness": TraitAssessment,
        "neuroticism": TraitAssessment
    },

    # ДИНАМИЧЕСКОЕ ЯДРО (медленно меняется)
    "core_dynamics": {
        "resilience": TraitAssessment,
        "authenticity": TraitAssessment,
        "growth_mindset": TraitAssessment,
        "emotional_granularity": TraitAssessment,
        "cognitive_flexibility": TraitAssessment,
        "self_compassion": TraitAssessment,
        "meaning_making": TraitAssessment
    },

    # АДАПТИВНЫЕ ЧЕРТЫ (быстро меняется)
    "adaptive_traits": {
        "current_energy": TraitAssessment,
        "stress_level": TraitAssessment,
        "openness_state": TraitAssessment,
        "creative_flow": TraitAssessment,
        "social_battery": TraitAssessment
    },

    # ДОМЕННЫЕ ПРОФИЛИ (важность доменов)
    "domain_affinities": {
        "IDENTITY": TraitAssessment,
        "RELATIONSHIPS": TraitAssessment,
        "CAREER": TraitAssessment,
        # ... 13 доменов всего
    },

    # УНИКАЛЬНАЯ ПОДПИСЬ
    "unique_signature": {
        "thinking_style": str,
        "decision_pattern": str,
        "energy_rhythm": str,
        "learning_edge": str,
        "love_language": str,
        "stress_response": str
    }
}
```

### Гибридная scoring система

```python
TraitAssessment = {
    "value": 0.75,              # Основное значение (0-1)
    "confidence": 0.92,         # Уверенность в оценке
    "variance": 0.08,           # Разброс между ответами
    "samples": 5,               # Количество ответов
    "last_updated": datetime,

    # Контекстные модификаторы
    "percentile": 82,           # Позиция среди всех
    "direction": "increasing",  # Тренд изменения
    "interpretation": "high",   # low/medium/high/very_high

    # Для UI
    "display_formats": {
        "percentage": "75%",
        "stars": 4,
        "label": "Развитая",
        "color": "#4CAF50"
    }
}
```

---

## Быстрый старт

### 1. Инициализация

```python
from selfology_bot.database.service import DatabaseService
from selfology_bot.soul_architect import SoulArchitectService

# Создаем database service
db = DatabaseService(
    host="localhost",
    port=5432,
    user="postgres",
    password="your_password",
    database="n8n",
    schema="selfology"
)
await db.initialize()

# Создаем Soul Architect service
soul = SoulArchitectService(db)
await soul.initialize()
```

### 2. Создание профиля

```python
# Создать новый профиль
profile = await soul.create_profile(user_id=123456)

print(f"Profile created!")
print(f"Completeness: {profile.completeness}")
print(f"Total samples: {profile.total_samples}")
```

### 3. Обновление черты

```python
# Обновить одну черту
profile = await soul.update_trait(
    user_id=123456,
    category="big_five",
    trait_name="openness",
    value=0.75,
    confidence=0.85,
    trigger="answer_to_question_42"
)

print(f"Openness updated to {profile.big_five.openness.value}")
```

### 4. Пакетное обновление

```python
# Обновить несколько черт за раз
updates = [
    {
        "category": "big_five",
        "trait_name": "openness",
        "value": 0.75,
        "confidence": 0.85
    },
    {
        "category": "adaptive_traits",
        "trait_name": "stress_level",
        "value": 0.6,
        "confidence": 0.9
    }
]

profile = await soul.batch_update_traits(
    user_id=123456,
    updates=updates
)
```

### 5. Получение профиля

```python
# Получить профиль
profile = await soul.get_profile(user_id=123456)

# Доступ к чертам
openness = profile.big_five.openness
print(f"Openness: {openness.value} (confidence: {openness.confidence})")
print(f"Interpretation: {openness.interpretation}")
print(f"Percentile: {openness.percentile}")
```

### 6. Анализ эволюции

```python
# Получить сводку эволюции за 30 дней
evolution = await soul.get_evolution(user_id=123456, days=30)

print(f"Total updates: {evolution.total_updates}")
print(f"Significant changes: {evolution.significant_changes}")
print(f"Most changed traits: {evolution.most_changed_traits}")

# Получить историю конкретной черты
history = await soul.get_trait_history(
    user_id=123456,
    category="adaptive_traits",
    trait_name="stress_level",
    days=7
)

for record in history:
    print(f"{record.timestamp}: {record.old_value} -> {record.new_value}")
```

---

## API Reference

### SoulArchitectService

Главный сервис для работы с профилями.

#### Методы

##### `initialize() -> bool`
Инициализация сервиса. Проверяет наличие таблиц в БД.

##### `create_profile(user_id: int) -> PersonalityProfile`
Создать новый профиль личности.

**Параметры:**
- `user_id` (int): ID пользователя

**Возвращает:** PersonalityProfile

**Raises:** Exception если профиль уже существует

##### `get_profile(user_id: int, raise_if_not_found: bool = True) -> Optional[PersonalityProfile]`
Получить профиль личности.

**Параметры:**
- `user_id` (int): ID пользователя
- `raise_if_not_found` (bool): Выбросить ошибку если не найден

**Возвращает:** PersonalityProfile или None

##### `update_trait(user_id: int, category: str, trait_name: str, value: float, confidence: float, trigger: Optional[str] = None) -> PersonalityProfile`
Обновить значение черты.

**Параметры:**
- `user_id` (int): ID пользователя
- `category` (str): Категория (big_five, core_dynamics, adaptive_traits, domain_affinities)
- `trait_name` (str): Имя черты
- `value` (float): Новое значение (0.0 - 1.0)
- `confidence` (float): Уверенность в значении
- `trigger` (Optional[str]): Что вызвало обновление

**Возвращает:** Обновленный PersonalityProfile

##### `batch_update_traits(user_id: int, updates: List[Dict]) -> PersonalityProfile`
Обновить несколько черт за раз.

**Параметры:**
- `user_id` (int): ID пользователя
- `updates` (List[Dict]): Список обновлений

**Возвращает:** Обновленный профиль

##### `get_evolution(user_id: int, days: int = 30) -> EvolutionSummary`
Получить сводку эволюции личности.

**Параметры:**
- `user_id` (int): ID пользователя
- `days` (int): Период для анализа (дней)

**Возвращает:** EvolutionSummary

##### `get_trait_history(user_id: int, category: str, trait_name: str, days: Optional[int] = None) -> List[TraitHistory]`
Получить историю изменений конкретной черты.

**Параметры:**
- `user_id` (int): ID пользователя
- `category` (str): Категория черты
- `trait_name` (str): Имя черты
- `days` (Optional[int]): Период (если None - вся история)

**Возвращает:** Список TraitHistory

---

## База данных

### Таблицы

#### `selfology.personality_profiles`
Хранение многослойных профилей личности.

```sql
CREATE TABLE selfology.personality_profiles (
    id SERIAL PRIMARY KEY,
    user_id BIGINT UNIQUE NOT NULL,
    profile_data JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

#### `selfology.trait_history`
История изменений психологических черт.

```sql
CREATE TABLE selfology.trait_history (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    trait_category VARCHAR(50) NOT NULL,
    trait_name VARCHAR(50) NOT NULL,
    old_value FLOAT,
    new_value FLOAT NOT NULL,
    confidence FLOAT NOT NULL,
    trigger VARCHAR(100),
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

#### `selfology.unique_signatures`
Уникальные подписи личности.

```sql
CREATE TABLE selfology.unique_signatures (
    id SERIAL PRIMARY KEY,
    user_id BIGINT UNIQUE NOT NULL,
    thinking_style VARCHAR(100),
    decision_pattern VARCHAR(100),
    energy_rhythm VARCHAR(100),
    learning_edge VARCHAR(100),
    love_language VARCHAR(100),
    stress_response VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### Миграция

```bash
# Применить миграцию
cd /home/ksnk/n8n-enterprise/projects/selfology
alembic upgrade head

# Откатить миграцию
alembic downgrade -1
```

---

## Тестирование

```bash
# Запустить тесты
cd /home/ksnk/n8n-enterprise/projects/selfology
pytest selfology_bot/soul_architect/tests/ -v

# Запустить конкретный тест
pytest selfology_bot/soul_architect/tests/test_scorer.py -v

# С покрытием
pytest selfology_bot/soul_architect/tests/ --cov=selfology_bot/soul_architect
```

---

## Конфигурация

Все настройки в `config.py`:

```python
from selfology_bot.soul_architect.config import config

# Scoring настройки
config.scoring.MIN_CONFIDENCE_THRESHOLD  # 0.5
config.scoring.SIGNIFICANT_CHANGE_THRESHOLD  # 0.2

# Профиль настройки
config.profile.DEFAULT_TRAIT_VALUE  # 0.5
config.profile.MIN_COMPLETENESS_FOR_INSIGHTS  # 0.3

# База данных
config.database.SCHEMA  # "selfology"
config.database.PERSONALITY_PROFILES_TABLE  # "personality_profiles"

# Эволюция
config.evolution.SHORT_PERIOD_DAYS  # 7
config.evolution.MEDIUM_PERIOD_DAYS  # 30
config.evolution.LONG_PERIOD_DAYS  # 90
```

---

## Примеры использования

### Пример 1: Полный цикл работы

```python
# Инициализация
db = DatabaseService(...)
await db.initialize()

soul = SoulArchitectService(db)
await soul.initialize()

# Создание профиля
profile = await soul.create_profile(user_id=123456)

# Обновление черт по мере ответов пользователя
for answer in user_answers:
    trait_category, trait_name, value = analyze_answer(answer)

    profile = await soul.update_trait(
        user_id=123456,
        category=trait_category,
        trait_name=trait_name,
        value=value,
        confidence=0.8,
        trigger=f"answer_{answer.id}"
    )

# Получение инсайтов
if profile.completeness > 0.3:
    evolution = await soul.get_evolution(user_id=123456, days=30)

    if evolution.significant_changes > 0:
        print(f"Значимые изменения: {evolution.most_changed_traits}")
```

### Пример 2: Анализ трендов

```python
# Получить историю черты
history = await soul.get_trait_history(
    user_id=123456,
    category="adaptive_traits",
    trait_name="stress_level",
    days=30
)

# Анализ тренда
from soul_architect.evolution_tracker import EvolutionTracker

tracker = EvolutionTracker()
trend = tracker.analyze_trait_trend(history, period_days=30)

print(f"Direction: {trend['direction']}")
print(f"Magnitude: {trend['magnitude']}")
print(f"Velocity: {trend['velocity']} per day")
```

### Пример 3: Построение профиля из данных

```python
from soul_architect.profile_builder import ProfileBuilder

builder = ProfileBuilder()

# Создать профиль из словаря
trait_data = {
    "big_five": {
        "openness": 0.75,
        "extraversion": 0.6
    },
    "core_dynamics": {
        "resilience": 0.8
    }
}

profile = builder.build_from_trait_dict(
    user_id=123456,
    trait_data=trait_data
)
```

---

## Зависимости

Минимальные зависимости для изоляции:

- `pydantic` >= 2.5.0 - модели данных
- `asyncpg` >= 0.29.0 - работа с PostgreSQL
- `selfology_bot.database.service` - только DatabaseService

---

## Best Practices

### 1. Инициализация
Всегда инициализируйте сервис перед использованием:

```python
soul = SoulArchitectService(db)
success = await soul.initialize()
if not success:
    raise RuntimeError("Failed to initialize Soul Architect")
```

### 2. Обработка ошибок
Обрабатывайте ошибки при работе с профилями:

```python
try:
    profile = await soul.get_profile(user_id)
except ValueError:
    # Профиль не найден - создаем новый
    profile = await soul.create_profile(user_id)
```

### 3. Пакетные обновления
Используйте `batch_update_traits` для обновления нескольких черт:

```python
# Лучше
await soul.batch_update_traits(user_id, updates)

# Хуже
for update in updates:
    await soul.update_trait(user_id, ...)  # N запросов к БД
```

### 4. Confidence и variance
Учитывайте confidence при принятии решений:

```python
if trait.confidence < 0.5:
    print("Недостаточно данных для надежной оценки")
elif trait.variance > 0.3:
    print("Высокий разброс в ответах - возможно непоследовательность")
```

---

## Интеграция с Selfology

### В Onboarding системе

```python
from selfology_bot.soul_architect import SoulArchitectService

class OnboardingOrchestrator:
    def __init__(self, db_service):
        self.soul = SoulArchitectService(db_service)

    async def process_answer(self, user_id, answer):
        # Анализ ответа
        traits = await self.analyze_answer(answer)

        # Обновление профиля
        for trait in traits:
            await self.soul.update_trait(
                user_id=user_id,
                category=trait.category,
                trait_name=trait.name,
                value=trait.value,
                confidence=trait.confidence
            )
```

---

## Roadmap

### Version 1.1 (Planned)
- [ ] Экспорт профилей в разные форматы (PDF, JSON, CSV)
- [ ] Визуализация эволюции черт
- [ ] Сравнение профилей между пользователями
- [ ] ML-powered предсказание будущих изменений

### Version 2.0 (Future)
- [ ] Интеграция с Qdrant для семантического поиска
- [ ] AI-generated инсайты о личности
- [ ] Автоматическое определение уникальной подписи

---

## Лицензия

Proprietary - Selfology.me

## Поддержка

По вопросам и issues обращаться к команде Selfology.

---

**Создано с любовью для проекта Selfology.me 🚀**
