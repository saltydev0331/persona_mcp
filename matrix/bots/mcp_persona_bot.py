"""
MCP-Connected Persona Bot - Full Intelligence Bridge

This bot connects Matrix to the persona-mcp backend for true AI persona interactions
with memory, relationships, and LLM-powered responses.
"""

import asyncio
import sys
import logging
import time
import json
from typing import Optional, Dict, Any
import websockets
from nio import AsyncClient, MatrixRoom, RoomMessageText, InviteEvent, JoinError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MCPPersonaBot:
    """Matrix bot with full MCP backend integration"""
    
    def __init__(self, persona_name: str):
        self.persona_name = persona_name
        self.homeserver = "http://localhost:8008"
        self.user_id = f"@{persona_name.lower()}:localhost"
        self.password = f"{persona_name.lower()}123"
        self.matrix_client = AsyncClient(self.homeserver, self.user_id)
        
        # MCP WebSocket connection
        self.mcp_uri = "ws://localhost:8000/mcp"
        self.mcp_websocket = None
        self.mcp_session_id = None
        
        # State tracking
        self.has_introduced = set()
        self.start_time = time.time()
        self.is_connected_to_mcp = False
        
    async def start(self):
        """Start the MCP-connected persona bot"""
        try:
            logger.info(f"🚀 Starting MCP-connected {self.persona_name}...")
            
            # Step 1: Connect to MCP server
            await self.connect_to_mcp()
            
            # Step 2: Initialize persona in MCP
            await self.initialize_persona()
            
            # Step 3: Connect to Matrix
            await self.connect_to_matrix()
            
            # Step 4: Start main loop
            await self.run_main_loop()
            
        except Exception as e:
            logger.error(f"❌ {self.persona_name} startup error: {e}")
        finally:
            await self.cleanup()
    
    async def connect_to_mcp(self):
        """Connect to the MCP server via WebSocket"""
        try:
            logger.info(f"🔌 {self.persona_name} connecting to MCP server...")
            self.mcp_websocket = await websockets.connect(self.mcp_uri)
            self.is_connected_to_mcp = True
            logger.info(f"✅ {self.persona_name} connected to MCP server")
        except Exception as e:
            logger.error(f"❌ {self.persona_name} failed to connect to MCP: {e}")
            raise
    
    async def initialize_persona(self):
        """Initialize or switch to the persona in MCP"""
        try:
            # First, try to switch to existing persona
            switch_request = {
                "jsonrpc": "2.0",
                "id": f"switch_{int(time.time())}",
                "method": "persona.switch",
                "params": {"persona_id": self.persona_name.lower()}  # Try with name first
            }
            
            await self.mcp_websocket.send(json.dumps(switch_request))
            response = await self.mcp_websocket.recv()
            result = json.loads(response)
            
            logger.info(f"🔍 Switch response: {result}")
            
            if "error" in result and result["error"] is not None:
                # Persona doesn't exist, create it
                logger.info(f"🆕 {self.persona_name} not found, creating new persona...")
                logger.info(f"🔍 Switch error was: {result['error']}")
                
                create_request = {
                    "jsonrpc": "2.0",
                    "id": f"create_{int(time.time())}",
                    "method": "persona.create",
                    "params": {
                        "name": self.persona_name.lower(),
                        "full_name": self.persona_name,
                        "background": f"I am {self.persona_name}, a conversational AI persona. I enjoy chatting and getting to know people in our Matrix chatroom.",
                        "personality_traits": {
                            "friendliness": "high",
                            "curiosity": "high", 
                            "helpfulness": "high",
                            "engagement": "high",
                            "humor": "moderate"
                        },
                        "speaking_style": "casual and warm",
                        "interests": ["conversation", "learning", "helping others"]
                    }
                }
                
                await self.mcp_websocket.send(json.dumps(create_request))
                create_response = await self.mcp_websocket.recv()
                create_result = json.loads(create_response)
                
                logger.info(f"🔍 Create response: {create_result}")
                
                if "error" in create_result and create_result["error"] is not None:
                    error_msg = create_result['error'].get('message', 'Unknown error') if isinstance(create_result['error'], dict) else create_result['error']
                    raise Exception(f"Failed to create persona: {error_msg}")
                
                # Extract the persona ID from creation response
                persona_data = create_result.get("result", {})
                persona_id = persona_data.get("persona_id")
                
                if not persona_id:
                    raise Exception("No persona_id returned from creation")
                
                logger.info(f"✅ {self.persona_name} persona created successfully with ID: {persona_id}")
                
                # Now switch to the newly created persona using its ID
                switch_request_with_id = {
                    "jsonrpc": "2.0",
                    "id": f"switch_new_{int(time.time())}",
                    "method": "persona.switch",
                    "params": {"persona_id": persona_id}
                }
                
                await self.mcp_websocket.send(json.dumps(switch_request_with_id))
                switch_response = await self.mcp_websocket.recv()
                switch_result = json.loads(switch_response)
                
                logger.info(f"🔍 Final switch response: {switch_result}")
                
                if "error" in switch_result and switch_result["error"] is not None:
                    error_msg = switch_result['error'].get('message', 'Unknown error') if isinstance(switch_result['error'], dict) else switch_result['error']
                    raise Exception(f"Failed to switch to persona: {error_msg}")
            
            logger.info(f"✅ {self.persona_name} persona initialized in MCP")
            
        except Exception as e:
            logger.error(f"❌ {self.persona_name} persona initialization failed: {e}")
            raise
    
    async def connect_to_matrix(self):
        """Connect to Matrix server"""
        try:
            logger.info(f"🔐 {self.persona_name} connecting to Matrix...")
            
            response = await self.matrix_client.login(self.password)
            if not hasattr(response, 'access_token'):
                raise Exception(f"Matrix login failed: {response}")
                
            logger.info(f"✅ {self.persona_name} connected to Matrix")
            
            # Set up callbacks
            self.matrix_client.add_event_callback(self.message_callback, RoomMessageText)
            self.matrix_client.add_event_callback(self.invite_callback, InviteEvent)
            
            # Small delay to ensure we're synced, then reset start time
            await asyncio.sleep(2)
            self.start_time = time.time()
            logger.info(f"⏰ {self.persona_name} ready to respond to NEW messages with MCP intelligence!")
            
        except Exception as e:
            logger.error(f"❌ {self.persona_name} Matrix connection failed: {e}")
            raise
    
    async def run_main_loop(self):
        """Run the main bot loop with Matrix sync"""
        # Create a task for Matrix sync
        sync_task = asyncio.create_task(self.matrix_client.sync_forever(timeout=30000))
        
        # Wait for the sync task (will run indefinitely)
        await sync_task
    
    async def invite_callback(self, room: MatrixRoom, event: InviteEvent):
        """Handle room invitations"""
        logger.info(f"📨 {self.persona_name} received invite to room")
        
        try:
            await self.matrix_client.join(room.room_id)
            logger.info(f"✅ {self.persona_name} joined room: {room.display_name or room.room_id}")
            
            # Send MCP-powered introduction
            if room.room_id not in self.has_introduced:
                introduction = await self.get_mcp_response("I just joined this Matrix chatroom. Please introduce yourself.")
                if introduction:
                    await self.matrix_client.room_send(
                        room_id=room.room_id,
                        message_type="m.room.message",
                        content={"msgtype": "m.text", "body": introduction}
                    )
                    self.has_introduced.add(room.room_id)
                    logger.info(f"📤 {self.persona_name} sent MCP-powered introduction")
                else:
                    # Fallback introduction
                    await self.matrix_client.room_send(
                        room_id=room.room_id,
                        message_type="m.room.message",
                        content={"msgtype": "m.text", "body": f"👋 Hello! I'm {self.persona_name}, powered by MCP intelligence. Great to be here!"}
                    )
                    self.has_introduced.add(room.room_id)
            
        except Exception as e:
            logger.error(f"❌ {self.persona_name} invite handling error: {e}")
    
    async def message_callback(self, room: MatrixRoom, event: RoomMessageText):
        """Handle messages with MCP-powered responses"""
        if event.sender == self.user_id:
            return  # Don't respond to own messages
        
        # Only respond to messages sent AFTER the bot started
        message_time = event.server_timestamp / 1000
        if message_time < self.start_time:
            return  # Ignore historical messages
        
        sender_name = event.sender.split(':')[0][1:]
        message = event.body
        
        # **NEVER respond to other bots** - prevents infinite loops
        if sender_name in ["alice", "bob", "charlie", "testbot"]:
            logger.info(f"🤐 {self.persona_name} ignoring bot message from {sender_name}")
            return
        
        logger.info(f"💬 {room.display_name}: {sender_name}: {message[:100]}...")
        
        # Check if we should respond (same logic as conversational bot but MCP-powered)
        should_respond = False
        persona_lower = self.persona_name.lower()
        
        # DEBUG: Log decision process
        logger.info(f"🔍 Checking if {self.persona_name} should respond to: '{message}'")
        
        # 1. Direct mentions always get a response
        if f"@{persona_lower}" in message.lower():
            should_respond = True
            logger.info(f"🎯 Direct mention detected - will respond")
        
        # 2. Direct address (name at start)
        elif message.lower().startswith(f"{persona_lower}"):
            should_respond = True
            logger.info(f"🎯 Direct address detected - will respond")
        
        # 2b. Direct address (name mentioned anywhere in short messages)
        elif persona_lower in message.lower() and len(message.split()) <= 4:
            should_respond = True  
            logger.info(f"🎯 Name mention in short message detected - will respond")
        
        # 3. General greetings (respond sometimes)
        elif any(greeting in message.lower() for greeting in ["hello everyone", "hi everyone", "hey everyone", "good morning", "good afternoon"]):
            should_respond = self._should_respond_randomly(0.8)  # 80% chance (higher for testing)
            logger.info(f"🎯 General greeting detected - respond: {should_respond}")
        
        # 4. Simple greetings
        elif any(greeting in message.lower() for greeting in ["hello", "hi", "hey"]) and len(message.split()) <= 2:
            should_respond = self._should_respond_randomly(0.7)  # 70% chance (higher for testing)
            logger.info(f"🎯 Simple greeting detected - respond: {should_respond}")
        
        # 5. Questions to the room
        elif "?" in message and len(message.split()) >= 3:
            should_respond = self._should_respond_randomly(0.6)  # 60% chance (higher for testing)
            logger.info(f"🎯 Question detected - respond: {should_respond}")
        
        # 6. Follow-up conversational patterns
        elif any(phrase in message.lower() for phrase in ["how are you", "how's it going", "what's up", "how do you do", "i'm good", "i am!", "doing well"]):
            should_respond = self._should_respond_randomly(0.5)  # 50% chance
            logger.info(f"🎯 Conversational pattern detected - respond: {should_respond}")
        
        else:
            logger.info(f"🤐 No response trigger matched for: '{message}'")
        
        if should_respond:
            logger.info(f"🚀 {self.persona_name} WILL respond to message from {sender_name}")
            try:
                # Get MCP-powered response
                logger.info(f"🧠 Requesting MCP response for: '{message[:50]}...'")
                mcp_response = await self.get_mcp_response(message)
                
                if mcp_response:
                    await self.matrix_client.room_send(
                        room_id=room.room_id,
                        message_type="m.room.message",
                        content={"msgtype": "m.text", "body": mcp_response}
                    )
                    
                    logger.info(f"📤 {self.persona_name} → {sender_name}: {mcp_response[:80]}... [MCP-powered]")
                else:
                    logger.warning(f"⚠️ {self.persona_name} got empty response from MCP")
                
            except Exception as e:
                logger.error(f"❌ {self.persona_name} failed to respond: {e}")
        else:
            logger.info(f"🤐 {self.persona_name} decided NOT to respond to: '{message}'")
    
    async def get_mcp_response(self, message: str) -> Optional[str]:
        """Get an intelligent response from the MCP server (optimized for chat)"""
        if not self.is_connected_to_mcp or not self.mcp_websocket:
            logger.warning(f"⚠️ {self.persona_name} not connected to MCP server")
            return None
        
        try:
            # Use regular chat for Matrix (streaming doesn't work well with Matrix's atomic messages)
            chat_request = {
                "jsonrpc": "2.0",
                "id": f"chat_{int(time.time())}",
                "method": "persona.chat",
                "params": {
                    "message": message,
                    "token_budget": 150  # Keep responses concise for chat
                }
            }
            
            logger.info(f"🧠 Sending MCP chat request...")
            
            await self.mcp_websocket.send(json.dumps(chat_request))
            response = await self.mcp_websocket.recv()
            result = json.loads(response)
            
            if "error" in result and result["error"] is not None:
                error_msg = result['error'].get('message', 'Unknown error') if isinstance(result['error'], dict) else result['error']
                logger.error(f"❌ MCP error: {error_msg}")
                return None
            
            # Extract the response content
            response_data = result.get("result", {})
            response_text = response_data.get("response", "")
            
            if response_text:
                # Strip quotes if the response is wrapped in them
                if response_text.startswith('"') and response_text.endswith('"'):
                    response_text = response_text[1:-1]
                elif response_text.startswith("'") and response_text.endswith("'"):
                    response_text = response_text[1:-1]
                
                processing_time = response_data.get("processing_time", 0)
                logger.info(f"⚡ {self.persona_name} got response in {processing_time:.2f}s: {response_text[:50]}...")
                return response_text
            else:
                logger.warning(f"⚠️ {self.persona_name} got empty response from MCP")
                return None
                
        except Exception as e:
            logger.error(f"❌ {self.persona_name} MCP communication error: {e}")
            return None
    
    def _should_respond_randomly(self, probability: float) -> bool:
        """Random response decision with given probability"""
        import random
        return random.random() < probability
    
    async def cleanup(self):
        """Clean up connections"""
        try:
            if self.mcp_websocket:
                await self.mcp_websocket.close()
                logger.info(f"🔌 {self.persona_name} MCP connection closed")
        except:
            pass
        
        try:
            await self.matrix_client.close()
            logger.info(f"🔌 {self.persona_name} Matrix connection closed")
        except:
            pass

async def main():
    if len(sys.argv) != 2:
        print("Usage: python mcp_persona_bot.py <PersonaName>")
        print("Example: python mcp_persona_bot.py Alice")
        return
    
    persona_name = sys.argv[1].capitalize()
    
    if persona_name not in ["Alice", "Bob", "Charlie"]:
        print(f"❌ Unknown persona: {persona_name}")
        print("Available personas: Alice, Bob, Charlie")
        return
    
    print(f"🤖 Starting MCP-CONNECTED {persona_name}...")
    print("🧠 This bot uses full persona-mcp intelligence!")
    print("🔗 Connecting to MCP server on localhost:8000")
    print("Press Ctrl+C to stop")
    
    bot = MCPPersonaBot(persona_name)
    
    try:
        await bot.start()
    except KeyboardInterrupt:
        print(f"\n🛑 Stopping {persona_name}...")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())