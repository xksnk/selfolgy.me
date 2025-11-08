#!/usr/bin/env python3
"""
Получить структуру программ из Notion
"""
from notion_client import Client
import json
from pathlib import Path
import os
from dotenv import load_dotenv

load_dotenv()
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
PAGE_ID = "4efea3f4316e422b9bfc53c761f397c4"

def extract_text_from_rich_text(rich_text_list):
    """Извлечь plain text из Notion rich_text"""
    if not rich_text_list:
        return ""
    return ''.join([t['plain_text'] for t in rich_text_list])

def get_block_text(block):
    """Получить текст из блока любого типа"""
    block_type = block['type']

    if block_type in ['paragraph', 'heading_1', 'heading_2', 'heading_3',
                      'bulleted_list_item', 'numbered_list_item', 'to_do']:
        rich_text = block[block_type].get('rich_text', [])
        return extract_text_from_rich_text(rich_text)
    elif block_type == 'toggle':
        rich_text = block['toggle'].get('rich_text', [])
        return extract_text_from_rich_text(rich_text)

    return None

def process_column_lists(notion, page_blocks):
    """Обработать column lists - найти программы"""

    programs = []

    for block in page_blocks:
        if block['type'] != 'column_list':
            continue

        block_id = block['id']
        columns = notion.blocks.children.list(block_id=block_id)

        for col in columns['results']:
            if col['type'] != 'column':
                continue

            col_id = col['id']
            col_blocks = notion.blocks.children.list(block_id=col_id)

            # Ищем программу в колонке
            program = process_column_for_program(notion, col_blocks['results'])

            if program:
                programs.append(program)

    return programs

def process_column_for_program(notion, blocks):
    """Обработать блоки колонки, найти программу"""

    program_name = None
    questions = []
    description = []

    for block in blocks:
        block_type = block['type']
        text = get_block_text(block)

        if not text:
            continue

        # Заголовок - название программы
        if block_type in ['heading_1', 'heading_2']:
            if not program_name:
                program_name = text

        # Описание
        elif block_type == 'paragraph':
            description.append(text)

        # Toggle блоки часто содержат вопросы
        elif block_type == 'toggle':
            # Получить вложенные блоки toggle
            toggle_id = block['id']
            toggle_children = notion.blocks.children.list(block_id=toggle_id)

            question = {
                'main_text': text,
                'sub_questions': []
            }

            for child in toggle_children['results']:
                child_text = get_block_text(child)
                if child_text:
                    question['sub_questions'].append(child_text)

            questions.append(question)

        # Списки - тоже могут быть вопросами
        elif block_type in ['bulleted_list_item', 'numbered_list_item']:
            questions.append({
                'main_text': text,
                'sub_questions': []
            })

    if program_name and questions:
        return {
            'name': program_name,
            'description': '\\n'.join(description),
            'questions': questions,
            'total_questions': len(questions)
        }

    return None

def main():
    print("🔍 Получаю программы из Notion...\n")

    try:
        notion = Client(auth=NOTION_TOKEN)

        # Получить блоки главной страницы
        blocks = notion.blocks.children.list(block_id=PAGE_ID)

        # Обработать column lists
        programs = process_column_lists(notion, blocks['results'])

        print(f"✅ Найдено программ: {len(programs)}\n")

        for i, program in enumerate(programs, 1):
            print(f"{i}. {program['name']}")
            print(f"   Описание: {program['description'][:100]}...")
            print(f"   Вопросов: {program['total_questions']}")
            print()

        # Сохранить в JSON
        output_path = Path(__file__).parent.parent / 'prompts' / 'notion_programs.json'

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(programs, f, ensure_ascii=False, indent=2)

        print(f"💾 Сохранено в: {output_path}")

        return programs

    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return []

if __name__ == '__main__':
    main()
