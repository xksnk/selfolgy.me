#!/usr/bin/env python3
"""
Дедупликация вопросов в базе
Этап 1: Точные дубликаты
Этап 2: Семантически похожие (через embeddings)
"""
import json
from pathlib import Path
import re
from collections import defaultdict
import os
from openai import OpenAI
import numpy as np
from tqdm import tqdm
from dotenv import load_dotenv

# Загрузить переменные окружения из .env
load_dotenv()

def normalize_text(text):
    """Нормализовать текст для сравнения"""
    # Убрать лишние пробелы, знаки препинания
    text = re.sub(r'\s+', ' ', text)
    text = text.strip().lower()
    # Убрать знаки препинания в конце
    text = text.rstrip('?.!,;:')
    return text

def cosine_similarity(vec1, vec2):
    """Косинусное сходство между двумя векторами"""
    return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))

def main():
    print("🔍 ДЕДУПЛИКАЦИЯ ВОПРОСОВ\n")
    print("="*80)

    # Загрузить базу
    data_file = Path('intelligent_question_core/data/selfology_questions_with_generated.json')
    with open(data_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    questions = data['questions']
    print(f"📊 Всего вопросов: {len(questions)}\n")

    # ========================================
    # ЭТАП 1: ТОЧНЫЕ ДУБЛИКАТЫ
    # ========================================
    print("="*80)
    print("📋 ЭТАП 1: ПОИСК ТОЧНЫХ ДУБЛИКАТОВ\n")

    # Индекс: нормализованный текст -> список вопросов
    text_index = defaultdict(list)

    for q in questions:
        norm_text = normalize_text(q['text'])
        text_index[norm_text].append(q)

    # Найти дубликаты
    exact_duplicates = 0
    duplicate_groups = []

    for norm_text, q_list in text_index.items():
        if len(q_list) > 1:
            # Сортировать по ID (первый будет мастер)
            q_list.sort(key=lambda x: x['id'])
            master = q_list[0]
            duplicates = q_list[1:]

            duplicate_groups.append({
                'master': master['id'],
                'duplicates': [q['id'] for q in duplicates],
                'text': master['text'][:80]
            })

            # Пометить дубликаты
            for dup in duplicates:
                dup['duplicate_of'] = master['id']
                exact_duplicates += 1

    print(f"✅ Найдено групп дубликатов: {len(duplicate_groups)}")
    print(f"✅ Всего точных дубликатов: {exact_duplicates}")

    if duplicate_groups:
        print(f"\n🔍 ПРИМЕРЫ ДУБЛИКАТОВ:\n")
        for i, group in enumerate(duplicate_groups[:5], 1):
            print(f"{i}. Мастер: {group['master']}")
            print(f"   Текст: {group['text']}...")
            print(f"   Дубликаты: {', '.join(group['duplicates'])}\n")

    # ========================================
    # ЭТАП 2: СЕМАНТИЧЕСКИ ПОХОЖИЕ
    # ========================================
    print("\n" + "="*80)
    print("🧠 ЭТАП 2: ПОИСК СЕМАНТИЧЕСКИ ПОХОЖИХ ВОПРОСОВ\n")

    # Проверить API ключ
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("⚠️  OPENAI_API_KEY не найден в .env")
        print("   Пропускаем семантический анализ")
        semantic_similar = 0
    else:
        client = OpenAI(api_key=api_key)

        # Отфильтровать только мастер-вопросы (без дубликатов)
        master_questions = [q for q in questions if 'duplicate_of' not in q]
        print(f"📊 Анализируем {len(master_questions)} уникальных вопросов")

        # Создать embeddings для всех вопросов
        print("\n🔄 Создание embeddings...")
        texts = [q['text'] for q in master_questions]

        embeddings = []
        batch_size = 100

        for i in tqdm(range(0, len(texts), batch_size), desc="Embeddings"):
            batch = texts[i:i+batch_size]
            response = client.embeddings.create(
                model="text-embedding-3-small",
                input=batch
            )
            batch_embeddings = [item.embedding for item in response.data]
            embeddings.extend(batch_embeddings)

        print(f"✅ Создано {len(embeddings)} embeddings\n")

        # Поиск похожих
        print("🔍 Поиск семантически похожих (similarity > 0.85)...\n")

        semantic_similar = 0
        similar_pairs = []

        for i in tqdm(range(len(master_questions)), desc="Сравнение"):
            q1 = master_questions[i]
            emb1 = embeddings[i]

            similar_to = []

            for j in range(i+1, len(master_questions)):
                q2 = master_questions[j]
                emb2 = embeddings[j]

                similarity = cosine_similarity(emb1, emb2)

                if similarity > 0.85:
                    similar_to.append({
                        'id': q2['id'],
                        'similarity': round(float(similarity), 3),
                        'text': q2['text'][:60]
                    })
                    semantic_similar += 1

                    similar_pairs.append({
                        'q1_id': q1['id'],
                        'q1_text': q1['text'][:60],
                        'q2_id': q2['id'],
                        'q2_text': q2['text'][:60],
                        'similarity': round(float(similarity), 3)
                    })

            if similar_to:
                if 'similar_to' not in q1:
                    q1['similar_to'] = []
                q1['similar_to'].extend(similar_to)

        print(f"\n✅ Найдено семантически похожих пар: {semantic_similar}")

        if similar_pairs:
            print(f"\n🔍 ПРИМЕРЫ ПОХОЖИХ ВОПРОСОВ:\n")
            for i, pair in enumerate(similar_pairs[:10], 1):
                print(f"{i}. [{pair['similarity']}] Похожесть:")
                print(f"   {pair['q1_id']}: {pair['q1_text']}...")
                print(f"   {pair['q2_id']}: {pair['q2_text']}...\n")

    # ========================================
    # СОХРАНЕНИЕ
    # ========================================
    print("="*80)
    print("💾 СОХРАНЕНИЕ РЕЗУЛЬТАТОВ\n")

    output_file = Path('intelligent_question_core/data/selfology_questions_deduplicated.json')

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"✅ Сохранено: {output_file}")

    # Статистика
    duplicates_count = sum(1 for q in questions if 'duplicate_of' in q)
    similar_count = sum(1 for q in questions if 'similar_to' in q)
    clean_count = len(questions) - duplicates_count

    print(f"\n\n{'='*80}")
    print(f"📊 ИТОГОВАЯ СТАТИСТИКА:\n")
    print(f"Всего вопросов: {len(questions)}")
    print(f"Точных дубликатов: {duplicates_count}")
    print(f"Уникальных вопросов: {clean_count}")
    print(f"Вопросов с похожими: {similar_count}")
    print(f"Семантически похожих пар: {semantic_similar}")

    print(f"\n💡 РЕКОМЕНДАЦИИ:")
    print(f"• При секвенировании игнорировать вопросы с duplicate_of")
    print(f"• Вопросы с similar_to выбирать осознанно - иногда нужны вариации")
    print(f"• После завершения можно физически удалить дубликаты")

if __name__ == '__main__':
    main()
