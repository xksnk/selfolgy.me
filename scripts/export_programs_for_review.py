#!/usr/bin/env python3
"""
Экспорт программ с вопросами в markdown для ревью.
Генерирует 39 файлов в review/programs/
"""
import json
from pathlib import Path
import re


def sanitize_filename(name: str) -> str:
    """Преобразовать название в безопасное имя файла"""
    # Заменить специальные символы
    name = re.sub(r'[/\\:*?"<>|→]', '_', name)
    # Убрать множественные пробелы и подчёркивания
    name = re.sub(r'[\s_]+', '_', name)
    return name.strip('_')


def main():
    print("📄 ЭКСПОРТ ПРОГРАММ ДЛЯ РЕВЬЮ\n")

    # Загрузить данные
    data_file = Path('prompts/all_programs_sequenced.json')
    if not data_file.exists():
        print(f"❌ Файл не найден: {data_file}")
        return

    with open(data_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    sequences = data.get('sequences', [])
    print(f"📊 Найдено программ: {len(sequences)}")

    # Создать директорию для экспорта
    output_dir = Path('review/programs')
    output_dir.mkdir(parents=True, exist_ok=True)

    # Загрузить метаданные программ для описаний
    programs_list_file = Path('prompts/all_programs_list.json')
    programs_meta = {}
    if programs_list_file.exists():
        with open(programs_list_file, 'r', encoding='utf-8') as f:
            programs_list = json.load(f)
            programs_meta = {p['name']: p for p in programs_list}

    # Экспортировать каждую программу
    for idx, seq in enumerate(sequences, 1):
        program_name = seq['program']
        questions = seq.get('questions_included', [])

        # Получить метаданные программы
        meta = programs_meta.get(program_name, {})
        description = meta.get('description', '')
        themes = meta.get('themes', [])
        domains = meta.get('domains', [])
        status = meta.get('status', 'unknown')
        priority = meta.get('priority', 0)

        # Сформировать имя файла с номером
        safe_name = sanitize_filename(program_name)
        filename = f"{idx:02d}_{safe_name}.md"
        filepath = output_dir / filename

        # Сформировать содержимое - только название и вопросы
        content = f"# {program_name}\n\n"

        # Вопросы с нумерацией (только текст)
        for q_idx, q in enumerate(questions, 1):
            q_text = q.get('text', '')
            content += f"{q_idx}. {q_text}\n"

        # Записать файл
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

        print(f"✅ {filename} — {len(questions)} вопросов")

    print(f"\n{'='*60}")
    print(f"📁 Файлы сохранены в: {output_dir.absolute()}")
    print(f"📊 Всего программ: {len(sequences)}")
    print(f"\n💡 Инструкция:")
    print("   1. Откройте файлы и исправьте вопросы")
    print("   2. Не меняйте формат (номер. текст)")
    print("   3. Не удаляйте строки с `q_...` (id вопроса)")
    print("   4. Верните исправленные файлы для импорта")


if __name__ == '__main__':
    main()
