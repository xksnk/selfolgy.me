#!/usr/bin/env python3
"""
Анализ метаданных вопросов - статистика и распределение значений
"""

import json
from pathlib import Path
from collections import defaultdict, Counter
from typing import Dict, List, Any

def analyze_questions():
    """Анализ статистики метаданных"""

    project_root = Path(__file__).parent.parent
    questions_file = project_root / "intelligent_question_core" / "data" / "enhanced_questions.json"

    with open(questions_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
        questions = data.get("questions", [])

    total = len(questions)

    # Счетчики
    domains = Counter()
    depth_levels = Counter()
    energy_dynamics = Counter()
    journey_stages = Counter()
    recommended_models = Counter()

    # Статистика по psychology полям
    complexity_dist = defaultdict(int)
    emotional_weight_dist = defaultdict(int)
    insight_potential_dist = defaultdict(int)
    safety_level_dist = defaultdict(int)
    trust_requirement_dist = defaultdict(int)

    # Обработка
    for q in questions:
        cls = q.get("classification", {})
        psy = q.get("psychology", {})
        hints = q.get("processing_hints", {})

        domains[cls.get("domain")] += 1
        depth_levels[cls.get("depth_level")] += 1
        energy_dynamics[cls.get("energy_dynamic")] += 1
        journey_stages[cls.get("journey_stage")] += 1
        recommended_models[hints.get("recommended_model")] += 1

        complexity_dist[psy.get("complexity")] += 1
        emotional_weight_dist[psy.get("emotional_weight")] += 1
        insight_potential_dist[psy.get("insight_potential")] += 1
        safety_level_dist[psy.get("safety_level")] += 1
        trust_requirement_dist[psy.get("trust_requirement")] += 1

    # Вывод отчета
    print("=" * 80)
    print("📊 СТАТИСТИКА МЕТАДАННЫХ ВОПРОСОВ")
    print("=" * 80)
    print(f"\nВсего вопросов: {total}\n")

    # Domains
    print("🏷️  PSYCHOLOGICAL DOMAINS:")
    for domain, count in sorted(domains.items(), key=lambda x: x[1], reverse=True):
        pct = count / total * 100
        bar = "█" * int(pct / 2)
        print(f"  {domain:20s} {count:3d} ({pct:5.1f}%) {bar}")

    # Depth levels
    print("\n📊 DEPTH LEVELS:")
    depth_order = ["SURFACE", "CONSCIOUS", "EDGE", "SHADOW", "CORE"]
    for depth in depth_order:
        count = depth_levels.get(depth, 0)
        pct = count / total * 100 if count else 0
        bar = "█" * int(pct / 2)
        print(f"  {depth:20s} {count:3d} ({pct:5.1f}%) {bar}")

    # Energy dynamics
    print("\n⚡ ENERGY DYNAMICS:")
    for energy, count in sorted(energy_dynamics.items(), key=lambda x: x[1], reverse=True):
        pct = count / total * 100
        bar = "█" * int(pct / 2)
        print(f"  {energy:20s} {count:3d} ({pct:5.1f}%) {bar}")

    # Journey stages
    print("\n🚀 JOURNEY STAGES:")
    for stage, count in sorted(journey_stages.items(), key=lambda x: x[1], reverse=True):
        pct = count / total * 100
        bar = "█" * int(pct / 2)
        print(f"  {stage:20s} {count:3d} ({pct:5.1f}%) {bar}")

    # Recommended models
    print("\n🤖 RECOMMENDED AI MODELS:")
    for model, count in sorted(recommended_models.items(), key=lambda x: x[1], reverse=True):
        pct = count / total * 100
        bar = "█" * int(pct / 2)
        print(f"  {model:20s} {count:3d} ({pct:5.1f}%) {bar}")

    # Psychology metrics (1-5 scale)
    print("\n🧠 PSYCHOLOGY METRICS (1-5 scale):")

    metrics = [
        ("Complexity", complexity_dist),
        ("Emotional Weight", emotional_weight_dist),
        ("Insight Potential", insight_potential_dist),
        ("Safety Level", safety_level_dist),
        ("Trust Requirement", trust_requirement_dist)
    ]

    for name, dist in metrics:
        print(f"\n  {name}:")
        avg = sum(k * v for k, v in dist.items()) / total
        for i in range(1, 6):
            count = dist.get(i, 0)
            pct = count / total * 100
            bar = "█" * int(pct / 2)
            print(f"    {i}: {count:3d} ({pct:5.1f}%) {bar}")
        print(f"    Среднее: {avg:.2f}")

    # Выводы
    print("\n" + "=" * 80)
    print("🎯 КЛЮЧЕВЫЕ ВЫВОДЫ:")
    print("=" * 80)

    # Топ 3 домена
    top_domains = sorted(domains.items(), key=lambda x: x[1], reverse=True)[:3]
    print(f"\n✅ Топ-3 домена:")
    for domain, count in top_domains:
        print(f"   • {domain}: {count} вопросов ({count/total*100:.1f}%)")

    # Распределение по глубине
    deep_questions = depth_levels.get("SHADOW", 0) + depth_levels.get("CORE", 0)
    print(f"\n✅ Глубокие вопросы (SHADOW + CORE): {deep_questions} ({deep_questions/total*100:.1f}%)")

    # Баланс энергии
    heavy = energy_dynamics.get("HEAVY", 0)
    healing = energy_dynamics.get("HEALING", 0)
    print(f"\n✅ Энергетический баланс:")
    print(f"   • HEAVY (тяжелые): {heavy} ({heavy/total*100:.1f}%)")
    print(f"   • HEALING (исцеляющие): {healing} ({healing/total*100:.1f}%)")
    if healing > 0:
        print(f"   • Соотношение: {heavy/healing:.2f} : 1")
    else:
        print(f"   • ⚠️ НЕТ вопросов с energy_dynamic=HEALING!")

    # AI модели
    claude_count = recommended_models.get("claude-3.5-sonnet", 0)
    print(f"\n✅ Рекомендации AI моделей:")
    print(f"   • Claude Sonnet: {claude_count} ({claude_count/total*100:.1f}%) - для сложных вопросов")
    print(f"   • GPT-4o: {recommended_models.get('gpt-4o', 0)} ({recommended_models.get('gpt-4o', 0)/total*100:.1f}%)")
    print(f"   • GPT-4o-mini: {recommended_models.get('gpt-4o-mini', 0)} ({recommended_models.get('gpt-4o-mini', 0)/total*100:.1f}%)")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    analyze_questions()
