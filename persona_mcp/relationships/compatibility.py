"""
Compatibility Engine for Persona Relationship Analysis

Calculates compatibility between personas based on personality traits,
interaction history, and behavioral patterns.
"""

from typing import Dict, List, Optional, Tuple, Any
from ..models import PersonaBase, Relationship, RelationshipType
from ..logging import get_logger
import math


class CompatibilityEngine:
    """Analyzes and calculates compatibility between personas"""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        
        # Personality trait weights for compatibility calculation
        self.trait_weights = {
            "openness": 0.2,
            "conscientiousness": 0.15,
            "extraversion": 0.25,
            "agreeableness": 0.25,
            "neuroticism": -0.15  # Negative weight - lower neuroticism is better for compatibility
        }
    
    def calculate_personality_compatibility(self, persona1: PersonaBase, persona2: PersonaBase) -> float:
        """Calculate compatibility based on personality traits (0.0 to 1.0)"""
        try:
            traits1 = persona1.personality_traits
            traits2 = persona2.personality_traits
            
            if not traits1 or not traits2:
                return 0.5  # Neutral compatibility if no trait data
            
            compatibility_factors = {}
            total_score = 0.0
            total_weight = 0.0
            
            # Compare each personality dimension
            for trait, weight in self.trait_weights.items():
                if trait in traits1 and trait in traits2:
                    value1 = float(traits1.get(trait, 0.5))
                    value2 = float(traits2.get(trait, 0.5))
                    
                    # Calculate compatibility for this trait
                    if trait == "neuroticism":
                        # For neuroticism, lower values are better, and similarity is good
                        trait_compatibility = 1.0 - abs(value1 - value2) - (max(value1, value2) * 0.3)
                    elif trait == "extraversion":
                        # Moderate complementarity can be good (not too different, not identical)
                        diff = abs(value1 - value2)
                        trait_compatibility = 1.0 - (diff * 0.7) if diff < 0.5 else 1.0 - diff
                    else:
                        # For most traits, similarity is good
                        trait_compatibility = 1.0 - abs(value1 - value2)
                    
                    trait_compatibility = max(0.0, min(1.0, trait_compatibility))
                    compatibility_factors[trait] = trait_compatibility
                    
                    total_score += trait_compatibility * abs(weight)
                    total_weight += abs(weight)
            
            # Calculate overall personality compatibility
            if total_weight > 0:
                personality_compatibility = total_score / total_weight
            else:
                personality_compatibility = 0.5
            
            self.logger.debug(f"Personality compatibility: {personality_compatibility:.3f} for {persona1.name} <-> {persona2.name}")
            return max(0.0, min(1.0, personality_compatibility))
            
        except Exception as e:
            self.logger.error(f"Error calculating personality compatibility: {e}")
            return 0.5
    
    def calculate_social_compatibility(self, persona1: PersonaBase, persona2: PersonaBase) -> float:
        """Calculate compatibility based on social attributes"""
        try:
            # Charisma interaction - high charisma personas work well together or with anyone
            charisma_factor = (persona1.charisma + persona2.charisma) / 40.0  # Max 20+20=40
            charisma_factor = min(1.0, charisma_factor)
            
            # Intelligence compatibility - some difference can be stimulating
            intel_diff = abs(persona1.intelligence - persona2.intelligence)
            if intel_diff <= 3:
                intel_factor = 1.0  # Similar intelligence - great
            elif intel_diff <= 6:
                intel_factor = 0.8  # Some difference - still good
            else:
                intel_factor = 0.5  # Large gap - potential issues
            
            # Social rank compatibility - consider class dynamics
            rank_compatibility = self._calculate_rank_compatibility(persona1.social_rank, persona2.social_rank)
            
            # Combine factors
            social_compatibility = (charisma_factor * 0.4 + intel_factor * 0.4 + rank_compatibility * 0.2)
            
            self.logger.debug(f"Social compatibility: {social_compatibility:.3f} for {persona1.name} <-> {persona2.name}")
            return max(0.0, min(1.0, social_compatibility))
            
        except Exception as e:
            self.logger.error(f"Error calculating social compatibility: {e}")
            return 0.5
    
    def calculate_interest_compatibility(self, persona1: PersonaBase, persona2: PersonaBase) -> float:
        """Calculate compatibility based on shared interests/topic preferences"""
        try:
            interests1 = persona1.topic_preferences
            interests2 = persona2.topic_preferences
            
            if not interests1 or not interests2:
                return 0.5  # Neutral if no interest data
            
            # Find common topics
            common_topics = set(interests1.keys()) & set(interests2.keys())
            if not common_topics:
                return 0.3  # Low compatibility if no shared interests
            
            # Calculate weighted similarity for shared interests
            total_similarity = 0.0
            total_weight = 0.0
            
            for topic in common_topics:
                interest1 = interests1[topic]
                interest2 = interests2[topic]
                
                # Both need to have some interest (> 20) for positive compatibility
                if interest1 > 20 and interest2 > 20:
                    # Similarity in interest level
                    similarity = 1.0 - abs(interest1 - interest2) / 100.0
                    # Weight by average interest level
                    weight = (interest1 + interest2) / 200.0
                    
                    total_similarity += similarity * weight
                    total_weight += weight
            
            if total_weight > 0:
                interest_compatibility = total_similarity / total_weight
            else:
                interest_compatibility = 0.3
            
            # Bonus for having many shared interests
            shared_ratio = len(common_topics) / max(len(interests1), len(interests2))
            interest_compatibility += shared_ratio * 0.2
            
            self.logger.debug(f"Interest compatibility: {interest_compatibility:.3f} for {persona1.name} <-> {persona2.name}")
            return max(0.0, min(1.0, interest_compatibility))
            
        except Exception as e:
            self.logger.error(f"Error calculating interest compatibility: {e}")
            return 0.5
    
    def calculate_overall_compatibility(self, persona1: PersonaBase, persona2: PersonaBase, 
                                     relationship: Optional[Relationship] = None) -> Dict[str, float]:
        """Calculate comprehensive compatibility analysis"""
        try:
            # Calculate component compatibilities
            personality_compat = self.calculate_personality_compatibility(persona1, persona2)
            social_compat = self.calculate_social_compatibility(persona1, persona2)
            interest_compat = self.calculate_interest_compatibility(persona1, persona2)
            
            # Relationship history factor
            history_factor = 0.5  # Default neutral
            if relationship:
                # Use existing relationship strength as history factor
                history_factor = max(0.0, min(1.0, (relationship.get_relationship_strength() + 1.0) / 2.0))
            
            # Weighted overall compatibility
            overall_compatibility = (
                personality_compat * 0.35 +
                social_compat * 0.25 +
                interest_compat * 0.25 +
                history_factor * 0.15
            )
            
            compatibility_analysis = {
                "overall": round(overall_compatibility, 3),
                "personality": round(personality_compat, 3),
                "social": round(social_compat, 3),
                "interests": round(interest_compat, 3),
                "history": round(history_factor, 3),
                "prediction": self._get_compatibility_prediction(overall_compatibility)
            }
            
            self.logger.info(f"Overall compatibility analysis: {compatibility_analysis['overall']:.3f} for {persona1.name} <-> {persona2.name}")
            return compatibility_analysis
            
        except Exception as e:
            self.logger.error(f"Error calculating overall compatibility: {e}")
            return {
                "overall": 0.5,
                "personality": 0.5,
                "social": 0.5,
                "interests": 0.5,
                "history": 0.5,
                "prediction": "neutral",
                "error": str(e)
            }
    
    def suggest_interaction_approach(self, persona1: PersonaBase, persona2: PersonaBase,
                                   compatibility_analysis: Dict[str, float]) -> Dict[str, Any]:
        """Suggest how personas should interact based on compatibility"""
        try:
            overall_compat = compatibility_analysis["overall"]
            suggestions = {
                "interaction_style": "",
                "recommended_topics": [],
                "potential_challenges": [],
                "relationship_potential": "",
                "interaction_frequency": "moderate"
            }
            
            # Determine interaction style
            if overall_compat > 0.8:
                suggestions["interaction_style"] = "collaborative_enthusiastic"
                suggestions["relationship_potential"] = "excellent_friends"
                suggestions["interaction_frequency"] = "frequent"
            elif overall_compat > 0.6:
                suggestions["interaction_style"] = "friendly_engaging"
                suggestions["relationship_potential"] = "good_friends"
                suggestions["interaction_frequency"] = "regular"
            elif overall_compat > 0.4:
                suggestions["interaction_style"] = "respectful_cautious"
                suggestions["relationship_potential"] = "cordial_acquaintances"
                suggestions["interaction_frequency"] = "occasional"
            else:
                suggestions["interaction_style"] = "formal_distant"
                suggestions["relationship_potential"] = "professional_only"
                suggestions["interaction_frequency"] = "minimal"
            
            # Recommend topics based on shared interests
            suggestions["recommended_topics"] = self._find_shared_topics(persona1, persona2)
            
            # Identify potential challenges
            suggestions["potential_challenges"] = self._identify_compatibility_challenges(
                persona1, persona2, compatibility_analysis
            )
            
            return suggestions
            
        except Exception as e:
            self.logger.error(f"Error generating interaction suggestions: {e}")
            return {"error": str(e)}
    
    def _calculate_rank_compatibility(self, rank1: str, rank2: str) -> float:
        """Calculate compatibility based on social ranks"""
        # Define rank hierarchy and compatibility matrix
        rank_hierarchy = {
            "noble": 4,
            "merchant": 3,
            "artisan": 2,
            "commoner": 1,
            "peasant": 0
        }
        
        rank1_level = rank_hierarchy.get(rank1, 1)
        rank2_level = rank_hierarchy.get(rank2, 1)
        
        # Calculate compatibility based on rank difference
        rank_diff = abs(rank1_level - rank2_level)
        
        if rank_diff == 0:
            return 1.0  # Same rank - perfect compatibility
        elif rank_diff == 1:
            return 0.8  # Adjacent ranks - good compatibility
        elif rank_diff == 2:
            return 0.6  # Two levels apart - some friction
        else:
            return 0.3  # Large gap - potential class conflict
    
    def _find_shared_topics(self, persona1: PersonaBase, persona2: PersonaBase) -> List[str]:
        """Find topics both personas are interested in"""
        interests1 = persona1.topic_preferences or {}
        interests2 = persona2.topic_preferences or {}
        
        shared_topics = []
        for topic in set(interests1.keys()) & set(interests2.keys()):
            if interests1[topic] > 30 and interests2[topic] > 30:  # Both moderately interested
                shared_topics.append(topic)
        
        # Sort by combined interest level
        shared_topics.sort(key=lambda t: interests1[t] + interests2[t], reverse=True)
        return shared_topics[:5]  # Top 5 shared interests
    
    def _identify_compatibility_challenges(self, persona1: PersonaBase, persona2: PersonaBase,
                                         compatibility_analysis: Dict[str, float]) -> List[str]:
        """Identify potential relationship challenges"""
        challenges = []
        
        if compatibility_analysis["personality"] < 0.4:
            challenges.append("personality_clash")
        
        if compatibility_analysis["social"] < 0.4:
            challenges.append("social_mismatch")
        
        if compatibility_analysis["interests"] < 0.3:
            challenges.append("few_shared_interests")
        
        # Check specific trait conflicts
        traits1 = persona1.personality_traits or {}
        traits2 = persona2.personality_traits or {}
        
        if traits1.get("neuroticism", 0.5) > 0.7 or traits2.get("neuroticism", 0.5) > 0.7:
            challenges.append("high_stress_potential")
        
        if abs(traits1.get("extraversion", 0.5) - traits2.get("extraversion", 0.5)) > 0.6:
            challenges.append("energy_level_mismatch")
        
        return challenges
    
    def _get_compatibility_prediction(self, overall_compatibility: float) -> str:
        """Get text prediction based on compatibility score"""
        if overall_compatibility > 0.8:
            return "excellent"
        elif overall_compatibility > 0.65:
            return "very_good"
        elif overall_compatibility > 0.5:
            return "good"
        elif overall_compatibility > 0.35:
            return "challenging"
        else:
            return "difficult"