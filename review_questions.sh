#!/bin/bash

# Скрипт для запуска ручной проверки вопросов программ Selfology
# Использование: ./review_questions.sh

cd /home/ksnk/n8n-enterprise/projects/selfology
source venv/bin/activate
python scripts/manual_question_review.py
