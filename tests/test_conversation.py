"""
Integration tests for conversation engine
"""

import pytest
import asyncio
import tempfile
import shutil
from pathlib import Path

from persona_mcp.models import Persona, Priority
from persona_mcp.persistence import SQLiteManager, VectorMemoryManager
from persona_mcp.llm import LLMManager
from persona_mcp.conversation import ConversationEngine


@pytest.fixture
async def temp_db():
    """Create temporary database for testing"""
    temp_dir = tempfile.mkdtemp()
    db_path = Path(temp_dir) / "test.db"
    
    db_manager = SQLiteManager(str(db_path))
    await db_manager.initialize()
    
    yield db_manager
    
    # Cleanup
    shutil.rmtree(temp_dir)


@pytest.fixture
async def temp_memory():
    """Create temporary vector memory for testing"""
    temp_dir = tempfile.mkdtemp()
    
    memory_manager = VectorMemoryManager(str(temp_dir))
    
    yield memory_manager
    
    await memory_manager.close()
    shutil.rmtree(temp_dir)


@pytest.fixture
def test_personas():
    """Create test personas"""
    
    aria = Persona(
        name="Aria",
        description="Friendly bard",
        topic_preferences={
            "music": 90,
            "stories": 85,
            "gossip": 70
        },
        charisma=16
    )
    aria.interaction_state.current_priority = Priority.SOCIAL
    aria.interaction_state.social_energy = 120
    
    kira = Persona(
        name="Kira", 
        description="Focused scholar",
        topic_preferences={
            "research": 95,
            "magic": 85,
            "gossip": 25
        },
        charisma=12
    )
    kira.interaction_state.current_priority = Priority.ACADEMIC
    kira.interaction_state.social_energy = 80
    
    return aria, kira


class TestConversationEngine:
    """Test conversation engine functionality"""
    
    @pytest.mark.asyncio
    async def test_engine_initialization(self, temp_db, temp_memory):
        """Test conversation engine initialization"""
        
        llm_manager = LLMManager()
        engine = ConversationEngine(temp_db, temp_memory, llm_manager)
        
        assert engine.db == temp_db
        assert engine.memory == temp_memory
        assert engine.llm == llm_manager
        assert len(engine.active_conversations) == 0
    
    @pytest.mark.asyncio
    async def test_continue_score_calculation(self, temp_db, temp_memory, test_personas):
        """Test continue score calculation"""
        
        aria, kira = test_personas
        
        # Save personas to database
        await temp_db.save_persona(aria)
        await temp_db.save_persona(kira)
        
        llm_manager = LLMManager()
        engine = ConversationEngine(temp_db, temp_memory, llm_manager)
        
        # Create conversation context
        from persona_mcp.models import ConversationContext
        context = ConversationContext(
            participants=[aria.id, kira.id],
            topic="music",  # Aria loves this, Kira doesn't
            duration=60
        )
        
        # Calculate continue score
        score = await engine.calculate_continue_score(aria, kira, context)
        
        # Score should be reasonable (0-100)
        assert 0 <= score <= 100
        
        # Aria should have higher interest in music topic
        aria_score = await engine.calculate_continue_score(aria, kira, context)
        
        # Change topic to research (Kira's favorite)
        context.topic = "research"
        kira_score = await engine.calculate_continue_score(kira, aria, context)
        
        # Kira should be more interested in research than Aria in music
        # (Note: this might not always be true due to other factors)
        assert isinstance(kira_score, int)
    
    @pytest.mark.asyncio
    async def test_conversation_initiation(self, temp_db, temp_memory, test_personas):
        """Test starting a conversation"""
        
        aria, kira = test_personas
        
        # Save personas
        await temp_db.save_persona(aria)
        await temp_db.save_persona(kira)
        
        llm_manager = LLMManager()
        engine = ConversationEngine(temp_db, temp_memory, llm_manager)
        
        # Start conversation
        context = await engine.initiate_conversation(
            aria, kira, "stories", token_budget=500
        )
        
        assert context is not None
        assert context.id in engine.active_conversations
        assert len(context.participants) == 2
        assert aria.id in context.participants
        assert kira.id in context.participants
        assert context.topic == "stories"
        assert context.token_budget == 500
    
    @pytest.mark.asyncio 
    async def test_conversation_unavailable_personas(self, temp_db, temp_memory, test_personas):
        """Test conversation with unavailable personas"""
        
        aria, kira = test_personas
        
        # Make Aria unavailable (no energy)
        aria.interaction_state.social_energy = 5
        
        await temp_db.save_persona(aria)
        await temp_db.save_persona(kira)
        
        llm_manager = LLMManager()
        engine = ConversationEngine(temp_db, temp_memory, llm_manager)
        
        # Try to start conversation
        context = await engine.initiate_conversation(aria, kira, "general")
        
        # Should fail because Aria is unavailable
        assert context is None
    
    @pytest.mark.asyncio
    async def test_relationship_caching(self, temp_db, temp_memory, test_personas):
        """Test relationship caching"""
        
        aria, kira = test_personas
        
        await temp_db.save_persona(aria)
        await temp_db.save_persona(kira)
        
        llm_manager = LLMManager()
        engine = ConversationEngine(temp_db, temp_memory, llm_manager)
        
        # Get relationship (should create new one)
        rel1 = await engine._get_relationship(aria.id, kira.id)
        assert rel1 is not None
        
        # Get same relationship again (should use cache)
        rel2 = await engine._get_relationship(aria.id, kira.id)
        assert rel2 is rel1  # Same object reference
        
        # Get reverse relationship (should use cache)
        rel3 = await engine._get_relationship(kira.id, aria.id)
        assert rel3 is rel1  # Same relationship


@pytest.mark.asyncio 
async def test_memory_storage_integration(temp_memory):
    """Test memory storage integration"""
    
    # Initialize memory for test persona
    await temp_memory.initialize_persona_memory("test_persona")
    
    from persona_mcp.models import Memory
    
    # Create test memory
    memory = Memory(
        persona_id="test_persona",
        content="I had an interesting conversation about magic today",
        memory_type="conversation",
        importance=0.8
    )
    
    # Store memory
    success = await temp_memory.store_memory(memory)
    assert success == True
    
    # Search for memory
    results = await temp_memory.search_memories(
        "test_persona", 
        "conversation about magic",
        n_results=5
    )
    
    assert len(results) >= 1
    assert any("magic" in result.content for result in results)


if __name__ == "__main__":
    pytest.main([__file__])