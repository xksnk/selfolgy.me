"""
Enhanced Memory System for Selfology - Chat Insights & Answer Versioning
"""

import json
import re
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timezone
from dataclasses import dataclass, asdict

from .vector_service import VectorService
from .user_service import UserService
from ..ai.clients import ai_client_manager
from ..ai.router import AIModel, AIRouter
from ..core.logging import LoggerMixin
from ..core.error_handling import handle_errors, ErrorCode


@dataclass
class ChatInsight:
    """Structured representation of chat insight"""
    user_id: str
    insight_text: str
    insight_type: str  # factual_update, emotional_insight, behavioral_pattern, value_expression
    domain: str        # IDENTITY, EMOTIONS, etc.
    depth_level: str   # SURFACE, CONSCIOUS, EDGE
    confidence: float  # AI confidence in insight importance
    trigger_context: str  # What triggered this insight
    related_question_ids: List[str]  # Connected core questions
    vector_impact: Dict[str, float]  # Impact on personality vector
    timestamp: datetime
    supersedes: Optional[str] = None  # ID of previous insight it replaces


class EnhancedMemorySystem(LoggerMixin):
    """
    Comprehensive memory system that captures and processes:
    1. Important statements from chat sessions
    2. Answer corrections and versioning
    3. Spontaneous insights and their impact
    4. Dynamic personality vector updates
    """
    
    def __init__(self):
        self.vector_service = VectorService()
        self.user_service = UserService()
        self.ai_router = AIRouter()
        
        # In-memory storage for active sessions (production: Redis)
        self.active_insights = {}  # user_id -> List[ChatInsight]
        self.answer_versions = {}  # user_id -> {question_id -> List[versions]}
        
    @handle_errors(ErrorCode.AI_API_ERROR, "Ошибка анализа важности сообщения")
    async def analyze_chat_message_importance(self, user_id: int, message: str, 
                                           conversation_context: List[str] = None) -> Dict[str, Any]:
        """
        Analyze if chat message contains important information worth remembering.
        """
        
        # Create analysis prompt
        system_prompt = """
Вы - AI система анализа важности информации для психологического профиля.

Проанализируйте сообщение пользователя и определите, содержит ли оно информацию, 
которую стоит запомнить для углубления понимания его личности.

Верните JSON:
{
  "should_remember": true/false,
  "importance_score": 0.0-1.0,
  "memory_type": "factual_update/emotional_insight/behavioral_pattern/value_expression/goal_statement/belief_change",
  "extracted_insights": ["инсайт1", "инсайт2"],
  "psychological_domain": "IDENTITY/EMOTIONS/RELATIONSHIPS/WORK/etc",
  "depth_level": "SURFACE/CONSCIOUS/EDGE", 
  "confidence": 0.0-1.0,
  "reasoning": "почему это важно запомнить"
}

ПРИМЕРЫ ВАЖНОЙ ИНФОРМАЦИИ:
- Личностные паттерны: "Я всегда откладываю сложные разговоры"
- Эмоциональные инсайты: "Понял что злюсь когда чувствую себя непонятым"
- Ценности: "Для меня семья важнее карьеры"
- Цели и мечты: "Хочу открыть свой бизнес к 35 годам"
- Убеждения: "Считаю что успех зависит только от меня"
- Травматический опыт: "После развода родителей не доверяю отношениям"

НЕ важная информация:
- Бытовые факты: "Завтракал овсянкой"
- Вопросы к боту: "Как дела?"
- Технические сообщения
        """
        
        messages = [{
            "role": "user",
            "content": f"""
Сообщение для анализа: "{message}"

{"Контекст разговора: " + str(conversation_context) if conversation_context else ""}

Проанализируйте важность для психологического профиля.
            """
        }]
        
        try:
            # Use fast model for importance analysis
            analysis_result = await ai_client_manager.generate_response(
                model=AIModel.GPT_4O_MINI,
                messages=messages,
                system_prompt=system_prompt,
                max_tokens=500
            )
            
            # Parse JSON response
            analysis = self._parse_importance_analysis(analysis_result)
            
            # Log analysis
            self.log_ai_interaction(
                model="gpt-4o-mini",
                user_id=user_id,
                context={
                    "analysis_type": "importance_detection",
                    "should_remember": analysis.get("should_remember", False),
                    "importance_score": analysis.get("importance_score", 0.0)
                }
            )
            
            return analysis
            
        except Exception as e:
            self.log_error("IMPORTANCE_ANALYSIS_ERROR", f"Failed to analyze importance: {e}", user_id)
            return {
                "should_remember": False,
                "importance_score": 0.0,
                "error": "analysis_failed"
            }
    
    @handle_errors(ErrorCode.AI_API_ERROR, "Ошибка создания инсайта")
    async def create_chat_insight(self, user_id: int, message: str, importance_analysis: Dict) -> Optional[ChatInsight]:
        """
        Create structured insight from important chat message.
        """
        
        if not importance_analysis.get("should_remember"):
            return None
        
        # Find related questions from core
        related_questions = await self._find_related_core_questions(
            message, 
            importance_analysis["psychological_domain"]
        )
        
        # Calculate vector impact
        vector_impact = await self._calculate_insight_vector_impact(
            message,
            importance_analysis,
            related_questions
        )
        
        # Create insight object
        insight = ChatInsight(
            user_id=str(user_id),
            insight_text=message,
            insight_type=importance_analysis["memory_type"],
            domain=importance_analysis["psychological_domain"],
            depth_level=importance_analysis["depth_level"],
            confidence=importance_analysis["confidence"],
            trigger_context="chat_session",
            related_question_ids=[q["id"] for q in related_questions],
            vector_impact=vector_impact,
            timestamp=datetime.now(timezone.utc)
        )
        
        # Store insight
        await self._store_chat_insight(insight)
        
        # Update vector database
        await self._apply_insight_to_vector(insight)
        
        self.log_user_action(
            "chat_insight_captured", 
            user_id,
            insight_type=insight.insight_type,
            domain=insight.domain,
            confidence=insight.confidence
        )
        
        return insight
    
    async def _find_related_core_questions(self, message: str, domain: str) -> List[Dict]:
        """
        Find questions from intelligent core related to the chat message.
        """
        
        try:
            from .intelligent_questioning import intelligent_questioning
            
            # Search questions in the same domain
            domain_questions = intelligent_questioning.question_core.search_questions(
                domain=domain,
                depth_level="CONSCIOUS"
            )
            
            # Use AI to find most relevant questions
            relevance_analysis = await ai_client_manager.generate_response(
                model=AIModel.GPT_4O_MINI,
                messages=[{
                    "role": "user",
                    "content": f"""
Пользователь сказал: "{message}"

Какие из этих вопросов наиболее связаны с его утверждением?
Верните JSON: {{"relevant_question_ids": ["q_xxx", "q_yyy"], "relevance_scores": [0.9, 0.7]}}

Вопросы для анализа:
{json.dumps([{"id": q["id"], "text": q["text"]} for q in domain_questions[:20]], ensure_ascii=False)}
                    """
                }],
                max_tokens=200
            )
            
            # Parse relevance results
            relevance_data = self._parse_json_response(relevance_analysis)
            relevant_ids = relevance_data.get("relevant_question_ids", [])
            
            # Return relevant questions
            return [
                q for q in domain_questions 
                if q["id"] in relevant_ids
            ][:3]  # Max 3 related questions
            
        except Exception as e:
            self.log_error("RELATED_QUESTIONS_ERROR", f"Failed to find related questions: {e}")
            return []
    
    async def handle_answer_correction(self, user_id: int, original_question_id: str, 
                                     new_answer: str, correction_reason: str) -> Dict[str, Any]:
        """
        Handle correction of previous answer to core question.
        """
        
        # Get previous answer versions
        if user_id not in self.answer_versions:
            self.answer_versions[user_id] = {}
        
        question_versions = self.answer_versions[user_id].get(original_question_id, [])
        
        # Create new version
        new_version = {
            "version": len(question_versions) + 1,
            "answer": new_answer,
            "correction_reason": correction_reason,
            "timestamp": datetime.now(timezone.utc),
            "is_current": True
        }
        
        # Mark previous versions as superseded
        for version in question_versions:
            version["is_current"] = False
        
        question_versions.append(new_version)
        self.answer_versions[user_id][original_question_id] = question_versions
        
        # Analyze new answer and calculate vector changes
        try:
            from .intelligent_questioning import intelligent_questioning
            
            question = intelligent_questioning.question_core.get_question(original_question_id)
            if question:
                # Get old analysis for comparison
                old_analysis = question_versions[-2].get("analysis") if len(question_versions) > 1 else {}
                
                # Analyze new answer
                new_analysis = await intelligent_questioning._analyze_answer_with_ai(
                    question=question,
                    answer=new_answer,
                    model=question["processing_hints"]["recommended_model"],
                    user_context=await intelligent_questioning._get_user_context(user_id)
                )
                
                new_version["analysis"] = new_analysis
                
                # Calculate vector corrections
                vector_corrections = await self._calculate_answer_correction_impact(
                    question, old_analysis, new_analysis
                )
                
                # Apply corrections to vector
                if vector_corrections:
                    await self.vector_service.apply_vector_corrections(
                        user_id=str(user_id),
                        corrections=vector_corrections,
                        source=f"answer_correction_{original_question_id}_v{new_version['version']}"
                    )
                
                # Log correction
                self.log_user_action(
                    "answer_corrected",
                    user_id,
                    question_id=original_question_id,
                    version=new_version["version"],
                    reason=correction_reason
                )
                
                return {
                    "correction_applied": True,
                    "new_version": new_version["version"],
                    "vector_corrections": vector_corrections,
                    "analysis": new_analysis
                }
        
        except Exception as e:
            self.log_error("ANSWER_CORRECTION_ERROR", f"Failed to process correction: {e}", user_id)
            
        return {
            "correction_applied": False,
            "error": "processing_failed"
        }
    
    async def detect_spontaneous_insights(self, user_id: int, chat_message: str) -> List[Dict]:
        """
        Detect spontaneous insights in user's chat message.
        """
        
        # Insight detection patterns
        insight_patterns = [
            r"я понял\s+что\s+(.+)",
            r"оказывается\s+(.+)",
            r"интересно\s+что\s+(.+)",
            r"теперь\s+я\s+вижу\s+(.+)",
            r"это\s+объясняет\s+(.+)",
            r"получается\s+(.+)",
            r"значит\s+(.+)",
            r"ага\s*[,!]*\s*(.+)",
            r"блин\s*[,!]*\s+(.+)",
            r"вот\s+оно\s+что\s*[,!]*\s*(.+)"
        ]
        
        detected_insights = []
        
        for pattern in insight_patterns:
            matches = re.finditer(pattern, chat_message.lower(), re.IGNORECASE)
            
            for match in matches:
                insight_text = match.group(1).strip()
                
                if len(insight_text) > 10:  # Meaningful insights only
                    
                    # Analyze insight with AI
                    insight_analysis = await self._analyze_spontaneous_insight(
                        user_id, insight_text, chat_message
                    )
                    
                    if insight_analysis["is_meaningful"]:
                        # Find or create related questions
                        related_questions = await self._find_or_create_insight_questions(
                            insight_text, 
                            insight_analysis["domain"]
                        )
                        
                        # Create insight record
                        insight_record = {
                            "text": insight_text,
                            "trigger_context": chat_message,
                            "analysis": insight_analysis,
                            "related_questions": related_questions,
                            "capture_timestamp": datetime.now(timezone.utc).isoformat()
                        }
                        
                        detected_insights.append(insight_record)
        
        # Store significant insights
        if detected_insights:
            await self._store_spontaneous_insights(user_id, detected_insights)
            
            self.log_user_action(
                "spontaneous_insights_detected",
                user_id,
                insights_count=len(detected_insights),
                context={"insights": [i["text"] for i in detected_insights]}
            )
        
        return detected_insights
    
    async def _analyze_spontaneous_insight(self, user_id: int, insight_text: str, full_context: str) -> Dict[str, Any]:
        """
        Analyze spontaneous insight to understand its psychological significance.
        """
        
        system_prompt = """
Вы - эксперт психолог, анализирующий спонтанный инсайт пользователя.

Определите психологическую значимость инсайта и верните JSON:
{
  "is_meaningful": true/false,
  "domain": "IDENTITY/EMOTIONS/RELATIONSHIPS/WORK/MONEY/HEALTH/CREATIVITY/SPIRITUALITY/PAST/FUTURE/LIFESTYLE/THOUGHTS",
  "depth_level": "SURFACE/CONSCIOUS/EDGE",  
  "insight_type": "self_awareness/pattern_recognition/emotional_understanding/behavioral_change/value_clarification",
  "psychological_markers": {
    "self_reflection": 0.0-1.0,
    "emotional_awareness": 0.0-1.0,
    "behavioral_insight": 0.0-1.0,
    "growth_potential": 0.0-1.0
  },
  "vector_implications": {
    "dimensions_affected": ["dimension1", "dimension2"],
    "expected_changes": {"dimension1": 0.1, "dimension2": -0.2}
  },
  "significance": "low/medium/high",
  "requires_follow_up": true/false
}

Анализируйте глубоко психологические значения и паттерны.
        """
        
        messages = [{
            "role": "user", 
            "content": f"""
Инсайт пользователя: "{insight_text}"
Контекст сообщения: "{full_context}"

Проанализируйте психологическую значимость.
            """
        }]
        
        try:
            analysis_result = await ai_client_manager.generate_response(
                model=AIModel.GPT_4,  # Use GPT-4 for insight analysis
                messages=messages,
                system_prompt=system_prompt,
                max_tokens=400
            )
            
            return self._parse_json_response(analysis_result)
            
        except Exception as e:
            self.log_error("INSIGHT_ANALYSIS_ERROR", f"Failed to analyze insight: {e}", user_id)
            
            # Fallback analysis
            return {
                "is_meaningful": True,  # Conservative - assume meaningful
                "domain": "THOUGHTS",
                "depth_level": "CONSCIOUS",
                "significance": "medium",
                "confidence": 0.3
            }
    
    async def _find_or_create_insight_questions(self, insight_text: str, domain: str) -> List[Dict]:
        """
        Find existing core questions related to insight, or create virtual questions.
        """
        
        try:
            from .intelligent_questioning import intelligent_questioning
            
            # First try to find existing questions
            domain_questions = intelligent_questioning.question_core.search_questions(
                domain=domain,
                depth_level="CONSCIOUS"
            )
            
            # Use semantic similarity to find most relevant
            if domain_questions:
                # Generate embedding for insight
                insight_embedding = await self.vector_service.generate_embedding(insight_text)
                
                # Find most similar questions (simplified - in production use vector similarity)
                related_questions = domain_questions[:3]  # Top 3 from domain
                
                return related_questions
            
            # If no good matches, create virtual question
            virtual_question = await self._create_virtual_question_for_insight(insight_text, domain)
            return [virtual_question] if virtual_question else []
            
        except Exception as e:
            self.log_error("INSIGHT_QUESTIONS_ERROR", f"Failed to find related questions: {e}")
            return []
    
    async def _create_virtual_question_for_insight(self, insight_text: str, domain: str) -> Optional[Dict]:
        """
        Create virtual question that could have led to this insight.
        """
        
        system_prompt = f"""
На основе инсайта пользователя создайте психологический вопрос, который мог бы привести к такому пониманию.

Требования:
- Домен: {domain}
- Вопрос должен быть глубоким и провоцирующим размышления
- Безопасный для эмоционального состояния
- В стиле профессионального психолога

Верните JSON:
{{
  "question_text": "текст вопроса",
  "classification": {{
    "journey_stage": "EXPLORING",
    "depth_level": "CONSCIOUS/EDGE",
    "domain": "{domain}",
    "energy_dynamic": "PROCESSING"
  }},
  "psychology": {{
    "complexity": 3,
    "emotional_weight": 2,
    "safety_level": 3,
    "trust_requirement": 3
  }}
}}
        """
        
        messages = [{
            "role": "user",
            "content": f"Инсайт пользователя: '{insight_text}'"
        }]
        
        try:
            question_result = await ai_client_manager.generate_response(
                model=AIModel.CLAUDE_SONNET,  # Best model for question generation
                messages=messages,
                system_prompt=system_prompt,
                max_tokens=300
            )
            
            question_data = self._parse_json_response(question_result)
            
            # Add virtual question metadata
            question_data["id"] = f"v_{user_id}_{int(datetime.now().timestamp())}"
            question_data["source_system"] = "ai_generated_from_insight"
            question_data["is_virtual"] = True
            question_data["original_insight"] = insight_text
            
            return question_data
            
        except Exception as e:
            self.log_error("VIRTUAL_QUESTION_ERROR", f"Failed to create virtual question: {e}")
            return None
    
    async def _store_chat_insight(self, insight: ChatInsight):
        """Store chat insight in database and vector store"""
        
        # Store in PostgreSQL (would need to create table)
        insight_data = asdict(insight)
        
        # Store in vector database for semantic search
        await self.vector_service.store_insight(
            user_id=insight.user_id,
            insight_text=insight.insight_text,
            insight_type=insight.insight_type,
            metadata={
                "domain": insight.domain,
                "depth_level": insight.depth_level,
                "confidence": insight.confidence,
                "related_questions": insight.related_question_ids,
                "timestamp": insight.timestamp.isoformat()
            }
        )
        
        # Update active insights cache
        if insight.user_id not in self.active_insights:
            self.active_insights[insight.user_id] = []
        
        self.active_insights[insight.user_id].append(insight)
    
    async def _apply_insight_to_vector(self, insight: ChatInsight):
        """Apply insight impact to user's personality vector"""
        
        if insight.vector_impact:
            await self.vector_service.update_user_personality_dimensions(
                user_id=insight.user_id,
                dimension_updates=insight.vector_impact,
                source_question=f"chat_insight_{insight.timestamp.isoformat()}",
                confidence=insight.confidence
            )
    
    async def get_user_insights_summary(self, user_id: int, days: int = 7) -> Dict[str, Any]:
        """
        Get summary of user's insights over specified period.
        """
        
        user_insights = self.active_insights.get(str(user_id), [])
        
        # Filter by time period
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        recent_insights = [
            i for i in user_insights 
            if i.timestamp > cutoff_date
        ]
        
        # Categorize insights
        insights_by_domain = {}
        insights_by_type = {}
        
        for insight in recent_insights:
            domain = insight.domain
            insight_type = insight.insight_type
            
            if domain not in insights_by_domain:
                insights_by_domain[domain] = []
            insights_by_domain[domain].append(insight.insight_text)
            
            if insight_type not in insights_by_type:
                insights_by_type[insight_type] = []
            insights_by_type[insight_type].append(insight.insight_text)
        
        return {
            "total_insights": len(recent_insights),
            "insights_by_domain": insights_by_domain,
            "insights_by_type": insights_by_type,
            "average_confidence": sum(i.confidence for i in recent_insights) / len(recent_insights) if recent_insights else 0,
            "most_active_domain": max(insights_by_domain.keys(), key=lambda k: len(insights_by_domain[k])) if insights_by_domain else None
        }
    
    def _parse_json_response(self, response: str) -> Dict[str, Any]:
        """Parse JSON from AI response"""
        try:
            # Try to find JSON in response
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                return {}
        except json.JSONDecodeError:
            return {}
    
    def _parse_importance_analysis(self, response: str) -> Dict[str, Any]:
        """Parse importance analysis from AI response"""
        parsed = self._parse_json_response(response)
        
        # Ensure required fields
        return {
            "should_remember": parsed.get("should_remember", False),
            "importance_score": parsed.get("importance_score", 0.0),
            "memory_type": parsed.get("memory_type", "general"),
            "psychological_domain": parsed.get("psychological_domain", "THOUGHTS"),
            "depth_level": parsed.get("depth_level", "SURFACE"),
            "confidence": parsed.get("confidence", 0.5),
            "reasoning": parsed.get("reasoning", "No specific reason"),
            "extracted_insights": parsed.get("extracted_insights", [])
        }
    
    async def _calculate_insight_vector_impact(self, insight_text: str, analysis: Dict, related_questions: List[Dict]) -> Dict[str, float]:
        """Calculate how insight should impact personality vector"""
        
        domain = analysis["psychological_domain"]
        depth = analysis["depth_level"]
        markers = analysis.get("psychological_markers", {})
        
        # Base impact based on domain
        domain_impact_mapping = {
            "IDENTITY": {"self_awareness": 0.1, "identity_clarity": 0.1},
            "EMOTIONS": {"emotional_intelligence": 0.1, "emotional_stability": 0.05},
            "RELATIONSHIPS": {"social_skills": 0.05, "empathy": 0.1},
            "WORK": {"achievement_orientation": 0.05, "career_clarity": 0.1}
        }
        
        base_impact = domain_impact_mapping.get(domain, {"general_insight": 0.05})
        
        # Adjust by depth level
        depth_multipliers = {
            "SURFACE": 0.5,
            "CONSCIOUS": 1.0,
            "EDGE": 1.5
        }
        
        multiplier = depth_multipliers.get(depth, 1.0)
        
        # Apply psychological markers
        vector_impact = {}
        for dimension, base_value in base_impact.items():
            final_value = base_value * multiplier
            
            # Apply specific psychological markers if available
            if dimension in markers:
                final_value *= markers[dimension]
            
            vector_impact[dimension] = round(final_value, 3)
        
        return vector_impact
    
    async def _calculate_answer_correction_impact(self, question: Dict, old_analysis: Dict, new_analysis: Dict) -> Dict[str, float]:
        """Calculate vector corrections needed for answer change"""
        
        if not old_analysis or not new_analysis:
            return {}
        
        corrections = {}
        
        # Compare key psychological markers
        old_markers = old_analysis.get("personality_markers", {})
        new_markers = new_analysis.get("personality_markers", {})
        
        for marker in set(old_markers.keys()) | set(new_markers.keys()):
            old_value = old_markers.get(marker, 0.0)
            new_value = new_markers.get(marker, 0.0)
            
            difference = new_value - old_value
            if abs(difference) > 0.1:  # Significant change
                corrections[marker] = difference
        
        return corrections


# Global instance
enhanced_memory = EnhancedMemorySystem()