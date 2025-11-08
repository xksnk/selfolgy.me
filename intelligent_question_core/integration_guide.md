# 🔌 Руководство по интеграции с основным проектом Selfology

## 📋 Подготовка к перемещению

### 1. Проверьте целостность ядра
```bash
cd intelligent_question_core/
python3 api/core_api.py  # должен пройти демо без ошибок
```

### 2. Убедитесь в наличии всех файлов
```
✅ data/selfology_intelligent_core.json     (908KB - главный файл)
✅ data/enhanced_questions.json             (693 вопроса с метаданными)  
✅ data/question_connections.json           (344 связи)
✅ data/question_search_indexes.json        (13,257 индексов)
✅ config/question_taxonomy_base.json       (13 доменов)
✅ config/energy_flow_rules_base.json       (правила переходов)
✅ api/core_api.py                          (основное API)
```

## 🏗️ Интеграция с основным проектом

### В основном проекте Selfology создайте:
```
selfology/
├── question_core/                    # ← Сюда перемещаем папку
│   └── intelligent_question_core/   # ← Вся наша папка
├── telegram_bot/
├── n8n_workflows/ 
├── database/
└── api/
```

### Интеграция с FastAPI:
```python
# В main.py основного проекта:
from question_core.intelligent_question_core.api.core_api import SelfologyQuestionCore

app = FastAPI()

# Инициализация ядра при старте
@app.on_event("startup")
async def startup_event():
    global question_core
    question_core = SelfologyQuestionCore(
        "question_core/intelligent_question_core/data/selfology_intelligent_core.json"
    )

# API endpoints для работы с вопросами
@app.get("/questions/search")
async def search_questions(
    domain: str = None,
    depth_level: str = None, 
    energy: str = None,
    min_safety: int = None
):
    return question_core.search_questions(
        domain=domain,
        depth_level=depth_level,
        energy=energy,
        min_safety=min_safety
    )

@app.get("/questions/{question_id}")
async def get_question(question_id: str):
    return question_core.get_question(question_id)

@app.get("/questions/{question_id}/connections")
async def get_connected_questions(question_id: str, connection_type: str = None):
    return question_core.find_connected_questions(question_id, connection_type)
```

### Интеграция с Telegram Bot:
```python
# В telegram_bot/handlers.py:
from question_core.intelligent_question_core.api.core_api import SelfologyQuestionCore

question_core = SelfologyQuestionCore()

async def select_next_question(user_id: int, current_question_id: str):
    """Выбор следующего вопроса на основе связей"""
    
    # Получаем связанные вопросы
    connected = question_core.find_connected_questions(
        current_question_id, 
        "logical_sequence"
    )
    
    # Фильтруем по безопасности пользователя
    user_trust_level = get_user_trust_level(user_id)
    safe_questions = [
        q for q in connected 
        if q["psychology"]["safety_level"] >= user_trust_level
    ]
    
    return safe_questions[0] if safe_questions else None
```

### Интеграция с n8n workflows:
```javascript
// В n8n Custom Code node:
const fs = require('fs');

// Загружаем ядро вопросов
const coreData = JSON.parse(
  fs.readFileSync('/path/to/question_core/data/selfology_intelligent_core.json')
);

// Ищем подходящий вопрос
function findQuestionByDomain(domain) {
  const searchIndexes = coreData.search_indexes;
  const questionIds = searchIndexes.by_classification.domain[domain] || [];
  
  if (questionIds.length > 0) {
    const questionId = questionIds[Math.floor(Math.random() * questionIds.length)];
    return coreData.questions.find(q => q.id === questionId);
  }
  
  return null;
}

// Пример использования в workflow
const identityQuestion = findQuestionByDomain("IDENTITY");
return [{ json: { nextQuestion: identityQuestion } }];
```

## 🔧 Обновление существующих workflow

### 1. Обновите COMPLETE-FIXED-WORKFLOW.json:
```json
{
  "nodes": [
    {
      "name": "Question Selector",
      "type": "n8n-nodes-base.code",
      "parameters": {
        "jsCode": "// Используем question_core для выбора вопроса\nconst questionCore = require('./question_core/api/core_api.py');\nreturn questionCore.selectOptimalQuestion($json);"
      }
    }
  ]
}
```

### 2. Обновите таблицы PostgreSQL:
```sql
-- Добавьте поля для работы с умным ядром
ALTER TABLE selfology.sessions ADD COLUMN current_question_id VARCHAR(10);
ALTER TABLE selfology.sessions ADD COLUMN question_sequence JSONB;
ALTER TABLE selfology.sessions ADD COLUMN energy_balance JSONB;

-- Создайте таблицу для связей вопросов
CREATE TABLE selfology.question_relationships (
    id SERIAL PRIMARY KEY,
    question_id VARCHAR(10),
    related_question_id VARCHAR(10),
    connection_type VARCHAR(50),
    strength DECIMAL(3,3),
    created_at TIMESTAMP DEFAULT NOW()
);
```

## 📊 Миграционный чеклист

### Перед перемещением:
- [ ] Убедитесь что все файлы на месте
- [ ] Запустите `python3 api/core_api.py` для проверки
- [ ] Сохраните backup текущих данных

### После перемещения:
- [ ] Обновите пути в import'ах
- [ ] Протестируйте API endpoints
- [ ] Проверьте интеграцию с Telegram Bot
- [ ] Обновите n8n workflows
- [ ] Добавьте в систему мониторинга

### Валидация работоспособности:
```python
# Тестовый скрипт после интеграции
def test_core_integration():
    # Тест поиска
    questions = core.search_questions(domain="IDENTITY")
    assert len(questions) > 0, "Поиск не работает"
    
    # Тест связей
    connected = core.find_connected_questions(questions[0]["id"])
    assert len(connected) > 0, "Связи не работают"
    
    # Тест рекомендаций моделей
    rec = core.get_processing_recommendation(questions[0]["id"])
    assert "recommended_model" in rec, "Роутер моделей не работает"
    
    print("✅ Все тесты пройдены!")
```

## 🚀 Производительность

- **Поиск вопросов:** O(1) благодаря индексам
- **Граф связей:** 344 связи для навигации  
- **Размер ядра:** 908KB (быстрая загрузка)
- **Память:** ~2MB в RAM при загрузке
- **API отклик:** <10ms для большинства операций

## 🔄 Обновление и развитие

### Добавление новых вопросов:
1. Добавить в `enhanced_questions.json`
2. Обновить индексы через `rebuild_indexes.py`
3. Пересчитать связи для новых вопросов

### Изменение классификации:
1. Обновить `question_taxonomy_base.json`
2. Перезапустить индексирование
3. Валидировать через Claude

## 💡 Рекомендации по использованию

### В production:
- Загружайте ядро один раз при старте приложения
- Кешируйте результаты поиска для частых запросов
- Мониторьте использование разных типов вопросов
- Собирайте метрики эффективности для оптимизации

### Для разработки:
- Используйте `search_api_demo.py` для тестирования
- Добавляйте новые типы связей по мере необходимости
- Экспериментируйте с энергетическими правилами

---

🎯 **Ядро готово к интеграции с основным проектом Selfology!**