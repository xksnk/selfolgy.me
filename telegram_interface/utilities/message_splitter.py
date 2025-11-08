"""
Message Splitter - разбиение длинных сообщений для Telegram

Telegram лимит: 4096 символов на сообщение.
Разбивает текст по параграфам чтобы не резать посередине предложения.
"""

import asyncio
import logging
from aiogram.types import Message

logger = logging.getLogger(__name__)

MAX_MESSAGE_LENGTH = 4000  # Оставляем запас для форматирования


async def send_long_message(message: Message, text: str, parse_mode: str = 'HTML'):
    """
    Отправляет длинное сообщение, разбивая его на части если нужно
    
    Args:
        message: Aiogram Message object
        text: Текст для отправки
        parse_mode: Режим парсинга (HTML/Markdown)
    """
    if len(text) <= MAX_MESSAGE_LENGTH:
        await message.answer(text, parse_mode=parse_mode)
        return

    # Разбиваем по параграфам
    parts = []
    current_part = ""

    # Сначала пробуем разбить по двойным переносам строк (параграфы)
    paragraphs = text.split('\n\n')

    for paragraph in paragraphs:
        # Если параграф сам по себе слишком длинный
        if len(paragraph) > MAX_MESSAGE_LENGTH:
            # Разбиваем по одинарным переносам
            lines = paragraph.split('\n')
            for line in lines:
                if len(current_part) + len(line) + 1 <= MAX_MESSAGE_LENGTH:
                    current_part += line + '\n'
                else:
                    if current_part:
                        parts.append(current_part.strip())
                    current_part = line + '\n'
        else:
            # Проверяем поместится ли параграф
            if len(current_part) + len(paragraph) + 2 <= MAX_MESSAGE_LENGTH:
                current_part += paragraph + '\n\n'
            else:
                if current_part:
                    parts.append(current_part.strip())
                current_part = paragraph + '\n\n'

    # Добавляем последнюю часть
    if current_part:
        parts.append(current_part.strip())

    # Отправляем все части
    for i, part in enumerate(parts):
        # Добавляем номер части если их больше 1
        if len(parts) > 1:
            part_indicator = f"\n\n<i>📄 Часть {i+1}/{len(parts)}</i>"
            await message.answer(part + part_indicator, parse_mode=parse_mode)
        else:
            await message.answer(part, parse_mode=parse_mode)

        # Небольшая задержка между сообщениями
        if i < len(parts) - 1:
            await asyncio.sleep(0.3)

    logger.info(f"📤 Long message sent in {len(parts)} parts")
