"""
Chat Coach Service - Separate chat service with personalization
Independent service for AI-powered coaching conversations
"""
import time
import asyncpg
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import sys
import re

# Add path for Phase 2 components
sys.path.append('/home/ksnk/n8n-enterprise/projects/selfology')

from data_access.user_dao import UserDAO
from data_access.vector_dao import VectorDAO
from data_access.coach_vector_dao import CoachVectorDAO
from services.message_embedding_service import MessageEmbeddingService
from core.config import get_config
from core.logging import chat_logger, LoggerMixin

# Phase 2 component imports
from coach.components.enhanced_ai_router import EnhancedAIRouter
from coach.components.adaptive_communication_style import AdaptiveCommunicationStyle

# 🔥 NEW: Phase 2-3 component imports (Deep Questions + Micro Interventions)
from coach.components.deep_question_generator import DeepQuestionGenerator
from coach.components.micro_interventions import MicroInterventions

# 🔥 TRACK 3: Confidence Calculator + Vector Storytelling (Phase 2-3)
from coach.components.confidence_calculator import ConfidenceCalculator
from coach.components.vector_storytelling import VectorStorytelling

# 🔥 NEW: AI Clients for REAL responses (not templates!)
from selfology_bot.ai.clients import ai_client_manager
from selfology_bot.ai.router import AIModel


@dataclass
class ChatResponse:
    """Response from chat service"""
    success: bool
    message: str
    response_text: Optional[str] = None
    ai_model_used: Optional[str] = None
    processing_time: Optional[float] = None
    insights_detected: Optional[List[str]] = None
    personality_updates: Optional[Dict[str, float]] = None


@dataclass
class UserContext:
    """User context for personalized responses"""
    user_id: str
    personality_profile: Optional[Dict[str, Any]] = None
    recent_messages: List[Dict[str, Any]] = None
    insights_history: List[Dict[str, Any]] = None
    assessment_data: Optional[Dict[str, Any]] = None
    onboarding_answers: List[Dict[str, Any]] = None  # 🔥 NEW: User's onboarding answers (work, goals, etc.)
    context_stories: List[Dict[str, Any]] = None  # 🔥 NEW: Специальные вопросы (цели, дилеммы, контекст)
    current_mood: Optional[str] = None
    conversation_stage: str = "general"


class ChatCoachService(LoggerMixin):
    """
    Independent Chat Coach Service

    Features:
    - Personalized responses based on user's psychological profile
    - Context-aware conversations with memory
    - Insight detection and storage
    - Personality-adaptive communication style
    - Independent from assessment system
    - 🔥 NEW: Deep question generation + Micro interventions (Phase 2-3)
    """

    def __init__(self, db_pool: Optional[asyncpg.Pool] = None):
        self.config = get_config()
        self.db_pool = db_pool

        # Initialize DAOs
        self.user_dao = UserDAO(db_pool)
        self.vector_dao = VectorDAO()

        # ⚡ NEW: CoachVectorDAO for fast Qdrant access
        self.coach_vector_dao = CoachVectorDAO()
        self.logger.info("✅ CoachVectorDAO initialized for semantic search")

        # 🔥 NEW: MessageEmbeddingService for semantic search
        self.embedding_service = MessageEmbeddingService()
        self.logger.info("✅ MessageEmbeddingService initialized (1536D OpenAI embeddings)")

        # Phase 2 components
        self.enhanced_router = EnhancedAIRouter()
        self.adaptive_styler = AdaptiveCommunicationStyle()
        self.logger.info("✅ Phase 2 components initialized (Enhanced Router + Adaptive Style)")

        # 🔥 NEW: Phase 2-3 components  
        self.question_generator = DeepQuestionGenerator()
        self.micro_interventions = MicroInterventions()
        self.logger.info("✅ Phase 2-3 components initialized (Deep Questions + Micro Interventions)")
        
        # 🔥 TRACK 3: Confidence + Storytelling (Phase 2-3)
        self.confidence_calc = ConfidenceCalculator()
        self.storyteller = VectorStorytelling()
        self.logger.info("✅ TRACK 3 components initialized (Confidence + Storytelling)")

        # 🔥 NEW: AI Client Manager for REAL AI responses!
        self.ai_client = ai_client_manager
        self.logger.info("✅ AI Client Manager initialized (Claude + OpenAI) - REAL RESPONSES ENABLED!")

        # Service configuration
        self.chat_config = self.config.get_service_config("chat_coach")
        self.context_window = self.chat_config.get("context_window", 10)
        self.personality_weight = self.chat_config.get("personality_weight", 0.7)
        self.memory_retention_days = self.chat_config.get("memory_retention_days", 30)

        # Response templates for different personality types
        self.response_templates = self._initialize_response_templates()

        # Conversation state (in production would use Redis)
        self.conversation_states = {}  # user_id -> conversation state

        self.logger.info("Chat Coach Service initialized")

    def _markdown_to_html(self, text: str) -> str:
        """
        Convert Markdown formatting to HTML for Telegram

        Converts:
        - **bold** → <b>bold</b>
        - _italic_ → <i>italic</i>
        - __italic__ → <i>italic</i>
        - ***bold italic*** → <b><i>bold italic</i></b>
        """
        if not text:
            return text

        # Convert ***bold italic*** first (before splitting into bold and italic)
        text = re.sub(r'\*\*\*(.+?)\*\*\*', r'<b><i>\1</i></b>', text)

        # Convert **bold**
        text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)

        # Convert _italic_ and __italic__
        text = re.sub(r'__(.+?)__', r'<i>\1</i>', text)
        text = re.sub(r'_(.+?)_', r'<i>\1</i>', text)

        return text

    async def start_chat_session(self, user_id: str) -> ChatResponse:
        """Start new chat session for user"""

        start_time = time.time()
        self.logger.log_service_call("start_chat_session", user_id)

        try:
            # Load user context
            user_context = await self._load_user_context(user_id)

            # Initialize conversation state
            self.conversation_states[user_id] = {
                "session_start": datetime.now(timezone.utc),
                "message_count": 0,
                "current_topic": None,
                "conversation_energy": 0.5,
                "last_insight": None
            }

            # Generate welcome message based on user profile
            welcome_message = await self._generate_welcome_message(user_context)

            # Convert Markdown to HTML for Telegram
            welcome_message_html = self._markdown_to_html(welcome_message)

            # Log chat message
            await self.user_dao.save_chat_message(
                user_id, welcome_message_html, "assistant",
                ai_model_used="personalized_template",
                response_time=time.time() - start_time
            )

            processing_time = time.time() - start_time
            self.logger.log_service_result("start_chat_session", True, processing_time)

            return ChatResponse(
                success=True,
                message="Chat session started",
                response_text=welcome_message_html,
                ai_model_used="personalized_template",
                processing_time=processing_time
            )

        except Exception as e:
            self.logger.log_error("CHAT_START_ERROR", f"Failed to start chat: {e}", user_id, e)
            return ChatResponse(
                success=False,
                message=f"Failed to start chat: {str(e)}"
            )

    async def process_message(self, user_id: str, message: str) -> ChatResponse:
        """Process user message and generate personalized response"""

        start_time = time.time()
        self.logger.log_service_call("process_message", user_id, message_length=len(message))

        try:
            # Load user context
            user_context = await self._load_user_context(user_id)

            # Save user message
            user_msg_id = await self.user_dao.save_chat_message(
                user_id, message, "user"
            )

            # Analyze message for insights
            insights_detected = await self._analyze_message_for_insights(message, user_context)

            # Detect message type and intent
            message_analysis = await self._analyze_message_intent(message, user_context)

            # 🔥 NEW: Enhanced AI Router with psychological context
            message_context = {
                'message': message,
                'crisis_detected': any(word in message.lower() for word in ['кризис', 'суицид', 'не хочу жить']),
                'existential_question': any(word in message.lower() for word in ['смысл жизни', 'зачем', 'кто я']),
                'depth_level': 'SHADOW' if len(message) > 200 else 'CONSCIOUS',
                'breakthrough_magnitude': 0.0,
                'needs_action_plan': message_analysis.get('intent') == 'advice_request',
                'emotional_support_needed': message_analysis.get('intent') == 'emotional_sharing'
            }

            # Route to optimal AI model
            recommended_model = self.enhanced_router.route(message_context)
            self.logger.info(f"🤖 Enhanced Router selected: {recommended_model}")

            # 🔥 NEW: Semantic search for similar emotional states (~200ms embedding + < 20ms search)
            similar_states = []
            trajectory_insights = None

            if user_context.personality_profile:
                # 🔥 QUICK FIX: Disable broken semantic search (embedding space mismatch)
                # ROOT CAUSE: Comparing personality narrative embeddings vs user message embeddings
                # TODO: Create chat_messages collection with message embeddings (see AI Engineer analysis)
                similar_states = []
                self.logger.warning(f"⚠️ Semantic search DISABLED (embedding space mismatch - personality narratives vs user messages)")

                # 3. Analyze personality trajectory for storytelling (< 30ms)
                trajectory_insights = await self.coach_vector_dao.analyze_personality_trajectory(
                    int(user_id),
                    window=20
                )
                
                if trajectory_insights:
                    # 🔥 TRACK 3: Add evolution points for storytelling
                    evolution_points = await self.coach_vector_dao.get_personality_trajectory(
                        int(user_id),
                        limit=132  # Full personality evolution history
                    )
                    trajectory_insights['evolution_points'] = evolution_points
                    
                    self.logger.info(
                        f"📈 Trajectory: {len(trajectory_insights.get('insights', []))} insights, "
                        f"{len(evolution_points)} evolution points"
                    )

            # Generate personalized response (теперь с контекстом similar_states + trajectory)
            response_text = await self._generate_personalized_response(
                user_id, message, user_context, message_analysis, similar_states, trajectory_insights
            )

            # 🔥 NEW: Generate deep follow-up questions (Phase 2-3)
            user_context_dict = {
                'big_five': user_context.personality_profile.get('traits', {}).get('big_five', {}) if user_context.personality_profile else {},
                'conversation_stage': user_context.conversation_stage,
                'current_mood': user_context.current_mood,
                'personality_profile': user_context.personality_profile
            }

            message_ctx = {
                'intent': message_analysis.get('intent'),
                'domain': message_analysis.get('domain', 'general'),
                'emotional_intensity': message_analysis.get('emotional_intensity', 'medium'),
                'insights_detected': len(insights_detected) > 0,
                'goal_related': message_analysis.get('intent') == 'advice_request'
            }

            deep_questions = self.question_generator.generate_questions(
                user_context=user_context_dict,
                message_context=message_ctx,
                count=2
            )

            if deep_questions:
                # Add questions to response
                questions_text = "\n\n🤔 **Давайте углубимся:**\n" + "\n".join(f"• {q}" for q in deep_questions)
            else:
                questions_text = ""

            self.logger.info(f"💭 Generated {len(deep_questions)} deep questions")

            # 🔥 NEW: Apply Micro Interventions to final response (Phase 2-3)
            intervention_context = {
                'negative_belief_detected': any(word in message.lower() for word in ['не могу', 'невозможно', 'не получится']),
                'negative_statement': message[:100] if any(word in message.lower() for word in ['не могу', 'невозможно']) else '',
                'positive_state_detected': any(word in message.lower() for word in ['получилось', 'удалось', 'смог']),
                'positive_state': 'успех' if 'получилось' in message.lower() else '',
                'comfort_zone_detected': message_analysis.get('intent') == 'progress_sharing'
            }

            final_response_with_interventions = self.micro_interventions.inject(
                response_text + questions_text,
                intervention_context
            )

            # Convert Markdown to HTML for Telegram
            final_response_html = self._markdown_to_html(final_response_with_interventions)

            # 🔥 TRACK 3: Store insights with confidence scores
            if insights_detected:
                for insight in insights_detected:
                    # Calculate confidence for insight
                    confidence, explanation = self.confidence_calc.calculate(
                        insight=insight,
                        user_context=user_context.__dict__
                    )
                    
                    insight['confidence'] = confidence
                    insight['confidence_explanation'] = explanation
                    
                    # Format insight with confidence
                    formatted_insight = self.confidence_calc.format_with_confidence(
                        insight["text"],
                        confidence,
                        explanation
                    )
                    
                    self.logger.info(f"💡 Insight confidence: {confidence:.2f} - {insight['type']}")
                    
                    await self.user_dao.save_user_insight(
                        user_id, formatted_insight, insight["type"],
                        insight.get("domain"), confidence
                    )

            # Update personality profile if significant markers detected
            personality_updates = await self._extract_personality_updates(message, user_context)
            if personality_updates:
                # This could trigger vector updates
                pass

            # 🔥 NEW: Save AI response with Enhanced Router's model selection + deep questions metadata
            ai_msg_id = await self.user_dao.save_chat_message(
                user_id, final_response_html, "assistant",
                ai_model_used=recommended_model,
                insights={"detected_insights": len(insights_detected), "deep_questions": len(deep_questions)},
                response_time=time.time() - start_time
            )

            # Update conversation state
            if user_id in self.conversation_states:
                self.conversation_states[user_id]["message_count"] += 1
                self.conversation_states[user_id]["last_interaction"] = datetime.now(timezone.utc)

                if insights_detected:
                    self.conversation_states[user_id]["last_insight"] = insights_detected[0]

            processing_time = time.time() - start_time
            self.logger.log_service_result("process_message", True, processing_time,
                                         insights_count=len(insights_detected))

            return ChatResponse(
                success=True,
                message="Message processed successfully",
                response_text=final_response_html,
                ai_model_used=recommended_model,
                processing_time=processing_time,
                insights_detected=[i["text"] for i in insights_detected],
                personality_updates=personality_updates
            )

        except Exception as e:
            self.logger.log_error("MESSAGE_PROCESSING_ERROR",
                                 f"Failed to process message: {e}", user_id, e)
            return ChatResponse(
                success=False,
                message=f"Failed to process message: {str(e)}"
            )

    async def get_conversation_history(self, user_id: str, limit: int = 20) -> ChatResponse:
        """Get conversation history for user"""

        self.logger.log_service_call("get_conversation_history", user_id, limit=limit)

        try:
            messages = await self.user_dao.get_recent_chat_history(user_id, limit)

            # Format messages for display
            formatted_history = []
            for msg in messages:
                formatted_history.append({
                    "timestamp": msg["timestamp"].isoformat(),
                    "type": msg["message_type"],
                    "content": msg["content"][:200] + "..." if len(msg["content"]) > 200 else msg["content"],
                    "ai_model": msg.get("ai_model_used")
                })

            self.logger.log_service_result("get_conversation_history", True)

            return ChatResponse(
                success=True,
                message="History retrieved",
                response_text=json.dumps(formatted_history, ensure_ascii=False)
            )

        except Exception as e:
            self.logger.log_error("HISTORY_RETRIEVAL_ERROR",
                                 f"Failed to get history: {e}", user_id, e)
            return ChatResponse(
                success=False,
                message=f"Failed to get history: {str(e)}"
            )

    async def _load_user_context(self, user_id: str) -> UserContext:
        """Load comprehensive user context for personalization

        🔥 NEW: Uses Qdrant for fast semantic search (< 20ms)
        """

        # Get user profile with personality data
        user_profile = await self.user_dao.get_user_profile(user_id)

        # Get recent conversation history
        recent_messages = await self.user_dao.get_recent_chat_history(user_id, self.context_window)

        # Get user insights
        insights_history = await self.user_dao.get_user_insights(user_id, 10)

        # ⚡ NEW: Get personality vector from QDRANT (< 10ms)
        personality_vector = await self.coach_vector_dao.get_current_personality_vector(int(user_id))

        if personality_vector:
            self.logger.info(f"✅ Loaded personality vector from Qdrant for user {user_id}")
        else:
            self.logger.warning(f"⚠️ No personality vector in Qdrant for user {user_id}")

        # 🔥 NEW: Get onboarding answers (work, goals, challenges, etc.)
        onboarding_answers = await self.user_dao.get_onboarding_answers(user_id, limit=30)
        if onboarding_answers:
            self.logger.info(f"✅ Loaded {len(onboarding_answers)} onboarding answers for user {user_id}")
        else:
            self.logger.info(f"ℹ️ No onboarding answers found for user {user_id}")

        # 🔥 NEW: Get context stories (специальные вопросы: дилеммы, цели, контекст)
        context_stories = await self.user_dao.get_context_stories(user_id, limit=10)
        if context_stories:
            self.logger.info(f"✅ Loaded {len(context_stories)} context stories for user {user_id}")
        else:
            self.logger.info(f"ℹ️ No context stories found for user {user_id}")

        # Analyze current mood from recent messages
        current_mood = self._analyze_current_mood(recent_messages)

        # Determine conversation stage
        conversation_stage = self._determine_conversation_stage(user_profile, recent_messages)

        return UserContext(
            user_id=user_id,
            personality_profile=personality_vector,
            recent_messages=recent_messages,
            insights_history=insights_history,
            assessment_data=user_profile.get("assessment_stats") if user_profile else None,
            onboarding_answers=onboarding_answers,
            context_stories=context_stories,
            current_mood=current_mood,
            conversation_stage=conversation_stage
        )

    async def _generate_welcome_message(self, user_context: UserContext) -> str:
        """Generate personalized welcome message"""

        user_profile = user_context.personality_profile
        assessment_complete = user_context.assessment_data and user_context.assessment_data.get("total_answers", 0) > 10

        # Personalize based on personality if available
        if user_profile and user_profile.get("traits"):
            # ⚡ NEW: Qdrant structure has "big_five" instead of "personality"
            personality = user_profile["traits"].get("big_five", {})

            # High extraversion - energetic greeting
            if personality.get("extraversion", 0) > 0.7:
                base_greeting = "Привет! Рад нашему общению! Готов поделиться тем, что вас вдохновляет?"

            # High openness - creative greeting
            elif personality.get("openness", 0) > 0.7:
                base_greeting = "Добро пожаловать! Всегда интересно исследовать новые идеи вместе. О чем думаете?"

            # High conscientiousness - structured greeting
            elif personality.get("conscientiousness", 0) > 0.7:
                base_greeting = "Здравствуйте! Готов помочь структурировать ваши мысли и найти решения."

            # Default
            else:
                base_greeting = "Привет! Готов выслушать и поддержать. Что у вас на душе?"

        else:
            base_greeting = "Добро пожаловать! Я ваш AI-коуч. Чем могу помочь сегодня?"

        # Add context based on assessment status
        if assessment_complete:
            context_addition = "\n\nНа основе вашего психологического профиля могу дать персонализированные советы."
        else:
            context_addition = "\n\nРекомендую пройти психологическое анкетирование для более точных советов."

        return base_greeting + context_addition

    async def _analyze_message_for_insights(self, message: str,
                                          user_context: UserContext) -> List[Dict[str, Any]]:
        """Analyze message for psychological insights"""

        insights = []
        message_lower = message.lower()

        # Insight patterns
        insight_patterns = [
            ("я понял", "realization"),
            ("оказывается", "discovery"),
            ("понимаю что", "understanding"),
            ("осознаю", "awareness"),
            ("получается", "conclusion")
        ]

        for pattern, insight_type in insight_patterns:
            if pattern in message_lower:
                # Extract the insight context
                pattern_index = message_lower.find(pattern)
                insight_context = message[max(0, pattern_index-20):pattern_index+100]

                insights.append({
                    "text": insight_context.strip(),
                    "type": f"spontaneous_{insight_type}",
                    "confidence": 0.7,
                    "domain": self._detect_psychological_domain(insight_context)
                })

        # Emotional state insights
        if any(word in message_lower for word in ["чувствую себя", "мое состояние", "я в"]):
            emotional_insight = self._extract_emotional_insight(message)
            if emotional_insight:
                insights.append(emotional_insight)

        # Goal-related insights
        if any(word in message_lower for word in ["хочу", "планирую", "мечтаю", "стремлюсь"]):
            goal_insight = self._extract_goal_insight(message)
            if goal_insight:
                insights.append(goal_insight)

        return insights

    async def _analyze_message_intent(self, message: str,
                                    user_context: UserContext) -> Dict[str, Any]:
        """Analyze message intent and determine response strategy"""

        message_lower = message.lower()

        # Question patterns
        if any(marker in message_lower for marker in ["как", "что делать", "помоги", "совет", "?"]):
            return {
                "intent": "advice_request",
                "urgency": "high" if any(word in message_lower for word in ["срочно", "помогите", "не знаю что делать"]) else "normal",
                "domain": self._detect_psychological_domain(message),
                "recommended_model": "gpt-4o"  # More sophisticated for advice
            }

        # Emotional sharing
        if any(marker in message_lower for marker in ["чувствую", "переживаю", "болит", "трудно"]):
            return {
                "intent": "emotional_sharing",
                "emotional_intensity": self._assess_emotional_intensity(message),
                "support_needed": True,
                "recommended_model": "gpt-4o-mini"
            }

        # Progress sharing
        if any(marker in message_lower for marker in ["получилось", "сделал", "удалось", "достиг"]):
            return {
                "intent": "progress_sharing",
                "celebration_appropriate": True,
                "recommended_model": "gpt-4o-mini"
            }

        # General conversation
        return {
            "intent": "general_conversation",
            "recommended_model": "gpt-4o-mini"
        }

    async def _generate_personalized_response(
        self,
        user_id: str,
        message: str,
        user_context: UserContext,
        message_analysis: Dict[str, Any],
        similar_states: List[Dict[str, Any]] = None,
        trajectory_insights: Dict[str, Any] = None
    ) -> str:
        """Generate personalized response based on user's personality and context

        🔥 NEW: Uses similar_states from Qdrant + trajectory insights for deeply personalized responses
        """

        intent = message_analysis.get("intent", "general_conversation")
        # ⚡ NEW: Qdrant structure has "big_five" instead of "personality"
        personality = user_context.personality_profile.get("traits", {}).get("big_five", {}) if user_context.personality_profile else {}

        # 🔥 HYBRID CONTEXT: Build enriched context from multiple sources
        context_enrichment = ""

        # 1. Recent conversation topics (НОВОЕ - заменяет broken semantic search)
        recent_topics = self._extract_recent_topics_from_context(user_context)
        if recent_topics:
            context_enrichment += f"\n\n🗨️ _Недавно обсуждали: {', '.join(recent_topics)}_"
            self.logger.info(f"💬 Added recent topics: {recent_topics}")

        # 2. Work/business context from onboarding (НОВОЕ - используем 84 ответа!)
        if intent == "advice_request" and message_analysis.get("domain") == "work":
            work_background = self._extract_work_background_from_onboarding(user_context)
            if work_background:
                context_enrichment += f"\n\n💼 _Ваш контекст: {work_background}_"
                self.logger.info(f"💼 Added work background from onboarding")

        # 3. Personality trajectory insights (уже работает)
        if trajectory_insights and trajectory_insights.get("insights"):
            # Add most relevant insight (first one is usually most significant)
            top_insight = trajectory_insights["insights"][0]
            context_enrichment += f"\n\n📈 _{top_insight}_"

        # 🔥 TRACK 3: Add personality journey narrative (ТОЛЬКО для релевантных вопросов)
        if user_context.personality_profile and trajectory_insights:
            evolution_points = trajectory_insights.get('evolution_points', [])

            # 🔥 FIX: Проверяем релевантность storytelling для текущего вопроса
            intent = message_analysis.get("intent", "general_conversation")
            domain = message_analysis.get("domain", "general")

            # Storytelling релевантен ТОЛЬКО для:
            # 1. Эмоциональных вопросов
            # 2. Вопросов про self-identity
            # 3. Вопросов про прогресс/изменения
            is_emotional_context = (
                intent == "emotional_sharing" or
                domain == "emotions" or
                any(keyword in message.lower() for keyword in [
                    "кто я", "что со мной", "как я изменился",
                    "мой путь", "моя история", "чувствую себя"
                ])
            )

            # Для бизнес-вопросов и advice_request - НЕ показываем историю
            is_action_oriented = (
                intent == "advice_request" or
                domain in ["work", "future"] or
                any(keyword in message.lower() for keyword in [
                    "что делать", "как решить", "помоги выбрать",
                    "направление", "бизнес", "проект", "блог"
                ])
            )

            if is_emotional_context and not is_action_oriented and len(evolution_points) >= 3:
                narrative = await self.storyteller.create_narrative(
                    user_id=int(user_id),
                    evolution_points=evolution_points
                )

                if narrative:
                    context_enrichment += f"\n\n{narrative}"
                    self.logger.info(f"📖 Added personality journey narrative ({len(narrative)} chars)")
            else:
                self.logger.info(f"📖 Skipped storytelling (not relevant for {intent}/{domain})")

        # 🔥 NEW: Call REAL AI instead of templates!
        try:
            # 1. Build system prompt with personality context
            system_prompt = self._build_ai_system_prompt(user_context, intent, context_enrichment)

            # 2. Build conversation messages
            messages = self._build_conversation_messages(user_context, message)

            # 3. Map Enhanced Router's model selection to AIModel enum
            recommended_model_str = self.enhanced_router.route({
                'message': message,
                'needs_action_plan': intent == 'advice_request',
                'emotional_support_needed': intent == 'emotional_sharing'
            })

            model_mapping = {
                'claude-3-5-sonnet': AIModel.CLAUDE_SONNET,
                'gpt-4o': AIModel.GPT_4,
                'gpt-4o-mini': AIModel.GPT_4O_MINI
            }
            ai_model = model_mapping.get(recommended_model_str, AIModel.GPT_4O_MINI)

            # 4. REAL AI CALL - This is where the magic happens!
            self.logger.info(f"🤖 Calling AI with model: {ai_model.value}")
            ai_response = await self.ai_client.generate_response(
                model=ai_model,
                messages=messages,
                system_prompt=system_prompt,
                max_tokens=1500,  # Enough for deep, detailed responses
                temperature=0.7   # Balanced creativity
            )

            self.logger.info(f"✅ AI response generated: {len(ai_response)} chars")

            # 5. Add context enrichment to AI response
            final_response = ai_response
            if context_enrichment:
                final_response += context_enrichment

            return final_response

        except Exception as e:
            self.logger.error(f"❌ AI call failed: {e}")
            # Fallback to simple template if AI fails
            return f"💙 Понимаю ваш вопрос. К сожалению, сейчас возникла техническая сложность. Попробуйте переформулировать, пожалуйста.{context_enrichment}"

    def _extract_user_interests(self, user_context: UserContext) -> List[Dict[str, str]]:
        """
        Извлекает интересы/экспертизу пользователя из onboarding answers

        Returns:
            List[{direction: str, why: str}] - направления с обоснованием
        """
        interests = []

        if not user_context.onboarding_answers:
            return interests

        # Анализируем psychological_insights для выявления паттернов
        for answer in user_context.onboarding_answers:
            insights = answer.get('psychological_insights', '')

            if insights and isinstance(insights, str):
                insights_lower = insights.lower()

                # Ищем темы/интересы в инсайтах
                if any(keyword in insights_lower for keyword in ['творчество', 'креатив', 'создавать', 'дизайн']):
                    interests.append({
                        'direction': 'Творческий контент (дизайн, искусство, креатив)',
                        'why': 'вижу ваш творческий потенциал в ответах'
                    })

                if any(keyword in insights_lower for keyword in ['помощь', 'люди', 'поддержка', 'консультир', 'коуч']):
                    interests.append({
                        'direction': 'Помогающий контент (коучинг, советы, наставничество)',
                        'why': 'заметна ваша готовность помогать другим'
                    })

                if any(keyword in insights_lower for keyword in ['аналитика', 'изучать', 'понимать', 'анализ', 'исследова']):
                    interests.append({
                        'direction': 'Аналитический контент (исследования, обзоры, аналитика)',
                        'why': 'видна ваша склонность к глубокому анализу'
                    })

                if any(keyword in insights_lower for keyword in ['бизнес', 'предприним', 'стратег', 'развитие']):
                    interests.append({
                        'direction': 'Бизнес-контент (стратегии, кейсы, развитие)',
                        'why': 'заметен ваш интерес к бизнесу и росту'
                    })

                if any(keyword in insights_lower for keyword in ['техно', 'it', 'программ', 'код']):
                    interests.append({
                        'direction': 'Технический контент (IT, программирование, инновации)',
                        'why': 'видна ваша техническая экспертиза'
                    })

        # Убираем дубликаты
        unique_interests = []
        seen = set()
        for interest in interests:
            if interest['direction'] not in seen:
                unique_interests.append(interest)
                seen.add(interest['direction'])

        return unique_interests[:5]  # Максимум 5 направлений

    def _generate_advice_response(self, message: str, personality: Dict[str, float],
                                user_context: UserContext, analysis: Dict[str, Any]) -> str:
        """Generate advice response adapted to personality"""

        domain = analysis.get("domain", "general")

        # 🔥 FIX: Извлекаем профессию из psychological_insights, НЕ из случайных raw_answer
        user_context_info = ""
        if user_context.onboarding_answers:
            # Ищем КОНКРЕТНЫЕ инсайты про работу/профессию/карьеру
            work_insights = []

            for answer in user_context.onboarding_answers:
                insights = answer.get('psychological_insights')

                # Проверяем есть ли в инсайтах информация про работу
                if insights and isinstance(insights, str):
                    insights_lower = insights.lower()
                    # Ищем ключевые слова про РАБОТУ (не здоровье, не эмоции)
                    if any(keyword in insights_lower for keyword in [
                        'работа', 'профессия', 'карьера', 'специалист по',
                        'должность', 'занимается', 'трудится', 'работает как'
                    ]):
                        # Дополнительная проверка: НЕ про здоровье/специалистов
                        if not any(health_word in insights_lower for health_word in [
                            'здоровье', 'лечение', 'врач', 'тренер для', 'специалист для'
                        ]):
                            work_insights.append(insights)

            # Если нашли инсайты про работу - используем их
            if work_insights:
                # Берем самый релевантный (первый найденный)
                work_context = work_insights[0]
                # Извлекаем суть (первые 80 символов)
                if len(work_context) > 80:
                    work_context = work_context[:80] + "..."
                user_context_info = f"\n\n_На основе ваших ответов вижу: {work_context}_"
                self.logger.info(f"💼 Using work context from insights: {work_context[:50]}...")
            # Если нет инсайтов про работу - НЕ придумываем профессию
            else:
                self.logger.info(f"💼 No work context found in onboarding answers, skipping context_info")

        # Base advice structure
        response = f"🎯 **Понял вашу ситуацию.**{user_context_info}\n\n"

        # Personality-adapted advice style
        if personality.get("conscientiousness", 0) > 0.7:
            # Structured, step-by-step advice
            response += "**Рекомендую структурированный подход:**\n"
            response += "1. Проанализируйте текущую ситуацию\n"
            response += "2. Определите конкретные шаги действий\n"
            response += "3. Установите реалистичные сроки\n\n"

        elif personality.get("openness", 0) > 0.7:
            # Creative, exploratory advice
            response += "**Попробуйте творческий подход:**\n"
            response += "• Рассмотрите нестандартные варианты решения\n"
            response += "• Подумайте о новых возможностях в ситуации\n"
            response += "• Экспериментируйте с разными подходами\n\n"

        else:
            # 🔥 FIX #5: Для бизнес-вопросов - конкретные рекомендации на основе интересов
            message_lower = message.lower()
            is_business_question = (
                domain == "work" and
                any(keyword in message_lower for keyword in [
                    'блог', 'контент', 'направление', 'что постить',
                    'бизнес', 'проект', 'развитие', 'стратегия'
                ])
            )

            if is_business_question:
                # Извлекаем интересы пользователя
                interests = self._extract_user_interests(user_context)

                if interests:
                    response += "**На основе вашего профиля вижу несколько направлений:**\n\n"
                    for interest in interests:
                        response += f"• **{interest['direction']}**  \n  _{interest['why']}_\n\n"
                    response += "**Мой совет:** попробуйте комбинировать 2-3 направления для уникальности.\n\n"
                    self.logger.info(f"💡 Generated {len(interests)} concrete recommendations for business question")
                else:
                    # Fallback если интересы не найдены
                    response += "**Мой совет:**\n"
                    response += "Разложите ситуацию на части и определите, что можете контролировать.\n\n"
            else:
                # Balanced advice для остальных вопросов
                response += "**Мой совет:**\n"
                response += "Разложите ситуацию на части и определите, что можете контролировать.\n\n"

        # Add domain-specific advice
        if domain == "relationships":
            response += "💙 **Помните:** открытая коммуникация - основа крепких отношений."
        elif domain == "work":
            response += "🚀 **Важно:** выбирайте цели, которые соответствуют вашим ценностям."
        elif domain == "emotions":
            response += "🌱 **Поддержка:** ваши эмоции - ценная информация о потребностях."

        response += "\n\nГотов обсудить детали! Что вас больше всего беспокоит в этой ситуации?"

        return response

    def _generate_supportive_response(self, message: str, personality: Dict[str, float],
                                    user_context: UserContext, analysis: Dict[str, Any]) -> str:
        """Generate supportive response for emotional sharing"""

        emotional_intensity = analysis.get("emotional_intensity", "medium")

        if emotional_intensity == "high":
            response = "💙 **Понимаю, что вам сейчас очень тяжело.**\n\n"
            response += "Спасибо за доверие. Поделиться сложными чувствами - это уже шаг к их пониманию.\n\n"
        else:
            response = "🤗 **Слышу вас.**\n\n"
            response += "Важно признавать свои чувства и давать им место.\n\n"

        # Personality-adapted support
        if personality.get("agreeableness", 0) > 0.6:
            # They value harmony and relationships
            response += "**💚 Помните:**\n"
            response += "• Вы не одиноки в своих переживаниях\n"
            response += "• Поддержка близких может быть очень ценной\n"
            response += "• Забота о себе - не эгоизм\n\n"

        elif personality.get("conscientiousness", 0) > 0.6:
            # They prefer practical solutions
            response += "**🎯 Что может помочь:**\n"
            response += "• Создайте план самоподдержки\n"
            response += "• Определите конкретные шаги для улучшения ситуации\n"
            response += "• Отслеживайте прогресс в преодолении трудностей\n\n"

        else:
            response += "**🌟 Напоминание:**\n"
            response += "Это временное состояние. Вы справитесь.\n\n"

        response += "Хотите рассказать больше? Я здесь, чтобы выслушать и поддержать. 💚"

        return response

    def _generate_celebratory_response(self, message: str, personality: Dict[str, float],
                                     user_context: UserContext) -> str:
        """Generate celebratory response for progress sharing"""

        if personality.get("extraversion", 0) > 0.7:
            # Enthusiastic celebration
            response = "🎉 **Вау, это потрясающе!**\n\n"
            response += "Ваш прогресс впечатляет! Отличная работа! 🚀\n\n"
        else:
            # Warm but measured celebration
            response = "✨ **Поздравляю с достижением!**\n\n"
            response += "Это действительно значимый прогресс. 👏\n\n"

        response += "**🎯 Что это означает:**\n"
        response += "• Вы движетесь в правильном направлении\n"
        response += "• Ваши усилия приносят результат\n"
        response += "• У вас есть сила менять свою жизнь\n\n"

        response += "Какие следующие шаги планируете? Готов поддержать! 💪"

        return response

    def _generate_conversational_response(self, message: str, personality: Dict[str, float],
                                        user_context: UserContext) -> str:
        """Generate general conversational response"""

        response = "💭 **Интересно!**\n\n"

        # Reference their message
        if len(message) > 50:
            response += f"Вы поделились важными мыслями о: \"{message[:80]}...\"\n\n"

        # Personality-adapted continuation
        if personality.get("openness", 0) > 0.7:
            response += "Мне нравится ваш подход к размышлениям. Какие новые идеи приходят в голову?\n\n"
        elif personality.get("conscientiousness", 0) > 0.7:
            response += "Похоже, вы тщательно обдумываете ситуацию. Какие конкретные аспекты важнее всего?\n\n"
        else:
            response += "Расскажите больше - что вас больше всего волнует в этой теме?\n\n"

        response += "Продолжайте делиться мыслями! 💬"

        return response

    def _analyze_current_mood(self, recent_messages: List[Dict[str, Any]]) -> str:
        """Analyze current mood from recent messages"""

        if not recent_messages:
            return "neutral"

        # Simple sentiment analysis of recent user messages
        user_messages = [msg for msg in recent_messages[-5:] if msg["message_type"] == "user"]

        if not user_messages:
            return "neutral"

        # Count emotional words
        positive_count = 0
        negative_count = 0

        for msg in user_messages:
            content = msg["content"].lower()

            positive_words = ["хорошо", "отлично", "рад", "счастлив", "вдохновляет"]
            negative_words = ["плохо", "грустно", "тяжело", "проблема", "болит"]

            positive_count += sum(1 for word in positive_words if word in content)
            negative_count += sum(1 for word in negative_words if word in content)

        if negative_count > positive_count:
            return "negative"
        elif positive_count > negative_count:
            return "positive"
        else:
            return "neutral"

    def _determine_conversation_stage(self, user_profile: Optional[Dict],
                                    recent_messages: List[Dict[str, Any]]) -> str:
        """Determine what stage of conversation we're in"""

        if not user_profile:
            return "initial"

        total_messages = user_profile.get("chat_stats", {}).get("total_messages", 0) if user_profile else 0
        assessment_complete = user_profile.get("user", {}).get("onboarding_completed", False) if user_profile else False

        if total_messages < 5:
            return "getting_acquainted"
        elif not assessment_complete:
            return "pre_assessment"
        elif total_messages < 50:
            return "building_rapport"
        else:
            return "deep_coaching"

    def _detect_psychological_domain(self, text: str) -> str:
        """Detect psychological domain from text content"""

        text_lower = text.lower()

        if any(word in text_lower for word in ["отношения", "люди", "семья", "друзья", "партнер"]):
            return "relationships"
        elif any(word in text_lower for word in ["работа", "карьера", "бизнес", "коллеги"]):
            return "work"
        elif any(word in text_lower for word in ["чувствую", "эмоции", "настроение", "переживаю"]):
            return "emotions"
        elif any(word in text_lower for word in ["цель", "мечта", "планы", "будущее"]):
            return "future"
        elif any(word in text_lower for word in ["здоровье", "тело", "самочувствие"]):
            return "health"
        else:
            return "general"

    def _assess_emotional_intensity(self, message: str) -> str:
        """Assess emotional intensity of message"""

        message_lower = message.lower()

        high_intensity_markers = ["очень", "крайне", "невыносимо", "ужасно", "прекрасно", "восхитительно"]
        medium_intensity_markers = ["довольно", "достаточно", "вполне"]

        if any(marker in message_lower for marker in high_intensity_markers):
            return "high"
        elif any(marker in message_lower for marker in medium_intensity_markers):
            return "medium"
        else:
            return "low"

    def _extract_emotional_insight(self, message: str) -> Optional[Dict[str, Any]]:
        """Extract emotional state insights from message"""

        # Simple pattern matching for emotional insights
        message_lower = message.lower()

        if "чувствую себя" in message_lower:
            # Extract what follows "чувствую себя"
            start_idx = message_lower.find("чувствую себя") + len("чувствую себя")
            emotional_state = message[start_idx:start_idx+50].strip()

            return {
                "text": f"Текущее эмоциональное состояние: {emotional_state}",
                "type": "emotional_state",
                "domain": "emotions",
                "confidence": 0.8
            }

        return None

    def _extract_goal_insight(self, message: str) -> Optional[Dict[str, Any]]:
        """Extract goal-related insights from message"""

        message_lower = message.lower()
        goal_verbs = ["хочу", "планирую", "мечтаю", "стремлюсь", "собираюсь"]

        for verb in goal_verbs:
            if verb in message_lower:
                start_idx = message_lower.find(verb)
                goal_description = message[start_idx:start_idx+100].strip()

                return {
                    "text": f"Выраженная цель/желание: {goal_description}",
                    "type": "goal_expression",
                    "domain": "future",
                    "confidence": 0.7
                }

        return None

    async def _extract_personality_updates(self, message: str,
                                         user_context: UserContext) -> Optional[Dict[str, float]]:
        """Extract personality updates from message content"""

        updates = {}
        message_lower = message.lower()

        # Openness indicators
        if any(word in message_lower for word in ["новое", "творчество", "идея", "эксперимент"]):
            updates["openness"] = 0.05

        # Conscientiousness indicators
        if any(word in message_lower for word in ["план", "организация", "дисциплина", "цель"]):
            updates["conscientiousness"] = 0.05

        # Extraversion indicators
        if any(word in message_lower for word in ["люди", "компания", "общение", "вечеринка"]):
            updates["extraversion"] = 0.05

        # Agreeableness indicators
        if any(word in message_lower for word in ["помощь", "доброта", "сотрудничество"]):
            updates["agreeableness"] = 0.05

        return updates if updates else None

    def _initialize_response_templates(self) -> Dict[str, Dict[str, str]]:
        """Initialize response templates for different personality types"""

        return {
            "advice_request": {
                "high_conscientiousness": "Рекомендую составить четкий план действий...",
                "high_openness": "Попробуйте творческий подход к решению...",
                "high_extraversion": "Обсудите это с близкими людьми...",
                "default": "Давайте разберем ситуацию по частям..."
            },
            "emotional_support": {
                "high_agreeableness": "Понимаю ваши чувства, это нормально...",
                "high_neuroticism": "Важно заботиться о своем эмоциональном состоянии...",
                "default": "Спасибо за доверие. Давайте найдем способы поддержки..."
            }
        }

    def _extract_recent_topics_from_context(self, user_context: UserContext) -> List[str]:
        """
        Извлекает темы разговора из недавней истории чата

        🔥 FIX: Заменяет broken semantic search - использует прямой анализ сообщений
        """
        topics = []

        if not user_context.recent_messages:
            return topics

        # Анализируем последние 10 сообщений на ключевые слова
        for msg in user_context.recent_messages[-10:]:
            content = msg.get('content', '').lower()

            # Бизнес/работа
            if any(kw in content for kw in ['блог', 'бизнес', 'проект', 'контент', 'стратегия', 'клиент']):
                topics.append('блог и бизнес-стратегия')

            # Отношения
            if any(kw in content for kw in ['отношения', 'партнер', 'семья', 'друзья', 'любовь']):
                topics.append('отношения и близость')

            # Самопознание
            if any(kw in content for kw in ['понять себя', 'кто я', 'ценности', 'цели', 'мечты']):
                topics.append('самопознание и идентичность')

            # Эмоции
            if any(kw in content for kw in ['чувствую', 'тревожно', 'страх', 'радость', 'грусть']):
                topics.append('эмоциональное состояние')

            # Развитие
            if any(kw in content for kw in ['развитие', 'рост', 'навыки', 'обучение', 'изменения']):
                topics.append('личностный рост')

        # Оставляем уникальные, максимум 3 темы
        unique_topics = list(dict.fromkeys(topics))[:3]
        return unique_topics

    def _extract_work_background_from_onboarding(self, user_context: UserContext) -> Optional[str]:
        """
        Извлекает контекст работы/бизнеса из ответов онбординга

        🔥 FIX: Использует 84 onboarding answers напрямую из psychological_insights
        """
        if not user_context.onboarding_answers:
            return None

        work_contexts = []

        for answer in user_context.onboarding_answers:
            insights = answer.get('psychological_insights', '')

            if isinstance(insights, str):
                insights_lower = insights.lower()

                # Ищем упоминания работы, бизнеса, проектов
                if any(kw in insights_lower for kw in ['работа', 'бизнес', 'проект', 'профессия', 'карьера', 'клиент', 'стратегия', 'блог']):
                    # Берем первые 200 символов для контекста
                    work_contexts.append(insights[:200])

        # Возвращаем самый релевантный контекст (первый найденный)
        if work_contexts:
            self.logger.info(f"💼 Found work context from onboarding: {len(work_contexts[0])} chars")
            return work_contexts[0]

        return None

    def _build_ai_system_prompt(self, user_context: UserContext, intent: str, context_enrichment: str) -> str:
        """
        Строит system prompt для AI на основе контекста пользователя

        🔥 NEW: Создает глубокий, персонализированный промпт с учетом личности
        """
        personality = user_context.personality_profile.get("traits", {}).get("big_five", {}) if user_context.personality_profile else {}

        # Описываем личностные черты
        traits_desc = []
        if personality:
            for trait, value in personality.items():
                if value > 0.7:
                    traits_desc.append(f"high {trait}")
                elif value < 0.3:
                    traits_desc.append(f"low {trait}")

        personality_context = f"User personality traits: {', '.join(traits_desc)}" if traits_desc else "New user, personality profile being built"

        # 🔥 NEW: Добавляем контекст из специальных вопросов (дилеммы, цели)
        context_stories_text = ""
        if user_context.context_stories:
            stories = [story.get('story_text', '') for story in user_context.context_stories[:3]]  # Top 3 most recent
            if stories:
                context_stories_text = "\n\nUser's current dilemmas and context:\n" + "\n".join([f"- {story}" for story in stories if story])

        # Адаптируем роль под тип запроса
        if intent == "advice_request":
            role_guidance = "Provide practical, actionable advice while considering their personality"
        elif intent == "emotional_sharing":
            role_guidance = "Offer empathetic support and emotional validation"
        elif intent == "progress_sharing":
            role_guidance = "Celebrate their achievements and encourage continued growth"
        else:
            role_guidance = "Engage in thoughtful, personalized conversation"

        prompt = f"""You are an empathetic AI psychology coach for Selfology.me platform.

USER CONTEXT:
{personality_context}{context_stories_text}
{context_enrichment if context_enrichment else "No additional context available yet"}

YOUR ROLE:
{role_guidance}

RESPONSE GUIDELINES:
- Length: 500-600 words (deep, thoughtful responses)
- Language: Russian (natural, conversational)
- Style: Warm but professional
- Personality adaptation: Reference their traits when relevant
- Include 1-2 thoughtful follow-up questions
- Balance emotional support with actionable insights
- Show genuine understanding of their situation

IMPORTANT:
- This is NOT a quick chatbot - take time to craft meaningful responses
- Reference their personality and context when relevant
- Ask questions that invite deeper self-reflection
- Avoid generic advice - make it personal to THEM"""

        return prompt

    def _build_conversation_messages(self, user_context: UserContext, current_message: str) -> List[Dict[str, str]]:
        """
        Строит историю разговора для контекста AI

        🔥 NEW: Включает последние 5 сообщений для continuity
        """
        messages = []

        # Добавляем недавнюю историю (последние 5 сообщений)
        if user_context.recent_messages:
            for msg in user_context.recent_messages[-5:]:
                role = "user" if msg.get("role") == "user" or msg.get("message_type") == "user" else "assistant"
                content = msg.get("content", "")

                # Обрезаем очень длинные сообщения
                if len(content) > 500:
                    content = content[:500] + "..."

                messages.append({
                    "role": role,
                    "content": content
                })

        # Добавляем текущее сообщение
        messages.append({
            "role": "user",
            "content": current_message
        })

        return messages
