#!/usr/bin/env python3
"""
Persona Admin Bot for Matrix

This bot provides administrative functions for managing personas via Matrix widgets.
It can deploy widget forms and manage persona bots.
"""

import asyncio
import json
import logging
import time
from typing import Optional
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from nio import AsyncClient, MatrixRoom, RoomMessageText, InviteEvent
import websockets

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class PersonaAdminBot:
    """Admin bot for persona management via Matrix widgets"""
    
    def __init__(self):
        self.user_id = "@alice:localhost"  # Use Alice's credentials for now
        self.password = "alice_password" 
        self.homeserver = "http://localhost:8008"
        self.mcp_url = "ws://localhost:8000/mcp"
        
        # Matrix client
        self.matrix_client = AsyncClient(self.homeserver, self.user_id)
        
        # MCP connection
        self.mcp_websocket = None
        self.is_connected_to_mcp = False
        
        # Track when bot started (to ignore historical messages)
        self.start_time = time.time()
        
    async def start(self):
        """Start the admin bot"""
        try:
            print("🔧 Starting Persona Admin Bot...")
            print("🎛️ This bot manages personas via Matrix widgets!")
            print("🔗 Connecting to MCP server on localhost:8000")
            print("Press Ctrl+C to stop")
            
            logger.info("🚀 Starting Persona Admin Bot...")
            
            # Connect to MCP first
            await self.connect_to_mcp()
            
            # Connect to Matrix
            await self.connect_to_matrix()
            
            # Run the main loop
            await self.run_main_loop()
            
        except KeyboardInterrupt:
            logger.info("👋 Admin bot stopping...")
        except Exception as e:
            logger.error(f"❌ Admin bot error: {e}")
        finally:
            await self.cleanup()
    
    async def connect_to_mcp(self):
        """Connect to MCP server"""
        try:
            logger.info("🔌 Admin bot connecting to MCP server...")
            self.mcp_websocket = await websockets.connect(self.mcp_url)
            self.is_connected_to_mcp = True
            logger.info("✅ Admin bot connected to MCP server")
        except Exception as e:
            logger.error(f"❌ Admin bot MCP connection failed: {e}")
            raise
    
    async def connect_to_matrix(self):
        """Connect to Matrix server"""
        try:
            logger.info("🔐 Admin bot connecting to Matrix...")
            
            response = await self.matrix_client.login(self.password)
            if not hasattr(response, 'access_token'):
                raise Exception(f"Matrix login failed: {response}")
                
            logger.info("✅ Admin bot connected to Matrix")
            
            # Set up callbacks
            self.matrix_client.add_event_callback(self.message_callback, RoomMessageText)
            self.matrix_client.add_event_callback(self.invite_callback, InviteEvent)
            
            # Small delay to ensure we're synced, then reset start time
            await asyncio.sleep(2)
            self.start_time = time.time()
            logger.info("⏰ Admin bot ready for commands!")
            
        except Exception as e:
            logger.error(f"❌ Admin bot Matrix connection failed: {e}")
            raise
    
    async def run_main_loop(self):
        """Run the main bot loop with Matrix sync"""
        sync_task = asyncio.create_task(self.matrix_client.sync_forever(timeout=30000))
        await sync_task
    
    async def invite_callback(self, room: MatrixRoom, event: InviteEvent):
        """Handle room invitations"""
        logger.info("📨 Admin bot received invite to room")
        
        try:
            await self.matrix_client.join(room.room_id)
            logger.info(f"✅ Admin bot joined room: {room.display_name or room.room_id}")
            
            # Send welcome message with available commands
            welcome = """🔧 **Persona Admin Bot Ready!**

Available commands:
• `!widget` - Deploy persona creator widget
• `!list-personas` - List all available personas  
• `!help` - Show this help message

Use the widget to create new personas with a beautiful form interface!"""
            
            await self.matrix_client.room_send(
                room_id=room.room_id,
                message_type="m.room.message",
                content={"msgtype": "m.text", "body": welcome}
            )
            
        except Exception as e:
            logger.error(f"❌ Admin bot invite handling error: {e}")
    
    async def message_callback(self, room: MatrixRoom, event: RoomMessageText):
        """Handle admin commands"""
        if event.sender == self.user_id:
            return  # Don't respond to own messages
        
        # Only respond to messages sent AFTER the bot started
        message_time = event.server_timestamp / 1000
        if message_time < self.start_time:
            return  # Ignore historical messages
        
        sender_name = event.sender.split(':')[0][1:]
        message = event.body.strip()
        
        logger.info(f"💬 {room.display_name}: {sender_name}: {message}")
        
        # Handle admin commands
        if message.startswith("!"):
            await self.handle_admin_command(room, message, sender_name)
    
    async def handle_admin_command(self, room: MatrixRoom, command: str, sender: str):
        """Handle administrative commands"""
        try:
            if command == "!widget":
                await self.deploy_widget(room)
            
            elif command == "!list-personas":
                await self.list_personas(room)
            
            elif command == "!help":
                await self.show_help(room)
            
            else:
                await self.matrix_client.room_send(
                    room_id=room.room_id,
                    message_type="m.room.message",
                    content={"msgtype": "m.text", "body": f"❓ Unknown command: {command}. Use `!help` for available commands."}
                )
        
        except Exception as e:
            logger.error(f"❌ Error handling command {command}: {e}")
            await self.matrix_client.room_send(
                room_id=room.room_id,
                message_type="m.room.message",
                content={"msgtype": "m.text", "body": f"❌ Error executing command: {e}"}
            )
    
    async def deploy_widget(self, room: MatrixRoom):
        """Deploy the persona creator widget"""
        try:
            # Create Matrix widget state event
            widget_content = {
                "type": "m.custom",
                "url": "http://localhost:8000/widget/persona-creator",
                "name": "Persona Creator",
                "data": {
                    "title": "Create New Persona",
                    "widget_id": "persona-creator"
                }
            }
            
            # Send widget as a state event
            await self.matrix_client.room_put_state(
                room_id=room.room_id,
                event_type="im.vector.modular.widgets",
                content=widget_content,
                state_key="persona-creator"
            )
            
            # Also send a message about the widget
            widget_message = """🎛️ **Persona Creator Widget Deployed!**

A widget form has been added to this room. You can now:

1. **Use the widget above** to create personas with a visual form
2. **Or visit directly**: http://localhost:8000/widget/persona-creator

The widget allows you to:
• Set persona name and description
• Define personality traits with sliders  
• Choose speaking style
• Create background stories

Try it out! 🚀"""
            
            await self.matrix_client.room_send(
                room_id=room.room_id,
                message_type="m.room.message",
                content={"msgtype": "m.text", "body": widget_message}
            )
            
            logger.info("🎛️ Widget deployed successfully")
            
        except Exception as e:
            logger.error(f"❌ Widget deployment failed: {e}")
            await self.matrix_client.room_send(
                room_id=room.room_id,
                message_type="m.room.message",
                content={"msgtype": "m.text", "body": f"❌ Widget deployment failed: {e}"}
            )
    
    async def list_personas(self, room: MatrixRoom):
        """List all available personas"""
        try:
            if not self.is_connected_to_mcp:
                await self.matrix_client.room_send(
                    room_id=room.room_id,
                    message_type="m.room.message",
                    content={"msgtype": "m.text", "body": "❌ Not connected to MCP server"}
                )
                return
            
            # Get personas from MCP
            list_request = {
                "jsonrpc": "2.0",
                "id": f"list_{int(time.time())}",
                "method": "persona.list"
            }
            
            await self.mcp_websocket.send(json.dumps(list_request))
            response = await self.mcp_websocket.recv()
            result = json.loads(response)
            
            if "error" in result and result["error"] is not None:
                error_msg = result['error'].get('message', 'Unknown error') if isinstance(result['error'], dict) else result['error']
                await self.matrix_client.room_send(
                    room_id=room.room_id,
                    message_type="m.room.message",
                    content={"msgtype": "m.text", "body": f"❌ Error listing personas: {error_msg}"}
                )
                return
            
            personas = result.get("result", {}).get("personas", [])
            
            if not personas:
                message = "📋 **No Personas Found**\n\nUse `!widget` to create your first persona!"
            else:
                message = f"📋 **Available Personas ({len(personas)})**\n\n"
                for persona in personas:
                    name = persona.get('name', 'Unknown')
                    desc = persona.get('description', 'No description')
                    status = persona.get('status', 'unknown')
                    message += f"• **{name.title()}** ({status})\n  {desc}\n\n"
            
            await self.matrix_client.room_send(
                room_id=room.room_id,
                message_type="m.room.message",
                content={"msgtype": "m.text", "body": message}
            )
            
        except Exception as e:
            logger.error(f"❌ Error listing personas: {e}")
            await self.matrix_client.room_send(
                room_id=room.room_id,
                message_type="m.room.message",
                content={"msgtype": "m.text", "body": f"❌ Error listing personas: {e}"}
            )
    
    async def show_help(self, room: MatrixRoom):
        """Show help message"""
        help_message = """🔧 **Persona Admin Bot Help**

**Available Commands:**
• `!widget` - Deploy persona creator widget form
• `!list-personas` - List all available personas
• `!help` - Show this help message

**Widget Features:**
• Visual form for creating personas
• Personality trait sliders
• Speaking style selection
• Background story editor

**Quick Start:**
1. Type `!widget` to deploy the form
2. Use the widget to create personas
3. Deploy persona bots manually or via future API

For technical support, check the MCP server logs."""
        
        await self.matrix_client.room_send(
            room_id=room.room_id,
            message_type="m.room.message",
            content={"msgtype": "m.text", "body": help_message}
        )
    
    async def cleanup(self):
        """Clean up connections"""
        try:
            if self.mcp_websocket:
                await self.mcp_websocket.close()
                logger.info("🔌 Admin bot MCP connection closed")
        except:
            pass
        
        try:
            await self.matrix_client.close()
            logger.info("🔌 Admin bot Matrix connection closed")
        except:
            pass

async def main():
    """Main function"""
    if len(sys.argv) != 1:
        print("Usage: python persona_admin_bot.py")
        sys.exit(1)
    
    admin_bot = PersonaAdminBot()
    await admin_bot.start()

if __name__ == "__main__":
    asyncio.run(main())