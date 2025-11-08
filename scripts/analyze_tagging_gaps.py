#!/usr/bin/env python3
"""
Анализ пробелов в маркировке
Понять почему 780 вопросов без меток и 11 программ без вопросов
"""
import json
from pathlib import Path
from collections import Counter

def main():
    print("🔍 АНАЛИЗ ПРОБЕЛОВ В МАРКИРОВКЕ\n")
    print("="*80)

    # Загрузить данные
    data = json.load(open('intelligent_question_core/data/selfology_questions_tagged.json'))
    programs = json.load(open('prompts/all_programs_list.json'))

    questions = data['questions']

    # Разделить на помеченные и непомеченные
    tagged = [q for q in questions if q.get('programs_tagged', [])]
    untagged = [q for q in questions if not q.get('programs_tagged', [])]

    print(f"📊 Помечено: {len(tagged)} вопросов")
    print(f"📊 Не помечено: {len(untagged)} вопросов\n")

    # Анализ непомеченных
    print("="*80)
    print("🔎 АНАЛИЗ НЕПОМЕЧЕННЫХ ВОПРОСОВ (780)\n")

    # По доменам
    untagged_domains = Counter(q['classification']['domain'] for q in untagged)
    print("По доменам:")
    for domain, count in sorted(untagged_domains.items(), key=lambda x: -x[1])[:15]:
        print(f"  {domain}: {count} вопросов")

    # По глубине
    untagged_depths = Counter(q['classification']['depth_level'] for q in untagged)
    print("\nПо глубине:")
    for depth, count in sorted(untagged_depths.items(), key=lambda x: -x[1]):
        print(f"  {depth}: {count} вопросов")

    # По энергетике
    untagged_energy = Counter(q['classification']['energy_dynamic'] for q in untagged)
    print("\nПо энергетике:")
    for energy, count in sorted(untagged_energy.items(), key=lambda x: -x[1]):
        print(f"  {energy}: {count} вопросов")

    # Примеры непомеченных вопросов
    print("\n\n🔍 ПРИМЕРЫ НЕПОМЕЧЕННЫХ ВОПРОСОВ:\n")
    for i, q in enumerate(untagged[:20], 1):
        print(f"{i}. [{q['classification']['domain']}] {q['text'][:80]}...")

    # Анализ программ без вопросов
    print("\n\n" + "="*80)
    print("🔎 АНАЛИЗ ПРОГРАММ БЕЗ ВОПРОСОВ (11)\n")

    zero_programs = []
    for prog in programs:
        count = sum(1 for q in questions
                   for tagged_prog in q.get('programs_tagged', [])
                   if tagged_prog['program'] == prog['name'])

        if count == 0:
            zero_programs.append(prog)
            print(f"\n📋 {prog['name']} (P{prog['priority']})")
            print(f"   Темы: {', '.join(prog['themes'][:3])}")
            print(f"   Домены: {', '.join(prog['domains'])}")

            # Поиск потенциально подходящих вопросов
            potential = []
            for q in questions:
                q_text = q['text'].lower()
                q_domain = q['classification']['domain']

                # Проверка по доменам
                if q_domain in prog['domains']:
                    # Проверка по темам в тексте
                    for theme in prog['themes']:
                        if theme.lower() in q_text:
                            potential.append(q)
                            break

            print(f"   ⚠️  Потенциально подходящих (по домену+теме в тексте): {len(potential)}")
            if potential:
                print(f"   Примеры:")
                for q in potential[:3]:
                    print(f"      • {q['text'][:70]}...")

    # Анализ порога релевантности
    print("\n\n" + "="*80)
    print("📈 АНАЛИЗ ПОРОГА РЕЛЕВАНТНОСТИ\n")

    # Собрать все scores
    all_scores = []
    for q in questions:
        for tagged in q.get('programs_tagged', []):
            all_scores.append(tagged['relevance_score'])

    if all_scores:
        print(f"Всего связей создано: {len(all_scores)}")
        print(f"Минимальный score: {min(all_scores)}")
        print(f"Максимальный score: {max(all_scores)}")
        print(f"Средний score: {sum(all_scores)/len(all_scores):.2f}")

        # Распределение по диапазонам
        ranges = {
            '0.5-0.6': sum(1 for s in all_scores if 0.5 <= s < 0.6),
            '0.6-0.7': sum(1 for s in all_scores if 0.6 <= s < 0.7),
            '0.7-0.8': sum(1 for s in all_scores if 0.7 <= s < 0.8),
            '0.8-0.9': sum(1 for s in all_scores if 0.8 <= s < 0.9),
            '0.9-1.0': sum(1 for s in all_scores if 0.9 <= s <= 1.0),
        }

        print("\nРаспределение по score:")
        for range_name, count in ranges.items():
            print(f"  {range_name}: {count} связей")

    # Рекомендации
    print("\n\n" + "="*80)
    print("💡 РЕКОМЕНДАЦИИ:\n")

    print("1. Программы без вопросов:")
    print("   • 2 программы P0 (Отношение с собой, Тренажёр) - требуют СРОЧНОЙ генерации")
    print("   • 6 программ P3 - современные темы, требуют генерации новых вопросов")
    print("   • 3 программы P4 (микро) - узкие темы, генерация\n")

    print("2. Непомеченные вопросы:")
    top_untagged_domain = untagged_domains.most_common(1)[0]
    print(f"   • Топ домен: {top_untagged_domain[0]} ({top_untagged_domain[1]} вопросов)")
    print(f"   • Нужно улучшить логику для этих доменов\n")

    print("3. Следующие шаги:")
    print("   • Снизить порог с 0.5 до 0.4 для расширения охвата")
    print("   • Добавить семантический поиск (embeddings) вместо keyword matching")
    print("   • Создать генератор вопросов для 11 программ без вопросов")

if __name__ == '__main__':
    main()
