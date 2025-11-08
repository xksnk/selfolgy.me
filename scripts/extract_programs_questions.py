#!/usr/bin/env python3
"""
Извлечь вопросы из всех программ Notion
"""
from notion_client import Client
import json
from pathlib import Path
import os
from dotenv import load_dotenv

load_dotenv()
NOTION_TOKEN = os.getenv("NOTION_TOKEN")

def extract_text(rich_text_list):
    return ''.join([t['plain_text'] for t in rich_text_list]) if rich_text_list else ""

def get_questions_from_page(notion, page_id, depth=0):
    """Рекурсивно извлечь вопросы из страницы"""
    questions = []

    try:
        blocks = notion.blocks.children.list(block_id=page_id)

        for block in blocks['results']:
            block_type = block['type']

            # Toggle блоки обычно содержат вопросы
            if block_type == 'toggle':
                question_text = extract_text(block['toggle'].get('rich_text', []))

                if question_text:
                    # Получить вложенные блоки (подвопросы)
                    sub_questions = []
                    try:
                        toggle_children = notion.blocks.children.list(block_id=block['id'])

                        for child in toggle_children['results']:
                            child_type = child['type']
                            child_text = None

                            if child_type in ['paragraph', 'bulleted_list_item', 'numbered_list_item']:
                                child_text = extract_text(child[child_type].get('rich_text', []))

                            if child_text:
                                sub_questions.append(child_text)

                    except:
                        pass

                    questions.append({
                        'text': question_text,
                        'sub_questions': sub_questions
                    })

            # Списки тоже могут быть вопросами
            elif block_type in ['bulleted_list_item', 'numbered_list_item']:
                text = extract_text(block[block_type].get('rich_text', []))

                if text and '?' in text:
                    questions.append({
                        'text': text,
                        'sub_questions': []
                    })

            # Параграфы с вопросами
            elif block_type == 'paragraph':
                text = extract_text(block['paragraph'].get('rich_text', []))

                if text and '?' in text:
                    questions.append({
                        'text': text,
                        'sub_questions': []
                    })

    except Exception as e:
        print(f"      ⚠️  Ошибка при обработке блоков: {e}")

    return questions

def main():
    # Загрузить список ВСЕХ страниц
    programs_file = Path('prompts/all_notion_pages.json')

    with open(programs_file, 'r', encoding='utf-8') as f:
        all_pages = json.load(f)

    # Исключить описательные страницы
    exclude = ['Selfolgy.me', 'Es Selfolgy.me']
    programs = [p for p in all_pages if p['name'] not in exclude]

    print(f"📚 Извлекаем вопросы из {len(programs)} программ\n")
    print("="*80)

    notion = Client(auth=NOTION_TOKEN)

    programs_with_questions = []

    for i, program in enumerate(programs, 1):
        program_name = program['name']
        program_id = program['id']

        print(f"\n{i}. 📄 {program_name}")
        print(f"   ID: {program_id}")

        # Получить вопросы
        questions = get_questions_from_page(notion, program_id)

        print(f"   ✅ Вопросов найдено: {len(questions)}")

        # Показать первые 3 вопроса
        if questions:
            print(f"\n   Первые вопросы:")
            for j, q in enumerate(questions[:3], 1):
                print(f"      {j}. {q['text'][:80]}...")
                if q['sub_questions']:
                    print(f"         Подвопросов: {len(q['sub_questions'])}")

        programs_with_questions.append({
            'id': program_id,
            'name': program_name,
            'questions': questions,
            'total_questions': len(questions)
        })

    # Сохранить
    output_file = Path('prompts/notion_programs_with_questions.json')

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(programs_with_questions, f, ensure_ascii=False, indent=2)

    print(f"\n\n{'='*80}")
    print(f"💾 Сохранено в: {output_file}")
    print("="*80)

    # Статистика
    total_questions = sum(p['total_questions'] for p in programs_with_questions)

    print(f"\n📊 СТАТИСТИКА:")
    print(f"   Программ: {len(programs_with_questions)}")
    print(f"   Всего вопросов: {total_questions}")
    print(f"   Среднее на программу: {total_questions / len(programs_with_questions):.1f}")

    print(f"\n📋 ПО ПРОГРАММАМ:")
    for p in programs_with_questions:
        print(f"   {p['name']}: {p['total_questions']} вопросов")

if __name__ == '__main__':
    main()
