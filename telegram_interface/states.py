"""
FSM States - состояния конечного автомата бота

Определяет все возможные состояния пользователя в процессе
взаимодействия с ботом.
"""

from aiogram.fsm.state import State, StatesGroup


class OnboardingStates(StatesGroup):
    """Состояния процесса онбординга"""
    
    gdpr_consent = State()           # Согласие с GDPR
    assessment_intro = State()       # Введение в оценку
    assessment_active = State()      # Активная оценка
    
    # Детальные состояния для Smart Mix онбординга
    onboarding_active = State()      # Активный процесс вопросов
    waiting_for_answer = State()     # Ожидаем текстовый ответ от пользователя
    processing_answer = State()      # Анализируем ответ и выбираем следующий вопрос
    onboarding_paused = State()      # Пауза по просьбе пользователя
    onboarding_complete = State()    # Онбординг завершен, создан профиль


class ChatStates(StatesGroup):
    """Состояния AI чата"""
    
    active = State()                 # Активная чат-сессия
    paused = State()                 # Чат на паузе
