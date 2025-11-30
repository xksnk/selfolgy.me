# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview
**Selfology.me** - AI Psychology Coach Telegram Bot built with FastAPI + aiogram architecture integrating with n8n workflows. Features clean architecture, comprehensive monitoring, and smart AI routing (Claude Sonnet 4 → GPT-4 → GPT-4o-mini) for cost optimization.

---

## 🎯 ТЕКУЩАЯ РАБОТА (ROADMAP)

**➡️ [docs/NEW_ONBOARDING_INTERVIEW.md](docs/NEW_ONBOARDING_INTERVIEW.md)** - План работы на 30 ноября

### Статус: БЕТА-ВЕРСИЯ V2 ГОТОВА К ТЕСТИРОВАНИЮ

Новая кластерная система онбординга:
- 29 программ, 190 кластеров, 674 вопроса
- 3 режима: Умный AI | Выбор программы | Закончить кластеры
- Тестировать: `/onboarding` в Telegram

---

## 🚀 ГЛАВНОЕ - КАК ПРАВИЛЬНО ЗАПУСКАТЬ БОТ

### ⚡ БЫСТРЫЙ СТАРТ (Основной способ запуска)

```bash
# Перейти в директорию проекта
cd /home/ksnk/n8n-enterprise/projects/selfology

# Запустить бот с hot reload (РЕКОМЕНДУЕТСЯ)
./run-local.sh
```

**Что делает `./run-local.sh`:**
- ✅ Автоматически активирует виртуальное окружение
- ✅ Устанавливает/обновляет зависимости
- ✅ Подключается к существующим Docker сервисам (PostgreSQL, Redis, Qdrant)
- ✅ Запускает `selfology_controller.py` - главный файл бота
- ✅ Включает hot reload - изменения применяются мгновенно
- ✅ URL: http://localhost:8001
- ✅ Health: http://localhost:8001/health

### 🛑 Остановка бота

```bash
# Ctrl+C в терминале где запущен бот
# ИЛИ
pkill -f selfology_controller.py
```

### 🔍 Проверка статуса

```bash
# Проверить запущен ли бот
pgrep -f selfology_controller.py

# Посмотреть логи в реальном времени
tail -f logs/selfology.log
```

### ⚠️ ВАЖНО: Управление экземплярами бота

**С октября 2025: автоматическая защита от дублирующих экземпляров через Redis lock**

Бот автоматически проверяет наличие других запущенных экземпляров и блокирует старт если обнаружен конфликт:

```bash
# Если видишь: "❌ Another bot instance is already running!"
# Останови старый экземпляр:
pkill -f selfology_controller.py

# Подождать пока lock освободится (max 30 секунд)
sleep 3

# Запустить заново - теперь lock будет получен
./run-local.sh
```

**Старая проблема РЕШЕНА**: Конфликт `terminated by other getUpdates request` больше не возникает благодаря Redis instance locking.

### 📁 ОСНОВНЫЕ ФАЙЛЫ

- **`selfology_controller.py`** - ГЛАВНЫЙ файл бота (entry point)
- **`run-local.sh`** - Скрипт быстрого запуска с hot reload
- **`telegram_interface/bot.py`** - Интерфейс Telegram (НЕ запускать напрямую!)
- **`src/main.py`** - FastAPI приложение (альтернативный режим)

---

## Essential Commands

### Development Environment

#### 🚀 Hot Reload Development (RECOMMENDED)
```bash
# Fastest development with hot reload - changes apply instantly!
./dev.sh start          # Start with Docker + hot reload
./dev.sh logs           # View real-time logs 
./dev.sh stop           # Stop dev containers
./dev.sh restart        # Quick restart

# Even faster - pure local development (no Docker rebuild)
./run-local.sh          # Uses existing Docker services, runs locally
```

#### 📦 Development Commands
```bash
# Docker-based development
./dev.sh start          # Full Docker dev environment with hot reload
./dev.sh build          # Rebuild dev image
./dev.sh shell          # Shell access to dev container
./dev.sh status         # Check container status
./dev.sh clean          # Clean dev environment

# Local development (fastest)
./run-local.sh          # Pure local run with hot reload
source venv/bin/activate # Manual venv activation
pip install -r requirements.txt
```

#### 🛠 Traditional Environment Setup
```bash
# Activate virtual environment (if needed for manual setup)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
# or for development dependencies  
pip install -e ".[dev]"
```

### Bot Management (Primary Interface)
```bash
# Start bot with full monitoring (recommended)
python scripts/selfology_manager.py start dev

# Check system health and status
python scripts/selfology_manager.py status

# View real-time logs
python scripts/selfology_manager.py follow main

# Monitor dashboard with metrics
python scripts/selfology_manager.py dashboard

# Analyze recent errors (last N hours)
python scripts/selfology_manager.py errors 6
```

### 🎯 Agile Debug System (NEW - Swiss Watch Precision)
```bash
# Master interface for all agile debugging
python scripts/selfology_agile_master.py overview

# Run full agile debug cycle (comprehensive analysis + fixes)
python scripts/selfology_agile_master.py agile-cycle

# Question approval workflow
python scripts/selfology_agile_master.py review-questions

# Telegram question reviewer (with approval buttons)
python scripts/telegram_question_reviewer.py

# Surgical debugging (precise fixes without breaking system)
python scripts/selfology_agile_master.py surgical-fix --component ai_router --issue "slow response"

# Continuous agile monitoring
python scripts/selfology_agile_master.py monitor --duration 24

# Learning engine insights
python scripts/selfology_agile_master.py learn --action insights

# System feedback collection
python scripts/selfology_agile_master.py feedback

# Intelligent refactoring
python scripts/selfology_agile_master.py refactor --target selfology_bot/ai
```

### Database Operations
```bash
# Connect to existing n8n PostgreSQL database
docker exec -it n8n-postgres psql -U postgres
# Password: sS67wM+1zMBRFHAW4kj9HwFl5J6+veo7Nirx0/I+oiU=

# Database migrations
alembic revision --autogenerate -m "Description"
alembic upgrade head
alembic downgrade -1

# Initialize database tables
python scripts/setup_database.py
```

### Testing & Quality
```bash
# Run tests
pytest tests/

# Code formatting
black selfology_bot/
ruff selfology_bot/

# Quick bot testing (minimal setup)
python simple_bot.py
```

### Docker & Production
```bash
# Production deployment
docker-compose -f docker-compose.selfology.yml up -d

# Build container
docker build -t selfology-bot .

# View logs from Docker containers
docker-compose logs -f selfology-bot
```

## Architecture Overview

### Core Structure
```
selfology_bot/              # Main application (Clean Architecture)
├── core/                   # Configuration, database, logging, monitoring  
│   ├── config.py          # Environment configuration
│   ├── database.py        # SQLAlchemy setup & connection
│   ├── logging.py         # Structured logging system
│   ├── monitoring.py      # Performance metrics & health checks
│   └── error_handling.py  # Standardized error codes & handling
├── models/                # SQLAlchemy models
│   └── user.py           # User profile & assessment data
├── bot/                   # Telegram bot implementation
│   ├── handlers/         # Command & message handlers
│   └── states.py         # FSM state management
├── ai/                    # AI service integration
│   ├── router.py         # Intelligent model selection
│   └── clients.py        # Claude, GPT-4, GPT-4o-mini clients
└── services/             # Business logic
    └── intelligent_questioning.py  # Psychology assessment engine
```

### Key Architectural Components

**AI Router** (`ai/router.py`): Intelligent model selection based on task complexity, user tier, and cost optimization. Routes 80% to GPT-4o-mini, 15% to GPT-4, 5% to Claude Sonnet for ~75% cost savings.

**State Management** (`bot/states.py`): aiogram FSM implementation with **Redis-based persistent storage**. Handles user flow: /start → GDPR consent → Onboarding → AI chat sessions.

**FSM Storage Architecture** (October 2025):
- 🔴 **Redis FSM Storage**: Persists states across bot restarts (replaces MemoryStorage)
- 📍 **Configuration**: Redis DB=1 (separate from cache), localhost:6379
- 🔒 **Instance Locking**: Prevents duplicate bot instances via Redis SET NX
- ⚡ **Graceful Shutdown**: Proper cleanup with signal handlers (SIGINT/SIGTERM)
- 🔄 **State Logging**: Middleware tracks all FSM transitions for debugging
- 🛡️ **Fallback Safety**: Database check when FSM state unexpectedly missing

**Monitoring System** (`core/monitoring.py`): Comprehensive logging with structured error codes (BOT_001-004, USER_001-004, AI_001-005, DB_001-004, VDB_001-003) and performance metrics tracking.

**Vector Integration**: Qdrant vector database for personality pattern storage and semantic search through user interaction history.

## Infrastructure Dependencies

### Existing Docker Services (DO NOT RECREATE)
These services are already running in `/home/ksnk/n8n-enterprise`:
- `n8n-postgres` (PostgreSQL 15) - port 5432
- `n8n-redis` (Redis 7-alpine) - port 6379  
- `qdrant` (Vector DB) - ports 6333-6334
- `chromadb` (Vector DB) - port 8000
- `ollama` (Local AI) - port 11434
- `n8n-main` (Workflows) - port 5678

**Network**: `n8n-enterprise_n8n-network`

### Intelligent Question Core Integration
Located in `intelligent_question_core/`:
- **1513 professional psychological questions** with full metadata (updated Oct 2025)
- **13 psychological domains** (IDENTITY, EMOTIONS, RELATIONSHIPS, etc.)
- **5 depth levels** (SURFACE → CONSCIOUS → EDGE → SHADOW → CORE)
- **Energy dynamics** (OPENING, NEUTRAL, PROCESSING, HEAVY, HEALING)
- **38 curated programs** with sequential question ordering - **ALL programs have questions!**
- **API**: `intelligent_question_core/api/core_api.py`

**🎉 October 2025 Achievement - AI-Generated Modern Programs:**
- **182 new questions generated** via Claude API for 13 modern programs
- Programs: AI-тревожность, Война за внимание, Инфо-ожирение, Скорость изменений, Выученная беспомощность 2.0, Паразоциальная зависимость, Гибридная жизнь, Аутентичность vs Алгоритмы, Эко-вина и климат-тревога, Поляризация и эмпатия, Dating apps выгорание, Родительская вина за экранное время, Криптовалютное FOMO
- Full pipeline: Generation → Integration → Deduplication → Tagging → Sequencing
- **Production-ready database**: `intelligent_question_core/data/selfology_final_sequenced.json`

**📊 Database Statistics:**
- Total questions: 1513 (1331 original + 182 generated)
- Unique questions: 1505 (8 duplicates removed)
- Questions with program tags: 93.3% (1411 questions)
- Questions in final sequences: 1476 questions across 38 programs
- 464 questions included in program sequences
- 2549 questions in reserve pool

**📋 Complete Program Coverage (38 programs):**
- **P0 (Ready)**: 13 programs - Подумать о жизни (42q), Карьера/бизнес (28q), Здоровье (20q), и др.
- **P1 (Critical)**: 5 programs - Исцеление прошлого, Работа со страхами, Выгорание, и др.
- **P2 (Classic)**: 7 programs - Тело и эмоции, Деньги и самоценность, и др.
- **P3 (Modern)**: 9 programs - AI-anxiety, Attention war, Info-obesity, и др.
- **P4 (Specialized)**: 4 programs - Dating apps, Воскресная тревога, и др.

**🔧 Question Processing Scripts:**
```bash
# Generate questions for new programs via Claude API
python scripts/generate_questions_for_programs.py

# Integrate generated questions into main database
python scripts/integrate_generated_questions.py

# Find and mark duplicates
python scripts/deduplicate_questions_simple.py

# Tag questions with relevant programs
python scripts/tag_questions_to_programs.py

# Create final sequences with energy balancing
python scripts/sequence_all_programs.py
```

**📁 Key Files:**
- `selfology_final_sequenced.json` - Production database with all metadata
- `generated_questions_for_programs.json` - AI-generated questions
- `all_programs_sequenced.json` - Sequenced programs with positions
- `all_programs_list.json` - Complete program catalog

## Development Guidelines

### Code Patterns
- Follow Clean Architecture: domain/application/infrastructure separation
- Use standardized error codes with descriptive messages
- Include comprehensive logging for all user actions and AI interactions
- Track performance metrics for cost optimization
- Maintain existing patterns in handlers, services, and AI routing

### Critical Safety Rules
- **Energy Safety**: NEVER ask HEAVY→HEAVY questions, always balance with HEALING
- **Trust Level Access**: Control deep psychological questions based on user progression
- **Vector Updates**: Each user interaction updates 693-dimensional personality profile
- **Model Optimization**: Use question's recommended_model for cost efficiency

### Monitoring & Debugging
1. Always check system status before changes: `python scripts/selfology_manager.py status`
2. Analyze errors with context: `python scripts/selfology_manager.py errors 6`
3. View user-specific logs: `python scripts/log_viewer.py view --user [USER_ID]`
4. Monitor performance: `python scripts/monitor_dashboard.py`

### Log Locations
- `logs/selfology.log` - Main application log
- `logs/errors/errors.log` - Errors with full traceback
- `logs/bot/bot_activity.log` - Bot events (hourly rotation)
- `logs/users/user_activity.log` - User actions (daily rotation)
- `logs/ai/ai_interactions.log` - AI API calls (6h rotation)
- `logs/metrics/metrics.log` - Performance metrics (hourly rotation)

## 🎯 Agile Debug System Features

### Question Approval Workflow
- **Telegram Integration**: Questions show with approval buttons in Telegram
- **Smart Warnings**: Automatic analysis of question quality and safety
- **Auto-Approval**: Questions auto-approve after 24h if not marked for work
- **Audit Trail**: Complete history of all approval decisions
- **CRITICAL**: Questions are **BLOCKED** from main system until approved

### Debug Learning Engine  
- **Pattern Recognition**: Learns from historical debugging sessions
- **Predictive Alerts**: Warns about potential issues before they happen
- **Solution Recommendations**: Suggests fixes based on learned patterns
- **Confidence Scoring**: Rates reliability of recommended solutions

### System Feedback Integration
- **Multi-Source Feedback**: Collects from monitoring, logs, user interactions
- **Real-Time Analysis**: Processes feedback as system runs
- **Pattern Detection**: Identifies recurring issues automatically
- **Priority Routing**: Routes critical issues to immediate attention

### Surgical Debugging
- **Swiss Watch Precision**: Minimal changes, maximum effect
- **Backup Creation**: Always creates backups before changes
- **Validation Pipeline**: Multi-stage validation before applying fixes
- **Rollback Capability**: Automatic rollback on validation failure
- **Risk Assessment**: Evaluates impact before applying changes

### Intelligent Refactoring
- **Code Quality Analysis**: Identifies smells, complexity, duplication
- **Safe Refactoring**: Only applies low-risk improvements automatically
- **Performance Optimization**: Focuses on bottlenecks from monitoring
- **Architecture Improvement**: Suggests structural improvements

## Important Notes

- **Never recreate existing Docker services** - use n8n-enterprise infrastructure
- **Always activate virtual environment** before any Python operations
- **Use existing network**: `n8n-enterprise_n8n-network` for Docker services
- **Test with real bot** (@SelfologyMeCoachBot) before production changes
- **Monitor costs** via AI router metrics and optimize model usage
- **Log everything** for debugging and performance optimization
- **Database**: Use existing n8n PostgreSQL, database name: `n8n`, **СХЕМА: `selfology`**
- **🚨 КРИТИЧНО**: ВСЕ таблицы Selfology ТОЛЬКО в схеме `selfology`, НЕ в `public`
- **🔴 Redis FSM**: States persist in Redis DB=1, bot prevents duplicate instances automatically
- **🛡️ Instance Safety**: Redis lock ensures only one bot instance runs at a time
- **⚡ Graceful Shutdown**: Always use Ctrl+C for clean shutdown with resource cleanup
- **🔑 Environment Variables**: Bot loads .env automatically via `load_dotenv()` in selfology_controller.py
- **🆕 CRITICAL**: Use Agile Debug System for all troubleshooting and improvements
- **🆕 Question Safety**: ALL questions must go through approval workflow before use
- **📊 Question Database**: Production database is `intelligent_question_core/data/selfology_final_sequenced.json` with 1513 questions, full metadata, program sequences, and positions

## Current Production Status
- ✅ Bot deployed: @SelfologyMeCoachBot
- ✅ Database: Connected to n8n PostgreSQL with selfology tables + new onboarding tables
- ✅ Monitoring: Real-time logging and error tracking active
- ✅ AI APIs: Claude + OpenAI configured with smart routing
- ✅ Vector DB: Qdrant ready for personality storage with 3 collections
- ✅ **Onboarding System Ready** (Sept 2025)
- ✅ **Phase 2-3 AI Coach Active** (Oct 2025) - 6 advanced components operational
- ✅ **Question Database Complete** (Oct 2025) - 1513 questions, 38 programs fully sequenced

## 🧠 NEW ONBOARDING SYSTEM (September 2025)

### **Architecture Completed:**
```
selfology_controller.py (управляет ботом)
    ↓
OnboardingOrchestrator (главный дирижер)
    ↓
├── QuestionRouter (Smart Mix алгоритм)
├── AnswerAnalyzer (анализ ответов) 
├── FatigueDetector (забота о пользователе)
└── EmbeddingCreator (векторы в Qdrant)
```

### **Key Features:**
- 🎯 **Smart Mix Algorithm**: 4 стратегии роутинга (ENTRY → EXPLORATION → DEEPENING → BALANCING)
- 🔬 **Двухфазный анализ**: Instant feedback <500ms + Deep analysis 2-10s в фоне
- 🤖 **AI Model Router**: Claude 10% + GPT-4o 75% + Mini 15% для cost optimization
- 😴 **FatigueDetector**: Умная забота о пользователе с красивыми сообщениями
- 📊 **Multilayer Personality**: Big Five + динамические + адаптивные + доменные черты
- 📈 **Vector Storage**: 3 уровня (512D/1536D/3072D) в Qdrant для разных задач
- 🚧 **Admin Features**: Кнопка "На доработку" только для админа (ID: 98005572)

### **Database Tables:**
- `questions_metadata` - метаданные вопросов + флаги админа
- `onboarding_sessions` - сессии пользователей
- `user_answers_new` - ответы пользователей
- `answer_analysis` - результаты AI анализа с версионированием

### **Message Templates:**
- ✅ Красивые шаблоны в `/templates/ru/onboarding.json`
- ✅ Человечные названия для debug (только админу)
- ✅ Шаблоны усталости и управления сессией
- ✅ Мгновенный фидбек и уведомления о готовом анализе

### **Commands:**
```bash
# Тестирование системы онбординга
/onboarding  # В Telegram боте - запуск новой системы

# Админские функции (только для ID 98005572)
- Кнопка "🚧 На доработку" для пометки вопросов
- Debug информация с человечными названиями
- Статистика и аналитика системы
```

### **Status:**
🎉 **ГОТОВА К ПРОДАКШНУ** - полная система умного онбординга с анализом души и заботой о пользователе!

---

## 🔥 PHASE 2-3 AI COACH SYSTEM (October 2025)

### **Architecture Active:**
```
SelfologyController
    ↓
ChatCoachService (services/chat_coach.py)
    ↓
├── Enhanced AI Router          # Psychological context-based model selection
├── Adaptive Communication Style # Big Five personality adaptation
├── Deep Question Generator     # 5 categories of deep questions
├── Micro Interventions        # Reframing, anchoring, gentle challenge
├── Confidence Calculator      # 5-factor confidence scoring (0.0-1.0)
└── Vector Storytelling        # 132-point personality narrative
```

### **6 Active Components:**

1. **Enhanced AI Router** (`coach/components/enhanced_ai_router.py`)
   - Routes based on psychological context (crisis, existential, depth_level)
   - Claude Sonnet 3.5: Crisis situations, existential questions, SHADOW depth
   - GPT-4o: Action plans, emotional support, structured guidance
   - GPT-4o-mini: Simple interactions, general chat

2. **Adaptive Communication Style** (`coach/components/adaptive_communication_style.py`)
   - **Depth adaptation**: surface → medium → deep → profound (based on openness)
   - **Emotional tone**: Matches user's Big Five personality traits
   - **Response structure**: bullet/narrative/mixed (based on conscientiousness)
   - **Directiveness**: Adjusts guidance level dynamically

3. **Deep Question Generator** (`coach/components/deep_question_generator.py`)
   - **5 question categories**: contradictions, patterns, resistance, desires, deepening
   - **Personality-aware**: Adapts to user's Big Five traits
   - **Non-intrusive**: 1-2 questions per response (не перегружает)
   - **Follow-up chain**: Builds on previous answers

4. **Micro Interventions** (`coach/components/micro_interventions.py`)
   - **Reframing**: Transforms negative beliefs into growth opportunities
   - **Anchoring**: Reinforces positive states and achievements
   - **Gentle challenge**: Pushes comfort zone boundaries safely
   - **Random selection**: Keeps interventions fresh and natural

5. **Confidence Calculator** (`coach/components/confidence_calculator.py`)
   - **5-factor scoring**:
     - data_consistency: How well data supports the insight
     - historical_patterns: Past evidence strength
     - user_validation: User's own confirmation
     - psychological_theory: Theoretical backing
     - context_completeness: Available information depth
   - **Honest scoring**: 0.0-1.0 with human-readable explanations
   - **Formatted output**: "Уверен (80%+)", "Гипотеза (40-59%)", etc.

6. **Vector Storytelling** (`coach/components/vector_storytelling.py`)
   - **132-point evolution**: Full personality journey visualization
   - **Breakthrough detection**: Identifies key transformation moments
   - **Archetype descriptions**: Based on Big Five patterns
   - **Trajectory narratives**: Shows growth direction and changes

### **Semantic Search Integration:**
Located at `services/message_embedding_service.py`:
- **OpenAI embeddings**: text-embedding-3-small (1536D)
- **Similar state search**: Finds emotional states from user's history
- **Context enrichment**: "You were in similar state 2 weeks ago..."
- **Speed**: ~200ms embedding + <20ms Qdrant search

### **Key Files:**
- `services/chat_coach.py` - Main ChatCoachService with all 6 components
- `coach/components/` - Individual component implementations
- `data_access/coach_vector_dao.py` - Fast Qdrant access for personality data
- `services/message_embedding_service.py` - OpenAI embedding creation

### **Testing:**
```bash
# Run Phase 2-3 integration tests
python tests/test_phase2_3_integration.py

# Expected output: All 6 components ✅
```

### **Configuration:**
- **Environment**: Requires OPENAI_API_KEY in .env for semantic search
- **Database**: Uses existing asyncpg pool from DatabaseService
- **Imports**: All use absolute imports (not relative) for clean integration

### **Expected Impact:**
| Metric | Before | After Phase 2-3 | Improvement |
|--------|--------|-----------------|-------------|
| Response length | ~150 words | 500-600 words | +300% |
| Messages/session | 3-5 | 15-20 | +300% |
| Insights/session | 1-2 | 7-10 | +400% |
| "Feels understood" | 30% | 85% | +183% |

### **Monitoring Phase 2-3:**
```bash
# Watch Phase 2-3 components in logs
tail -f logs/selfology.log | grep "Enhanced Router\|Deep Questions\|Confidence\|Storytelling"

# Check which AI models are selected
grep "Enhanced Router" logs/selfology.log | tail -20
```

### **Status:**
✅ **ACTIVE IN PRODUCTION** - All 6 components operational since Oct 5, 2025