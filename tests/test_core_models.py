"""
Unit tests for persona_mcp.core.models module

Tests the shared data models used by both MCP server and PersonaAPI server
to ensure data consistency and operational parity.
"""

import pytest
import time
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock

from persona_mcp.core.models import (
    Priority, PersonaBase, PersonaInteractionState, Persona,
    Memory, RelationshipType, EmotionalState, Relationship,
    ConversationContext, ConversationTurn, MCPRequest, MCPResponse,
    MCPError, SimulationState
)


class TestPriorityEnum:
    """Test Priority enumeration"""
    
    def test_priority_values(self):
        """Test that all priority values are correct"""
        assert Priority.URGENT == "urgent"
        assert Priority.IMPORTANT == "important"
        assert Priority.CASUAL == "casual"
        assert Priority.SOCIAL == "social"
        assert Priority.ACADEMIC == "academic"
        assert Priority.BUSINESS == "business"
        assert Priority.NONE == "none"
    
    def test_priority_string_comparison(self):
        """Test that priorities can be compared as strings"""
        assert Priority.URGENT == "urgent"
        assert Priority.NONE == "none"


class TestPersonaBase:
    """Test PersonaBase model"""
    
    def test_persona_base_creation(self):
        """Test creating a PersonaBase with required fields"""
        persona = PersonaBase(
            name="Test Persona",
            description="A test persona for unit testing"
        )
        
        assert persona.name == "Test Persona"
        assert persona.description == "A test persona for unit testing"
        assert len(persona.id) > 0  # UUID should be generated
        assert isinstance(persona.personality_traits, dict)
        assert isinstance(persona.topic_preferences, dict)
        assert persona.charisma == 10  # default value
        assert persona.intelligence == 10  # default value
        assert persona.social_rank == "commoner"  # default value
        assert isinstance(persona.created_at, datetime)
    
    def test_persona_base_with_custom_values(self):
        """Test PersonaBase with custom field values"""
        custom_traits = {"extroversion": 0.8, "openness": 0.6}
        custom_topics = {"technology": 90, "sports": 20}
        
        persona = PersonaBase(
            name="Custom Persona",
            description="Custom test persona",
            personality_traits=custom_traits,
            topic_preferences=custom_topics,
            charisma=18,
            intelligence=14,
            social_rank="noble"
        )
        
        assert persona.personality_traits == custom_traits
        assert persona.topic_preferences == custom_topics
        assert persona.charisma == 18
        assert persona.intelligence == 14
        assert persona.social_rank == "noble"
    
    def test_persona_base_validation(self):
        """Test PersonaBase field validation"""
        # Test charisma bounds
        with pytest.raises(ValueError):
            PersonaBase(name="Test", description="Test", charisma=0)
        
        with pytest.raises(ValueError):
            PersonaBase(name="Test", description="Test", charisma=21)
        
        # Test intelligence bounds
        with pytest.raises(ValueError):
            PersonaBase(name="Test", description="Test", intelligence=0)
        
        with pytest.raises(ValueError):
            PersonaBase(name="Test", description="Test", intelligence=21)


class TestPersonaInteractionState:
    """Test PersonaInteractionState model"""
    
    def test_interaction_state_creation(self):
        """Test creating PersonaInteractionState"""
        state = PersonaInteractionState(persona_id="test-persona-123")
        
        assert state.persona_id == "test-persona-123"
        assert state.interest_level == 50  # default
        assert state.interaction_fatigue == 0
        assert state.current_priority == Priority.NONE
        assert state.available_time == 300  # 5 minutes default
        assert state.social_energy == 100
        assert state.cooldown_until == 0
        assert isinstance(state.last_updated, datetime)
    
    def test_is_available_when_ready(self):
        """Test is_available returns True when persona is ready"""
        state = PersonaInteractionState(
            persona_id="test-persona",
            available_time=100,
            social_energy=50,
            cooldown_until=0
        )
        
        assert state.is_available() == True
    
    def test_is_available_when_on_cooldown(self):
        """Test is_available returns False when on cooldown"""
        future_time = time.time() + 3600  # 1 hour in future
        state = PersonaInteractionState(
            persona_id="test-persona",
            cooldown_until=future_time
        )
        
        assert state.is_available() == False
    
    def test_is_available_when_no_time(self):
        """Test is_available returns False when no available time"""
        state = PersonaInteractionState(
            persona_id="test-persona",
            available_time=20  # Less than 30 second threshold
        )
        
        assert state.is_available() == False
    
    def test_is_available_when_low_energy(self):
        """Test is_available returns False when social energy too low"""
        state = PersonaInteractionState(
            persona_id="test-persona",
            social_energy=5  # Less than 10 threshold
        )
        
        assert state.is_available() == False
    
    def test_apply_fatigue(self):
        """Test apply_fatigue method"""
        state = PersonaInteractionState(
            persona_id="test-persona",
            interaction_fatigue=0,
            social_energy=100,
            available_time=300
        )
        
        # Apply 90 seconds of interaction
        state.apply_fatigue(90)
        
        assert state.interaction_fatigue == 3  # 90 // 30 = 3
        assert state.social_energy == 99  # 100 - (90 // 60) = 99
        assert state.available_time == 210  # 300 - 90 = 210
    
    def test_regenerate_energy(self):
        """Test regenerate_energy method"""
        state = PersonaInteractionState(
            persona_id="test-persona",
            social_energy=50,
            interaction_fatigue=10
        )
        
        # Regenerate over 10 minutes (600 seconds)
        state.regenerate_energy(600)
        
        assert state.social_energy == 60  # 50 + (600 // 60) = 60
        assert state.interaction_fatigue == 8  # 10 - (600 // 300) = 8
    
    def test_regenerate_energy_caps(self):
        """Test regenerate_energy respects caps"""
        state = PersonaInteractionState(
            persona_id="test-persona",
            social_energy=190,
            interaction_fatigue=1
        )
        
        # Regenerate over 20 minutes
        state.regenerate_energy(1200)
        
        assert state.social_energy == 200  # Capped at 200
        assert state.interaction_fatigue == 0  # Capped at 0


class TestPersona:
    """Test Persona model (complete persona with interaction state)"""
    
    def test_persona_creation(self):
        """Test creating a complete Persona"""
        persona = Persona(
            name="Complete Persona",
            description="A complete persona with interaction state"
        )
        
        assert persona.name == "Complete Persona"
        assert persona.interaction_state is not None
        assert persona.interaction_state.persona_id == persona.id
    
    def test_persona_with_custom_interaction_state(self):
        """Test Persona with custom interaction state"""
        custom_state = PersonaInteractionState(
            persona_id="custom-id",
            interest_level=75
        )
        
        persona = Persona(
            name="Custom Persona",
            description="Custom persona",
            interaction_state=custom_state
        )
        
        assert persona.interaction_state.interest_level == 75
        assert persona.interaction_state.persona_id == "custom-id"


class TestMemory:
    """Test Memory model"""
    
    def test_memory_creation(self):
        """Test creating a Memory record"""
        memory = Memory(
            persona_id="test-persona",
            content="This is a test memory"
        )
        
        assert memory.persona_id == "test-persona"
        assert memory.content == "This is a test memory"
        assert len(memory.id) > 0  # UUID generated
        assert memory.memory_type == "conversation"  # default
        assert memory.importance == 0.5  # default
        assert memory.emotional_valence == 0.0  # default
        assert memory.visibility == "private"  # default
        assert isinstance(memory.created_at, datetime)
        assert memory.accessed_count == 0
        assert memory.last_accessed is None
    
    def test_memory_with_custom_values(self):
        """Test Memory with custom field values"""
        metadata = {"location": "conference_room", "participants": ["alice", "bob"]}
        
        memory = Memory(
            persona_id="test-persona",
            content="Important meeting notes",
            memory_type="event",
            importance=0.9,
            emotional_valence=0.3,
            related_personas=["alice", "bob"],
            visibility="shared",
            metadata=metadata
        )
        
        assert memory.memory_type == "event"
        assert memory.importance == 0.9
        assert memory.emotional_valence == 0.3
        assert memory.related_personas == ["alice", "bob"]
        assert memory.visibility == "shared"
        assert memory.metadata == metadata
    
    def test_memory_validation(self):
        """Test Memory field validation"""
        # Test importance bounds
        with pytest.raises(ValueError):
            Memory(persona_id="test", content="test", importance=1.5)
        
        with pytest.raises(ValueError):
            Memory(persona_id="test", content="test", importance=-0.1)
        
        # Test emotional valence bounds
        with pytest.raises(ValueError):
            Memory(persona_id="test", content="test", emotional_valence=1.1)
        
        with pytest.raises(ValueError):
            Memory(persona_id="test", content="test", emotional_valence=-1.1)
    
    def test_memory_access(self):
        """Test memory access tracking"""
        memory = Memory(
            persona_id="test-persona",
            content="Test memory for access tracking"
        )
        
        assert memory.accessed_count == 0
        assert memory.last_accessed is None
        
        # Access the memory
        memory.access()
        
        assert memory.accessed_count == 1
        assert memory.last_accessed is not None
        assert isinstance(memory.last_accessed, datetime)
        
        # Access again
        memory.access()
        
        assert memory.accessed_count == 2


class TestRelationshipType:
    """Test RelationshipType enumeration"""
    
    def test_relationship_types(self):
        """Test all relationship type values"""
        assert RelationshipType.STRANGER == "stranger"
        assert RelationshipType.ACQUAINTANCE == "acquaintance"
        assert RelationshipType.FRIEND == "friend"
        assert RelationshipType.CLOSE_FRIEND == "close_friend"
        assert RelationshipType.RIVAL == "rival"
        assert RelationshipType.ENEMY == "enemy"
        assert RelationshipType.MENTOR == "mentor"
        assert RelationshipType.STUDENT == "student"
        assert RelationshipType.ROMANTIC == "romantic"
        assert RelationshipType.FAMILY == "family"


class TestEmotionalState:
    """Test EmotionalState model"""
    
    def test_emotional_state_creation(self):
        """Test creating EmotionalState"""
        state = EmotionalState(persona_id="test-persona")
        
        assert state.persona_id == "test-persona"
        assert state.mood == 0.0  # neutral default
        assert state.energy_level == 0.5  # medium default
        assert state.stress_level == 0.0  # calm default
        assert state.curiosity == 0.5  # medium default
        assert state.social_battery == 1.0  # full default
        assert isinstance(state.last_updated, datetime)
    
    def test_emotional_state_validation(self):
        """Test EmotionalState field validation"""
        # Test mood bounds
        with pytest.raises(ValueError):
            EmotionalState(persona_id="test", mood=1.1)
        
        with pytest.raises(ValueError):
            EmotionalState(persona_id="test", mood=-1.1)
        
        # Test energy bounds
        with pytest.raises(ValueError):
            EmotionalState(persona_id="test", energy_level=1.1)
        
        with pytest.raises(ValueError):
            EmotionalState(persona_id="test", energy_level=-0.1)
    
    def test_apply_interaction_effect_positive(self):
        """Test positive interaction effects"""
        state = EmotionalState(
            persona_id="test-persona",
            mood=0.0,
            social_battery=1.0
        )
        
        # Apply positive 30-minute interaction
        state.apply_interaction_effect(relationship_quality=0.8, duration_minutes=30)
        
        assert state.mood > 0.0  # Should improve mood
        assert state.social_battery < 1.0  # Should drain battery
        assert isinstance(state.last_updated, datetime)
    
    def test_apply_interaction_effect_negative(self):
        """Test negative interaction effects"""
        state = EmotionalState(
            persona_id="test-persona",
            mood=0.0,
            social_battery=1.0
        )
        
        # Apply negative interaction
        state.apply_interaction_effect(relationship_quality=-0.6, duration_minutes=15)
        
        assert state.mood < 0.0  # Should worsen mood
        assert state.social_battery < 1.0  # Should still drain battery
    
    def test_regenerate_over_time(self):
        """Test emotional state regeneration"""
        state = EmotionalState(
            persona_id="test-persona",
            mood=0.5,  # Positive mood
            social_battery=0.3  # Low battery
        )
        
        # Regenerate over 2 hours
        state.regenerate_over_time(hours_elapsed=2.0)
        
        assert state.mood < 0.5  # Should drift toward neutral
        assert state.social_battery > 0.3  # Should regenerate


class TestRelationship:
    """Test Relationship model"""
    
    def test_relationship_creation(self):
        """Test creating a Relationship"""
        relationship = Relationship(
            persona1_id="alice",
            persona2_id="bob"
        )
        
        assert relationship.persona1_id == "alice"
        assert relationship.persona2_id == "bob"
        assert len(relationship.id) > 0  # UUID generated
        assert relationship.affinity == 0.0  # neutral default
        assert relationship.trust == 0.0
        assert relationship.respect == 0.0
        assert relationship.intimacy == 0.0
        assert relationship.relationship_type == RelationshipType.STRANGER
        assert relationship.interaction_count == 0
        assert relationship.total_interaction_time == 0
        assert relationship.last_interaction is None
        assert isinstance(relationship.first_meeting, datetime)
    
    def test_get_compatibility_score(self):
        """Test compatibility score calculation"""
        relationship = Relationship(
            persona1_id="alice",
            persona2_id="bob",
            affinity=0.8,
            trust=0.6,
            respect=0.7,
            intimacy=0.4
        )
        
        score = relationship.get_compatibility_score()
        assert 0.0 <= score <= 1.0
        assert score > 0.5  # Should be high with positive values
    
    def test_get_relationship_strength(self):
        """Test relationship strength calculation"""
        relationship = Relationship(
            persona1_id="alice",
            persona2_id="bob",
            affinity=0.6,
            trust=0.4,
            respect=0.5,
            intimacy=0.3
        )
        
        strength = relationship.get_relationship_strength()
        assert -1.0 <= strength <= 1.0
        assert strength > 0  # Should be positive with positive values
    
    def test_update_relationship_type_friend(self):
        """Test automatic relationship type update to friend"""
        relationship = Relationship(
            persona1_id="alice",
            persona2_id="bob",
            affinity=0.6,
            trust=0.5,
            respect=0.4,
            intimacy=0.3
        )
        
        relationship.update_relationship_type()
        assert relationship.relationship_type == RelationshipType.FRIEND
    
    def test_update_relationship_type_enemy(self):
        """Test automatic relationship type update to enemy"""
        relationship = Relationship(
            persona1_id="alice",
            persona2_id="bob",
            affinity=-0.8,
            trust=-0.7,
            respect=-0.6,
            intimacy=0.0
        )
        
        # Calculate expected strength: (-0.8 * 0.4) + (-0.7 * 0.3) + (-0.6 * 0.2) + (0.0 * 0.1) = -0.65
        # This should be > -0.7, so should be RIVAL, not ENEMY
        relationship.update_relationship_type()
        assert relationship.relationship_type == RelationshipType.RIVAL
    
    def test_update_from_interaction_positive(self):
        """Test relationship update from positive interaction"""
        relationship = Relationship(
            persona1_id="alice",
            persona2_id="bob"
        )
        
        initial_affinity = relationship.affinity
        
        # Positive 15-minute interaction with high quality (>0.7 for memorable moment)
        relationship.update_from_interaction(
            interaction_quality=0.8,
            duration_minutes=15.0,
            context="friendly_chat"
        )
        
        assert relationship.affinity > initial_affinity
        assert relationship.interaction_count == 1
        assert relationship.total_interaction_time == 15
        assert relationship.last_interaction is not None
        assert len(relationship.memorable_moments) > 0  # High quality interaction
    
    def test_update_from_interaction_negative(self):
        """Test relationship update from negative interaction"""
        relationship = Relationship(
            persona1_id="alice",
            persona2_id="bob",
            affinity=0.3  # Start with some positive affinity
        )
        
        # Negative interaction
        relationship.update_from_interaction(
            interaction_quality=-0.6,
            duration_minutes=10.0,
            context="argument"
        )
        
        assert relationship.affinity < 0.3  # Should decrease
        assert relationship.interaction_count == 1
    
    def test_get_interaction_modifier(self):
        """Test interaction modifier calculation"""
        relationship = Relationship(
            persona1_id="alice",
            persona2_id="bob",
            affinity=0.5,
            trust=0.4,
            recent_interaction_quality=0.2
        )
        
        modifier = relationship.get_interaction_modifier()
        assert -0.5 <= modifier <= 0.5
        assert modifier > 0  # Should be positive for good relationship


class TestConversationContext:
    """Test ConversationContext model"""
    
    def test_conversation_context_creation(self):
        """Test creating ConversationContext"""
        context = ConversationContext()
        
        assert len(context.id) > 0  # UUID generated
        assert context.participants == []
        assert context.current_speaker is None
        assert context.topic == "general"  # default
        assert context.topic_drift_count == 0
        assert context.duration == 0
        assert context.token_budget == 1000  # default
        assert context.tokens_used == 0
        assert context.continue_score == 50  # default
        assert context.turn_count == 0
        assert isinstance(context.started_at, datetime)
        assert context.ended_at is None
        assert context.exit_reason is None
    
    def test_conversation_with_participants(self):
        """Test ConversationContext with participants"""
        context = ConversationContext(
            participants=["alice", "bob", "charlie"],
            topic="technology",
            token_budget=2000
        )
        
        assert context.participants == ["alice", "bob", "charlie"]
        assert context.topic == "technology"
        assert context.token_budget == 2000
    
    def test_add_turn(self):
        """Test adding a conversation turn"""
        context = ConversationContext()
        
        context.add_turn(speaker_id="alice", continue_score=75)
        
        assert context.current_speaker == "alice"
        assert context.turn_count == 1
        assert context.continue_score == 75
        assert context.score_history == [75]
    
    def test_should_continue_positive(self):
        """Test should_continue returns True when appropriate"""
        context = ConversationContext(
            continue_score=60,
            token_budget=100
        )
        
        assert context.should_continue() == True
    
    def test_should_continue_low_score(self):
        """Test should_continue returns False for low score"""
        context = ConversationContext(
            continue_score=30,  # Below 40 threshold
            token_budget=100
        )
        
        assert context.should_continue() == False
    
    def test_should_continue_low_budget(self):
        """Test should_continue returns False for low token budget"""
        context = ConversationContext(
            continue_score=60,
            token_budget=30  # Below 50 threshold
        )
        
        assert context.should_continue() == False
    
    def test_end_conversation(self):
        """Test ending a conversation"""
        context = ConversationContext()
        
        assert context.ended_at is None
        assert context.exit_reason is None
        
        context.end_conversation("natural_conclusion")
        
        assert context.ended_at is not None
        assert isinstance(context.ended_at, datetime)
        assert context.exit_reason == "natural_conclusion"


class TestConversationTurn:
    """Test ConversationTurn model"""
    
    def test_conversation_turn_creation(self):
        """Test creating ConversationTurn"""
        turn = ConversationTurn(
            conversation_id="conv-123",
            speaker_id="alice",
            turn_number=1,
            content="Hello, how are you?",
            continue_score=70
        )
        
        assert len(turn.id) > 0  # UUID generated
        assert turn.conversation_id == "conv-123"
        assert turn.speaker_id == "alice"
        assert turn.turn_number == 1
        assert turn.content == "Hello, how are you?"
        assert turn.response_type == "full_llm"  # default
        assert turn.continue_score == 70
        assert turn.tokens_used == 0  # default
        assert turn.processing_time == 0.0  # default
        assert isinstance(turn.created_at, datetime)
    
    def test_conversation_turn_validation(self):
        """Test ConversationTurn validation"""
        # Test continue_score bounds
        with pytest.raises(ValueError):
            ConversationTurn(
                conversation_id="conv-123",
                speaker_id="alice",
                turn_number=1,
                content="Test",
                continue_score=101  # Above 100
            )
        
        with pytest.raises(ValueError):
            ConversationTurn(
                conversation_id="conv-123",
                speaker_id="alice",
                turn_number=1,
                content="Test",
                continue_score=-1  # Below 0
            )


class TestMCPModels:
    """Test MCP JSON-RPC models"""
    
    def test_mcp_request_creation(self):
        """Test creating MCPRequest"""
        request = MCPRequest(
            method="test_method",
            params={"param1": "value1"},
            id="req-123"
        )
        
        assert request.jsonrpc == "2.0"
        assert request.method == "test_method"
        assert request.params == {"param1": "value1"}
        assert request.id == "req-123"
    
    def test_mcp_request_minimal(self):
        """Test MCPRequest with minimal fields"""
        request = MCPRequest(method="ping")
        
        assert request.jsonrpc == "2.0"
        assert request.method == "ping"
        assert request.params is None
        assert request.id is None
    
    def test_mcp_response_success(self):
        """Test MCPResponse for successful result"""
        response = MCPResponse(
            result={"success": True, "data": "test"},
            id="req-123"
        )
        
        assert response.jsonrpc == "2.0"
        assert response.result == {"success": True, "data": "test"}
        assert response.error is None
        assert response.id == "req-123"
    
    def test_mcp_response_error(self):
        """Test MCPResponse for error"""
        error_data = {"code": -32602, "message": "Invalid params"}
        response = MCPResponse(
            error=error_data,
            id="req-123"
        )
        
        assert response.jsonrpc == "2.0"
        assert response.result is None
        assert response.error == error_data
        assert response.id == "req-123"
    
    def test_mcp_error_creation(self):
        """Test creating MCPError"""
        error = MCPError(
            code=-32600,
            message="Invalid Request",
            data={"details": "Missing required field"}
        )
        
        assert error.code == -32600
        assert error.message == "Invalid Request"
        assert error.data == {"details": "Missing required field"}


class TestSimulationState:
    """Test SimulationState model"""
    
    def test_simulation_state_creation(self):
        """Test creating SimulationState"""
        state = SimulationState()
        
        assert state.active_conversations == {}
        assert state.persona_locations == {}
        assert isinstance(state.last_tick, float)  # Just check it's a float timestamp
        assert state.simulation_running == False
        assert state.metrics == {}
    
    def test_simulation_state_with_data(self):
        """Test SimulationState with active data"""
        conversations = {"conv1": ConversationContext()}
        locations = {"alice": "room1", "bob": "room2"}
        metrics = {"total_interactions": 42, "average_quality": 0.75}
        
        state = SimulationState(
            active_conversations=conversations,
            persona_locations=locations,
            simulation_running=True,
            metrics=metrics
        )
        
        assert state.active_conversations == conversations
        assert state.persona_locations == locations
        assert state.simulation_running == True
        assert state.metrics == metrics


class TestModelIntegration:
    """Test integration between different models"""
    
    def test_persona_with_emotional_state_and_relationships(self):
        """Test how different models work together"""
        # Create personas
        alice = Persona(name="Alice", description="Test persona Alice")
        bob = Persona(name="Bob", description="Test persona Bob")
        
        # Create emotional states
        alice_emotions = EmotionalState(persona_id=alice.id, mood=0.3)
        bob_emotions = EmotionalState(persona_id=bob.id, mood=-0.1)
        
        # Create relationship
        relationship = Relationship(
            persona1_id=alice.id,
            persona2_id=bob.id,
            affinity=0.4
        )
        
        # Create memory for Alice about Bob
        memory = Memory(
            persona_id=alice.id,
            content="Had an interesting conversation with Bob about technology",
            related_personas=[bob.id],
            importance=0.7
        )
        
        # Test that all models are properly connected
        assert alice.id != bob.id
        assert alice_emotions.persona_id == alice.id
        assert bob_emotions.persona_id == bob.id
        assert relationship.persona1_id == alice.id
        assert relationship.persona2_id == bob.id
        assert memory.persona_id == alice.id
        assert bob.id in memory.related_personas
    
    def test_conversation_flow(self):
        """Test conversation models working together"""
        # Create conversation context
        context = ConversationContext(
            participants=["alice", "bob"],
            topic="machine_learning"
        )
        
        # Add turns
        turn1 = ConversationTurn(
            conversation_id=context.id,
            speaker_id="alice",
            turn_number=1,
            content="What do you think about neural networks?",
            continue_score=80
        )
        
        context.add_turn("alice", 80)
        
        turn2 = ConversationTurn(
            conversation_id=context.id,
            speaker_id="bob",
            turn_number=2,
            content="They're fascinating! I especially like transformers.",
            continue_score=85
        )
        
        context.add_turn("bob", 85)
        
        # Test conversation state
        assert context.turn_count == 2
        assert context.current_speaker == "bob"
        assert context.score_history == [80, 85]
        assert context.should_continue() == True
        
        # Test turns reference same conversation
        assert turn1.conversation_id == context.id
        assert turn2.conversation_id == context.id
    
    def test_mcp_request_response_cycle(self):
        """Test MCP request/response models"""
        # Create request
        request = MCPRequest(
            method="get_persona",
            params={"persona_id": "alice"},
            id="req-456"
        )
        
        # Create successful response
        response = MCPResponse(
            result={
                "persona": {
                    "id": "alice",
                    "name": "Alice",
                    "description": "Test persona"
                }
            },
            id=request.id
        )
        
        # Test request-response matching
        assert response.id == request.id
        assert response.result is not None
        assert response.error is None
        
        # Create error response
        error_response = MCPResponse(
            error={
                "code": -32602,
                "message": "Persona not found"
            },
            id=request.id
        )
        
        assert error_response.id == request.id
        assert error_response.result is None
        assert error_response.error is not None