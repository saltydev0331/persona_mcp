#!/usr/bin/env python3
"""
Test ChromaDB Memory Integration - Full Workflow

This script tests the complete memory workflow:
1. Connect to MCP server
2. List available personas  
3. Switch to a persona
4. Chat to generate memories
5. Search memories
"""

import asyncio
import json
import websockets
from datetime import datetime

class MemoryTestClient:
    def __init__(self, uri="ws://localhost:8000/mcp"):
        self.uri = uri
        self.websocket = None
        self.request_id = 0

    def get_next_id(self):
        self.request_id += 1
        return str(self.request_id)

    async def connect(self):
        """Connect to the MCP server"""
        try:
            self.websocket = await websockets.connect(self.uri)
            print(f"✓ Connected to MCP server at {self.uri}")
            return True
        except Exception as e:
            print(f"✗ Failed to connect: {e}")
            return False

    async def send_request(self, method, params=None):
        """Send MCP request and return response"""
        request = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {},
            "id": self.get_next_id()
        }
        
        print(f"\n→ {method}")
        if params:
            print(f"  Params: {json.dumps(params, indent=2)}")
        
        await self.websocket.send(json.dumps(request))
        response = await self.websocket.recv()
        result = json.loads(response)
        
        if "error" in result and result["error"]:
            print(f"✗ Error: {result['error']}")
            return None
        else:
            print(f"✓ Success")
            return result.get("result")

    async def close(self):
        """Close connection"""
        if self.websocket:
            await self.websocket.close()
            print("Connection closed")

async def test_memory_workflow():
    """Test complete memory workflow"""
    client = MemoryTestClient()
    
    if not await client.connect():
        return
    
    try:
        # Step 1: List personas
        print("\n=== Step 1: List Available Personas ===")
        personas = await client.send_request("persona.list")
        
        if not personas or not personas.get("personas"):
            print("No personas found!")
            return
            
        print(f"Found {len(personas['personas'])} personas:")
        for persona in personas["personas"]:
            print(f"  - {persona['name']} (ID: {persona['id'][:8]}...)")
        
        # Step 2: Switch to first persona (Aria - the bard who loves stories)
        first_persona = personas["personas"][0]
        print(f"\n=== Step 2: Switch to {first_persona['name']} ===")
        
        switch_result = await client.send_request("persona.switch", {
            "persona_id": first_persona["id"]
        })
        
        if switch_result:
            print(f"✓ Switched to {switch_result['name']}")
        
        # Step 3: Have some conversations to create memories
        print(f"\n=== Step 3: Create Memories Through Conversation ===")
        
        conversations = [
            "I love reading about magical theories and ancient spells",
            "Tell me about your favorite books on enchantment",
            "What's your opinion on defensive magic versus offensive spells?",
            "I heard there's a new library opening with rare magical texts"
        ]
        
        for i, message in enumerate(conversations, 1):
            print(f"  Chat {i}: {message}")
            chat_result = await client.send_request("persona.chat", {
                "message": message,
                "token_budget": 300
            })
            
            if chat_result:
                print(f"    Response: {chat_result['response'][:60]}...")
            
            # Small delay between messages
            await asyncio.sleep(0.5)
        
        # Step 4: Search memories
        print(f"\n=== Step 4: Search Memories ===")
        
        search_queries = [
            "magic books",
            "spells and enchantment", 
            "library",
            "defensive magic"
        ]
        
        for query in search_queries:
            print(f"\n  Searching for: '{query}'")
            memories = await client.send_request("memory.search", {
                "query": query,
                "n_results": 3
            })
            
            if memories and memories.get("memories"):
                print(f"    Found {len(memories['memories'])} memories:")
                for j, memory in enumerate(memories["memories"], 1):
                    print(f"      {j}. {memory['content'][:80]}...")
                    print(f"         Importance: {memory['importance']:.2f}")
            else:
                print("    No memories found")
        
        # Step 5: Memory statistics
        print(f"\n=== Step 5: Memory Statistics ===")
        stats = await client.send_request("memory.stats")
        
        if stats:
            print(f"  Total memories: {stats.get('total_memories', 0)}")
            if 'memory_types' in stats:
                for mem_type, count in stats['memory_types'].items():
                    print(f"  {mem_type}: {count}")
        
    except Exception as e:
        print(f"Test failed: {e}")
    
    finally:
        await client.close()

if __name__ == "__main__":
    print("Testing ChromaDB Memory Integration")
    print("=" * 40)
    asyncio.run(test_memory_workflow())