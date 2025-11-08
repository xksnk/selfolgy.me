#!/usr/bin/env python3
"""
Объединение существующих 693 вопросов с восстановленными 250 новыми
"""

import json
from pathlib import Path
from collections import Counter
from datetime import datetime

# Пути
BASE_DIR = Path("/home/ksnk/n8n-enterprise/projects/selfology")
EXISTING_FILE = BASE_DIR / "intelligent_question_core/data/selfology_intelligent_core.json"
GENERATED_DIR = BASE_DIR / "intelligent_question_core/data/generated_blocks"
OUTPUT_FILE = BASE_DIR / "intelligent_question_core/data/selfology_intelligent_core_enhanced.json"

def load_existing_questions():
    """Загрузить существующие 693 вопроса"""
    print(f"📂 Читаю существующие вопросы: {EXISTING_FILE}")

    with open(EXISTING_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)

    questions = data.get('questions', [])
    print(f"✅ Загружено {len(questions)} существующих вопросов")

    return data, questions

def load_generated_blocks():
    """Загрузить восстановленные блоки"""
    print(f"\n📂 Читаю восстановленные блоки: {GENERATED_DIR}")

    all_questions = []
    block_files = sorted(GENERATED_DIR.glob("*.json"))

    for block_file in block_files:
        if block_file.name in ['README.md', 'SUMMARY.md']:
            continue

        with open(block_file, 'r', encoding='utf-8') as f:
            questions = json.load(f)

        all_questions.extend(questions)
        print(f"   ✅ {block_file.name}: {len(questions)} вопросов")

    print(f"✅ Загружено {len(all_questions)} новых вопросов")

    return all_questions

def check_duplicates(existing, new):
    """Проверить дубликаты по ID и тексту"""
    existing_ids = {q['id'] for q in existing}
    existing_texts = {q['text'].lower().strip() for q in existing}

    duplicates_by_id = []
    duplicates_by_text = []
    unique_new = []

    for q in new:
        q_id = q.get('id', '')
        q_text = q.get('text', '').lower().strip()

        if q_id in existing_ids:
            duplicates_by_id.append(q_id)
        elif q_text in existing_texts:
            duplicates_by_text.append(q_text[:50] + "...")
        else:
            unique_new.append(q)
            existing_ids.add(q_id)
            existing_texts.add(q_text)

    if duplicates_by_id:
        print(f"\n⚠️  Найдено {len(duplicates_by_id)} дубликатов по ID")

    if duplicates_by_text:
        print(f"⚠️  Найдено {len(duplicates_by_text)} дубликатов по тексту")

    return unique_new

def analyze_distribution(questions):
    """Анализ распределения вопросов"""
    domains = Counter()
    depth_levels = Counter()
    energy_dynamics = Counter()
    journey_stages = Counter()

    for q in questions:
        classification = q.get('classification', {})
        domains[classification.get('domain', 'UNKNOWN')] += 1
        depth_levels[classification.get('depth_level', 'UNKNOWN')] += 1
        energy_dynamics[classification.get('energy_dynamic', 'UNKNOWN')] += 1
        journey_stages[classification.get('journey_stage', 'UNKNOWN')] += 1

    return {
        'domains': dict(domains),
        'depth_levels': dict(depth_levels),
        'energy_dynamics': dict(energy_dynamics),
        'journey_stages': dict(journey_stages)
    }

def main():
    print("🔄 Объединение вопросов Selfology\n")
    print("=" * 60)

    # Загрузить существующие
    existing_data, existing_questions = load_existing_questions()

    # Загрузить новые
    new_questions = load_generated_blocks()

    # Проверить дубликаты
    print(f"\n🔍 Проверка дубликатов...")
    unique_new = check_duplicates(existing_questions, new_questions)

    print(f"\n✅ Уникальных новых вопросов: {len(unique_new)}")

    # Объединить
    all_questions = existing_questions + unique_new
    total = len(all_questions)

    print(f"\n📊 Итого вопросов: {total}")
    print(f"   - Существующих: {len(existing_questions)}")
    print(f"   - Добавлено новых: {len(unique_new)}")

    # Анализ
    print(f"\n📈 Анализ распределения...")
    distribution = analyze_distribution(all_questions)

    print(f"\n🏷️  По доменам:")
    for domain, count in sorted(distribution['domains'].items(), key=lambda x: -x[1]):
        print(f"   {domain:20} - {count:3} вопросов")

    print(f"\n📊 По глубине:")
    for level, count in sorted(distribution['depth_levels'].items(), key=lambda x: -x[1]):
        print(f"   {level:20} - {count:3} вопросов")

    # Создать итоговую структуру
    output_data = {
        "metadata": {
            "version": "2.1",
            "title": "Selfology Intelligent Question Core - Enhanced",
            "description": "Профессиональные психологические вопросы для глубокого самопознания",
            "total_questions": total,
            "original_questions": len(existing_questions),
            "generated_questions": len(unique_new),
            "last_updated": datetime.now().isoformat(),
            "sources": [
                "original_693_professional_questions",
                "ai_generated_250_questions_claude_opus_4"
            ],
            "distribution": distribution
        },
        "questions": all_questions
    }

    # Сохранить
    print(f"\n💾 Сохранение объединенного файла...")
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    print(f"✅ Сохранено: {OUTPUT_FILE}")
    print(f"📦 Размер: {OUTPUT_FILE.stat().st_size / 1024:.1f} KB")

    # Также обновить основной файл (бэкап создан)
    backup_file = EXISTING_FILE.parent / f"selfology_intelligent_core.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    print(f"\n🔄 Создание бэкапа оригинала...")
    with open(EXISTING_FILE, 'r', encoding='utf-8') as f_in:
        with open(backup_file, 'w', encoding='utf-8') as f_out:
            f_out.write(f_in.read())

    print(f"✅ Бэкап: {backup_file.name}")

    print(f"\n✨ Готово!")
    print(f"\n📁 Файлы:")
    print(f"   - Основной (enhanced): {OUTPUT_FILE.name}")
    print(f"   - Оригинал (693): {EXISTING_FILE.name}")
    print(f"   - Бэкап: {backup_file.name}")

if __name__ == "__main__":
    main()
