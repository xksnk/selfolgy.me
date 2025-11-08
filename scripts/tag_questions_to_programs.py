#!/usr/bin/env python3
"""
ЭТАП 1: Маркировка вопросов программами
Проходим по всем 1331 вопросам и определяем в какие программы каждый подходит
"""
import json
from pathlib import Path
from collections import defaultdict
import re

def normalize_text(text):
    """Нормализовать текст для анализа"""
    return text.lower().strip()

def calculate_relevance(question, program):
    """
    Вычислить релевантность вопроса к программе
    Возвращает score от 0.0 до 1.0
    """
    score = 0.0

    # Данные вопроса
    q_domain = question['classification']['domain']
    q_text = normalize_text(question['text'])
    q_energy = question['classification']['energy_dynamic']
    q_depth = question['classification']['depth_level']

    # 1. Совпадение по domain (вес 30%)
    if q_domain in program['domains']:
        score += 0.3

    # 2. Совпадение по темам в тексте вопроса (вес 40%)
    theme_matches = 0
    for theme in program['themes']:
        if normalize_text(theme) in q_text:
            theme_matches += 1

    if theme_matches > 0:
        score += min(0.4, theme_matches * 0.2)

    # 3. Специальные правила для программ (вес 30%)

    # ГОТОВЫЕ ПРОГРАММЫ (P0) - улучшенная логика
    if program['name'] == 'Ресурс':
        if any(word in q_text for word in ['энерг', 'сил', 'ресурс', 'восстанов', 'отдых', 'гордитесь', 'помог']):
            score += 0.3
        elif q_energy in ['OPENING', 'HEALING']:
            score += 0.2

    elif program['name'] == 'Изучить себя':
        if any(word in q_text for word in ['кто вы', 'кто ты', 'опиш себя', 'какой ты', 'какой вы', 'характер', 'личность']):
            score += 0.3
        elif q_domain == 'IDENTITY' and q_depth in ['CONSCIOUS', 'SURFACE']:
            score += 0.2

    elif program['name'] == 'Мечтатели':
        if any(word in q_text for word in ['мечт', 'мир', 'измени', 'идеальн', 'будущ', 'команд']):
            score += 0.3
        elif 'FUTURE' in program['domains'] and q_domain in ['IDENTITY', 'GOALS']:
            score += 0.2

    elif program['name'] == 'Отношение с самим собой':
        if any(word in q_text for word in ['отношени с собой', 'люб к себе', 'принима себя', 'критику', 'самокритик']):
            score += 0.4
        elif q_domain == 'IDENTITY' and any(word in q_text for word in ['себя', 'собой']):
            score += 0.2

    elif program['name'] == 'Тренажёр, чтобы начать жить':
        if any(word in q_text for word in ['начать', 'действ', 'сдела', 'застой', 'двига', 'шаг']):
            score += 0.3

    elif program['name'] == 'Подумать о жизни':
        if any(word in q_text for word in ['смысл', 'жизн', 'ценност', 'важно', 'главно']):
            score += 0.3
        elif q_domain in ['VALUES', 'SPIRITUALITY', 'IDENTITY']:
            score += 0.2

    elif program['name'] == 'Улучшить эмоциональное состояние':
        if q_domain == 'EMOTIONS' or any(word in q_text for word in ['чувств', 'эмоци', 'настроен', 'состояни']):
            score += 0.3

    elif program['name'] == 'Подумать о карьере или бизнесе':
        if q_domain == 'WORK' or any(word in q_text for word in ['работ', 'карьер', 'бизнес', 'професси']):
            score += 0.3

    elif program['name'] == 'Перебрать цели':
        if q_domain == 'GOALS' or any(word in q_text for word in ['цел', 'достиже', 'хоч', 'хотел бы', 'мечта']):
            score += 0.3

    elif program['name'] == 'Задуматься о здоровье':
        if q_domain == 'BODY' or any(word in q_text for word in ['здоров', 'тело', 'физич', 'сон', 'питан']):
            score += 0.3

    # КРИТИЧЕСКИЕ ПРОГРАММЫ (P1)
    elif program['name'] == 'Исцеление прошлого':
        if q_depth in ['SHADOW', 'CORE'] or q_domain == 'PAST':
            score += 0.3
        elif any(word in q_text for word in ['прошл', 'детст', 'трав', 'прости', 'боль']):
            score += 0.3
        elif q_energy == 'HEALING':
            score += 0.2

    elif program['name'] == 'Работа со страхами':
        if q_domain == 'FEARS':
            score += 0.4
        elif any(word in q_text for word in ['страх', 'боя', 'тревог', 'опаса', 'пугает']):
            score += 0.3

    elif program['name'] == 'Выгорание → Ресурс':
        if any(word in q_text for word in ['устал', 'выгор', 'истощ', 'энерг на нуле', 'восстанов']):
            score += 0.4

    elif program['name'] == 'Границы личности':
        if any(word in q_text for word in ['границ', 'отказ', 'должен', 'обязан', 'нет', 'согласи']):
            score += 0.3

    elif program['name'] == 'Разобраться в отношениях':
        if q_domain == 'RELATIONSHIPS':
            score += 0.3
        elif any(word in q_text for word in ['отношени', 'партнер', 'близк', 'любов', 'конфликт']):
            score += 0.3

    # КЛАССИЧЕСКИЕ (P2)
    elif program['name'] == 'Тело и эмоции':
        if q_domain == 'BODY' or any(word in q_text for word in ['тел', 'ощущ', 'чувств', 'соматик']):
            score += 0.3

    elif program['name'] == 'Деньги и самоценность':
        if any(word in q_text for word in ['деньг', 'финанс', 'богат', 'бедн', 'заработ', 'ценность']):
            score += 0.3

    return min(1.0, score)

def main():
    print("🏷️  ЭТАП 1: МАРКИРОВКА ВОПРОСОВ ПРОГРАММАМИ\n")
    print("="*80)

    # Загрузить базу вопросов (будет обновлена после дедупликации)
    db_file = Path('intelligent_question_core/data/selfology_questions_deduplicated.json')
    with open(db_file, 'r', encoding='utf-8') as f:
        db_data = json.load(f)

    questions = db_data['questions']

    # Загрузить список программ
    programs_file = Path('prompts/all_programs_list.json')
    with open(programs_file, 'r', encoding='utf-8') as f:
        programs = json.load(f)

    print(f"📊 Вопросов: {len(questions)}")
    print(f"📊 Программ: {len(programs)}\n")

    # Статистика
    tagged_count = 0
    program_stats = defaultdict(int)

    # Маркировка
    for i, question in enumerate(questions, 1):
        if i % 100 == 0:
            print(f"   Обработано: {i}/{len(questions)}...")

        # Анализ релевантности к каждой программе
        programs_tagged = []

        for program in programs:
            score = calculate_relevance(question, program)

            # Порог релевантности: 0.4 (снижен для лучшего охвата)
            if score >= 0.4:
                programs_tagged.append({
                    'program': program['name'],
                    'relevance_score': round(score, 2),
                    'status': 'tagged'  # будет pending/approved/excluded после этапа 2
                })
                program_stats[program['name']] += 1

        # Добавить метаданные
        question['programs_tagged'] = programs_tagged

        if programs_tagged:
            tagged_count += 1

    # Сохранить результат
    output_file = Path('intelligent_question_core/data/selfology_questions_tagged.json')

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(db_data, f, ensure_ascii=False, indent=2)

    print(f"\n\n{'='*80}")
    print(f"✅ МАРКИРОВКА ЗАВЕРШЕНА\n")
    print(f"📊 Вопросов с программами: {tagged_count}/{len(questions)} ({tagged_count/len(questions)*100:.1f}%)")
    print(f"📊 Вопросов без программ: {len(questions) - tagged_count}")

    print(f"\n\n📋 СТАТИСТИКА ПО ПРОГРАММАМ:\n")

    for program in sorted(programs, key=lambda p: (p['priority'], p['name'])):
        count = program_stats.get(program['name'], 0)
        status_emoji = "✅" if program['status'] == 'ready' else "📋"
        priority_label = f"P{program['priority']}"

        print(f"{status_emoji} [{priority_label}] {program['name']}: {count} вопросов")

    print(f"\n💾 Результат сохранен: {output_file}")

    # Примеры маркировки
    print(f"\n\n🔍 ПРИМЕРЫ МАРКИРОВКИ:\n")

    examples_shown = 0
    for q in questions[:100]:  # Первые 100 вопросов
        if q['programs_tagged'] and examples_shown < 5:
            print(f"ID: {q['id']}")
            print(f"Текст: {q['text'][:70]}...")
            print(f"Домен: {q['classification']['domain']}")
            print(f"Программы ({len(q['programs_tagged'])}):")
            for prog in q['programs_tagged']:
                print(f"   • {prog['program']} (score: {prog['relevance_score']})")
            print()
            examples_shown += 1

if __name__ == '__main__':
    main()
