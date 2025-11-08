#!/bin/bash
cd /home/ksnk/n8n-enterprise/projects/selfology
source venv/bin/activate
# OPENAI_API_KEY загружается из .env файла через load_dotenv()
python scripts/create_digital_personality_vectors.py --user-id 98005572
