"""
Fixed Persona Bot - No infinite loops!

This version prevents bots from responding to each other endlessly.
"""

import asyncio
import sys
import logging
from nio import AsyncClient, MatrixRoom, RoomMessageText, InviteEvent, JoinError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FixedPersonaBot:
    def __init__(self, persona_name: str):
        self.persona_name = persona_name
        self.homeserver = "http://localhost:8008"
        self.user_id = f"@{persona_name.lower()}:localhost"
        self.password = f"{persona_name.lower()}123"
        self.client = AsyncClient(self.homeserver, self.user_id)
        self.has_introduced = set()  # Track rooms where we've introduced
        
    async def start(self):
        """Start the persona bot"""
        try:
            # Login
            response = await self.client.login(self.password)
            if hasattr(response, 'access_token'):
                logger.info(f"✅ {self.persona_name} logged in successfully")
            else:
                logger.error(f"❌ {self.persona_name} login failed: {response}")
                return False
                
            # Set up event callbacks
            self.client.add_event_callback(self.message_callback, RoomMessageText)
            self.client.add_event_callback(self.invite_callback, InviteEvent)
            
            logger.info(f"🤖 {self.persona_name} is ready and listening...")
            
            # Start syncing
            await self.client.sync_forever(timeout=30000)
            
        except Exception as e:
            logger.error(f"❌ Error with {self.persona_name}: {e}")
        finally:
            await self.client.close()
    
    async def invite_callback(self, room: MatrixRoom, event: InviteEvent):
        """Auto-accept room invitations"""
        logger.info(f"📨 {self.persona_name} received invite to room")
        
        try:
            # Accept the invitation
            await self.client.join(room.room_id)
            logger.info(f"✅ {self.persona_name} joined room: {room.display_name or room.room_id}")
            
            # Send ONE introduction message
            await self.client.room_send(
                room_id=room.room_id,
                message_type="m.room.message",
                content={
                    "msgtype": "m.text",
                    "body": f"👋 Hello everyone! I'm {self.persona_name}. Nice to meet you all!"
                }
            )
            
            # Mark this room as introduced
            self.has_introduced.add(room.room_id)
            
        except JoinError as e:
            logger.error(f"❌ {self.persona_name} failed to join room: {e}")
        except Exception as e:
            logger.error(f"❌ Error handling invite: {e}")
    
    async def message_callback(self, room: MatrixRoom, event: RoomMessageText):
        """Handle incoming messages - FIXED to prevent loops"""
        if event.sender == self.user_id:
            return  # Don't respond to own messages
            
        # Log the message
        sender_name = event.sender.split(':')[0][1:]  # Extract username
        logger.info(f"💬 {room.display_name}: {sender_name}: {event.body}")
        
        # **CRITICAL FIX**: Don't respond to other bot messages
        if sender_name in ["alice", "bob", "charlie", "testbot"]:
            logger.info(f"🤐 {self.persona_name} ignoring bot message from {sender_name}")
            return
        
        # Only respond to human messages
        message = event.body.lower()
        response = None
        
        # Respond if directly mentioned by name
        if f"@{self.persona_name.lower()}" in message or f"{self.persona_name.lower()}" in message:
            response = f"Hi! You mentioned me. I'm {self.persona_name}. How can I help?"
        
        # Respond to questions about the persona (only if asked by humans)
        elif "who are you" in message and not any(bot in event.sender for bot in ["alice", "bob", "charlie"]):
            response = f"I'm {self.persona_name}, a persona from the MCP system!"
        
        # Send response if we have one
        if response:
            try:
                await self.client.room_send(
                    room_id=room.room_id,
                    message_type="m.room.message",
                    content={
                        "msgtype": "m.text",
                        "body": response  # No **Name**: prefix to avoid confusing formatting
                    }
                )
                logger.info(f"📤 {self.persona_name} responded to {sender_name}")
            except Exception as e:
                logger.error(f"❌ Failed to send message: {e}")

async def main():
    if len(sys.argv) != 2:
        print("Usage: python fixed_persona_bot.py <PersonaName>")
        print("Example: python fixed_persona_bot.py Alice")
        return
    
    persona_name = sys.argv[1].capitalize()
    
    if persona_name not in ["Alice", "Bob", "Charlie"]:
        print(f"❌ Unknown persona: {persona_name}")
        print("Available personas: Alice, Bob, Charlie")
        return
    
    print(f"🤖 Starting FIXED {persona_name} persona bot...")
    print("🛡️ This version prevents infinite loops!")
    print("Press Ctrl+C to stop")
    
    bot = FixedPersonaBot(persona_name)
    
    try:
        await bot.start()
    except KeyboardInterrupt:
        print(f"\n🛑 Stopping {persona_name} bot...")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())