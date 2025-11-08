# Полная структура проекта Selfology.me

## 📁 Корневой уровень

### Основные файлы запуска
- `selfology_controller.py` - **ГЛАВНЫЙ** файл бота (entry point)
- `run-local.sh` - Скрипт быстрого запуска с hot reload
- `dev.sh` - Development environment management
- `Dockerfile`, `Dockerfile.dev`, `Dockerfile.new`, `Dockerfile.test` - Docker образы
- `docker-compose.yml`, `docker-compose.dev.yml`, `docker-compose.enterprise.yml`, `docker-compose.microservices.yml`, `docker-compose.selfology.yml`, `docker-compose.test.yml`
- `requirements.txt`, `requirements-monitoring.txt` - Python зависимости
- `pyproject.toml` - Python project configuration
- `alembic.ini` - Database migrations config
- `Makefile` - Build automation

### Конфигурация
- `.gitignore` - Git ignore rules
- `claude-config.json` - Claude AI configuration
- `.env` (не в репо) - Environment variables

### Документация (корень)
- `README.md` - Main documentation
- `CLAUDE.md` - **Claude Code instructions**
- `Selfolgy.md` - Project overview
- `START_BOT.md` - Bot startup guide

#### Архитектурная документация
- `ARCHITECTURE_CONTRACTS.md`
- `ARCHITECTURE_DIAGRAMS.md`
- `ARCHITECTURE_REFACTORING_PLAN.md`
- `README_ARCHITECTURE.md`
- `REFACTORED_ARCHITECTURE.md`
- `REFACTORING_PROGRESS.md`
- `REFACTORING_REPORT_FSM.md`
- `REFACTORING_RULES_SELFOLOGY.md`

#### DevOps документация
- `DEVOPS_GUIDE.md`
- `DEVOPS_QUICK_START.md`
- `DEVOPS_STRATEGY.md`
- `MIGRATION_GUIDE.md`

#### Мониторинг документация
- `MONITORING.md`
- `MONITORING_SUMMARY.md`
- `MONITORING_SYSTEM.md`
- `MONITORING_TRANSPARENCY.md`

#### Планирование и стратегия
- `MVP_PLAN.md`
- `AGENT_STRATEGY_PLAN.md`
- `DEBUGGING_STRATEGY.md`
- `ONBOARDING_DEVELOPMENT_PLAN.md`
- `PHASE_2_ANALYSIS_SYSTEM_PLAN.md`

#### Testing документация
- `TESTING_CODE_EXAMPLES.md`
- `TESTING_IMPLEMENTATION_PLAN.md`
- `TESTING_INDEX.md`
- `TESTING_README.md`
- `TESTING_STRATEGY.md`
- `TESTING_STRATEGY_SUMMARY.md`

#### Векторная система
- `VECTOR_PIPELINE.md`
- `VECTOR_SYSTEM_VERIFICATION.md`

#### Отчеты и анализы
- `EXECUTIVE_SUMMARY_RU.md`
- `FINAL_REPORT_02_10_2025.md`
- `DIAGNOSTIC_REPORT_2025-10-01.md`
- `DETAILED_FIX_PLAN_2025-10-01.md`
- `FIX_REPORT_personality_summary.md`
- `CLEANUP_LOG.md`
- `ARCHIVE_LIST.md`
- `AUTOMERGE_STATUS.md`
- `AUTO_RETRY_FIX.md`

#### Questions система
- `QUESTIONS_FOR_IMPROVEMENT.md`
- `QUESTIONS_MERGE_COMPLETE.md`
- `QUICK_MERGE_INSTRUCTIONS.md`
- `NEXT_STEPS_QUESTIONS.md`
- `COUNTER_SYSTEM_FILES.md`
- `STATUS_GENERATION_COMPLETE.md`
- `PRIVACY_AUDIT.md`

### Скрипты для анализа/тестирования (корень)
- `check_analysis.py`
- `check_sessions.py`
- `debug_user_data.py`
- `diagnose_onboarding.py`
- `monitor_onboarding.py`
- `onboarding_profiler.py`
- `process_orphaned_answers.py`
- `process_single_answer.py`
- `reprocess_missing_vectors.py`
- `reprocess_vectors_simple.py`
- `review_questions.sh`
- `run_create_personality_vectors.sh`
- `run_personality_extraction.sh`
- `test_chat_coach_fix.py`
- `test_create_personality_vector.py`
- `test_embeddings_simple.py`
- `test_monitoring_system.py`
- `test_onboarding_answers_fix.py`
- `test_orchestrator_fixes.py`
- `test_qdrant_setup.py`
- `test_redis_fsm.py`
- `test_refactored_system.py`

---

## 📂 .claude/ - Claude Code конфигурация

```
.claude/
├── README.md
├── BACKLOG.md
├── settings.json
├── settings.local.json
├── agents/
│   └── selfology-architect.md
└── commands/
    ├── check-system.md
    ├── show-backlog.md
    └── test-system.md
```

---

## 📂 .github/ - GitHub Actions

```
.github/
└── workflows/
    └── ci-cd-pipeline.yml
```

---

## 📂 alembic/ - Database Migrations

```
alembic/
├── env.py
├── script.py.mako
└── versions/
    ├── 001_create_soul_architect_tables.py
    ├── 002_create_event_outbox_table.py
    ├── 003_add_global_answer_counter_trigger.py
    ├── 004_create_user_stats_table.py
    ├── 006_digital_personality.py
    ├── 007_optimize_counter_triggers.py
    └── 008_complete_answer_counter_sync.py
```

---

## 📂 archive/ - Deprecated Code

```
archive/
├── deprecated_bots/
│   ├── enterprise_monitored_bot.py
│   ├── fixed_architecture_bot.py
│   ├── human_friendly_bot.py
│   ├── intelligent_bot.py
│   ├── monitored_bot.py
│   ├── monitored_bot_example.py
│   ├── polished_bot.py
│   ├── production_monitored_bot.py
│   ├── quick_intelligent_bot.py
│   ├── simple_bot.py
│   ├── test_db_bot.py
│   ├── user_friendly_bot.py
│   └── working_bot.py
├── deprecated_handlers/
│   ├── assessment.py
│   └── assessment_handler.py
├── deprecated_main_files/
│   ├── main.py
│   └── main_refactored.py
├── deprecated_onboarding_dao.py_20250909_093926
├── deprecated_templates_onboarding.json_20250909_093920
└── deprecated_services/
    └── intelligent_questioning.py
```

---

## 📂 coach/ - Phase 2-3 AI Coach System

```
coach/
├── README.md
├── ai_coach_prompt.md
├── architecture_recommendations.md
├── COMPLETION_SUMMARY.md
├── DATABASE_SCHEMA_FIX.md
├── EXECUTIVE_SUMMARY.md
├── IMPLEMENTATION_PLAN.md
├── IMPLEMENTATION_PLAN_PHASE_2_3.md
├── IMPORT_FIX_COMPLETE.md
├── INTEGRATION_COMPLETE.md
├── PHASE2_3_ACTIVATED.md
├── PHASE2_3_STATUS.md
├── PRODUCT_ROADMAP.md
└── components/
    ├── adaptive_communication_style.py
    ├── confidence_calculator.py
    ├── deep_question_generator.py
    ├── enhanced_ai_router.py
    ├── micro_interventions.py
    └── vector_storytelling.py
```

---

## 📂 core/ - Core Infrastructure

```
core/
├── __init__.py
├── config.py - Environment configuration
├── logging.py - Structured logging
├── enhanced_logging.py - Advanced logging features
├── monitoring_orchestrator.py - Monitoring coordination
├── monitoring_dashboard.py - Dashboard interface
├── monitoring_api.py - Monitoring API
├── health_monitoring.py - Health checks
├── log_aggregation.py - Log collection
├── event_bus.py - Event bus implementation
├── event_bus_monitor.py - Event monitoring
├── domain_events.py - Domain events definitions
├── outbox_pattern.py - Outbox pattern for events
├── circuit_breaker.py - Circuit breaker pattern
├── retry.py - Retry logic
├── service_protocols.py - Service interfaces
└── Dockerfile.event-monitor
```

---

## 📂 data_access/ - Data Access Layer

```
data_access/
├── __init__.py
├── assessment_dao.py - Assessment data access
├── coach_vector_dao.py - Coach vector operations
├── user_dao.py - User data access
└── vector_dao.py - Vector database operations
```

---

## 📂 docs/ - Documentation

```
docs/
├── API_DOCUMENTATION.md
├── ARCHITECTURE.md
├── CATEGORIES_IMPLEMENTATION_PLAN.md
├── CONTEXT_STORIES_INTEGRATION.md
├── COUNTER_ANALYSIS_RU.md
├── COUNTER_ARCHITECTURE.md
├── COUNTER_DECISION_MATRIX.md
├── COUNTER_RECOMMENDATION.txt
├── DATA_STORAGE_ARCHITECTURE_ANALYSIS.md
├── GENERATION_RESULTS_SUMMARY.md
├── IMPLEMENTATION_PLAN_FOR_APPROVAL.md
├── MIGRATION_PLAN_DATA_OPTIMIZATION.md
├── MONITORING_INTEGRATION.md
├── ONBOARDING_MONITORING.md
├── ONBOARDING_OPTIMIZATION_FINAL_PLAN.md
├── PROGRAM_ROADMAP.md
├── PROJECT_STRUCTURE.md
├── QUESTIONS_CATEGORY_ANALYSIS.md
├── QUESTION_DATABASE_CHANGELOG.md
├── RUNBOOK.md
├── VECTOR_OPTIMIZATION_ANALYSIS.md
├── VECTOR_OPTIMIZATION_QUICK_START.md
├── VECTOR_OPTIMIZATION_README.md
├── global_answer_counter.md
└── refactoring_summary.md
```

---

## 📂 examples/ - Code Examples

```
examples/
├── counter_usage_examples.py
├── optimized_data_access_patterns.py
└── vector_optimization_examples.py
```

---

## 📂 intelligent_question_core/ - Question Database System

```
intelligent_question_core/
├── README.md
├── AI_SYSTEM_INSTRUCTIONS.md
├── CORE_SUMMARY.md
├── FINAL_VALIDATION.md
├── TECHNICAL_EXAMPLES.md
├── integration_guide.md
├── questions_with_elaborations.md
├── api/
│   ├── ai_model_router.py
│   ├── core_api.py
│   └── search_api_demo.py
├── config/
│   ├── ai_analysis_config.json
│   ├── energy_flow_rules_base.json
│   └── question_taxonomy_base.json
└── docs/
    ├── ai_analysis_materials.md
    ├── core_completion_report.txt
    ├── corrected_roadmap.md
    └── project_roadmap_human_language.md
```

**ПРИМЕЧАНИЕ**: База данных вопросов (`selfology_final_sequenced.json`) находится в `prompts/` папке (см. ниже).

---

## 📂 migrations/ - SQL Migrations

```
migrations/
├── 010_create_user_context_stories.sql
├── 011_add_questions_table.sql
├── 012_optimize_answer_analysis_bigfive.sql
├── add_processing_status_tracking.sql
└── create_user_context_stories.sql
```

---

## 📂 prompts/ - AI Prompts & Question Database

```
prompts/
├── GENERATE_MISSING_QUESTIONS_PROMPT.md
├── SELFOLOGY_CONTEXT_FOR_OPUS.md
├── transformation_architect.md
├── all_notion_pages.json
├── all_programs_list.json
├── all_programs_sequenced.json - ✅ Sequenced programs
├── generated_questions_for_programs.json - ✅ AI-generated questions
├── notion_programs.json
├── notion_programs_full.json
├── notion_programs_list.json
├── notion_programs_with_questions.json
└── program_question_matches.json

**🔥 ВАЖНО: Production база данных вопросов**
НЕТ selfology_final_sequenced.json в этой папке!
Нужно проверить где находится production database.
```

---

## 📂 scripts/ - Utility Scripts

### Main Scripts
```
scripts/
├── __init__.py
├── selfology_manager.py - **Bot management CLI**
├── deploy.sh
├── backup-restore.sh
├── migration-manager.sh
├── health_check.py
├── system_diagnostics.py
├── log_viewer.py
├── monitor_dashboard.py
└── onboarding_monitoring_cli.py
```

### Database Scripts
```
scripts/
├── setup_database.py
├── migrate.py
├── migrate_flags_to_db.py
├── migrate_to_selfology_schema.py
├── cleanup_orphaned_data.py
├── sync_answer_counters.py
└── sync_questions_json_to_db.py
```

### Question Processing Scripts
```
scripts/
├── generate_questions_for_programs.py - Generate via Claude API
├── integrate_generated_questions.py - Integrate into main DB
├── deduplicate_questions.py
├── deduplicate_questions_simple.py
├── tag_questions_to_programs.py
├── sequence_all_programs.py
├── match_programs_to_questions.py
├── populate_questions_metadata.py
├── add_program_metadata.py
├── update_elaborations.py
├── validate_questions_completeness.py
└── analyze_questions_metadata.py
```

### Merging Scripts
```
scripts/
├── auto_merge_all_questions.py
├── merge_all_questions.py
├── merge_final_dataset.py
├── merge_generated_questions.py
├── simple_paste_merge.py
├── final_merge_questions.py
├── extract_programs_questions.py
├── extract_questions_from_logs.py
└── extract_from_outputs.py
```

### Analysis & Reprocessing Scripts
```
scripts/
├── full_reanalysis.py
├── retroactive_analysis.py
├── reanalyze_context_story.py
├── reprocess_answer_14.py
├── reprocess_context_story.py
├── reprocess_old_analyses.py
├── reprocess_single_answer.py
└── analyze_tagging_gaps.py
```

### Vector & Personality Scripts
```
scripts/
├── create_digital_personality_vectors.py
├── create_digital_personality_vectors_enhanced.py
├── create_vectors_from_analysis.py
├── extract_digital_personality.py
├── generate_full_personality_report.py
├── setup_qdrant.py
├── check_qdrant_status.py
└── create_chat_messages_collection.py
```

### Testing Scripts
```
scripts/
├── test_claude_api.py
├── test_coach_semantic_search.py
├── test_personality_summary_fix.py
├── test_vector_creation.py
├── test_vectorization_fix.py
└── validate_test_coverage.py
```

### Enhanced Tables & Data Scripts
```
scripts/
├── create_enhanced_tables.py
├── counter_health_check.py
├── backfill_chat_embeddings.py
├── clean_json_flags.py
├── save_3_blocks_opus.py
├── save_all_blocks.sh
└── save_generated_blocks.py
```

### Notion Integration
```
scripts/
└── fetch_notion_programs.py
```

### Question Review
```
scripts/
├── manual_question_review.py
└── telegram_question_reviewer.py - **Telegram approval workflow**
```

### Debuggers
```
scripts/
├── selfology-debugger.py
└── setup.py
```

### 🎯 Agile Debug System
```
scripts/agile_debug/
├── __init__.py
├── debug_learning_engine.py
├── monitoring_integration.py
├── question_approval_workflow.py
├── refactoring_agent.py
├── surgical_debugger.py
└── system_feedback_collector.py

scripts/
└── agile_debug_system.py - **Master agile debug CLI**
```

### 🐛 Debug Package
```
scripts/debug/
├── __init__.py
├── ai_system_analyzer.py
├── chat_manager_debugger.py
├── integration_tester.py
├── performance_profiler.py
├── production_guardian.py
├── question_core_validator.py
├── system_diagnostics.py
└── workflow_optimizer.py

scripts/
└── debug_agent.py
```

---

## 📂 selfology_bot/ - Main Bot Application

```
selfology_bot/
├── __init__.py
├── ai/ - AI Integration
│   ├── clients.py - AI clients (Claude, GPT-4, GPT-4o-mini)
│   └── router.py - Intelligent model selection
├── analysis/ - Onboarding Analysis System
│   ├── __init__.py
│   ├── ai_model_router.py
│   ├── analysis_config.py
│   ├── analysis_templates.py
│   ├── answer_analyzer.py - Two-phase analysis
│   ├── embedding_creator.py - Vector creation
│   ├── personality_extractor.py
│   └── trait_extractor.py
├── bot/ - Telegram Bot Interface
│   ├── states.py - FSM states
│   └── handlers/
│       ├── profile.py
│       └── start.py
├── core/ - Core Infrastructure
│   ├── config.py
│   ├── database.py
│   ├── error_handling.py
│   ├── logging.py
│   └── monitoring.py
├── database/ - Database Access
│   ├── __init__.py
│   ├── digital_personality_dao.py
│   ├── onboarding_dao.py
│   ├── service.py
│   └── user_dao.py
├── messages/ - Message Templates
│   ├── __init__.py
│   ├── constants.py
│   ├── formatters.py
│   ├── human_names.py
│   ├── service.py
│   ├── validators.py
│   └── templates/ru/
│       ├── chat.json
│       ├── errors.json
│       ├── general.json
│       └── onboarding.json - **Onboarding templates**
├── models/ - SQLAlchemy Models
│   ├── __init__.py
│   └── user.py
├── monitoring/ - Monitoring System
│   ├── README.md
│   ├── __init__.py
│   ├── auto_retry.py
│   ├── onboarding_monitor.py
│   └── telegram_alerting.py
├── services/ - Business Logic
│   ├── chat_service.py
│   ├── memory_system.py
│   ├── personality_service.py
│   ├── user_service.py
│   ├── vector_service.py
│   └── onboarding/
│       ├── __init__.py
│       ├── fatigue_detector.py - User fatigue detection
│       ├── orchestrator.py - **Onboarding orchestrator**
│       ├── question_router.py - Smart Mix algorithm
│       └── session_reporter.py
└── soul_architect/ - Soul Architect System
    ├── README.md
    ├── __init__.py
    ├── config.py
    ├── evolution_tracker.py
    ├── models.py
    ├── profile_builder.py
    ├── service.py
    ├── trait_scorer.py
    └── tests/
        ├── __init__.py
        ├── test_models.py
        └── test_scorer.py
```

---

## 📂 services/ - Top-level Services

```
services/
├── __init__.py
├── assessment_engine.py
├── chat_coach.py - **ChatCoachService with Phase 2-3 components**
├── message_embedding_service.py - OpenAI embeddings
├── statistics_service.py
├── user_profile_service.py
└── vector_service.py
```

---

## 📂 src/ - Clean Architecture Structure

```
src/
├── application/ - Application Layer
│   ├── dto/
│   │   ├── __init__.py
│   │   ├── assessment_dto.py
│   │   ├── chat_dto.py
│   │   ├── personality_dto.py
│   │   └── user_dto.py
│   ├── interfaces/
│   │   ├── __init__.py
│   │   ├── ai_service.py
│   │   ├── external_api_service.py
│   │   ├── notification_service.py
│   │   └── vector_service.py
│   └── use_cases/
│       ├── __init__.py
│       ├── assessment_use_cases.py
│       ├── chat_use_cases.py
│       ├── personality_use_cases.py
│       └── user_use_cases.py
├── config/ - Configuration
│   ├── __init__.py
│   ├── container.py - DI container
│   └── settings.py
├── domain/ - Domain Layer
│   ├── entities/
│   │   ├── __init__.py
│   │   ├── assessment.py
│   │   ├── chat.py
│   │   ├── personality.py
│   │   └── user.py
│   ├── exceptions.py
│   ├── repositories/
│   │   ├── __init__.py
│   │   ├── assessment_repository.py
│   │   ├── chat_repository.py
│   │   ├── personality_repository.py
│   │   └── user_repository.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── ai_routing_service.py
│   │   ├── personality_analysis_service.py
│   │   └── user_tier_service.py
│   └── value_objects/
│       ├── __init__.py
│       ├── ai_model.py
│       ├── telegram_id.py
│       ├── traits.py
│       └── username.py
├── infrastructure/ - Infrastructure Layer
│   ├── database/
│   │   ├── __init__.py
│   │   ├── connection.py
│   │   └── models.py
│   ├── external_services/
│   │   ├── __init__.py
│   │   └── ai_service.py
│   └── repositories/
│       ├── __init__.py
│       └── user_repository.py
├── monitoring/ - Monitoring
│   ├── __init__.py
│   ├── health_checks.py
│   └── logging_config.py
├── presentation/ - Presentation Layer
│   ├── api/
│   │   └── __init__.py
│   └── telegram/
│       └── __init__.py
└── main.py - **Alternative entry point (FastAPI)**
```

---

## 📂 static/ - Static Files

```
static/
└── dashboard.html
```

---

## 📂 systems/ - Microservices Architecture

```
systems/
├── base.py
├── analysis_system.py
├── analysis/
│   ├── ai_router.py
│   └── analysis_worker_service.py
├── coach/
│   ├── coach_interaction_service.py
│   └── insight_generator_service.py
├── onboarding/
│   ├── question_selection_service.py
│   └── session_management_service.py
├── profile/
│   ├── profile_storage_service.py
│   └── trait_evolution_service.py
└── telegram/
    └── telegram_gateway_service.py
```

---

## 📂 telegram_interface/ - Telegram Interface

```
telegram_interface/
├── __init__.py
├── bot.py - **Telegram bot setup (НЕ запускать напрямую!)**
└── handlers/
    ├── __init__.py
    ├── chat_handler.py
    ├── profile_handler.py
    └── stats_handler.py
```

---

## 📂 tests/ - Testing

```
tests/
├── chaos/
│   └── chaos_engineering_tests.py
├── e2e/
│   ├── test_complete_user_journey.py
│   └── test_onboarding_flow.py
├── integration/
│   └── test_event_bus_with_outbox.py
├── load/
│   └── k6_load_test.js
└── performance/
    └── load-test.js
```

---

## 🎯 КЛЮЧЕВЫЕ ФАЙЛЫ И ПАПКИ

### 🚀 Запуск бота
1. **`selfology_controller.py`** - ГЛАВНЫЙ entry point
2. **`run-local.sh`** - Быстрый запуск с hot reload
3. **`telegram_interface/bot.py`** - Telegram bot interface (не запускать напрямую)

### 🧠 Core Systems
1. **`selfology_bot/services/onboarding/orchestrator.py`** - Onboarding orchestration
2. **`services/chat_coach.py`** - Phase 2-3 AI Coach with 6 components
3. **`selfology_bot/analysis/answer_analyzer.py`** - Two-phase analysis
4. **`coach/components/`** - 6 Phase 2-3 components

### 📊 Question Database
1. **`prompts/all_programs_sequenced.json`** - Sequenced programs
2. **`prompts/generated_questions_for_programs.json`** - AI-generated questions
3. **`intelligent_question_core/api/core_api.py`** - Question API
4. **Где production database `selfology_final_sequenced.json`?** ⚠️

### 🔧 Management Tools
1. **`scripts/selfology_manager.py`** - Bot management CLI
2. **`scripts/agile_debug_system.py`** - Agile debug master
3. **`scripts/telegram_question_reviewer.py`** - Question approval workflow

### 📝 Documentation
1. **`CLAUDE.md`** - Claude Code instructions (THIS FILE!)
2. **`README.md`** - Main documentation
3. **`coach/README.md`** - Phase 2-3 documentation
4. **`docs/`** - All detailed documentation

---

## 📊 СТАТИСТИКА

### Основные папки
- **15 top-level directories**
- **~500+ Python files**
- **~100+ Markdown documentation files**
- **~50+ configuration files**

### Размеры кода (примерно)
- `selfology_bot/`: ~50 files
- `scripts/`: ~100+ files
- `src/`: ~40 files (Clean Architecture)
- `coach/components/`: 6 Phase 2-3 components
- `tests/`: ~5 test files

### Документация
- Root MD files: ~40
- `docs/`: ~25 files
- `coach/`: ~10 MD files
- `intelligent_question_core/docs/`: ~4 files

---

## ⚠️ КРИТИЧНЫЕ ЗАМЕЧАНИЯ

### 🔴 ВАЖНО: Найти production database!
```
❌ НЕ НАЙДЕН: prompts/selfology_final_sequenced.json
✅ ЕСТЬ: prompts/all_programs_sequenced.json
✅ ЕСТЬ: prompts/generated_questions_for_programs.json

🔍 НУЖНО: Найти где находится финальная база на 1513 вопросов!
```

### 📁 Возможные локации
1. `intelligent_question_core/data/` (упомянуто в CLAUDE.md)
2. Не закоммичен в git?
3. Находится на production сервере?

---

## 🎯 НАВИГАЦИЯ ПО ПРОЕКТУ

### Работа с ботом
```bash
./run-local.sh                              # Запуск
python scripts/selfology_manager.py status  # Статус
python scripts/selfology_manager.py errors  # Ошибки
```

### Работа с вопросами
```bash
python scripts/generate_questions_for_programs.py  # Генерация
python scripts/integrate_generated_questions.py    # Интеграция
python scripts/sequence_all_programs.py            # Секвенирование
```

### Agile Debug
```bash
python scripts/selfology_agile_master.py overview      # Обзор
python scripts/telegram_question_reviewer.py           # Approval workflow
```

### Testing
```bash
pytest tests/e2e/test_onboarding_flow.py    # E2E tests
pytest tests/integration/                    # Integration tests
```

---

**Создано**: 2025-01-08
**Автор**: Claude Code
**Версия**: 1.0
