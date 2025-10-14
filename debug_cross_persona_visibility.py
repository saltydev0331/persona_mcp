#!/usr/bin/env python3
"""
Debug script for cross-persona memory visibility
"""

import asyncio
import json
import websockets

async def debug_cross_persona_memory():
    uri = "ws://localhost:8000/mcp"
    
    try:
        websocket = await websockets.connect(uri)
        
        # Helper to send requests
        async def send_request(method, params=None):
            request = {
                "jsonrpc": "2.0",
                "method": method,
                "params": params or {},
                "id": "debug"
            }
            await websocket.send(json.dumps(request))
            response = await websocket.recv()
            return json.loads(response)
        
        print("=== DEBUGGING CROSS-PERSONA MEMORY VISIBILITY ===")
        
        # Switch to Aria
        personas_response = await send_request("persona.list")
        aria_id = personas_response["result"]["personas"][0]["id"]
        await send_request("persona.switch", {"persona_id": aria_id})
        print(f"✓ Switched to Aria: {aria_id}")
        
        # Store test memory with explicit visibility
        store_response = await send_request("memory.store", {
            "content": "DEBUG: Aria's test shared memory",
            "visibility": "shared",
            "importance": 0.8,
            "memory_type": "manual"
        })
        print(f"✓ Stored shared memory: {store_response['result']['memory_id']}")
        
        # Store private memory 
        private_response = await send_request("memory.store", {
            "content": "DEBUG: Aria's test private memory", 
            "visibility": "private",
            "importance": 0.8,
            "memory_type": "manual"
        })
        print(f"✓ Stored private memory: {private_response['result']['memory_id']}")
        
        # Switch to Kira
        kira_id = personas_response["result"]["personas"][1]["id"]
        await send_request("persona.switch", {"persona_id": kira_id})
        print(f"✓ Switched to Kira: {kira_id}")
        
        # Search cross-persona with verbose output
        search_response = await send_request("memory.search_cross_persona", {
            "query": "DEBUG Aria test memory",
            "n_results": 5,
            "min_importance": 0.1,
            "include_shared": True,
            "include_public": True
        })
        
        print("\n=== CROSS-PERSONA SEARCH RESULTS ===")
        memories = search_response["result"]["memories"] 
        for i, memory in enumerate(memories):
            print(f"{i+1}. Content: {memory['content'][:50]}...")
            print(f"   Visibility: {memory['visibility']}")
            print(f"   Source: {memory['source_persona']}")
            print(f"   Importance: {memory['importance']}")
            print()
        
        print(f"Found {len(memories)} memories")
        private_count = len([m for m in memories if m['visibility'] == 'private'])
        shared_count = len([m for m in memories if m['visibility'] == 'shared']) 
        public_count = len([m for m in memories if m['visibility'] == 'public'])
        
        print(f"Private: {private_count}, Shared: {shared_count}, Public: {public_count}")
        
        if private_count > 0:
            print("⚠️  WARNING: Found private memories in cross-persona search!")
        else:
            print("✓ No private memories found (correct)")
        
        await websocket.close()
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_cross_persona_memory())