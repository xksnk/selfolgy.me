#!/usr/bin/env python3
"""
Объединение сгенерированных вопросов в один файл
"""

import json
from pathlib import Path
from collections import Counter

# ВСТАВЬ СЮДА РЕЗУЛЬТАТЫ ОТ АГЕНТОВ (будет заполнено вручную)

# Блок 1: EDGE (75 вопросов)
EDGE_QUESTIONS = []  # JSON array from agent

# Блок 2: SHADOW (40 вопросов)
SHADOW_QUESTIONS = []  # JSON array from agent

# Блок 3: CORE (25 вопросов)
CORE_QUESTIONS = []  # JSON array from agent

# Блок 4: HEALING (60 вопросов)
HEALING_QUESTIONS = []  # JSON array from agent

# Блок 5: EMOTIONS (50 вопросов)
EMOTIONS_QUESTIONS = []  # JSON array from agent

# Блок 6: RELATIONSHIPS (50 вопросов)
RELATIONSHIPS_QUESTIONS = []  # JSON array from agent

# Блок 7: GOALS (50 вопросов)
GOALS_QUESTIONS = []  # JSON array from agent

# Блок 8: FEARS (30 вопросов)
FEARS_QUESTIONS = []  # JSON array from agent

# Блок 9: VALUES (30 вопросов)
VALUES_QUESTIONS = []  # JSON array from agent

# Блок 10: ENTRY (50 вопросов)
ENTRY_QUESTIONS = []  # JSON array from agent

# Блок 11: DEEPENING (100 вопросов)
DEEPENING_QUESTIONS = []  # JSON array from agent

# Блок 12: INTEGRATING (50 вопросов)
INTEGRATING_QUESTIONS = []  # JSON array from agent

# Блок 13: TRANSFORMING (30 вопросов)
TRANSFORMING_QUESTIONS = []  # JSON array from agent


def merge_all_questions():
    """Объединить все сгенерированные вопросы"""

    all_questions = []

    # Объединяем все блоки
    all_questions.extend(EDGE_QUESTIONS)
    all_questions.extend(SHADOW_QUESTIONS)
    all_questions.extend(CORE_QUESTIONS)
    all_questions.extend(HEALING_QUESTIONS)
    all_questions.extend(EMOTIONS_QUESTIONS)
    all_questions.extend(RELATIONSHIPS_QUESTIONS)
    all_questions.extend(GOALS_QUESTIONS)
    all_questions.extend(FEARS_QUESTIONS)
    all_questions.extend(VALUES_QUESTIONS)
    all_questions.extend(ENTRY_QUESTIONS)
    all_questions.extend(DEEPENING_QUESTIONS)
    all_questions.extend(INTEGRATING_QUESTIONS)
    all_questions.extend(TRANSFORMING_QUESTIONS)

    print(f"📊 Всего объединено: {len(all_questions)} вопросов")

    # Статистика
    domains = Counter()
    depth_levels = Counter()
    energy_dynamics = Counter()
    journey_stages = Counter()

    for q in all_questions:
        cls = q.get("classification", {})
        domains[cls.get("domain")] += 1
        depth_levels[cls.get("depth_level")] += 1
        energy_dynamics[cls.get("energy_dynamic")] += 1
        journey_stages[cls.get("journey_stage")] += 1

    # Создаем финальную структуру
    result = {
        "metadata": {
            "version": "2.0",
            "title": "AI Generated Questions - Missing Categories",
            "generation_date": "2025-10-06",
            "generation_model": "claude-opus-4",
            "total_questions": len(all_questions),
            "categories": {
                "depth_levels": dict(depth_levels),
                "energy_dynamics": dict(energy_dynamics),
                "journey_stages": dict(journey_stages),
                "domains": dict(domains)
            }
        },
        "questions": all_questions
    }

    # Сохраняем
    project_root = Path(__file__).parent.parent
    output_file = project_root / "intelligent_question_core" / "data" / "generated_questions_v2.json"

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"✅ Сохранено в: {output_file}")
    print(f"\n📊 Статистика:")
    print(f"  Depth Levels: {dict(depth_levels)}")
    print(f"  Energy Dynamics: {dict(energy_dynamics)}")
    print(f"  Journey Stages: {dict(journey_stages)}")
    print(f"  Domains: {dict(domains)}")

    return output_file


if __name__ == "__main__":
    merge_all_questions()
