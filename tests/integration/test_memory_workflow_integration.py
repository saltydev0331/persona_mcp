#!/usr/bin/env python3
"""
Integration tests for memory workflow functionality

Tests the complete memory integration workflow including conversation storage,
memory search, and cross-session persistence.
"""

import pytest
import asyncio
import json
import websockets
import time
from typing import Dict, Any, List, Optional

from persona_mcp.logging import get_logger


class MemoryWorkflowTester:
    """Helper class for memory workflow integration tests"""
    
    def __init__(self, uri: str = "ws://localhost:8000/mcp"):
        self.uri = uri
        self.logger = get_logger(__name__)
        self.websocket = None
        self.request_id = 0
    
    async def __aenter__(self):
        """Async context manager entry"""
        self.websocket = await websockets.connect(self.uri)
        self.logger.info(f"Connected to MCP server at {self.uri}")
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.websocket:
            await self.websocket.close()
            self.logger.info("Connection closed")
    
    def get_next_id(self) -> str:
        """Get next request ID"""
        self.request_id += 1
        return str(self.request_id)
    
    async def send_request(self, method: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Send MCP request and return response"""
        request = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {},
            "id": self.get_next_id()
        }
        
        await self.websocket.send(json.dumps(request))
        response = await asyncio.wait_for(self.websocket.recv(), timeout=10.0)
        return json.loads(response)
    
    async def setup_persona(self, persona_index: int = 0) -> str:
        """Setup by switching to a specific persona, returns persona_id"""
        # List personas
        list_response = await self.send_request("persona.list")
        assert "result" in list_response, "Failed to list personas"
        
        personas = list_response["result"]["personas"]
        assert len(personas) > persona_index, f"Not enough personas (need at least {persona_index + 1})"
        
        # Switch to target persona
        target_persona = personas[persona_index]
        switch_response = await self.send_request(
            "persona.switch",
            {"persona_id": target_persona["id"]}
        )
        
        assert "result" in switch_response, "Failed to switch persona"
        result = switch_response["result"]
        assert "persona_id" in result, "Switch response missing persona_id"
        assert result["persona_id"] == target_persona["id"], "Switched to wrong persona"
        
        return target_persona["id"]
    
    async def chat_and_create_memories(self, messages: List[str]) -> List[str]:
        """Send multiple chat messages to create memories, returns responses"""
        responses = []
        
        for message in messages:
            response = await self.send_request("persona.chat", {
                "message": message,
                "token_budget": 300
            })
            
            assert "result" in response, f"Chat failed for message: {message}"
            assert response["result"] is not None, f"Chat result is None for message: {message}"
            assert "response" in response["result"], f"Chat result missing 'response' field for message: {message}"
            
            responses.append(response["result"]["response"])
            
            # Small delay between messages to ensure proper sequencing
            await asyncio.sleep(0.5)
        
        return responses


@pytest.mark.asyncio
@pytest.mark.integration
async def test_memory_workflow_basic():
    """Test basic memory workflow: chat -> search memories"""
    async with MemoryWorkflowTester() as tester:
        # Setup persona
        persona_id = await tester.setup_persona(0)
        
        # Create some memories through conversation
        test_messages = [
            "I love reading about magical theories and ancient spells",
            "Tell me about your favorite books on enchantment", 
            "What's your opinion on defensive magic versus offensive spells?"
        ]
        
        responses = await tester.chat_and_create_memories(test_messages)
        assert len(responses) == len(test_messages)
        
        # Wait a moment for memory storage to complete
        await asyncio.sleep(2.0)
        
        # Search for memories
        search_response = await tester.send_request("memory.search", {
            "persona_id": persona_id,
            "query": "magic spells",
            "limit": 10
        })
        
        assert "result" in search_response, "Memory search failed"
        memories = search_response["result"]["memories"]
        
        # Should find memories related to our conversations
        assert len(memories) > 0, "Should find some memories"
        
        # Check memory structure
        for memory in memories:
            required_fields = ["content", "importance", "memory_type", "created_at"]
            for field in required_fields:
                assert field in memory, f"Memory missing field: {field}"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_memory_search_relevance():
    """Test that memory search returns relevant results"""
    async with MemoryWorkflowTester() as tester:
        persona_id = await tester.setup_persona(0)
        
        # Create distinct memory topics
        messages = [
            "I'm fascinated by quantum computing and its potential applications",
            "Machine learning algorithms are revolutionizing data analysis",
            "Python is my favorite programming language for data science",
            "I enjoy hiking in the mountains during weekends",
            "Classical music helps me concentrate while coding"
        ]
        
        await tester.chat_and_create_memories(messages)
        await asyncio.sleep(2.0)  # Wait for memory storage
        
        # Search for programming-related memories
        search_response = await tester.send_request("memory.search", {
            "persona_id": persona_id,
            "query": "programming Python coding",
            "limit": 5
        })
        
        assert "result" in search_response
        memories = search_response["result"]["memories"]
        
        # Should find relevant memories
        assert len(memories) > 0, "Should find programming-related memories"
        
        # Check that results are actually relevant
        programming_terms = ["python", "programming", "coding", "algorithm", "quantum", "machine learning"]
        found_relevant = False
        
        for memory in memories:
            content_lower = memory["content"].lower()
            if any(term in content_lower for term in programming_terms):
                found_relevant = True
                break
        
        assert found_relevant, "Search results should be relevant to the query"


@pytest.mark.asyncio 
@pytest.mark.integration
async def test_memory_persistence_across_sessions():
    """Test that memories persist across different chat sessions"""
    async with MemoryWorkflowTester() as tester:
        persona_id = await tester.setup_persona(0)
        
        # First session - create memories
        first_session_messages = [
            "My name is Alice and I work as a software developer",
            "I specialize in backend systems using Go and PostgreSQL"
        ]
        
        await tester.chat_and_create_memories(first_session_messages)
        await asyncio.sleep(1.5)
        
    # Second session - new connection, same persona
    async with MemoryWorkflowTester() as tester:
        persona_id = await tester.setup_persona(0)
        
        # Try to recall information from previous session
        recall_message = "Do you remember what my name is and what I do for work?"
        
        recall_response = await tester.send_request("persona.chat", {
            "message": recall_message,
            "token_budget": 200
        })
        
        assert "result" in recall_response
        response_text = recall_response["result"]["response"].lower()
        
        # Should reference Alice or software developer (based on memory)
        memory_indicators = ["alice", "software", "developer", "backend", "go", "postgresql"]
        found_memory_reference = any(indicator in response_text for indicator in memory_indicators)
        
        # Also check memory search directly
        search_response = await tester.send_request("memory.search", {
            "persona_id": persona_id,
            "query": "Alice software developer",
            "limit": 5
        })
        
        assert "result" in search_response
        memories = search_response["result"]["memories"]
        assert len(memories) > 0, "Should find memories from previous session"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_memory_stats_and_management():
    """Test memory statistics and management functions"""
    async with MemoryWorkflowTester() as tester:
        persona_id = await tester.setup_persona(0)
        
        # Create some memories
        messages = [
            "I love artificial intelligence research",
            "Neural networks are fascinating computational models",
            "Deep learning has transformed computer vision"
        ]
        
        await tester.chat_and_create_memories(messages)
        await asyncio.sleep(2.0)
        
        # Get memory statistics
        stats_response = await tester.send_request("memory.stats", {
            "persona_id": persona_id
        })
        
        assert "result" in stats_response, "Memory stats request failed"
        stats = stats_response["result"]
        
        # Check stats structure
        expected_fields = ["total_memories", "memory_types", "avg_importance", "created_today"]
        for field in expected_fields:
            assert field in stats, f"Stats missing field: {field}"
        
        # Should have some memories
        assert stats["total_memories"] > 0, "Should have created some memories"
        
        # Test memory search with specific persona_id
        search_response = await tester.send_request("memory.search", {
            "persona_id": persona_id,
            "query": "artificial intelligence",
            "limit": 3
        })
        
        assert "result" in search_response
        memories = search_response["result"]["memories"]
        
        # Verify search results
        assert len(memories) > 0, "Should find AI-related memories"


@pytest.mark.asyncio
@pytest.mark.integration 
async def test_memory_importance_scoring():
    """Test that memory importance scoring works correctly"""
    async with MemoryWorkflowTester() as tester:
        persona_id = await tester.setup_persona(0)
        
        # Create memories with different expected importance levels
        messages = [
            "Hello there!",  # Low importance - simple greeting
            "I am getting married next month and I'm very excited!",  # High importance - major life event
            "The weather is nice today",  # Low importance - casual comment  
            "I just got diagnosed with a serious medical condition",  # High importance - major personal issue
        ]
        
        await tester.chat_and_create_memories(messages)
        await asyncio.sleep(2.0)
        
        # Search for all memories to check importance scores
        search_response = await tester.send_request("memory.search", {
            "persona_id": persona_id,
            "query": "married medical weather hello",  # Broad query to get all
            "limit": 10
        })
        
        assert "result" in search_response
        memories = search_response["result"]["memories"]
        assert len(memories) > 0
        
        # Check that importance scores exist and are reasonable
        importance_scores = [memory["importance"] for memory in memories]
        
        # Should have a range of importance scores
        assert min(importance_scores) >= 0.0, "Importance should be non-negative"
        assert max(importance_scores) <= 1.0, "Importance should not exceed 1.0"
        
        # Should have some variation in scores
        if len(importance_scores) > 1:
            assert max(importance_scores) > min(importance_scores), "Should have varied importance scores"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])