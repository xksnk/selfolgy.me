# Selfology Documentation Index

> **Updated:** 2024-11-30 | **Status:** After Phase 1-2 refactoring

## Quick Links

- [CLAUDE.md](../CLAUDE.md) - Project instructions for AI assistants
- [README.md](../README.md) - Project overview

---

## Architecture

Technical architecture and system design documentation.

| File | Description |
|------|-------------|
| [ARCHITECTURE.md](architecture/ARCHITECTURE.md) | General system architecture overview |
| [CHAT_COACH_ARCHITECTURE.md](architecture/CHAT_COACH_ARCHITECTURE.md) | AI coach architecture with UserDossierService |
| [PROJECT_STRUCTURE.md](architecture/PROJECT_STRUCTURE.md) | Codebase structure and organization |
| [DATA_STORAGE_ARCHITECTURE_ANALYSIS.md](architecture/DATA_STORAGE_ARCHITECTURE_ANALYSIS.md) | Database and vector storage design |
| [COUNTER_ARCHITECTURE.md](architecture/COUNTER_ARCHITECTURE.md) | Answer counter system design |

---

## Guides

Operational guides and how-to documentation.

| File | Description |
|------|-------------|
| [API_DOCUMENTATION.md](guides/API_DOCUMENTATION.md) | API endpoints and usage |
| [RUNBOOK.md](guides/RUNBOOK.md) | Operations runbook for deployment and maintenance |
| [MONITORING_INTEGRATION.md](guides/MONITORING_INTEGRATION.md) | Monitoring setup and integration |
| [ONBOARDING_MONITORING.md](guides/ONBOARDING_MONITORING.md) | Onboarding flow monitoring |

---

## Roadmaps

Development plans and future work.

| File | Description |
|------|-------------|
| [REFACTORING_PLAN.md](roadmaps/REFACTORING_PLAN.md) | Current refactoring plan (Phase 1-4) |
| [CURRENT_STATE_BEFORE_REFACTOR.md](roadmaps/CURRENT_STATE_BEFORE_REFACTOR.md) | System state snapshot before refactoring |
| [PROGRAM_ROADMAP.md](roadmaps/PROGRAM_ROADMAP.md) | Program development roadmap |
| [PROGRAMS_REFACTOR_ROADMAP.md](roadmaps/PROGRAMS_REFACTOR_ROADMAP.md) | Programs system refactoring |
| [PROGRAM_INTEGRATION_ROADMAP.md](roadmaps/PROGRAM_INTEGRATION_ROADMAP.md) | Program integration plan |
| [CATEGORIES_IMPLEMENTATION_PLAN.md](roadmaps/CATEGORIES_IMPLEMENTATION_PLAN.md) | Question categories implementation |
| [NEW_ONBOARDING_INTERVIEW.md](roadmaps/NEW_ONBOARDING_INTERVIEW.md) | New onboarding interview design |

---

## Research

Research documents and analysis.

| File | Description |
|------|-------------|
| [ai_coach_architecture_research.md](research/ai_coach_architecture_research.md) | AI coach architecture research |
| [ai_coach_knows_all_v2.md](research/ai_coach_knows_all_v2.md) | "AI coach knows everything" architecture |
| [ai_coach_knows_everything_v3.md](research/ai_coach_knows_everything_v3.md) | Extended "knows everything" research |
| [digital_personality_fingerprint.md](research/digital_personality_fingerprint.md) | Digital personality architecture |
| [question_design_best_practices_v2.md](research/question_design_best_practices_v2.md) | Question design best practices |
| [reflective_survey_methodology_v2.md](research/reflective_survey_methodology_v2.md) | Reflective survey methodology |
| [perplexity_coach_research_prompt.md](research/perplexity_coach_research_prompt.md) | Research prompts |
| [appleOrange.md](research/appleOrange.md) | Misc research notes |

---

## Archive Location

Old/completed documents are archived in `_archive/old_docs/` (gitignored).
To recover archived docs, use git history:

```bash
# List archived docs in git history
git show HEAD~1:docs/FILENAME.md

# Restore specific file
git checkout HEAD~1 -- path/to/old/file.md
```

---

## File Organization Rules

1. **architecture/** - System design docs (how things work)
2. **guides/** - How-to docs (how to do things)
3. **roadmaps/** - Plans and futures (what we'll do)
4. **research/** - Analysis and research (why we do things)

### Naming Conventions

- Use UPPERCASE for main docs (e.g., `ARCHITECTURE.md`)
- Use lowercase with underscores for research (e.g., `ai_coach_research.md`)
- Date format: YYYY-MM-DD in content headers
- Max file size: 600 lines (split if larger)
