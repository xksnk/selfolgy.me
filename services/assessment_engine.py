"""
Assessment Engine - Independent Q&A processing service
CRITICAL FIX: No session-based approach - tracks individual questions per user
"""
import sys
import time
import asyncio
import asyncpg
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timezone

# Add question core to path
sys.path.append(str(Path(__file__).parent.parent / "intelligent_question_core"))
from intelligent_question_core.api.core_api import SelfologyQuestionCore

from data_access.assessment_dao import AssessmentDAO
from data_access.user_dao import UserDAO
from core.config import get_config
from core.logging import assessment_logger, LoggerMixin


@dataclass
class AssessmentResult:
    """Result of assessment operation"""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    next_question: Optional[Dict[str, Any]] = None
    user_progress: Optional[Dict[str, Any]] = None


@dataclass
class QuestionAnalysis:
    """Analysis of user's answer to a question"""
    emotional_state: str
    openness_level: float
    depth_of_reflection: float
    vulnerability_shown: float
    resistance_detected: bool
    key_insights: List[str]
    energy_impact: float
    trust_building: float
    personality_markers: Dict[str, float]
    recommended_next_energy: str


class AssessmentEngine(LoggerMixin):
    """
    Independent Assessment Engine Service
    
    CRITICAL FIX: Eliminates session-based anti-pattern
    - Tracks completed questions per user (NOT sessions)
    - Each answer processed and stored immediately
    - Smart routing based on user history + current state
    - No session concept - pure user progress tracking
    - Never asks same question twice to same user
    """
    
    def __init__(self, db_pool: Optional[asyncpg.Pool] = None):
        self.config = get_config()
        self.db_pool = db_pool
        
        # Initialize question core
        self.question_core = SelfologyQuestionCore(self.config.question_core_path)
        
        # Initialize DAOs
        self.assessment_dao = AssessmentDAO(db_pool)
        self.user_dao = UserDAO(db_pool)
        
        # Configuration
        self.engine_config = self.config.get_service_config("assessment_engine")
        self.max_questions = self.engine_config.get("max_questions_per_session", 50)
        self.energy_threshold = self.engine_config.get("energy_safety_threshold", -1.5)
        self.healing_debt_limit = self.engine_config.get("healing_debt_limit", 1.0)
        
        # User state tracking (in production would use Redis)
        self.user_states = {}  # user_id -> current assessment state
        
        self.logger.info(f"Assessment Engine initialized with {len(self.question_core.questions_lookup)} questions")
    
    async def start_assessment(self, user_id: str, telegram_data: Dict[str, Any]) -> AssessmentResult:
        """Start assessment for user - NO SESSION CREATION"""
        
        start_time = time.time()
        self.logger.log_service_call("start_assessment", user_id)
        
        try:
            # Ensure user exists
            await self.assessment_dao.create_user_profile(user_id, telegram_data)
            
            # Get user's completed questions (NO SESSION DEPENDENCY)
            completed_questions = await self.assessment_dao.get_user_completed_questions(user_id)
            
            self.logger.info(f"User {user_id} has completed {len(completed_questions)} questions")
            
            # Initialize user state for this interaction
            self.user_states[user_id] = {
                "current_energy": 0.3,
                "trust_level": 1.0,
                "completed_questions": completed_questions,
                "start_time": datetime.now(timezone.utc)
            }
            
            # Select first/next question based on completed history
            next_question = await self._select_optimal_question(user_id, completed_questions)
            
            if not next_question:
                return AssessmentResult(
                    success=False,
                    message="No suitable questions available or assessment complete",
                    data={"completed_count": len(completed_questions)}
                )
            
            # Get user progress info
            progress_info = await self._get_user_progress_info(user_id, completed_questions)
            
            processing_time = time.time() - start_time
            self.logger.log_service_result("start_assessment", True, processing_time, 
                                         question_id=next_question["id"], user_id=user_id)
            
            return AssessmentResult(
                success=True,
                message="Assessment ready - question selected",
                next_question=next_question,
                user_progress=progress_info,
                data={
                    "questions_completed": len(completed_questions),
                    "assessment_stage": self._get_assessment_stage(len(completed_questions)),
                    "question_id": next_question["id"]
                }
            )
            
        except Exception as e:
            self.logger.log_error("ASSESSMENT_START_ERROR", f"Failed to start assessment: {e}", 
                                 user_id, e)
            return AssessmentResult(
                success=False,
                message=f"Failed to start assessment: {str(e)}"
            )
    
    async def process_answer(self, user_id: str, question_id: str, 
                           answer_text: str) -> AssessmentResult:
        """Process user answer - IMMEDIATE PROCESSING AND STORAGE"""
        
        start_time = time.time()
        self.logger.log_service_call("process_answer", user_id, 
                                   question_id=question_id, answer_length=len(answer_text))
        
        try:
            # Get question from core
            question = self.question_core.get_question(question_id)
            if not question:
                raise ValueError(f"Question {question_id} not found in core")
            
            # 1. IMMEDIATE ANALYSIS - no waiting for sessions
            analysis = await self._analyze_answer(user_id, question, answer_text)
            
            # 2. IMMEDIATE STORAGE - save answer instantly
            answer_id = await self.assessment_dao.save_question_answer(
                user_id, question_id, answer_text, analysis.__dict__
            )
            
            # 3. UPDATE USER STATE - real-time energy and trust tracking
            await self._update_user_state(user_id, question, analysis)
            
            # 4. GET NEXT QUESTION - intelligent selection based on history
            completed_questions = await self.assessment_dao.get_user_completed_questions(user_id)
            next_question = await self._select_optimal_question(user_id, completed_questions)
            
            # 5. CHECK COMPLETION STATUS
            assessment_complete = await self._check_assessment_completion(user_id, completed_questions)
            
            if assessment_complete:
                await self.assessment_dao.complete_assessment(user_id)
                
                return AssessmentResult(
                    success=True,
                    message="Assessment completed successfully!",
                    data={
                        "assessment_complete": True,
                        "total_questions": len(completed_questions),
                        "analysis": analysis.__dict__,
                        "answer_id": answer_id
                    }
                )
            
            # 6. PREPARE USER PROGRESS
            progress_info = await self._get_user_progress_info(user_id, completed_questions)
            
            processing_time = time.time() - start_time
            self.logger.log_service_result("process_answer", True, processing_time,
                                         answer_id=answer_id, next_question_id=next_question["id"] if next_question else None)
            
            return AssessmentResult(
                success=True,
                message="Answer processed successfully",
                next_question=next_question,
                user_progress=progress_info,
                data={
                    "answer_id": answer_id,
                    "analysis": analysis.__dict__,
                    "questions_completed": len(completed_questions),
                    "assessment_stage": self._get_assessment_stage(len(completed_questions))
                }
            )
            
        except Exception as e:
            self.logger.log_error("ANSWER_PROCESSING_ERROR", 
                                 f"Failed to process answer: {e}", user_id, e)
            return AssessmentResult(
                success=False,
                message=f"Failed to process answer: {str(e)}"
            )
    
    async def get_assessment_status(self, user_id: str) -> AssessmentResult:
        """Get current assessment status for user"""
        
        self.logger.log_service_call("get_assessment_status", user_id)
        
        try:
            # Get user profile
            user_profile = await self.user_dao.get_user_profile(user_id)
            if not user_profile:
                return AssessmentResult(
                    success=False,
                    message="User not found"
                )
            
            # Get assessment statistics
            stats = await self.assessment_dao.get_user_answer_statistics(user_id)
            
            # Get current state
            current_state = await self.assessment_dao.get_user_assessment_state(user_id)
            
            # Determine next action
            completed_questions = await self.assessment_dao.get_user_completed_questions(user_id)
            next_question = await self._select_optimal_question(user_id, completed_questions)
            
            status_data = {
                "user_profile": user_profile,
                "assessment_stats": stats,
                "current_state": current_state,
                "next_question_available": next_question is not None,
                "assessment_complete": user_profile["user"]["onboarding_completed"],
                "questions_completed": len(completed_questions),
                "assessment_stage": self._get_assessment_stage(len(completed_questions))
            }
            
            self.logger.log_service_result("get_assessment_status", True)
            
            return AssessmentResult(
                success=True,
                message="Assessment status retrieved",
                data=status_data,
                next_question=next_question
            )
            
        except Exception as e:
            self.logger.log_error("STATUS_RETRIEVAL_ERROR", 
                                 f"Failed to get assessment status: {e}", user_id, e)
            return AssessmentResult(
                success=False,
                message=f"Failed to get status: {str(e)}"
            )
    
    async def _select_optimal_question(self, user_id: str, 
                                     completed_questions: List[str]) -> Optional[Dict[str, Any]]:
        """Select optimal next question - INTELLIGENT ALGORITHM"""
        
        user_state = self.user_states.get(user_id, {})
        current_energy = user_state.get("current_energy", 0.3)
        trust_level = user_state.get("trust_level", 1.0)
        
        # 1. ENERGY SAFETY CHECK - if user is depleted, prioritize healing
        if current_energy < self.energy_threshold:
            healing_questions = self.question_core.search_questions(
                energy="HEALING", 
                min_safety=4
            )
            
            available_healing = [q for q in healing_questions if q["id"] not in completed_questions]
            if available_healing:
                self.logger.info(f"Selected HEALING question for user {user_id} (energy={current_energy})")
                return available_healing[0]
        
        # 2. DOMAIN PROGRESSION - explore new domains first
        explored_domains = self._get_explored_domains(completed_questions)
        available_domains = [
            "IDENTITY", "EMOTIONS", "RELATIONSHIPS", "WORK", 
            "HEALTH", "CREATIVITY", "FUTURE", "LIFESTYLE"
        ]
        
        unexplored_domains = [d for d in available_domains if d not in explored_domains]
        
        if unexplored_domains:
            # Start with a new domain
            target_domain = unexplored_domains[0]
            domain_questions = self.question_core.search_questions(
                domain=target_domain,
                journey_stage="EXPLORING",
                min_safety=3
            )
            
            available_domain = [q for q in domain_questions if q["id"] not in completed_questions]
            if available_domain:
                # Filter by trust level
                suitable = [q for q in available_domain 
                          if q["psychology"]["trust_requirement"] <= trust_level]
                
                if suitable:
                    self.logger.info(f"Selected domain exploration question for {user_id}: {target_domain}")
                    return suitable[0]
        
        # 3. DEPTH PROGRESSION - go deeper in explored domains
        if explored_domains:
            for domain in explored_domains:
                deeper_questions = self.question_core.search_questions(
                    domain=domain,
                    depth_level="SUBCONSCIOUS",  # Deeper questions
                    min_safety=2
                )
                
                available_deeper = [q for q in deeper_questions if q["id"] not in completed_questions]
                suitable_deeper = [q for q in available_deeper 
                                 if q["psychology"]["trust_requirement"] <= trust_level]
                
                if suitable_deeper:
                    self.logger.info(f"Selected deeper question for {user_id} in {domain}")
                    return suitable_deeper[0]
        
        # 4. SAFE FALLBACK - any available safe question
        safe_questions = self.question_core.search_questions(
            energy="NEUTRAL",
            min_safety=4
        )
        
        available_safe = [q for q in safe_questions if q["id"] not in completed_questions]
        if available_safe:
            self.logger.info(f"Selected safe fallback question for {user_id}")
            return available_safe[0]
        
        # 5. NO MORE QUESTIONS AVAILABLE
        self.logger.info(f"No more suitable questions available for user {user_id}")
        return None
    
    async def _analyze_answer(self, user_id: str, question: Dict[str, Any], 
                            answer_text: str) -> QuestionAnalysis:
        """Analyze user's answer with domain-specific intelligence"""
        
        # Basic metrics
        word_count = len(answer_text.split())
        answer_length = len(answer_text)
        
        # Emotional analysis
        positive_words = ["хорошо", "отлично", "люблю", "радует", "счастлив", "вдохновляет"]
        negative_words = ["плохо", "грустно", "злой", "проблема", "тяжело", "страшно", "болит"]
        vulnerability_words = ["чувствую", "боюсь", "переживаю", "волнуюсь", "сложно", "трудно"]
        
        positive_count = sum(1 for word in positive_words if word in answer_text.lower())
        negative_count = sum(1 for word in negative_words if word in answer_text.lower())
        vulnerability_count = sum(1 for word in vulnerability_words if word in answer_text.lower())
        
        # Determine emotional state
        if negative_count > positive_count:
            emotional_state = "negative"
            energy_impact = -0.2
        elif positive_count > 0:
            emotional_state = "positive"
            energy_impact = 0.15
        else:
            emotional_state = "neutral"
            energy_impact = 0.0
        
        # Calculate metrics
        openness_level = min(1.0, (word_count / 20.0) + (answer_length / 200.0))
        depth_of_reflection = min(1.0, word_count / 25.0)
        vulnerability_shown = min(1.0, (vulnerability_count / max(1, len(vulnerability_words))) + 
                                      (openness_level * 0.3))
        
        # Resistance detection
        resistance_detected = (word_count < 5 or 
                             "не знаю" in answer_text.lower() or
                             "не хочу" in answer_text.lower())
        
        # Trust building
        trust_building = openness_level * vulnerability_shown * 0.1
        
        # Generate insights based on domain
        key_insights = self._generate_domain_insights(question, answer_text, openness_level)
        
        # Personality markers based on question domain and answer content
        personality_markers = self._extract_personality_markers(question, answer_text)
        
        # Recommend next energy type
        if emotional_state == "negative" and vulnerability_shown > 0.5:
            recommended_next_energy = "HEALING"
        elif resistance_detected:
            recommended_next_energy = "OPENING"
        elif openness_level > 0.7 and trust_building > 0.05:
            recommended_next_energy = "PROCESSING"  # Can go deeper
        else:
            recommended_next_energy = "NEUTRAL"
        
        return QuestionAnalysis(
            emotional_state=emotional_state,
            openness_level=round(openness_level, 2),
            depth_of_reflection=round(depth_of_reflection, 2),
            vulnerability_shown=round(vulnerability_shown, 2),
            resistance_detected=resistance_detected,
            key_insights=key_insights,
            energy_impact=energy_impact,
            trust_building=trust_building,
            personality_markers=personality_markers,
            recommended_next_energy=recommended_next_energy
        )
    
    def _generate_domain_insights(self, question: Dict[str, Any], answer: str, 
                                openness: float) -> List[str]:
        """Generate domain-specific insights"""
        
        domain = question["classification"]["domain"]
        insights = []
        
        if domain == "IDENTITY":
            if openness > 0.7:
                insights.append("Высокий уровень самоосознанности")
            if "я" in answer.lower()[:10]:  # Self-focus at beginning
                insights.append("Сильная самофокусированность")
        
        elif domain == "EMOTIONS":
            emotional_words = ["чувствую", "эмоции", "переживаю"]
            if any(word in answer.lower() for word in emotional_words):
                insights.append("Развитая эмоциональная осознанность")
        
        elif domain == "RELATIONSHIPS":
            social_words = ["люди", "друзья", "семья", "отношения"]
            if any(word in answer.lower() for word in social_words):
                insights.append("Высокая социальная ориентированность")
        
        elif domain == "WORK":
            if any(word in answer.lower() for word in ["карьера", "цель", "достижение"]):
                insights.append("Сильная мотивация достижения")
        
        # General insights
        if len(answer.split()) > 50:
            insights.append("Склонность к детальному анализу")
        
        if "потому что" in answer.lower() or "поэтому" in answer.lower():
            insights.append("Аналитический стиль мышления")
        
        return insights[:3]  # Limit to top 3
    
    def _extract_personality_markers(self, question: Dict[str, Any], answer: str) -> Dict[str, float]:
        """Extract personality markers from answer"""
        
        markers = {}
        domain = question["classification"]["domain"]
        answer_lower = answer.lower()
        
        # Openness markers
        if any(word in answer_lower for word in ["новое", "творческ", "идея", "эксперимент"]):
            markers["openness"] = 0.1
        
        # Conscientiousness markers
        if any(word in answer_lower for word in ["план", "организ", "цель", "дисциплин"]):
            markers["conscientiousness"] = 0.1
        
        # Extraversion markers
        if any(word in answer_lower for word in ["люди", "общение", "команда", "группа"]):
            markers["extraversion"] = 0.1
        
        # Agreeableness markers
        if any(word in answer_lower for word in ["помощь", "сотрудничество", "доброта"]):
            markers["agreeableness"] = 0.1
        
        # Neuroticism markers (reverse scoring)
        if any(word in answer_lower for word in ["спокойн", "стабильн", "уравновешен"]):
            markers["emotional_stability"] = 0.1
        elif any(word in answer_lower for word in ["тревож", "стресс", "волнени"]):
            markers["neuroticism"] = 0.1
        
        return markers
    
    async def _update_user_state(self, user_id: str, question: Dict[str, Any], 
                               analysis: QuestionAnalysis):
        """Update user's energy and trust state"""
        
        if user_id not in self.user_states:
            self.user_states[user_id] = {"current_energy": 0.3, "trust_level": 1.0}
        
        # Update energy
        energy_impacts = {
            "OPENING": 0.3,
            "NEUTRAL": 0.0,
            "PROCESSING": -0.1,
            "HEAVY": -0.5,
            "HEALING": 0.4
        }
        
        question_energy_impact = energy_impacts.get(question["classification"]["energy_dynamic"], 0.0)
        total_energy_change = question_energy_impact + analysis.energy_impact
        
        self.user_states[user_id]["current_energy"] = max(-2.0, 
            min(2.0, self.user_states[user_id]["current_energy"] + total_energy_change))
        
        # Update trust
        trust_change = analysis.trust_building
        self.user_states[user_id]["trust_level"] = min(5.0, 
            self.user_states[user_id]["trust_level"] + trust_change)
        
        self.logger.info(f"Updated user {user_id} state: energy={self.user_states[user_id]['current_energy']:.2f}, trust={self.user_states[user_id]['trust_level']:.2f}")
    
    def _get_explored_domains(self, completed_questions: List[str]) -> List[str]:
        """Get domains that user has already explored"""
        
        explored = set()
        for question_id in completed_questions:
            question = self.question_core.get_question(question_id)
            if question:
                explored.add(question["classification"]["domain"])
        
        return list(explored)
    
    async def _get_user_progress_info(self, user_id: str, 
                                    completed_questions: List[str]) -> Dict[str, Any]:
        """Get comprehensive user progress information"""
        
        user_state = self.user_states.get(user_id, {})
        explored_domains = self._get_explored_domains(completed_questions)
        
        return {
            "questions_completed": len(completed_questions),
            "current_energy": user_state.get("current_energy", 0.3),
            "trust_level": user_state.get("trust_level", 1.0),
            "domains_explored": explored_domains,
            "assessment_stage": self._get_assessment_stage(len(completed_questions)),
            "completion_percentage": min(100, (len(completed_questions) / 20) * 100)  # Assume 20 questions for basic completion
        }
    
    def _get_assessment_stage(self, questions_completed: int) -> str:
        """Determine current assessment stage"""
        
        if questions_completed == 0:
            return "not_started"
        elif questions_completed < 5:
            return "initial_exploration"
        elif questions_completed < 15:
            return "domain_mapping" 
        elif questions_completed < 25:
            return "depth_analysis"
        elif questions_completed < 40:
            return "comprehensive_profiling"
        else:
            return "advanced_insights"
    
    async def _check_assessment_completion(self, user_id: str, 
                                         completed_questions: List[str]) -> bool:
        """Check if assessment should be considered complete"""
        
        # Basic completion criteria
        min_questions = 15  # Minimum for basic profiling
        min_domains = 4     # Should explore at least 4 domains
        
        if len(completed_questions) < min_questions:
            return False
        
        explored_domains = self._get_explored_domains(completed_questions)
        if len(explored_domains) < min_domains:
            return False
        
        # Check if user has good coverage across important domains
        important_domains = ["IDENTITY", "EMOTIONS", "RELATIONSHIPS", "WORK"]
        covered_important = [d for d in important_domains if d in explored_domains]
        
        if len(covered_important) < 3:
            return False
        
        self.logger.info(f"Assessment completion check for {user_id}: {len(completed_questions)} questions, {len(explored_domains)} domains - COMPLETE")
        return True