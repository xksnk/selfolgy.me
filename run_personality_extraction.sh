#!/bin/bash
cd /home/ksnk/n8n-enterprise/projects/selfology
source venv/bin/activate
# OPENAI_API_KEY загружается из .env файла через load_dotenv()
python scripts/extract_digital_personality.py --user-id 98005572
