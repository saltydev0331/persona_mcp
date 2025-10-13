"""
Unit tests for persona data models
"""

import pytest
import time
from datetime import datetime
from persona_mcp.models import (
    Persona, PersonaInteractionState, Priority, ConversationContext, 
    Relationship, Memory
)


class TestPersonaInteractionState:
    """Test persona interaction state functionality"""
    
    def test_is_available_basic(self):
        """Test basic availability check"""
        state = PersonaInteractionState(persona_id="test")
        assert state.is_available() == True
    
    def test_is_available_cooldown(self):
        """Test availability with cooldown"""
        state = PersonaInteractionState(persona_id="test")
        state.cooldown_until = time.time() + 60  # 1 minute in future
        assert state.is_available() == False
    
    def test_is_available_low_energy(self):
        """Test availability with low energy"""
        state = PersonaInteractionState(persona_id="test")
        state.social_energy = 5  # Below threshold
        assert state.is_available() == False
    
    def test_apply_fatigue(self):
        """Test fatigue application"""
        state = PersonaInteractionState(persona_id="test")
        initial_energy = state.social_energy
        initial_time = state.available_time
        
        state.apply_fatigue(120)  # 2 minutes
        
        assert state.interaction_fatigue > 0
        assert state.social_energy < initial_energy
        assert state.available_time < initial_time
    
    def test_regenerate_energy(self):
        """Test energy regeneration"""
        state = PersonaInteractionState(persona_id="test")
        state.social_energy = 50
        state.interaction_fatigue = 10
        
        state.regenerate_energy(600)  # 10 minutes
        
        assert state.social_energy > 50
        assert state.interaction_fatigue < 10


class TestPersona:
    """Test persona model"""
    
    def test_persona_creation(self):
        """Test basic persona creation"""
        persona = Persona(
            name="Test Persona",
            description="A test persona"
        )
        
        assert persona.name == "Test Persona"
        assert persona.interaction_state is not None
        assert persona.interaction_state.persona_id == persona.id
    
    def test_persona_with_preferences(self):
        """Test persona with topic preferences"""
        persona = Persona(
            name="Scholar",
            description="A learned scholar",
            topic_preferences={
                "books": 90,
                "magic": 80,
                "gossip": 20
            }
        )
        
        assert persona.topic_preferences["books"] == 90
        assert persona.topic_preferences["gossip"] == 20


class TestConversationContext:
    """Test conversation context"""
    
    def test_conversation_creation(self):
        """Test conversation context creation"""
        context = ConversationContext(
            participants=["persona1", "persona2"]
        )
        
        assert len(context.participants) == 2
        assert context.continue_score == 50
        assert context.should_continue() == True
    
    def test_add_turn(self):
        """Test adding conversation turns"""
        context = ConversationContext(
            participants=["persona1", "persona2"]
        )
        
        context.add_turn("persona1", 75)
        
        assert context.turn_count == 1
        assert context.current_speaker == "persona1"
        assert context.continue_score == 75
        assert len(context.score_history) == 1
    
    def test_should_continue(self):
        """Test conversation continuation logic"""
        context = ConversationContext()
        
        # High score should continue
        context.continue_score = 80
        assert context.should_continue() == True
        
        # Low score should not continue
        context.continue_score = 30
        assert context.should_continue() == False
        
        # Low token budget should not continue
        context.continue_score = 80
        context.token_budget = 20
        assert context.should_continue() == False


class TestRelationship:
    """Test relationship model"""
    
    def test_relationship_creation(self):
        """Test relationship creation"""
        rel = Relationship(
            persona1_id="alice",
            persona2_id="bob"
        )
        
        assert rel.affinity == 0.0
        assert rel.trust == 0.0
        assert rel.respect == 0.0
        assert rel.interaction_count == 0
    
    def test_compatibility_score(self):
        """Test compatibility score calculation"""
        rel = Relationship(
            persona1_id="alice",
            persona2_id="bob",
            affinity=0.8,
            trust=0.6,
            respect=0.4
        )
        
        score = rel.get_compatibility_score()
        expected = (0.8 * 0.4) + (0.6 * 0.3) + (0.4 * 0.3)
        assert abs(score - expected) < 0.01
    
    def test_update_from_interaction(self):
        """Test relationship updates"""
        rel = Relationship(
            persona1_id="alice",
            persona2_id="bob"
        )
        
        initial_affinity = rel.affinity
        initial_count = rel.interaction_count
        
        rel.update_from_interaction(positive=True, significance=0.1)
        
        assert rel.affinity > initial_affinity
        assert rel.interaction_count == initial_count + 1
        assert rel.last_interaction is not None


class TestMemory:
    """Test memory model"""
    
    def test_memory_creation(self):
        """Test memory creation"""
        memory = Memory(
            persona_id="test",
            content="I remember this conversation"
        )
        
        assert memory.persona_id == "test"
        assert memory.content == "I remember this conversation"
        assert memory.importance == 0.5
        assert memory.accessed_count == 0
    
    def test_memory_access(self):
        """Test memory access tracking"""
        memory = Memory(
            persona_id="test",
            content="Test memory"
        )
        
        initial_count = memory.accessed_count
        memory.access()
        
        assert memory.accessed_count == initial_count + 1
        assert memory.last_accessed is not None


if __name__ == "__main__":
    pytest.main([__file__])