"""
Тест MVP чата по архитектуре из исследований.

Включает тесты:
- SessionManager: управление сессией
- ChatMVP: основной чат
- UserDossierService: AI-резюме личности
- Resistance handling: обработка сопротивления
"""

import asyncio
import sys
import os

# Добавляем путь к проекту
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from selfology_bot.services.onboarding.cluster_router import ClusterRouter
from selfology_bot.services.chat import (
    ChatMVP, SessionManager, BlockType,
    UserDossierService, UserDossier,
    CorrectionDetector, CheckInManager, DossierValidator
)


def test_session_manager():
    """Тест SessionManager"""
    print("=" * 60)
    print("TEST: SessionManager")
    print("=" * 60)

    # Инициализация
    router = ClusterRouter()
    manager = SessionManager(router)

    user_id = 12345

    # 1. Создание сессии
    session = manager.get_or_create_session(user_id)
    print(f"1. Created session: {session.session_id}")
    assert session.user_id == user_id
    assert session.program_id is None

    # 2. Выбор программы
    programs = router.get_all_programs()
    print(f"2. Available programs: {len(programs)}")

    if programs:
        program_id = programs[0]['id']
        session = manager.start_program(user_id, program_id)
        print(f"3. Started program: {session.program_name}")
        assert session.program_id == program_id

        # 4. Получение следующего блока
        next_block = manager.get_next_block(user_id)
        if next_block:
            print(f"4. Next block: {next_block['block_name']} ({next_block['block_type']})")
            assert next_block['block_id'] is not None

        # 5. Получение следующего вопроса
        next_question = manager.get_next_question(user_id)
        if next_question:
            print(f"5. Next question: {next_question['text'][:50]}...")
            assert next_question['id'] is not None

            # 6. Записать ответ
            manager.record_answer(user_id, next_question['id'], "Test answer")
            print(f"6. Recorded answer for question {next_question['id']}")

        # 7. Получить сводку
        summary = manager.get_session_summary(user_id)
        print(f"7. Summary: {summary['answered_questions']}/{summary['total_questions']} questions")
        print(f"   Completion: {summary['completion_percent']}%")

    print("\nSessionManager: PASSED")


async def test_chat_mvp():
    """Тест ChatMVP"""
    print("\n" + "=" * 60)
    print("TEST: ChatMVP")
    print("=" * 60)

    # Инициализация
    router = ClusterRouter()
    chat = ChatMVP(router)

    user_id = 54321

    # 1. Начать чат
    response = await chat.start_chat(user_id)
    print(f"1. Start chat: needs_program_selection={response.needs_program_selection}")
    assert response.success
    assert response.needs_program_selection

    # 2. Выбрать программу
    programs = response.available_programs
    if programs:
        program_id = programs[0]['id']
        response = await chat.select_program(user_id, program_id)
        print(f"2. Selected program: {response.message[:50]}...")
        assert response.success

        # 3. Получить следующий шаг
        response = await chat.get_next_step(user_id)
        print(f"3. Next step: {response.message[:50]}...")
        assert response.success

        if response.question:
            # 4. Отправить сообщение
            personality = {
                'openness': 0.7,
                'conscientiousness': 0.6,
                'extraversion': 0.5,
                'agreeableness': 0.8,
                'neuroticism': 0.3
            }
            response = await chat.process_message(
                user_id,
                "Это мой тестовый ответ на вопрос. Я размышляю о своей жизни.",
                personality=personality
            )
            print(f"4. Process message: {response.message[:50]}...")
            assert response.success

            # 5. Проверить статус
            status = chat.get_status(user_id)
            print(f"5. Status: {status.message}")
            assert status.session_summary is not None

    print("\nChatMVP: PASSED")


async def test_resistance_handling():
    """Тест обработки сопротивления"""
    print("\n" + "=" * 60)
    print("TEST: Resistance Handling")
    print("=" * 60)

    router = ClusterRouter()
    chat = ChatMVP(router)

    user_id = 99999

    # Настраиваем сессию
    await chat.start_chat(user_id)
    programs = router.get_all_programs()
    if programs:
        await chat.select_program(user_id, programs[0]['id'])
        await chat.get_next_step(user_id)

        # Отправляем сообщение с сопротивлением
        response = await chat.process_message(
            user_id,
            "Не хочу об этом говорить, давай о другом"
        )
        print(f"1. Resistance detected: {response.resistance_options is not None}")

        if response.resistance_options:
            print(f"2. Alternatives: {len(response.resistance_options.get('alternatives', []))}")
            print(f"3. Response: {response.message[:100]}...")
            assert response.resistance_options['resistance_detected']

    print("\nResistance Handling: PASSED")


def test_user_dossier_dataclass():
    """Тест UserDossier dataclass"""
    print("\n" + "=" * 60)
    print("TEST: UserDossier Dataclass")
    print("=" * 60)

    # Создаём досье вручную
    dossier = UserDossier(
        user_id=12345,
        who="Журналист 30+, ведёт блоги о позитивном взгляде на мир",
        top_goals=[
            "Создать медиа компанию",
            "Найти друзей для совместных выходных",
            "Достичь финансовой стабильности через блоги"
        ],
        top_barriers=[
            "Внутренний конфликт: хочу страдать vs желание радости",
            "Не могу ценить хорошее (защитный механизм?)",
            "Тревога, страх неопределённости"
        ],
        patterns=[
            "Говорит о тревоге часто (5 из 10 ответов)",
            "Амбивалентность к успеху",
            "Ищет направление в жизни"
        ],
        contradictions=[
            "Цель 'спокойствие' vs барьер 'хочу страдать'",
            "Хочет друзей vs избегает людей"
        ],
        hypothesis="Защитный механизм - если не привязываться к хорошему, не будет больно его терять",
        style_hints={
            "подход": "творческий, философский",
            "энергия": "спокойная, рефлексивная",
            "безопасность": "высокая, много reassurance"
        }
    )

    print(f"1. Created dossier for user {dossier.user_id}")
    assert dossier.user_id == 12345
    assert len(dossier.top_goals) == 3
    assert len(dossier.top_barriers) == 3

    # 2. Тест to_prompt_context
    context = dossier.to_prompt_context()
    print(f"2. Generated context: {len(context)} chars")
    assert "КТО:" in context
    assert "ГЛАВНЫЕ ЦЕЛИ:" in context
    assert "ГЛАВНЫЕ БАРЬЕРЫ:" in context
    assert "ПАТТЕРНЫ:" in context
    assert "ПРОТИВОРЕЧИЯ:" in context
    assert "КАК ОБЩАТЬСЯ:" in context

    # 3. Проверяем что контекст короткий
    print(f"3. Context length: {len(context)} chars (target: <2000)")
    assert len(context) < 2000  # Должно быть ~500-1000 токенов

    print("\nUserDossier Dataclass: PASSED")


def test_dossier_service_init():
    """Тест инициализации UserDossierService"""
    print("\n" + "=" * 60)
    print("TEST: UserDossierService Init")
    print("=" * 60)

    # Без зависимостей
    service = UserDossierService()
    print("1. Created service without dependencies")
    assert service.cache_ttl == 3600
    assert service.update_threshold == 5

    # Проверяем что _extract_simple_dossier работает
    raw_data = {
        'goals': [
            {'goal': 'Создать медиа компанию'},
            {'goal': 'Найти друзей'},
            {'goal': 'Финансовая стабильность'}
        ],
        'barriers': [
            {'barrier': 'Тревога'},
            {'barrier': 'Не могу ценить хорошее'}
        ],
        'identity': [
            {'description': 'Журналист'}
        ]
    }

    dossier = service._extract_simple_dossier(999, raw_data)
    print(f"2. Extracted simple dossier: {len(dossier.top_goals)} goals, {len(dossier.top_barriers)} barriers")
    assert len(dossier.top_goals) == 3
    assert len(dossier.top_barriers) == 2
    assert "Журналист" in dossier.who

    # Проверяем style hints из Big Five
    big_five = {
        'openness': 0.8,
        'conscientiousness': 0.3,
        'extraversion': 0.2,
        'agreeableness': 0.9,
        'neuroticism': 0.75  # > 0.7 для срабатывания безопасности
    }
    hints = service._compute_style_hints(big_five)
    print(f"3. Computed style hints: {hints}")
    assert 'творческий' in hints.get('подход', ''), "Openness > 0.7 should set творческий подход"
    assert 'высокая' in hints.get('безопасность', ''), "Neuroticism > 0.7 should set высокая безопасность"

    print("\nUserDossierService Init: PASSED")


def test_correction_detector():
    """Тест CorrectionDetector"""
    print("\n" + "=" * 60)
    print("TEST: CorrectionDetector")
    print("=" * 60)

    detector = CorrectionDetector()

    # 1. Прямая коррекция
    test_cases = [
        ("Нет, на самом деле я хочу другое", True, "fact_wrong"),
        ("Это не так, я никогда не говорил про медиа", True, "fact_wrong"),
        ("Ты ошибаешься, моя цель совсем другая", True, "fact_wrong"),
        ("Это было раньше, сейчас у меня другие планы", True, "outdated"),
        ("Раньше да, но сейчас всё изменилось", True, "outdated"),
        ("Уже не актуально", True, "outdated"),
        ("Не совсем так, частично верно", True, "partial"),
        ("Да, именно так", False, None),
        ("Расскажу подробнее", False, None),
    ]

    passed = 0
    for message, expected_detected, expected_type in test_cases:
        result = detector.detect(message)
        type_match = (result.correction_type.value if result.correction_type else None) == expected_type

        if result.detected == expected_detected and type_match:
            passed += 1
            status = "✅"
        else:
            status = "❌"

        print(f"{status} '{message[:40]}...' → detected={result.detected}, type={result.correction_type}")

    print(f"\nPassed: {passed}/{len(test_cases)}")
    assert passed == len(test_cases), f"Only {passed}/{len(test_cases)} tests passed"

    print("\nCorrectionDetector: PASSED")


def test_check_in_manager():
    """Тест CheckInManager"""
    print("\n" + "=" * 60)
    print("TEST: CheckInManager")
    print("=" * 60)

    manager = CheckInManager()

    # 1. Инкремент сессий
    manager.increment_session(user_id=123)
    manager.increment_session(user_id=123)
    print(f"1. Session count after 2 increments: {manager._session_counts.get(123)}")
    assert manager._session_counts.get(123) == 2

    # 2. Форматирование вопроса
    from selfology_bot.services.chat.dossier_validator import CheckInItem
    from datetime import datetime

    item = CheckInItem(
        fact_type='goal',
        fact_text='Создать медиа компанию',
        added_at=datetime.now()
    )
    question = manager._format_check_in_question(item)
    print(f"2. Formatted question: {question}")
    assert 'медиа компанию' in question.lower()

    # 3. Запись валидации
    manager.record_validation(
        user_id=123,
        fact_type='goal',
        fact_text='Создать медиа компанию',
        still_relevant=True
    )
    print(f"3. Recorded validation, history: {len(manager._validation_history.get(123, {}))}")
    assert len(manager._validation_history.get(123, {})) == 1

    print("\nCheckInManager: PASSED")


def test_dossier_validator():
    """Тест DossierValidator"""
    print("\n" + "=" * 60)
    print("TEST: DossierValidator")
    print("=" * 60)

    validator = DossierValidator()

    # 1. Сохранение последнего сообщения коуча
    validator.set_last_coach_message(user_id=456, message="Ты говорил что хочешь создать медиа компанию")
    print(f"1. Last coach message saved: {validator._last_coach_messages.get(456)[:30]}...")
    assert validator._last_coach_messages.get(456) is not None

    # 2. Обработка check-in ответа
    from selfology_bot.services.chat.dossier_validator import CheckInItem
    from datetime import datetime

    item = CheckInItem(
        fact_type='goal',
        fact_text='Создать медиа компанию',
        added_at=datetime.now()
    )

    # Положительный ответ
    still_relevant, response = validator.handle_check_in_response(456, item, "Да, всё ещё актуально")
    print(f"2. Positive response: still_relevant={still_relevant}")
    assert still_relevant is True

    # Отрицательный ответ
    still_relevant, response = validator.handle_check_in_response(456, item, "Нет, уже изменил планы")
    print(f"3. Negative response: still_relevant={still_relevant}")
    assert still_relevant is False

    print("\nDossierValidator: PASSED")


def main():
    """Запуск всех тестов"""
    print("\n" + "=" * 60)
    print("MVP CHAT TESTS")
    print("=" * 60)

    # Синхронные тесты
    test_session_manager()
    test_user_dossier_dataclass()
    test_dossier_service_init()
    test_correction_detector()
    test_check_in_manager()
    test_dossier_validator()

    # Асинхронные тесты
    asyncio.run(test_chat_mvp())
    asyncio.run(test_resistance_handling())

    print("\n" + "=" * 60)
    print("ALL TESTS PASSED!")
    print("=" * 60)


if __name__ == "__main__":
    main()
