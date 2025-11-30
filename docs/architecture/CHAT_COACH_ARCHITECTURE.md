# Chat Coach Architecture

## Архитектура AI-коуча который "знает всё"

### Проблема
- 72 цели + 62 барьера + 47 интересов = 10K+ токенов
- Невозможно загружать всё в каждый промпт

### Решение: UserDossierService

```
БЫЛО: raw data (10K+ токенов)
СТАЛО: AI-досье (~500 токенов)
```

**Структура досье:**
- WHO: кто пользователь (2 предложения)
- TOP_GOALS: топ-3 цели с объяснением
- TOP_BARRIERS: топ-3 барьера с гипотезой причин
- PATTERNS: паттерны из ответов
- CONTRADICTIONS: противоречия (цели vs барьеры)
- STYLE_HINTS: как общаться (из Big Five)

### Компоненты

```
selfology_bot/services/chat/
├── chat_mvp.py           # Основной чат
├── session_manager.py    # Управление сессией
├── user_dossier_service.py  # AI-резюме личности
└── dossier_validator.py  # Коррекции + check-in
```

### DossierValidator

**1. CorrectionDetector** - реактивная коррекция:
```python
# Маркеры:
"нет, на самом деле..." → fact_wrong
"это было раньше..."    → outdated
"не совсем так..."      → partial
```

**2. CheckInManager** - проактивная валидация:
```python
# Триггеры:
- После 5 сессий без валидации
- Цели старше 30 дней
- Барьеры старше 45 дней
```

### Flow

```
process_message(user_id, message)
    ↓
get_user_dossier() → ~500 токенов
    ↓
dossier_validator.process_message()
    ├── correction_detected? → invalidate + response_prefix
    └── check_in_needed? → add check_in question
    ↓
_build_ai_prompt(dossier, style_hints)
    ↓
AI генерирует ПЕРСОНАЛИЗИРОВАННЫЙ ответ
```

### Кэширование

```python
# Redis (1 час TTL)
dossier:{user_id} → UserDossier JSON

# Инвалидация:
- После 5 новых ответов
- При изменении digital_personality
- При детекции коррекции
```

### Тестирование

```bash
python tests/test_chat_mvp.py

# Тесты:
✅ SessionManager
✅ UserDossier Dataclass
✅ UserDossierService Init
✅ CorrectionDetector (9/9 cases)
✅ CheckInManager
✅ DossierValidator
✅ ChatMVP
✅ Resistance Handling
```

### Использование

```python
from selfology_bot.services.chat import ChatMVP, UserDossierService

# Инициализация
chat = ChatMVP(
    cluster_router=router,
    db_pool=pool,
    ai_client=client,
    redis_client=redis
)

# Получить досье
dossier = await chat.get_user_dossier(user_id)
print(dossier.to_prompt_context())  # ~500 токенов

# Обработать сообщение (автоматически использует досье)
response = await chat.process_message(user_id, "Расскажи о моих целях")
```

### Roadmap

- [x] UserDossierService (AI-резюме)
- [x] CorrectionDetector (автокоррекция)
- [x] CheckInManager (валидация)
- [ ] Semantic Search (Qdrant) для релевантных целей/барьеров
- [ ] Pattern Analyzer (противоречия, breakthroughs)

---
*Создано: 2025-11-30*
