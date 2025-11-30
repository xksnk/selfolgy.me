"""
FSM States для Selfology бота.

Извлечено из selfology_controller.py для модульности.
"""

from aiogram.fsm.state import State, StatesGroup


class OnboardingStates(StatesGroup):
    """Состояния онбординга"""
    gdpr_consent = State()
    assessment_intro = State()
    assessment_active = State()

    # Детальные состояния для Smart Mix онбординга
    onboarding_active = State()        # Активный процесс вопросов
    waiting_for_answer = State()       # Ожидаем текстовый ответ от пользователя
    processing_answer = State()        # Анализируем ответ и выбираем следующий вопрос
    onboarding_paused = State()        # Пауза по просьбе пользователя
    onboarding_complete = State()      # Онбординг завершен

    # Состояния для блочной системы программ
    choosing_mode = State()            # Выбор: авто / вручную
    choosing_program = State()         # Выбор программы из списка
    program_active = State()           # Активная программа
    waiting_program_answer = State()   # Ожидание ответа в программе
    block_transition = State()         # Переход между блоками


class ChatStates(StatesGroup):
    """Состояния чата с AI-коучем"""
    active = State()
    paused = State()
