#!/usr/bin/env python3
"""
Финальное объединение всех вопросов:
- 943 вопроса из selfology_intelligent_core_enhanced.json
- 390 вопросов из 8 новых блоков (05-09, 11-13)
= 1333 вопроса (с проверкой дубликатов)
"""

import json
from pathlib import Path
from collections import Counter

# Пути
DATA_DIR = Path("/home/ksnk/n8n-enterprise/projects/selfology/intelligent_question_core/data")
BLOCKS_DIR = DATA_DIR / "generated_blocks"
ENHANCED_FILE = DATA_DIR / "selfology_intelligent_core_enhanced.json"
OUTPUT_FILE = DATA_DIR / "selfology_intelligent_core_complete.json"

def load_json(filepath):
    """Загрузить JSON файл"""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_json(data, filepath):
    """Сохранить JSON файл"""
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def check_duplicates(existing, new):
    """Проверить дубликаты по ID и тексту"""
    existing_ids = {q['id'] for q in existing}
    existing_texts = {q['text'].lower().strip() for q in existing}

    duplicates = []
    unique_new = []

    for question in new:
        q_id = question['id']
        q_text = question['text'].lower().strip()

        if q_id in existing_ids or q_text in existing_texts:
            duplicates.append(question)
        else:
            unique_new.append(question)

    return unique_new, duplicates

def analyze_distribution(questions):
    """Анализ распределения вопросов"""
    domains = Counter()
    depths = Counter()
    energies = Counter()
    stages = Counter()

    for q in questions:
        cls = q.get('classification', {})
        domains[cls.get('domain', 'UNKNOWN')] += 1
        depths[cls.get('depth_level', 'UNKNOWN')] += 1
        energies[cls.get('energy_dynamic', 'UNKNOWN')] += 1
        stages[cls.get('journey_stage', 'UNKNOWN')] += 1

    return {
        'domains': dict(domains),
        'depths': dict(depths),
        'energies': dict(energies),
        'stages': dict(stages)
    }

def main():
    print("🔄 Финальное объединение всех вопросов")
    print("=" * 60)

    # 1. Загрузить существующие 943 вопроса
    print("\n📖 Загружаю существующие вопросы...")
    enhanced_data = load_json(ENHANCED_FILE)

    # Файл имеет структуру {metadata: {...}, questions: [...]}
    if isinstance(enhanced_data, dict) and 'questions' in enhanced_data:
        existing_questions = enhanced_data['questions']
        print(f"   ✅ Загружено: {len(existing_questions)} вопросов из enhanced dataset")
    else:
        existing_questions = enhanced_data
        print(f"   ✅ Загружено: {len(existing_questions)} вопросов")

    # 2. Загрузить новые блоки
    print("\n📦 Загружаю новые блоки...")
    new_blocks = [
        "05_EMOTIONS.json",
        "06_RELATIONSHIPS.json",
        "07_GOALS.json",
        "08_FEARS.json",
        "09_VALUES.json",
        "11_DEEPENING.json",
        "12_INTEGRATING.json",
        "13_TRANSFORMING.json"
    ]

    new_questions = []
    for block_file in new_blocks:
        block_path = BLOCKS_DIR / block_file
        if block_path.exists():
            block_data = load_json(block_path)

            # Блоки имеют структуру {block_info: {...}, questions: [...]}
            if isinstance(block_data, dict) and 'questions' in block_data:
                questions = block_data['questions']
                new_questions.extend(questions)
                print(f"   ✅ {block_file}: {len(questions)} вопросов")
            else:
                new_questions.extend(block_data)
                print(f"   ✅ {block_file}: {len(block_data)} вопросов")
        else:
            print(f"   ⚠️  {block_file}: не найден")

    print(f"\n   📊 Всего новых вопросов: {len(new_questions)}")

    # 3. Проверка дубликатов
    print("\n🔍 Проверка дубликатов...")
    unique_new, duplicates = check_duplicates(existing_questions, new_questions)

    if duplicates:
        print(f"   ⚠️  Найдено дубликатов: {len(duplicates)}")
        print("   📝 Первые 3 дубликата:")
        for dup in duplicates[:3]:
            print(f"      - {dup['id']}: {dup['text'][:60]}...")
    else:
        print(f"   ✅ Дубликатов не найдено")

    print(f"   ✅ Уникальных новых вопросов: {len(unique_new)}")

    # 4. Объединение
    print("\n🔗 Объединяю вопросы...")
    all_questions = existing_questions + unique_new
    print(f"   ✅ Итого: {len(all_questions)} вопросов")

    # 5. Анализ распределения
    print("\n📊 Анализ финального распределения:")
    distribution = analyze_distribution(all_questions)

    print("\n   Домены:")
    for domain, count in sorted(distribution['domains'].items(), key=lambda x: -x[1]):
        print(f"      {domain:20s}: {count:4d} вопросов")

    print("\n   Глубина:")
    depth_order = ['SURFACE', 'CONSCIOUS', 'EDGE', 'SHADOW', 'CORE']
    for depth in depth_order:
        count = distribution['depths'].get(depth, 0)
        if count > 0:
            print(f"      {depth:20s}: {count:4d} вопросов")

    print("\n   Энергетика:")
    for energy, count in sorted(distribution['energies'].items(), key=lambda x: -x[1]):
        print(f"      {energy:20s}: {count:4d} вопросов")

    print("\n   Стадии путешествия:")
    for stage, count in sorted(distribution['stages'].items(), key=lambda x: -x[1]):
        print(f"      {stage:20s}: {count:4d} вопросов")

    # 6. Сохранение
    print(f"\n💾 Сохраняю финальный датасет...")

    # Создаю финальную структуру с метаданными
    from datetime import datetime
    final_data = {
        "metadata": {
            "version": "3.0",
            "title": "Selfology Intelligent Question Core - Complete",
            "description": "Полный набор профессиональных психологических вопросов для глубокого самопознания",
            "total_questions": len(all_questions),
            "original_questions": len(existing_questions),
            "new_generated_questions": len(unique_new),
            "duplicates_removed": len(duplicates),
            "last_updated": datetime.now().isoformat(),
            "sources": [
                "selfology_intelligent_core_enhanced.json (943 questions)",
                "ai_generated_8_blocks_claude_opus_4 (390 questions)"
            ],
            "distribution": distribution
        },
        "questions": all_questions
    }

    save_json(final_data, OUTPUT_FILE)

    # Статистика файла
    file_size_mb = OUTPUT_FILE.stat().st_size / (1024 * 1024)
    print(f"   ✅ Сохранено в: {OUTPUT_FILE}")
    print(f"   📦 Размер файла: {file_size_mb:.2f} MB")

    # 7. Финальная сводка
    print("\n" + "=" * 60)
    print("✨ ФИНАЛЬНАЯ СВОДКА")
    print("=" * 60)
    print(f"📊 Существующие вопросы:     {len(existing_questions):4d}")
    print(f"➕ Новые уникальные вопросы: {len(unique_new):4d}")
    if duplicates:
        print(f"➖ Дубликаты (пропущено):    {len(duplicates):4d}")
    print(f"🎯 ИТОГО вопросов:           {len(all_questions):4d}")
    print("=" * 60)

    # 8. Создание summary файла
    summary = {
        "total_questions": len(all_questions),
        "sources": {
            "existing_enhanced": len(existing_questions),
            "new_blocks": len(unique_new),
            "duplicates_removed": len(duplicates)
        },
        "distribution": distribution,
        "file": str(OUTPUT_FILE),
        "size_mb": round(file_size_mb, 2)
    }

    summary_file = DATA_DIR / "FINAL_MERGE_SUMMARY.json"
    save_json(summary, summary_file)
    print(f"\n📋 Детальная статистика сохранена в: {summary_file}")

    print("\n✅ Готово! Финальный датасет создан.")

if __name__ == "__main__":
    main()
