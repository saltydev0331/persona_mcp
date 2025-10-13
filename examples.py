"""
Example usage scripts for the Persona MCP Server
"""

import asyncio
import json
import websockets
from typing import Dict, Any


class MCPClient:
    """Simple MCP client for testing the server"""
    
    def __init__(self, uri: str = "ws://localhost:8000/mcp"):
        self.uri = uri
        self.websocket = None
        self.request_id = 0
    
    async def connect(self):
        """Connect to the MCP server"""
        self.websocket = await websockets.connect(self.uri)
        print(f"Connected to {self.uri}")
    
    async def disconnect(self):
        """Disconnect from the server"""
        if self.websocket:
            await self.websocket.close()
    
    async def send_request(self, method: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Send a JSON-RPC 2.0 request"""
        self.request_id += 1
        
        request = {
            "jsonrpc": "2.0",
            "method": method,
            "id": str(self.request_id)
        }
        
        if params:
            request["params"] = params
        
        # Send request
        await self.websocket.send(json.dumps(request))
        
        # Get response
        response_str = await self.websocket.recv()
        response = json.loads(response_str)
        
        return response
    
    async def list_personas(self):
        """List all available personas"""
        response = await self.send_request("persona.list")
        return response.get("result", {})
    
    async def switch_persona(self, persona_id: str):
        """Switch to a specific persona"""
        response = await self.send_request("persona.switch", {"persona_id": persona_id})
        return response.get("result", {})
    
    async def chat(self, message: str):
        """Send a chat message to the current persona"""
        response = await self.send_request("persona.chat", {"message": message})
        return response.get("result", {})
    
    async def system_status(self):
        """Get system status"""
        response = await self.send_request("system.status")
        return response.get("result", {})


async def basic_conversation_example():
    """Example: Basic conversation with a persona"""
    
    client = MCPClient()
    
    try:
        await client.connect()
        
        print("=== Persona MCP Server - Basic Conversation Example ===\n")
        
        # Get system status
        print("1. Checking system status...")
        status = await client.system_status()
        print(f"   System: {status.get('system_status')}")
        print(f"   LLM Available: {status.get('llm_available')}")
        print(f"   Total Personas: {status.get('total_personas')}")
        print()
        
        # List available personas
        print("2. Listing available personas...")
        personas_result = await client.list_personas()
        personas = personas_result.get("personas", [])
        
        for i, persona in enumerate(personas):
            print(f"   {i+1}. {persona['name']} - {persona['description']}")
            print(f"      Available: {persona['available']}, Energy: {persona['social_energy']}")
        print()
        
        if not personas:
            print("No personas available!")
            return
        
        # Switch to first available persona
        available_personas = [p for p in personas if p["available"]]
        if not available_personas:
            print("No personas are currently available!")
            return
        
        selected_persona = available_personas[0]
        print(f"3. Switching to {selected_persona['name']}...")
        
        switch_result = await client.switch_persona(selected_persona["id"])
        print(f"   Switched to: {switch_result.get('name')}")
        print(f"   Status: {switch_result.get('status')}")
        print()
        
        # Have a conversation
        print("4. Starting conversation...")
        conversation_messages = [
            "Hello! How are you today?",
            "What do you like to talk about?",
            "Tell me something interesting about yourself.",
            "I should probably let you go now."
        ]
        
        for i, message in enumerate(conversation_messages):
            print(f"   User: {message}")
            
            chat_result = await client.chat(message)
            response = chat_result.get("response", "No response")
            continue_score = chat_result.get("continue_score", 0)
            
            print(f"   {selected_persona['name']}: {response}")
            print(f"   [Continue Score: {continue_score}]")
            print()
            
            # Small delay between messages
            await asyncio.sleep(1)
        
        print("Conversation completed!")
        
    finally:
        await client.disconnect()


async def persona_comparison_example():
    """Example: Compare how different personas respond to the same question"""
    
    client = MCPClient()
    
    try:
        await client.connect()
        
        print("=== Persona Comparison Example ===\n")
        
        # Get personas
        personas_result = await client.list_personas()
        personas = [p for p in personas_result.get("personas", []) if p["available"]]
        
        if len(personas) < 2:
            print("Need at least 2 available personas for comparison!")
            return
        
        question = "What's your opinion on magic and its role in society?"
        
        print(f"Question: {question}\n")
        
        for persona in personas[:2]:  # Compare first 2 personas
            print(f"Switching to {persona['name']}...")
            await client.switch_persona(persona["id"])
            
            result = await client.chat(question)
            response = result.get("response", "No response")
            
            print(f"{persona['name']}: {response}")
            print(f"Continue Score: {result.get('continue_score')}")
            print()
        
    finally:
        await client.disconnect()


async def memory_search_example():
    """Example: Test memory search functionality"""
    
    client = MCPClient()
    
    try:
        await client.connect()
        
        print("=== Memory Search Example ===\n")
        
        # Switch to a persona
        personas_result = await client.list_personas()
        personas = [p for p in personas_result.get("personas", []) if p["available"]]
        
        if not personas:
            print("No available personas!")
            return
        
        persona = personas[0]
        await client.switch_persona(persona["id"])
        print(f"Using persona: {persona['name']}\n")
        
        # Have some conversation to build memory
        conversation_topics = [
            "I love reading fantasy books.",
            "Yesterday I saw a beautiful sunset.",
            "I'm interested in learning about magic.",
            "Music always makes me feel better."
        ]
        
        print("Building conversation history...")
        for topic in conversation_topics:
            result = await client.chat(topic)
            print(f"   Discussed: {topic}")
        
        print("\nSearching memories...")
        
        # Search for memories
        search_result = await client.send_request("memory.search", {
            "query": "magic and books",
            "n_results": 3
        })
        
        memories = search_result.get("result", {}).get("memories", [])
        
        if memories:
            print(f"Found {len(memories)} relevant memories:")
            for i, memory in enumerate(memories, 1):
                print(f"   {i}. {memory['content'][:100]}...")
                print(f"      Importance: {memory['importance']:.2f}")
        else:
            print("No memories found.")
        
    finally:
        await client.disconnect()


async def simulation_monitoring_example():
    """Example: Monitor simulation in real-time"""
    
    client = MCPClient()
    
    try:
        await client.connect()
        
        print("=== Simulation Monitoring Example ===\n")
        print("This example monitors the server state over time.")
        print("(Run the simulation with: python -m persona_mcp.simulation.chatroom)")
        print("Press Ctrl+C to stop monitoring\n")
        
        try:
            while True:
                # Get system status
                status = await client.system_status()
                
                print(f"Time: {status.get('timestamp', 'unknown')}")
                print(f"Active Conversations: {status.get('active_conversations', 0)}")
                print(f"Available Personas: {status.get('available_personas', 0)}")
                
                # Get persona states
                personas_result = await client.list_personas()
                personas = personas_result.get("personas", [])
                
                for persona in personas:
                    energy = persona.get("social_energy", 0)
                    available = persona.get("available", False)
                    status_icon = "✅" if available else "😴"
                    
                    print(f"  {status_icon} {persona['name']}: Energy {energy}")
                
                print("-" * 40)
                await asyncio.sleep(10)  # Check every 10 seconds
                
        except KeyboardInterrupt:
            print("Monitoring stopped.")
        
    finally:
        await client.disconnect()


if __name__ == "__main__":
    print("Persona MCP Server - Example Usage")
    print("=" * 40)
    print("1. Basic Conversation")
    print("2. Persona Comparison") 
    print("3. Memory Search")
    print("4. Simulation Monitoring")
    print()
    
    choice = input("Select example (1-4): ").strip()
    
    if choice == "1":
        asyncio.run(basic_conversation_example())
    elif choice == "2":
        asyncio.run(persona_comparison_example())
    elif choice == "3":
        asyncio.run(memory_search_example())
    elif choice == "4":
        asyncio.run(simulation_monitoring_example())
    else:
        print("Invalid choice. Running basic conversation example...")
        asyncio.run(basic_conversation_example())