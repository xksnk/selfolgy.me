#!/usr/bin/env python3
"""
Упрощенная дедупликация - только точные дубликаты
"""
import json
from pathlib import Path
import re
from collections import defaultdict

def normalize_text(text):
    """Нормализовать текст для сравнения"""
    text = re.sub(r'\s+', ' ', text)
    text = text.strip().lower()
    text = text.rstrip('?.!,;:')
    return text

def main():
    print("🔍 БЫСТРАЯ ДЕДУПЛИКАЦИЯ (только точные совпадения)\n")
    print("="*80)

    # Загрузить базу
    data_file = Path('intelligent_question_core/data/selfology_questions_with_generated.json')
    with open(data_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    questions = data['questions']
    print(f"📊 Всего вопросов: {len(questions)}\n")

    # Найти точные дубликаты
    text_index = defaultdict(list)

    for q in questions:
        norm_text = normalize_text(q['text'])
        text_index[norm_text].append(q)

    # Пометить дубликаты
    exact_duplicates = 0
    duplicate_groups = []

    for norm_text, q_list in text_index.items():
        if len(q_list) > 1:
            q_list.sort(key=lambda x: x['id'])
            master = q_list[0]
            duplicates = q_list[1:]

            duplicate_groups.append({
                'master': master['id'],
                'duplicates': [q['id'] for q in duplicates],
                'text': master['text'][:80]
            })

            for dup in duplicates:
                dup['duplicate_of'] = master['id']
                exact_duplicates += 1

    print(f"✅ Найдено групп дубликатов: {len(duplicate_groups)}")
    print(f"✅ Всего точных дубликатов: {exact_duplicates}")

    if duplicate_groups:
        print(f"\n🔍 ПРИМЕРЫ ДУБЛИКАТОВ:\n")
        for i, group in enumerate(duplicate_groups[:10], 1):
            print(f"{i}. Мастер: {group['master']}")
            print(f"   Текст: {group['text']}...")
            print(f"   Дубликаты: {', '.join(group['duplicates'])}\n")

    # Сохранить
    output_file = Path('intelligent_question_core/data/selfology_questions_deduplicated.json')

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Сохранено: {output_file}")

    duplicates_count = sum(1 for q in questions if 'duplicate_of' in q)
    clean_count = len(questions) - duplicates_count

    print(f"\n{'='*80}")
    print(f"📊 ИТОГ:\n")
    print(f"Всего вопросов: {len(questions)}")
    print(f"Точных дубликатов: {duplicates_count}")
    print(f"Уникальных вопросов: {clean_count}")

if __name__ == '__main__':
    main()
