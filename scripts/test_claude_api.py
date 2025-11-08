#!/usr/bin/env python3
"""Тест Claude API"""
import anthropic
import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv('ANTHROPIC_API_KEY')
print(f"API Key: {api_key[:20]}...")

try:
    print("Создаем клиент...")
    client = anthropic.Anthropic(api_key=api_key)

    print("Отправляем тестовый запрос...")
    response = client.messages.create(
        model="claude-3-5-haiku-20241022",
        max_tokens=100,
        messages=[
            {"role": "user", "content": "Скажи 'привет' на русском"}
        ]
    )

    print(f"Ответ: {response.content[0].text}")

except Exception as e:
    print(f"Ошибка: {e}")
    import traceback
    traceback.print_exc()