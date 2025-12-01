# Техническая спецификация генерации книг

## Языки
- RU (оригинал)
- EN
- ES

---

## Структура файлов

```
intelligent_question_core/data/
  selfology_programs_v2.json              # Структура + RU тексты (оригинал)
  translations/
    questions_en.json                      # {"q_podumat_o_zhiznib1q1": "Describe your state..."}
    questions_es.json                      # {"q_podumat_o_zhiznib1q1": "Describe tu estado..."}
    blocks_en.json                         # {"block_id": {"name": "...", "description": "..."}}
    blocks_es.json
    programs_en.json                       # {"program_id": "Think about life"}
    programs_es.json

products/book/
  templates/
    ru/
      intro.md                             # Вводная часть
      warnings.md                          # Предупреждения
      conclusion.md                        # Заключение
    en/
      intro.md
      warnings.md
      conclusion.md
    es/
      intro.md
      warnings.md
      conclusion.md

  scripts/
    generate_books.py                      # Основной скрипт

  exports/
    ru/
      book1_programs.md
      book2_depth.md
    en/
      book1_programs.md
      book2_depth.md
    es/
      book1_programs.md
      book2_depth.md
```

---

## Алгоритм генерации

### Входные данные

```python
SOURCE_JSON = "intelligent_question_core/data/selfology_programs_v2.json"
TRANSLATIONS_DIR = "intelligent_question_core/data/translations/"
TEMPLATES_DIR = "products/book/templates/"
OUTPUT_DIR = "products/book/exports/"

LANGUAGES = ["ru", "en", "es"]

# Время на кластер
DEPTH_TIME = {
    "Foundation": "5-10",
    "Exploration": "10-20",
    "Integration": "15-30"
}

# =============================================================================
# STRATIFICATION SYSTEM — Визуальное ощущение глубины (без текстовых лейблов)
# =============================================================================
# Источник: products/research/ — Perplexity research Dec 2024
# Принцип: Пользователь ЧУВСТВУЕТ глубину, не читая "ГЛУБОКО" или "ПОВЕРХНОСТНО"
#
# 4 измерения накапливаются для создания ощущения интенсивности:

DEPTH_TYPOGRAPHY = {
    "Foundation": {
        "font_weight": 400,        # Light — лёгкость, доступность
        "line_height": 1.8,        # Много воздуха — разрешение дышать
        "letter_spacing": "+0.5px", # Открытый — приглашающий
        "question_spacing": "2em",  # Группировка — коллективное ощущение
    },
    "Exploration": {
        "font_weight": 500,        # Medium — требует внимания
        "line_height": 1.6,        # Умеренное сжатие
        "letter_spacing": "0px",   # Нейтральный
        "question_spacing": "2.5em", # Индивидуальный выбор
    },
    "Integration": {
        "font_weight": 600,        # Semi-bold — вес, интенсивность
        "line_height": 1.4,        # Плотно — глубокий фокус, меньше escape room
        "letter_spacing": "-0.2px", # Сжатый — плотность, серьёзность
        "question_spacing": "3-4em", # Изоляция — интроспекция, уединение
    }
}

# Психология: Тяжелее шрифт + плотнее текст = когнитивная нагрузка ощущается
# без слов. Пользователь замедляется естественно на Integration.

# Дополнительное измерение: фоновая текстура (subtle, почти незаметная)
DEPTH_BACKGROUND = {
    "Foundation": "pure_white",           # Чистый белый — лёгкость
    "Exploration": "1%_gray_pattern",     # Едва заметный паттерн — вес
    "Integration": "2%_gray_halftone",    # Subtle halftone — глубина
}
# Мозг регистрирует "больше веса впереди" без осознания паттерна
```

### Функции

```python
def load_source():
    """Загрузить основной JSON с RU текстами"""
    with open(SOURCE_JSON) as f:
        return json.load(f)

def load_translations(lang):
    """Загрузить переводы для языка"""
    if lang == "ru":
        return None  # Используем оригинал

    return {
        "questions": load_json(f"{TRANSLATIONS_DIR}/questions_{lang}.json"),
        "blocks": load_json(f"{TRANSLATIONS_DIR}/blocks_{lang}.json"),
        "programs": load_json(f"{TRANSLATIONS_DIR}/programs_{lang}.json")
    }

def get_text(item, field, translations, item_type):
    """Получить текст на нужном языке"""
    if translations is None:
        return item[field]

    item_id = item["id"]
    trans_dict = translations[item_type]

    if item_id in trans_dict:
        if isinstance(trans_dict[item_id], dict):
            return trans_dict[item_id].get(field, item[field])
        return trans_dict[item_id]

    return item[field]  # Fallback на оригинал

def load_template(lang, template_name):
    """Загрузить шаблон на нужном языке"""
    path = f"{TEMPLATES_DIR}/{lang}/{template_name}.md"
    with open(path) as f:
        return f.read()
```

### Генерация Книги 1

```python
def generate_book1(lang):
    """Книга 1: 29 программ самопознания"""

    data = load_source()
    trans = load_translations(lang)

    output = []

    # 1. Вводная часть
    output.append(load_template(lang, "intro"))
    output.append("\n---\n")

    # 2. Главы по программам
    for program in data["programs"]:

        # Заголовок главы
        program_name = get_text(program, "name", trans, "programs")
        output.append(f"\n# {program_name}\n")

        # Кластеры (уже отсортированы по sequence)
        for block in program["blocks"]:

            block_name = get_text(block, "name", trans, "blocks")
            block_desc = get_text(block, "description", trans, "blocks")
            block_type = block["type"]

            time = DEPTH_TIME[block_type]
            typo = DEPTH_TYPOGRAPHY[block_type]

            # Заголовок кластера (без emoji — глубина через typography)
            output.append(f"\n## {block_name}\n")
            output.append(f"*{block_desc}*\n")
            output.append(f"\n~{time} мин\n")  # Время без emoji — минимализм

            # Предупреждение для Integration
            if block_type == "Integration":
                warning = load_template(lang, "warnings")
                output.append(f"\n{warning}\n")

            output.append("\n---\n")

            # Вопросы
            for i, question in enumerate(block["questions"], 1):
                q_text = get_text(question, "text", trans, "questions")
                output.append(f"\n**{i}.** {q_text}\n")
                output.append("\n_________________________________\n")
                output.append("_________________________________\n")
                output.append("_________________________________\n")

    # 3. Заключение
    output.append("\n---\n")
    output.append(load_template(lang, "conclusion"))

    # Сохранение
    output_path = f"{OUTPUT_DIR}/{lang}/book1_programs.md"
    with open(output_path, "w") as f:
        f.write("\n".join(output))
```

### Генерация Книги 2

```python
def generate_book2(lang):
    """Книга 2: Путь в глубину"""

    data = load_source()
    trans = load_translations(lang)

    # 1. Собрать все кластеры
    all_blocks = []
    for program in data["programs"]:
        for block in program["blocks"]:
            all_blocks.append({
                "block": block,
                "program": program
            })

    # 2. Разбить по типам
    foundation = [b for b in all_blocks if b["block"]["type"] == "Foundation"]
    exploration = [b for b in all_blocks if b["block"]["type"] == "Exploration"]
    integration = [b for b in all_blocks if b["block"]["type"] == "Integration"]

    # 3. Чередовать темы внутри каждой группы
    foundation = interleave_by_program(foundation)
    exploration = interleave_by_program(exploration)
    integration = interleave_by_program(integration)

    output = []

    # 4. Вводная часть
    output.append(load_template(lang, "intro"))
    output.append("\n---\n")

    # 5. Часть 1: Foundation
    # Визуальный стиль: light weight, много воздуха, открытый tracking
    output.append("\n# ЧАСТЬ 1: Пробуждение\n")
    output.append("*Мягкое начало. Здесь безопасно исследовать.*\n")
    output.append("\n---\n")

    for item in foundation:
        output.append(format_block(item, trans, lang, "Foundation"))

    # 6. Часть 2: Exploration
    # Визуальный стиль: medium weight, умеренное сжатие
    output.append("\n# ЧАСТЬ 2: Погружение\n")
    output.append("*Глубже. Здесь может быть некомфортно — это нормально.*\n")
    output.append("\n---\n")

    for item in exploration:
        output.append(format_block(item, trans, lang, "Exploration"))

    # 7. Часть 3: Integration
    # Визуальный стиль: semi-bold, плотный, изолированные вопросы
    output.append("\n# ЧАСТЬ 3: Интеграция\n")
    output.append("*Глубинная работа. Убедитесь что вы в безопасном месте.*\n")
    output.append(load_template(lang, "warnings"))
    output.append("\n---\n")

    for item in integration:
        output.append(format_block(item, trans, lang, "Integration"))

    # 8. Заключение
    output.append("\n---\n")
    output.append(load_template(lang, "conclusion"))

    # Сохранение
    output_path = f"{OUTPUT_DIR}/{lang}/book2_depth.md"
    with open(output_path, "w") as f:
        f.write("\n".join(output))


def interleave_by_program(blocks):
    """Чередовать кластеры по программам"""
    # Группируем по программам
    by_program = {}
    for b in blocks:
        prog_id = b["program"]["id"]
        if prog_id not in by_program:
            by_program[prog_id] = []
        by_program[prog_id].append(b)

    # Чередуем
    result = []
    program_lists = list(by_program.values())
    max_len = max(len(lst) for lst in program_lists)

    for i in range(max_len):
        for lst in program_lists:
            if i < len(lst):
                result.append(lst[i])

    return result


def format_block(item, trans, lang, depth_level):
    """Форматировать кластер для вывода с учётом глубины"""
    block = item["block"]
    program = item["program"]

    program_name = get_text(program, "name", trans, "programs")
    block_name = get_text(block, "name", trans, "blocks")
    block_desc = get_text(block, "description", trans, "blocks")

    time = DEPTH_TIME[depth_level]
    typo = DEPTH_TYPOGRAPHY[depth_level]

    lines = []

    # Контекст программы — через hierarchy, не brackets
    # Program name: lighter/smaller чем cluster name
    lines.append(f"\n### {program_name}\n")  # Меньший заголовок — контекст
    lines.append(f"\n## {block_name}\n")      # Основной заголовок кластера
    lines.append(f"*{block_desc}*\n")
    lines.append(f"\n~{time} мин\n")          # Время без emoji

    lines.append("\n---\n")

    # Вопросы с spacing по глубине
    # question_spacing применяется в LaTeX/CSS, здесь структура
    for i, question in enumerate(block["questions"], 1):
        q_text = get_text(question, "text", trans, "questions")
        lines.append(f"\n**{i}.** {q_text}\n")

        # Место для ответа — больше на глубоких уровнях
        if depth_level == "Foundation":
            lines.append("\n_________________________________\n")
            lines.append("_________________________________\n")
        elif depth_level == "Exploration":
            lines.append("\n_________________________________\n")
            lines.append("_________________________________\n")
            lines.append("_________________________________\n")
        else:  # Integration — максимум места
            lines.append("\n_________________________________\n")
            lines.append("_________________________________\n")
            lines.append("_________________________________\n")
            lines.append("_________________________________\n")

    return "\n".join(lines)
```

### Главная функция

```python
def main():
    """Генерация всех книг на всех языках"""

    for lang in LANGUAGES:
        print(f"Generating {lang}...")

        # Создать директории
        os.makedirs(f"{OUTPUT_DIR}/{lang}", exist_ok=True)

        # Генерация
        generate_book1(lang)
        generate_book2(lang)

        print(f"  ✅ book1_programs.md")
        print(f"  ✅ book2_depth.md")

    print("\nDone!")


if __name__ == "__main__":
    main()
```

---

## Формат файлов переводов

### questions_en.json
```json
{
  "q_podumat_o_zhiznib1q1": "Describe your state right now in three words",
  "q_podumat_o_zhiznib1q2": "What does your typical morning look like?",
  "q_podumat_o_zhiznib1q3": "What do you do on weekends when no one demands anything from you?"
}
```

### blocks_en.json
```json
{
  "block_podumat_o_zhiznizdes_i_seychas": {
    "name": "Here and Now",
    "description": "orientation"
  },
  "block_podumat_o_zhiznilyudi_ryadom": {
    "name": "People Around",
    "description": "ecosystem of influences"
  }
}
```

### programs_en.json
```json
{
  "program_podumat_o_zhizni": "Think About Life",
  "program_podumat_o_karere_ili_biznese": "Think About Career or Business"
}
```

---

## Checklist

### Подготовка
- [ ] Создать структуру директорий
- [ ] Написать шаблоны intro.md для RU
- [ ] Написать шаблоны warnings.md для RU
- [ ] Написать шаблоны conclusion.md для RU
- [ ] Перевести шаблоны на EN
- [ ] Перевести шаблоны на ES
- [ ] Создать questions_en.json (674 вопроса)
- [ ] Создать questions_es.json (674 вопроса)
- [ ] Создать blocks_en.json (190 кластеров)
- [ ] Создать blocks_es.json (190 кластеров)
- [ ] Создать programs_en.json (29 программ)
- [ ] Создать programs_es.json (29 программ)

### Генерация
- [ ] Написать generate_books.py
- [ ] Протестировать на RU
- [ ] Протестировать на EN
- [ ] Протестировать на ES
- [ ] Проверить форматирование
- [ ] Финальная генерация
