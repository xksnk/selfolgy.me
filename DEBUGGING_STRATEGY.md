# 🔍 DEBUGGING STRATEGY - Selfology System

## ПРОБЛЕМА
Сейчас невозможно отследить путь одного ответа через всю систему:
- Где именно ломается?
- Какие данные передаются между компонентами?
- Почему векторы не создаются?

## РЕШЕНИЕ: Request Tracing

### 1. Trace ID для каждого ответа

Добавить в начало `process_user_answer()`:
```python
import uuid

trace_id = str(uuid.uuid4())[:8]  # Короткий ID
logger.info(f"[{trace_id}] 🎯 START processing answer from user {user_id}")
```

Передавать trace_id через все компоненты:
```python
# В каждом логе
logger.info(f"[{trace_id}] ✅ AI analysis completed")
logger.info(f"[{trace_id}] 📊 Creating vectors...")
logger.error(f"[{trace_id}] ❌ No personality_summary found!")
```

### 2. Data Validation Checkpoints

В каждой критической точке логировать ЧТО передается:

```python
# После AI анализа
logger.info(f"[{trace_id}] 📋 Analysis result keys: {list(analysis_result.keys())}")
logger.info(f"[{trace_id}] 🔍 Has personality_summary: {'personality_summary' in analysis_result}")

# Перед созданием векторов
logger.info(f"[{trace_id}] 📊 Vector creation input: user_id={user_id}, has_summary={bool(summary_data)}")

# После создания векторов
logger.info(f"[{trace_id}] ✅ Vector creation result: {vector_success}")
```

### 3. Централизованный Trace Log

Создать `/home/ksnk/n8n-enterprise/projects/selfology/logs/trace.log`:

Формат:
```
[trace_id] [timestamp] [component] [action] [data]
```

Пример:
```
[a3f5b2c1] 2025-10-02T17:45:00 orchestrator START answer_processing user_id=98005572
[a3f5b2c1] 2025-10-02T17:45:05 answer_analyzer AI_CALL model=gpt-4o
[a3f5b2c1] 2025-10-02T17:45:10 answer_analyzer AI_RESPONSE keys=['psychological_insights','trait_scores']
[a3f5b2c1] 2025-10-02T17:45:10 answer_analyzer ERROR missing_key='personality_summary'
[a3f5b2c1] 2025-10-02T17:45:11 embedding_creator VECTOR_SKIP reason='no_personality_summary'
[a3f5b2c1] 2025-10-02T17:45:11 orchestrator COMPLETE vectors=false
```

### 4. Contract Validation Decorators

Создать декоратор для валидации контрактов:

```python
def validate_contract(required_keys: List[str]):
    def decorator(func):
        async def wrapper(*args, **kwargs):
            result = await func(*args, **kwargs)

            # Проверяем что все required_keys есть в результате
            if isinstance(result, dict):
                missing = [k for k in required_keys if k not in result]
                if missing:
                    logger.error(f"CONTRACT VIOLATION in {func.__name__}: missing keys {missing}")
                    raise ContractViolationError(f"Missing required keys: {missing}")

            return result
        return wrapper
    return decorator

# Использование:
@validate_contract(["personality_summary", "trait_scores", "psychological_insights"])
async def analyze_answer(self, ...):
    # ...
```

---

## 🎯 IMMEDIATE ACTION PLAN

### Step 1: Добавить trace_id (5 минут)
Файлы:
- `selfology_bot/services/onboarding/orchestrator.py`
  - Метод: `process_user_answer()` - добавить генерацию trace_id
  - Передать через весь pipeline

### Step 2: Добавить data validation logs (10 минут)
Файлы:
- `selfology_bot/analysis/answer_analyzer.py`
  - После AI вызова: логировать keys результата
  - Проверить наличие personality_summary

- `selfology_bot/analysis/embedding_creator.py`
  - В начале: логировать что получили
  - При ошибке: логировать ПОЧЕМУ failed

### Step 3: Исправить personality_summary (20 минут)
Файл: `selfology_bot/analysis/answer_analyzer.py`

Добавить ПОСЛЕ AI анализа:
```python
# Генерируем personality_summary для векторизации
personality_summary = {
    "nano": self._generate_nano_summary(ai_response),
    "narrative": self._generate_narrative_summary(ai_response),
    "embedding_prompt": self._generate_embedding_prompt(ai_response)
}

result["personality_summary"] = personality_summary
```

### Step 4: Исправить vector creation (10 минут)
Файл: `selfology_bot/analysis/embedding_creator.py`

Изменить логику:
```python
# Было:
if not summary_data:
    logger.error(...)  # Логирует но продолжает
    return False

# Должно быть:
if not summary_data:
    logger.error(f"[{trace_id}] ❌ CRITICAL: No personality_summary in analysis_result")
    logger.error(f"[{trace_id}] 📋 Available keys: {list(analysis_result.keys())}")
    return False  # ✅ Правильно возвращает False
```

### Step 5: Обновлять статус на 'completed' (5 минут)
Файл: `selfology_bot/services/onboarding/orchestrator.py`

После успешного анализа:
```python
# Обновляем статус в БД
await self.onboarding_dao.update_answer_status(answer_id, "completed")
```

---

## 📊 TESTING PROTOCOL

### Test 1: Single Answer E2E Test
```bash
# 1. Ответить на вопрос в боте
# 2. Проверить логи:
grep "trace_id_here" logs/trace.log

# 3. Проверить БД:
SELECT analysis_status FROM user_answers_new WHERE id = ...;

# 4. Проверить Qdrant:
curl http://localhost:6333/collections/selfology_answers_medium
```

### Test 2: Bulk Reprocessing
```bash
# Перезапустить анализ для 4 существующих ответов
python scripts/reprocess_answers.py --answer-ids 35,36,39,40
```

---

## 🔴 КРИТИЧЕСКИЕ МЕТРИКИ (для мониторинга)

После каждого ответа проверять:

1. ✅ Анализ создан в answer_analysis?
2. ✅ personality_summary есть в raw_ai_response?
3. ✅ Статус обновлен на 'completed'?
4. ✅ Вектор создан в Qdrant?
5. ✅ total_answers_analyzed инкрементирован?

Если хотя бы один ❌ - ALARM!

---

## 💡 NEXT: Auto-Healing

Добавить авто-восстановление:

```python
# Каждые 5 минут проверять
async def health_check():
    # Найти ответы где analysis_status='analyzed' но нет векторов
    broken_answers = await find_broken_answers()

    for answer in broken_answers:
        logger.warning(f"🔧 Auto-healing answer {answer.id}")
        await retry_vector_creation(answer.id)
```
