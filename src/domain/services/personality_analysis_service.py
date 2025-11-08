"""Personality analysis domain service."""

from typing import Dict, List, Optional
from datetime import datetime

from ..entities import PersonalityProfile, PersonalityTrait, AssessmentResponse, ChatMessage
from ..value_objects import BigFiveTrait, PersonalityScore, TelegramId


class PersonalityAnalysisService:
    """Domain service for personality analysis operations."""
    
    def analyze_assessment_responses(
        self,
        assessment: AssessmentResponse,
        existing_profile: Optional[PersonalityProfile] = None
    ) -> PersonalityProfile:
        """Analyze assessment responses to generate personality insights."""
        
        if existing_profile:
            profile = existing_profile
        else:
            profile = PersonalityProfile.create_empty(
                user_id=assessment.user_id,
                version=1 if not existing_profile else existing_profile.version + 1
            )
        
        # Analyze scale answers to extract Big Five traits
        scale_answers = assessment.get_scale_answers()
        trait_scores = self._calculate_big_five_scores(scale_answers)
        
        # Update personality traits
        for trait_type, score_value in trait_scores.items():
            confidence = self._calculate_confidence(scale_answers, trait_type)
            score = PersonalityScore(value=score_value, confidence=confidence)
            
            trait = PersonalityTrait(
                trait=trait_type,
                score=score,
                updated_at=datetime.utcnow(),
                source=f"assessment_{assessment.assessment_type.value}"
            )
            
            profile.add_trait(trait)
        
        return profile
    
    def analyze_chat_patterns(
        self,
        messages: List[ChatMessage],
        existing_profile: Optional[PersonalityProfile] = None
    ) -> Optional[PersonalityProfile]:
        """Analyze chat patterns to update personality insights."""
        
        if not messages:
            return existing_profile
        
        # Extract personality indicators from chat content
        personality_indicators = self._extract_personality_indicators(messages)
        
        if not personality_indicators:
            return existing_profile
        
        # Update existing profile or create new one
        user_id = messages[0].user_id
        
        if existing_profile:
            profile = existing_profile
        else:
            profile = PersonalityProfile.create_empty(user_id, version=1)
        
        # Update traits based on chat analysis
        for trait_type, indicators in personality_indicators.items():
            score_value = self._calculate_trait_from_indicators(indicators)
            confidence = self._calculate_chat_confidence(indicators)
            
            if confidence > 0.3:  # Only update if we have some confidence
                score = PersonalityScore(value=score_value, confidence=confidence)
                
                trait = PersonalityTrait(
                    trait=trait_type,
                    score=score,
                    updated_at=datetime.utcnow(),
                    source="chat_analysis"
                )
                
                profile.add_trait(trait)
        
        return profile
    
    def merge_personality_profiles(
        self,
        profiles: List[PersonalityProfile]
    ) -> PersonalityProfile:
        """Merge multiple personality profiles into one comprehensive profile."""
        
        if not profiles:
            raise ValueError("Cannot merge empty profile list")
        
        if len(profiles) == 1:
            return profiles[0]
        
        # Use the latest profile as base
        base_profile = max(profiles, key=lambda p: p.updated_at)
        merged_profile = PersonalityProfile.create_empty(
            user_id=base_profile.user_id,
            version=base_profile.version + 1
        )
        
        # Merge traits from all profiles with weighted averaging
        for trait_type in BigFiveTrait:
            trait_data = []
            
            for profile in profiles:
                if trait_type in profile.traits:
                    trait = profile.traits[trait_type]
                    trait_data.append((trait.score.value, trait.score.confidence, trait.updated_at))
            
            if trait_data:
                merged_score = self._calculate_weighted_average(trait_data)
                merged_confidence = self._calculate_merged_confidence(trait_data)
                
                merged_trait = PersonalityTrait(
                    trait=trait_type,
                    score=PersonalityScore(value=merged_score, confidence=merged_confidence),
                    updated_at=datetime.utcnow(),
                    source="profile_merge"
                )
                
                merged_profile.add_trait(merged_trait)
        
        return merged_profile
    
    def _calculate_big_five_scores(self, scale_answers: Dict[str, int]) -> Dict[BigFiveTrait, float]:
        """Calculate Big Five trait scores from scale answers."""
        # This is a simplified version - in reality, you'd have a proper mapping
        # of questions to traits and validated scoring algorithms
        
        trait_scores = {}
        
        # Example mapping - this would be much more sophisticated in reality
        question_mappings = {
            "openness": ["q1", "q6", "q11"],
            "conscientiousness": ["q2", "q7", "q12"], 
            "extraversion": ["q3", "q8", "q13"],
            "agreeableness": ["q4", "q9", "q14"],
            "neuroticism": ["q5", "q10", "q15"]
        }
        
        for trait_name, question_ids in question_mappings.items():
            trait_type = BigFiveTrait(trait_name)
            
            # Calculate average score for trait questions
            scores = [scale_answers.get(qid, 3) for qid in question_ids if qid in scale_answers]
            if scores:
                # Normalize to 0-1 range (assuming 1-5 scale)
                avg_score = sum(scores) / len(scores)
                normalized_score = (avg_score - 1) / 4  # Convert 1-5 to 0-1
                trait_scores[trait_type] = min(max(normalized_score, 0.0), 1.0)
        
        return trait_scores
    
    def _calculate_confidence(self, scale_answers: Dict[str, int], trait: BigFiveTrait) -> float:
        """Calculate confidence score for a trait based on answer consistency."""
        # Simplified confidence calculation
        # In reality, this would consider answer patterns, response times, etc.
        return 0.8  # Placeholder
    
    def _extract_personality_indicators(
        self,
        messages: List[ChatMessage]
    ) -> Dict[BigFiveTrait, List[Dict]]:
        """Extract personality indicators from chat messages."""
        # Simplified version - in reality, this would use NLP and ML
        indicators = {trait: [] for trait in BigFiveTrait}
        
        for message in messages:
            if message.is_user_message:
                content = message.content.lower()
                
                # Simple keyword-based analysis (would be much more sophisticated)
                if any(word in content for word in ["creative", "new", "art", "idea"]):
                    indicators[BigFiveTrait.OPENNESS].append({
                        "type": "keyword",
                        "strength": 0.3,
                        "timestamp": message.timestamp
                    })
                
                if any(word in content for word in ["organized", "plan", "schedule"]):
                    indicators[BigFiveTrait.CONSCIENTIOUSNESS].append({
                        "type": "keyword",
                        "strength": 0.3,
                        "timestamp": message.timestamp
                    })
                
                # Add more sophisticated analysis here...
        
        return indicators
    
    def _calculate_trait_from_indicators(self, indicators: List[Dict]) -> float:
        """Calculate trait score from personality indicators."""
        if not indicators:
            return 0.5  # Neutral score
        
        # Simple weighted average
        total_strength = sum(ind["strength"] for ind in indicators)
        return min(max(total_strength / len(indicators), 0.0), 1.0)
    
    def _calculate_chat_confidence(self, indicators: List[Dict]) -> float:
        """Calculate confidence from chat indicators."""
        if not indicators:
            return 0.0
        
        # Confidence based on number and recency of indicators
        base_confidence = min(len(indicators) * 0.1, 0.5)
        return base_confidence
    
    def _calculate_weighted_average(self, trait_data: List[tuple]) -> float:
        """Calculate weighted average of trait scores."""
        total_weighted = sum(score * confidence for score, confidence, _ in trait_data)
        total_weight = sum(confidence for _, confidence, _ in trait_data)
        
        if total_weight == 0:
            return 0.5
        
        return total_weighted / total_weight
    
    def _calculate_merged_confidence(self, trait_data: List[tuple]) -> float:
        """Calculate merged confidence score."""
        confidences = [confidence for _, confidence, _ in trait_data]
        return min(sum(confidences) / len(confidences), 1.0)