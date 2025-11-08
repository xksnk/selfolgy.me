#!/usr/bin/env python3
"""
Финальный скрипт объединения всех сгенерированных вопросов

Читает JSON файлы из generated_blocks/ и объединяет их
"""

import json
from pathlib import Path
from collections import Counter
from datetime import datetime


def main():
    project_root = Path(__file__).parent.parent
    blocks_dir = project_root / "intelligent_question_core" / "data" / "generated_blocks"

    print("🚀 Объединение сгенерированных вопросов\n")

    # Список файлов блоков
    block_files = sorted(blocks_dir.glob("*.json"))

    if not block_files:
        print(f"❌ Нет JSON файлов в {blocks_dir}")
        print(f"\n💡 Создай файлы блоков:")
        print(f"  01_EDGE.json - 75 questions")
        print(f"  02_SHADOW.json - 40 questions")
        print(f"  и т.д.")
        return

    # Объединяем все блоки
    all_questions = []

    print(f"📖 Найдено блоков: {len(block_files)}\n")

    for block_file in block_files:
        try:
            with open(block_file, 'r', encoding='utf-8') as f:
                questions = json.load(f)

            if isinstance(questions, list):
                all_questions.extend(questions)
                print(f"  ✅ {block_file.name}: {len(questions)} вопросов")
            else:
                print(f"  ⚠️ {block_file.name}: неверный формат")

        except Exception as e:
            print(f"  ❌ {block_file.name}: ошибка - {e}")

    if not all_questions:
        print("\n❌ Нет вопросов для объединения!")
        return

    print(f"\n📊 Всего объединено: {len(all_questions)} вопросов")

    # Исправление domain
    domain_mapping = {
        "patterns": "IDENTITY",
        "past_present": "PAST",
        "contradictions": "IDENTITY",
        "lessons": "GROWTH",
        "evolution": "GROWTH"
    }

    fixed_count = 0
    for q in all_questions:
        cls = q.get("classification", {})
        domain = cls.get("domain")
        if domain in domain_mapping:
            cls["domain"] = domain_mapping[domain]
            fixed_count += 1

    if fixed_count > 0:
        print(f"🔧 Исправлено нестандартных доменов: {fixed_count}")

    # Статистика
    stats = {}
    for field in ["domain", "depth_level", "energy_dynamic", "journey_stage"]:
        counter = Counter()
        for q in all_questions:
            cls = q.get("classification", {})
            counter[cls.get(field)] += 1
        stats[field] = dict(counter)

    # Метаданные
    result = {
        "metadata": {
            "version": "2.0",
            "title": "AI Generated Questions - Missing Categories",
            "generation_date": datetime.now().strftime("%Y-%m-%d"),
            "generation_model": "claude-opus-4",
            "total_questions": len(all_questions),
            "categories": {
                "depth_levels": stats.get("depth_level", {}),
                "energy_dynamics": stats.get("energy_dynamic", {}),
                "journey_stages": stats.get("journey_stage", {}),
                "domains": stats.get("domain", {})
            }
        },
        "questions": all_questions
    }

    # Сохранение
    output_file = project_root / "intelligent_question_core" / "data" / "generated_questions_v2.json"

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Сохранено в: {output_file}")
    print(f"📊 Размер: {output_file.stat().st_size / 1024:.1f} KB")

    # Статистика
    print("\n" + "="*60)
    print("📊 СТАТИСТИКА")
    print("="*60)

    for category, data in stats.items():
        print(f"\n{category.upper()}:")
        for key, count in sorted(data.items(), key=lambda x: x[1], reverse=True):
            pct = count / len(all_questions) * 100
            print(f"  {key:20s} {count:3d} ({pct:5.1f}%)")

    print("\n" + "="*60)


if __name__ == "__main__":
    main()
