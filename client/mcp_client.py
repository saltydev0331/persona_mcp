"""
MCP Test Client for Persona Server

A comprehensive WebSocket client for testing the Persona MCP server.
Supports all MCP methods and provides interactive testing capabilities.

Usage:
    python mcp_client.py                    # Interactive mode
    python mcp_client.py --auto-test        # Run automated tests
    python mcp_client.py --method persona.list  # Single method test
"""

import asyncio
import json
import websockets
import sys
import argparse
from datetime import datetime
from typing import Dict, Any, Optional

class MCPTestClient:
    def __init__(self, uri: str = "ws://localhost:8000/mcp"):
        self.uri = uri
        self.websocket = None
        self.request_id = 0
        self.current_persona = None
        
    def get_next_id(self) -> str:
        self.request_id += 1
        return str(self.request_id)
    
    async def connect(self) -> bool:
        """Connect to the MCP server"""
        try:
            self.websocket = await websockets.connect(self.uri)
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ✓ Connected to MCP server at {self.uri}")
            return True
        except Exception as e:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ✗ Failed to connect: {e}")
            return False
    
    async def send_request(self, method: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Send a JSON-RPC request and get response"""
        if not self.websocket:
            raise Exception("Not connected to server")
        
        request = {
            "jsonrpc": "2.0",
            "method": method,
            "id": self.get_next_id()
        }
        
        if params:
            request["params"] = params
            
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] → Sending: {method}")
        if params:
            print(f"    Params: {json.dumps(params, indent=2)}")
            
        await self.websocket.send(json.dumps(request))
        response_raw = await self.websocket.recv()
        response = json.loads(response_raw)
        
        if "error" in response and response["error"] is not None:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ✗ Error: {response['error']}")
        else:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ✓ Success")
            if "result" in response:
                print(f"    Result: {json.dumps(response['result'], indent=2)}")
                
        return response
    
    async def close(self):
        """Close the connection"""
        if self.websocket:
            await self.websocket.close()
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Connection closed")
    
    # MCP Method Wrappers
    async def list_personas(self):
        """List all available personas"""
        return await self.send_request("persona.list")
    
    async def switch_persona(self, persona_id: str):
        """Switch to a different persona"""
        result = await self.send_request("persona.switch", {"persona_id": persona_id})
        if "result" in result:
            self.current_persona = persona_id
        return result
    
    async def chat(self, message: str, token_budget: int = 500):
        """Chat with the current persona"""
        return await self.send_request("persona.chat", {
            "message": message,
            "token_budget": token_budget
        })
    
    async def query_memory(self, query: str, limit: int = 5):
        """Query conversation memory"""
        return await self.send_request("persona.memory", {
            "query": query,
            "limit": limit
        })
    
    async def get_relationship(self, target_persona: str = None):
        """Get relationship status with another persona"""
        params = {}
        if target_persona:
            params["target_persona"] = target_persona
        return await self.send_request("persona.relationship", params)
    
    async def get_status(self):
        """Get current persona status"""
        return await self.send_request("persona.status")

class InteractiveClient:
    """Interactive command-line interface for the MCP client"""
    
    def __init__(self, client: MCPTestClient):
        self.client = client
        self.running = True
    
    def print_help(self):
        """Print available commands"""
        print("\n" + "="*60)
        print("MCP PERSONA CLIENT - INTERACTIVE MODE")
        print("="*60)
        print("Available commands:")
        print("  list                          - List all personas")
        print("  switch <persona_id>           - Switch to persona (aria/kira)")
        print("  chat <message>                - Chat with current persona")
        print("  memory <query>                - Search conversation memory")
        print("  relationship [target]         - Check relationship status")
        print("  status                        - Get current persona status")
        print("  raw <method> [params_json]    - Send raw MCP request")
        print("  help                          - Show this help")
        print("  quit/exit                     - Exit the client")
        print("="*60)
        print(f"Current persona: {self.client.current_persona or 'None'}")
        print("="*60)
    
    async def run(self):
        """Run the interactive client"""
        self.print_help()
        
        while self.running:
            try:
                command = input("\nmcp> ").strip().split()
                if not command:
                    continue
                
                cmd = command[0].lower()
                args = command[1:] if len(command) > 1 else []
                
                if cmd in ['quit', 'exit']:
                    self.running = False
                elif cmd == 'help':
                    self.print_help()
                elif cmd == 'list':
                    await self.client.list_personas()
                elif cmd == 'switch':
                    if args:
                        await self.client.switch_persona(args[0])
                    else:
                        print("Usage: switch <persona_id>")
                elif cmd == 'chat':
                    if args:
                        message = ' '.join(args)
                        await self.client.chat(message)
                    else:
                        print("Usage: chat <message>")
                elif cmd == 'memory':
                    if args:
                        query = ' '.join(args)
                        await self.client.query_memory(query)
                    else:
                        print("Usage: memory <query>")
                elif cmd == 'relationship':
                    target = args[0] if args else None
                    await self.client.get_relationship(target)
                elif cmd == 'status':
                    await self.client.get_status()
                elif cmd == 'raw':
                    if args:
                        method = args[0]
                        params = None
                        if len(args) > 1:
                            try:
                                params = json.loads(' '.join(args[1:]))
                            except json.JSONDecodeError:
                                print("Invalid JSON parameters")
                                continue
                        await self.client.send_request(method, params)
                    else:
                        print("Usage: raw <method> [params_json]")
                else:
                    print(f"Unknown command: {cmd}. Type 'help' for available commands.")
                    
            except KeyboardInterrupt:
                print("\nExiting...")
                self.running = False
            except Exception as e:
                print(f"Error: {e}")

async def run_auto_test(client: MCPTestClient):
    """Run automated tests of all MCP functionality"""
    print("\n" + "="*60)
    print("RUNNING AUTOMATED MCP TESTS")
    print("="*60)
    
    try:
        # Test 1: List personas
        print("\n🧪 Test 1: List Available Personas")
        response = await client.list_personas()
        
        # Test 2: Switch to Aria
        print("\n🧪 Test 2: Switch to Aria Persona")
        await client.switch_persona("aria")
        
        # Test 3: Chat with Aria
        print("\n🧪 Test 3: Chat with Aria")
        await client.chat("Hello Aria! Can you introduce yourself?")
        
        # Test 4: Query memory
        print("\n🧪 Test 4: Query Conversation Memory")
        await client.query_memory("introduction")
        
        # Test 5: Check relationship status
        print("\n🧪 Test 5: Check Relationship Status")
        await client.get_relationship()
        
        # Test 6: Switch to Kira
        print("\n🧪 Test 6: Switch to Kira Persona")
        await client.switch_persona("kira")
        
        # Test 7: Chat with Kira
        print("\n🧪 Test 7: Chat with Kira")
        await client.chat("Hi Kira! What makes you different from Aria?")
        
        # Test 8: Get current status
        print("\n🧪 Test 8: Get Current Status")
        await client.get_status()
        
        print("\n" + "="*60)
        print("✓ ALL TESTS COMPLETED")
        print("="*60)
        
    except Exception as e:
        print(f"\n✗ Test failed: {e}")

async def main():
    parser = argparse.ArgumentParser(description="MCP Test Client for Persona Server")
    parser.add_argument("--uri", default="ws://localhost:8000/mcp", help="MCP server URI")
    parser.add_argument("--auto-test", action="store_true", help="Run automated tests")
    parser.add_argument("--method", help="Single method to test")
    parser.add_argument("--params", help="JSON parameters for single method test")
    
    args = parser.parse_args()
    
    client = MCPTestClient(args.uri)
    
    # Connect to server
    if not await client.connect():
        return 1
    
    try:
        if args.auto_test:
            # Run automated tests
            await run_auto_test(client)
        elif args.method:
            # Run single method test
            params = None
            if args.params:
                try:
                    params = json.loads(args.params)
                except json.JSONDecodeError:
                    print("Invalid JSON parameters")
                    return 1
            await client.send_request(args.method, params)
        else:
            # Interactive mode
            interactive = InteractiveClient(client)
            await interactive.run()
            
    finally:
        await client.close()
    
    return 0

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\nExiting...")
        sys.exit(0)