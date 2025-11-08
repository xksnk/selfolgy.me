# 🔧 Подробный план исправлений - 2025-10-01

## 📋 Контекст

**Текущая ситуация:**
- Бот запущен и работает частично
- Ответы сохраняются в БД
- AI анализ НЕ работает (3 критичные ошибки)

**Цель:**
Исправить 3 критичные проблемы для полноценной работы системы анализа ответов.

---

## 🎯 Проблемы и решения

### Проблема #1: AnswerAnalyzer - отсутствующие методы

#### 📍 Локация
```
Файл: selfology_bot/analysis/answer_analyzer.py
Строка 177: enriched["energy_level"] = self._estimate_user_energy(enriched)
Строка 143: return await self._get_emergency_analysis(...)
```

#### 🐛 Суть проблемы
```python
# ОШИБКА 1:
AttributeError: 'AnswerAnalyzer' object has no attribute '_estimate_user_energy'

# ОШИБКА 2:
AttributeError: 'AnswerAnalyzer' object has no attribute '_get_emergency_analysis'
```

Эти методы **вызываются**, но **не определены** в классе.

#### 🔍 Анализ кода

**Где вызываются:**

1. **`_estimate_user_energy()`** - строка 177:
```python
async def _enrich_context(...) -> Dict[str, Any]:
    # ... код ...
    enriched["trust_level"] = min(1.0, 0.2 + (question_number / 30.0) * 0.8)

    # ❌ ОШИБКА - метод не существует:
    enriched["energy_level"] = self._estimate_user_energy(enriched)

    return enriched
```

**Цель метода:** Оценить текущий уровень энергии пользователя на основе:
- Времени суток
- Длины ответов
- Скорости ответов
- Истории взаимодействия

2. **`_get_emergency_analysis()`** - строка 143:
```python
except Exception as e:
    logger.error(f"❌ Error in comprehensive analysis for user {user_id}: {e}")

    # ... обновление статистики ...

    # ❌ ОШИБКА - метод не существует:
    return await self._get_emergency_analysis(question_data, user_answer, user_context, str(e))
```

**Цель метода:** Предоставить минимальный fallback анализ если основной pipeline упал:
- Базовые traits (neutral значения)
- Простой instant feedback
- Флаг что это emergency response

#### ✅ Решение

**Вариант A: Добавить полноценные методы** (20-30 мин)
```python
def _estimate_user_energy(self, context: Dict[str, Any]) -> float:
    """
    Оценка энергетического уровня пользователя

    Args:
        context: Обогащенный контекст с данными о пользователе

    Returns:
        float от 0.0 до 1.0 (0.0 = низкая энергия, 1.0 = высокая)
    """
    energy_score = 0.5  # Базовая оценка

    # 1. Анализ длины ответов (более длинные = выше энергия)
    answer_length = context.get("answer_length", 50)
    if answer_length > 200:
        energy_score += 0.2
    elif answer_length < 30:
        energy_score -= 0.2

    # 2. Анализ скорости ответов (быстрые = выше энергия)
    response_time = context.get("response_time_seconds", 60)
    if response_time < 30:
        energy_score += 0.1
    elif response_time > 120:
        energy_score -= 0.1

    # 3. Прогресс в онбординге (усталость накапливается)
    question_number = context.get("question_number", 1)
    fatigue_factor = min(0.3, question_number / 100)  # Max 0.3 усталости
    energy_score -= fatigue_factor

    # 4. Fatigue level из контекста
    fatigue_level = context.get("fatigue_level", 0.0)
    energy_score -= fatigue_level * 0.3

    # Нормализуем в диапазон [0.0, 1.0]
    return max(0.0, min(1.0, energy_score))

async def _get_emergency_analysis(
    self,
    question_data: Dict[str, Any],
    user_answer: str,
    user_context: Dict[str, Any],
    error_message: str
) -> Dict[str, Any]:
    """
    Emergency fallback анализ при сбое основного pipeline

    Args:
        question_data: Данные вопроса
        user_answer: Ответ пользователя
        user_context: Контекст пользователя
        error_message: Сообщение об ошибке

    Returns:
        Минимальный но валидный анализ
    """
    user_id = user_context.get("user_id", "unknown")

    logger.warning(f"🚨 Using emergency analysis for user {user_id} due to: {error_message}")

    # Создаем минимальный валидный анализ
    return {
        "user_id": user_id,
        "question_id": question_data.get("id", "unknown"),

        # Instant feedback (нейтральный)
        "instant_feedback": "Спасибо за ваш ответ. Обрабатываю информацию...",

        # Минимальные traits (все нейтральные значения)
        "traits": {
            "openness": 0.5,
            "conscientiousness": 0.5,
            "extraversion": 0.5,
            "agreeableness": 0.5,
            "neuroticism": 0.5
        },

        # Психологические insights (простое отражение)
        "psychological_insights": f"Ваш ответ показывает вдумчивость и готовность к самопознанию.",

        # Emotional state (neutral)
        "emotional_state": "neutral",

        # Fatigue level (низкий)
        "fatigue_level": 0.0,

        # Metadata
        "analysis_version": "emergency_fallback_v1",
        "ai_model_used": "emergency_handler",
        "processing_time_ms": 0,
        "processed_at": datetime.now().isoformat(),

        # Флаги
        "is_emergency_analysis": True,
        "original_error": error_message,
        "quality_score": 0.3,  # Низкое качество
        "confidence_score": 0.2  # Низкая уверенность
    }
```

**Вариант B: Временная заглушка** (5 мин, быстрый фикс)
```python
def _estimate_user_energy(self, context: Dict[str, Any]) -> float:
    """Временная заглушка - возвращает средний уровень энергии"""
    return 0.5

async def _get_emergency_analysis(self, question_data, user_answer, user_context, error_message):
    """Временная заглушка - минимальный анализ"""
    return {
        "instant_feedback": "Спасибо за ваш ответ.",
        "traits": {"openness": 0.5, "conscientiousness": 0.5, "extraversion": 0.5,
                   "agreeableness": 0.5, "neuroticism": 0.5},
        "is_emergency_analysis": True
    }
```

#### 🎯 Рекомендация
**Использовать Вариант A** - полноценные методы, т.к.:
1. Система анализа критична для продукта
2. Emergency handler нужен для resilience
3. Один раз написать правильно = меньше проблем потом

#### ⏱️ Время: 20-30 минут

---

### Проблема #2: Счетчик questions_asked не инкрементируется

#### 📍 Локация
```
Файл: selfology_bot/services/onboarding/orchestrator.py
Метод: start_onboarding() или process_answer()
```

#### 🐛 Суть проблемы
```
БД показывает: questions_asked = 0
Telegram показывает: "Вопрос 3/693"

Причина: Счетчик в БД НЕ обновляется при отправке вопроса
```

#### 🔍 Анализ кода

**Проблема:** В `orchestrator.py` НЕТ упоминаний `questions_asked`.

Проверка показала:
```bash
grep "questions_asked" selfology_bot/services/onboarding/orchestrator.py
# Результат: No matches found
```

Это значит что **инкремент счетчика просто отсутствует**.

**Где ДОЛЖЕН быть инкремент:**

1. После выбора и отправки первого вопроса (`start_onboarding`)
2. После выбора и отправки следующего вопроса (`process_answer`)

**Текущий flow:**
```python
async def start_onboarding(self, user_id: int):
    # 1. Выбираем первый вопрос
    first_question = await self.question_router.get_first_question(...)

    # 2. Создаем сессию в БД
    session_id = await self.onboarding_dao.create_session(...)

    # 3. Сохраняем в памяти
    self.active_sessions[user_id] = {...}

    # 4. Возвращаем вопрос для отправки
    return {...}

    # ❌ НЕТ: await self._increment_questions_asked(session_id)
```

#### ✅ Решение

**Шаг 1:** Найти где создается/обновляется сессия в БД
```python
# Проверяем OnboardingDAO
grep -n "def.*update_session\|def.*increment" selfology_bot/database/onboarding_dao.py
```

**Шаг 2:** Если метод есть - использовать его
```python
async def _increment_questions_asked(self, session_id: int):
    """Инкремент счетчика заданных вопросов"""
    await self.onboarding_dao.increment_questions_asked(session_id)
```

**Шаг 3:** Если метода нет - добавить в OnboardingDAO
```python
# В selfology_bot/database/onboarding_dao.py

async def increment_questions_asked(self, session_id: int):
    """Инкремент счетчика questions_asked"""
    await self.session.execute(
        text("""
            UPDATE selfology.onboarding_sessions
            SET questions_asked = questions_asked + 1,
                last_activity = NOW()
            WHERE id = :session_id
        """),
        {"session_id": session_id}
    )
    await self.session.commit()
    logger.debug(f"✅ Incremented questions_asked for session {session_id}")
```

**Шаг 4:** Вызывать в orchestrator.py

**Место 1 - после отправки первого вопроса:**
```python
async def start_onboarding(self, user_id: int):
    # ... существующий код выбора вопроса ...

    # Создаем сессию
    session_id = await self.onboarding_dao.create_session(...)

    # ✅ ДОБАВИТЬ: Инкремент при отправке первого вопроса
    await self.onboarding_dao.increment_questions_asked(session_id)

    # Сохраняем в памяти
    self.active_sessions[user_id] = {...}

    return {...}
```

**Место 2 - после отправки следующего вопроса:**
```python
async def process_answer(self, user_id: int, answer_text: str):
    # ... обработка ответа ...

    # Получаем следующий вопрос
    next_question = await self.question_router.get_next_question(...)

    # ✅ ДОБАВИТЬ: Инкремент при отправке следующего вопроса
    session_id = self.active_sessions[user_id]["session_id"]
    await self.onboarding_dao.increment_questions_asked(session_id)

    return next_question
```

#### 🎯 Важно
Инкремент должен быть **после** того как вопрос выбран, но **до** того как мы вернем его пользователю. Это гарантирует что счетчик = реальному количеству **отправленных** вопросов.

#### ⏱️ Время: 10-15 минут

---

### Проблема #3: Qdrant коллекции не создаются

#### 📍 Локация
```
Файл: selfology_bot/analysis/embedding_creator.py
Метод: setup_qdrant_collections()
```

#### 🐛 Суть проблемы
```
Логи говорят: "✅ Created 3 Qdrant collections"
Реальность: curl http://localhost:6333/collections показывает что их нет

Причина: URL неправильный или создание проходит с ошибкой которая не логируется
```

#### 🔍 Анализ кода

**Текущий код (embedding_creator.py):**
```python
def __init__(self):
    # ...
    # Коннекция к Qdrant (пока mock)
    self.qdrant_client = None  # Будет инициализирован в setup
```

**Проблема:** `qdrant_client = None` - коннекция не установлена!

Логи показывают что метод `setup_qdrant_collections()` вызывается:
```
2025-10-01 15:51:12,415 - analysis.embedding_creator - INFO - 🏗️ Setting up Qdrant collections...
2025-10-01 15:51:12,916 - analysis.embedding_creator - INFO - ✅ Created 3 Qdrant collections
```

Но проверка через API показывает что коллекций нет.

**Гипотеза 1:** URL неправильный
```bash
# Из .env.development:
QDRANT_URL=http://qdrant:6333

# Проблема: в локальном запуске "qdrant:6333" не резолвится
# Нужно: http://localhost:6333
```

**Гипотеза 2:** Ошибка создания подавляется
```python
try:
    # создание коллекции
    logger.info("✅ Created")
except Exception:
    pass  # ❌ Ошибка подавлена, не видна!
```

#### ✅ Решение

**Шаг 1:** Найти метод `setup_qdrant_collections()`
```bash
grep -n "def setup_qdrant_collections" selfology_bot/analysis/embedding_creator.py
```

**Шаг 2:** Проверить инициализацию Qdrant client
```python
# Должно быть примерно так:

import os
from qdrant_client import QdrantClient

def __init__(self):
    # ...

    # ✅ ИСПРАВИТЬ: Правильная инициализация с fallback на localhost
    qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")

    # Для локального запуска форсируем localhost
    if "qdrant:6333" in qdrant_url:
        qdrant_url = "http://localhost:6333"
        logger.info(f"🔧 Adjusted Qdrant URL for local run: {qdrant_url}")

    try:
        self.qdrant_client = QdrantClient(url=qdrant_url)
        logger.info(f"📈 Connected to Qdrant at {qdrant_url}")
    except Exception as e:
        logger.error(f"❌ Failed to connect to Qdrant: {e}")
        self.qdrant_client = None
```

**Шаг 3:** Убедиться что ошибки НЕ подавляются
```python
async def setup_qdrant_collections(self):
    """Создание коллекций в Qdrant"""

    if not self.qdrant_client:
        raise RuntimeError("❌ Qdrant client not initialized")

    logger.info("🏗️ Setting up Qdrant collections...")

    collections_to_create = [
        {
            "name": "selfology_answers_small",
            "vector_size": 512,
            "distance": "Cosine"
        },
        {
            "name": "selfology_answers_medium",
            "vector_size": 1536,
            "distance": "Cosine"
        },
        {
            "name": "selfology_answers_large",
            "vector_size": 3072,
            "distance": "Cosine"
        }
    ]

    created_count = 0

    for collection_config in collections_to_create:
        try:
            name = collection_config["name"]

            # Проверяем существует ли уже
            existing = await self.qdrant_client.get_collections()
            if name in [c.name for c in existing.collections]:
                logger.info(f"✅ Collection {name} already exists")
                created_count += 1
                continue

            # Создаем новую коллекцию
            await self.qdrant_client.create_collection(
                collection_name=name,
                vectors_config={
                    "size": collection_config["vector_size"],
                    "distance": collection_config["distance"]
                }
            )

            logger.info(f"✅ Created collection {name}")
            created_count += 1

        except Exception as e:
            # ❌ НЕ ПОДАВЛЯЕМ ОШИБКУ!
            logger.error(f"❌ Failed to create collection {name}: {e}")
            raise  # Пробрасываем ошибку выше

    logger.info(f"✅ Created/verified {created_count} Qdrant collections")
    return created_count == len(collections_to_create)
```

**Шаг 4:** Добавить проверку после создания
```python
# В orchestrator.py после setup:

if not await self.embedding_creator.setup_qdrant_collections():
    logger.warning("⚠️ Failed to setup Qdrant collections - embeddings will not work!")
```

#### 🎯 Важно
1. **URL** должен быть `localhost:6333` для локального запуска
2. **Ошибки** НЕ должны подавляться
3. **Проверка** создания должна быть explicit

#### ⏱️ Время: 15-20 минут

---

## 📊 Суммарный план действий

### Последовательность (от простого к сложному):

#### Этап 1: Быстрый фикс счетчика (10-15 мин)
1. Добавить метод `increment_questions_asked` в `OnboardingDAO`
2. Вызывать после отправки вопроса в `orchestrator.py`
3. Проверить в БД что счетчик работает

#### Этап 2: Исправить Qdrant (15-20 мин)
4. Исправить URL в `embedding_creator.py` (localhost для локального запуска)
5. Добавить proper error handling
6. Проверить через `curl localhost:6333/collections` что коллекции созданы

#### Этап 3: Добавить методы в AnswerAnalyzer (20-30 мин)
7. Добавить `_estimate_user_energy()` с логикой
8. Добавить `_get_emergency_analysis()` для fallback
9. Убедиться что нет других missing методов

#### Этап 4: Тестирование (10-15 мин)
10. Перезапустить бот (hot reload сделает автоматически)
11. Отправить новый ответ на вопрос
12. Проверить:
    - ✅ Счетчик `questions_asked` инкрементирован
    - ✅ AI анализ создан в `answer_analysis`
    - ✅ Коллекции Qdrant существуют
    - ✅ Embeddings созданы

---

## ⚡ Быстрая последовательность команд

```bash
# 1. Исправляем счетчик (просто, быстро)
claude "Добавь increment_questions_asked в OnboardingDAO и вызови в orchestrator"

# 2. Исправляем Qdrant (средняя сложность)
claude "Исправь Qdrant URL в embedding_creator для локального запуска"

# 3. Исправляем AnswerAnalyzer (сложнее, но критично)
claude "Добавь методы _estimate_user_energy и _get_emergency_analysis в AnswerAnalyzer"

# 4. Тестируем
claude "Отправь тестовый ответ и проверь что все работает"
```

---

## 🎯 Ожидаемый результат

### После исправлений:

**БД (PostgreSQL):**
```sql
Session 4:
  questions_asked: 3      ← Корректный счетчик
  questions_answered: 2   ← Корректно

Answer 4:
  question_id: q_433
  analysis_status: completed  ← НЕ pending!

Analysis 1:
  user_answer_id: 4
  traits: {"openness": 0.7, ...}  ← Реальные значения
  psychological_insights: "..."    ← Реальный AI анализ
```

**Qdrant:**
```json
{
  "collections": [
    "selfology_answers_small",
    "selfology_answers_medium",
    "selfology_answers_large",
    ...
  ]
}
```

**Telegram:**
```
Вопрос 4/693  ← Соответствует БД
```

---

## ⏱️ Общее время: ~60-80 минут

**Разбивка:**
- Счетчик: 10-15 мин
- Qdrant: 15-20 мин
- AnswerAnalyzer: 20-30 мин
- Тестирование: 10-15 мин
- Буфер на неожиданности: 5-10 мин

---

## 💡 Советы при исправлении

### 1. Hot Reload работает
Бот запущен с `watchmedo` - изменения применятся автоматически через 1-2 секунды после сохранения файла.

### 2. Логи в реальном времени
```bash
# Смотреть что происходит:
tail -f logs/selfology.log

# Или через background bash:
BashOutput bash_id=f321fb
```

### 3. Тестировать по одному
Не исправляй все сразу. Порядок:
1. Исправил счетчик → протестировал → работает ✅
2. Исправил Qdrant → протестировал → работает ✅
3. Исправил AnswerAnalyzer → протестировал → работает ✅

### 4. Backup перед большими изменениями
```bash
cp selfology_bot/analysis/answer_analyzer.py selfology_bot/analysis/answer_analyzer.py.backup
```

### 5. Проверка после каждого шага
```bash
# После фикса счетчика:
SELECT questions_asked FROM selfology.onboarding_sessions WHERE id = 4;

# После фикса Qdrant:
curl localhost:6333/collections | jq

# После фикса AnswerAnalyzer:
SELECT COUNT(*) FROM selfology.answer_analysis;
```

---

**Готов начинать исправления? С чего начнем?**

1. Счетчик (самое простое)
2. Qdrant (средняя сложность)
3. AnswerAnalyzer (самое важное)
