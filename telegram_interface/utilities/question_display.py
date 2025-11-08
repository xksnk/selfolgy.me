"""
Question Display - отображение вопросов онбординга

Вспомогательная функция для красивого отображения вопросов
с метаданными, elaborations и admin кнопками.
"""

import logging
from aiogram.types import Message, CallbackQuery
from selfology_bot.messages.human_names import HumanNames

logger = logging.getLogger(__name__)

ADMIN_USER_ID = "98005572"


async def show_onboarding_question(
    question: dict,
    session_info: dict,
    telegram_id: str,
    target,  # Message or CallbackQuery
    messages,  # MessageService
    is_edit: bool = False
):
    """
    Универсальная функция для показа вопроса онбординга
    
    Args:
        question: Объект вопроса из JSON
        session_info: Информация о сессии (question_number, total_questions, etc)
        telegram_id: ID пользователя
        target: Message или CallbackQuery объект для ответа
        messages: MessageService для получения шаблонов
        is_edit: True если нужно edit_text, False если answer
    """
    is_admin = str(telegram_id) == ADMIN_USER_ID

    # Человечные названия для debug (только админу)
    classification = question.get('classification', {})
    domain_human = HumanNames.get_domain_human(classification.get('domain', ''))
    depth_human = HumanNames.get_depth_human(classification.get('depth_level', ''))
    energy_human = HumanNames.get_energy_human(classification.get('energy_dynamic', ''))

    # Debug лог для проверки метаданных
    if is_admin:
        logger.debug(
            f"🔍 Question metadata for {question['id']}: "
            f"domain={classification.get('domain')}, "
            f"depth={classification.get('depth_level')}, "
            f"energy={classification.get('energy_dynamic')}"
        )

    # Извлекаем elaborations если есть
    elaborations = question.get('elaborations', {})
    elaboration_content = elaborations.get('content', '')
    elaboration_type = elaborations.get('type', '')
    elaboration_priority = elaborations.get('priority', '')
    elaboration_icon = HumanNames.get_elaboration_icon(elaboration_type) if elaboration_type else ''

    text = messages.get_message('onboarding_question', 'ru', 'onboarding',
        question_number=session_info['question_number'],
        total_questions=session_info['total_questions'],
        total_lifetime=session_info.get('total_lifetime', 0),
        question_text=question['text'],
        question_id=question['id'],
        is_admin=is_admin,
        domain_human=domain_human,
        depth_human=depth_human,
        energy_human=energy_human,
        elaboration_content=elaboration_content,
        elaboration_type=elaboration_type,
        elaboration_priority=elaboration_priority,
        elaboration_icon=elaboration_icon
    )

    # Кнопки в зависимости от роли пользователя
    keyboard_name = "admin_answer_buttons" if is_admin else "onboarding_answer_buttons"
    keyboard = messages.get_keyboard(keyboard_name, 'ru')

    if is_edit:
        await target.message.edit_text(text, reply_markup=keyboard, parse_mode='HTML')
    else:
        await target.answer(text, reply_markup=keyboard, parse_mode='HTML')

    logger.info(f"📋 Question {question['id']} shown to user {telegram_id}")
