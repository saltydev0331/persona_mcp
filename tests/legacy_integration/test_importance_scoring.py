"""
Test the intelligent memory importance scoring system
"""

import asyncio
import sys
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from persona_mcp.memory.importance_scorer import MemoryImportanceScorer
from persona_mcp.models.database import Persona, ConversationTurn, Relationship


class ImportanceScoringTest:
    """Test memory importance scoring with various scenarios"""
    
    def __init__(self):
        self.scorer = MemoryImportanceScorer()
        
        # Create test personas with different interests
        self.wizard_persona = Persona(
            id="wizard_1",
            name="Gandalf",
            description="A wise wizard",
            topic_preferences={
                "magic": 95,
                "adventure": 80,
                "knowledge": 90,
                "danger": 75,
                "gossip": 20,
                "trade": 30
            }
        )
        
        self.merchant_persona = Persona(
            id="merchant_1", 
            name="Thorin",
            description="A shrewd merchant",
            topic_preferences={
                "trade": 95,
                "profit": 90,
                "business": 85,
                "gossip": 70,
                "magic": 40,
                "danger": 30
            }
        )
        
        # Test relationship
        self.close_relationship = Relationship(
            persona1_id="wizard_1",
            persona2_id="merchant_1",
            relationship_type="friend",
            affinity=0.85,  # Close friends (0-1 scale)
            trust=0.90
        )

    def test_emotional_content_scoring(self):
        """Test emotional content detection and scoring"""
        print("=== EMOTIONAL CONTENT SCORING ===")
        
        test_cases = [
            ("I'm devastated by this news!", "High intensity emotion"),
            ("That makes me really happy!", "Medium intensity with exclamation"),
            ("I feel quite content today.", "Low intensity emotion"),
            ("The weather is nice.", "No emotional content"),
            ("I LOVE THIS SO MUCH!!!", "Multiple intensity indicators"),
            ("I'm furious about this betrayal!", "High emotion + significance")
        ]
        
        for content, description in test_cases:
            importance = self.scorer.calculate_importance(
                content=content,
                speaker=self.wizard_persona
            )
            emotional_score = self.scorer._analyze_emotional_content(content)
            print(f"'{content}'")
            print(f"  -> Emotional: {emotional_score:.3f}, Total: {importance:.3f} ({description})")
            print()

    def test_context_significance_scoring(self):
        """Test contextual significance pattern detection"""
        print("=== CONTEXT SIGNIFICANCE SCORING ===")
        
        test_cases = [
            ("There's an emergency at the castle!", "Emergency keyword"),
            ("I have a secret to tell you.", "Secret revelation"),
            ("This is the first time I've seen magic like this.", "First time significance"),
            ("Let's make a promise to meet again.", "Promise/commitment"),
            ("We had a terrible fight yesterday.", "Conflict significance"),
            ("The weather is nice today.", "No significance patterns")
        ]
        
        for content, description in test_cases:
            importance = self.scorer.calculate_importance(
                content=content,
                speaker=self.wizard_persona
            )
            context_score = self.scorer._analyze_context_significance(content)
            print(f"'{content}'")
            print(f"  -> Context: {context_score:.3f}, Total: {importance:.3f} ({description})")
            print()

    def test_persona_interest_alignment(self):
        """Test persona interest alignment scoring"""
        print("=== PERSONA INTEREST ALIGNMENT ===")
        
        # Wizard test cases
        wizard_cases = [
            ("I discovered a new magic spell today!", "High magic interest"),
            ("The ancient knowledge contains great power.", "High knowledge interest"), 
            ("Let's discuss trade routes and profits.", "Low trade interest"),
            ("I heard some interesting gossip.", "Very low gossip interest")
        ]
        
        print("WIZARD PERSONA TESTS:")
        for content, description in wizard_cases:
            importance = self.scorer.calculate_importance(
                content=content,
                speaker=self.wizard_persona
            )
            interest_score = self.scorer._calculate_persona_interest_alignment(content, self.wizard_persona)
            print(f"'{content}'")
            print(f"  -> Interest: {interest_score:.3f}, Total: {importance:.3f} ({description})")
            print()
        
        # Merchant test cases
        merchant_cases = [
            ("I made a huge profit on this deal!", "High business/profit interest"),
            ("There's juicy gossip about the nobles.", "High gossip interest"),
            ("Magic spells are quite fascinating.", "Medium magic interest"),
            ("We're in terrible danger from dragons!", "Low danger interest")
        ]
        
        print("MERCHANT PERSONA TESTS:")
        for content, description in merchant_cases:
            importance = self.scorer.calculate_importance(
                content=content,
                speaker=self.merchant_persona
            )
            interest_score = self.scorer._calculate_persona_interest_alignment(content, self.merchant_persona)
            print(f"'{content}'")
            print(f"  -> Interest: {interest_score:.3f}, Total: {importance:.3f} ({description})")
            print()

    def test_user_engagement_scoring(self):
        """Test user engagement pattern detection"""
        print("=== USER ENGAGEMENT SCORING ===")
        
        test_cases = [
            ("What do you think about this? How does it work?", "Multiple questions"),
            ("Tell me more! Explain everything!", "Engagement + exclamations"),
            ("I completely agree with your opinion on this matter.", "Agreement + length"),
            ("Yes.", "Short, minimal engagement"),
            ("That's fascinating! How did you learn to do that? I want to know everything about magic spells and their history.", "High engagement indicators"),
        ]
        
        for content, description in test_cases:
            importance = self.scorer.calculate_importance(
                content=content,
                speaker=self.wizard_persona
            )
            engagement_score = self.scorer._analyze_user_engagement(content)
            print(f"'{content}'")
            print(f"  -> Engagement: {engagement_score:.3f}, Total: {importance:.3f} ({description})")
            print()

    def test_relationship_factor_scoring(self):
        """Test relationship significance in importance"""
        print("=== RELATIONSHIP FACTOR SCORING ===")
        
        content = "I trust you with this important secret."
        
        # Test with close relationship
        importance_close = self.scorer.calculate_importance(
            content=content,
            speaker=self.wizard_persona,
            listener=self.merchant_persona,
            relationship=self.close_relationship
        )
        
        # Test without relationship
        importance_neutral = self.scorer.calculate_importance(
            content=content,
            speaker=self.wizard_persona,
            listener=self.merchant_persona,
            relationship=None
        )
        
        print(f"Content: '{content}'")
        print(f"With close relationship: {importance_close:.3f}")
        print(f"Without relationship: {importance_neutral:.3f}")
        print(f"Relationship bonus: {importance_close - importance_neutral:.3f}")
        print()

    def test_memory_type_adjustments(self):
        """Test memory type-specific importance adjustments"""
        print("=== MEMORY TYPE ADJUSTMENTS ===")
        
        base_content = "This is important information."
        base_importance = self.scorer.calculate_importance(
            content=base_content,
            speaker=self.wizard_persona
        )
        
        memory_types = [
            ("conversation", "Standard conversation"),
            ("observation", "Passive observation"),
            ("reflection", "Internal thought"),
            ("relationship", "Relationship insight"),
            ("goal", "Goal-related memory"),
            ("secret", "Secret information"),
            ("trauma", "Traumatic event"),
            ("achievement", "Accomplishment"),
            ("routine", "Daily routine")
        ]
        
        print(f"Base importance: {base_importance:.3f}")
        print()
        
        for memory_type, description in memory_types:
            adjusted_importance = self.scorer.calculate_importance_for_memory_type(
                memory_type=memory_type,
                base_importance=base_importance
            )
            multiplier = adjusted_importance / base_importance
            print(f"{memory_type:12} -> {adjusted_importance:.3f} ({multiplier:.1f}x) - {description}")
        print()

    def test_comprehensive_scenarios(self):
        """Test comprehensive real-world scenarios"""
        print("=== COMPREHENSIVE SCENARIOS ===")
        
        scenarios = [
            {
                "content": "EMERGENCY! The dragon is attacking the village! We need to evacuate everyone now!",
                "speaker": self.wizard_persona,
                "listener": self.merchant_persona,
                "context": {"continue_score": 95, "topic": "emergency"},
                "relationship": self.close_relationship,
                "description": "High-stakes emergency with emotion, urgency, and relationship"
            },
            {
                "content": "I learned a fascinating new spell today that can transmute metals.",
                "speaker": self.wizard_persona,
                "listener": self.merchant_persona,
                "context": {"continue_score": 70, "topic": "magic"},
                "relationship": self.close_relationship,
                "description": "Magic topic aligned with wizard, moderate engagement"
            },
            {
                "content": "The grain prices have increased by 5% this month.",
                "speaker": self.merchant_persona,
                "listener": self.wizard_persona,
                "context": {"continue_score": 30, "topic": "trade"},
                "relationship": None,
                "description": "Business topic misaligned with wizard, low engagement"
            },
            {
                "content": "I'm so bored. Nothing interesting is happening.",
                "speaker": self.wizard_persona,
                "listener": None,
                "context": {"continue_score": 20, "topic": "general"},
                "relationship": None,
                "description": "Low emotion, no significance, poor engagement"
            },
            {
                "content": "I promise I'll help you find your lost family heirloom. This means everything to me.",
                "speaker": self.wizard_persona,
                "listener": self.merchant_persona,
                "context": {"continue_score": 85, "topic": "personal"},
                "relationship": self.close_relationship,
                "description": "Promise + emotional + personal + relationship significance"
            }
        ]
        
        for scenario in scenarios:
            importance = self.scorer.calculate_importance(
                content=scenario["content"],
                speaker=scenario["speaker"],
                listener=scenario.get("listener"),
                context=scenario.get("context"),
                relationship=scenario.get("relationship")
            )
            
            print(f"Scenario: {scenario['description']}")
            print(f"Content: '{scenario['content']}'")
            print(f"Importance: {importance:.3f}")
            
            # Add interpretation
            if importance >= 0.8:
                interpretation = "CRITICAL - Will be strongly retained"
            elif importance >= 0.6:
                interpretation = "HIGH - Important memory"
            elif importance >= 0.4:
                interpretation = "MEDIUM - Standard retention"
            elif importance >= 0.3:
                interpretation = "LOW - May be pruned"
            else:
                interpretation = "MINIMAL - Likely to be pruned"
            
            print(f"Interpretation: {interpretation}")
            print("-" * 60)

    def run_all_tests(self):
        """Run all importance scoring tests"""
        print("MEMORY IMPORTANCE SCORING SYSTEM TESTS")
        print("=" * 60)
        print()
        
        self.test_emotional_content_scoring()
        self.test_context_significance_scoring()
        self.test_persona_interest_alignment()
        self.test_user_engagement_scoring()
        self.test_relationship_factor_scoring()
        self.test_memory_type_adjustments()
        self.test_comprehensive_scenarios()
        
        print("✅ All importance scoring tests completed!")


if __name__ == "__main__":
    tester = ImportanceScoringTest()
    tester.run_all_tests()