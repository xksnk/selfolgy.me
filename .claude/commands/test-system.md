# Тестирование конкретной системы

Запусти тесты для указанной системы с подробным выводом.

## Использование:
```
/test-system question_selection
/test-system soul_architect
/test-system telegram_gateway
```

## Что тестируем:

**question_selection:**
```bash
source venv/bin/activate
pytest tests/unit/systems/question_selection/ -v --tb=short
pytest tests/e2e/test_onboarding_flow.py -k "question" -v
```

**soul_architect:**
```bash
source venv/bin/activate
pytest tests/unit/systems/soul_architect/ -v --tb=short
```

**telegram_gateway:**
```bash
source venv/bin/activate
pytest tests/unit/systems/telegram_gateway/ -v --tb=short
```

**analysis_worker:**
```bash
source venv/bin/activate
pytest tests/unit/systems/analysis_worker/ -v --tb=short
```

**ai_router:**
```bash
source venv/bin/activate
pytest tests/unit/systems/ai_router/ -v --tb=short
```

**core (все паттерны):**
```bash
source venv/bin/activate
pytest tests/unit/core/ -v --tb=short
pytest tests/integration/core/ -v --tb=short
```

Укажи систему для тестирования!
