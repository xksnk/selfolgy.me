from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends
from typing import Dict, Any

from ..states import OnboardingStates, PersonalityTestStates
from ...core.database import get_db
from ...services.user_service import UserService
from ...services.vector_service import VectorService
from ...ai.router import AIRouter, TaskComplexity
from ...ai.clients import ai_client_manager

router = Router()


# Big Five Personality Assessment Questions
BIG_FIVE_QUESTIONS = {
    "openness": [
        "Я часто экспериментирую с новыми идеями и подходами",
        "Мне интересны абстрактные концепции и теории", 
        "Я предпочитаю творческие решения стандартным",
        "Меня привлекают новые и необычные переживания"
    ],
    "conscientiousness": [
        "Я всегда довожу начатое дело до конца",
        "Порядок и организованность важны для меня",
        "Я планирую свои действия заранее",
        "Я ответственно отношусь к своим обязательствам"
    ],
    "extraversion": [
        "Я легко завожу новые знакомства",
        "Мне комфортно быть в центре внимания",
        "Я получаю энергию от общения с людьми",
        "Я предпочитаю активные групповые мероприятия"
    ],
    "agreeableness": [
        "Я всегда стараюсь помочь другим людям",
        "Мне важно поддерживать гармонию в отношениях",
        "Я доверяю людям и верю в их добрые намерения",
        "Я готов идти на компромиссы ради общего блага"
    ],
    "neuroticism": [
        "Я часто переживаю и волнуюсь по мелочам",
        "Стресс сильно влияет на мое самочувствие",
        "Мое настроение часто меняется в течение дня",
        "Я склонен к тревожным мыслям о будущем"
    ]
}

VALUES_QUESTIONS = [
    {
        "category": "family",
        "question": "Насколько важны для вас семейные отношения и близкие связи?",
        "options": ["Критически важно", "Очень важно", "Важно", "Умеренно важно", "Не очень важно"]
    },
    {
        "category": "career", 
        "question": "Насколько важен для вас карьерный рост и профессиональные достижения?",
        "options": ["Критически важно", "Очень важно", "Важно", "Умеренно важно", "Не очень важно"]
    },
    {
        "category": "health",
        "question": "Насколько важно для вас физическое и психическое здоровье?",
        "options": ["Критически важно", "Очень важно", "Важно", "Умеренно важно", "Не очень важно"]
    },
    {
        "category": "creativity",
        "question": "Насколько важны для вас творческая самореализация и самовыражение?",
        "options": ["Критически важно", "Очень важно", "Важно", "Умеренно важно", "Не очень важно"]
    },
    {
        "category": "security",
        "question": "Насколько важны для вас стабильность и финансовая безопасность?",
        "options": ["Критически важно", "Очень важно", "Важно", "Умеренно важно", "Не очень важно"]
    }
]


@router.callback_query(F.data == "start_assessment")
async def start_personality_assessment(
    callback: CallbackQuery, 
    state: FSMContext,
    session: AsyncSession = Depends(get_db)
):
    """Start the Big Five personality assessment"""
    
    await state.update_data(
        current_trait=0,
        current_question=0,
        responses={}
    )
    
    intro_text = """
🧠 Психологическая диагностика личности

Сейчас я проведу с вами быстрый, но точный психологический анализ на основе модели "Большая Пятерка" - золотого стандарта в психологии личности.

📊 Что мы определим:
• **Открытость** - склонность к новому опыту
• **Добросовестность** - организованность и целеустремленность  
• **Экстраверсия** - энергичность в социальном взаимодействии
• **Доброжелательность** - склонность к сотрудничеству
• **Нейротизм** - эмоциональная стабильность

⏱️ Займет 5-7 минут
🎯 20 вопросов с выбором ответа

Готовы начать?
    """
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 Начать тест", callback_data="begin_big_five")],
        [InlineKeyboardButton(text="📖 Подробнее о тесте", callback_data="explain_big_five")]
    ])
    
    await callback.message.edit_text(intro_text, reply_markup=keyboard)
    await state.set_state(OnboardingStates.personality_test_intro)


@router.callback_query(F.data == "explain_big_five")
async def explain_big_five(callback: CallbackQuery):
    """Explain the Big Five model"""
    
    explanation = """
📚 Модель "Большая Пятерка"

Это научно обоснованная модель, используемая психологами во всем мире для описания человеческой личности.

🔍 **Открытость к опыту**
Воображение, любознательность, креативность

📋 **Добросовестность**  
Самоконтроль, организованность, настойчивость

👥 **Экстраверсия**
Общительность, энергичность, позитивные эмоции

🤝 **Доброжелательность**
Доверие, сотрудничество, эмпатия

😰 **Нейротизм** 
Эмоциональная нестабильность, тревожность

✅ **Точность**: 85-90% (исследования подтверждают высокую валидность)
🔬 **Научность**: Используется в ведущих университетах мира
🎯 **Практичность**: Поможет лучше понять себя и свои реакции
    """
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 Понятно, начинаем!", callback_data="begin_big_five")]
    ])
    
    await callback.message.edit_text(explanation, reply_markup=keyboard)


@router.callback_query(F.data == "begin_big_five")
async def begin_big_five_test(callback: CallbackQuery, state: FSMContext):
    """Begin the Big Five personality test"""
    
    await show_next_question(callback.message, state)
    await state.set_state(PersonalityTestStates.big_five_openness)


async def show_next_question(message: Message, state: FSMContext):
    """Show the next personality test question"""
    
    data = await state.get_data()
    current_trait = data.get("current_trait", 0)
    current_question = data.get("current_question", 0)
    
    trait_names = list(BIG_FIVE_QUESTIONS.keys())
    
    if current_trait >= len(trait_names):
        await complete_personality_test(message, state)
        return
    
    trait_name = trait_names[current_trait]
    questions = BIG_FIVE_QUESTIONS[trait_name]
    
    if current_question >= len(questions):
        # Move to next trait
        await state.update_data(
            current_trait=current_trait + 1,
            current_question=0
        )
        await show_next_question(message, state)
        return
    
    question_text = questions[current_question]
    progress = (current_trait * 4 + current_question + 1)
    total_questions = len(trait_names) * 4
    
    trait_emoji = {
        "openness": "🎨",
        "conscientiousness": "📋", 
        "extraversion": "👥",
        "agreeableness": "🤝",
        "neuroticism": "😰"
    }
    
    text = f"""
{trait_emoji.get(trait_name, "🧠")} **{trait_name.title()}**

**Вопрос {progress}/{total_questions}:**

{question_text}

Насколько это утверждение соответствует вам?
    """
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💯 Полностью согласен", callback_data=f"answer_5_{trait_name}_{current_question}")],
        [InlineKeyboardButton(text="✅ Скорее согласен", callback_data=f"answer_4_{trait_name}_{current_question}")],
        [InlineKeyboardButton(text="🤔 Нейтрально", callback_data=f"answer_3_{trait_name}_{current_question}")],
        [InlineKeyboardButton(text="❌ Скорее не согласен", callback_data=f"answer_2_{trait_name}_{current_question}")],
        [InlineKeyboardButton(text="🚫 Совершенно не согласен", callback_data=f"answer_1_{trait_name}_{current_question}")]
    ])
    
    await message.edit_text(text, reply_markup=keyboard)


@router.callback_query(F.data.startswith("answer_"))
async def handle_personality_answer(callback: CallbackQuery, state: FSMContext):
    """Handle personality test answer"""
    
    # Parse callback data: answer_{score}_{trait}_{question}
    parts = callback.data.split("_")
    score = int(parts[1])
    trait = parts[2]
    question_idx = int(parts[3])
    
    data = await state.get_data()
    responses = data.get("responses", {})
    
    if trait not in responses:
        responses[trait] = {}
    
    responses[trait][question_idx] = score
    
    await state.update_data(
        responses=responses,
        current_question=data.get("current_question", 0) + 1
    )
    
    await show_next_question(callback.message, state)


async def complete_personality_test(message: Message, state: FSMContext):
    """Complete personality test and show results"""
    
    data = await state.get_data()
    responses = data.get("responses", {})
    
    # Calculate trait scores
    trait_scores = {}
    for trait, answers in responses.items():
        avg_score = sum(answers.values()) / len(answers)
        trait_scores[trait] = round(avg_score / 5.0, 2)  # Normalize to 0-1
    
    await state.update_data(personality_scores=trait_scores)
    
    # Show preliminary results
    results_text = f"""
🎉 Тест завершен! Ваш психологический профиль:

🎨 **Открытость**: {trait_scores.get('openness', 0):.0%}
📋 **Добросовестность**: {trait_scores.get('conscientiousness', 0):.0%}  
👥 **Экстраверсия**: {trait_scores.get('extraversion', 0):.0%}
🤝 **Доброжелательность**: {trait_scores.get('agreeableness', 0):.0%}
😰 **Эмоциональная нестабильность**: {trait_scores.get('neuroticism', 0):.0%}

Теперь давайте определим ваши жизненные ценности и приоритеты.

Это поможет AI-коучу лучше понимать ваши мотивы и давать более точные рекомендации.
    """
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Продолжить", callback_data="start_values_assessment")],
        [InlineKeyboardButton(text="📈 Подробные результаты", callback_data="detailed_personality_results")]
    ])
    
    await message.edit_text(results_text, reply_markup=keyboard)


@router.callback_query(F.data == "start_values_assessment")
async def start_values_assessment(callback: CallbackQuery, state: FSMContext):
    """Start values assessment"""
    
    await state.update_data(
        current_values_question=0,
        values_responses={}
    )
    
    await show_next_values_question(callback.message, state)
    await state.set_state(PersonalityTestStates.values_family)


async def show_next_values_question(message: Message, state: FSMContext):
    """Show next values question"""
    
    data = await state.get_data()
    current_question = data.get("current_values_question", 0)
    
    if current_question >= len(VALUES_QUESTIONS):
        await complete_values_assessment(message, state)
        return
    
    question_data = VALUES_QUESTIONS[current_question]
    
    text = f"""
💎 **Жизненные ценности**

**Вопрос {current_question + 1}/{len(VALUES_QUESTIONS)}:**

{question_data['question']}
    """
    
    keyboard_buttons = []
    for i, option in enumerate(question_data['options']):
        score = 5 - i  # Reverse scoring for importance
        keyboard_buttons.append([
            InlineKeyboardButton(
                text=f"{option}", 
                callback_data=f"values_{question_data['category']}_{score}"
            )
        ])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    
    await message.edit_text(text, reply_markup=keyboard)


@router.callback_query(F.data.startswith("values_"))
async def handle_values_answer(callback: CallbackQuery, state: FSMContext):
    """Handle values assessment answer"""
    
    # Parse: values_{category}_{score}
    parts = callback.data.split("_")
    category = parts[1]
    score = int(parts[2])
    
    data = await state.get_data()
    values_responses = data.get("values_responses", {})
    values_responses[category] = score
    
    current_question = data.get("current_values_question", 0) + 1
    
    await state.update_data(
        values_responses=values_responses,
        current_values_question=current_question
    )
    
    await show_next_values_question(callback.message, state)


async def complete_values_assessment(message: Message, state: FSMContext):
    """Complete values assessment"""
    
    data = await state.get_data()
    values_responses = data.get("values_responses", {})
    
    # Normalize values scores
    values_scores = {k: v / 5.0 for k, v in values_responses.items()}
    
    await state.update_data(values_scores=values_scores)
    
    text = """
🎯 **Постановка целей**

Последний шаг - определим ваши главные цели на ближайшие 6-12 месяцев.

Это поможет AI-коучу фокусировать советы на том, что для вас действительно важно.

Выберите до 3 главных целей:
    """
    
    goal_categories = [
        ("career", "🚀 Карьера и профессия"),
        ("relationships", "❤️ Отношения и семья"), 
        ("health", "💪 Здоровье и фитнес"),
        ("learning", "📚 Обучение и развитие"),
        ("creativity", "🎨 Творчество и хобби"),
        ("travel", "✈️ Путешествия и опыт"),
        ("finance", "💰 Финансы и инвестиции"),
        ("spirituality", "🧘 Духовность и философия")
    ]
    
    keyboard_buttons = []
    for goal_id, goal_text in goal_categories:
        keyboard_buttons.append([
            InlineKeyboardButton(text=goal_text, callback_data=f"goal_{goal_id}")
        ])
    
    keyboard_buttons.append([
        InlineKeyboardButton(text="✅ Завершить выбор", callback_data="complete_goals")
    ])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    
    await message.edit_text(text, reply_markup=keyboard)
    await state.set_state(PersonalityTestStates.goals_short_term)


@router.callback_query(F.data.startswith("goal_"))
async def handle_goal_selection(callback: CallbackQuery, state: FSMContext):
    """Handle goal selection"""
    
    goal_id = callback.data.split("_")[1]
    
    data = await state.get_data()
    selected_goals = data.get("selected_goals", [])
    
    if goal_id in selected_goals:
        selected_goals.remove(goal_id)
        status = "❌"
    else:
        if len(selected_goals) < 3:
            selected_goals.append(goal_id)
            status = "✅"
        else:
            await callback.answer("Максимум 3 цели!", show_alert=True)
            return
    
    await state.update_data(selected_goals=selected_goals)
    await callback.answer(f"{status} Выбрано целей: {len(selected_goals)}/3")


@router.callback_query(F.data == "complete_goals")
async def complete_goals_selection(
    callback: CallbackQuery, 
    state: FSMContext,
    session: AsyncSession = Depends(get_db)
):
    """Complete goals selection and finish onboarding"""
    
    data = await state.get_data()
    selected_goals = data.get("selected_goals", [])
    
    if not selected_goals:
        await callback.answer("Выберите хотя бы одну цель!", show_alert=True)
        return
    
    # Compile all assessment data
    personality_scores = data.get("personality_scores", {})
    values_scores = data.get("values_scores", {})
    
    assessment_data = {
        "personality": personality_scores,
        "values": values_scores,
        "goals": selected_goals,
        "version": 1,
        "completed_at": datetime.utcnow().isoformat()
    }
    
    # Save to database
    user_service = UserService(session)
    vector_service = VectorService()
    
    # Save questionnaire response
    await user_service.save_questionnaire_response(
        telegram_id=callback.from_user.id,
        questionnaire_type="complete_assessment",
        responses=assessment_data
    )
    
    # Generate personality description for vector embedding
    personality_description = generate_personality_description(assessment_data)
    
    # Store in vector database
    vector_id = await vector_service.store_personality_profile(
        user_id=str(callback.from_user.id),
        personality_data=assessment_data,
        text_description=personality_description
    )
    
    # Save personality vector
    await user_service.save_personality_vector(
        telegram_id=callback.from_user.id,
        traits=assessment_data,
        qdrant_point_id=vector_id,
        source_data="complete_assessment"
    )
    
    # Mark onboarding as completed
    await user_service.update_onboarding_status(callback.from_user.id, True)
    
    # Generate AI insights about the personality
    await generate_initial_insights(callback, state, assessment_data, session)


async def generate_initial_insights(
    callback: CallbackQuery, 
    state: FSMContext, 
    assessment_data: Dict[str, Any],
    session: AsyncSession
):
    """Generate initial AI insights about user's personality"""
    
    # Use AI Router for deep analysis
    router = AIRouter(user_tier="free")  # TODO: Get actual user tier
    
    routing_result = router.route_request(
        task_description="deep personality analysis assessment results",
        message_content=f"Personality assessment results: {assessment_data}",
        context={"questionnaire_type": "personality", "is_onboarding": True}
    )
    
    # Create system prompt for personality analysis
    system_prompt = """
    Вы эксперт-психолог, анализирующий результаты психологической диагностики.
    
    Проанализируйте результаты и дайте:
    1. Краткую характеристику личности (3-4 предложения)
    2. Ключевые сильные стороны (2-3 пункта)
    3. Зоны роста и развития (2-3 пункта)  
    4. Персональные рекомендации (2-3 совета)
    
    Тон: дружелюбный, поддерживающий, конструктивный.
    Формат: структурированный текст с emoji.
    """
    
    messages = [
        {
            "role": "user", 
            "content": f"Результаты психологической диагностики пользователя:\n{assessment_data}"
        }
    ]
    
    try:
        insights = await ai_client_manager.generate_response(
            model=routing_result.model,
            messages=messages,
            system_prompt=system_prompt,
            max_tokens=800
        )
        
        # Store insights
        user_service = UserService(session)
        await user_service.save_chat_message(
            telegram_id=callback.from_user.id,
            content=insights,
            message_type="assistant",
            ai_model_used=routing_result.model.value,
            insights={"type": "initial_assessment", "cost": routing_result.estimated_cost}
        )
        
        completion_text = f"""
🎉 **Онбординг завершен!**

Ваш персональный профиль создан и сохранен. Теперь AI-коуч знает вас лучше!

**💡 Первичный анализ вашей личности:**

{insights}

---

🚀 **Что дальше?**
• Начните диалог с AI-коучем  
• Ведите умный дневник
• Отслеживайте прогресс по целям
• Получайте персональные инсайты

Добро пожаловать в Selfology! 🌟
        """
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💬 Начать чат с коучем", callback_data="start_chat")],
            [InlineKeyboardButton(text="📊 Посмотреть профиль", callback_data="show_profile")]
        ])
        
        await callback.message.edit_text(completion_text, reply_markup=keyboard)
        
    except Exception as e:
        # Fallback without AI analysis
        completion_text = """
🎉 **Онбординг завершен!**

Ваш персональный профиль создан! AI-коуч теперь может предоставлять персонализированные советы на основе вашей личности.

🚀 **Готово к использованию:**
✅ Психологический профиль сохранен
✅ Жизненные ценности определены  
✅ Цели установлены
✅ Векторный анализ настроен

Добро пожаловать в Selfology! 🌟
        """
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💬 Начать чат с коучем", callback_data="start_chat")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
        ])
        
        await callback.message.edit_text(completion_text, reply_markup=keyboard)
    
    await state.clear()  # Clear onboarding state


def generate_personality_description(assessment_data: Dict[str, Any]) -> str:
    """Generate human-readable personality description for vector embedding"""
    
    personality = assessment_data.get("personality", {})
    values = assessment_data.get("values", {})
    goals = assessment_data.get("goals", [])
    
    # Convert scores to descriptive text
    trait_descriptions = {
        "openness": {
            "high": "креативная, любознательная, открытая к новому опыту",
            "medium": "умеренно открытая к новым идеям", 
            "low": "предпочитающая знакомое и проверенное"
        },
        "conscientiousness": {
            "high": "организованная, целеустремленная, дисциплинированная",
            "medium": "умеренно организованная",
            "low": "спонтанная, гибкая в планах"
        },
        "extraversion": {
            "high": "общительная, энергичная, любящая компанию", 
            "medium": "амбивертная",
            "low": "интровертная, предпочитающая уединение"
        },
        "agreeableness": {
            "high": "доброжелательная, сотрудничающая, эмпатичная",
            "medium": "умеренно дружелюбная",
            "low": "независимая, прямолинейная"
        },
        "neuroticism": {
            "high": "эмоционально чувствительная, склонная к переживаниям",
            "medium": "умеренно эмоциональная",
            "low": "эмоционально стабильная, спокойная"
        }
    }
    
    def get_level(score):
        if score > 0.7:
            return "high"
        elif score < 0.3:
            return "low" 
        return "medium"
    
    personality_text = []
    for trait, score in personality.items():
        level = get_level(score)
        if trait in trait_descriptions and level in trait_descriptions[trait]:
            personality_text.append(trait_descriptions[trait][level])
    
    # Top values
    top_values = sorted(values.items(), key=lambda x: x[1], reverse=True)[:3]
    values_text = [k for k, v in top_values if v > 0.6]
    
    # Goals
    goal_names = {
        "career": "карьерный рост",
        "relationships": "отношения",
        "health": "здоровье", 
        "learning": "обучение",
        "creativity": "творчество",
        "travel": "путешествия",
        "finance": "финансы",
        "spirituality": "духовное развитие"
    }
    goals_text = [goal_names.get(g, g) for g in goals]
    
    description = f"""
Личность: {', '.join(personality_text)}.
Ключевые ценности: {', '.join(values_text)}.
Основные цели: {', '.join(goals_text)}.
    """.strip()
    
    return description