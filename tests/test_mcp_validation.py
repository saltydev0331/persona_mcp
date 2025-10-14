"""
Test MCP input validation

Tests that MCP handlers properly validate input parameters and return
appropriate error messages for invalid inputs.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock

from persona_mcp.mcp.handlers import MCPHandlers
from persona_mcp.models import MCPRequest, Persona, PersonaInteractionState, Priority


@pytest.fixture
def mock_handlers():
    """Create MCPHandlers with mocked dependencies"""
    handlers = MCPHandlers(
        conversation_engine=AsyncMock(),
        db_manager=AsyncMock(),
        memory_manager=AsyncMock(),
        llm_manager=AsyncMock(),
        session_manager=AsyncMock()
    )
    
    # Mock WebSocket ID for handlers that need it
    handlers.websocket_id = "test_websocket_123"
    
    return handlers


@pytest.fixture
def sample_persona():
    """Create a sample persona for testing"""
    return Persona(
        id="test_persona_id",
        name="TestPersona", 
        description="A test persona",
        personality_traits={"friendly": True, "helpful": True},
        topic_preferences={"general": 50},
        interaction_state=PersonaInteractionState(
            persona_id="test_persona_id",
            social_energy=100,
            available_time=60,
            interaction_fatigue=0,
            current_priority=Priority.SOCIAL
        )
    )


class TestPersonaSwitchValidation:
    """Test persona.switch input validation"""
    
    @pytest.mark.asyncio
    async def test_missing_persona_id(self, mock_handlers):
        """Test persona.switch fails with missing persona_id"""
        params = {}  # Missing persona_id
        
        with pytest.raises(ValueError, match="persona_id is required"):
            await mock_handlers.handle_persona_switch(params)
    
    @pytest.mark.asyncio
    async def test_empty_persona_id(self, mock_handlers):
        """Test persona.switch fails with empty persona_id"""
        params = {"persona_id": ""}  # Empty persona_id
        
        with pytest.raises(ValueError, match="persona_id is required"):
            await mock_handlers.handle_persona_switch(params)
    
    @pytest.mark.asyncio
    async def test_nonexistent_persona(self, mock_handlers):
        """Test persona.switch fails with nonexistent persona"""
        # Mock db to return None (persona not found)
        mock_handlers.db.load_persona = AsyncMock(return_value=None)
        mock_handlers.db.list_personas = AsyncMock(return_value=[])
        
        params = {"persona_id": "nonexistent_persona"}
        
        with pytest.raises(ValueError, match="Persona not found: nonexistent_persona"):
            await mock_handlers.handle_persona_switch(params)
    
    @pytest.mark.asyncio
    async def test_unavailable_persona(self, mock_handlers, sample_persona):
        """Test persona.switch fails with unavailable persona"""
        # Make persona unavailable
        sample_persona.interaction_state.social_energy = -10  # Exhausted
        
        mock_handlers.db.load_persona = AsyncMock(return_value=sample_persona)
        
        params = {"persona_id": "test_persona_id"}
        
        with pytest.raises(ValueError, match="is not available for interaction"):
            await mock_handlers.handle_persona_switch(params)


class TestPersonaChatValidation:
    """Test persona.chat input validation"""
    
    @pytest.mark.asyncio
    async def test_missing_message(self, mock_handlers):
        """Test persona.chat fails with missing message"""
        params = {}  # Missing message
        
        with pytest.raises(ValueError, match="message is required"):
            await mock_handlers.handle_persona_chat(params)
    
    @pytest.mark.asyncio
    async def test_empty_message(self, mock_handlers):
        """Test persona.chat fails with empty message"""
        params = {"message": ""}  # Empty message
        
        with pytest.raises(ValueError, match="message is required"):
            await mock_handlers.handle_persona_chat(params)
    
    @pytest.mark.asyncio
    async def test_no_persona_selected(self, mock_handlers):
        """Test persona.chat fails when no persona is selected"""
        # Mock session manager to return None (no current persona)
        mock_handlers.session.get_current_persona = MagicMock(return_value=None)
        
        params = {"message": "Hello"}
        
        with pytest.raises(ValueError, match="No persona selected. Use persona.switch first"):
            await mock_handlers.handle_persona_chat(params)
    
    @pytest.mark.asyncio
    async def test_invalid_token_budget(self, mock_handlers, sample_persona):
        """Test persona.chat handles invalid token budget gracefully"""
        # Mock valid persona selection
        mock_handlers.session.get_current_persona = MagicMock(return_value="test_persona_id")
        mock_handlers.db.load_persona = AsyncMock(return_value=sample_persona)
        mock_handlers.session.get_conversation_context = MagicMock(return_value={})
        
        # Mock conversation session with proper attributes
        mock_session = MagicMock()
        mock_session.turn_count = 0
        mock_handlers.session.get_conversation_session = MagicMock(return_value=mock_session)
        mock_handlers.session.get_current_conversation_id = MagicMock(return_value="test_conv_id")
        
        # Mock conversation engine
        mock_handlers.conversation.create_conversation_turn = AsyncMock()
        
        # Mock LLM response - this is the key fix!
        mock_handlers.llm.ollama.generate_response = AsyncMock(return_value="Test response from LLM")
        
        # Mock memory operations
        mock_handlers.memory.store_memory = AsyncMock()
        
        # Test with negative token budget (should use default)
        params = {"message": "Hello", "token_budget": -100}
        
        # Should not raise an error, but should handle gracefully
        result = await mock_handlers.handle_persona_chat(params)
        assert "response" in result


class TestMemorySearchValidation:
    """Test memory.search input validation"""
    
    @pytest.mark.asyncio
    async def test_missing_query(self, mock_handlers):
        """Test memory.search fails with missing query"""
        params = {"persona_id": "test_persona"}  # Missing query
        
        with pytest.raises(ValueError, match="query is required"):
            await mock_handlers.handle_memory_search(params)
    
    @pytest.mark.asyncio
    async def test_empty_query(self, mock_handlers):
        """Test memory.search fails with empty query"""
        params = {"persona_id": "test_persona", "query": ""}  # Empty query
        
        with pytest.raises(ValueError, match="query is required"):
            await mock_handlers.handle_memory_search(params)
    
    @pytest.mark.asyncio
    async def test_missing_persona_id_without_session(self, mock_handlers):
        """Test memory.search fails when no persona_id and no session"""
        # Clear websocket_id to simulate no session
        mock_handlers.websocket_id = None
        
        params = {"query": "test query"}  # Missing persona_id, no session
        
        with pytest.raises(ValueError, match="persona_id is required"):
            await mock_handlers.handle_memory_search(params)
    
    @pytest.mark.asyncio
    async def test_valid_memory_search_with_defaults(self, mock_handlers):
        """Test memory.search works with valid minimal params"""
        # Mock memory search results
        mock_handlers.memory.search_memories = AsyncMock(return_value=[])
        
        params = {"persona_id": "test_persona", "query": "test query"}
        
        result = await mock_handlers.handle_memory_search(params)
        
        # Should call with default values
        mock_handlers.memory.search_memories.assert_called_once_with(
            "test_persona",
            "test query", 
            n_results=5,  # Default
            memory_type=None,
            min_importance=0.0  # Default
        )
        
        assert "memories" in result


class TestPersonaCreateValidation:
    """Test persona.create input validation"""
    
    @pytest.mark.asyncio
    async def test_missing_name(self, mock_handlers):
        """Test persona.create fails with missing name"""
        params = {"description": "Test description"}  # Missing name
        
        with pytest.raises(ValueError, match="name is required"):
            await mock_handlers.handle_persona_create(params)
    
    @pytest.mark.asyncio
    async def test_empty_name(self, mock_handlers):
        """Test persona.create fails with empty name"""
        params = {"name": "", "description": "Test description"}  # Empty name
        
        with pytest.raises(ValueError, match="name is required"):
            await mock_handlers.handle_persona_create(params)
    
    @pytest.mark.asyncio
    async def test_valid_persona_create_with_defaults(self, mock_handlers, sample_persona):
        """Test persona.create works with minimal valid params"""
        # Mock successful persona creation
        mock_handlers.db.save_persona = AsyncMock(return_value=True)
        mock_handlers.memory.initialize_persona_memory = AsyncMock()
        
        params = {"name": "NewPersona", "description": "A new test persona"}
        
        result = await mock_handlers.handle_persona_create(params)
        
        # Should create persona with expected response format
        assert result["name"] == "NewPersona"
        assert result["created"] == True
        assert "persona_id" in result
        
        # Should have called save_persona and initialize_persona_memory
        mock_handlers.db.save_persona.assert_called_once()
        mock_handlers.memory.initialize_persona_memory.assert_called_once()


class TestNumericValidation:
    """Test numeric parameter validation"""
    
    @pytest.mark.asyncio
    async def test_memory_search_invalid_n_results(self, mock_handlers):
        """Test memory.search handles invalid n_results gracefully"""
        mock_handlers.memory.search_memories = AsyncMock(return_value=[])
        
        # Test with string instead of number
        params = {
            "persona_id": "test_persona", 
            "query": "test",
            "n_results": "invalid"
        }
        
        # Should either convert or use default, not crash
        result = await mock_handlers.handle_memory_search(params)
        assert "memories" in result
    
    @pytest.mark.asyncio
    async def test_memory_search_invalid_min_importance(self, mock_handlers):
        """Test memory.search handles invalid min_importance gracefully"""
        mock_handlers.memory.search_memories = AsyncMock(return_value=[])
        
        # Test with string instead of float
        params = {
            "persona_id": "test_persona",
            "query": "test", 
            "min_importance": "invalid"
        }
        
        # Should either convert or use default, not crash
        result = await mock_handlers.handle_memory_search(params)
        assert "memories" in result


class TestErrorMessageQuality:
    """Test that error messages are helpful and informative"""
    
    @pytest.mark.asyncio
    async def test_error_messages_include_context(self, mock_handlers):
        """Test error messages include relevant context"""
        # Test persona not found includes the ID that was searched for
        mock_handlers.db.load_persona = AsyncMock(return_value=None)
        mock_handlers.db.list_personas = AsyncMock(return_value=[])
        
        params = {"persona_id": "specific_missing_id"}
        
        with pytest.raises(ValueError) as exc_info:
            await mock_handlers.handle_persona_switch(params)
        
        error_message = str(exc_info.value)
        assert "specific_missing_id" in error_message
        assert "Persona not found" in error_message
    
    @pytest.mark.asyncio
    async def test_unavailable_persona_includes_name(self, mock_handlers, sample_persona):
        """Test unavailable persona error includes persona name"""
        # Make persona unavailable
        sample_persona.interaction_state.social_energy = -10
        sample_persona.name = "SpecificPersonaName"
        
        mock_handlers.db.load_persona = AsyncMock(return_value=sample_persona)
        
        params = {"persona_id": "test_persona_id"}
        
        with pytest.raises(ValueError) as exc_info:
            await mock_handlers.handle_persona_switch(params)
        
        error_message = str(exc_info.value)
        assert "SpecificPersonaName" in error_message
        assert "not available for interaction" in error_message


if __name__ == "__main__":
    pytest.main([__file__, "-v"])