#!/usr/bin/env python3
"""
Простой тест исправления get_onboarding_answers()
"""
import asyncio
import asyncpg
import sys
import os

sys.path.insert(0, '/home/ksnk/n8n-enterprise/projects/selfology')
os.chdir('/home/ksnk/n8n-enterprise/projects/selfology')


async def test_fix():
    """Test the fix directly"""

    print("=" * 80)
    print("ТЕСТ ИСПРАВЛЕНИЯ: UserDAO.get_onboarding_answers()")
    print("=" * 80)

    # Create database pool
    pool = await asyncpg.create_pool(
        host='localhost',
        port=5432,
        user='n8n',
        password='sS67wM+1zMBRFHAW4kj9HwFl5J6+veo7Nirx0/I+oiU=',
        database='n8n',
        min_size=1,
        max_size=5
    )

    test_user_id = "98005572"

    print(f"\n1. Тестируем пользователя: {test_user_id} (как строка)")
    print("-" * 80)

    # Import UserDAO
    from data_access.user_dao import UserDAO
    user_dao = UserDAO(db_pool=pool)

    # Test get_onboarding_answers
    print("\n2. Вызов get_onboarding_answers()...")
    try:
        answers = await user_dao.get_onboarding_answers(test_user_id, limit=30)

        print(f"   ✅ УСПЕХ! Загружено ответов: {len(answers)}")

        if answers:
            print(f"\n   Первые 3 ответа:")
            for i, answer in enumerate(answers[:3], 1):
                print(f"\n   #{i}:")
                print(f"   - question_id: {answer.get('question_json_id')}")
                raw = answer.get('raw_answer', '')
                print(f"   - answer: {raw[:80]}..." if len(raw) > 80 else f"   - answer: {raw}")
                print(f"   - answered_at: {answer.get('answered_at')}")

        print("\n" + "=" * 80)
        print("✅ ТЕСТ ПРОЙДЕН! Проблема с типами РЕШЕНА!")
        print("=" * 80)

        # Test with ChatCoachService
        print("\n3. Тестируем ChatCoachService._load_user_context()...")
        from services.chat_coach import ChatCoachService

        chat_service = ChatCoachService(db_pool=pool)

        user_context = await chat_service._load_user_context(test_user_id)
        print(f"   ✅ UserContext загружен!")
        print(f"   - onboarding_answers: {len(user_context.onboarding_answers)} items")
        print(f"   - recent_messages: {len(user_context.recent_messages)} items")
        print(f"   - insights_history: {len(user_context.insights_history)} items")

        print("\n" + "=" * 80)
        print("✅ ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
        print("=" * 80)

        success = True

    except Exception as e:
        print(f"   ❌ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
        success = False

    # Cleanup
    await pool.close()

    return success


if __name__ == "__main__":
    success = asyncio.run(test_fix())
    sys.exit(0 if success else 1)
