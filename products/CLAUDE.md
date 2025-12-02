# CLAUDE.md — Products Subproject

## Обзор

Подпроект для создания цифровых продуктов на основе базы вопросов Selfology.

**Источник данных:** `intelligent_question_core/data/selfology_master.json`
- 29 программ
- 190 кластеров (blocks)
- 657 вопросов
- 369 с метаданными (depth, domain, safety)
- 315 с улучшенными AI-формулировками

---

## Архитектура данных

### Single Source of Truth

```
selfology_master.json (v3.0)
├── Структура: программы → кластеры → вопросы
├── Метаданные из core базы (369 вопросов)
├── AI-улучшенные формулировки (315 вопросов)
└── Понятные описания кластеров (170 шт)
```

### API

```python
# Новый API (рекомендуется)
from intelligent_question_core.api.master_api import SelfologyMasterAPI
api = SelfologyMasterAPI()

# Программы и кластеры
programs = api.get_programs()  # ['Подумать о жизни', ...]
clusters = api.get_program_clusters('Подумать о жизни')

# Поиск вопросов
safe = api.get_safe_entry_questions()  # Foundation + safety >= 4
deep = api.get_deep_questions()        # Integration или SHADOW/CORE

# Рекомендация модели
rec = api.get_processing_recommendation('q_xxx')
# → {'recommended_model': 'gpt-4o', 'reasoning': '...'}
```

### Скрипты обработки данных

```bash
# Мёрдж баз (v2 + core) через Claude
python products/book/scripts/merge_databases.py

# Переформулировка описаний кластеров
python products/book/scripts/rewrite_descriptions.py --apply

# Применение всех изменений → master.json
python products/book/scripts/apply_all_changes.py
```

---

## Текущий продукт: Две книги PDF

### Книга 1: "29 программ самопознания" (тематический подход)
- Пользователь приходит с конкретной болью (отношения, карьера, страхи)
- Открывает оглавление → находит тему → проходит кластеры
- Структура: Программа → Кластеры (от лёгких к глубоким) → Вопросы

### Книга 2: "Путь в глубину" (прогрессивный подход)
- Пользователь хочет исследовать себя без конкретного фокуса
- Постепенное погружение: Часть 1 (легко) → Часть 2 (глубже) → Часть 3 (самое глубокое)
- Темы ЧЕРЕДУЮТСЯ внутри каждого уровня для разнообразия

### Метаданные кластера
| Поле | Пример | Использование |
|------|--------|---------------|
| name | "Люди рядом" | Заголовок кластера |
| description | "кто влияет на меня" | Понятный подзаголовок |
| type | Foundation/Exploration/Integration | Уровень глубины |
| time | 5-10 / 10-20 / 15-30 мин | Планирование |

### Языки
- RU (основной)
- EN (перевод)
- ES (перевод)

---

## Текущее состояние

### Что сделано
- [x] Структура папок `products/book/latex/`
- [x] LaTeX стиль `selfology-book.sty`
- [x] Генератор Book 1: `generate_book1.py`
- [x] Генератор Book 2: `generate_book2.py`
- [x] **Book 1 PDF готов**: 236 страниц, 29 программ, 190 кластеров
- [x] **Book 2 PDF готов**: кластеры по глубине (Foundation → Exploration → Integration)
- [x] Экранирование LaTeX символов
- [x] Удаление emoji из исходников
- [x] Визуальная дифференциация глубины (questionF/E/I)
- [x] **Unified master база** с AI-улучшениями
- [x] **Master API** для программного доступа
- [x] **170 описаний кластеров** переписаны понятным языком

### Команды генерации

```bash
cd /home/ksnk/microservices/critical/selfology-bot/products/book/latex

# Book 1: По программам
python3 generate_book1.py && xelatex selfology-book1.tex

# Book 2: По глубине
python3 generate_book2.py && xelatex selfology-book2.tex
```

---

## Структура папок

```
products/
├── CLAUDE.md              ← этот файл
├── README.md              ← обзор продуктов
└── book/
    ├── ALGORITHM.md       ← алгоритм генерации (для PM)
    ├── scripts/
    │   ├── merge_databases.py      ← AI-мёрдж баз (Claude)
    │   ├── rewrite_descriptions.py ← переформулировка описаний
    │   ├── apply_all_changes.py    ← создание master.json
    │   └── validate_questions.py   ← 3-этапная валидация
    ├── templates/
    │   ├── selfology-book.latex    ← LaTeX шаблон
    │   └── ru/
    │       ├── intro.md
    │       ├── warnings.md
    │       └── conclusion.md
    ├── latex/
    │   ├── generate_book1.py
    │   ├── generate_book2.py
    │   └── selfology-book.sty
    └── exports/
        └── ru/
            ├── selfology-book1.pdf
            └── selfology-book2.pdf
```

---

## Принципы дизайна

- **Минимализм** — но смелый, с контрастом
- **Швейцарская типографика** — современная интерпретация
- **Воздух** — пространство для рефлексии
- **Безопасность** — визуальные сигналы глубины
- **Прогресс** — ощущение движения вперёд

---

## Что пользователь должен ЧУВСТВОВАТЬ

- Глубину — через визуальный вес, не через слова
- Безопасность — "тут будет непросто, приготовься"
- Прогресс — "я двигаюсь вперёд"
- Пространство — "мне дают время подумать"
