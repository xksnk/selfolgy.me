#!/usr/bin/env python3
"""
Экстрактор вопросов из Task outputs

ИНСТРУКЦИЯ:
1. Прокрути терминал вверх к Task outputs
2. Найди каждый output (помечен как "Task: Generate ... questions")
3. Скопируй JSON array из output
4. Вставь ниже в соответствующую переменную

Формат каждого блока:
BLOCK_NAME = [
  {"id": "...", "text": "...", ...},
  ...
]
"""

import json
from pathlib import Path
from collections import Counter

# ============================================================================
# ДАННЫЕ ОТ АГЕНТОВ - ВСТАВЬ СЮДА JSON ИЗ TASK OUTPUTS
# ============================================================================

# ПРИМЕР: Первый вопрос из EDGE блока для демонстрации формата
EXAMPLE_EDGE_QUESTION = {
    "id": "q_EDGE_001",
    "text": "Когда ты говоришь 'я в порядке', как часто это правда...",
    "source_system": "ai_generation_v2_2025",
    "classification": {
      "journey_stage": "DEEPENING",
      "depth_level": "EDGE",
      "domain": "EMOTIONS",
      "energy_dynamic": "PROCESSING"
    },
    "psychology": {
      "complexity": 3,
      "emotional_weight": 3,
      "insight_potential": 4,
      "safety_level": 3,
      "trust_requirement": 3
    },
    "original_metadata": {},
    "connections": [],
    "processing_hints": {
      "recommended_model": "claude-3.5-sonnet",
      "batch_compatible": True,
      "requires_context": False
    }
}

# TODO: Заполни эти списки данными из Task outputs

EDGE_QUESTIONS = []  # Task output 1 - 75 questions

SHADOW_QUESTIONS = []  # Task output 2 - 40 questions

CORE_QUESTIONS = []  # Task output 3 - 25 questions

HEALING_QUESTIONS = []  # Task output 4 - 60 questions

EMOTIONS_QUESTIONS = []  # Task output 5 - 50 questions

RELATIONSHIPS_QUESTIONS = []  # Task output 6 - 50 questions

GOALS_QUESTIONS = []  # Task output 7 - 50 questions

FEARS_QUESTIONS = []  # Task output 8 - 30 questions

VALUES_QUESTIONS = []  # Task output 9 - 30 questions

ENTRY_QUESTIONS = []  # Task output 10 - 50 questions

DEEPENING_QUESTIONS = []  # Task output 11 - 100 questions

INTEGRATING_QUESTIONS = []  # Task output 12 - 50 questions

TRANSFORMING_QUESTIONS = []  # Task output 13 - 30 questions

# ============================================================================
# АВТОМАТИЧЕСКАЯ ОБРАБОТКА
# ============================================================================

def save_blocks_to_files():
    """Сохранить каждый блок в отдельный JSON файл"""

    project_root = Path(__file__).parent.parent
    blocks_dir = project_root / "intelligent_question_core" / "data" / "generated_blocks"
    blocks_dir.mkdir(parents=True, exist_ok=True)

    blocks = {
        "01_EDGE.json": EDGE_QUESTIONS,
        "02_SHADOW.json": SHADOW_QUESTIONS,
        "03_CORE.json": CORE_QUESTIONS,
        "04_HEALING.json": HEALING_QUESTIONS,
        "05_EMOTIONS.json": EMOTIONS_QUESTIONS,
        "06_RELATIONSHIPS.json": RELATIONSHIPS_QUESTIONS,
        "07_GOALS.json": GOALS_QUESTIONS,
        "08_FEARS.json": FEARS_QUESTIONS,
        "09_VALUES.json": VALUES_QUESTIONS,
        "10_ENTRY.json": ENTRY_QUESTIONS,
        "11_DEEPENING.json": DEEPENING_QUESTIONS,
        "12_INTEGRATING.json": INTEGRATING_QUESTIONS,
        "13_TRANSFORMING.json": TRANSFORMING_QUESTIONS
    }

    print("💾 Сохранение блоков в файлы...\n")

    total_saved = 0

    for filename, questions in blocks.items():
        file_path = blocks_dir / filename

        if not questions:
            print(f"  ⚠️ {filename}: ПУСТОЙ - нужно заполнить в скрипте")
            continue

        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(questions, f, indent=2, ensure_ascii=False)

        total_saved += len(questions)
        print(f"  ✅ {filename}: {len(questions)} вопросов")

    print(f"\n📊 Всего сохранено: {total_saved} вопросов")

    return total_saved


def merge_all():
    """Объединить все блоки"""

    all_blocks = [
        EDGE_QUESTIONS, SHADOW_QUESTIONS, CORE_QUESTIONS, HEALING_QUESTIONS,
        EMOTIONS_QUESTIONS, RELATIONSHIPS_QUESTIONS, GOALS_QUESTIONS,
        FEARS_QUESTIONS, VALUES_QUESTIONS, ENTRY_QUESTIONS,
        DEEPENING_QUESTIONS, INTEGRATING_QUESTIONS, TRANSFORMING_QUESTIONS
    ]

    all_questions = []
    for block in all_blocks:
        all_questions.extend(block)

    # Fix domains
    domain_mapping = {
        "patterns": "IDENTITY",
        "past_present": "PAST",
        "contradictions": "IDENTITY",
        "lessons": "GROWTH",
        "evolution": "GROWTH"
    }

    for q in all_questions:
        cls = q.get("classification", {})
        domain = cls.get("domain")
        if domain in domain_mapping:
            cls["domain"] = domain_mapping[domain]

    # Статистика
    stats = {
        "domains": Counter(),
        "depth_levels": Counter(),
        "energy_dynamics": Counter(),
        "journey_stages": Counter()
    }

    for q in all_questions:
        cls = q.get("classification", {})
        stats["domains"][cls.get("domain")] += 1
        stats["depth_levels"][cls.get("depth_level")] += 1
        stats["energy_dynamics"][cls.get("energy_dynamic")] += 1
        stats["journey_stages"][cls.get("journey_stage")] += 1

    # Создаем финальный файл
    result = {
        "metadata": {
            "version": "2.0",
            "title": "AI Generated Questions - Missing Categories",
            "generation_date": "2025-10-06",
            "generation_model": "claude-opus-4",
            "total_questions": len(all_questions),
            "categories": {
                "depth_levels": dict(stats["depth_levels"]),
                "energy_dynamics": dict(stats["energy_dynamics"]),
                "journey_stages": dict(stats["journey_stages"]),
                "domains": dict(stats["domains"])
            }
        },
        "questions": all_questions
    }

    project_root = Path(__file__).parent.parent
    output_file = project_root / "intelligent_question_core" / "data" / "generated_questions_v2.json"

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    return output_file, len(all_questions), stats


def main():
    print("🚀 Автоматическое объединение вопросов\n")
    print("="*70)

    # Проверка что данные заполнены
    all_blocks = [
        ("EDGE", EDGE_QUESTIONS),
        ("SHADOW", SHADOW_QUESTIONS),
        ("CORE", CORE_QUESTIONS),
        ("HEALING", HEALING_QUESTIONS),
        ("EMOTIONS", EMOTIONS_QUESTIONS),
        ("RELATIONSHIPS", RELATIONSHIPS_QUESTIONS),
        ("GOALS", GOALS_QUESTIONS),
        ("FEARS", FEARS_QUESTIONS),
        ("VALUES", VALUES_QUESTIONS),
        ("ENTRY", ENTRY_QUESTIONS),
        ("DEEPENING", DEEPENING_QUESTIONS),
        ("INTEGRATING", INTEGRATING_QUESTIONS),
        ("TRANSFORMING", TRANSFORMING_QUESTIONS)
    ]

    empty_blocks = [name for name, data in all_blocks if not data]

    if empty_blocks:
        print("⚠️ ВНИМАНИЕ: Следующие блоки ПУСТЫЕ:\n")
        for block in empty_blocks:
            print(f"  - {block}")
        print(f"\n📝 ИНСТРУКЦИЯ:")
        print(f"  1. Открой этот скрипт: scripts/extract_from_outputs.py")
        print(f"  2. Найди Task outputs выше в терминале")
        print(f"  3. Скопируй JSON array из каждого output")
        print(f"  4. Вставь в соответствующую переменную (EDGE_QUESTIONS = [...])")
        print(f"  5. Запусти скрипт заново")
        print(f"\n❌ Скрипт остановлен - нужно заполнить данные")
        return

    # Сохраняем в отдельные файлы
    print("ШАГ 1: Сохранение блоков в файлы...")
    print("-"*70)
    total_saved = save_blocks_to_files()

    # Объединяем всё
    print(f"\nШАГ 2: Объединение всех блоков...")
    print("-"*70)
    output_file, total_count, stats = merge_all()

    print(f"\n✅ Объединено: {total_count} вопросов")
    print(f"💾 Файл: {output_file}")

    # Статистика
    print(f"\nШАГ 3: Статистика")
    print("-"*70)

    for category, counter in stats.items():
        print(f"\n{category.upper().replace('_', ' ')}:")
        for key, count in sorted(counter.items(), key=lambda x: x[1], reverse=True):
            pct = count / total_count * 100
            print(f"  {str(key):20s} {count:3d} ({pct:5.1f}%)")

    print("\n" + "="*70)
    print("✅ ЗАВЕРШЕНО!")
    print("="*70)

    print(f"\nСледующий шаг:")
    print(f"  python3 scripts/validate_questions_completeness.py")


if __name__ == "__main__":
    main()
