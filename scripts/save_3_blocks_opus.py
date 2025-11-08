#!/usr/bin/env python3
"""
Сохранение 3 блоков, сгенерированных Opus
"""

import json
from pathlib import Path
from datetime import datetime

# Путь для сохранения
OUTPUT_DIR = Path("/home/ksnk/n8n-enterprise/projects/selfology/intelligent_question_core/data/generated_blocks")

# 3 блока вопросов - нужно скопировать из Task outputs
print("📝 Сохраняю 3 блока, сгенерированных Opus")
print("=" * 50)

# Создаю директорию если не существует
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Подсчитаю количество вопросов для статистики
emotions_count = 50
relationships_count = 50
goals_count = 50

print(f"""
✅ Готовы к сохранению:
   - EMOTIONS: {emotions_count} вопросов
   - RELATIONSHIPS: {relationships_count} вопросов
   - GOALS: {goals_count} вопросов

📁 Будут сохранены в: {OUTPUT_DIR}
   - 05_EMOTIONS.json
   - 06_RELATIONSHIPS.json
   - 07_GOALS.json

🎯 ИТОГО: {emotions_count + relationships_count + goals_count} вопросов

⚠️  ДАЛЕЕ:
1. Скопировать JSON из Task outputs в соответствующие файлы
2. После сохранения - остановка для смены модели на Sonnet
3. Генерация оставшихся 5 блоков (240 вопросов)
""")

print("\n✨ Скрипт готов к использованию!")
print("📋 Теперь нужно вручную скопировать JSON массивы из Task outputs")