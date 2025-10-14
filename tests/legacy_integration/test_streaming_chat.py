#!/usr/bin/env python3
"""
Test client for streaming persona chat

Validates the new WebSocket streaming functionality.
"""

import asyncio
import json
import logging
import websockets
import time
from datetime import datetime


async def test_streaming_chat():
    """Test the streaming chat functionality"""
    
    print("🌊 Testing WebSocket Streaming Chat")
    print("=" * 50)
    
    uri = "ws://localhost:8000/mcp"
    
    try:
        async with websockets.connect(uri) as websocket:
            print("✅ Connected to MCP WebSocket server")
            
            # Step 1: List personas
            print("\n1. Listing available personas...")
            list_request = {
                "jsonrpc": "2.0",
                "method": "persona.list",
                "id": "list_1"
            }
            await websocket.send(json.dumps(list_request))
            response = await websocket.recv()
            personas_data = json.loads(response)
            
            if "result" in personas_data and personas_data["result"]["personas"]:
                personas = personas_data["result"]["personas"]
                print(f"   Found {len(personas)} personas:")
                for persona in personas:
                    print(f"   - {persona['name']}: {persona['description'][:50]}...")
                
                # Step 2: Switch to first persona
                first_persona = personas[0]
                print(f"\n2. Switching to persona: {first_persona['name']}")
                
                switch_request = {
                    "jsonrpc": "2.0",
                    "method": "persona.switch",
                    "params": {"persona_id": first_persona["id"]},
                    "id": "switch_1"
                }
                await websocket.send(json.dumps(switch_request))
                response = await websocket.recv()
                switch_data = json.loads(response)
                
                if "result" in switch_data:
                    print(f"   ✅ Switched to {first_persona['name']}")
                else:
                    print(f"   ❌ Switch failed: {switch_data}")
                    return
                
                # Step 3: Test streaming chat
                print(f"\n3. Testing streaming chat with {first_persona['name']}...")
                
                stream_request = {
                    "jsonrpc": "2.0",
                    "method": "persona.chat_stream",
                    "params": {
                        "message": "Tell me a very short joke about programming",
                        "token_budget": 200
                    },
                    "id": "stream_1"
                }
                
                print(f"   Sending: '{stream_request['params']['message']}'")
                print("   Streaming response:")
                print("   " + "-" * 40)
                
                await websocket.send(json.dumps(stream_request))
                
                # Collect streaming events
                events = []
                start_time = time.time()
                full_response = ""
                
                while True:
                    try:
                        # Wait for next message with timeout
                        response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                        event_data = json.loads(response)
                        
                        if "result" in event_data:
                            event_type = event_data["result"]["event_type"]
                            events.append(event_data)
                            
                            if event_type == "stream_start":
                                print(f"   🚀 Stream started (ID: {event_data['result']['stream_id'][:8]}...)")
                                
                            elif event_type == "stream_chunk":
                                chunk = event_data["result"]["data"]["chunk"]
                                chunk_num = event_data["result"]["data"]["chunk_number"]
                                full_response += chunk
                                print(f"   📝 Chunk {chunk_num:2d}: '{chunk}'", end="", flush=True)
                                
                            elif event_type == "stream_complete":
                                data = event_data["result"]["data"]
                                elapsed = time.time() - start_time
                                print(f"\n   ✅ Stream complete!")
                                print(f"   📊 Chunks: {data['chunk_count']}, Time: {elapsed:.2f}s")
                                print(f"   📝 Response: '{data['full_response']}'")
                                break
                                
                            elif event_type == "stream_error":
                                error_info = event_data['result'].get('error', {})
                                if isinstance(error_info, dict):
                                    error_msg = error_info.get('data', error_info.get('message', 'Unknown error'))
                                else:
                                    error_msg = str(error_info)
                                print(f"\n   ❌ Stream error: {error_msg}")
                                print(f"   📝 Full error: {event_data}")
                                break
                                
                            elif event_type == "stream_cancelled":
                                print(f"\n   🛑 Stream cancelled")
                                break
                        
                        elif "error" in event_data:
                            print(f"\n   ❌ Request error: {event_data['error']}")
                            break
                            
                    except asyncio.TimeoutError:
                        print(f"\n   ⏱️  Stream timeout after 10s")
                        break
                
                print("   " + "-" * 40)
                
                # Step 4: Test regular chat for comparison
                print(f"\n4. Testing regular chat for comparison...")
                
                regular_request = {
                    "jsonrpc": "2.0",
                    "method": "persona.chat",
                    "params": {
                        "message": "Tell me another short joke",
                        "token_budget": 200
                    },
                    "id": "regular_1"
                }
                
                regular_start = time.time()
                await websocket.send(json.dumps(regular_request))
                response = await websocket.recv()
                regular_time = time.time() - regular_start
                regular_data = json.loads(response)
                
                if "result" in regular_data:
                    print(f"   Regular response ({regular_time:.2f}s): '{regular_data['result']['response']}'")
                else:
                    print(f"   Regular chat error: {regular_data}")
                
                # Summary
                print(f"\n" + "=" * 50)
                print("🎯 STREAMING TEST SUMMARY")
                print("=" * 50)
                
                if events:
                    stream_events = len(events)
                    has_chunks = any(e["result"]["event_type"] == "stream_chunk" for e in events)
                    
                    print(f"✅ WebSocket streaming integration working")
                    print(f"✅ JSON-RPC 2.0 streaming events: {stream_events}")
                    print(f"✅ Progressive chunk delivery: {'Yes' if has_chunks else 'No'}")
                    print(f"✅ Full response reconstruction: {'Yes' if full_response else 'No'}")
                    
                    if full_response:
                        print(f"📝 Final response length: {len(full_response)} chars")
                    
                    print(f"\n🚀 Streaming vs Regular:")
                    streaming_time = elapsed if 'elapsed' in locals() else 0
                    if streaming_time > 0 and regular_time > 0:
                        if streaming_time < regular_time:
                            improvement = ((regular_time - streaming_time) / regular_time) * 100
                            print(f"   ⚡ Streaming faster by {improvement:.1f}%")
                        else:
                            print(f"   🐌 Regular faster (streaming adds overhead for short responses)")
                        print(f"   📊 Streaming: {streaming_time:.2f}s, Regular: {regular_time:.2f}s")
                    
                else:
                    print("❌ No streaming events received")
                
            else:
                print("   ❌ No personas found")
                
    except (websockets.exceptions.ConnectionClosed, ConnectionRefusedError, OSError):
        print("❌ Cannot connect to MCP server")
        print("💡 Make sure the server is running: python server.py")
        
    except Exception as e:
        print(f"❌ Test error: {e}")
        import traceback
        traceback.print_exc()


async def test_streaming_control():
    """Test streaming control features (cancellation, etc.)"""
    
    print("\n🛑 Testing Streaming Control Features")
    print("=" * 50)
    
    uri = "ws://localhost:8000/mcp"
    
    try:
        async with websockets.connect(uri) as websocket:
            print("✅ Connected for control tests")
            
            # Switch to a persona first
            personas_request = {
                "jsonrpc": "2.0",
                "method": "persona.list",
                "id": "control_list"
            }
            await websocket.send(json.dumps(personas_request))
            response = await websocket.recv()
            personas_data = json.loads(response)
            
            if "result" in personas_data and personas_data["result"]["personas"]:
                first_persona = personas_data["result"]["personas"][0]
                
                switch_request = {
                    "jsonrpc": "2.0",
                    "method": "persona.switch", 
                    "params": {"persona_id": first_persona["id"]},
                    "id": "control_switch"
                }
                await websocket.send(json.dumps(switch_request))
                await websocket.recv()  # Consume response
                
                print(f"   Switched to {first_persona['name']}")
                
                # Start a stream and then close connection quickly
                print("   Testing connection handling...")
                
                stream_request = {
                    "jsonrpc": "2.0",
                    "method": "persona.chat_stream",
                    "params": {
                        "message": "Tell me a long story about space exploration and alien civilizations",
                        "token_budget": 500
                    },
                    "id": "control_stream"
                }
                
                await websocket.send(json.dumps(stream_request))
                
                # Read first few events then disconnect
                for i in range(3):
                    response = await websocket.recv()
                    event = json.loads(response)
                    if "result" in event:
                        event_type = event["result"]["event_type"] 
                        print(f"   Received: {event_type}")
                
                print("   🛑 Simulating connection close...")
                # Connection will close when we exit the context
                
            print("✅ Connection control test completed")
            
    except Exception as e:
        print(f"❌ Control test error: {e}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    async def main():
        await test_streaming_chat()
        await asyncio.sleep(1)  # Brief pause
        await test_streaming_control()
    
    asyncio.run(main())