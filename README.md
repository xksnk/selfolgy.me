# Selfology Bot - AI Psychology Coach

FastAPI + Telegram bot implementation for the Selfology AI psychology coaching platform.

## Architecture

```
FastAPI Core:
├── Telegram Bot (aiogram) - State management & dialogues
├── AI Router - Claude/GPT selection logic  
├── Psychology Engine - Assessment flows & analysis
├── Vector Store - Qdrant integration for personality patterns
└── Database - PostgreSQL for user profiles & history

n8n Integration:
├── Complex workflows via webhooks
├── Scheduled analysis tasks
├── External service integrations
└── Background processing
```

## Features

- **🧠 Psychological Assessment**: Big Five personality test + values + goals
- **🤖 AI Routing**: Smart model selection (Claude/GPT-4/GPT-4o-mini) 
- **💬 Intelligent Chat**: Context-aware conversations with personality memory
- **📊 Vector Analysis**: Semantic search through user history and patterns
- **🎯 Goal Tracking**: Progress monitoring and AI insights
- **🔒 Privacy First**: GDPR compliant with data control options

## Quick Start

### 1. Environment Setup

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your API keys:
# - TELEGRAM_BOT_TOKEN
# - ANTHROPIC_API_KEY  
# - OPENAI_API_KEY
# - DATABASE_URL
# - QDRANT_URL
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
# or
pip install -e .
```

### 3. Database Setup

```bash
# Initialize Alembic
alembic init alembic

# Create initial migration
alembic revision --autogenerate -m "Initial tables"

# Run migrations
alembic upgrade head
```

### 4. Start Services

Required services:
- PostgreSQL database
- Qdrant vector database
- Redis (optional, for caching)

```bash
# Development mode (polling)
python main.py

# Production mode (webhook)
uvicorn main:app --host 0.0.0.0 --port 8000
```

## AI Router Cost Optimization

The system uses intelligent model routing to optimize both quality and cost:

| Model | Use Case | Avg Cost | Usage % |
|-------|----------|----------|---------|
| GPT-4o-mini | Validation, simple tasks | $0.01 | 80% |
| GPT-4 | Daily chat, coaching | $0.05 | 15% |
| Claude Sonnet | Deep psychological analysis | $0.15 | 5% |

**Result**: ~$0.25/user/month vs $1.50+ with single premium model

## Project Structure

```
selfology_bot/
├── core/           # FastAPI core, config, database
├── models/         # SQLAlchemy models
├── bot/            # Telegram bot handlers and states
├── ai/             # AI clients and routing logic
├── services/       # Business logic services
└── __init__.py

main.py            # FastAPI application entry point
requirements.txt   # Python dependencies
alembic/           # Database migrations
```

## Key Components

### AI Router (`ai/router.py`)
Intelligent model selection based on:
- Task complexity analysis
- User tier (free/premium)  
- Cost optimization
- Context requirements

### Vector Service (`services/vector_service.py`)
- Personality profile embeddings
- Semantic search through chat history
- Pattern detection and insights
- Context retrieval for AI conversations

### Assessment Handler (`bot/handlers/assessment.py`)
- Big Five personality test (20 questions)
- Values assessment (5 categories)
- Goal setting and prioritization
- AI analysis and insights generation

## n8n Integration

The bot integrates with n8n workflows via webhooks for:

- **Complex Analysis**: Weekly deep personality insights
- **Scheduled Tasks**: Daily check-ins, progress reports
- **External APIs**: Calendar, note apps, fitness trackers
- **Background Processing**: Large dataset analysis

Webhook endpoint: `POST /n8n/webhook`

## Development

### Testing
```bash
pytest tests/
```

### Code Formatting
```bash
black selfology_bot/
ruff selfology_bot/
```

### Database Migrations
```bash
# Create new migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

## Deployment

### Docker (Recommended)
```bash
docker build -t selfology-bot .
docker run -d --name selfology-bot \
  --env-file .env \
  -p 8000:8000 \
  selfology-bot
```

### Manual Deployment
1. Set up PostgreSQL and Qdrant
2. Configure environment variables
3. Run database migrations
4. Start with `uvicorn main:app --host 0.0.0.0 --port 8000`
5. Set up Telegram webhook (production only)

## API Endpoints

- `GET /` - Health check and bot info
- `GET /health` - Service status
- `POST /webhook` - Telegram webhook (production)
- `POST /n8n/webhook` - n8n integration

## Contributing

1. Fork the repository
2. Create feature branch
3. Make changes with tests
4. Submit pull request

## License

Private project - All rights reserved