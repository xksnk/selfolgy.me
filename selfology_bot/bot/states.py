from aiogram.fsm.state import State, StatesGroup


class OnboardingStates(StatesGroup):
    """User onboarding flow states"""
    welcome = State()
    gdpr_consent = State()
    basic_info = State()
    personality_test_intro = State()
    personality_test = State()
    values_assessment = State()
    goals_setting = State()
    onboarding_complete = State()


class PersonalityTestStates(StatesGroup):
    """Personality assessment flow states"""
    big_five_openness = State()
    big_five_conscientiousness = State()
    big_five_extraversion = State()
    big_five_agreeableness = State()
    big_five_neuroticism = State()
    
    values_family = State()
    values_career = State()
    values_health = State()
    values_creativity = State()
    values_security = State()
    
    goals_short_term = State()
    goals_long_term = State()
    goals_priorities = State()
    
    test_complete = State()


class ChatStates(StatesGroup):
    """Main chat interaction states"""
    idle = State()
    chatting = State()
    daily_checkin = State()
    goal_tracking = State()
    deep_reflection = State()


class SettingsStates(StatesGroup):
    """User settings and preferences"""
    main_menu = State()
    privacy_settings = State()
    notification_settings = State()
    ai_preferences = State()
    export_data = State()


class CoachingStates(StatesGroup):
    """AI coaching session states"""
    session_start = State()
    problem_identification = State()
    context_gathering = State()
    solution_exploration = State()
    action_planning = State()
    session_summary = State()