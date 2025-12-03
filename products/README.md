# Selfology Digital Products

Подпроект для создания digital-продуктов на основе ядра вопросов.

## Источник данных

**Ядро**: [`../intelligent_question_core/data/selfology_programs_v2.json`](../intelligent_question_core/data/selfology_programs_v2.json)

```
version: 2.0
generated_at: 2025-11-29
```

---

## Структура данных

### Иерархия

```
29 Программ
  └── 190 Кластеров (блоков)
        └── 674 Вопроса
```

### Программа (Program)

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | string | Уникальный ID программы |
| `name` | string | Название программы |
| `blocks` | array | Массив кластеров |

### Кластер (Block)

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | string | Уникальный ID кластера |
| `sequence` | int | Порядок в программе (1, 2, 3...) |
| `name` | string | Название кластера |
| `description` | string | Краткое описание |
| `type` | enum | `Foundation` / `Exploration` / `Integration` |
| `questions` | array | Массив вопросов |
| `block_metadata` | object | Метаданные для AI-системы |

### Вопрос (Question)

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | string | Уникальный ID вопроса |
| `position` | int | Глобальная позиция в программе |
| `position_in_block` | int | Позиция внутри кластера |
| `text` | string | Текст вопроса |
| `format` | enum | `ai_only` / `book_only` / `both` |

### Метаданные кластера (block_metadata)

| Поле | Значения | Описание |
|------|----------|----------|
| `base_journey_stage` | `ENTRY` / `EXPLORATION` / `INTEGRATION` | Этап путешествия |
| `base_depth_range` | `SURFACE` → `CONSCIOUS` → `EDGE` → `SHADOW` → `CORE` | Диапазон глубины |
| `base_energy_dynamic` | `OPENING` / `NEUTRAL` / `PROCESSING` / `HEAVY` / `HEALING` | Энергетика |
| `base_safety_minimum` | 1-5 | Минимальный уровень безопасности |
| `base_complexity_range` | [min, max] | Диапазон сложности (1-5) |
| `base_emotional_weight_range` | [min, max] | Эмоциональный вес (1-5) |

---

## Форматы вопросов

| Формат | Где используется |
|--------|------------------|
| `ai_only` | Только в боте (интерактивный диалог) |
| `book_only` | Только в книге (для самостоятельной работы) |
| `both` | И в боте, и в книге |

---

## Статистика по волнам

| Волна | Кластеров | Вопросов | Назначение |
|-------|-----------|----------|------------|
| ENTRY | 32 | 118 | Знакомство, ориентация |
| EXPLORATION | 120 | 402 | Исследование, углубление |
| INTEGRATION | 38 | 154 | Синтез, завершение |

---

## Структура подпроекта

```
products/
├── book/              # Книга-воркбук
├── cards/             # Карточная колода
├── exports/           # Готовые экспорты
├── scripts/           # Скрипты генерации
├── archive/           # Старые версии
└── README.md          # Этот файл
```

---

## Продукты (Roadmap)

- [ ] **Книга-воркбук** — 29 глав по программам
- [ ] **Карточная колода** — 190 карт по кластерам
- [ ] **Notion шаблон** — интерактивный журнал
- [ ] **PDF для печати** — красивый дизайн

---

## Архив

Старые версии экспортов находятся в `archive/`:
- `selfology_book_book_only.md` — первая версия книги
- `selfology_book_book_only.html` — HTML версия
