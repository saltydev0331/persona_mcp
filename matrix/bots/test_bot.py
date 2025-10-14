"""
Test Matrix Bot for Persona MCP Integration

This is a simple test bot to verify our Matrix setup works before 
implementing full persona integration.
"""

import asyncio
import json
from nio import AsyncClient, MatrixRoom, RoomMessageText

class TestBot:
    def __init__(self, homeserver: str, user_id: str, password: str):
        self.homeserver = homeserver
        self.user_id = user_id
        self.password = password
        self.client = AsyncClient(homeserver, user_id)
        
    async def message_callback(self, room: MatrixRoom, event: RoomMessageText):
        """Handle incoming messages"""
        if event.sender == self.user_id:
            return  # Don't respond to our own messages
            
        print(f"Message in {room.display_name}: {event.sender}: {event.body}")
        
        # Simple test response
        if event.body.lower().startswith("hello"):
            await self.client.room_send(
                room_id=room.room_id,
                message_type="m.room.message",
                content={
                    "msgtype": "m.text",
                    "body": f"Hello back! I'm a test bot from persona-mcp."
                }
            )
    
    async def start(self):
        """Start the bot"""
        try:
            # Login
            response = await self.client.login(self.password)
            if hasattr(response, 'access_token'):
                print(f"Logged in as {self.user_id}")
            else:
                print(f"Login failed: {response}")
                return
                
            # Set up message callback
            self.client.add_event_callback(self.message_callback, RoomMessageText)
            
            # Start syncing
            print("Bot started. Listening for messages...")
            await self.client.sync_forever(timeout=30000)
            
        except Exception as e:
            print(f"Error: {e}")
        finally:
            await self.client.close()

async def main():
    # Configuration
    homeserver = "http://localhost:8008"
    
    # Using dedicated bot account (separate from your user account)
    user_id = "@testbot:localhost"
    password = "test123"
    
    print(f"Attempting to connect as {user_id}")
    print("Testing Matrix bot connection with dedicated bot credentials...")
    
    bot = TestBot(homeserver, user_id, password)
    await bot.start()

if __name__ == "__main__":
    asyncio.run(main())