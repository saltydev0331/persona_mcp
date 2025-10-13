"""
Tests for MCP protocol compliance and JSON-RPC handling
"""

import pytest
import json
import asyncio
from unittest.mock import AsyncMock, MagicMock

from persona_mcp.models import MCPRequest, MCPResponse, Persona
from persona_mcp.mcp.handlers import MCPHandlers
from persona_mcp.persistence import SQLiteManager, VectorMemoryManager
from persona_mcp.llm import LLMManager
from persona_mcp.conversation import ConversationEngine


@pytest.fixture
def mock_components():
    """Create mock components for testing"""
    
    db_manager = AsyncMock(spec=SQLiteManager)
    memory_manager = AsyncMock(spec=VectorMemoryManager)
    llm_manager = AsyncMock(spec=LLMManager)
    conversation_engine = AsyncMock(spec=ConversationEngine)
    
    return db_manager, memory_manager, llm_manager, conversation_engine


@pytest.fixture
def mcp_handlers(mock_components):
    """Create MCP handlers with mock components"""
    
    db_manager, memory_manager, llm_manager, conversation_engine = mock_components
    
    handlers = MCPHandlers(
        conversation_engine,
        db_manager,
        memory_manager,
        llm_manager
    )
    
    return handlers


class TestMCPProtocol:
    """Test MCP JSON-RPC 2.0 protocol compliance"""
    
    @pytest.mark.asyncio
    async def test_valid_request_format(self, mcp_handlers):
        """Test handling of valid JSON-RPC 2.0 request"""
        
        request_data = {
            "jsonrpc": "2.0",
            "method": "system.status",
            "id": "test-123"
        }
        
        response = await mcp_handlers.handle_request(request_data)
        
        assert response.jsonrpc == "2.0"
        assert response.id == "test-123"
        assert response.error is None
        assert response.result is not None
    
    @pytest.mark.asyncio
    async def test_invalid_method(self, mcp_handlers):
        """Test handling of invalid method"""
        
        request_data = {
            "jsonrpc": "2.0", 
            "method": "invalid.method",
            "id": "test-456"
        }
        
        response = await mcp_handlers.handle_request(request_data)
        
        assert response.jsonrpc == "2.0"
        assert response.id == "test-456"
        assert response.error is not None
        assert response.error["code"] == -32601  # Method not found
    
    @pytest.mark.asyncio
    async def test_request_without_id(self, mcp_handlers):
        """Test notification (request without id)"""
        
        request_data = {
            "jsonrpc": "2.0",
            "method": "system.status"
            # No id field = notification
        }
        
        response = await mcp_handlers.handle_request(request_data)
        
        assert response.jsonrpc == "2.0"
        assert response.id is None


class TestPersonaOperations:
    """Test persona-related MCP operations"""
    
    @pytest.mark.asyncio
    async def test_persona_list(self, mcp_handlers, mock_components):
        """Test persona.list method"""
        
        db_manager, _, _, _ = mock_components
        
        # Mock personas
        test_personas = [
            Persona(name="Aria", description="Bard"),
            Persona(name="Kira", description="Scholar")
        ]
        db_manager.list_personas.return_value = test_personas
        
        result = await mcp_handlers.handle_persona_list({})
        
        assert "personas" in result
        assert len(result["personas"]) == 2
        assert result["total_count"] == 2
        assert any(p["name"] == "Aria" for p in result["personas"])
        assert any(p["name"] == "Kira" for p in result["personas"])
    
    @pytest.mark.asyncio
    async def test_persona_switch_success(self, mcp_handlers, mock_components):
        """Test successful persona switch"""
        
        db_manager, _, _, _ = mock_components
        
        # Mock persona
        test_persona = Persona(name="Aria", description="Bard")
        test_persona.interaction_state.social_energy = 100
        db_manager.load_persona.return_value = test_persona
        
        params = {"persona_id": test_persona.id}
        result = await mcp_handlers.handle_persona_switch(params)
        
        assert result["persona_id"] == test_persona.id
        assert result["name"] == "Aria"
        assert result["status"] == "active"
        assert mcp_handlers.current_persona_id == test_persona.id
    
    @pytest.mark.asyncio
    async def test_persona_switch_not_found(self, mcp_handlers, mock_components):
        """Test persona switch with non-existent persona"""
        
        db_manager, _, _, _ = mock_components
        db_manager.load_persona.return_value = None
        
        params = {"persona_id": "non-existent"}
        
        with pytest.raises(ValueError, match="Persona not found"):
            await mcp_handlers.handle_persona_switch(params)
    
    @pytest.mark.asyncio
    async def test_persona_chat_no_persona(self, mcp_handlers):
        """Test chat without selecting persona first"""
        
        params = {"message": "Hello"}
        
        with pytest.raises(ValueError, match="No persona selected"):
            await mcp_handlers.handle_persona_chat(params)
    
    @pytest.mark.asyncio
    async def test_persona_create(self, mcp_handlers, mock_components):
        """Test persona creation"""
        
        db_manager, memory_manager, _, _ = mock_components
        db_manager.save_persona.return_value = True
        memory_manager.initialize_persona_memory.return_value = True
        
        params = {
            "name": "New Persona",
            "description": "A test persona",
            "charisma": 15
        }
        
        result = await mcp_handlers.handle_persona_create(params)
        
        assert result["name"] == "New Persona"
        assert result["created"] == True
        assert "persona_id" in result


class TestConversationOperations:
    """Test conversation-related MCP operations"""
    
    @pytest.mark.asyncio
    async def test_conversation_start(self, mcp_handlers, mock_components):
        """Test starting a conversation"""
        
        db_manager, _, _, conversation_engine = mock_components
        
        # Mock personas
        persona1 = Persona(name="Alice", description="Test")
        persona2 = Persona(name="Bob", description="Test")
        
        db_manager.load_persona.side_effect = [persona1, persona2]
        
        # Mock conversation context
        from persona_mcp.models import ConversationContext
        mock_context = ConversationContext(
            participants=[persona1.id, persona2.id],
            topic="general"
        )
        conversation_engine.initiate_conversation.return_value = mock_context
        
        params = {
            "persona1_id": persona1.id,
            "persona2_id": persona2.id,
            "topic": "general"
        }
        
        result = await mcp_handlers.handle_conversation_start(params)
        
        assert result["conversation_id"] == mock_context.id
        assert len(result["participants"]) == 2
        assert result["topic"] == "general"
        assert result["started"] == True


class TestSystemOperations:
    """Test system-related MCP operations"""
    
    @pytest.mark.asyncio
    async def test_system_status(self, mcp_handlers, mock_components):
        """Test system status endpoint"""
        
        db_manager, _, llm_manager, conversation_engine = mock_components
        
        # Mock components
        llm_manager.ollama.is_available.return_value = True
        db_manager.list_personas.return_value = [
            Persona(name="Aria", description="Bard"),
            Persona(name="Kira", description="Scholar")
        ]
        conversation_engine.active_conversations = {}
        
        result = await mcp_handlers.handle_system_status({})
        
        assert result["system_status"] == "operational"
        assert result["llm_available"] == True
        assert result["total_personas"] == 2
        assert result["active_conversations"] == 0
    
    @pytest.mark.asyncio
    async def test_system_models(self, mcp_handlers, mock_components):
        """Test system models endpoint"""
        
        _, _, llm_manager, _ = mock_components
        
        llm_manager.ollama.list_available_models.return_value = [
            "llama3.1:8b",
            "mistral:7b"
        ]
        llm_manager.ollama.default_model = "llama3.1:8b"
        
        result = await mcp_handlers.handle_system_models({})
        
        assert len(result["available_models"]) == 2
        assert "llama3.1:8b" in result["available_models"]
        assert result["current_model"] == "llama3.1:8b"
        assert result["provider"] == "ollama"


if __name__ == "__main__":
    pytest.main([__file__])