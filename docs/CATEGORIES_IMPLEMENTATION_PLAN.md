# 🎯 План Внедрения Категорий в Базу Вопросов

**Дата**: 6 октября 2025
**База**: selfology_intelligent_core_complete.json (1331 вопрос)

---

## 📊 ТЕКУЩЕЕ СОСТОЯНИЕ

### База Вопросов
- **Всего вопросов**: 1331
- **Источники**:
  - `ai_generation_v2_2025`: 638 (новые сгенерированные)
  - `deep_understanding_v3`: 375 (старые глубокие)
  - `onboarding_v7`: 318 (онбординг)

### Статус Категорий
- ❌ **Поле "category" отсутствует** во всех вопросах
- ✅ **Естественные группы видны** по domain + depth_level
- ✅ **Метаданные богатые**: domain, depth_level, journey_stage, energy_dynamic

### Распределение (топ-8 доменов)

| Домен | Вопросов | % |
|-------|----------|---|
| IDENTITY | 758 | 56.9% |
| RELATIONSHIPS | 121 | 9.1% |
| EMOTIONS | 100 | 7.5% |
| VALUES | 74 | 5.6% |
| GOALS | 63 | 4.7% |
| FEARS | 50 | 3.8% |
| GROWTH | 49 | 3.7% |
| WORK | 36 | 2.7% |

### Глубина

| Уровень | Вопросов | % |
|---------|----------|---|
| SURFACE | 52 | 3.9% |
| CONSCIOUS | 838 | 63.0% |
| EDGE | 249 | 18.7% |
| SHADOW | 120 | 9.0% |
| CORE | 72 | 5.4% |

**✅ ОТЛИЧНО**: Есть все уровни глубины!

### Энергия

| Тип | Вопросов | % |
|-----|----------|---|
| NEUTRAL | 698 | 52.4% |
| HEAVY | 234 | 17.6% |
| PROCESSING | 187 | 14.0% |
| HEALING | 161 | 12.1% ← ВАЖНО для баланса |
| OPENING | 51 | 3.8% |

**✅ ХОРОШО**: 161 HEALING вопрос для баланса после HEAVY!

---

## 🎯 РЕКОМЕНДУЕМАЯ СТРУКТУРА КАТЕГОРИЙ

### Вариант 1️⃣: По Доменам (12 категорий)

**Основа**: используем поле `domain` как основную категорию

```
CATEGORIES_BY_DOMAIN = {
    "IDENTITY": {
        "display_name": "Идентичность и Самопонимание",
        "description": "Кто я? Мои роли, характер, убеждения",
        "icon": "👤",
        "questions": 758
    },
    "RELATIONSHIPS": {
        "display_name": "Отношения и Связи",
        "description": "Близость, любовь, семья, границы",
        "icon": "❤️",
        "questions": 121
    },
    "EMOTIONS": {
        "display_name": "Эмоции и Чувства",
        "description": "Эмоциональный интеллект, осознанность",
        "icon": "💭",
        "questions": 100
    },
    "VALUES": {
        "display_name": "Ценности и Принципы",
        "description": "Что для меня важно? Мои приоритеты",
        "icon": "💎",
        "questions": 74
    },
    "GOALS": {
        "display_name": "Цели и Стремления",
        "description": "Куда я иду? Мои мечты и планы",
        "icon": "🎯",
        "questions": 63
    },
    "FEARS": {
        "display_name": "Страхи и Сопротивления",
        "description": "Что меня останавливает? Работа со страхами",
        "icon": "😰",
        "questions": 50
    },
    "GROWTH": {
        "display_name": "Рост и Развитие",
        "description": "Как я меняюсь? Мой путь развития",
        "icon": "🌱",
        "questions": 49
    },
    "WORK": {
        "display_name": "Работа и Призвание",
        "description": "Карьера, профессия, самореализация",
        "icon": "💼",
        "questions": 36
    },
    ... остальные домены
}
```

**Внутри каждой категории**: автоматическая сортировка по `depth_level`
- SURFACE → CONSCIOUS → EDGE → SHADOW → CORE

### Вариант 2️⃣: По Глубине (5 категорий)

**Основа**: используем `depth_level` как основную категорию

```
CATEGORIES_BY_DEPTH = {
    "SURFACE": {
        "display_name": "Первое Знакомство",
        "description": "Легкие вопросы для начала пути",
        "level": 1,
        "questions": 52
    },
    "CONSCIOUS": {
        "display_name": "Осознанное Исследование",
        "description": "Рефлексия и понимание себя",
        "level": 2,
        "questions": 838
    },
    "EDGE": {
        "display_name": "Граница Комфорта",
        "description": "Честность с собой, выход из зоны комфорта",
        "level": 3,
        "questions": 249
    },
    "SHADOW": {
        "display_name": "Теневая Работа",
        "description": "Скрытые части, трудные темы",
        "level": 4,
        "questions": 120
    },
    "CORE": {
        "display_name": "Глубинная Трансформация",
        "description": "Самые глубокие истины о себе",
        "level": 5,
        "questions": 72
    }
}
```

**Внутри каждой категории**: автоматическая группировка по `domain`

### Вариант 3️⃣: ГИБРИДНЫЙ (РЕКОМЕНДУЮ! ⭐)

**Двухуровневая иерархия**: Domain → Depth

```json
{
  "category": "EMOTIONS",
  "subcategory": "EDGE",
  "display_name": "Эмоции: Граница Комфорта",
  "full_path": "EMOTIONS > EDGE",
  "category_position": 15,
  "total_in_category": 50
}
```

**Преимущества**:
- ✅ Пользователь выбирает тему (домен)
- ✅ Система ведет по глубине (автоматическая прогрессия)
- ✅ Безопасная последовательность (не прыгает по уровням)
- ✅ Естественные группы по 10-50 вопросов

**Пример прогрессии для категории EMOTIONS**:
```
1. EMOTIONS_SURFACE (1 вопрос)
   "Какие эмоции ты чувствуешь чаще всего?"

2. EMOTIONS_CONSCIOUS (13 вопросов)
   "Где в теле ты чувствуешь радость?"
   "Как меняется дыхание когда приходит тревога?"
   ...

3. EMOTIONS_EDGE (24 вопроса)
   "Когда ты говоришь 'я в порядке' - как часто это правда?"
   "Какую эмоцию труднее всего признать перед собой?"
   ...

4. EMOTIONS_SHADOW (10 вопросов)
   "Какую эмоцию ты подавляешь так долго что она стала частью тебя?"
   ...

5. EMOTIONS_CORE (2 вопроса)
   "Кем бы ты был если позволишь себе чувствовать всё?"
```

### Вариант 4️⃣: Специальные Программы

**Кураторские подборки** для конкретных запросов:

```
SPECIAL_PROGRAMS = {
    "HEALING_JOURNEY": {
        "display_name": "🌸 Путь Исцеления",
        "description": "Программа благодарности и восстановления",
        "questions": [все HEALING вопросы = 161],
        "duration": "7 дней",
        "questions_per_day": 23
    },
    "SHADOW_WORK": {
        "display_name": "🌑 Теневая Работа",
        "description": "Глубокое исследование скрытых частей себя",
        "questions": [все SHADOW + CORE = 192],
        "duration": "14 дней",
        "questions_per_day": 14
    },
    "EDGE_BREAKTHROUGH": {
        "display_name": "🔥 Прорыв Границ",
        "description": "Выход из зоны комфорта",
        "questions": [все EDGE = 249],
        "duration": "21 день",
        "questions_per_day": 12
    },
    "EMOTIONAL_MASTERY": {
        "display_name": "💭 Мастерство Эмоций",
        "description": "Полный путь эмоционального интеллекта",
        "questions": [EMOTIONS domain all depths = 100],
        "duration": "10 дней",
        "questions_per_day": 10
    },
    "RELATIONSHIP_DEEP_DIVE": {
        "display_name": "❤️ Глубина Отношений",
        "description": "Трансформация отношений с собой и другими",
        "questions": [RELATIONSHIPS domain all depths = 121],
        "duration": "12 дней",
        "questions_per_day": 10
    }
}
```

---

## 🛠️ ПЛАН ВНЕДРЕНИЯ

### Этап 1: Добавление Метаданных (2-3 часа)

**Создать скрипт** `scripts/add_categories_to_questions.py`:

```python
#!/usr/bin/env python3
"""
Добавляет поля category в каждый вопрос
"""
import json
from pathlib import Path

def add_categories(questions: list) -> list:
    """Добавляет category metadata к каждому вопросу"""

    # Группируем по domain + depth
    categories = {}

    for q in questions:
        domain = q['classification']['domain']
        depth = q['classification']['depth_level']

        cat_key = f"{domain}_{depth}"

        if cat_key not in categories:
            categories[cat_key] = {
                'questions': [],
                'domain': domain,
                'depth': depth
            }

        categories[cat_key]['questions'].append(q)

    # Сортируем вопросы внутри каждой категории
    depth_order = ['SURFACE', 'CONSCIOUS', 'EDGE', 'SHADOW', 'CORE']

    updated_questions = []

    for cat_key in sorted(categories.keys()):
        cat_data = categories[cat_key]
        cat_questions = cat_data['questions']

        # Сортируем по энергии: OPENING → NEUTRAL → PROCESSING → HEAVY → HEALING
        energy_order = {
            'OPENING': 1,
            'NEUTRAL': 2,
            'PROCESSING': 3,
            'HEAVY': 4,
            'HEALING': 5
        }

        cat_questions.sort(
            key=lambda x: energy_order.get(
                x['classification']['energy_dynamic'],
                99
            )
        )

        # Добавляем category metadata
        for idx, q in enumerate(cat_questions, 1):
            q['category'] = {
                'name': cat_data['domain'],
                'subcategory': cat_data['depth'],
                'display_name': f"{cat_data['domain']}: {cat_data['depth']}",
                'position_in_category': idx,
                'total_in_category': len(cat_questions)
            }

            updated_questions.append(q)

    return updated_questions

def main():
    # Загрузить базу
    input_file = Path('intelligent_question_core/data/selfology_intelligent_core_complete.json')

    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    print(f"📖 Загружено {len(data['questions'])} вопросов")

    # Добавить категории
    updated = add_categories(data['questions'])

    # Обновить метаданные
    data['questions'] = updated
    data['metadata']['version'] = '4.0'
    data['metadata']['last_updated'] = datetime.now().isoformat()
    data['metadata']['categories_added'] = True

    # Сохранить
    output_file = Path('intelligent_question_core/data/selfology_intelligent_core_categorized.json')

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"✅ Сохранено в {output_file}")
    print(f"✅ Добавлены категории для всех {len(updated)} вопросов")

if __name__ == '__main__':
    from datetime import datetime
    main()
```

**Запустить**:
```bash
python3 scripts/add_categories_to_questions.py
```

**Результат**: `selfology_intelligent_core_categorized.json` с category metadata

---

### Этап 2: Обновление Базы Данных (1-2 часа)

**SQL миграция** - добавить поля в `questions_metadata`:

```sql
-- Добавить поля категорий
ALTER TABLE selfology.questions_metadata
ADD COLUMN IF NOT EXISTS category VARCHAR(50),
ADD COLUMN IF NOT EXISTS subcategory VARCHAR(50),
ADD COLUMN IF NOT EXISTS category_position INTEGER,
ADD COLUMN IF NOT EXISTS category_display_name VARCHAR(100);

-- Создать индексы для быстрого поиска
CREATE INDEX IF NOT EXISTS idx_category
ON selfology.questions_metadata(category);

CREATE INDEX IF NOT EXISTS idx_subcategory
ON selfology.questions_metadata(subcategory);

CREATE INDEX IF NOT EXISTS idx_category_position
ON selfology.questions_metadata(category, category_position);

-- Комментарии
COMMENT ON COLUMN selfology.questions_metadata.category IS 'Основная категория (domain)';
COMMENT ON COLUMN selfology.questions_metadata.subcategory IS 'Подкатегория (depth_level)';
COMMENT ON COLUMN selfology.questions_metadata.category_position IS 'Позиция вопроса внутри категории';
```

**Скрипт обновления** `scripts/sync_categories_to_db.py`:

```python
#!/usr/bin/env python3
"""
Синхронизирует category metadata из JSON в PostgreSQL
"""
import asyncio
import json
from pathlib import Path
from selfology_bot.database import DatabaseService

async def sync_categories():
    """Синхронизировать категории в БД"""

    # Загрузить categorized JSON
    with open('intelligent_question_core/data/selfology_intelligent_core_categorized.json', 'r') as f:
        data = json.load(f)

    db = DatabaseService(...)  # ваши параметры
    await db.initialize()

    async with db.get_connection() as conn:
        updated = 0

        for q in data['questions']:
            qid = q['id']
            cat = q.get('category', {})

            if not cat:
                continue

            await conn.execute("""
                UPDATE selfology.questions_metadata
                SET
                    category = $1,
                    subcategory = $2,
                    category_position = $3,
                    category_display_name = $4
                WHERE json_id = $5
            """,
                cat.get('name'),
                cat.get('subcategory'),
                cat.get('position_in_category'),
                cat.get('display_name'),
                qid
            )

            updated += 1

            if updated % 100 == 0:
                print(f"  ✅ Обновлено {updated} вопросов...")

    await db.close()

    print(f"\n🎉 Синхронизировано {updated} вопросов!")

if __name__ == '__main__':
    asyncio.run(sync_categories())
```

---

### Этап 3: CategoryManager (2-3 часа)

**Создать** `systems/onboarding/category_manager.py`:

```python
"""
CategoryManager - управление категориями вопросов
"""
from typing import List, Optional, Dict
from dataclasses import dataclass

@dataclass
class Category:
    """Категория вопросов"""
    name: str
    display_name: str
    description: str
    icon: str
    total_questions: int
    available_depths: List[str]

@dataclass
class CategoryProgress:
    """Прогресс пользователя в категории"""
    category: str
    subcategory: str
    answered: int
    total: int
    last_question_position: int

class CategoryManager:
    """Управление категориями"""

    CATEGORIES = {
        'EMOTIONS': Category(
            name='EMOTIONS',
            display_name='Эмоции и Чувства',
            description='Эмоциональный интеллект и осознанность',
            icon='💭',
            total_questions=100,
            available_depths=['SURFACE', 'CONSCIOUS', 'EDGE', 'SHADOW', 'CORE']
        ),
        'RELATIONSHIPS': Category(...),
        # ... остальные категории
    }

    def __init__(self, db_service):
        self.db = db_service

    async def get_available_categories(
        self,
        user_id: int
    ) -> List[Category]:
        """Получить доступные категории для пользователя"""
        # Все категории доступны с самого начала
        return list(self.CATEGORIES.values())

    async def start_category(
        self,
        user_id: int,
        category_name: str,
        session_id: int
    ) -> Optional[Dict]:
        """Начать категорию - вернуть первый вопрос"""

        # Получить первый вопрос категории
        async with self.db.get_connection() as conn:
            question = await conn.fetchrow("""
                SELECT json_id, category, subcategory, category_position
                FROM selfology.questions_metadata
                WHERE category = $1
                AND category_position = 1
                ORDER BY
                    CASE subcategory
                        WHEN 'SURFACE' THEN 1
                        WHEN 'CONSCIOUS' THEN 2
                        WHEN 'EDGE' THEN 3
                        WHEN 'SHADOW' THEN 4
                        WHEN 'CORE' THEN 5
                    END
                LIMIT 1
            """, category_name)

            return dict(question) if question else None

    async def get_next_question_in_category(
        self,
        user_id: int,
        category_name: str,
        current_position: int,
        session_id: int
    ) -> Optional[Dict]:
        """Получить следующий вопрос в категории"""

        async with self.db.get_connection() as conn:
            # Получить следующий неотвеченный вопрос
            question = await conn.fetchrow("""
                SELECT qm.json_id, qm.category, qm.subcategory, qm.category_position
                FROM selfology.questions_metadata qm
                LEFT JOIN selfology.user_answers_new ua
                    ON ua.question_json_id = qm.json_id
                    AND ua.session_id = $3
                WHERE qm.category = $1
                AND qm.category_position > $2
                AND ua.id IS NULL
                ORDER BY qm.category_position
                LIMIT 1
            """, category_name, current_position, session_id)

            return dict(question) if question else None

    async def get_category_progress(
        self,
        user_id: int,
        category_name: str,
        session_id: int
    ) -> CategoryProgress:
        """Получить прогресс в категории"""

        async with self.db.get_connection() as conn:
            stats = await conn.fetchrow("""
                WITH category_questions AS (
                    SELECT json_id, category_position
                    FROM selfology.questions_metadata
                    WHERE category = $1
                ),
                answered AS (
                    SELECT COUNT(*) as count,
                           MAX(qm.category_position) as last_position
                    FROM selfology.user_answers_new ua
                    JOIN selfology.questions_metadata qm
                        ON ua.question_json_id = qm.json_id
                    WHERE ua.session_id = $2
                    AND qm.category = $1
                )
                SELECT
                    (SELECT COUNT(*) FROM category_questions) as total,
                    COALESCE(answered.count, 0) as answered,
                    COALESCE(answered.last_position, 0) as last_position
                FROM answered
            """, category_name, session_id)

            return CategoryProgress(
                category=category_name,
                subcategory='',  # TODO: определить текущую подкатегорию
                answered=stats['answered'],
                total=stats['total'],
                last_question_position=stats['last_position']
            )
```

---

### Этап 4: Обновить QuestionRouter (1-2 часа)

**Добавить поддержку категорий** в `systems/onboarding/question_selection_service.py`:

```python
class QuestionRouter:
    """Роутер вопросов с поддержкой категорий"""

    def __init__(self, db_service):
        self.db = db_service
        self.category_manager = CategoryManager(db_service)

    async def get_next_question(
        self,
        user_id: int,
        session_id: int,
        mode: str = 'auto'  # 'auto', 'category', 'smart_mix'
    ) -> Optional[Dict]:
        """
        Получить следующий вопрос

        Args:
            mode:
                - 'auto': автоматический выбор (Smart Mix)
                - 'category': пользователь выбрал категорию
                - 'smart_mix': умная смесь из разных категорий
        """

        if mode == 'category':
            # Пользователь выбрал конкретную категорию
            return await self._get_next_from_active_category(user_id, session_id)

        elif mode == 'smart_mix':
            # Умная смесь: балансируем домены и глубину
            return await self._smart_mix_selection(user_id, session_id)

        else:  # 'auto'
            # Автоматический выбор по существующему алгоритму
            return await self._auto_selection(user_id, session_id)

    async def _get_next_from_active_category(
        self,
        user_id: int,
        session_id: int
    ) -> Optional[Dict]:
        """Получить следующий вопрос из активной категории"""

        # Получить активную категорию пользователя
        async with self.db.get_connection() as conn:
            active = await conn.fetchrow("""
                SELECT category, last_question_position
                FROM selfology.user_category_progress
                WHERE user_id = $1 AND session_id = $2
                AND completed_at IS NULL
            """, user_id, session_id)

            if not active:
                return None

            # Получить следующий вопрос
            return await self.category_manager.get_next_question_in_category(
                user_id,
                active['category'],
                active['last_question_position'],
                session_id
            )
```

---

### Этап 5: UI в Telegram Боте (2-3 часа)

**Добавить команды и кнопки** в `selfology_bot/bot/handlers/onboarding.py`:

```python
# Команда /categories - показать доступные категории
@router.message(Command("categories"))
async def show_categories(message: Message, state: FSMContext):
    """Показать доступные категории"""

    user_id = message.from_user.id

    # Получить категории
    categories = await category_manager.get_available_categories(user_id)

    # Создать кнопки
    keyboard = []
    for cat in categories:
        progress = await category_manager.get_category_progress(
            user_id,
            cat.name,
            session_id
        )

        button_text = f"{cat.icon} {cat.display_name} ({progress.answered}/{progress.total})"
        keyboard.append([InlineKeyboardButton(
            text=button_text,
            callback_data=f"category_{cat.name}"
        )])

    await message.answer(
        "📚 Выбери категорию для исследования:\n\n"
        "Каждая категория ведет тебя от простых вопросов к более глубоким.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )

# Callback для выбора категории
@router.callback_query(F.data.startswith("category_"))
async def select_category(callback: CallbackQuery, state: FSMContext):
    """Выбор категории"""

    category_name = callback.data.replace("category_", "")
    user_id = callback.from_user.id

    # Начать категорию
    question = await category_manager.start_category(
        user_id,
        category_name,
        session_id
    )

    if question:
        await state.update_data(active_category=category_name)

        # Показать первый вопрос
        await send_question(callback.message, question)
    else:
        await callback.answer("Категория пуста или завершена!")

# Команда /progress - показать прогресс
@router.message(Command("progress"))
async def show_progress(message: Message):
    """Показать прогресс по категориям"""

    user_id = message.from_user.id

    progress_text = "📊 Твой прогресс:\n\n"

    for cat_name in CATEGORY_NAMES:
        progress = await category_manager.get_category_progress(
            user_id,
            cat_name,
            session_id
        )

        percent = (progress.answered / progress.total * 100) if progress.total > 0 else 0
        bar = "█" * int(percent / 10) + "░" * (10 - int(percent / 10))

        progress_text += (
            f"{CATEGORIES[cat_name].icon} {CATEGORIES[cat_name].display_name}\n"
            f"{bar} {progress.answered}/{progress.total} ({percent:.0f}%)\n\n"
        )

    await message.answer(progress_text)
```

---

## 📋 ЧЕКЛИСТ ВНЕДРЕНИЯ

### Фаза 1: Подготовка (День 1)
- [ ] Создать скрипт `add_categories_to_questions.py`
- [ ] Запустить скрипт, получить `selfology_intelligent_core_categorized.json`
- [ ] Проверить результат: все вопросы имеют category metadata
- [ ] Создать SQL миграцию для БД
- [ ] Применить миграцию к PostgreSQL

### Фаза 2: Синхронизация (День 1-2)
- [ ] Создать скрипт `sync_categories_to_db.py`
- [ ] Запустить синхронизацию
- [ ] Проверить: SELECT * FROM questions_metadata WHERE category IS NOT NULL
- [ ] Создать таблицу `user_category_progress` для отслеживания прогресса

### Фаза 3: Backend (День 2-3)
- [ ] Создать `CategoryManager` class
- [ ] Написать юнит-тесты для CategoryManager
- [ ] Обновить `QuestionRouter` с поддержкой категорий
- [ ] Интеграционные тесты

### Фаза 4: Frontend (День 3-4)
- [ ] Добавить команду `/categories`
- [ ] Добавить callback для выбора категории
- [ ] Добавить команду `/progress`
- [ ] Добавить inline кнопки в сообщениях с вопросами
- [ ] Тестирование UI в Telegram

### Фаза 5: Деплой и Мониторинг (День 4-5)
- [ ] Деплой на продакшн
- [ ] Мониторинг метрик использования категорий
- [ ] Сбор фидбека от пользователей
- [ ] Оптимизация на основе данных

---

## 🎯 ОЖИДАЕМЫЕ РЕЗУЛЬТАТЫ

### Метрики Успеха

| Метрика | До | После | Цель |
|---------|----|----|------|
| Ответов за сессию | 3-5 | 10-15 | +200% |
| Completion rate | 20% | 60% | +200% |
| Время в приложении | 5 мин | 20 мин | +300% |
| Возвратов на след. день | 15% | 40% | +167% |

### Польза для Пользователя
- ✅ **Ясность**: понятно какая тема исследуется
- ✅ **Прогресс**: видимое продвижение внутри категории
- ✅ **Контроль**: выбор темы которая актуальна сейчас
- ✅ **Безопасность**: постепенное углубление без шока

### Польза для Системы
- ✅ **Структура**: организованная база вопросов
- ✅ **Аналитика**: понимание какие темы интересны
- ✅ **Персонализация**: рекомендации следующей категории
- ✅ **Маркетинг**: "Пройди программу Эмоционального Мастерства за 10 дней!"

---

## 🚀 БЫСТРЫЙ СТАРТ

**Хочешь начать прямо сейчас?**

```bash
# 1. Создать categorized версию
python3 scripts/add_categories_to_questions.py

# 2. Применить SQL миграцию
docker exec n8n-postgres psql -U n8n -d n8n -f migrations/add_categories.sql

# 3. Синхронизировать с БД
python3 scripts/sync_categories_to_db.py

# 4. Запустить тесты
python3 -m pytest tests/test_category_manager.py

# 5. Запустить бота
./run-local.sh
```

**Готов создавать скрипты?** 💪
