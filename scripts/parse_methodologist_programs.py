#!/usr/bin/env python3
"""
Парсер файла методолога с переработанными программами.
Извлекает программы, блоки и вопросы в структурированный JSON.

Входной файл: research/Ты методолог по дизайну рефлексивных опросников..md
Выходной файл: intelligent_question_core/data/selfology_programs_v2.json
"""

import re
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
import hashlib


def generate_id(prefix: str, name: str) -> str:
    """Генерация уникального ID из названия"""
    # Транслитерация и очистка
    translit = {
        'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'e',
        'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
        'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
        'ф': 'f', 'х': 'h', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'sch',
        'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya',
        ' ': '_', '-': '_', '/': '_', '→': '_to_', ':': '', '.': '', ',': '',
        '(': '', ')': '', '«': '', '»': '', '"': '', "'": ''
    }

    name_lower = name.lower()
    result = ''
    for char in name_lower:
        if char in translit:
            result += translit[char]
        elif char.isalnum():
            result += char

    # Убрать множественные подчёркивания
    result = re.sub(r'_+', '_', result).strip('_')

    return f"{prefix}_{result}"


def parse_format_markers(text: str) -> str:
    """Определить формат вопроса по маркерам 📖/🤖"""
    if '📖🤖' in text or '🤖📖' in text:
        return 'both'
    elif '📖' in text:
        return 'book_only'
    elif '🤖' in text:
        return 'ai_only'
    return 'both'  # по умолчанию


def clean_question_text(text: str) -> str:
    """Очистить текст вопроса от маркеров и форматирования"""
    # Убрать маркеры формата
    text = text.replace('📖', '').replace('🤖', '')
    # Убрать **bold**
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    # Убрать номер в начале
    text = re.sub(r'^\d+\.\s*', '', text)
    # Убрать лишние пробелы
    text = text.strip()
    return text


def determine_block_type(block_name: str, block_sequence: int, total_blocks: int) -> str:
    """Определить тип блока по названию и позиции"""
    name_lower = block_name.lower()

    # Foundation признаки
    foundation_keywords = ['здесь и сейчас', 'ориентация', 'текущ', 'где я', 'фундамент', 'основ']
    for kw in foundation_keywords:
        if kw in name_lower:
            return 'Foundation'

    # Integration признаки
    integration_keywords = ['будущ', 'образ', 'интеграц', 'смысл', 'гордость', 'закрытие', 'итог']
    for kw in integration_keywords:
        if kw in name_lower:
            return 'Integration'

    # По позиции
    if block_sequence == 1:
        return 'Foundation'
    elif block_sequence == total_blocks:
        return 'Integration'

    return 'Exploration'


def parse_block_header(line: str) -> Optional[Dict]:
    """Парсить заголовок блока: ### Блок N: Название (описание)"""
    # Паттерн: ### Блок N: Название
    match = re.match(r'^###\s*Блок\s*(\d+)[:\s]+(.+?)(?:\s*\((.+?)\))?$', line.strip())
    if match:
        return {
            'sequence': int(match.group(1)),
            'name': match.group(2).strip(),
            'description': match.group(3).strip() if match.group(3) else ''
        }
    return None


def parse_question_line(line: str) -> Optional[Dict]:
    """Парсить строку вопроса: N. **Текст вопроса** 📖🤖"""
    # Паттерн: N. **текст** маркеры
    match = re.match(r'^(\d+)\.\s*\*\*(.+?)\*\*\s*([📖🤖]*)', line.strip())
    if match:
        return {
            'position': int(match.group(1)),
            'text': match.group(2).strip(),
            'format': parse_format_markers(match.group(3))
        }

    # Альтернативный паттерн без bold
    match = re.match(r'^(\d+)\.\s*(.+?)\s*([📖🤖]*)$', line.strip())
    if match:
        text = match.group(2).strip()
        # Убедиться что это не комментарий
        if not text.startswith('*') and len(text) > 10:
            return {
                'position': int(match.group(1)),
                'text': clean_question_text(text),
                'format': parse_format_markers(match.group(3))
            }

    return None


def parse_program_header(line: str) -> Optional[str]:
    """Парсить заголовок программы: ## Selfology: Название или ## ПЕРЕРАБОТАННАЯ ПРОГРАММА"""
    # Паттерн: ## Selfology: Название
    match = re.match(r'^##\s*(?:Selfology:\s*)?(.+)$', line.strip())
    if match:
        name = match.group(1).strip()
        # Пропускаем служебные заголовки
        skip_patterns = ['ПЕРЕРАБОТАННАЯ', 'Критичные проблемы', 'Что изменилось', 'РЕШЕНИЕ']
        for pattern in skip_patterns:
            if pattern in name:
                return None
        return name
    return None


def parse_methodologist_file(filepath: str) -> Dict[str, Any]:
    """
    Главный парсер файла методолога.

    Возвращает структуру:
    {
        "version": "2.0",
        "programs": [
            {
                "id": "program_...",
                "name": "...",
                "blocks": [
                    {
                        "id": "block_...",
                        "name": "...",
                        "type": "Foundation|Exploration|Integration",
                        "questions": [...]
                    }
                ]
            }
        ]
    }
    """

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    lines = content.split('\n')

    programs = []
    current_program = None
    current_block = None

    i = 0
    while i < len(lines):
        line = lines[i]

        # Ищем заголовок программы
        if line.startswith('## Selfology:'):
            program_name = parse_program_header(line)
            if program_name:
                # Сохраняем предыдущую программу
                if current_program:
                    if current_block and current_block['questions']:
                        current_program['blocks'].append(current_block)
                    if current_program['blocks']:
                        programs.append(current_program)

                # Начинаем новую программу
                current_program = {
                    'id': generate_id('program', program_name),
                    'name': program_name,
                    'blocks': []
                }
                current_block = None
                print(f"📘 Найдена программа: {program_name}")

        # Ищем заголовок блока
        elif line.startswith('### Блок'):
            block_info = parse_block_header(line)
            if block_info and current_program:
                # Сохраняем предыдущий блок
                if current_block and current_block['questions']:
                    current_program['blocks'].append(current_block)

                # Начинаем новый блок
                current_block = {
                    'id': generate_id('block', f"{current_program['name']}_{block_info['name']}"),
                    'sequence': block_info['sequence'],
                    'name': block_info['name'],
                    'description': block_info['description'],
                    'type': None,  # определим позже
                    'questions': []
                }
                print(f"  📦 Блок {block_info['sequence']}: {block_info['name']}")

        # Ищем вопрос
        elif current_block and re.match(r'^\d+\.', line.strip()):
            question = parse_question_line(line)
            if question:
                # Используем позицию внутри блока для уникальности ID
                position_in_block = len(current_block['questions']) + 1
                question['id'] = generate_id('q', f"{current_program['name']}_b{current_block['sequence']}_q{position_in_block}")
                question['position_in_block'] = position_in_block
                current_block['questions'].append(question)

        i += 1

    # Сохраняем последнюю программу и блок
    if current_block and current_block['questions']:
        current_program['blocks'].append(current_block)
    if current_program and current_program['blocks']:
        programs.append(current_program)

    # Определяем типы блоков
    for program in programs:
        total_blocks = len(program['blocks'])
        for block in program['blocks']:
            block['type'] = determine_block_type(block['name'], block['sequence'], total_blocks)

    # Статистика
    total_questions = sum(
        len(block['questions'])
        for program in programs
        for block in program['blocks']
    )
    total_blocks = sum(len(program['blocks']) for program in programs)

    result = {
        'version': '2.0',
        'generated_at': datetime.now().isoformat(),
        'metadata': {
            'total_programs': len(programs),
            'total_blocks': total_blocks,
            'total_questions': total_questions,
            'source_file': str(filepath)
        },
        'programs': programs
    }

    return result


def add_block_metadata(programs: List[Dict]) -> List[Dict]:
    """
    Добавить базовые метаданные блоков на основе их типа.
    """

    block_defaults = {
        'Foundation': {
            'base_journey_stage': 'ENTRY',
            'base_depth_range': ['SURFACE', 'CONSCIOUS'],
            'base_energy_dynamic': 'OPENING',
            'base_safety_minimum': 4,
            'base_complexity_range': [1, 2],
            'base_emotional_weight_range': [1, 2]
        },
        'Exploration': {
            'base_journey_stage': 'EXPLORATION',
            'base_depth_range': ['CONSCIOUS', 'EDGE', 'SHADOW'],
            'base_energy_dynamic': 'PROCESSING',
            'base_safety_minimum': 2,
            'base_complexity_range': [2, 4],
            'base_emotional_weight_range': [2, 4]
        },
        'Integration': {
            'base_journey_stage': 'INTEGRATION',
            'base_depth_range': ['SHADOW', 'CORE'],
            'base_energy_dynamic': 'HEALING',
            'base_safety_minimum': 2,
            'base_complexity_range': [3, 4],
            'base_emotional_weight_range': [2, 3]
        }
    }

    for program in programs:
        for block in program['blocks']:
            block_type = block.get('type', 'Exploration')
            block['block_metadata'] = block_defaults.get(block_type, block_defaults['Exploration'])

    return programs


def main():
    print("=" * 60)
    print("🔍 ПАРСИНГ ФАЙЛА МЕТОДОЛОГА")
    print("=" * 60)

    # Пути - ищем файл по паттерну
    research_dir = Path('research')
    input_files = list(research_dir.glob('*методолог*.md'))
    if not input_files:
        print("❌ Файл методолога не найден в research/")
        return
    input_file = input_files[0]
    output_file = Path('intelligent_question_core/data/selfology_programs_v2.json')

    if not input_file.exists():
        print(f"❌ Файл не найден: {input_file}")
        return

    # Парсинг
    print(f"\n📄 Читаю файл: {input_file}")
    result = parse_methodologist_file(input_file)

    # Добавляем метаданные блоков
    result['programs'] = add_block_metadata(result['programs'])

    # Статистика
    print(f"\n{'=' * 60}")
    print("📊 СТАТИСТИКА:")
    print(f"  Программ: {result['metadata']['total_programs']}")
    print(f"  Блоков: {result['metadata']['total_blocks']}")
    print(f"  Вопросов: {result['metadata']['total_questions']}")

    # Детали по программам
    print(f"\n📋 ПРОГРАММЫ:")
    for prog in result['programs']:
        q_count = sum(len(b['questions']) for b in prog['blocks'])
        print(f"  • {prog['name']}: {len(prog['blocks'])} блоков, {q_count} вопросов")

    # Сохранение
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"\n💾 Сохранено в: {output_file}")
    print("=" * 60)


if __name__ == '__main__':
    main()
