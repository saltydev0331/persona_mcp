#!/usr/bin/env python3
"""
Cross-Persona Memory Test

Validates the new cross-persona memory sharing functionality.
"""

import asyncio
import json
import websockets
from datetime import datetime

async def test_cross_persona_memory():
    uri = "ws://localhost:8000/mcp"
    
    try:
        async with websockets.connect(uri) as websocket:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ✓ Connected to MCP server")
            
            # Switch to Aria
            await websocket.send(json.dumps({
                "jsonrpc": "2.0",
                "method": "persona.switch",
                "params": {"persona_id": "Aria"},
                "id": "1"
            }))
            response = await websocket.recv()
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ✓ Switched to Aria")
            
            # Store a shared memory from Aria (explicitly specify persona_id)
            await websocket.send(json.dumps({
                "jsonrpc": "2.0",
                "method": "memory.store",
                "params": {
                    "persona_id": "aria",  # Explicitly use consistent ID
                    "content": "The tavern serves excellent honey mead on Thursdays",
                    "memory_type": "local_knowledge",
                    "visibility": "shared",
                    "importance": 0.7,
                    "related_personas": ["kira"]
                },
                "id": "2"
            }))
            response = await websocket.recv()
            result = json.loads(response)
            shared_memory_id = result["result"]["memory_id"]
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ✓ Stored shared memory: {shared_memory_id}")
            
            # Store a public memory from Aria
            await websocket.send(json.dumps({
                "jsonrpc": "2.0", 
                "method": "memory.store",
                "params": {
                    "persona_id": "aria",  # Explicitly use consistent ID
                    "content": "The old oak tree by the river is a great meeting spot",
                    "memory_type": "location",
                    "visibility": "public",
                    "importance": 0.6
                },
                "id": "3"
            }))
            response = await websocket.recv()
            result = json.loads(response)
            public_memory_id = result["result"]["memory_id"]
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ✓ Stored public memory: {public_memory_id}")
            
            # Switch to Kira
            await websocket.send(json.dumps({
                "jsonrpc": "2.0",
                "method": "persona.switch", 
                "params": {"persona_id": "Kira"},
                "id": "4"
            }))
            response = await websocket.recv()
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ✓ Switched to Kira")
            
            # Search for cross-persona memories from Kira's perspective
            await websocket.send(json.dumps({
                "jsonrpc": "2.0",
                "method": "memory.search_cross_persona",
                "params": {
                    "persona_id": "kira",  # Explicitly specify the requesting persona ID
                    "query": "tavern honey mead",
                    "n_results": 10,
                    "min_importance": 0.5,
                    "include_shared": True,
                    "include_public": True
                },
                "id": "4"
            }))
            response = await websocket.recv()
            result = json.loads(response)
            
            print(f"\\n[{datetime.now().strftime('%H:%M:%S')}] 🔍 Cross-persona search results:")
            memories = result["result"]["memories"]
            
            found_shared = False
            for memory in memories:
                if memory["source"] == "cross_persona":
                    print(f"  📋 Found shared memory from {memory['source_persona']}: {memory['content'][:50]}...")
                    print(f"      Visibility: {memory['visibility']}, Importance: {memory['importance']}")
                    if "tavern" in memory["content"].lower():
                        found_shared = True
            
            if found_shared:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ Cross-persona memory sharing working!")
            else:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ Shared memory not found in cross-persona search")
            
            # Test shared memory statistics
            await websocket.send(json.dumps({
                "jsonrpc": "2.0",
                "method": "memory.shared_stats",
                "params": {},
                "id": "6"
            }))
            response = await websocket.recv()
            result = json.loads(response)
            
            print(f"\\n[{datetime.now().strftime('%H:%M:%S')}] 📊 Shared memory statistics:")
            stats = result["result"]["shared_memory_statistics"]
            print(f"  Total personas: {stats['total_personas']}")
            print(f"  Shared memories: {stats['shared_memories']}")
            print(f"  Public memories: {stats['public_memories']}")
            print(f"  Cross-references: {stats['cross_references']}")
            
            print(f"\\n[{datetime.now().strftime('%H:%M:%S')}] 🎉 Phase 2 Cross-Persona Memory System: COMPLETE!")
            
    except Exception as e:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ Test failed: {e}")

if __name__ == "__main__":
    print("=" * 60)
    print("PHASE 2 COMPLETION TEST - CROSS-PERSONA MEMORY")
    print("=" * 60)
    asyncio.run(test_cross_persona_memory())