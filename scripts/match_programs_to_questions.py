#!/usr/bin/env python3
"""
Сопоставить вопросы из Notion программ с базой 1331 вопрос
Добавить метаданные program и position
"""
import json
from pathlib import Path
from difflib import SequenceMatcher
import re

def normalize_text(text):
    """Нормализовать текст для сравнения"""
    # Убрать лишние пробелы, перевод строк
    text = re.sub(r'\s+', ' ', text)
    # Убрать знаки препинания в конце
    text = text.strip().rstrip('?.!,;:')
    # Нижний регистр
    text = text.lower()
    return text

def texts_similar(text1, text2, threshold=0.85):
    """Проверить схожесть текстов"""
    norm1 = normalize_text(text1)
    norm2 = normalize_text(text2)

    # Точное совпадение
    if norm1 == norm2:
        return 1.0

    # Fuzzy matching
    ratio = SequenceMatcher(None, norm1, norm2).ratio()
    return ratio if ratio >= threshold else 0.0

def main():
    print("🔗 СОПОСТАВЛЕНИЕ ВОПРОСОВ ИЗ NOTION С БАЗОЙ\n")
    print("="*80)

    # Загрузить вопросы из Notion программ
    notion_file = Path('prompts/notion_programs_with_questions.json')
    with open(notion_file, 'r', encoding='utf-8') as f:
        notion_programs = json.load(f)

    # Загрузить базу вопросов
    db_file = Path('intelligent_question_core/data/selfology_intelligent_core_complete.json')
    with open(db_file, 'r', encoding='utf-8') as f:
        db_data = json.load(f)

    db_questions = db_data['questions']

    print(f"📊 Вопросов в Notion программах: {sum(p['total_questions'] for p in notion_programs)}")
    print(f"📊 Вопросов в базе: {len(db_questions)}\n")

    # Создать словарь для быстрого поиска
    # normalized_text -> list of db questions
    db_index = {}
    for q in db_questions:
        norm_text = normalize_text(q['text'])
        if norm_text not in db_index:
            db_index[norm_text] = []
        db_index[norm_text].append(q)

    # Сопоставить
    matches = []
    unmatched_notion = []

    for program in notion_programs:
        program_name = program['name']

        if program['total_questions'] == 0:
            continue

        print(f"\n{'─'*80}")
        print(f"📄 Программа: {program_name}")
        print(f"   Вопросов: {program['total_questions']}")

        program_matches = 0

        for position, notion_q in enumerate(program['questions'], 1):
            notion_text = notion_q['text']
            norm_notion = normalize_text(notion_text)

            # Поиск точного совпадения
            if norm_notion in db_index:
                for db_q in db_index[norm_notion]:
                    matches.append({
                        'program': program_name,
                        'position': position,
                        'notion_text': notion_text,
                        'db_question_id': db_q['id'],
                        'db_text': db_q['text'],
                        'match_type': 'exact',
                        'similarity': 1.0
                    })
                    program_matches += 1
                    print(f"   ✅ {position}. Точное совпадение: {db_q['id']}")
                    break
            else:
                # Поиск похожих
                best_match = None
                best_similarity = 0.0

                for db_q in db_questions[:500]:  # Проверяем первые 500 для скорости
                    similarity = texts_similar(notion_text, db_q['text'], threshold=0.80)

                    if similarity > best_similarity:
                        best_similarity = similarity
                        best_match = db_q

                if best_match and best_similarity >= 0.80:
                    matches.append({
                        'program': program_name,
                        'position': position,
                        'notion_text': notion_text,
                        'db_question_id': best_match['id'],
                        'db_text': best_match['text'],
                        'match_type': 'fuzzy',
                        'similarity': best_similarity
                    })
                    program_matches += 1
                    print(f"   🔸 {position}. Похожий ({best_similarity:.0%}): {best_match['id']}")
                else:
                    unmatched_notion.append({
                        'program': program_name,
                        'position': position,
                        'text': notion_text
                    })
                    print(f"   ❌ {position}. НЕ найден: {notion_text[:60]}...")

        print(f"   📊 Совпадений: {program_matches}/{program['total_questions']}")

    # Сохранить результаты
    output_file = Path('prompts/program_question_matches.json')

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            'matches': matches,
            'unmatched_notion_questions': unmatched_notion,
            'stats': {
                'total_notion_questions': sum(p['total_questions'] for p in notion_programs),
                'total_matches': len(matches),
                'exact_matches': sum(1 for m in matches if m['match_type'] == 'exact'),
                'fuzzy_matches': sum(1 for m in matches if m['match_type'] == 'fuzzy'),
                'unmatched': len(unmatched_notion)
            }
        }, f, ensure_ascii=False, indent=2)

    print(f"\n\n{'='*80}")
    print(f"📊 ИТОГОВАЯ СТАТИСТИКА:")
    print("="*80)
    print(f"✅ Всего совпадений: {len(matches)}")
    print(f"   • Точных: {sum(1 for m in matches if m['match_type'] == 'exact')}")
    print(f"   • Похожих: {sum(1 for m in matches if m['match_type'] == 'fuzzy')}")
    print(f"❌ Не найдено: {len(unmatched_notion)}")
    print(f"\n💾 Результаты сохранены в: {output_file}")

    # Показать несовпавшие
    if unmatched_notion:
        print(f"\n\n🔍 НЕСОВПАВШИЕ ВОПРОСЫ (первые 10):")
        for i, um in enumerate(unmatched_notion[:10], 1):
            print(f"{i}. [{um['program']}] {um['text'][:70]}...")

if __name__ == '__main__':
    main()
