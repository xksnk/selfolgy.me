#!/usr/bin/env python3
"""
Простейший способ объединить вопросы

ИНСТРУКЦИЯ:
1. Запусти скрипт: python3 scripts/simple_paste_merge.py
2. Вставь JSON когда попросит
3. Нажми Ctrl+D когда закончишь вставлять
4. Повтори для всех 13 блоков
"""

import json
import sys
from pathlib import Path

BLOCKS = [
    ("EDGE", 75),
    ("SHADOW", 40),
    ("CORE", 25),
    ("HEALING", 60),
    ("EMOTIONS", 50),
    ("RELATIONSHIPS", 50),
    ("GOALS", 50),
    ("FEARS", 30),
    ("VALUES", 30),
    ("ENTRY", 50),
    ("DEEPENING", 100),
    ("INTEGRATING", 50),
    ("TRANSFORMING", 30)
]

def collect_block(block_name, expected_count):
    """Собрать один блок вопросов через stdin"""

    print(f"\n{'='*70}")
    print(f"📋 БЛОК: {block_name} (ожидается ~{expected_count} вопросов)")
    print(f"{'='*70}")
    print(f"\n1. Прокрути терминал вверх")
    print(f"2. Найди Task output: 'Generate {block_name} questions'")
    print(f"3. Скопируй ВЕСЬ JSON array (от [ до ])")
    print(f"4. Вставь ЗДЕСЬ и нажми Ctrl+D\n")
    print(f"Вставляй JSON:")
    print(f"-"*70)

    # Читаем из stdin
    json_text = sys.stdin.read()

    try:
        questions = json.loads(json_text)

        if not isinstance(questions, list):
            print(f"\n❌ Ошибка: ожидался JSON array")
            return None

        print(f"\n✅ Получено: {len(questions)} вопросов")

        if len(questions) != expected_count:
            print(f"⚠️ Внимание: ожидалось {expected_count}, получено {len(questions)}")
            confirm = input(f"Продолжить? (y/n): ")
            if confirm.lower() != 'y':
                return None

        return questions

    except json.JSONDecodeError as e:
        print(f"\n❌ Ошибка парсинга JSON: {e}")
        return None


def main():
    print("🚀 Простой Merge - Вставка JSON из терминала")
    print("="*70)

    project_root = Path(__file__).parent.parent
    blocks_dir = project_root / "intelligent_question_core" / "data" / "generated_blocks"
    blocks_dir.mkdir(parents=True, exist_ok=True)

    all_questions = []
    blocks_saved = {}

    for block_name, expected_count in BLOCKS:
        questions = collect_block(block_name, expected_count)

        if questions is None:
            print(f"\n❌ Пропуск блока {block_name}")
            continue

        # Сохраняем блок
        block_file = blocks_dir / f"{block_name}.json"
        with open(block_file, 'w', encoding='utf-8') as f:
            json.dump(questions, f, indent=2, ensure_ascii=False)

        all_questions.extend(questions)
        blocks_saved[block_name] = len(questions)

        print(f"💾 Сохранено: {block_file}")

    # Финальное объединение
    print(f"\n{'='*70}")
    print(f"📊 ИТОГО")
    print(f"{'='*70}")

    for block_name, count in blocks_saved.items():
        print(f"  ✅ {block_name}: {count} вопросов")

    print(f"\n🎯 Всего: {len(all_questions)} вопросов")

    if all_questions:
        # Сохраняем объединенный файл
        output_file = project_root / "intelligent_question_core" / "data" / "generated_questions_v2.json"

        result = {
            "metadata": {
                "version": "2.0",
                "generation_date": "2025-10-06",
                "total_questions": len(all_questions)
            },
            "questions": all_questions
        }

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        print(f"\n✅ Объединенный файл: {output_file}")
        print(f"\nСледующий шаг:")
        print(f"  python3 scripts/validate_questions_completeness.py")


if __name__ == "__main__":
    main()
