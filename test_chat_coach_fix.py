#!/usr/bin/env python3
"""
Test script for ChatCoachService fix - onboarding answers type conversion
"""
import asyncio
import sys
import os

# Set up path
sys.path.insert(0, '/home/ksnk/n8n-enterprise/projects/selfology')
os.chdir('/home/ksnk/n8n-enterprise/projects/selfology')

from selfology_bot.database.service import DatabaseService
from services.chat_coach import ChatCoachService


async def test_chat_coach_fix():
    """Test that ChatCoachService can now load onboarding answers"""

    print("=" * 80)
    print("ТЕСТ ИСПРАВЛЕНИЯ: ChatCoachService.get_onboarding_answers()")
    print("=" * 80)

    # Initialize database
    db_service = DatabaseService()
    await db_service.initialize()

    # Initialize ChatCoachService
    chat_service = ChatCoachService(db_pool=db_service.pool)

    # Test user_id
    test_user_id = "98005572"

    print(f"\n1. Тестируем пользователя: {test_user_id}")
    print("-" * 80)

    # Test start_chat_session (это вызывает _load_user_context)
    print("\n2. Запуск чат-сессии (вызывает get_onboarding_answers)...")
    try:
        response = await chat_service.start_chat_session(test_user_id)

        if response.success:
            print(f"   ✅ УСПЕХ!")
            print(f"   Message: {response.message}")
            print(f"   Processing time: {response.processing_time:.3f}s")
            print(f"\n   Welcome message:")
            print(f"   {response.response_text[:200]}...")
        else:
            print(f"   ❌ ОШИБКА: {response.message}")
            return False

    except Exception as e:
        print(f"   ❌ ИСКЛЮЧЕНИЕ: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Direct test of get_onboarding_answers
    print("\n3. Прямой тест get_onboarding_answers()...")
    try:
        from data_access.user_dao import UserDAO
        user_dao = UserDAO(db_pool=db_service.pool)

        answers = await user_dao.get_onboarding_answers(test_user_id, limit=30)
        print(f"   ✅ Загружено ответов: {len(answers)}")

        if answers:
            print(f"\n   Пример первого ответа:")
            first = answers[0]
            print(f"   - question_id: {first.get('question_json_id')}")
            print(f"   - answer: {first.get('raw_answer', '')[:100]}...")
            print(f"   - answered_at: {first.get('answered_at')}")

    except Exception as e:
        print(f"   ❌ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
        return False

    print("\n" + "=" * 80)
    print("✅ ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
    print("=" * 80)

    # Cleanup
    await db_service.close()

    return True


if __name__ == "__main__":
    success = asyncio.run(test_chat_coach_fix())
    sys.exit(0 if success else 1)
