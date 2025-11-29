#!/usr/bin/env python3
"""
Экспорт программ Selfology в форматы для книги/ревью.

Форматы:
- Markdown (для ревью и GitHub)
- HTML (для веб-превью)
- PDF-ready (markdown с разметкой для pandoc)

Опции:
- --format: markdown, html, all
- --filter: book_only, ai_only, both, all
- --output: output directory
- --single: export as single file vs separate files

Использование:
    python scripts/export_programs_book.py --format markdown --filter book_only
    python scripts/export_programs_book.py --format all --filter all
"""

import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any


# Пути
PROGRAMS_JSON = Path("intelligent_question_core/data/selfology_programs_v2.json")
OUTPUT_DIR = Path("exports/programs")


def load_programs() -> Dict[str, Any]:
    """Загрузить данные программ из JSON."""
    with open(PROGRAMS_JSON, "r", encoding="utf-8") as f:
        return json.load(f)


def filter_questions(questions: List[Dict], filter_type: str) -> List[Dict]:
    """Фильтровать вопросы по формату."""
    if filter_type == "all":
        return questions

    result = []
    for q in questions:
        fmt = q.get("format", "both")
        if filter_type == "book_only" and fmt in ("book_only", "both"):
            result.append(q)
        elif filter_type == "ai_only" and fmt in ("ai_only", "both"):
            result.append(q)
        elif filter_type == "both" and fmt == "both":
            result.append(q)
    return result


def format_block_type_emoji(block_type: str) -> str:
    """Эмодзи для типа блока."""
    emojis = {
        "Foundation": "🌱",
        "Exploration": "🔍",
        "Integration": "🎯"
    }
    return emojis.get(block_type, "📦")


def export_program_markdown(program: Dict, filter_type: str) -> str:
    """Экспортировать программу в Markdown."""
    lines = []

    # Заголовок программы
    lines.append(f"# {program['name']}\n")

    # Статистика
    total_questions = sum(len(b['questions']) for b in program['blocks'])
    lines.append(f"*Блоков: {len(program['blocks'])} | Вопросов: {total_questions}*\n")
    lines.append("---\n")

    question_num = 0
    for block in program['blocks']:
        questions = filter_questions(block['questions'], filter_type)
        if not questions:
            continue

        # Заголовок блока
        emoji = format_block_type_emoji(block['type'])
        lines.append(f"\n## {emoji} {block['name']}\n")
        if block.get('description'):
            lines.append(f"*{block['description']}*\n")
        lines.append("")

        # Вопросы
        for q in questions:
            question_num += 1
            # Маркер формата
            format_marker = ""
            if filter_type == "all":
                fmt = q.get("format", "both")
                if fmt == "book_only":
                    format_marker = " 📖"
                elif fmt == "ai_only":
                    format_marker = " 🤖"

            lines.append(f"{question_num}. {q['text']}{format_marker}")
            lines.append("")  # Пустая строка для записи ответа

    lines.append("\n---")
    lines.append(f"*Экспортировано: {datetime.now().strftime('%Y-%m-%d %H:%M')}*")

    return "\n".join(lines)


def export_program_html(program: Dict, filter_type: str) -> str:
    """Экспортировать программу в HTML."""
    html = []

    html.append("<!DOCTYPE html>")
    html.append("<html lang='ru'>")
    html.append("<head>")
    html.append("  <meta charset='UTF-8'>")
    html.append(f"  <title>Selfology: {program['name']}</title>")
    html.append("  <style>")
    html.append("""
    body {
      font-family: 'Georgia', serif;
      max-width: 800px;
      margin: 0 auto;
      padding: 40px 20px;
      line-height: 1.6;
      color: #333;
    }
    h1 {
      color: #2c3e50;
      border-bottom: 2px solid #3498db;
      padding-bottom: 10px;
    }
    h2 {
      color: #34495e;
      margin-top: 40px;
    }
    .block-foundation { border-left: 4px solid #27ae60; padding-left: 15px; }
    .block-exploration { border-left: 4px solid #3498db; padding-left: 15px; }
    .block-integration { border-left: 4px solid #9b59b6; padding-left: 15px; }
    .question {
      margin: 20px 0;
      padding: 15px;
      background: #f9f9f9;
      border-radius: 8px;
    }
    .question-number {
      font-weight: bold;
      color: #3498db;
    }
    .answer-space {
      margin-top: 10px;
      min-height: 80px;
      border: 1px dashed #ccc;
      border-radius: 4px;
      padding: 10px;
      background: white;
    }
    .format-book { color: #27ae60; font-size: 0.8em; }
    .format-ai { color: #e74c3c; font-size: 0.8em; }
    .stats {
      color: #7f8c8d;
      font-size: 0.9em;
      margin-bottom: 20px;
    }
    """)
    html.append("  </style>")
    html.append("</head>")
    html.append("<body>")

    # Заголовок
    html.append(f"<h1>Selfology: {program['name']}</h1>")

    total_questions = sum(len(b['questions']) for b in program['blocks'])
    html.append(f"<p class='stats'>Блоков: {len(program['blocks'])} | Вопросов: {total_questions}</p>")

    question_num = 0
    for block in program['blocks']:
        questions = filter_questions(block['questions'], filter_type)
        if not questions:
            continue

        # Блок
        block_class = f"block-{block['type'].lower()}"
        emoji = format_block_type_emoji(block['type'])
        html.append(f"<div class='{block_class}'>")
        html.append(f"<h2>{emoji} {block['name']}</h2>")
        if block.get('description'):
            html.append(f"<p><em>{block['description']}</em></p>")

        # Вопросы
        for q in questions:
            question_num += 1
            format_class = ""
            format_label = ""
            if filter_type == "all":
                fmt = q.get("format", "both")
                if fmt == "book_only":
                    format_class = "format-book"
                    format_label = " 📖"
                elif fmt == "ai_only":
                    format_class = "format-ai"
                    format_label = " 🤖"

            html.append("<div class='question'>")
            html.append(f"  <span class='question-number'>{question_num}.</span> {q['text']}")
            if format_label:
                html.append(f"  <span class='{format_class}'>{format_label}</span>")
            html.append("  <div class='answer-space'></div>")
            html.append("</div>")

        html.append("</div>")

    html.append(f"<p style='margin-top: 40px; color: #95a5a6; font-size: 0.8em;'>")
    html.append(f"Экспортировано: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    html.append("</p>")
    html.append("</body>")
    html.append("</html>")

    return "\n".join(html)


def export_all_programs_single(data: Dict, format_type: str, filter_type: str) -> str:
    """Экспортировать все программы в один файл."""
    if format_type == "markdown":
        lines = []
        lines.append("# Selfology: Книга Рефлексии\n")
        lines.append(f"*{data['metadata']['total_programs']} программ | "
                    f"{data['metadata']['total_blocks']} блоков | "
                    f"{data['metadata']['total_questions']} вопросов*\n")
        lines.append("---\n")
        lines.append("## Оглавление\n")

        for i, prog in enumerate(data['programs'], 1):
            q_count = sum(len(b['questions']) for b in prog['blocks'])
            lines.append(f"{i}. [{prog['name']}](#{prog['id']}) — {q_count} вопросов")

        lines.append("\n---\n")

        for prog in data['programs']:
            lines.append(f"\n<a name='{prog['id']}'></a>")
            lines.append(export_program_markdown(prog, filter_type))
            lines.append("\n---\n")

        return "\n".join(lines)

    elif format_type == "html":
        # Для HTML генерируем полную книгу
        html = []
        html.append("<!DOCTYPE html>")
        html.append("<html lang='ru'>")
        html.append("<head>")
        html.append("  <meta charset='UTF-8'>")
        html.append("  <title>Selfology: Книга Рефлексии</title>")
        html.append("  <style>")
        html.append("""
        body {
          font-family: 'Georgia', serif;
          max-width: 900px;
          margin: 0 auto;
          padding: 40px 20px;
          line-height: 1.6;
        }
        .program {
          page-break-before: always;
          margin-top: 60px;
        }
        .program:first-child { page-break-before: avoid; }
        h1 { color: #2c3e50; text-align: center; }
        h2 { color: #34495e; }
        .toc { background: #f5f5f5; padding: 20px; border-radius: 8px; }
        .toc a { color: #3498db; text-decoration: none; }
        .toc a:hover { text-decoration: underline; }
        """)
        html.append("  </style>")
        html.append("</head>")
        html.append("<body>")
        html.append("<h1>Selfology: Книга Рефлексии</h1>")
        html.append(f"<p style='text-align: center; color: #7f8c8d;'>"
                   f"{data['metadata']['total_programs']} программ | "
                   f"{data['metadata']['total_blocks']} блоков | "
                   f"{data['metadata']['total_questions']} вопросов</p>")

        # Оглавление
        html.append("<div class='toc'>")
        html.append("<h2>Оглавление</h2>")
        html.append("<ol>")
        for prog in data['programs']:
            q_count = sum(len(b['questions']) for b in prog['blocks'])
            html.append(f"<li><a href='#{prog['id']}'>{prog['name']}</a> — {q_count} вопросов</li>")
        html.append("</ol>")
        html.append("</div>")

        # Программы
        for prog in data['programs']:
            html.append(f"<div class='program' id='{prog['id']}'>")
            # Вставляем содержимое программы (без html/head/body)
            prog_html = export_program_html(prog, filter_type)
            # Извлекаем только body content
            start = prog_html.find("<body>") + 6
            end = prog_html.find("</body>")
            html.append(prog_html[start:end])
            html.append("</div>")

        html.append("</body>")
        html.append("</html>")
        return "\n".join(html)


def main():
    parser = argparse.ArgumentParser(description="Экспорт программ Selfology")
    parser.add_argument(
        "--format",
        choices=["markdown", "html", "all"],
        default="markdown",
        help="Формат экспорта"
    )
    parser.add_argument(
        "--filter",
        choices=["book_only", "ai_only", "both", "all"],
        default="all",
        help="Фильтр вопросов по формату"
    )
    parser.add_argument(
        "--output",
        type=str,
        default=str(OUTPUT_DIR),
        help="Директория для экспорта"
    )
    parser.add_argument(
        "--single",
        action="store_true",
        help="Экспортировать в один файл (вместо отдельных)"
    )

    args = parser.parse_args()

    # Загрузка данных
    print("📄 Загружаю данные...")
    data = load_programs()
    print(f"✅ Загружено {data['metadata']['total_programs']} программ")

    # Создание директории
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Формирование суффикса для имени файла
    filter_suffix = f"_{args.filter}" if args.filter != "all" else ""

    if args.single:
        # Экспорт в один файл
        print(f"📦 Экспортирую все программы в один файл...")

        if args.format in ("markdown", "all"):
            content = export_all_programs_single(data, "markdown", args.filter)
            filepath = output_dir / f"selfology_book{filter_suffix}.md"
            filepath.write_text(content, encoding="utf-8")
            print(f"✅ Сохранено: {filepath}")

        if args.format in ("html", "all"):
            content = export_all_programs_single(data, "html", args.filter)
            filepath = output_dir / f"selfology_book{filter_suffix}.html"
            filepath.write_text(content, encoding="utf-8")
            print(f"✅ Сохранено: {filepath}")

    else:
        # Экспорт отдельных файлов
        print(f"📦 Экспортирую {len(data['programs'])} программ...")

        for prog in data['programs']:
            prog_dir = output_dir / prog['id']
            prog_dir.mkdir(parents=True, exist_ok=True)

            if args.format in ("markdown", "all"):
                content = export_program_markdown(prog, args.filter)
                filepath = prog_dir / f"{prog['id']}{filter_suffix}.md"
                filepath.write_text(content, encoding="utf-8")

            if args.format in ("html", "all"):
                content = export_program_html(prog, args.filter)
                filepath = prog_dir / f"{prog['id']}{filter_suffix}.html"
                filepath.write_text(content, encoding="utf-8")

        print(f"✅ Экспортировано в: {output_dir}")

    # Статистика
    print(f"\n{'='*50}")
    print("📊 СТАТИСТИКА ЭКСПОРТА:")
    print(f"{'='*50}")
    print(f"Программ: {data['metadata']['total_programs']}")
    print(f"Блоков: {data['metadata']['total_blocks']}")
    print(f"Вопросов: {data['metadata']['total_questions']}")
    print(f"Формат: {args.format}")
    print(f"Фильтр: {args.filter}")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
