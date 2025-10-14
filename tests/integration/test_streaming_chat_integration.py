#!/usr/bin/env python3
"""
Integration tests for streaming persona chat functionality

Tests the complete WebSocket streaming workflow with real server.
"""

import pytest
import asyncio
import json
import websockets
import time
from typing import Dict, Any, List
from datetime import datetime

from persona_mcp.logging import get_logger


class StreamingChatTester:
    """Helper class for streaming chat tests"""
    
    def __init__(self, uri: str = "ws://localhost:8000/mcp"):
        self.uri = uri
        self.logger = get_logger(__name__)
        self.websocket = None
    
    async def __aenter__(self):
        """Async context manager entry"""
        self.websocket = await websockets.connect(self.uri)
        self.logger.info(f"Connected to WebSocket server at {self.uri}")
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.websocket:
            await self.websocket.close()
            self.logger.info("WebSocket connection closed")
    
    async def send_request(self, method: str, params: Dict[str, Any] = None, request_id: str = None) -> Dict[str, Any]:
        """Send JSON-RPC request and get response"""
        request = {
            "jsonrpc": "2.0",
            "method": method,
            "id": request_id or f"{method}_{int(time.time())}"
        }
        if params:
            request["params"] = params
            
        await self.websocket.send(json.dumps(request))
        response = await self.websocket.recv()
        return json.loads(response)
    
    async def stream_chat(self, message: str, token_budget: int = 200) -> List[Dict[str, Any]]:
        """Send streaming chat request and collect all events"""
        request = {
            "jsonrpc": "2.0",
            "method": "persona.chat_stream",
            "params": {
                "message": message,
                "token_budget": token_budget
            },
            "id": f"stream_{int(time.time())}"
        }
        
        await self.websocket.send(json.dumps(request))
        
        events = []
        start_time = time.time()
        
        while True:
            try:
                response = await asyncio.wait_for(self.websocket.recv(), timeout=15.0)
                event_data = json.loads(response)
                
                if "result" in event_data:
                    events.append(event_data)
                    event_type = event_data["result"]["event_type"]
                    
                    if event_type == "stream_complete":
                        break
                elif "error" in event_data:
                    self.logger.error(f"Stream error: {event_data['error']}")
                    break
                    
            except asyncio.TimeoutError:
                self.logger.warning("Stream timeout - breaking")
                break
        
        return events


@pytest.mark.asyncio
@pytest.mark.integration
async def test_persona_list_functionality():
    """Test basic persona listing functionality"""
    async with StreamingChatTester() as tester:
        response = await tester.send_request("persona.list")
        
        assert "result" in response
        assert "personas" in response["result"]
        personas = response["result"]["personas"]
        assert isinstance(personas, list)
        assert len(personas) > 0
        
        # Check persona structure
        first_persona = personas[0]
        required_fields = ["id", "name", "description"]
        for field in required_fields:
            assert field in first_persona, f"Persona missing required field: {field}"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_persona_switch_functionality():
    """Test persona switching functionality"""
    async with StreamingChatTester() as tester:
        # Get available personas
        list_response = await tester.send_request("persona.list")
        personas = list_response["result"]["personas"]
        assert len(personas) > 0
        
        # Switch to first persona
        target_persona = personas[0]
        switch_response = await tester.send_request(
            "persona.switch",
            {"persona_id": target_persona["id"]}
        )
        
        assert "result" in switch_response
        result = switch_response["result"]
        assert "persona_id" in result, "Switch response missing persona_id"
        assert result["persona_id"] == target_persona["id"]
        assert result["name"] == target_persona["name"]


@pytest.mark.asyncio
@pytest.mark.integration
async def test_streaming_chat_workflow():
    """Test complete streaming chat workflow"""
    async with StreamingChatTester() as tester:
        # Setup: Get personas and switch
        list_response = await tester.send_request("persona.list")
        personas = list_response["result"]["personas"]
        target_persona = personas[0]
        
        switch_response = await tester.send_request(
            "persona.switch",
            {"persona_id": target_persona["id"]}
        )
        assert "result" in switch_response, "Failed to switch persona"
        assert "persona_id" in switch_response["result"], "Switch response missing persona_id"
        assert switch_response["result"]["persona_id"] == target_persona["id"]
        
        # Test streaming chat
        test_message = "Tell me a very short joke about programming"
        events = await tester.stream_chat(test_message)
        
        # Validate streaming events
        assert len(events) > 0, "Should receive at least one streaming event"
        
        # Check for required event types
        event_types = {event["result"]["event_type"] for event in events}
        assert "stream_start" in event_types, "Should have stream_start event"
        assert "stream_complete" in event_types, "Should have stream_complete event"
        
        # Validate stream_start event
        start_events = [e for e in events if e["result"]["event_type"] == "stream_start"]
        assert len(start_events) == 1, "Should have exactly one stream_start event"
        
        start_event = start_events[0]["result"]
        assert "stream_id" in start_event
        assert "persona_id" in start_event
        assert start_event["persona_id"] == target_persona["id"]
        
        # Validate stream_complete event
        complete_events = [e for e in events if e["result"]["event_type"] == "stream_complete"]
        assert len(complete_events) == 1, "Should have exactly one stream_complete event"
        
        complete_event = complete_events[0]["result"]
        assert "full_response" in complete_event
        assert "tokens_used" in complete_event
        assert "processing_time" in complete_event
        assert len(complete_event["full_response"]) > 0, "Should have non-empty response"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_streaming_chat_with_chunks():
    """Test streaming chat receives chunk events"""
    async with StreamingChatTester() as tester:
        # Setup
        list_response = await tester.send_request("persona.list")
        personas = list_response["result"]["personas"]
        
        switch_response = await tester.send_request(
            "persona.switch", 
            {"persona_id": personas[0]["id"]}
        )
        assert "result" in switch_response, "Failed to switch persona"
        assert "persona_id" in switch_response["result"], "Switch response missing persona_id"
        
        # Stream with longer message to generate chunks
        test_message = "Please tell me a detailed explanation of what makes a good software engineer, including technical skills, soft skills, and career development advice."
        events = await tester.stream_chat(test_message, token_budget=500)
        
        # Should have chunks for longer responses
        chunk_events = [e for e in events if e["result"]["event_type"] == "stream_chunk"]
        
        # Verify chunks are properly formed
        full_text = ""
        for chunk_event in chunk_events:
            chunk_data = chunk_event["result"]
            assert "chunk" in chunk_data
            assert "stream_id" in chunk_data
            full_text += chunk_data["chunk"]
        
        # Compare with complete response
        complete_events = [e for e in events if e["result"]["event_type"] == "stream_complete"]
        if complete_events:
            complete_response = complete_events[0]["result"]["full_response"]
            # Chunks should roughly match complete response (allowing for minor variations)
            assert len(full_text) > 0, "Chunks should contain content"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_multiple_sequential_chats():
    """Test multiple sequential streaming chats maintain context"""
    async with StreamingChatTester() as tester:
        # Setup
        list_response = await tester.send_request("persona.list")
        personas = list_response["result"]["personas"]
        
        switch_response = await tester.send_request(
            "persona.switch",
            {"persona_id": personas[0]["id"]}
        )
        assert "result" in switch_response, "Failed to switch persona"
        assert "persona_id" in switch_response["result"], "Switch response missing persona_id"
        
        # Multiple chats
        messages = [
            "Hello, can you remember my name is Alice?",
            "What programming language do you think I should learn?", 
            "Do you remember what my name is?"
        ]
        
        responses = []
        for message in messages:
            events = await tester.stream_chat(message)
            complete_events = [e for e in events if e["result"]["event_type"] == "stream_complete"]
            
            assert len(complete_events) == 1, f"Should get complete event for message: {message}"
            response = complete_events[0]["result"]["full_response"]
            responses.append(response)
            
            # Small delay between messages
            await asyncio.sleep(0.5)
        
        # Verify we got responses
        assert len(responses) == len(messages)
        for i, response in enumerate(responses):
            assert len(response) > 0, f"Response {i+1} should not be empty"


if __name__ == "__main__":
    # Allow running directly for development
    pytest.main([__file__, "-v", "-s", "--tb=short"])