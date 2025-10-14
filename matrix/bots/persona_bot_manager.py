"""
Persona Bot Manager - Automated Matrix Bot Management

This script manages multiple persona bots, handles room invitations,
and automates the join process for multi-persona simulations.
"""

import asyncio
import json
from typing import Dict, List, Optional
from nio import AsyncClient, MatrixRoom, RoomMessageText, InviteEvent, JoinError
import websockets
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PersonaBot:
    def __init__(self, homeserver: str, user_id: str, password: str, persona_name: str):
        self.homeserver = homeserver
        self.user_id = user_id
        self.password = password
        self.persona_name = persona_name
        self.client = AsyncClient(homeserver, user_id)
        self.mcp_client = None
        self.rooms = set()
        
    async def start(self):
        """Start the persona bot"""
        try:
            # Login
            response = await self.client.login(self.password)
            if hasattr(response, 'access_token'):
                logger.info(f"✅ {self.persona_name} ({self.user_id}) logged in successfully")
            else:
                logger.error(f"❌ {self.persona_name} login failed: {response}")
                return False
                
            # Set up event callbacks
            self.client.add_event_callback(self.message_callback, RoomMessageText)
            self.client.add_event_callback(self.invite_callback, InviteEvent)
            
            # Connect to MCP backend (placeholder for now)
            await self.connect_to_mcp()
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error starting {self.persona_name}: {e}")
            return False
    
    async def connect_to_mcp(self):
        """Connect to persona-mcp backend (placeholder)"""
        # TODO: Implement WebSocket connection to persona-mcp
        logger.info(f"🔌 {self.persona_name} connecting to MCP backend...")
        # self.mcp_client = MCPWebSocketClient("ws://localhost:8000")
    
    async def message_callback(self, room: MatrixRoom, event: RoomMessageText):
        """Handle incoming messages"""
        if event.sender == self.user_id:
            return  # Don't respond to own messages
            
        logger.info(f"📝 {self.persona_name} received message in {room.display_name}: {event.body}")
        
        # Simple response for now - will be replaced with MCP integration
        if event.body.lower().startswith(f"@{self.persona_name.lower()}") or event.body.lower().startswith("hello"):
            await self.send_response(room.room_id, f"Hello! I'm {self.persona_name}, a persona from the MCP system.")
    
    async def invite_callback(self, room: MatrixRoom, event: InviteEvent):
        """Auto-accept room invitations"""
        logger.info(f"📨 {self.persona_name} received invite to room: {room.room_id}")
        
        try:
            # Accept the invitation
            await self.client.join(room.room_id)
            self.rooms.add(room.room_id)
            logger.info(f"✅ {self.persona_name} joined room: {room.room_id}")
            
            # Send introduction message
            await self.send_response(room.room_id, f"👋 Hello everyone! I'm {self.persona_name}. Looking forward to our conversations!")
            
        except JoinError as e:
            logger.error(f"❌ {self.persona_name} failed to join room {room.room_id}: {e}")
    
    async def send_response(self, room_id: str, message: str):
        """Send a message to a room"""
        try:
            await self.client.room_send(
                room_id=room_id,
                message_type="m.room.message",
                content={
                    "msgtype": "m.text",
                    "body": f"**{self.persona_name}**: {message}"
                }
            )
        except Exception as e:
            logger.error(f"❌ {self.persona_name} failed to send message: {e}")
    
    async def create_room(self, room_name: str, room_topic: str = "") -> Optional[str]:
        """Create a new Matrix room"""
        try:
            response = await self.client.room_create(
                visibility="private",
                name=room_name,
                topic=room_topic,
                initial_state=[{
                    "type": "m.room.history_visibility",
                    "content": {"history_visibility": "invited"}
                }]
            )
            
            if hasattr(response, 'room_id'):
                logger.info(f"🏠 {self.persona_name} created room: {room_name} ({response.room_id})")
                self.rooms.add(response.room_id)
                return response.room_id
            else:
                logger.error(f"❌ Failed to create room: {response}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error creating room: {e}")
            return None
    
    async def invite_to_room(self, room_id: str, user_id: str):
        """Invite a user to a room"""
        try:
            await self.client.room_invite(room_id, user_id)
            logger.info(f"📤 {self.persona_name} invited {user_id} to room {room_id}")
        except Exception as e:
            logger.error(f"❌ Failed to invite {user_id} to room {room_id}: {e}")

class PersonaBotManager:
    def __init__(self, homeserver: str = "http://localhost:8008"):
        self.homeserver = homeserver
        self.bots: Dict[str, PersonaBot] = {}
        self.running = False
    
    async def register_persona_bot(self, persona_name: str, password: str = None) -> bool:
        """Register a new persona bot account"""
        if password is None:
            password = f"{persona_name.lower()}123"
        
        username = persona_name.lower()
        user_id = f"@{username}:localhost"
        
        # Register the account
        registration_url = f"{self.homeserver}/_matrix/client/r0/register"
        registration_data = {
            "username": username,
            "password": password,
            "auth": {"type": "m.login.dummy"}
        }
        
        import aiohttp
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(registration_url, json=registration_data) as response:
                    if response.status == 200:
                        data = await response.json()
                        logger.info(f"✅ Registered persona bot: {user_id}")
                        
                        # Create bot instance
                        bot = PersonaBot(self.homeserver, user_id, password, persona_name)
                        self.bots[persona_name] = bot
                        return True
                    else:
                        error_text = await response.text()
                        if "User ID already taken" in error_text:
                            logger.info(f"ℹ️ User {user_id} already exists, creating bot instance")
                            # Create bot instance even if user exists
                            bot = PersonaBot(self.homeserver, user_id, password, persona_name)
                            self.bots[persona_name] = bot
                            return True
                        else:
                            logger.error(f"❌ Registration failed for {user_id}: {error_text}")
                            return False
                            
            except Exception as e:
                logger.error(f"❌ Error registering {user_id}: {e}")
                return False
    
    async def start_all_bots(self):
        """Start all registered persona bots"""
        if not self.bots:
            logger.warning("⚠️ No bots registered")
            return
        
        logger.info(f"🚀 Starting {len(self.bots)} persona bots...")
        
        tasks = []
        for persona_name, bot in self.bots.items():
            tasks.append(bot.start())
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Start sync loops for successful bots
        sync_tasks = []
        for i, (persona_name, bot) in enumerate(self.bots.items()):
            if results[i] is True:
                sync_tasks.append(bot.client.sync_forever(timeout=30000))
        
        if sync_tasks:
            self.running = True
            logger.info(f"🔄 Starting sync loops for {len(sync_tasks)} bots...")
            await asyncio.gather(*sync_tasks, return_exceptions=True)
    
    async def create_simulation_room(self, room_name: str, persona_names: List[str], human_user_id: str) -> Optional[str]:
        """Create a room and invite all specified personas and the human user"""
        if not self.bots:
            logger.error("❌ No bots available to create room")
            return None
        
        # Use first bot to create room
        creator_bot = list(self.bots.values())[0]
        room_topic = f"Multi-persona simulation with: {', '.join(persona_names)}"
        
        room_id = await creator_bot.create_room(room_name, room_topic)
        if not room_id:
            return None
        
        # Invite human user
        await creator_bot.invite_to_room(room_id, human_user_id)
        
        # Invite all specified personas
        for persona_name in persona_names:
            if persona_name in self.bots:
                bot = self.bots[persona_name]
                await creator_bot.invite_to_room(room_id, bot.user_id)
        
        logger.info(f"🎭 Created simulation room '{room_name}' with {len(persona_names)} personas")
        return room_id
    
    async def stop_all_bots(self):
        """Stop all bots gracefully"""
        logger.info("🛑 Stopping all persona bots...")
        self.running = False
        
        for bot in self.bots.values():
            try:
                await bot.client.close()
            except Exception as e:
                logger.error(f"Error stopping bot: {e}")

async def main():
    """Demo: Create and manage persona bots"""
    manager = PersonaBotManager()
    
    # Register some persona bots
    personas = ["Alice", "Bob", "Charlie"]
    
    print("🤖 Registering persona bots...")
    for persona in personas:
        success = await manager.register_persona_bot(persona)
        if not success:
            print(f"Failed to register {persona}")
            return
    
    print("✅ All persona bots registered!")
    print("🚀 Starting persona bots...")
    
    # Start bots in background
    start_task = asyncio.create_task(manager.start_all_bots())
    
    # Wait a moment for bots to initialize
    await asyncio.sleep(2)
    
    # Create a simulation room
    print("🏠 Creating simulation room...")
    room_id = await manager.create_simulation_room(
        room_name="Persona Simulation Room",
        persona_names=personas,
        human_user_id="@saltydev0331:localhost"  # Your user ID
    )
    
    if room_id:
        print(f"✅ Created room: {room_id}")
        print("🎭 All personas should auto-join and introduce themselves!")
        print("\nPress Ctrl+C to stop all bots...")
        
        try:
            await start_task
        except KeyboardInterrupt:
            print("\n🛑 Stopping bots...")
            await manager.stop_all_bots()
    else:
        print("❌ Failed to create room")
        await manager.stop_all_bots()

if __name__ == "__main__":
    asyncio.run(main())