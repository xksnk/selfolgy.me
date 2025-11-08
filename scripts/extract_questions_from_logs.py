#!/usr/bin/env python3
"""
Извлечение сгенерированных вопросов из Claude логов
"""

import json
import re
from pathlib import Path

# Путь к JSONL логу Claude
CLAUDE_LOG = Path.home() / ".claude/projects/-home-ksnk/b9bccf6c-f044-476f-ba23-4eb804006f02.jsonl"
OUTPUT_DIR = Path("/home/ksnk/n8n-enterprise/projects/selfology/intelligent_question_core/data/generated_blocks")

# Паттерны для поиска блоков вопросов
BLOCK_PATTERNS = {
    "EDGE": r'"id":\s*"q_EDGE_',
    "SHADOW": r'"id":\s*"q_SHADOW_',
    "CORE": r'"id":\s*"q_CORE_',
    "HEALING": r'"id":\s*"q_HEALING_',
    "EMOTIONS": r'"id":\s*"q_EMOTIONS_',
    "RELATIONSHIPS": r'"id":\s*"q_RELATIONSHIPS_',
    "GOALS": r'"id":\s*"q_GOALS_',
    "FEARS": r'"id":\s*"q_FEARS_',
    "VALUES": r'"id":\s*"q_VALUES_',
    "ENTRY": r'"id":\s*"q_ENTRY_',
    "DEEPENING": r'"id":\s*"q_DEEPENING_',
    "INTEGRATING": r'"id":\s*"q_INTEGRATING_',
    "TRANSFORMING": r'"id":\s*"q_TRANSFORMING_'
}

def extract_json_from_text(text):
    """Извлечь JSON массив из текста с markdown блоками"""
    # Паттерн для ```json ... ```
    match = re.search(r'```json\s*(\[.*?\])\s*```', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    # Попробовать найти просто JSON массив
    match = re.search(r'(\[\s*\{.*?\}\s*\])', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    return None

def extract_all_blocks():
    """Извлечь все блоки вопросов из логов"""

    if not CLAUDE_LOG.exists():
        print(f"❌ Лог файл не найден: {CLAUDE_LOG}")
        return {}

    print(f"📂 Читаю лог: {CLAUDE_LOG}")

    blocks_found = {}

    with open(CLAUDE_LOG, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            try:
                data = json.loads(line)

                # Проверяем только ответы от ассистента
                if data.get('type') != 'assistant':
                    continue

                message = data.get('message', {})
                content = message.get('content', [])

                # Ищем текстовые блоки с JSON
                for item in content:
                    if item.get('type') == 'text':
                        text = item.get('text', '')

                        # Проверяем какой блок это может быть
                        for block_name, pattern in BLOCK_PATTERNS.items():
                            if re.search(pattern, text):
                                questions = extract_json_from_text(text)
                                if questions:
                                    blocks_found[block_name] = questions
                                    print(f"✅ Найден блок {block_name}: {len(questions)} вопросов (строка {line_num})")
                                    break

            except json.JSONDecodeError:
                continue
            except Exception as e:
                print(f"⚠️  Ошибка на строке {line_num}: {e}")
                continue

    return blocks_found

def save_blocks(blocks):
    """Сохранить блоки в отдельные файлы"""

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    block_numbers = {
        "EDGE": "01",
        "SHADOW": "02",
        "CORE": "03",
        "HEALING": "04",
        "EMOTIONS": "05",
        "RELATIONSHIPS": "06",
        "GOALS": "07",
        "FEARS": "08",
        "VALUES": "09",
        "ENTRY": "10",
        "DEEPENING": "11",
        "INTEGRATING": "12",
        "TRANSFORMING": "13"
    }

    total_questions = 0

    for block_name, questions in blocks.items():
        block_num = block_numbers.get(block_name, "99")
        filename = OUTPUT_DIR / f"{block_num}_{block_name}.json"

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(questions, f, ensure_ascii=False, indent=2)

        total_questions += len(questions)
        print(f"💾 Сохранено: {filename} ({len(questions)} вопросов)")

    return total_questions

def main():
    print("🔍 Извлечение вопросов из Claude логов...\n")

    blocks = extract_all_blocks()

    if not blocks:
        print("\n❌ Вопросы не найдены в логах")
        return

    print(f"\n📊 Найдено блоков: {len(blocks)}")

    total = save_blocks(blocks)

    print(f"\n✅ Готово! Всего восстановлено: {total} вопросов")
    print(f"📁 Сохранено в: {OUTPUT_DIR}")

    # Показать статистику
    print("\n📈 Статистика:")
    for block_name, questions in sorted(blocks.items()):
        print(f"   {block_name:15} - {len(questions):3} вопросов")

if __name__ == "__main__":
    main()
