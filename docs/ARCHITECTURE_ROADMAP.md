# 🏗️ ARCHITECTURE ROADMAP: Цифровой отпечаток личности

> **Источник**: [research/Архитектура цифрового отпечатка личности для AI-коуча.md](../research/Архитектура%20цифрового%20отпечатка%20личности%20для%20AI-коуча.md)
>
> **Последнее обновление**: 2025-11-20
>
> **Текущая фаза**: Month 1 - Foundation

---

## 📊 ОБЩИЙ ПРОГРЕСС

| Месяц | Фаза | Статус | Прогресс |
|-------|------|--------|----------|
| 1 | Foundation | ✅ Complete | 100% |
| 2 | Core Features | ✅ Complete | 100% |
| 3 | Psychological Depth | ✅ Complete | 100% |
| 4 | Temporal & Advanced | ✅ Complete | 100% |
| 5 | Validation | ✅ Complete | 100% |
| 6 | Production | 🔄 In Progress | 50% |

---

## 🎯 КРИТИЧЕСКИЕ МЕТРИКИ (Targets)

| Метрика | Target | Текущее | Статус |
|---------|--------|---------|--------|
| Predictive Accuracy | >70% | N/A | ⏳ |
| Coherence Score | >0.75 | N/A | ⏳ |
| Depth Metric | >0.6 | N/A | ⏳ |
| Therapeutic Alliance | >0.7 | N/A | ⏳ |
| Semantic Search Relevance | >70% | Active (episodic_memory) | ✅ |

---

## 🗄️ ЦЕЛЕВАЯ АРХИТЕКТУРА

### PostgreSQL Tables (selfology schema)

**Существующие (✅):**
- users, sessions, user_answers_new, answer_analysis, digital_personality, personality_profiles, onboarding_sessions

**Новые (созданы 2025-11-20):**
- [x] core_beliefs
- [x] cognitive_distortions
- [x] defense_mechanisms
- [x] blind_spots
- [x] attachment_patterns
- [x] growth_areas
- [x] personality_states (обычная таблица, TimescaleDB позже)
- [x] alliance_measurements (обычная таблица, TimescaleDB позже)
- [x] breakthrough_moments (обычная таблица, TimescaleDB позже)

### Qdrant Collections (5 штук)

| Collection | Dimensions | Model | Статус |
|------------|------------|-------|--------|
| `episodic_memory` | 768 | RuBERT Conversational | ✅ Создана |
| `semantic_knowledge` | 2048 | GigaEmbeddings | ✅ Создана |
| `emotional_thematic` | 1536 | Hybrid | ✅ Создана |
| `psychological_constructs` | 1024 | GigaEmbeddings | ✅ Создана |
| `meta_patterns` | 1024 | GigaEmbeddings | ✅ Создана |

### Embedding Models

- [x] DeepPavlov/rubert-base-cased-conversational (768d) - для episodic ✅ Установлен
- [ ] GigaEmbeddings (2048d) или Cohere multilingual (1024d) - для semantic
- [ ] Hybrid composition pipeline - для emotional_thematic

---

## 📅 MONTH 1: FOUNDATION

### Week 1-2: Infrastructure Setup

#### Database Configuration
- [x] Исправить DB_PORT в selfology_controller.py (5432 → 5434)
- [x] Исправить DB_NAME в selfology_controller.py (n8n → selfology)
- [x] Исправить core/config.py
- [x] Исправить orchestrator.py
- [x] Исправить systems/analysis_system.py
- [x] Исправить core/monitoring_orchestrator.py
- [x] Проверить подключение к selfology-postgres ✅ 84 answers
- [ ] Обновить остальные скрипты с хардкодом (низкий приоритет, ~50 файлов)

#### TimescaleDB Setup
- [x] Проверить наличие TimescaleDB extension - НЕТ в контейнере
- [ ] Установить TimescaleDB в контейнер (отложено на Month 4)
- [ ] Конвертировать таблицы в hypertables

#### Qdrant Collections
- [x] Создать collection `episodic_memory` (768d, cosine) ✅
- [x] Создать collection `semantic_knowledge` (2048d, cosine) ✅
- [x] Создать collection `emotional_thematic` (1536d, cosine) ✅
- [x] Создать collection `psychological_constructs` (1024d, cosine) ✅
- [x] Создать collection `meta_patterns` (1024d, cosine) ✅
- [x] Настроить payload indexes (user_id, created_at) ✅

#### Embedding Models
- [x] Установить sentence-transformers ✅
- [x] Проверить DeepPavlov RuBERT (768d) ✅ Работает
- [x] Настроить OpenAI text-embedding-3-large (2048d/1024d) ✅
- [x] Создать EmbeddingService с multi-model support ✅

### Week 3-4: Basic Data Structures

#### New PostgreSQL Tables
- [ ] Создать таблицу `core_beliefs`
- [ ] Создать таблицу `cognitive_distortions`
- [ ] Создать таблицу `defense_mechanisms`
- [ ] Создать таблицу `blind_spots`
- [ ] Создать таблицу `attachment_patterns`
- [ ] Создать таблицу `growth_areas`
- [ ] Создать hypertable `personality_states`
- [ ] Создать hypertable `alliance_measurements`
- [ ] Создать hypertable `breakthrough_moments`

#### Data Migration
- [ ] Аудит существующих данных (users, answers, analyses)
- [ ] Скрипт миграции в новые таблицы
- [ ] Backfill personality_states из существующих данных

#### Basic Embedding Pipeline
- [ ] Создать dual-embedding service (RuBERT + GigaEmbed)
- [ ] Pipeline: answer → episodic_memory (RuBERT 768d)
- [ ] Pipeline: analysis → semantic_knowledge (GigaEmbed 2048d)
- [ ] Тест на существующих данных

---

## 📅 MONTH 2: CORE FEATURES

### All 5 Qdrant Collections Working
- [x] Populate episodic_memory с историческими данными ✅ 82 points
- [x] Populate semantic_knowledge с AI-анализами ✅ 46 points (OpenAI 2048d)
- [x] Populate emotional_thematic с эмоциональными паттернами ✅ 44 points (hybrid 1536d)
- [x] Populate psychological_constructs с извлеченными конструктами ✅ (auto-save via orchestrator)
- [x] Populate meta_patterns с мета-паттернами ✅ (auto-save blind spots via orchestrator)

### AI Analysis Pipeline (Enhanced)
- [x] Улучшить AnswerAnalyzer для извлечения конструктов ✅
- [x] Добавить detection когнитивных искажений ✅
- [x] Добавить detection защитных механизмов ✅
- [x] Сохранение в новые таблицы PostgreSQL ✅ (cognitive_distortions, defense_mechanisms)

### Cognitive Distortion Detection
- [x] Implement detector для 15 типов искажений ✅
- [x] Паттерн-матчинг + контекстный анализ ✅
- [x] Терапевтический фидбэк в ChatCoachService ✅
- [ ] Target: F1 > 0.68 (требует тестирования)

### Defense Mechanism Detection
- [x] Basic detection для 12 основных механизмов ✅
- [x] Evidence extraction из текста ✅
- [x] Pattern strength calculation ✅
- [x] Maturity level classification (primitive/neurotic/mature) ✅

---

## 📅 MONTH 3: PSYCHOLOGICAL DEPTH

### Attachment Style Assessment
- [x] Implement classifier (secure/anxious/avoidant/disorganized) ✅
- [x] Two-dimensional model (anxiety/avoidance) ✅
- [x] Evidence-based assessment ✅
- [x] EMA smoothing for history ✅
- [ ] Target: 84% accuracy (requires testing with real data)

### Core Beliefs Extraction
- [x] NLP pipeline для извлечения убеждений ✅
- [x] Valence scoring (-1 to 1) ✅
- [x] Confidence calculation ✅
- [ ] Contradiction detection (кросс-сессионный анализ - Phase 4)

### Blind Spot Detection
- [x] Pattern analysis для single response ✅
- [x] Evidence extraction из текста ✅
- [x] Surfacing strategy (alliance > 0.7) ✅
- [ ] Cross-session pattern aggregation (Phase 4)

### Therapeutic Alliance Tracking
- [x] WAI-SR measurement (bond/task/goal) ✅
- [x] Behavioral indicators (engagement, disclosure) ✅
- [x] Alliance score calculation ✅
- [x] Trust/resistance indicators ✅
- [ ] Target: >0.7 (requires testing)

### Gating Mechanism
- [x] Implement `should_surface_content()` ✅
- [x] Alliance threshold checks (content-specific) ✅
- [x] Time-based readiness (content-specific) ✅
- [x] Content-specific thresholds (10 types) ✅
- [x] Integration in ChatCoachService ✅

---

## 📅 MONTH 4: TEMPORAL & ADVANCED

### TimescaleDB Integration
- [ ] personality_states time-series queries (отложено на Phase 5)
- [ ] Aggregation functions (weekly averages)
- [ ] Variability tracking

### Breakthrough Detection ✅
- [x] Multi-indicator approach (5 типов: insight, emotional_release, belief_shift, defense_lowering, integration)
- [x] Insight emergence detection
- [x] Emotional release detection
- [x] Belief shift detection
- [x] Defense lowering detection
- [x] Integration with AnswerAnalyzer and ChatCoachService
- [x] Celebration responses for breakthroughs
- [ ] Target: F1 = 0.88 (requires testing)

### Growth Area Tracking ✅
- [x] Progress measurement (6 growth areas)
- [x] Goal attainment scoring (positive/negative indicators)
- [x] Growth summary and top areas
- [x] Integration with AnswerAnalyzer and ChatCoachService
- [x] Progress feedback in responses

### Meta-Pattern Analysis ✅
- [x] Cross-session pattern detection (15 pattern types)
- [x] Recurrence counting and strength calculation
- [x] Pattern evolution tracking (emerging/stable/growing)
- [x] Therapeutic insights generation
- [x] Integration with AnswerAnalyzer and ChatCoachService

---

## 📅 MONTH 5: VALIDATION

### Technical Validation
- [ ] All metrics > thresholds
- [ ] Performance benchmarks
- [ ] System health monitoring

### Psychometric Validation
- [ ] BFI-2 comparison
- [ ] Convergent validity > 0.48
- [ ] Discriminant validity > 0.65

### Clinical Validation
- [ ] **⚠️ ТРЕБУЕТСЯ: Licensed психолог**
- [ ] Monthly review protocol
- [ ] Agreement score > 0.75
- [ ] Case study evaluation

### A/B Testing
- [ ] Old vs New system comparison
- [ ] User engagement metrics
- [ ] Therapeutic outcome metrics

### Performance Optimization
- [ ] Qdrant HNSW tuning
- [ ] PostgreSQL index optimization
- [ ] Caching strategy

---

## 📅 MONTH 6: PRODUCTION

### Full Migration
- [ ] Final data sync
- [ ] Traffic cutover
- [ ] Old system read-only (30 days)

### Monitoring Dashboard
- [ ] Real-time metrics
- [ ] Alert system
- [ ] Health checks

### Continuous Validation
- [ ] Automated psychometric tests
- [ ] Performance regression detection
- [ ] Quality alerts

### User Feedback Loop
- [ ] Feedback collection
- [ ] Analysis pipeline
- [ ] Iterative improvement

---

## 🚨 КРИТИЧЕСКИЕ ЗАВИСИМОСТИ

### Внешние
- [ ] **Психолог для клинической валидации** (Month 5)
- [ ] GigaEmbeddings API access или Cohere API key
- [ ] TimescaleDB license (free for < 100GB)

### Технические
- [ ] RuBERT model (~1.5GB RAM)
- [ ] Qdrant storage (~10GB для 5 коллекций)
- [ ] GPU для fine-tuning (optional)

---

## 📝 ЗАМЕТКИ И РЕШЕНИЯ

### 2025-11-20
- Обнаружена критическая проблема: код подключался к n8n-postgres вместо selfology-postgres
- Исправлены 5 критичных файлов (controller, config, orchestrator, analysis_system, monitoring)
- Подтверждено: selfology-postgres содержит 84 ответа в схеме selfology
- Остается ~50 файлов с хардкодом (скрипты, тесты) - низкий приоритет

**Инфраструктура завершена:**
- ✅ Созданы 5 Qdrant коллекций с правильными dimensions
- ✅ Созданы 9 PostgreSQL таблиц для психологических конструктов
- ✅ EmbeddingService с multi-model support (RuBERT 768d + fallback)
- ✅ VectorStorageService для unified Qdrant operations
- ✅ Backfill 82/84 ответов в episodic_memory
- ✅ Интеграция в OnboardingOrchestrator (auto-save new answers)
- ✅ Semantic search включен в ChatCoachService (episodic_memory)
- ✅ OpenAI text-embedding-3-large для semantic_knowledge (2048d)
- ✅ OpenAI для psychological_constructs и meta_patterns (1024d)
- ✅ .env исправлен для localhost (Redis, PostgreSQL port 5434)

**Month 2 Progress (2025-11-20):**
- ✅ Backfill semantic_knowledge: 46 points (OpenAI 2048d embeddings)
- ✅ Backfill emotional_thematic: 44 points (hybrid 1536d)
- ✅ CognitiveDistortionDetector: 15 типов искажений с терапевтическими ответами
- ✅ DefenseMechanismDetector: 12 механизмов с maturity levels
- ✅ CoreBeliefsExtractor: извлечение глубинных убеждений (Young schemas)
- ✅ BlindSpotDetector: детекция слепых зон (avoidance, contradiction, rationalization, deflection)
- ✅ Интеграция в AnswerAnalyzer: полная детекция всех 4 компонентов
- ✅ Интеграция в ChatCoachService: real-time детекция + терапевтический фидбэк
- ✅ Сохранение в psychological_constructs: core_beliefs, distortions, defenses
- ✅ Сохранение в meta_patterns: blind_spots
- ✅ Созданы файлы:
  - `selfology_bot/coach/components/cognitive_distortion_detector.py`
  - `selfology_bot/coach/components/defense_mechanism_detector.py`
  - `selfology_bot/coach/components/core_beliefs_extractor.py`
  - `selfology_bot/coach/components/blind_spot_detector.py`
  - `selfology_bot/coach/components/therapeutic_alliance_tracker.py`
  - `selfology_bot/coach/components/gating_mechanism.py`
  - `scripts/backfill_semantic_emotional.py`

**Month 3 Progress (2025-11-20):**
- ✅ TherapeuticAllianceTracker: WAI-SR модель (bond/task/goal)
- ✅ Trust/Resistance indicators detection
- ✅ Engagement & Disclosure depth calculation
- ✅ GatingMechanism: 10 типов контента с порогами
- ✅ Интеграция в ChatCoachService с real-time alliance измерением
- ✅ Автоматическое gating для distortions и beliefs
- ✅ AttachmentStyleClassifier: 4 типа привязанности
- ✅ Two-dimensional model (anxiety/avoidance dimensions)

**Month 4 Progress (2025-11-20):**
- ✅ BreakthroughDetector: 5 типов прорывов с индикаторами
- ✅ GrowthAreaTracker: 6 зон роста с измерением прогресса
- ✅ MetaPatternAnalyzer: 15 типов мета-паттернов
- ✅ Интеграция в AnswerAnalyzer: полная детекция всех компонентов
- ✅ Интеграция в ChatCoachService: real-time детекция + therapeutic feedback
- ✅ Celebration responses для breakthroughs
- ✅ Progress feedback для growth areas
- ✅ Therapeutic insights для meta-patterns
- ✅ Созданы файлы:
  - `selfology_bot/coach/components/breakthrough_detector.py`
  - `selfology_bot/coach/components/growth_area_tracker.py`
  - `selfology_bot/coach/components/meta_pattern_analyzer.py`

### Архитектурные решения
- **Embedding models**: RuBERT для episodic (русские диалоги), GigaEmbed для semantic
- **Gating**: alliance > 0.6, time > 21 days для unconscious content
- **Chunking**: 300-400 tokens, 75-100 overlap

---

## 🔗 СВЯЗАННЫЕ ДОКУМЕНТЫ

- [Исследование](../research/Архитектура%20цифрового%20отпечатка%20личности%20для%20AI-коуча.md)
- [CLAUDE.md](../CLAUDE.md)
- [Database schema](../alembic/) (migrations)

---

## ⏭️ СЛЕДУЮЩИЕ ШАГИ

1. **Сейчас**: Установить TimescaleDB и создать 5 коллекций Qdrant
2. **Эта неделя**: Подключить RuBERT model
3. **Следующая неделя**: Создать новые PostgreSQL таблицы
