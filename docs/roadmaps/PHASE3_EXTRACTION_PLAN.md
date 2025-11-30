# Phase 3: Extraction Plan for selfology_controller.py

## Current State
- **File:** selfology_controller.py
- **Lines:** 2,403
- **Target:** Max 600 lines per file

## Extraction Order (Bottom-Up, Safest First)

### Step 1: Extract FSM States (NO DEPENDENCIES)
```
selfology_bot/bot/states.py
├── OnboardingStates (19 lines)
└── ChatStates (27 lines)
```
**Risk:** LOW - standalone dataclasses, no method dependencies

### Step 2: Extract Onboarding Handlers (~660 lines)
```
selfology_bot/bot/handlers/onboarding.py
├── _show_onboarding_question
├── _show_cluster_question
├── cmd_onboarding
├── handle_onboarding_answer
├── callback_skip_question
├── callback_end_session
├── callback_flag_question
├── callback_end_onboarding
├── callback_continue_onboarding
├── callback_mode_auto
├── callback_mode_program
├── callback_select_program
├── handle_program_number_input
└── callback_back_to_mode_selection
```
**Risk:** MEDIUM - depends on self.orchestrator, self.db_service

### Step 3: Extract Program Flow Handlers (~576 lines)
```
selfology_bot/bot/handlers/program.py
├── callback_mode_finish
├── callback_continue_cluster
├── callback_continue_next_cluster
├── callback_pause_cluster
├── callback_continue_session
├── _show_program_question
├── handle_program_answer
├── _show_block_transition
├── _complete_program_flow
├── callback_continue_program_block
├── callback_pause_program
├── callback_skip_program_question
└── callback_process_orphaned
```
**Risk:** MEDIUM - depends on orchestrator and state

### Step 4: Extract Chat Handlers (~158 lines)
```
selfology_bot/bot/handlers/chat.py
├── cmd_chat
├── callback_start_chat
├── handle_chat_message
├── callback_coming_soon
└── handle_unknown
```
**Risk:** MEDIUM - depends on ChatCoachService

### Step 5: Extract Menu/GDPR Handlers (~80 lines)
```
selfology_bot/bot/handlers/menu.py
├── callback_main_menu
├── callback_help
├── callback_profile
├── callback_gdpr_details
├── callback_gdpr_accept
└── callback_gdpr_decline
```
**Risk:** LOW - mostly UI code

### Step 6: Refactor Core Controller (~500 lines remaining)
```
selfology_controller.py (refactored)
├── Imports
├── SelfologyController
│   ├── __init__
│   ├── _register_handlers (imports from handlers/)
│   ├── _send_long_message
│   ├── _log_state_change
│   ├── _show_main_menu
│   └── Instance lock methods
└── main()
```

## Target Structure After Extraction

```
selfology_bot/
├── bot/
│   ├── __init__.py
│   ├── states.py           # FSM states (~50 lines)
│   └── handlers/
│       ├── __init__.py
│       ├── onboarding.py   # Onboarding handlers (~600 lines)
│       ├── program.py      # Program flow (~550 lines)
│       ├── chat.py         # Chat handlers (~200 lines)
│       └── menu.py         # Menu/GDPR (~100 lines)
│
selfology_controller.py     # Core controller (~500 lines)
```

## Verification After Each Step

```bash
# After each extraction:
1. python -c "from selfology_controller import SelfologyController; print('OK')"
2. source venv/bin/activate && timeout 10 python selfology_controller.py
3. Send /start to bot in Telegram
```

## Backwards Compatibility Strategy

During extraction, keep temporary imports in selfology_controller.py:
```python
# TEMPORARY: backwards compat during refactor
from selfology_bot.bot.states import OnboardingStates, ChatStates
# ... use normally in code
```

After all handlers migrated, remove old code blocks.

## Rollback Plan

If anything breaks:
```bash
git checkout HEAD~1 -- selfology_controller.py
```

---
Created: 2024-11-30
