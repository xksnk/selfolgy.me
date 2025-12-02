#!/usr/bin/env python3
"""
Генератор книг Selfology
Создаёт две книги на основе базы вопросов:
- Книга 1: 29 программ самопознания (по темам)
- Книга 2: Путь в глубину (от простого к сложному)
"""

import json
import os
from pathlib import Path
from datetime import datetime

# Пути
BASE_DIR = Path(__file__).parent.parent.parent.parent
SOURCE_JSON = BASE_DIR / "intelligent_question_core/data/selfology_programs_v2.json"
TRANSLATIONS_DIR = BASE_DIR / "intelligent_question_core/data/translations"
TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
OUTPUT_DIR = Path(__file__).parent.parent / "exports"

# Конфигурация
LANGUAGES = ["ru"]  # Пока только русский, потом добавим en, es

DEPTH_LABELS = {
    "ru": {
        "Foundation": "ПОВЕРХНОСТЬ",
        "Exploration": "ИССЛЕДОВАНИЕ",
        "Integration": "ГЛУБИНА"
    },
    "en": {
        "Foundation": "SURFACE",
        "Exploration": "EXPLORATION",
        "Integration": "DEPTH"
    },
    "es": {
        "Foundation": "SUPERFICIE",
        "Exploration": "EXPLORACIÓN",
        "Integration": "PROFUNDIDAD"
    }
}

DEPTH_TIME = {
    "Foundation": "5–10",
    "Exploration": "10–20",
    "Integration": "15–30"
}

DEPTH_NAMES = {
    "ru": {
        "Foundation": "Поверхность",
        "Exploration": "Исследование",
        "Integration": "Глубина"
    }
}

PART_DESCRIPTIONS = {
    "ru": {
        "Foundation": "Разминка для внутреннего исследователя. Лёгкие вопросы, чтобы войти в контакт с собой.",
        "Exploration": "Опускаемся глубже. Здесь начинается настоящая работа. Может быть некомфортно — это нормально.",
        "Integration": "Глубинная работа. Эти вопросы требуют сил, времени и безопасного пространства."
    }
}


def escape_latex(text):
    """Экранировать специальные символы LaTeX и убрать emoji"""
    if not text:
        return text

    # Убираем emoji и специальные символы
    cleanup = [
        ('→', '—'),  # Стрелка на тире
        ('🤖', ''),   # Робот
        ('🚨', ''),   # Сирена
        ('🌱', ''),   # Росток
        ('🔍', ''),   # Лупа
        ('💎', ''),   # Алмаз
        ('⏱️', ''),   # Таймер
        ('⚠️', ''),   # Предупреждение
    ]
    for old, new in cleanup:
        text = text.replace(old, new)

    # Порядок важен - & должен быть первым
    replacements = [
        ('\\', '\\textbackslash{}'),
        ('&', '\\&'),
        ('%', '\\%'),
        ('$', '\\$'),
        ('#', '\\#'),
        ('_', '\\_'),
        ('{', '\\{'),
        ('}', '\\}'),
        ('~', '\\textasciitilde{}'),
        ('^', '\\textasciicircum{}'),
    ]
    for old, new in replacements:
        text = text.replace(old, new)
    return text


def load_source():
    """Загрузить основной JSON"""
    with open(SOURCE_JSON, "r", encoding="utf-8") as f:
        return json.load(f)


def load_translations(lang):
    """Загрузить переводы для языка"""
    if lang == "ru":
        return None  # Используем оригинал

    translations = {}
    for file_type in ["questions", "blocks", "programs"]:
        path = TRANSLATIONS_DIR / f"{file_type}_{lang}.json"
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                translations[file_type] = json.load(f)
        else:
            translations[file_type] = {}

    return translations


def get_text(item, field, translations, item_type):
    """Получить текст на нужном языке"""
    if translations is None:
        return item.get(field, "")

    item_id = item.get("id", "")
    trans_dict = translations.get(item_type, {})

    if item_id in trans_dict:
        if isinstance(trans_dict[item_id], dict):
            return trans_dict[item_id].get(field, item.get(field, ""))
        return trans_dict[item_id]

    return item.get(field, "")  # Fallback на оригинал


def load_template(lang, template_name):
    """Загрузить шаблон на нужном языке"""
    path = TEMPLATES_DIR / lang / f"{template_name}.md"
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    return ""


def format_question_block(questions, translations, start_num=1):
    """Форматировать блок вопросов — компактно, без места для ответа"""
    lines = []
    for i, question in enumerate(questions, start_num):
        q_text = get_text(question, "text", translations, "questions")
        q_text = escape_latex(q_text)
        lines.append(f"**{i}.** {q_text}")
        lines.append("")
    return "\n".join(lines)


def generate_book1(lang):
    """
    Книга 1: 29 программ самопознания
    Структура: главы по программам, внутри — кластеры по порядку
    """
    print(f"  Генерирую Книгу 1 ({lang})...")

    data = load_source()
    trans = load_translations(lang)

    output = []

    # Метаданные для Pandoc
    output.append("---")
    output.append("title: 29 программ самопознания")
    output.append("subtitle: Книга рефлексии")
    output.append("author: Selfology")
    output.append(f"date: {datetime.now().strftime('%Y')}")
    output.append("lang: ru")
    output.append("---")
    output.append("")

    # Вводная часть
    output.append(load_template(lang, "intro"))
    output.append("")
    output.append("\\newpage")
    output.append("")

    # Главы по программам
    for prog_idx, program in enumerate(data["programs"], 1):
        program_name = escape_latex(get_text(program, "name", trans, "programs"))

        output.append(f"# {prog_idx}. {program_name}")
        output.append("")

        # Кластеры
        for block in program["blocks"]:
            block_name = escape_latex(get_text(block, "name", trans, "blocks"))
            block_desc = escape_latex(get_text(block, "description", trans, "blocks"))
            block_type = block.get("type", "Foundation")

            depth_label = DEPTH_LABELS.get(lang, {}).get(block_type, "")
            time = DEPTH_TIME.get(block_type, "10")

            # Компактный заголовок: УРОВЕНЬ \n Название — описание — время
            # Используем чистый LaTeX для samepage (markdown внутри не работает)
            desc_time = f" — {block_desc}" if block_desc else ""
            output.append("\\begin{samepage}")
            output.append(f"\\subsection{{{depth_label}}}")
            output.append(f"\\section{{{block_name}{desc_time} — \\textasciitilde{{}}{time} мин}}")
            output.append("\\end{samepage}")
            output.append("")

            # Предупреждение для Integration
            if block_type == "Integration":
                output.append(load_template(lang, "warnings"))
                output.append("")

            # Вопросы
            output.append(format_question_block(block["questions"], trans))
            output.append("")

        output.append("\\newpage")
        output.append("")

    # Заключение
    output.append(load_template(lang, "conclusion"))

    # Сохранение
    output_path = OUTPUT_DIR / lang / "book1_programs.md"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(output))

    print(f"    ✅ {output_path}")
    return output_path


def interleave_by_program(blocks):
    """Чередовать кластеры по программам для разнообразия"""
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
    if not program_lists:
        return result

    max_len = max(len(lst) for lst in program_lists)

    for i in range(max_len):
        for lst in program_lists:
            if i < len(lst):
                result.append(lst[i])

    return result


def generate_book2(lang):
    """
    Книга 2: Путь в глубину
    Структура: 3 части по глубине, кластеры чередуются по темам
    """
    print(f"  Генерирую Книгу 2 ({lang})...")

    data = load_source()
    trans = load_translations(lang)

    # Собрать все кластеры
    all_blocks = []
    for program in data["programs"]:
        for block in program["blocks"]:
            all_blocks.append({
                "block": block,
                "program": program
            })

    # Разбить по типам
    foundation = [b for b in all_blocks if b["block"].get("type") == "Foundation"]
    exploration = [b for b in all_blocks if b["block"].get("type") == "Exploration"]
    integration = [b for b in all_blocks if b["block"].get("type") == "Integration"]

    # Чередовать темы
    foundation = interleave_by_program(foundation)
    exploration = interleave_by_program(exploration)
    integration = interleave_by_program(integration)

    output = []

    # Метаданные
    output.append("---")
    output.append("title: Путь в глубину")
    output.append("subtitle: От поверхности к сути")
    output.append("author: Selfology")
    output.append(f"date: {datetime.now().strftime('%Y')}")
    output.append("lang: ru")
    output.append("---")
    output.append("")

    # Вводная часть
    output.append(load_template(lang, "intro"))
    output.append("")
    output.append("\\newpage")
    output.append("")

    # Три части
    parts = [
        ("Foundation", foundation, "ЧАСТЬ 1"),
        ("Exploration", exploration, "ЧАСТЬ 2"),
        ("Integration", integration, "ЧАСТЬ 3")
    ]

    for block_type, blocks, part_name in parts:
        depth_label = DEPTH_LABELS.get(lang, {}).get(block_type, "")
        depth_name = DEPTH_NAMES.get(lang, {}).get(block_type, block_type)
        description = PART_DESCRIPTIONS.get(lang, {}).get(block_type, "")

        output.append(f"# {part_name}: {depth_label}")
        output.append("")
        output.append(f"*{description}*")
        output.append("")

        # Предупреждение для Integration
        if block_type == "Integration":
            output.append(load_template(lang, "warnings"))
            output.append("")

        output.append("---")
        output.append("")

        # Кластеры
        for item in blocks:
            block = item["block"]
            program = item["program"]

            program_name = escape_latex(get_text(program, "name", trans, "programs"))
            block_name = escape_latex(get_text(block, "name", trans, "blocks"))
            block_desc = escape_latex(get_text(block, "description", trans, "blocks"))

            time = DEPTH_TIME.get(block_type, "10")

            # Компактный заголовок с samepage (чистый LaTeX)
            desc_time = f" — {block_desc}" if block_desc else ""
            output.append("\\begin{samepage}")
            output.append(f"\\section{{[{program_name}] {block_name}{desc_time} — \\textasciitilde{{}}{time} мин}}")
            output.append("\\end{samepage}")
            output.append("")

            # Вопросы
            output.append(format_question_block(block["questions"], trans))
            output.append("")

        output.append("\\newpage")
        output.append("")

    # Заключение
    output.append(load_template(lang, "conclusion"))

    # Сохранение
    output_path = OUTPUT_DIR / lang / "book2_depth.md"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(output))

    print(f"    ✅ {output_path}")
    return output_path


def main():
    """Генерация всех книг"""
    print("=" * 50)
    print("Генератор книг Selfology")
    print("=" * 50)
    print()

    for lang in LANGUAGES:
        print(f"Язык: {lang.upper()}")

        # Создать директории
        (OUTPUT_DIR / lang).mkdir(parents=True, exist_ok=True)

        # Генерация
        book1_path = generate_book1(lang)
        book2_path = generate_book2(lang)

        print()

    print("=" * 50)
    print("Готово!")
    print()
    print("Следующий шаг — конвертация в PDF:")
    print("  python generate_books.py --pdf")
    print("=" * 50)


if __name__ == "__main__":
    main()
