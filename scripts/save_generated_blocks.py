#!/usr/bin/env python3
"""
Сохранение сгенерированных блоков вопросов из Task outputs
Временный скрипт для ручного копирования данных из терминала
"""

import json
from pathlib import Path
from datetime import datetime

# Путь для сохранения
OUTPUT_DIR = Path("/home/ksnk/n8n-enterprise/projects/selfology/intelligent_question_core/data/generated_blocks")

# ВСТАВЬ СЮДА JSON ИЗ TASK OUTPUTS:
# После запуска скрипта, скопируй JSON массивы из терминала в соответствующие переменные

EMOTIONS_QUESTIONS = []  # Вставь сюда 50 вопросов из блока EMOTIONS

RELATIONSHIPS_QUESTIONS = []  # Вставь сюда 50 вопросов из блока RELATIONSHIPS

GOALS_QUESTIONS = []  # Вставь сюда 50 вопросов из блока GOALS

# Позже добавить:
# FEARS_QUESTIONS = []  # 30 вопросов
# VALUES_QUESTIONS = []  # 30 вопросов
# DEEPENING_QUESTIONS = []  # 100 вопросов
# INTEGRATING_QUESTIONS = []  # 50 вопросов
# TRANSFORMING_QUESTIONS = []  # 30 вопросов

def save_block(questions, block_name, block_number):
    """Сохранить блок в файл"""
    if not questions:
        print(f"⚠️  {block_name} - пустой, пропускаю")
        return

    filename = OUTPUT_DIR / f"{block_number}_{block_name}.json"

    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(questions, f, ensure_ascii=False, indent=2)

    print(f"✅ Сохранено: {filename} ({len(questions)} вопросов)")

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("📝 Сохранение сгенерированных блоков")
    print("=" * 50)

    # Первая партия (Opus)
    save_block(EMOTIONS_QUESTIONS, "EMOTIONS", "05")
    save_block(RELATIONSHIPS_QUESTIONS, "RELATIONSHIPS", "06")
    save_block(GOALS_QUESTIONS, "GOALS", "07")

    # Вторая партия (после смены модели на Sonnet)
    # save_block(FEARS_QUESTIONS, "FEARS", "08")
    # save_block(VALUES_QUESTIONS, "VALUES", "09")
    # save_block(DEEPENING_QUESTIONS, "DEEPENING", "11")
    # save_block(INTEGRATING_QUESTIONS, "INTEGRATING", "12")
    # save_block(TRANSFORMING_QUESTIONS, "TRANSFORMING", "13")

    print("\n✅ Готово!")
    print(f"📁 Файлы сохранены в: {OUTPUT_DIR}")

if __name__ == "__main__":
    main()