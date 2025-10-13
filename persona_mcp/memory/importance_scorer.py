"""
Smart memory importance scoring system

Calculates memory importance based on multiple factors:
- Conversation context and engagement
- Emotional content and intensity  
- Persona interests alignment
- User engagement signals
- Temporal factors (recency, time of day)
- Relationship significance
"""

import re
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import math

from ..models import Persona, Memory, Relationship, ConversationTurn


class MemoryImportanceScorer:
    """Intelligent memory importance scoring system"""
    
    def __init__(self):
        # Emotional intensity keywords and scores
        self.emotion_keywords = {
            # High intensity emotions (0.8-1.0)
            "love": 0.9, "hate": 0.9, "furious": 0.95, "ecstatic": 0.9,
            "devastated": 0.9, "thrilled": 0.85, "terrified": 0.9,
            "overjoyed": 0.85, "enraged": 0.9, "heartbroken": 0.9,
            
            # Medium intensity emotions (0.5-0.8) 
            "happy": 0.6, "sad": 0.6, "angry": 0.7, "excited": 0.7,
            "worried": 0.6, "surprised": 0.65, "disappointed": 0.6,
            "anxious": 0.7, "proud": 0.7, "embarrassed": 0.65,
            
            # Low intensity emotions (0.2-0.5)
            "content": 0.4, "curious": 0.4, "tired": 0.3, "bored": 0.2,
            "interested": 0.5, "confused": 0.4, "amused": 0.4
        }
        
        # Context significance patterns
        self.significance_patterns = {
            # Very high significance (0.8-1.0)
            r'\b(emergency|urgent|crisis|death|born|married|divorced)\b': 0.9,
            r'\b(secret|confession|betrayal|revelation|discovered)\b': 0.85,
            r'\b(first time|never again|last chance|forever)\b': 0.8,
            
            # High significance (0.6-0.8)
            r'\b(important|significant|critical|serious|major)\b': 0.7,
            r'\b(promise|swear|vow|commitment|decision)\b': 0.7,
            r'\b(fight|argument|conflict|disagreement)\b': 0.65,
            
            # Medium significance (0.4-0.6)
            r'\b(interesting|unusual|strange|weird|funny)\b': 0.5,
            r'\b(plan|idea|suggestion|proposal)\b': 0.5,
            r'\b(remember|forget|recall|remind)\b': 0.45,
            
            # Topic-specific significance
            r'\b(magic|spell|enchant|wizard|dragon|artifact)\b': 0.6,  # Fantasy
            r'\b(business|trade|profit|loss|money)\b': 0.55,  # Commerce
            r'\b(family|friend|enemy|ally|relationship)\b': 0.6  # Social
        }
        
        # Conversation quality indicators
        self.engagement_patterns = {
            r'\?': 0.1,  # Questions show engagement
            r'!': 0.05,  # Exclamations show emotion
            r'\b(tell me|explain|describe|how|why|what|when|where)\b': 0.15,  # Information seeking
            r'\b(agree|disagree|think|feel|believe|opinion)\b': 0.1  # Opinion sharing
        }

    def calculate_importance(
        self,
        content: str,
        speaker: Persona,
        listener: Optional[Persona] = None,
        context: Optional[Dict[str, Any]] = None,
        turn: Optional[ConversationTurn] = None,
        relationship: Optional[Relationship] = None
    ) -> float:
        """
        Calculate comprehensive importance score (0.0 to 1.0)
        
        Scoring breakdown:
        - Base engagement: 0.3 (everyone gets minimum importance)
        - Emotional content: 0.0-0.25 (high emotions = more important)
        - Context significance: 0.0-0.2 (keywords, patterns, urgency)
        - Persona interests: 0.0-0.15 (alignment with speaker's interests)
        - User engagement: 0.0-0.1 (questions, responses, interaction quality)
        - Relationship factor: 0.0-0.1 (stronger relationships = more important)
        - Recency bonus: 0.0-0.05 (recent memories slightly more important)
        """
        
        # Start with base importance
        importance = 0.3
        
        # 1. Emotional content analysis (0.0-0.25)
        emotional_score = self._analyze_emotional_content(content)
        importance += emotional_score * 0.25
        
        # 2. Context significance analysis (0.0-0.2) 
        context_score = self._analyze_context_significance(content, context)
        importance += context_score * 0.2
        
        # 3. Persona interest alignment (0.0-0.15)
        if speaker:
            interest_score = self._calculate_persona_interest_alignment(content, speaker)
            importance += interest_score * 0.15
        
        # 4. User engagement signals (0.0-0.1)
        engagement_score = self._analyze_user_engagement(content, turn)
        importance += engagement_score * 0.1
        
        # 5. Relationship significance (0.0-0.1)
        if relationship and listener:
            relationship_score = self._calculate_relationship_factor(relationship, speaker, listener)
            importance += relationship_score * 0.1
        
        # 6. Recency bonus (0.0-0.05)
        recency_score = self._calculate_recency_bonus()
        importance += recency_score * 0.05
        
        # Ensure score stays within bounds
        return max(0.1, min(1.0, importance))

    def _analyze_emotional_content(self, content: str) -> float:
        """Analyze emotional intensity in content (returns 0.0-1.0)"""
        content_lower = content.lower()
        max_emotion_score = 0.0
        
        # Check for emotion keywords
        for emotion, score in self.emotion_keywords.items():
            if emotion in content_lower:
                max_emotion_score = max(max_emotion_score, score)
        
        # Check for emotional punctuation patterns
        exclamation_count = content.count('!')
        if exclamation_count >= 3:
            max_emotion_score = max(max_emotion_score, 0.8)
        elif exclamation_count >= 2:
            max_emotion_score = max(max_emotion_score, 0.6)
        elif exclamation_count >= 1:
            max_emotion_score = max(max_emotion_score, 0.4)
        
        # Check for ALL CAPS (intensity indicator)
        caps_ratio = sum(1 for c in content if c.isupper()) / max(len(content), 1)
        if caps_ratio > 0.3:  # More than 30% caps
            max_emotion_score = max(max_emotion_score, 0.7)
        elif caps_ratio > 0.1:  # More than 10% caps
            max_emotion_score = max(max_emotion_score, 0.4)
        
        return max_emotion_score

    def _analyze_context_significance(self, content: str, context: Optional[Dict[str, Any]] = None) -> float:
        """Analyze contextual significance patterns (returns 0.0-1.0)"""
        content_lower = content.lower()
        max_significance = 0.0
        
        # Check significance patterns
        for pattern, score in self.significance_patterns.items():
            if re.search(pattern, content_lower):
                max_significance = max(max_significance, score)
        
        # Context-based adjustments
        if context:
            # High continue score indicates engaging conversation
            continue_score = context.get('continue_score', 50)
            if continue_score >= 80:
                max_significance = max(max_significance, 0.7)
            elif continue_score >= 60:
                max_significance = max(max_significance, 0.5)
            
            # Conversation topic relevance
            topic = context.get('topic', '').lower()
            if topic in ['crisis', 'emergency', 'important', 'secret']:
                max_significance = max(max_significance, 0.8)
            elif topic in ['personal', 'relationship', 'family']:
                max_significance = max(max_significance, 0.6)
        
        return max_significance

    def _calculate_persona_interest_alignment(self, content: str, speaker: Persona) -> float:
        """Calculate how well content aligns with persona interests (returns 0.0-1.0)"""
        if not hasattr(speaker, 'topic_preferences') or not speaker.topic_preferences:
            return 0.5  # Default moderate interest
        
        content_lower = content.lower()
        max_alignment = 0.0
        
        # Check each topic preference
        for topic, preference_score in speaker.topic_preferences.items():
            topic_lower = topic.lower()
            
            # Check if topic appears in content
            if topic_lower in content_lower:
                # Convert preference score (typically 0-100) to 0-1 scale
                normalized_preference = min(preference_score / 100.0, 1.0)
                max_alignment = max(max_alignment, normalized_preference)
        
        # If no specific topic match, check general interests
        if max_alignment == 0.0:
            # Default alignment based on persona personality traits
            if hasattr(speaker, 'personality_traits') and speaker.personality_traits:
                if 'curious' in speaker.personality_traits:
                    max_alignment = 0.6
                elif 'social' in speaker.personality_traits:
                    max_alignment = 0.5
                else:
                    max_alignment = 0.4
            else:
                max_alignment = 0.5
        
        return max_alignment

    def _analyze_user_engagement(self, content: str, turn: Optional[ConversationTurn] = None) -> float:
        """Analyze user engagement indicators (returns 0.0-1.0)"""
        engagement_score = 0.0
        content_lower = content.lower()
        
        # Check engagement patterns
        for pattern, score in self.engagement_patterns.items():
            matches = len(re.findall(pattern, content_lower))
            engagement_score += matches * score
        
        # Length indicates engagement (longer responses = more engaged)
        word_count = len(content.split())
        if word_count >= 50:
            engagement_score += 0.3
        elif word_count >= 20:
            engagement_score += 0.2
        elif word_count >= 10:
            engagement_score += 0.1
        
        # Turn-specific factors
        if turn:
            # High continue score indicates engagement
            if hasattr(turn, 'continue_score'):
                if turn.continue_score >= 70:
                    engagement_score += 0.2
                elif turn.continue_score >= 50:
                    engagement_score += 0.1
            
            # Response quality
            if hasattr(turn, 'response_type'):
                if turn.response_type == 'creative':
                    engagement_score += 0.15
                elif turn.response_type == 'detailed':
                    engagement_score += 0.1
        
        return min(engagement_score, 1.0)

    def _calculate_relationship_factor(self, relationship: Relationship, speaker: Persona, listener: Persona) -> float:
        """Calculate relationship significance factor (returns 0.0-1.0)"""
        if not relationship:
            return 0.3  # Neutral relationship
        
        # Strong relationships make memories more important
        affinity = getattr(relationship, 'affinity', 0.0)
        trust = getattr(relationship, 'trust', 0.0)
        
        # Normalize scores (already on 0-1 scale)
        affinity_normalized = max(0, min(affinity, 1.0))
        trust_normalized = max(0, min(trust, 1.0))
        
        # Combined relationship strength
        relationship_strength = (affinity_normalized + trust_normalized) / 2
        
        # Both very positive and very negative relationships are important
        if relationship_strength >= 0.8 or relationship_strength <= 0.2:
            return 0.9
        elif relationship_strength >= 0.6 or relationship_strength <= 0.4:
            return 0.7
        else:
            return 0.5

    def _calculate_recency_bonus(self) -> float:
        """Calculate recency bonus for new memories (returns 0.0-1.0)"""
        # Recent memories get slight importance boost
        # This encourages retention of fresh information
        return 1.0  # All new memories get full recency bonus

    def calculate_importance_for_memory_type(
        self,
        memory_type: str,
        base_importance: float
    ) -> float:
        """Apply memory type-specific adjustments to importance score"""
        
        type_multipliers = {
            'conversation': 1.0,      # Standard conversations
            'observation': 0.8,       # Things the persona noticed
            'reflection': 1.2,        # Persona's internal thoughts
            'relationship': 1.3,      # Relationship changes/insights
            'goal': 1.4,              # Goal-related memories
            'secret': 1.5,            # Secret information
            'trauma': 1.6,            # Traumatic/significant events
            'achievement': 1.3,       # Accomplishments
            'learning': 1.1,          # New knowledge/skills
            'routine': 0.6            # Daily routine activities
        }
        
        multiplier = type_multipliers.get(memory_type, 1.0)
        adjusted_importance = base_importance * multiplier
        
        return max(0.1, min(1.0, adjusted_importance))

    def get_importance_explanation(self, importance_score: float, factors: Dict[str, float]) -> str:
        """Generate human-readable explanation of importance score"""
        
        explanations = []
        
        if importance_score >= 0.9:
            explanations.append("Extremely important")
        elif importance_score >= 0.7:
            explanations.append("High importance") 
        elif importance_score >= 0.5:
            explanations.append("Moderate importance")
        elif importance_score >= 0.3:
            explanations.append("Low importance")
        else:
            explanations.append("Minimal importance")
        
        # Add factor explanations
        if factors.get('emotional', 0) >= 0.2:
            explanations.append("strong emotional content")
        if factors.get('context', 0) >= 0.15:
            explanations.append("significant context")
        if factors.get('interests', 0) >= 0.12:
            explanations.append("aligns with interests")
        if factors.get('engagement', 0) >= 0.08:
            explanations.append("high user engagement")
        if factors.get('relationship', 0) >= 0.08:
            explanations.append("important relationship")
        
        return " - " + ", ".join(explanations) if explanations else f"Score: {importance_score:.2f}"