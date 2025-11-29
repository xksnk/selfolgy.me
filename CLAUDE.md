# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Selfology.me** - AI Psychology Coach Telegram Bot based on research "Архитектура цифрового отпечатка личности для AI-коуча".

**Core Concept:** Build a digital personality fingerprint through 10 psychological detection components, 5 vector memory collections, and 4-layer personality model.

**Bot:** @SelfologyMeCoachBot
**Admin:** ID 98005572 (@axksnk)

---

## Quick Start

### Run Bot
```bash
cd /home/ksnk/microservices/critical/selfology-bot
./run-local.sh
```

### Stop Bot
```bash
pkill -f selfology_controller.py
```

### Check Status
```bash
pgrep -f selfology_controller.py
tail -f logs/selfology.log
```

### Key Files
- `selfology_controller.py` - Main entry point
- `services/chat_coach.py` - ChatCoachService with 6 Phase 2-3 components
- `selfology_bot/analysis/answer_analyzer.py` - AnswerAnalyzer with all detectors
- `selfology_bot/coach/components/` - 10 psychological detector implementations

---

## System Architecture

### 10 Psychological Components

All integrated in AnswerAnalyzer and ChatCoachService:

| Component | File | What it detects |
|-----------|------|-----------------|
| CognitiveDistortionDetector | `cognitive_distortion_detector.py` | 15 distortion types |
| DefenseMechanismDetector | `defense_mechanism_detector.py` | 12 mechanisms + maturity |
| CoreBeliefsExtractor | `core_beliefs_extractor.py` | Young schemas, valence |
| BlindSpotDetector | `blind_spot_detector.py` | 4 blind spot types |
| TherapeuticAllianceTracker | `therapeutic_alliance_tracker.py` | WAI-SR (bond/task/goal) |
| GatingMechanism | `gating_mechanism.py` | 10 content type thresholds |
| AttachmentStyleClassifier | `attachment_style_classifier.py` | 4 attachment styles |
| BreakthroughDetector | `breakthrough_detector.py` | 5 breakthrough types |
| GrowthAreaTracker | `growth_area_tracker.py` | 6 growth areas |
| MetaPatternAnalyzer | `meta_pattern_analyzer.py` | 15 meta-patterns |

### 5 Qdrant Collections

| Collection | Dimensions | Model | Purpose |
|------------|------------|-------|---------|
| episodic_memory | 768 | RuBERT | User answers, semantic search |
| semantic_knowledge | 2048 | OpenAI | AI analyses |
| emotional_thematic | 1536 | Hybrid | Emotions, themes |
| psychological_constructs | 1024 | OpenAI | Beliefs, distortions |
| meta_patterns | 1024 | OpenAI | Blind spots, patterns |

### 4-Layer Personality Model

1. **Big Five** - Stable traits (OCEAN)
2. **Dynamic Traits** - Emotional regulation, stress response
3. **Adaptive Traits** - Coping, defenses, attachment
4. **Domain Traits** - Work, relationships, health

### ChatCoachService (6 Phase 2-3 Components)

- Enhanced AI Router - psychological context routing
- Adaptive Communication Style - Big Five adaptation
- Deep Question Generator - 5 question categories
- Micro Interventions - reframing, anchoring, challenge
- Confidence Calculator - 5-factor scoring
- Vector Storytelling - 132-point evolution

### AI Router

| Condition | Model | Reason |
|-----------|-------|--------|
| Crisis, existential, SHADOW depth | Claude Sonnet 4 | Safety, nuance |
| Action plans, emotional support | GPT-4o | Quality balance |
| Simple chat | GPT-4o-mini | Speed, cost |

---

## Development Roadmap

See `docs/ARCHITECTURE_ROADMAP.md` for full details.

| Month | Phase | Status |
|-------|-------|--------|
| 1 | Foundation | ✅ 100% |
| 2 | Core Features | ✅ 100% |
| 3 | Psychological Depth | ✅ 100% |
| 4 | Temporal & Advanced | ✅ 100% |
| 5 | Validation | ✅ 100% |
| 6 | Production | 🔄 50% |

**Remaining:**
- Clinical validation (requires psychologist)
- Target metrics validation
- A/B testing

---

## Database

### PostgreSQL
- **Host:** localhost
- **Port:** 5434
- **Database:** selfology
- **Schema:** selfology
- **User:** selfology_user
- **Password:** selfology_secure_2024

### Tables (selfology schema)

**Core:**
- users, onboarding_sessions, user_answers_new, answer_analysis

**Psychological constructs:**
- cognitive_distortions, defense_mechanisms, core_beliefs
- blind_spots, attachment_patterns, growth_areas
- personality_states, alliance_measurements, breakthrough_moments

**Personality:**
- digital_personality, personality_profiles

### Redis
- **Host:** localhost
- **Port:** 6379
- **DB 0:** Cache
- **DB 1:** FSM Storage

---

## Essential Commands

### Health Check
```bash
python scripts/psychological_health_check.py
```

### Testing
```bash
pytest tests/
python tests/test_psychological_components.py
```

### Validation with AI
```bash
python scripts/opus_validation.py --samples 30
```

### Database
```bash
docker exec selfology-postgres psql -U selfology_user -d selfology
```

### Logs
```bash
tail -f logs/selfology.log
grep "Error" logs/selfology.log | tail -20
```

---

## Bot Features

### Whitelist
Only user ID 98005572 can use the bot. Others get "🔒 Доступ ограничен".

Configured in `selfology_controller.py`:
```python
WHITELIST_USERS = [98005572]
```

### Auto Menu Commands
Bot automatically sets Telegram menu on startup:
- /start - Начать работу с коучем
- /onboarding - Пройти психологический онбординг
- /chat - Чат с AI-коучем
- /profile - Мой профиль
- /help - Помощь

### Instance Locking
Redis lock prevents duplicate bot instances (BOT_INSTANCE_LOCK_KEY).

---

## Documentation

- `docs/ARCHITECTURE_ROADMAP.md` - Development roadmap with progress
- `docs/selfology_architecture.html` - Interactive architecture visualization
- `research/` - Original research documents

---

## Important Notes

### Paths
- **Project:** `/home/ksnk/microservices/critical/selfology-bot`
- **NOT:** `/home/ksnk/n8n-enterprise/projects/selfology`

### Database
- Use `selfology` database, NOT `n8n`
- All tables in `selfology` schema, NOT `public`
- Port 5434 for selfology-postgres

### Development
- All imports are absolute (not relative)
- Russian regex patterns in detectors
- Russian comments in code
- English variable names

### Safety
- Energy Safety: Never HEAVY→HEAVY questions
- Gating: Check alliance before surfacing content
- 693 questions in Intelligent Question Core

---

## Production Status

- ✅ Bot deployed: @SelfologyMeCoachBot
- ✅ 10 psychological components operational
- ✅ 5 Qdrant collections populated
- ✅ PostgreSQL with 9 psychological tables
- ✅ Redis FSM + instance locking
- ✅ Whitelist for personal use
- ✅ Auto-set bot menu commands
- ✅ HTML architecture visualization
