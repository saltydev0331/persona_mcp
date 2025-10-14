#!/usr/bin/env python3
"""
Streaming Test Client for MCP Persona Server

This client properly handles streaming responses to show real-time text generation.
"""

import asyncio
import json
import websockets
from datetime import datetime

async def test_streaming():
    uri = "ws://localhost:8000/mcp"
    
    try:
        async with websockets.connect(uri) as websocket:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ✓ Connected to MCP server")
            
            # First, switch to Aria
            switch_request = {
                "jsonrpc": "2.0",
                "method": "persona.switch",
                "params": {"persona_id": "aria"},
                "id": "1"
            }
            
            await websocket.send(json.dumps(switch_request))
            response = await websocket.recv()
            switch_result = json.loads(response)
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ✓ Switched to {switch_result['result']['name']}")
            
            # Now start streaming chat
            stream_request = {
                "jsonrpc": "2.0",
                "method": "persona.chat_stream",
                "params": {
                    "message": "Tell me a detailed story about your most memorable adventure as a bard",
                    "token_budget": 1000
                },
                "id": "2"
            }
            
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] → Starting streaming chat...")
            await websocket.send(json.dumps(stream_request))
            
            # Collect streaming responses
            response_text = ""
            chunk_count = 0
            
            while True:
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=30.0)
                    data = json.loads(message)
                    
                    if "result" in data:
                        event_type = data["result"].get("event_type")
                        
                        if event_type == "stream_start":
                            print(f"[{datetime.now().strftime('%H:%M:%S')}] 🚀 Stream started")
                            print(f"[{datetime.now().strftime('%H:%M:%S')}] 📝 Aria says:")
                            
                        elif event_type == "stream_chunk":
                            chunk = data["result"]["data"].get("chunk", "")
                            response_text += chunk
                            chunk_count += 1
                            # Print each chunk in real-time
                            print(chunk, end="", flush=True)
                            
                        elif event_type == "stream_complete":
                            print(f"\n\n[{datetime.now().strftime('%H:%M:%S')}] ✅ Stream complete!")
                            print(f"[{datetime.now().strftime('%H:%M:%S')}] 📊 Received {chunk_count} chunks")
                            
                            # Show final stats
                            final_data = data["result"]["data"]
                            print(f"[{datetime.now().strftime('%H:%M:%S')}] 🔢 Total tokens: {final_data.get('tokens_used', 0)}")
                            print(f"[{datetime.now().strftime('%H:%M:%S')}] ⏱️  Processing time: {final_data.get('processing_time', 0):.2f}s")
                            break
                            
                        elif event_type == "stream_error":
                            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] ❌ Stream error: {data['result']['data']}")
                            break
                            
                except asyncio.TimeoutError:
                    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] ⏰ Stream timeout - no more data")
                    break
                except Exception as e:
                    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] ❌ Error: {e}")
                    break
            
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 🏁 Streaming test complete")
            
    except Exception as e:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ Connection failed: {e}")

if __name__ == "__main__":
    print("=" * 60)
    print("MCP PERSONA SERVER - STREAMING TEST")
    print("=" * 60)
    asyncio.run(test_streaming())