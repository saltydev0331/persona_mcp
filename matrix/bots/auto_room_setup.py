"""
Auto Room Manager - Create rooms and auto-invite personas

This script creates a room and automatically invites personas who will
auto-accept the invitations.
"""

import asyncio
import logging
from nio import AsyncClient, MatrixRoom, InviteEvent, JoinError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AutoJoinBot:
    """A bot that automatically accepts invitations"""
    
    def __init__(self, homeserver: str, user_id: str, password: str, persona_name: str):
        self.homeserver = homeserver
        self.user_id = user_id
        self.password = password
        self.persona_name = persona_name
        self.client = AsyncClient(homeserver, user_id)
        
    async def start(self):
        """Start the bot and set up auto-join"""
        try:
            # Login
            response = await self.client.login(self.password)
            if hasattr(response, 'access_token'):
                logger.info(f"✅ {self.persona_name} logged in")
                
                # Set up invite callback
                self.client.add_event_callback(self.invite_callback, InviteEvent)
                return True
            else:
                logger.error(f"❌ {self.persona_name} login failed")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error starting {self.persona_name}: {e}")
            return False
    
    async def invite_callback(self, room: MatrixRoom, event: InviteEvent):
        """Auto-accept room invitations"""
        logger.info(f"📨 {self.persona_name} received invite to {room.room_id}")
        
        try:
            # Accept the invitation
            await self.client.join(room.room_id)
            logger.info(f"✅ {self.persona_name} joined room")
            
            # Send introduction message
            await self.client.room_send(
                room_id=room.room_id,
                message_type="m.room.message",
                content={
                    "msgtype": "m.text",
                    "body": f"👋 Hello everyone! I'm {self.persona_name}. Ready for our conversation!"
                }
            )
            
        except JoinError as e:
            logger.error(f"❌ {self.persona_name} failed to join: {e}")
    
    async def sync_once(self):
        """Sync once to process any pending invites"""
        try:
            await self.client.sync(timeout=5000)
        except Exception as e:
            logger.error(f"Sync error for {self.persona_name}: {e}")

class RoomManager:
    """Manages room creation and persona invitations"""
    
    def __init__(self, homeserver: str = "http://localhost:8008"):
        self.homeserver = homeserver
        self.creator_client = None
        
    async def setup_creator(self, user_id: str, password: str):
        """Set up the room creator client (your account)"""
        self.creator_client = AsyncClient(self.homeserver, user_id)
        
        response = await self.creator_client.login(password)
        if hasattr(response, 'access_token'):
            logger.info(f"✅ Room creator logged in: {user_id}")
            return True
        else:
            logger.error(f"❌ Creator login failed: {response}")
            return False
    
    async def create_simulation_room(self, room_name: str, room_topic: str = ""):
        """Create a new simulation room"""
        if not self.creator_client:
            logger.error("❌ Creator client not set up")
            return None
            
        try:
            response = await self.creator_client.room_create(
                visibility="private",
                name=room_name,
                topic=room_topic,
                initial_state=[{
                    "type": "m.room.history_visibility",
                    "content": {"history_visibility": "invited"}
                }]
            )
            
            if hasattr(response, 'room_id'):
                logger.info(f"🏠 Created room: {room_name} ({response.room_id})")
                return response.room_id
            else:
                logger.error(f"❌ Failed to create room: {response}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error creating room: {e}")
            return None
    
    async def invite_personas(self, room_id: str, persona_user_ids: list):
        """Invite all personas to the room"""
        if not self.creator_client:
            logger.error("❌ Creator client not set up")
            return
            
        for user_id in persona_user_ids:
            try:
                await self.creator_client.room_invite(room_id, user_id)
                logger.info(f"📤 Invited {user_id} to room")
                # Small delay between invites
                await asyncio.sleep(0.5)
            except Exception as e:
                logger.error(f"❌ Failed to invite {user_id}: {e}")

async def main():
    """Create a multi-persona room with auto-joining bots"""
    
    # Persona configurations
    personas = [
        {"name": "Alice", "user_id": "@alice:localhost", "password": "alice123"},
        {"name": "Bob", "user_id": "@bob:localhost", "password": "bob123"},
        {"name": "Charlie", "user_id": "@charlie:localhost", "password": "charlie123"}
    ]
    
    print("🤖 Setting up auto-join persona bots...")
    
    # Create and start persona bots
    bots = []
    for persona in personas:
        bot = AutoJoinBot(
            homeserver="http://localhost:8008",
            user_id=persona["user_id"],
            password=persona["password"],
            persona_name=persona["name"]
        )
        
        success = await bot.start()
        if success:
            bots.append(bot)
            print(f"✅ {persona['name']} bot ready")
        else:
            print(f"❌ Failed to start {persona['name']} bot")
    
    if not bots:
        print("❌ No bots started successfully")
        return
    
    print(f"\n🏠 Creating simulation room...")
    
    # Set up room manager
    room_manager = RoomManager()
    creator_success = await room_manager.setup_creator("@saltydev0331:localhost", "Fz1BF0m7#")
    
    if not creator_success:
        print("❌ Failed to set up room creator")
        return
    
    # Create room
    room_id = await room_manager.create_simulation_room(
        room_name="Multi-Persona Simulation",
        room_topic="Automated persona chatroom with Alice, Bob, and Charlie"
    )
    
    if not room_id:
        print("❌ Failed to create room")
        return
    
    print(f"✅ Room created: {room_id}")
    
    # Start sync loops for bots to receive invitations
    sync_tasks = []
    for bot in bots:
        sync_tasks.append(bot.client.sync_forever(timeout=30000))
    
    # Start syncing in background
    sync_task = asyncio.create_task(asyncio.gather(*sync_tasks, return_exceptions=True))
    
    # Wait a moment for sync to start
    await asyncio.sleep(1)
    
    # Invite all personas
    print("📤 Inviting personas to room...")
    persona_user_ids = [p["user_id"] for p in personas]
    await room_manager.invite_personas(room_id, persona_user_ids)
    
    # Wait for personas to join
    print("⏳ Waiting for personas to join...")
    await asyncio.sleep(3)
    
    # Sync once for each bot to process invitations
    for bot in bots:
        await bot.sync_once()
        await asyncio.sleep(1)
    
    print("✅ Setup complete!")
    print(f"🎭 Room ID: {room_id}")
    print("💬 Go to Element Web and join the 'Multi-Persona Simulation' room to start chatting!")
    print("\nPress Enter to stop bots...")
    
    try:
        input()  # Wait for user input
    except KeyboardInterrupt:
        pass
    
    print("🛑 Stopping bots...")
    sync_task.cancel()
    
    # Close all clients
    for bot in bots:
        try:
            await bot.client.close()
        except:
            pass
    
    try:
        await room_manager.creator_client.close()
    except:
        pass
    
    print("✅ All bots stopped")

if __name__ == "__main__":
    asyncio.run(main())