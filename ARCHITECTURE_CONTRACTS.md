# ARCHITECTURE CONTRACTS - Selfology System

## 🎯 ЦЕЛЬ
Явные контракты между всеми компонентами системы. Каждый компонент ОБЯЗАН соблюдать эти контракты.

---

## 📋 PIPELINE: Onboarding Flow

### 1. OnboardingOrchestrator → AnswerAnalyzer

**Метод**: `answer_analyzer.analyze_answer()`

**Входные параметры**:
```python
{
    "question_text": str,           # Текст вопроса
    "user_answer": str,             # Ответ пользователя
    "question_metadata": {          # Метаданные вопроса
        "domain": str,
        "depth_level": str,
        "energy_dynamic": str
    },
    "context": {                    # Контекст анализа
        "answer_history": List[Dict],
        "question_history": List[str],
        "user_profile": Optional[Dict]
    }
}
```

**ОБЯЗАТЕЛЬНЫЙ возврат**:
```python
{
    # === ВЕРСИОНИРОВАНИЕ ===
    "analysis_version": "2.0",
    "created_at": str,              # ISO datetime

    # === КРИТИЧНО: Эти поля ОБЯЗАТЕЛЬНЫ ===
    "personality_summary": {        # ❗ БЕЗ ЭТОГО ВЕКТОРЫ НЕ СОЗДАЮТСЯ
        "nano": str,                # 50 символов (строго ограничено)
        "structured": str,          # JSON string с архетипом и чертами
        "narrative": str,           # 200-300 слов
        "embedding_prompt": str     # Оптимизировано для embeddings
    },

    # === Психологический анализ ===
    "psychological_analysis": {     # ✅ DICT (не строка!)
        "insights": {
            "main": str,            # Основной инсайт
            "patterns": [str],      # Паттерны поведения
            "growth_edge": str      # Зона роста
        },
        "emotional_assessment": {
            "primary": str,         # neutral/positive/negative
            "valence": float,       # -1.0 to 1.0
            "arousal": float        # 0.0 to 1.0
        },
        "behavioral_patterns": [str],
        "growth_indicators": [str]
    },

    # === Черты личности ===
    "personality_traits": {         # ✅ DICT (не trait_scores!)
        "big_five": {
            "openness": float,      # 0.0 to 1.0
            "conscientiousness": float,
            "extraversion": float,
            "agreeableness": float,
            "neuroticism": float
        }
    },

    # === Метаданные качества ===
    "quality_metadata": {
        "trait_confidence": {       # Confidence для каждой черты
            "openness": float,
            "conscientiousness": float,
            ...
        },
        "overall_reliability": float,
        "data_completeness": float,
        "needs_validation": bool
    },

    # === Рекомендации роутера ===
    "router_recommendations": {},   # Рекомендации для QuestionRouter

    # === Технические данные ===
    "processing_metadata": {
        "model_used": str,          # gpt-4o / gpt-4o-mini / claude-3.5-sonnet
        "analysis_depth": str,      # shallow / standard / deep
        "special_situation": str,   # None / crisis / breakthrough / resistance
        "question_domain": str,
        "question_number": int
    },

    # === Debug информация ===
    "debug_info": {
        "raw_ai_response_length": int,
        "trait_extraction_successful": bool,
        "fallback_used": bool,
        "processing_notes": [str]
    }
}
```

**СТАТУС**: ✅ КОНТРАКТ СОБЛЮДАЕТСЯ (исправлено 02.10.2025)

---

### 2. OnboardingOrchestrator → EmbeddingCreator

**Метод**: `embedding_creator.create_personality_vector()`

**Входные параметры**:
```python
{
    "user_id": int,
    "analysis_result": Dict,        # ❗ ДОЛЖЕН содержать personality_summary
    "is_update": bool
}
```

**ТРЕБОВАНИЯ к analysis_result**:
```python
analysis_result["personality_summary"] = {
    "nano": str,                    # ❗ ОБЯЗАТЕЛЬНО
    "narrative": str,               # ❗ ОБЯЗАТЕЛЬНО
    "embedding_prompt": str         # Опционально, fallback на narrative
}
```

**Возврат**:
```python
bool  # True если векторы созданы, False если ошибка
```

**ТЕКУЩАЯ ПРОБЛЕМА**:
- ❌ Всегда возвращает True даже когда векторы НЕ созданы
- ❌ Нет логирования причины ошибки

---

### 3. OnboardingOrchestrator → PersonalityExtractor

**Метод**: `personality_extractor.extract_from_answer()`

**Входные параметры**:
```python
{
    "question_text": str,
    "user_answer": str,
    "question_metadata": Dict,
    "existing_personality": Optional[Dict]
}
```

**ОБЯЗАТЕЛЬНЫЙ возврат**:
```python
{
    "identity": [{"aspect": str, "description": str, "confidence": str}],
    "interests": [{"activity": str, "context": str, "status": str}],
    "skills": [{"skill": str, "level": str, "specifics": List[str]}],
    "goals": [{"goal": str, "type": str, "priority": str}],
    "barriers": [{"barrier": str, "type": str, "impact": str}],
    "relationships": [{"person": str, "relationship": str}],
    "values": [{"value": str, "context": str}],
    "health": [{"aspect": str, "condition": str, "impact": str}],
    "current_state": [{"activity": str, "status": str}],
    "key_phrases": List[str]
}
```

**ВАЖНО**: Все поля - ARRAYS, не dict!

---

### 4. OnboardingOrchestrator → DigitalPersonalityDAO

**Метод**: `personality_dao.update_personality()`

**Входные параметры**:
```python
{
    "user_id": int,
    "new_extraction": Dict,  # Формат из PersonalityExtractor
    "merge": bool            # True = инкремент счетчика, False = reset
}
```

**Поведение**:
- `merge=True`: total_answers_analyzed += 1
- `merge=False`: total_answers_analyzed = 1

**Возврат**:
```python
bool  # True если успешно
```

---

## ✅ ИСПРАВЛЕННЫЕ ПРОБЛЕМЫ (02.10.2025)

### ✅ Проблема #1: personality_summary не создавался
**Где**: onboarding_dao.py:451
**Root Cause**: Сохранялся только `debug_info` вместо полного `analysis_result`
**Решение**: Изменено на `json.dumps(analysis_result, ensure_ascii=False)`
**Статус**: ✅ ИСПРАВЛЕНО

### ⏳ Проблема #2: Векторы не создаются (0 в Qdrant)
**Где**: EmbeddingCreator.create_personality_vector()
**Файл**: selfology_bot/analysis/embedding_creator.py
**Статус**: Требует тестирования после исправления #1

### ⏳ Проблема #3: analysis_status не обновляется в 'completed'
**Где**: OnboardingOrchestrator._run_deep_analysis_pipeline()
**Файл**: selfology_bot/services/onboarding/orchestrator.py
**Статус**: Требует исправления

---

## 📊 DATA INTEGRITY CHECK

### PostgreSQL:
- user_answers_new: 32 ответа
- answer_analysis: 4 анализа
- Статус 'completed': 0 ❌

### Qdrant:
- selfology_answers_small: 0 векторов ❌
- selfology_answers_medium: 0 векторов ❌
- selfology_answers_large: 0 векторов ❌

### Проблема:
Даже для ответов с реальным AI анализом (gpt-4o) векторы НЕ созданы!

---

## ✅ NEXT STEPS (в порядке приоритета)

1. ✅ Исправить AnswerAnalyzer - добавить personality_summary
2. ✅ Исправить EmbeddingCreator - правильное логирование ошибок
3. ✅ Добавить обновление статуса в 'completed'
4. ✅ Запустить тест: ответить на вопрос → проверить что вектор создан
5. ✅ Запустить bulk reprocessing для 4 существующих анализов
