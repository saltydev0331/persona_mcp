"""
Integration tests for the relationship management system.

Tests the complete relationship workflow from persona interactions
to relationship evolution and compatibility analysis.
"""

import pytest
import asyncio
from datetime import datetime, timezone
from typing import Dict, List, Any

from persona_mcp.database import get_db_session
from persona_mcp.models import Persona, Relationship, RelationshipType, EmotionalState
from persona_mcp.relationships.manager import RelationshipManager
from persona_mcp.relationships.compatibility import CompatibilityEngine


class TestRelationshipsIntegration:
    """Integration tests for the complete relationship system"""
    
    @pytest.fixture(autouse=True)
    async def setup_test_data(self, test_db):
        """Set up test personas and basic relationships"""
        
        async with get_db_session() as session:
            # Create test personas with different personalities
            self.alice = Persona(
                id="alice_test",
                name="Alice",
                description="A cheerful and optimistic software engineer",
                background="A cheerful and optimistic software engineer who loves learning new technologies.",
                traits=["curious", "collaborative", "detail-oriented"],
                interests=["programming", "books", "hiking"],
                personality_scores={"openness": 0.8, "conscientiousness": 0.7, "extraversion": 0.6, "agreeableness": 0.8, "neuroticism": 0.3}
            )
            
            self.bob = Persona(
                id="bob_test", 
                name="Bob",
                description="A practical and methodical data analyst",
                background="A practical and methodical data analyst who prefers structured approaches.",
                traits=["analytical", "patient", "systematic"],
                interests=["data", "statistics", "chess"],
                personality_scores={"openness": 0.6, "conscientiousness": 0.9, "extraversion": 0.4, "agreeableness": 0.7, "neuroticism": 0.2}
            )
            
            self.charlie = Persona(
                id="charlie_test",
                name="Charlie",
                description="A creative and spontaneous artist",
                background="A creative and spontaneous artist who thinks outside the box.",
                traits=["creative", "spontaneous", "passionate"],
                interests=["art", "music", "travel"],
                personality_scores={"openness": 0.9, "conscientiousness": 0.4, "extraversion": 0.8, "agreeableness": 0.6, "neuroticism": 0.6}
            )
            
            session.add_all([self.alice, self.bob, self.charlie])
            await session.commit()
            
        # Initialize relationship manager
        async with get_db_session() as session:
            self.relationship_manager = RelationshipManager(session)
            self.compatibility_engine = CompatibilityEngine()

    async def test_relationship_creation_and_evolution(self):
        """Test creating relationships and watching them evolve through interactions"""
        
        async with get_db_session() as session:
            relationship_manager = RelationshipManager(session)
            
            # Initially no relationship exists
            relationship = await relationship_manager.get_relationship("alice_test", "bob_test")
            assert relationship is None
            
            # Process first interaction - positive
            success = await relationship_manager.process_interaction(
                "alice_test", "bob_test", 
                interaction_quality=0.7,  # Good interaction
                duration_minutes=15.0,
                context="collaborative_work"
            )
            assert success
            
            # Check relationship was created
            relationship = await relationship_manager.get_relationship("alice_test", "bob_test")
            assert relationship is not None
            assert relationship.persona1_id == "alice_test"
            assert relationship.persona2_id == "bob_test"
            assert relationship.interaction_count == 1
            assert relationship.total_interaction_time == 15.0
            assert relationship.affinity > 0.5  # Should be positive
            assert relationship.trust > 0.5
            
            # Process more positive interactions
            for i in range(5):
                await relationship_manager.process_interaction(
                    "alice_test", "bob_test",
                    interaction_quality=0.6 + (i * 0.05),  # Gradually improving
                    duration_minutes=10.0,
                    context=f"session_{i+2}"
                )
            
            # Check relationship evolution
            updated_relationship = await relationship_manager.get_relationship("alice_test", "bob_test")
            assert updated_relationship.interaction_count == 6
            assert updated_relationship.affinity > relationship.affinity  # Should improve
            assert updated_relationship.trust > relationship.trust
            assert updated_relationship.get_compatibility_score() > 0.6
            
            # Check relationship type progression
            relationship_strength = updated_relationship.get_relationship_strength()
            assert relationship_strength > 0.5

    async def test_negative_interaction_impact(self):
        """Test how negative interactions affect relationships"""
        
        async with get_db_session() as session:
            relationship_manager = RelationshipManager(session)
            
            # Start with positive interaction
            await relationship_manager.process_interaction(
                "alice_test", "charlie_test",
                interaction_quality=0.8,
                duration_minutes=20.0,
                context="initial_meeting"
            )
            
            initial_relationship = await relationship_manager.get_relationship("alice_test", "charlie_test")
            initial_affinity = initial_relationship.affinity
            
            # Process several negative interactions
            for i in range(3):
                await relationship_manager.process_interaction(
                    "alice_test", "charlie_test",
                    interaction_quality=-0.4,  # Negative interaction
                    duration_minutes=5.0,
                    context="conflict"
                )
            
            # Check degradation
            updated_relationship = await relationship_manager.get_relationship("alice_test", "charlie_test")
            assert updated_relationship.affinity < initial_affinity
            assert updated_relationship.trust < initial_relationship.trust
            
            # Relationship should still exist but be weaker
            assert updated_relationship.get_relationship_strength() < initial_relationship.get_relationship_strength()

    async def test_compatibility_analysis(self):
        """Test comprehensive compatibility analysis between personas"""
        
        async with get_db_session() as session:
            relationship_manager = RelationshipManager(session)
            
            # Test compatibility between Alice (collaborative) and Bob (systematic)
            compatibility = self.compatibility_engine.calculate_overall_compatibility(
                self.alice, self.bob, None  # No existing relationship
            )
            
            # Should have moderate compatibility
            assert 0.4 <= compatibility["overall_score"] <= 0.8
            
            # Check specific compatibility factors
            assert "personality_compatibility" in compatibility
            assert "social_compatibility" in compatibility  
            assert "interest_compatibility" in compatibility
            
            # Test interaction suggestions
            suggestions = self.compatibility_engine.suggest_interaction_approach(
                self.alice, self.bob, compatibility
            )
            
            assert "recommended_approach" in suggestions
            assert "conversation_topics" in suggestions
            assert "potential_challenges" in suggestions
            assert len(suggestions["conversation_topics"]) > 0

    async def test_emotional_state_management(self):
        """Test emotional state creation and updates"""
        
        async with get_db_session() as session:
            relationship_manager = RelationshipManager(session)
            
            # Get initial emotional state (should be created if doesn't exist)
            emotional_state = await relationship_manager.get_emotional_state("alice_test")
            assert emotional_state is not None
            assert emotional_state.persona_id == "alice_test"
            assert 0.0 <= emotional_state.mood <= 1.0
            assert 0.0 <= emotional_state.energy_level <= 1.0
            
            # Update emotional state
            emotional_state.mood = 0.8
            emotional_state.energy_level = 0.9
            emotional_state.social_battery = 0.7
            
            success = await relationship_manager.update_emotional_state(emotional_state)
            assert success
            
            # Verify update
            updated_state = await relationship_manager.get_emotional_state("alice_test")
            assert updated_state.mood == 0.8
            assert updated_state.energy_level == 0.9
            assert updated_state.social_battery == 0.7

    async def test_relationship_statistics(self):
        """Test relationship statistics gathering"""
        
        async with get_db_session() as session:
            relationship_manager = RelationshipManager(session)
            
            # Create some relationships
            await relationship_manager.process_interaction("alice_test", "bob_test", 0.8, 15.0, "work")
            await relationship_manager.process_interaction("bob_test", "charlie_test", 0.3, 10.0, "casual")
            await relationship_manager.process_interaction("alice_test", "charlie_test", -0.2, 5.0, "conflict")
            
            # Get statistics
            stats = await relationship_manager.get_relationship_stats()
            
            assert "total_relationships" in stats
            assert "relationship_types" in stats
            assert "average_compatibility" in stats
            assert "total_interactions" in stats
            
            assert stats["total_relationships"] >= 3
            assert stats["total_interactions"] >= 3
            assert isinstance(stats["relationship_types"], dict)

    async def test_persona_relationship_listing(self):
        """Test listing all relationships for a specific persona"""
        
        async with get_db_session() as session:
            relationship_manager = RelationshipManager(session)
            
            # Create relationships for Alice
            await relationship_manager.process_interaction("alice_test", "bob_test", 0.7, 20.0, "collaboration")
            await relationship_manager.process_interaction("alice_test", "charlie_test", 0.4, 15.0, "social")
            
            # Get Alice's relationships
            relationships = await relationship_manager.get_persona_relationships("alice_test")
            
            assert len(relationships) >= 2
            
            # Check that all relationships involve Alice
            for rel in relationships:
                assert rel.persona1_id == "alice_test" or rel.persona2_id == "alice_test"

    async def test_handler_method_availability(self):
        """Test that relationship handler methods exist and are properly structured"""
        
        # Import here to check availability without full initialization
        from persona_mcp.mcp.handlers import MCPHandlers
        import inspect
        
        # Get all methods from the MCPHandlers class
        methods = inspect.getmembers(MCPHandlers, predicate=inspect.isfunction)
        method_names = [name for name, _ in methods]
        
        # Check for relationship handler methods
        required_handlers = [
            "handle_relationship_get",
            "handle_relationship_list", 
            "handle_relationship_compatibility",
            "handle_relationship_stats",
            "handle_relationship_update",
            "handle_emotional_get_state",
            "handle_emotional_update_state"
        ]
        
        for handler in required_handlers:
            assert handler in method_names, f"Handler {handler} not found in MCPHandlers class"
        
        # Test handler method signatures
        for handler in required_handlers:
            method = getattr(MCPHandlers, handler)
            sig = inspect.signature(method)
            
            # All handlers should accept self and params
            param_names = list(sig.parameters.keys())
            assert 'self' in param_names, f"{handler} missing 'self' parameter"
            assert 'params' in param_names, f"{handler} missing 'params' parameter"

    async def test_relationship_type_evolution(self):
        """Test how relationship types evolve based on interactions"""
        
        async with get_db_session() as session:
            relationship_manager = RelationshipManager(session)
            
            # Start with casual interactions
            await relationship_manager.process_interaction("alice_test", "bob_test", 0.5, 5.0, "casual")
            
            relationship = await relationship_manager.get_relationship("alice_test", "bob_test")
            initial_type = relationship.relationship_type
            
            # Process many positive, longer interactions
            for i in range(10):
                await relationship_manager.process_interaction(
                    "alice_test", "bob_test",
                    interaction_quality=0.8,
                    duration_minutes=30.0,  # Longer interactions
                    context="deep_collaboration"
                )
            
            # Check if relationship type evolved
            updated_relationship = await relationship_manager.get_relationship("alice_test", "bob_test")
            
            # Should have stronger relationship metrics
            assert updated_relationship.affinity > 0.7
            assert updated_relationship.trust > 0.7
            assert updated_relationship.interaction_count > 10
            
            # Relationship strength should be high
            assert updated_relationship.get_relationship_strength() > 0.7

    async def test_cross_persona_relationship_impact(self):
        """Test how relationships affect cross-persona interactions"""
        
        async with get_db_session() as session:
            relationship_manager = RelationshipManager(session)
            
            # Create strong positive relationship between Alice and Bob
            for i in range(5):
                await relationship_manager.process_interaction(
                    "alice_test", "bob_test",
                    interaction_quality=0.8,
                    duration_minutes=20.0,
                    context="strong_bond"
                )
            
            # Create negative relationship between Alice and Charlie  
            for i in range(3):
                await relationship_manager.process_interaction(
                    "alice_test", "charlie_test",
                    interaction_quality=-0.3,
                    duration_minutes=5.0,
                    context="conflict"
                )
            
            # Get Alice's relationships
            alice_relationships = await relationship_manager.get_persona_relationships("alice_test")
            
            # Should have both positive and negative relationships
            compatibility_scores = [rel.get_compatibility_score() for rel in alice_relationships]
            assert max(compatibility_scores) > 0.6  # Strong positive relationship
            assert min(compatibility_scores) < 0.4  # Weak/negative relationship

    async def test_relationship_stats_comprehensive(self):
        """Test comprehensive relationship statistics"""
        
        async with get_db_session() as session:
            relationship_manager = RelationshipManager(session)
            
            # Create diverse relationships
            interactions = [
                ("alice_test", "bob_test", 0.8, 25.0, "professional"),
                ("bob_test", "charlie_test", 0.2, 10.0, "awkward"),
                ("alice_test", "charlie_test", -0.1, 5.0, "conflict"),
                ("alice_test", "bob_test", 0.9, 30.0, "collaboration"),  # Second interaction
            ]
            
            for persona1, persona2, quality, duration, context in interactions:
                await relationship_manager.process_interaction(persona1, persona2, quality, duration, context)
            
        # Test relationship stats directly via manager
        stats = await relationship_manager.get_relationship_stats()
        assert stats["total_relationships"] >= 3
        assert stats["total_interactions"] >= 4
        assert "relationship_types" in stats
        assert "average_compatibility" in stats

    async def test_edge_cases_and_error_handling(self):
        """Test edge cases and error handling in relationship system"""
        
        async with get_db_session() as session:
            relationship_manager = RelationshipManager(session)
            
            # Test invalid interaction quality processing
            success = await relationship_manager.process_interaction(
                "alice_test", "bob_test", 
                2.0,  # Invalid: outside [-1, 1] range - should be clamped
                15.0, "test"
            )
            # Should still succeed but clamp the value
            assert success
            
            # Test nonexistent personas
            success = await relationship_manager.process_interaction(
                "nonexistent1", "nonexistent2",
                0.5, 15.0, "test"
            )
            # Should handle gracefully
            assert not success

    async def test_relationship_bidirectionality(self):
        """Test that relationships are properly bidirectional"""
        
        async with get_db_session() as session:
            relationship_manager = RelationshipManager(session)
            
            # Create relationship Alice -> Bob
            await relationship_manager.process_interaction("alice_test", "bob_test", 0.7, 15.0, "test")
            
            # Should be accessible both ways
            rel_ab = await relationship_manager.get_relationship("alice_test", "bob_test")
            rel_ba = await relationship_manager.get_relationship("bob_test", "alice_test")
            
            # Should be the same relationship object
            assert rel_ab is not None
            assert rel_ba is not None
            assert rel_ab.id == rel_ba.id
            assert rel_ab.affinity == rel_ba.affinity


@pytest.mark.asyncio
class TestRelationshipCompatibilityEngine:
    """Focused tests for the compatibility engine"""
    
    async def test_personality_compatibility_calculation(self):
        """Test personality-based compatibility scoring"""
        
        engine = CompatibilityEngine()
        
        # Create personas with similar personalities
        similar_persona1 = Persona(
            id="sim1", name="Sim1", background="test",
            personality_scores={"openness": 0.8, "conscientiousness": 0.7, "extraversion": 0.6, "agreeableness": 0.8, "neuroticism": 0.3}
        )
        similar_persona2 = Persona(
            id="sim2", name="Sim2", background="test", 
            personality_scores={"openness": 0.7, "conscientiousness": 0.8, "extraversion": 0.5, "agreeableness": 0.9, "neuroticism": 0.2}
        )
        
        # Create personas with opposite personalities
        opposite_persona1 = Persona(
            id="opp1", name="Opp1", background="test",
            personality_scores={"openness": 0.9, "conscientiousness": 0.2, "extraversion": 0.9, "agreeableness": 0.3, "neuroticism": 0.8}
        )
        opposite_persona2 = Persona(
            id="opp2", name="Opp2", background="test",
            personality_scores={"openness": 0.1, "conscientiousness": 0.9, "extraversion": 0.1, "agreeableness": 0.9, "neuroticism": 0.2}
        )
        
        # Test similar personalities
        similar_compat = engine.calculate_personality_compatibility(similar_persona1, similar_persona2)
        assert similar_compat > 0.6
        
        # Test opposite personalities  
        opposite_compat = engine.calculate_personality_compatibility(opposite_persona1, opposite_persona2)
        assert opposite_compat < 0.5

    async def test_interest_compatibility_calculation(self):
        """Test interest-based compatibility scoring"""
        
        engine = CompatibilityEngine()
        
        # Personas with overlapping interests
        shared_interests1 = Persona(
            id="shared1", name="Shared1", background="test",
            interests=["programming", "books", "hiking", "music"]
        )
        shared_interests2 = Persona(
            id="shared2", name="Shared2", background="test",
            interests=["books", "hiking", "cooking", "travel"]
        )
        
        # Personas with no shared interests
        different_interests1 = Persona(
            id="diff1", name="Diff1", background="test", 
            interests=["programming", "gaming", "tech"]
        )
        different_interests2 = Persona(
            id="diff2", name="Diff2", background="test",
            interests=["art", "dance", "literature"]
        )
        
        # Test shared interests
        shared_compat = engine.calculate_interest_compatibility(shared_interests1, shared_interests2)
        assert shared_compat > 0.3  # Should find some overlap
        
        # Test different interests
        different_compat = engine.calculate_interest_compatibility(different_interests1, different_interests2)
        assert different_compat < 0.3  # Should be lower compatibility

    async def test_interaction_suggestions_quality(self):
        """Test quality and relevance of interaction suggestions"""
        
        engine = CompatibilityEngine()
        
        # Create personas with known characteristics
        technical_persona = Persona(
            id="tech", name="Tech", background="Software engineer with a passion for AI",
            interests=["programming", "AI", "robotics"],
            traits=["analytical", "curious", "detail-oriented"]
        )
        creative_persona = Persona(
            id="creative", name="Creative", background="Artist and designer",
            interests=["art", "design", "photography"],
            traits=["creative", "intuitive", "expressive"]
        )
        
        compatibility = engine.calculate_overall_compatibility(technical_persona, creative_persona, None)
        suggestions = engine.suggest_interaction_approach(technical_persona, creative_persona, compatibility)
        
        # Verify suggestion structure
        assert "recommended_approach" in suggestions
        assert "conversation_topics" in suggestions
        assert "potential_challenges" in suggestions
        
        # Should suggest topics that bridge both personas' interests
        topics = suggestions["conversation_topics"]
        assert len(topics) > 0
        
        # At least one topic should relate to technology or creativity
        topic_text = " ".join(topics).lower()
        assert any(keyword in topic_text for keyword in ["tech", "creative", "design", "digital", "innovation"])