#!/usr/bin/env python3
"""
Добавить метаданные program и position к вопросам в базе
"""
import json
from pathlib import Path

def main():
    print("📋 ДОБАВЛЕНИЕ МЕТАДАННЫХ ПРОГРАММ К ВОПРОСАМ\n")
    print("="*80)

    # Загрузить базу вопросов
    db_file = Path('intelligent_question_core/data/selfology_intelligent_core_complete.json')
    with open(db_file, 'r', encoding='utf-8') as f:
        db_data = json.load(f)

    questions = db_data['questions']

    # Загрузить совпадения
    matches_file = Path('prompts/program_question_matches.json')
    with open(matches_file, 'r', encoding='utf-8') as f:
        matches_data = json.load(f)

    matches = matches_data['matches']

    print(f"📊 Вопросов в базе: {len(questions)}")
    print(f"📊 Совпадений: {len(matches)}\n")

    # Создать индекс: question_id -> match metadata
    match_index = {}
    for match in matches:
        q_id = match['db_question_id']
        if q_id not in match_index:
            match_index[q_id] = []
        match_index[q_id].append({
            'program': match['program'],
            'position': match['position']
        })

    # Подсчитать программы на вопрос
    program_stats = {}
    for q_id, programs in match_index.items():
        count = len(programs)
        if count not in program_stats:
            program_stats[count] = 0
        program_stats[count] += 1

    print(f"📈 СТАТИСТИКА ПО ПРОГРАММАМ НА ВОПРОС:")
    for count in sorted(program_stats.keys()):
        print(f"   {count} программ: {program_stats[count]} вопросов")

    # Добавить метаданные к вопросам
    updated_count = 0

    for question in questions:
        q_id = question['id']

        if q_id in match_index:
            # Вопрос используется в программах
            question['programs'] = match_index[q_id]
            updated_count += 1
        else:
            # Вопрос не используется в программах
            question['programs'] = []

    print(f"\n✅ Обновлено вопросов: {updated_count}/{len(questions)}")
    print(f"   Без программ: {len(questions) - updated_count}")

    # Сохранить обновленную базу
    output_file = Path('intelligent_question_core/data/selfology_intelligent_core_with_programs.json')

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(db_data, f, ensure_ascii=False, indent=2)

    print(f"\n💾 Сохранено в: {output_file}")

    # Показать примеры
    print(f"\n\n🔍 ПРИМЕРЫ ВОПРОСОВ С ПРОГРАММАМИ:\n")

    examples_shown = 0
    for q in questions:
        if q['programs'] and examples_shown < 5:
            print(f"ID: {q['id']}")
            print(f"Текст: {q['text'][:60]}...")
            print(f"Программы ({len(q['programs'])}):")
            for prog in q['programs']:
                print(f"   • {prog['program']} - позиция {prog['position']}")
            print()
            examples_shown += 1

    # Статистика по программам
    print(f"\n\n📊 СТАТИСТИКА ПО ПРОГРАММАМ:\n")

    program_question_count = {}
    for match in matches:
        prog = match['program']
        if prog not in program_question_count:
            program_question_count[prog] = 0
        program_question_count[prog] += 1

    for prog_name in sorted(program_question_count.keys()):
        count = program_question_count[prog_name]
        print(f"   {prog_name}: {count} вопросов")

if __name__ == '__main__':
    main()
