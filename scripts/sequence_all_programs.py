#!/usr/bin/env python3
"""
ЭТАП 2: СЕКВЕНИРОВАНИЕ
Для каждой программы отобрать финальные вопросы и определить последовательность
"""
import json
from pathlib import Path
from collections import defaultdict, Counter
import random
random.seed(42)  # Для воспроизводимости

# Маппинг глубины для сортировки
DEPTH_ORDER = {
    'SURFACE': 1,
    'CONSCIOUS': 2,
    'EDGE': 3,
    'SHADOW': 4,
    'CORE': 5
}

# Маппинг энергетики
ENERGY_WEIGHT = {
    'OPENING': -2,    # Легкие, открывающие
    'NEUTRAL': 0,     # Нейтральные
    'HEALING': -1,    # Исцеляющие
    'PROCESSING': 1,  # Обрабатывающие
    'HEAVY': 2        # Тяжелые
}

def calculate_target_size(program_name, tagged_count):
    """Определить целевой размер программы"""

    # Существующие программы из Notion - сохраняем их размер
    existing_sizes = {
        'Подумать о жизни': 42,
        'Подумать о карьере или бизнесе': 28,
        'Задуматься о здоровье': 20,
        'Изучить себя': 15,
        'Улучшить эмоциональное состояние': 15,
        'Перебрать цели': 8,
        'Отношение с самим собой': 7,
        'Переосмыслить тайм-менеджмент': 7,
        'Мечтатели': 6,
        'Тренажёр, чтобы начать жить': 6,
        'Рефлексия': 5,
        '3 кита очищения': 3,
        'Ресурс': 2
    }

    if program_name in existing_sizes:
        return existing_sizes[program_name]

    # Для новых программ - в зависимости от количества доступных
    if tagged_count >= 100:
        return min(40, tagged_count // 3)  # Большие программы: 30-40
    elif tagged_count >= 50:
        return min(25, tagged_count // 2)  # Средние: 20-25
    elif tagged_count >= 20:
        return min(15, tagged_count // 2)  # Малые: 10-15
    else:
        return min(10, tagged_count)       # Микро: все что есть до 10

def group_by_theme(questions):
    """Группировать вопросы по темам (на основе первых слов)"""
    groups = defaultdict(list)

    for q in questions:
        # Извлечь первые 2-3 слова как тему
        words = q['text'].lower().split()[:3]
        theme = ' '.join(words)

        # Нормализовать общие начала
        if any(w in theme for w in ['что', 'какой', 'какая', 'какое']):
            theme = 'что'
        elif any(w in theme for w in ['как', 'каким']):
            theme = 'как'
        elif any(w in theme for w in ['почему', 'зачем']):
            theme = 'почему'
        elif any(w in theme for w in ['кто', 'кого', 'кому']):
            theme = 'кто'
        elif any(w in theme for w in ['когда', 'в какой момент']):
            theme = 'когда'

        groups[theme].append(q)

    return groups

def select_diverse_questions(questions, target_size):
    """Выбрать разнообразные вопросы из всех тем"""

    # Группировать по темам
    theme_groups = group_by_theme(questions)

    selected = []

    # Если вопросов меньше целевого - берем все
    if len(questions) <= target_size:
        return questions

    # Распределить квоту по темам пропорционально
    questions_per_theme = max(1, target_size // len(theme_groups))

    # Сначала берем по квоте из каждой темы
    for theme, theme_questions in theme_groups.items():
        # Сортировать по глубине внутри темы
        theme_questions.sort(key=lambda q: (
            DEPTH_ORDER.get(q['classification']['depth_level'], 99),
            q['id']
        ))

        # Взять до квоты
        selected.extend(theme_questions[:questions_per_theme])

    # Если не хватает - добавить из самых больших групп
    if len(selected) < target_size:
        remaining = target_size - len(selected)

        # Сортировать группы по размеру
        sorted_groups = sorted(theme_groups.items(), key=lambda x: len(x[1]), reverse=True)

        for theme, theme_questions in sorted_groups:
            # Пропустить уже использованные
            unused = [q for q in theme_questions if q not in selected]

            if unused:
                take = min(remaining, len(unused))
                selected.extend(unused[:take])
                remaining -= take

                if remaining <= 0:
                    break

    return selected[:target_size]

def check_energy_balance(sequence):
    """Проверить энергетический баланс последовательности"""
    issues = []
    heavy_count = 0

    for i, q in enumerate(sequence):
        energy = q['classification']['energy_dynamic']

        if energy == 'HEAVY':
            heavy_count += 1

            if heavy_count >= 3:
                issues.append({
                    'position': i + 1,
                    'issue': 'too_many_heavy',
                    'message': f'3+ HEAVY вопроса подряд (позиции {i-1}-{i+1})'
                })
        else:
            heavy_count = 0  # Сброс счетчика

    return issues

def rebalance_sequence(sequence):
    """Перебалансировать последовательность для энергетической безопасности"""

    rebalanced = []
    heavy_buffer = []  # Буфер для HEAVY вопросов

    for q in sequence:
        energy = q['classification']['energy_dynamic']

        if energy == 'HEAVY':
            heavy_buffer.append(q)

            # Если накопилось 2 HEAVY - вставить разгрузку
            if len(heavy_buffer) >= 2:
                # Добавить накопленные HEAVY
                rebalanced.extend(heavy_buffer)
                heavy_buffer = []

                # Найти HEALING или OPENING вопрос далее
                for future_q in sequence[sequence.index(q)+1:]:
                    if future_q['classification']['energy_dynamic'] in ['HEALING', 'OPENING']:
                        # Переместить его сюда
                        rebalanced.append(future_q)
                        sequence.remove(future_q)
                        break
        else:
            # Сначала выгрузить буфер HEAVY если есть
            if heavy_buffer:
                rebalanced.extend(heavy_buffer)
                heavy_buffer = []

            # Добавить текущий не-HEAVY
            rebalanced.append(q)

    # Добавить оставшиеся HEAVY в конце
    rebalanced.extend(heavy_buffer)

    return rebalanced

def sequence_program(program_name, tagged_questions, target_size=None):
    """Создать последовательность для программы"""

    print(f"\n🔄 Секвенирование: {program_name}")
    print(f"   Помечено вопросов: {len(tagged_questions)}")

    # Фильтровать дубликаты
    unique_questions = []
    seen_ids = set()

    for q in tagged_questions:
        # Пропустить если это дубликат
        if 'duplicate_of' in q:
            continue

        if q['id'] not in seen_ids:
            unique_questions.append(q)
            seen_ids.add(q['id'])

    print(f"   Уникальных: {len(unique_questions)}")

    # Определить целевой размер
    if target_size is None:
        target_size = calculate_target_size(program_name, len(unique_questions))

    print(f"   Целевой размер: {target_size}")

    # Выбрать разнообразные вопросы
    selected = select_diverse_questions(unique_questions, target_size)

    # Сортировать по глубине и энергетике
    selected.sort(key=lambda q: (
        DEPTH_ORDER.get(q['classification']['depth_level'], 99),
        ENERGY_WEIGHT.get(q['classification']['energy_dynamic'], 0),
        q['id']
    ))

    # Проверить энергетический баланс
    issues = check_energy_balance(selected)

    if issues:
        print(f"   ⚠️  Найдены проблемы с балансом: {len(issues)}")
        # Перебалансировать
        selected = rebalance_sequence(selected)
        print(f"   ✅ Перебалансировано")

    # Присвоить позиции
    sequenced = []
    for i, q in enumerate(selected, 1):
        q_copy = q.copy()
        q_copy['program_position'] = i
        q_copy['program_status'] = 'included'
        sequenced.append(q_copy)

    # Пометить исключенные
    excluded = []
    for q in unique_questions:
        if q not in selected:
            q_copy = q.copy()
            q_copy['program_status'] = 'excluded'

            # Определить причину исключения
            if len(unique_questions) > target_size * 2:
                q_copy['exclusion_reason'] = 'too_many_questions'
            else:
                # Проверить, есть ли похожий включенный
                included_texts = [sq['text'][:30] for sq in selected]
                if any(q['text'][:30] == it for it in included_texts):
                    q_copy['exclusion_reason'] = 'similar_included'
                else:
                    q_copy['exclusion_reason'] = 'theme_coverage'

            excluded.append(q_copy)

    print(f"   ✅ Включено: {len(sequenced)}")
    print(f"   ❌ Исключено: {len(excluded)}")

    return {
        'program': program_name,
        'total_tagged': len(tagged_questions),
        'total_unique': len(unique_questions),
        'included_count': len(sequenced),
        'excluded_count': len(excluded),
        'questions_included': sequenced,
        'questions_excluded': excluded
    }

def main():
    print("🎯 ЭТАП 2: СЕКВЕНИРОВАНИЕ ВСЕХ ПРОГРАММ\n")
    print("="*80)

    # Загрузить дедуплицированную базу
    data_file = Path('intelligent_question_core/data/selfology_questions_deduplicated.json')
    with open(data_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    questions = data['questions']

    # Загрузить список программ
    programs_file = Path('prompts/all_programs_list.json')
    with open(programs_file, 'r', encoding='utf-8') as f:
        programs = json.load(f)

    # Индексировать вопросы по программам
    program_questions = defaultdict(list)

    for q in questions:
        for tagged_prog in q.get('programs_tagged', []):
            prog_name = tagged_prog['program']
            program_questions[prog_name].append(q)

    # Секвенировать каждую программу с вопросами
    all_sequences = []
    programs_with_questions = []
    programs_without_questions = []

    for program in programs:
        prog_name = program['name']

        if prog_name in program_questions:
            programs_with_questions.append(prog_name)

            # Секвенировать
            sequence = sequence_program(
                prog_name,
                program_questions[prog_name]
            )
            all_sequences.append(sequence)
        else:
            programs_without_questions.append(prog_name)

    # Сохранить результаты
    output_file = Path('prompts/all_programs_sequenced.json')

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            'metadata': {
                'total_programs': len(programs),
                'programs_with_questions': len(programs_with_questions),
                'programs_without_questions': len(programs_without_questions),
                'programs_needing_generation': programs_without_questions
            },
            'sequences': all_sequences
        }, f, ensure_ascii=False, indent=2)

    # Обновить базу вопросов с финальными позициями
    questions_updated = questions.copy()

    for seq in all_sequences:
        prog_name = seq['program']

        # Обновить включенные вопросы
        for q in seq['questions_included']:
            # Найти вопрос в базе
            for base_q in questions_updated:
                if base_q['id'] == q['id']:
                    if 'programs_final' not in base_q:
                        base_q['programs_final'] = []

                    base_q['programs_final'].append({
                        'program': prog_name,
                        'position': q['program_position'],
                        'status': 'included'
                    })
                    break

        # Обновить исключенные
        for q in seq['questions_excluded']:
            for base_q in questions_updated:
                if base_q['id'] == q['id']:
                    if 'programs_final' not in base_q:
                        base_q['programs_final'] = []

                    base_q['programs_final'].append({
                        'program': prog_name,
                        'status': 'excluded',
                        'reason': q.get('exclusion_reason', 'unknown')
                    })
                    break

    # Сохранить обновленную базу
    data['questions'] = questions_updated

    final_db_file = Path('intelligent_question_core/data/selfology_final_sequenced.json')
    with open(final_db_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    # Статистика
    print(f"\n\n{'='*80}")
    print(f"📊 ИТОГОВАЯ СТАТИСТИКА:\n")

    print(f"✅ Программ с вопросами: {len(programs_with_questions)}")
    for prog_name in programs_with_questions[:10]:
        seq = next(s for s in all_sequences if s['program'] == prog_name)
        print(f"   • {prog_name}: {seq['included_count']} вопросов")

    if len(programs_with_questions) > 10:
        print(f"   ... и еще {len(programs_with_questions) - 10}")

    print(f"\n❌ Программ без вопросов (требуют генерации): {len(programs_without_questions)}")
    for prog_name in programs_without_questions:
        print(f"   • {prog_name}")

    total_included = sum(s['included_count'] for s in all_sequences)
    total_excluded = sum(s['excluded_count'] for s in all_sequences)

    print(f"\n📈 Общая статистика вопросов:")
    print(f"   Включено в программы: {total_included}")
    print(f"   Исключено: {total_excluded}")

    print(f"\n💾 Файлы сохранены:")
    print(f"   • {output_file}")
    print(f"   • {final_db_file}")

if __name__ == '__main__':
    main()