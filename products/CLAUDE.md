# CLAUDE.md — Products Subproject

## Обзор

Подпроект для создания цифровых продуктов на основе базы вопросов Selfology.

**Источник данных:** `intelligent_question_core/data/selfology_programs_v2.json`
- 29 программ
- 190 кластеров (blocks)
- 674 вопроса

---

## Текущий продукт: Две книги PDF

### Книга 1: "29 программ самопознания" (тематический подход)
- Пользователь приходит с конкретной болью (отношения, карьера, страхи)
- Открывает оглавление → находит тему → проходит кластеры
- Структура: Программа → Кластеры (от лёгких к глубоким) → Вопросы
- User flow: выбор темы → последовательное погружение внутри темы

### Книга 2: "Путь в глубину" (прогрессивный подход)
- Пользователь хочет исследовать себя без конкретного фокуса
- Постепенное погружение: Часть 1 (легко) → Часть 2 (глубже) → Часть 3 (самое глубокое)
- Темы ЧЕРЕДУЮТСЯ внутри каждого уровня для разнообразия
- Те же кластеры, реорганизованные по глубине

### Метаданные кластера
| Поле | Пример | Использование |
|------|--------|---------------|
| name | "Люди рядом" | Заголовок кластера |
| description | "экосистема влияний" | Контекст |
| type | Foundation/Exploration/Integration | Уровень глубины |
| time | 5-10 / 10-20 / 15-30 мин | Планирование |
| program.name | "Отношения" | Контекст в Книге 2 |

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
- [x] **Book 1 PDF готов**: 236 страниц, 29 программ, 190 кластеров, 674 вопроса
- [x] **Book 2 PDF готов**: кластеры по глубине (Foundation → Exploration → Integration)
- [x] Экранирование LaTeX символов
- [x] Удаление emoji из исходников
- [x] Визуальная дифференциация глубины (questionF/E/I)

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
    ├── TECHNICAL_SPEC.md  ← техническая спецификация
    ├── scripts/
    │   └── generate_books.py
    ├── templates/
    │   ├── STYLE_SPEC.md         ← спецификация стиля
    │   ├── selfology-book.latex  ← LaTeX шаблон
    │   └── ru/
    │       ├── intro.md
    │       ├── warnings.md
    │       └── conclusion.md
    └── exports/
        └── ru/
            ├── book1_programs.md
            ├── book1_programs.pdf
            ├── book2_depth.md
            └── book2_depth.pdf
```

---

## Ключевые команды

```bash
# Генерация markdown
cd products/book
python3 scripts/generate_books.py

# Конвертация в PDF
cd exports/ru
pandoc book1_programs.md -o book1_programs.pdf \
  --pdf-engine=xelatex \
  --template=../../templates/selfology-book.latex

pandoc book2_depth.md -o book2_depth.pdf \
  --pdf-engine=xelatex \
  --template=../../templates/selfology-book.latex
```

---

## Принципы дизайна (цель)

- **Минимализм** — но смелый, с контрастом
- **Швейцарская типографика** — современная интерпретация
- **Воздух** — пространство для рефлексии
- **Безопасность** — визуальные сигналы глубины
- **Прогресс** — ощущение движения вперёд
- **Мультиязычность** — работает для кириллицы и латиницы

---

## Что пользователь должен ЧУВСТВОВАТЬ

- Глубину — через визуальный вес, не через слова
- Безопасность — "тут будет непросто, приготовься"
- Прогресс — "я двигаюсь вперёд"
- Пространство — "мне дают время подумать"
