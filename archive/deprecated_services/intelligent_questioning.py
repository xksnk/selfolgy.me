"""
Intelligent Questioning System - Integration with Question Core
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timezone
import asyncio

# Add question core to path
sys.path.append(str(Path(__file__).parent.parent.parent / "intelligent_question_core"))

from intelligent_question_core.api.core_api import SelfologyQuestionCore
from .vector_service import VectorService
from .user_service import UserService
from ..ai.router import AIRouter
from ..core.logging import LoggerMixin
from ..core.error_handling import handle_errors, ErrorCode


class IntelligentQuestioningSystem(LoggerMixin):
    """
    Core intelligent questioning system that integrates the Question Core
    with adaptive AI for personalized psychological assessment.
    """
    
    def __init__(self):
        # Initialize question core
        core_path = Path(__file__).parent.parent.parent / "intelligent_question_core/data/selfology_intelligent_core.json"
        self.question_core = SelfologyQuestionCore(str(core_path))
        
        self.vector_service = VectorService()
        self.ai_router = AIRouter()
        
        # Session state storage (in production would use Redis)
        self.session_states = {}
        
        self.logger.info("Intelligent Questioning System initialized with 693 questions")
    
    @handle_errors(ErrorCode.AI_ROUTING_ERROR, "Ошибка выбора вопроса")
    async def start_intelligent_onboarding(self, user_id: int, user_tier: str = "free") -> Dict[str, Any]:
        """
        Start intelligent onboarding with first question from core.
        """
        
        # Initialize session state
        self.session_states[user_id] = {
            "current_energy": 0.3,        # Начинаем с небольшого позитива
            "trust_level": 1.0,           # Минимальное доверие
            "questions_asked": [],
            "energy_timeline": [0.3],
            "resistance_count": 0,
            "breakthrough_count": 0,
            "session_start": datetime.now(timezone.utc),
            "current_domain": None,
            "healing_debt": 0.0,
            "user_tier": user_tier
        }
        
        # Select first question - always safe and opening
        first_question = await self._select_first_question(user_id)
        
        # Update session state
        self.session_states[user_id]["questions_asked"].append(first_question["id"])
        self.session_states[user_id]["current_domain"] = first_question["classification"]["domain"]
        
        # Log start of intelligent onboarding
        self.log_user_action("intelligent_onboarding_started", user_id,
                           question_id=first_question["id"],
                           domain=first_question["classification"]["domain"])
        
        return {
            "question": first_question,
            "session_info": {
                "energy_level": self.session_states[user_id]["current_energy"],
                "trust_level": self.session_states[user_id]["trust_level"],
                "question_number": 1
            }
        }
    
    async def _select_first_question(self, user_id: int) -> Dict[str, Any]:
        """Select optimal first question for user"""
        
        # Пробуем найти безопасные вопросы для начала (без строгих фильтров)
        # Сначала пробуем CONSCIOUS уровень (более мягкий чем SURFACE)
        entry_questions = self.question_core.search_questions(
            depth_level="CONSCIOUS",
            min_safety=4
        )
        
        # Если нет подходящих, пробуем без фильтра энергии
        if not entry_questions:
            entry_questions = self.question_core.search_questions(min_safety=3)
        
        if entry_questions:
            # Select randomly from safe entry questions
            import random
            selected = random.choice(entry_questions[:5])  # Top 5 safest
            
            self.logger.info(f"Selected entry question for user {user_id}: {selected['id']}")
            return selected
        
        # Fallback to simplest question
        fallback_questions = self.question_core.search_questions(
            depth_level="SURFACE",
            min_safety=5
        )
        
        return fallback_questions[0] if fallback_questions else None
    
    @handle_errors(ErrorCode.AI_API_ERROR, "Ошибка анализа ответа")
    async def process_user_answer(self, user_id: int, question_id: str, answer: str) -> Dict[str, Any]:
        """
        Process user answer with intelligent analysis and vector updates.
        """
        
        # 1. Get question from core
        question = self.question_core.get_question(question_id)
        if not question:
            raise ValueError(f"Question {question_id} not found in core")
        
        # 2. Analyze answer with recommended AI model
        model = question["processing_hints"]["recommended_model"]
        user_context = await self._get_user_context(user_id)
        
        answer_analysis = await self._analyze_answer_with_ai(
            question=question,
            answer=answer,
            model=model,
            user_context=user_context
        )
        
        # 3. Update session state
        session_impact = await self._update_session_state(user_id, question, answer_analysis)
        
        # 4. Update personality vector
        vector_updates = await self._update_personality_vector(user_id, question, answer_analysis)
        
        # 5. Select next question intelligently
        next_question = await self._select_next_question_adaptive(user_id, question, answer_analysis)
        
        # Log the interaction
        self.log_ai_interaction(
            model=model,
            response_time=answer_analysis.get("processing_time", 0),
            cost=answer_analysis.get("estimated_cost", 0),
            user_id=user_id,
            question_id=question_id
        )
        
        return {
            "answer_analysis": answer_analysis,
            "session_impact": session_impact,
            "vector_updates": vector_updates,
            "next_question": next_question,
            "session_state": self.session_states[user_id].copy()
        }
    
    async def _analyze_answer_with_ai(self, question: Dict, answer: str, model: str, user_context: Dict) -> Dict:
        """Analyze user answer with recommended AI model"""
        
        # Create analysis prompt based on question metadata
        system_prompt = self._create_analysis_prompt(question, user_context)
        
        messages = [{
            "role": "user",
            "content": f"""
Вопрос: {question['text']}
Ответ пользователя: {answer}

Проанализируйте ответ согласно инструкциям.
            """
        }]
        
        try:
            from ..ai.clients import ai_client_manager
            from ..ai.router import AIModel
            
            # Convert model string to enum
            ai_model = AIModel(model) if model in [m.value for m in AIModel] else AIModel.GPT_4O_MINI
            
            analysis_result = await ai_client_manager.generate_response(
                model=ai_model,
                messages=messages,
                system_prompt=system_prompt,
                max_tokens=800
            )
            
            # Parse structured analysis from AI response
            return self._parse_analysis_response(analysis_result, question, answer)
            
        except Exception as e:
            self.log_error("AI_ANALYSIS_ERROR", f"Failed to analyze answer: {e}", user_id)
            
            # Fallback analysis
            return self._create_fallback_analysis(question, answer)
    
    def _create_analysis_prompt(self, question: Dict, user_context: Dict) -> str:
        """Create analysis prompt based on question metadata"""
        
        domain = question["classification"]["domain"]
        depth = question["classification"]["depth_level"]
        energy = question["classification"]["energy_dynamic"]
        
        return f"""
Вы - эксперт психолог, анализирующий ответ на вопрос из системы Selfology.

КОНТЕКСТ ВОПРОСА:
- Домен: {domain}
- Глубина: {depth}  
- Энергетический тип: {energy}
- Сложность: {question['psychology']['complexity']}/5
- Эмоциональная нагрузка: {question['psychology']['emotional_weight']}/5

КОНТЕКСТ ПОЛЬЗОВАТЕЛЯ:
- Уровень доверия: {user_context.get('trust_level', 1.0)}/5.0
- Энергетическое состояние: {user_context.get('energy_level', 0.0)}/2.0
- Пройденных вопросов: {user_context.get('questions_count', 0)}

ЗАДАЧА:
Проанализируйте ответ и верните JSON с полями:
{{
  "emotional_state": "positive/neutral/negative",
  "openness_level": 0.0-1.0,
  "depth_of_reflection": 0.0-1.0,
  "resistance_detected": true/false,
  "vulnerability_shown": 0.0-1.0,
  "key_insights": ["инсайт1", "инсайт2"],
  "personality_markers": {{"trait": "value"}},
  "energy_impact": -1.0 до +1.0,
  "trust_building": 0.0-1.0,
  "recommended_next_energy": "OPENING/NEUTRAL/PROCESSING/HEAVY/HEALING"
}}

Анализируйте объективно, ищите паттерны и глубинные смыслы.
        """
    
    def _parse_analysis_response(self, ai_response: str, question: Dict, answer: str) -> Dict:
        """Parse AI analysis response into structured data"""
        
        try:
            # Try to extract JSON from response
            import re
            json_match = re.search(r'\{.*\}', ai_response, re.DOTALL)
            if json_match:
                analysis = json.loads(json_match.group())
            else:
                # Parse from structured text
                analysis = self._parse_text_analysis(ai_response)
            
            # Add metadata
            analysis["question_id"] = question["id"]
            analysis["question_domain"] = question["classification"]["domain"]
            analysis["processing_time"] = 0.5  # Placeholder
            analysis["estimated_cost"] = 0.05  # Placeholder
            analysis["analysis_timestamp"] = datetime.now(timezone.utc).isoformat()
            
            return analysis
            
        except Exception as e:
            self.logger.warning(f"Failed to parse AI analysis: {e}")
            return self._create_fallback_analysis(question, answer)
    
    def _create_fallback_analysis(self, question: Dict, answer: str) -> Dict:
        """Create fallback analysis when AI fails"""
        
        return {
            "emotional_state": "neutral",
            "openness_level": 0.5,
            "depth_of_reflection": 0.3,
            "resistance_detected": False,
            "vulnerability_shown": 0.3,
            "key_insights": ["Пользователь ответил на вопрос"],
            "personality_markers": {},
            "energy_impact": 0.0,
            "trust_building": 0.1,
            "recommended_next_energy": "NEUTRAL",
            "fallback_analysis": True,
            "question_id": question["id"],
            "question_domain": question["classification"]["domain"]
        }
    
    async def _update_session_state(self, user_id: int, question: Dict, answer_analysis: Dict) -> Dict:
        """Update session state based on question and answer analysis"""
        
        session = self.session_states.get(user_id, {})
        
        # Update energy level
        question_energy_impact = {
            "OPENING": +0.3,
            "NEUTRAL": 0.0,
            "PROCESSING": -0.1, 
            "HEAVY": -0.5,
            "HEALING": +0.4
        }
        
        energy_change = (
            question_energy_impact.get(question["classification"]["energy_dynamic"], 0.0) +
            answer_analysis.get("energy_impact", 0.0)
        )
        
        session["current_energy"] = max(-2.0, min(2.0, session["current_energy"] + energy_change))
        session["energy_timeline"].append(session["current_energy"])
        
        # Update trust level
        trust_change = answer_analysis.get("trust_building", 0.0)
        session["trust_level"] = min(5.0, session["trust_level"] + trust_change * 0.1)
        
        # Track resistance and breakthroughs
        if answer_analysis.get("resistance_detected"):
            session["resistance_count"] += 1
        
        if answer_analysis.get("vulnerability_shown", 0) > 0.7:
            session["breakthrough_count"] += 1
        
        # Update healing debt
        if question["classification"]["energy_dynamic"] == "HEAVY":
            session["healing_debt"] += 0.5
        elif question["classification"]["energy_dynamic"] == "HEALING":
            session["healing_debt"] = max(0, session["healing_debt"] - 0.4)
        
        self.session_states[user_id] = session
        
        return {
            "energy_change": energy_change,
            "new_energy_level": session["current_energy"],
            "trust_change": trust_change,
            "new_trust_level": session["trust_level"],
            "healing_debt": session["healing_debt"]
        }
    
    async def _update_personality_vector(self, user_id: int, question: Dict, answer_analysis: Dict) -> Dict:
        """Update user's personality vector based on answer analysis"""
        
        domain = question["classification"]["domain"]
        personality_markers = answer_analysis.get("personality_markers", {})
        
        # Map domain to vector dimensions
        vector_mapping = {
            "IDENTITY": ["self_awareness", "self_acceptance", "identity_clarity"],
            "EMOTIONS": ["emotional_intelligence", "emotional_stability", "emotion_expression"],
            "RELATIONSHIPS": ["social_skills", "empathy", "attachment_style"],
            "WORK": ["achievement_orientation", "work_satisfaction", "career_clarity"],
            "MONEY": ["financial_confidence", "money_beliefs", "security_orientation"],
            "HEALTH": ["body_awareness", "self_care", "vitality"],
            "CREATIVITY": ["creative_expression", "artistic_appreciation", "innovation"],
            "SPIRITUALITY": ["meaning_seeking", "transcendence", "spiritual_practices"],
            "PAST": ["past_integration", "trauma_healing", "family_patterns"],
            "FUTURE": ["goal_orientation", "optimism", "future_planning"],
            "LIFESTYLE": ["life_balance", "habit_strength", "routine_flexibility"],
            "THOUGHTS": ["cognitive_flexibility", "critical_thinking", "mindfulness"]
        }
        
        # Calculate vector updates
        vector_updates = {}
        domain_dimensions = vector_mapping.get(domain, [])
        
        for dimension in domain_dimensions:
            if dimension in personality_markers:
                vector_updates[dimension] = personality_markers[dimension]
        
        # Apply updates to vector store
        if vector_updates:
            await self.vector_service.update_user_personality_dimensions(
                user_id=str(user_id),
                dimension_updates=vector_updates,
                source_question=question["id"],
                confidence=answer_analysis.get("openness_level", 0.5)
            )
        
        return vector_updates
    
    async def _select_next_question_adaptive(self, user_id: int, current_question: Dict, answer_analysis: Dict) -> Optional[Dict]:
        """
        Intelligently select next question based on user state and answer analysis.
        """
        
        session = self.session_states.get(user_id, {})
        
        # 1. Check energy safety requirements
        if session["healing_debt"] > 0.5 or session["current_energy"] < -1.0:
            # URGENT: Need healing question
            healing_questions = self.question_core.search_questions(
                energy="HEALING",
                min_safety=4,
                domain=current_question["classification"]["domain"]  # Same domain for relevance
            )
            
            if healing_questions:
                selected = healing_questions[0]
                self.logger.info(f"Selected HEALING question for user {user_id} due to energy debt")
                return selected
        
        # 2. Check for resistance - need to back off
        if answer_analysis.get("resistance_detected") or session["resistance_count"] > 2:
            # Select gentler questions
            gentle_questions = self.question_core.search_questions(
                energy="NEUTRAL",
                depth_level="SURFACE",
                min_safety=5
            )
            
            if gentle_questions:
                selected = gentle_questions[0]
                self.logger.info(f"Selected gentle question for user {user_id} due to resistance")
                return selected
        
        # 3. Check for breakthrough potential - can deepen
        if (answer_analysis.get("vulnerability_shown", 0) > 0.7 and 
            session["trust_level"] > 3.0 and 
            session["current_energy"] > 0.0):
            
            # Look for deeper connected questions
            connected_questions = self.question_core.find_connected_questions(
                current_question["id"],
                "depth_progression"
            )
            
            # Filter by trust level
            accessible_questions = [
                q for q in connected_questions 
                if q["psychology"]["trust_requirement"] <= session["trust_level"]
            ]
            
            if accessible_questions:
                selected = accessible_questions[0]
                self.logger.info(f"Selected deeper question for user {user_id} - breakthrough potential")
                return selected
        
        # 4. Logical continuation - thematic connections
        thematic_questions = self.question_core.find_connected_questions(
            current_question["id"],
            "thematic_cluster"
        )
        
        # Filter already asked questions
        asked_ids = session["questions_asked"]
        new_questions = [q for q in thematic_questions if q["id"] not in asked_ids]
        
        # Filter by safety and trust
        safe_questions = [
            q for q in new_questions
            if (q["psychology"]["safety_level"] >= 3 and
                q["psychology"]["trust_requirement"] <= session["trust_level"])
        ]
        
        if safe_questions:
            selected = safe_questions[0]
            self.logger.info(f"Selected thematic continuation for user {user_id}")
            return selected
        
        # 5. Fallback - explore new domain
        unexplored_domains = await self._get_unexplored_domains(user_id)
        
        if unexplored_domains:
            domain_questions = self.question_core.search_questions(
                domain=unexplored_domains[0],
                journey_stage="EXPLORING",
                depth_level="CONSCIOUS",
                min_safety=3
            )
            
            if domain_questions:
                selected = domain_questions[0]
                self.logger.info(f"Selected new domain question for user {user_id}: {unexplored_domains[0]}")
                return selected
        
        # 6. Ultimate fallback - safe question
        fallback_questions = self.question_core.search_questions(
            energy="NEUTRAL",
            min_safety=5
        )
        
        return fallback_questions[0] if fallback_questions else None
    
    async def _get_user_context(self, user_id: int) -> Dict[str, Any]:
        """Get comprehensive user context for AI analysis"""
        
        session = self.session_states.get(user_id, {})
        
        return {
            "trust_level": session.get("trust_level", 1.0),
            "energy_level": session.get("current_energy", 0.0),
            "questions_count": len(session.get("questions_asked", [])),
            "resistance_count": session.get("resistance_count", 0),
            "breakthrough_count": session.get("breakthrough_count", 0),
            "session_duration_minutes": self._get_session_duration(user_id),
            "current_domain": session.get("current_domain"),
            "user_tier": session.get("user_tier", "free")
        }
    
    def _get_session_duration(self, user_id: int) -> int:
        """Calculate session duration in minutes"""
        session = self.session_states.get(user_id, {})
        start_time = session.get("session_start")
        
        if start_time:
            duration = datetime.now(timezone.utc) - start_time
            return int(duration.total_seconds() / 60)
        
        return 0
    
    async def _get_unexplored_domains(self, user_id: int) -> List[str]:
        """Get domains not yet explored by user"""
        
        session = self.session_states.get(user_id, {})
        asked_questions = session.get("questions_asked", [])
        
        # Get domains of asked questions
        explored_domains = set()
        for question_id in asked_questions:
            question = self.question_core.get_question(question_id)
            if question:
                explored_domains.add(question["classification"]["domain"])
        
        # Return unexplored domains
        all_domains = [
            "IDENTITY", "EMOTIONS", "RELATIONSHIPS", "WORK", 
            "MONEY", "HEALTH", "CREATIVITY", "SPIRITUALITY",
            "PAST", "FUTURE", "LIFESTYLE", "THOUGHTS"
        ]
        
        return [d for d in all_domains if d not in explored_domains]
    
    def get_session_analytics(self, user_id: int) -> Dict[str, Any]:
        """Get detailed session analytics"""
        
        session = self.session_states.get(user_id, {})
        
        if not session:
            return {"error": "No session found"}
        
        # Calculate energy balance
        energy_timeline = session.get("energy_timeline", [])
        energy_trend = "stable"
        if len(energy_timeline) > 1:
            if energy_timeline[-1] > energy_timeline[0]:
                energy_trend = "improving"
            elif energy_timeline[-1] < energy_timeline[0]:
                energy_trend = "declining"
        
        # Domain coverage
        asked_questions = session.get("questions_asked", [])
        domain_coverage = {}
        
        for question_id in asked_questions:
            question = self.question_core.get_question(question_id)
            if question:
                domain = question["classification"]["domain"]
                domain_coverage[domain] = domain_coverage.get(domain, 0) + 1
        
        return {
            "session_duration_minutes": self._get_session_duration(user_id),
            "questions_asked": len(asked_questions),
            "energy_trend": energy_trend,
            "current_energy": session.get("current_energy", 0.0),
            "trust_progression": session.get("trust_level", 1.0),
            "resistance_incidents": session.get("resistance_count", 0),
            "breakthrough_moments": session.get("breakthrough_count", 0),
            "domain_coverage": domain_coverage,
            "healing_debt": session.get("healing_debt", 0.0),
            "session_safety": "safe" if session.get("healing_debt", 0) < 1.0 else "needs_healing"
        }


# Global instance
intelligent_questioning = IntelligentQuestioningSystem()