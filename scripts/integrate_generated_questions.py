#!/usr/bin/env python3
"""
Интеграция сгенерированных вопросов в основную базу
"""
import json
from pathlib import Path
from datetime import datetime

def main():
    print("🔄 ИНТЕГРАЦИЯ СГЕНЕРИРОВАННЫХ ВОПРОСОВ\n")
    print("="*80)

    # Загрузить сгенерированные вопросы
    generated_file = Path('prompts/generated_questions_for_programs.json')
    with open(generated_file, 'r', encoding='utf-8') as f:
        generated_data = json.load(f)

    # Загрузить существующую базу
    db_file = Path('intelligent_question_core/data/selfology_questions_deduplicated.json')
    with open(db_file, 'r', encoding='utf-8') as f:
        db_data = json.load(f)

    questions = db_data['questions']

    print(f"📊 Существующая база: {len(questions)} вопросов")
    print(f"📊 Новые вопросы: {generated_data['metadata']['total_questions']}")

    # Найти максимальный ID для продолжения нумерации
    existing_ids = [q['id'] for q in questions]
    max_num = 0
    for qid in existing_ids:
        # Извлечь число из ID типа "q_001"
        if qid.startswith('q_'):
            try:
                num = int(qid.split('_')[1])
                max_num = max(max_num, num)
            except:
                pass

    print(f"\n🔢 Максимальный ID в базе: q_{max_num:03d}")
    print(f"🔢 Новые ID начнутся с: q_{max_num+1:03d}\n")

    # Интегрировать вопросы
    added_count = 0

    for program_data in generated_data['programs']:
        prog_name = program_data['program']
        prog_questions = program_data['questions']

        print(f"\n📦 Программа: {prog_name}")
        print(f"   Вопросов: {len(prog_questions)}")

        for q in prog_questions:
            max_num += 1

            # Создать новый вопрос в формате базы
            new_question = {
                'id': f'q_{max_num:03d}',
                'text': q['text'],
                'classification': {
                    'journey_stage': 'EXPLORING',  # По умолчанию для новых программ
                    'depth_level': q['depth_level'],
                    'domain': q['domain'],
                    'energy_dynamic': q['energy_dynamic']
                },
                'source_system': 'generated_2025',
                'generated_at': q['generated_at'],
                'original_program': prog_name,
                'programs_tagged': [{
                    'program': prog_name,
                    'relevance_score': 1.0,  # Максимальная релевантность - созданы для программы
                    'status': 'tagged'
                }]
            }

            questions.append(new_question)
            added_count += 1

    # Обновить метаданные базы
    db_data['questions'] = questions

    if 'metadata' not in db_data:
        db_data['metadata'] = {}

    db_data['metadata']['last_updated'] = datetime.now().isoformat()
    db_data['metadata']['total_questions'] = len(questions)
    db_data['metadata']['generated_questions_added'] = added_count

    # Сохранить обновленную базу
    output_file = Path('intelligent_question_core/data/selfology_questions_with_generated.json')

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(db_data, f, ensure_ascii=False, indent=2)

    print(f"\n\n{'='*80}")
    print(f"✅ ИНТЕГРАЦИЯ ЗАВЕРШЕНА\n")
    print(f"📊 Добавлено новых вопросов: {added_count}")
    print(f"📊 Всего вопросов в базе: {len(questions)}")
    print(f"\n💾 Сохранено: {output_file}")

    print(f"\n\n{'='*80}")
    print(f"📋 СЛЕДУЮЩИЕ ШАГИ:\n")
    print(f"1. Запустить дедупликацию для проверки на совпадения:")
    print(f"   python scripts/deduplicate_questions.py")
    print(f"\n2. Запустить тегирование для связывания с другими программами:")
    print(f"   python scripts/tag_questions_to_programs.py")
    print(f"\n3. Запустить секвенирование для финальных последовательностей:")
    print(f"   python scripts/sequence_all_programs.py")

if __name__ == '__main__':
    main()
