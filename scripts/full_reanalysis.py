#!/usr/bin/env python3
"""
Полный перезапуск анализа для пользователя

Этот скрипт:
1. Получает все ответы пользователя
2. Запускает AI анализ для каждого ответа
3. Извлекает конкретику (PersonalityExtractor)
4. Создает векторы в Qdrant
5. Формирует цифровую личность
"""

import asyncio
import asyncpg
import sys
import os
import json
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from selfology_bot.analysis.answer_analyzer import AnswerAnalyzer
from selfology_bot.analysis.personality_extractor import PersonalityExtractor
from selfology_bot.analysis.embedding_creator import EmbeddingCreator

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "user": "n8n",
    "password": "sS67wM+1zMBRFHAW4kj9HwFl5J6+veo7Nirx0/I+oiU=",
    "database": "n8n"
}

USER_ID = 98005572


def load_questions_from_json():
    """Загрузить вопросы из JSON файла"""
    json_path = os.path.join(
        os.path.dirname(__file__),
        '../intelligent_question_core/data/selfology_intelligent_core.json'
    )

    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # Файл содержит словарь с ключом 'questions'
            questions_list = data['questions']
            # Конвертируем список в словарь по ID
            return {q['id']: q for q in questions_list}
    except Exception as e:
        print(f"⚠️ Не удалось загрузить вопросы: {e}")
        return {}


# Загружаем вопросы один раз при импорте
QUESTIONS_CACHE = load_questions_from_json()


async def get_question_text(conn, question_json_id: str) -> tuple[str, dict]:
    """Получить текст вопроса из кеша или метаданных"""

    # Пытаемся найти в кеше вопросов
    if question_json_id in QUESTIONS_CACHE:
        # Возвращаем ПОЛНЫЙ объект вопроса как есть
        return QUESTIONS_CACHE[question_json_id]['text'], QUESTIONS_CACHE[question_json_id]

    # Получаем метаданные из questions_metadata
    question_meta = await conn.fetchrow("""
        SELECT json_id, domain, depth_level, energy
        FROM selfology.questions_metadata
        WHERE json_id = $1
    """, question_json_id)

    metadata = {
        "domain": "GENERAL",
        "depth_level": "surface",
        "energy_dynamic": "neutral"
    }

    if question_meta:
        metadata = {
            "domain": question_meta.get('domain', 'GENERAL'),
            "depth_level": question_meta.get('depth_level', 'surface'),
            "energy_dynamic": question_meta.get('energy', 'neutral')
        }

    # Используем placeholder для текста
    return f"Вопрос {question_json_id}", metadata


def safe_deserialize_personality_field(value):
    """
    Безопасно десериализовать поле personality

    Args:
        value: Значение из БД (может быть: JSON строка, список, None)

    Returns:
        Список (пустой если не удалось десериализовать)
    """
    # Если None - вернуть пустой список
    if value is None:
        return []

    # Если уже список - вернуть как есть
    if isinstance(value, list):
        return value

    # Если строка - попытаться распарсить JSON
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            # Убедиться что это список
            if isinstance(parsed, list):
                return parsed
            else:
                print(f"⚠️ JSON содержит не список: {type(parsed)}, возвращаем пустой массив")
                return []
        except json.JSONDecodeError as e:
            print(f"⚠️ Не удалось распарсить JSON: {e}, возвращаем пустой массив")
            return []

    # Для всех других типов - пустой список
    print(f"⚠️ Неожиданный тип данных: {type(value)}, возвращаем пустой массив")
    return []


async def process_answer(
    answer_id: int,
    question_json_id: str,
    user_answer: str,
    session_id: int,
    conn: asyncpg.Connection,
    analyzer: AnswerAnalyzer,
    extractor: PersonalityExtractor
):
    """Обработать один ответ"""

    print(f"\n{'='*70}")
    print(f"📝 ОТВЕТ #{answer_id}: {question_json_id}")
    print(f"{'='*70}")

    # 1. Получить текст вопроса и полный объект
    question_text, question_data = await get_question_text(conn, question_json_id)
    print(f"❓ Вопрос: {question_text[:100]}...")
    print(f"💬 Ответ: {user_answer[:100]}...")

    # 2. Запустить AI анализ
    print(f"\n🤖 Запуск AI анализа...")

    try:
        # question_data уже содержит ВСЕ нужные поля из JSON
        analysis_result = await analyzer.analyze_answer(
            question_data=question_data,
            user_answer=user_answer,
            user_context={
                "user_id": USER_ID,
                "session_id": session_id,
                "answer_history": [],
                "question_history": []
            }
        )

        # Проверить наличие personality_summary
        if "personality_summary" not in analysis_result:
            print("⚠️ WARNING: personality_summary не создан в анализе!")
            return False

        print(f"✅ Анализ готов:")
        print(f"   - personality_summary: {analysis_result['personality_summary'].get('nano', 'N/A')[:80]}...")
        print(f"   - Модель: {analysis_result['processing_metadata']['model_used']}")

        # 3. Сохранить анализ в БД
        print(f"\n💾 Сохранение анализа в БД...")

        analysis_id = await conn.fetchval("""
            INSERT INTO selfology.answer_analysis (
                user_answer_id,
                raw_ai_response,
                ai_model_used,
                analysis_version
            ) VALUES ($1, $2, $3, $4)
            RETURNING id
        """,
            answer_id,
            json.dumps(analysis_result, ensure_ascii=False),
            analysis_result['processing_metadata']['model_used'],
            analysis_result.get('analysis_version', '2.0')
        )

        print(f"✅ Анализ сохранен с ID: {analysis_id}")

        # 4. Обновить статус ответа
        await conn.execute("""
            UPDATE selfology.user_answers_new
            SET analysis_status = 'analyzed'
            WHERE id = $1
        """, answer_id)

        # 5. Извлечь конкретику
        print(f"\n🧠 Извлечение конкретики...")

        # Получить существующую digital_personality
        existing_personality = await conn.fetchrow("""
            SELECT identity, interests, skills, goals, barriers, relationships,
                   values, health, current_state
            FROM selfology.digital_personality
            WHERE user_id = $1
        """, USER_ID)

        # ИСПРАВЛЕНИЕ: Безопасная десериализация ВСЕХ полей
        existing_data = {}
        if existing_personality:
            for key in ['identity', 'interests', 'skills', 'goals', 'barriers',
                       'relationships', 'values', 'health', 'current_state']:
                # Используем безопасную десериализацию
                value = existing_personality[key]
                existing_data[key] = safe_deserialize_personality_field(value)

                # Debug: показать тип и размер
                print(f"   - {key}: {type(existing_data[key]).__name__} with {len(existing_data[key])} items")

        extracted = await extractor.extract_from_answer(
            question_text=question_text,
            user_answer=user_answer,
            question_metadata=question_data,  # Передаем полный объект вопроса
            existing_personality=existing_data if existing_data else None
        )

        # Объединить с существующими данными
        merged = extractor.merge_extractions(existing_data, extracted)

        print(f"✅ Извлечено:")
        print(f"   - interests: {len(merged.get('interests', []))} items")
        print(f"   - goals: {len(merged.get('goals', []))} items")
        print(f"   - skills: {len(merged.get('skills', []))} items")

        # 6. Обновить digital_personality
        await conn.execute("""
            INSERT INTO selfology.digital_personality (
                user_id, identity, interests, skills, goals, barriers,
                relationships, values, health, current_state,
                total_answers_analyzed, last_updated
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, 1, NOW())
            ON CONFLICT (user_id) DO UPDATE SET
                identity = $2,
                interests = $3,
                skills = $4,
                goals = $5,
                barriers = $6,
                relationships = $7,
                values = $8,
                health = $9,
                current_state = $10,
                total_answers_analyzed = selfology.digital_personality.total_answers_analyzed + 1,
                last_updated = NOW()
        """,
            USER_ID,
            json.dumps(merged.get('identity', []), ensure_ascii=False),
            json.dumps(merged.get('interests', []), ensure_ascii=False),
            json.dumps(merged.get('skills', []), ensure_ascii=False),
            json.dumps(merged.get('goals', []), ensure_ascii=False),
            json.dumps(merged.get('barriers', []), ensure_ascii=False),
            json.dumps(merged.get('relationships', []), ensure_ascii=False),
            json.dumps(merged.get('values', []), ensure_ascii=False),
            json.dumps(merged.get('health', []), ensure_ascii=False),
            json.dumps(merged.get('current_state', []), ensure_ascii=False)
        )

        print(f"✅ digital_personality обновлен")

        return True

    except Exception as e:
        print(f"❌ Ошибка при обработке: {e}")
        import traceback
        traceback.print_exc()
        return False


async def create_vectors(conn: asyncpg.Connection, embedding_creator: EmbeddingCreator):
    """Создать векторы в Qdrant"""

    print(f"\n{'='*70}")
    print(f"🎯 СОЗДАНИЕ ВЕКТОРОВ В QDRANT")
    print(f"{'='*70}")

    # Получить все анализы с personality_summary
    analyses = await conn.fetch("""
        SELECT aa.id, aa.raw_ai_response, ua.id as answer_id
        FROM selfology.answer_analysis aa
        JOIN selfology.user_answers_new ua ON aa.user_answer_id = ua.id
        JOIN selfology.onboarding_sessions os ON ua.session_id = os.id
        WHERE os.user_id = $1
          AND aa.raw_ai_response ? 'personality_summary'
        ORDER BY aa.id
    """, USER_ID)

    print(f"📊 Найдено анализов с personality_summary: {len(analyses)}")

    if not analyses:
        print("⚠️ Нет анализов для векторизации!")
        return

    # ИСПРАВЛЕНИЕ: Создаем векторы для последнего (самого полного) анализа
    # Берем последний анализ, т.к. он содержит агрегированную информацию
    last_analysis = analyses[-1]
    response = last_analysis['raw_ai_response']
    if isinstance(response, str):
        response = json.loads(response)

    print(f"\n🔄 Создание векторов для пользователя {USER_ID}...")
    print(f"   Используется анализ ID: {last_analysis['id']}")

    try:
        # ИСПРАВЛЕНИЕ: Передаем analysis_result вместо personality_summaries
        success = await embedding_creator.create_personality_vector(
            user_id=USER_ID,
            analysis_result=response,  # Передаем полный результат анализа
            is_update=True  # Это обновление существующего профиля
        )

        if success:
            print(f"✅ Векторы успешно созданы в Qdrant!")

            # Обновить статусы ответов на completed
            await conn.execute("""
                UPDATE selfology.user_answers_new ua
                SET analysis_status = 'completed'
                FROM selfology.onboarding_sessions os
                WHERE ua.session_id = os.id
                  AND os.user_id = $1
                  AND ua.analysis_status = 'analyzed'
            """, USER_ID)

            print(f"✅ Статусы обновлены на 'completed'")
        else:
            print(f"❌ Ошибка создания векторов")

    except Exception as e:
        print(f"❌ Ошибка при создании векторов: {e}")
        import traceback
        traceback.print_exc()


async def main():
    """Главная функция"""

    print("\n" + "🔄"*35)
    print("ПОЛНЫЙ ПЕРЕЗАПУСК АНАЛИЗА")
    print("🔄"*35)
    print(f"\nПользователь: {USER_ID}")
    print(f"Время начала: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # Инициализация
    conn = await asyncpg.connect(**DB_CONFIG)
    analyzer = AnswerAnalyzer()
    extractor = PersonalityExtractor()
    embedding_creator = EmbeddingCreator()

    try:
        # 1. Получить все ответы
        answers = await conn.fetch("""
            SELECT
                ua.id,
                ua.question_json_id,
                ua.raw_answer,
                ua.session_id
            FROM selfology.user_answers_new ua
            JOIN selfology.onboarding_sessions os ON ua.session_id = os.id
            WHERE os.user_id = $1
            ORDER BY ua.id
        """, USER_ID)

        print(f"📊 Найдено ответов: {len(answers)}")

        # 2. Обработать каждый ответ
        results = []
        for answer in answers:
            success = await process_answer(
                answer_id=answer['id'],
                question_json_id=answer['question_json_id'],
                user_answer=answer['raw_answer'],
                session_id=answer['session_id'],
                conn=conn,
                analyzer=analyzer,
                extractor=extractor
            )
            results.append((answer['id'], success))

            # Небольшая пауза между запросами
            await asyncio.sleep(1)

        # 3. Создать векторы в Qdrant
        await create_vectors(conn, embedding_creator)

        # 4. Итоги
        print(f"\n{'='*70}")
        print("📊 ИТОГИ")
        print(f"{'='*70}")

        successful = sum(1 for _, success in results if success)

        for answer_id, success in results:
            status = "✅ OK" if success else "❌ FAIL"
            print(f"  Ответ #{answer_id}: {status}")

        print(f"\n✅ Успешно обработано: {successful}/{len(results)}")

        if successful == len(results):
            print(f"\n🎉 ВСЕ ОТВЕТЫ УСПЕШНО ПРОАНАЛИЗИРОВАНЫ!")
        else:
            print(f"\n⚠️ Некоторые ответы не удалось обработать")

        print(f"\nВремя завершения: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
