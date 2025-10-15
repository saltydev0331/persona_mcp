#!/usr/bin/env python3
"""
Quick test to check if MCP server WebSocket is reachable
"""

import asyncio
import websockets
import json

async def test_mcp_connection():
    uri = "ws://localhost:8000/mcp"
    print(f"Testing connection to {uri}")
    
    try:
        async with websockets.connect(uri) as websocket:
            print("✅ Connected successfully!")
            
            # Send a simple test message
            test_message = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "ping",
                "params": {}
            }
            
            await websocket.send(json.dumps(test_message))
            print("📤 Sent test message")
            
            # Wait for response (with timeout)
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                print(f"📥 Received: {response}")
            except asyncio.TimeoutError:
                print("⏰ No response received (timeout)")
                
    except Exception as e:
        print(f"❌ Connection failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_mcp_connection())