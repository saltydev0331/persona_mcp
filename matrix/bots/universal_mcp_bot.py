"""
Universal MCP-Connected Persona Bot with Enhanced Logging

This bot can run any persona from the database with comprehensive logging and monitoring.
"""

import asyncio
import sys
import logging
import time
import json
import argparse
import traceback
from datetime import datetime
from typing import Optional, Dict, Any
import websockets
from nio import AsyncClient, MatrixRoom, RoomMessageText, InviteEvent, JoinError

class BotLogger:
    """Enhanced logging for bot monitoring"""
    
    def __init__(self, persona_name: str, log_file: str = None):
        self.persona_name = persona_name
        
        # Create logger
        self.logger = logging.getLogger(f"MCPBot-{persona_name}")
        self.logger.setLevel(logging.DEBUG)
        
        # Remove existing handlers
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)
        
        # Console handler with formatting
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_format = logging.Formatter(
            f'[{persona_name}] %(asctime)s - %(levelname)s - %(message)s',
            datefmt='%H:%M:%S'
        )
        console_handler.setFormatter(console_format)
        self.logger.addHandler(console_handler)
        
        # File handler if specified
        if log_file:
            try:
                file_handler = logging.FileHandler(log_file, mode='a')
                file_handler.setLevel(logging.DEBUG)
                file_format = logging.Formatter(
                    f'[{persona_name}] %(asctime)s - %(levelname)s - %(message)s - %(pathname)s:%(lineno)d',
                    datefmt='%Y-%m-%d %H:%M:%S'
                )
                file_handler.setFormatter(file_format)
                self.logger.addHandler(file_handler)
                self.logger.info(f"Logging to file: {log_file}")
            except Exception as e:
                self.logger.error(f"Failed to setup file logging: {e}")
    
    def info(self, msg): self.logger.info(msg)
    def debug(self, msg): self.logger.debug(msg)
    def warning(self, msg): self.logger.warning(msg)
    def error(self, msg): self.logger.error(msg)
    def critical(self, msg): self.logger.critical(msg)
    
    def log_exception(self, msg: str, exc: Exception):
        """Log exception with full traceback"""
        self.logger.error(f"{msg}: {exc}")
        self.logger.debug(f"Traceback:\n{traceback.format_exc()}")

class UniversalMCPBot:
    """Universal Matrix bot with full MCP backend integration"""
    
    def __init__(self, persona_id: str, persona_name: str, log_file: str = None):
        self.persona_id = persona_id
        self.persona_name = persona_name
        self.homeserver = "http://localhost:8008"
        self.user_id = f"@{persona_name.lower()}:localhost"
        self.password = f"{persona_name.lower()}123"
        
        # Enhanced logging
        self.logger = BotLogger(persona_name, log_file)
        
        self.matrix_client = AsyncClient(self.homeserver, self.user_id)
        
        # MCP WebSocket connection
        self.mcp_uri = "ws://localhost:8000/mcp"
        self.mcp_websocket = None
        self.mcp_session_id = None
        
        # State tracking
        self.has_introduced = set()
        self.start_time = time.time()
        self.is_connected_to_mcp = False
        self.last_heartbeat = time.time()
        
        # Health monitoring
        self.health_stats = {
            "messages_processed": 0,
            "mcp_requests": 0,
            "matrix_errors": 0,
            "mcp_errors": 0,
            "last_activity": datetime.now().isoformat()
        }
        
    async def start(self):
        """Start the universal MCP-connected persona bot"""
        try:
            self.logger.info(f"🚀 Starting Universal MCP Bot for {self.persona_name} (ID: {self.persona_id})")
            self.logger.info(f"📊 Process PID: {sys.argv[0]} - Args: {sys.argv}")
            
            # Step 1: Connect to MCP server
            await self.connect_to_mcp()
            
            # Step 2: Initialize persona in MCP
            await self.initialize_persona()
            
            # Step 3: Connect to Matrix
            await self.connect_to_matrix()
            
            # Step 4: Setup message handlers
            self.setup_matrix_handlers()
            
            # Step 5: Start main loop with health monitoring
            await self.run_with_monitoring()
            
        except Exception as e:
            self.logger.log_exception("Critical error in bot startup", e)
            raise
    
    async def connect_to_mcp(self):
        """Connect to MCP server with retry logic"""
        max_retries = 5
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                self.logger.info(f"🔗 Connecting to MCP server (attempt {attempt + 1}/{max_retries})")
                self.mcp_websocket = await websockets.connect(
                    self.mcp_uri,
                    ping_interval=20,
                    ping_timeout=10
                )
                self.is_connected_to_mcp = True
                self.logger.info("✅ Connected to MCP server")
                return
                
            except Exception as e:
                self.logger.warning(f"❌ MCP connection attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                else:
                    raise Exception(f"Failed to connect to MCP after {max_retries} attempts")
    
    async def initialize_persona(self):
        """Initialize persona in MCP system"""
        try:
            self.logger.info(f"🧠 Initializing persona {self.persona_name} in MCP")
            
            # Switch to our persona
            request = {
                "jsonrpc": "2.0",
                "method": "persona.switch",
                "params": {"persona_id": self.persona_id},
                "id": "init_persona"
            }
            
            await self.mcp_websocket.send(json.dumps(request))
            response = await self.mcp_websocket.recv()
            result = json.loads(response)
            
            if "error" in result:
                raise Exception(f"Failed to initialize persona: {result['error']}")
            
            self.logger.info(f"✅ Persona {self.persona_name} initialized successfully")
            self.health_stats["last_activity"] = datetime.now().isoformat()
            
        except Exception as e:
            self.logger.log_exception("Failed to initialize persona", e)
            raise
    
    async def connect_to_matrix(self):
        """Connect to Matrix homeserver"""
        try:
            self.logger.info(f"🔑 Logging into Matrix as {self.user_id}")
            
            login_response = await self.matrix_client.login(self.password)
            if hasattr(login_response, 'access_token'):
                self.logger.info("✅ Matrix login successful")
            else:
                raise Exception(f"Matrix login failed: {login_response}")
                
        except Exception as e:
            self.logger.log_exception("Matrix connection failed", e)
            raise
    
    def setup_matrix_handlers(self):
        """Setup Matrix event handlers"""
        self.logger.info("📝 Setting up Matrix event handlers")
        
        self.matrix_client.add_event_callback(self.on_message, RoomMessageText)
        self.matrix_client.add_event_callback(self.on_invite, InviteEvent)
    
    async def on_message(self, room: MatrixRoom, event: RoomMessageText):
        """Handle incoming Matrix messages with enhanced logging"""
        try:
            self.health_stats["messages_processed"] += 1
            self.health_stats["last_activity"] = datetime.now().isoformat()
            
            # Skip our own messages
            if event.sender == self.matrix_client.user_id:
                return
            
            self.logger.debug(f"📨 Message from {event.sender} in {room.name}: {event.body[:100]}...")
            
            # Process message through MCP
            response = await self.process_with_mcp(event.body, event.sender, room.room_id)
            
            if response:
                await self.matrix_client.room_send(
                    room_id=room.room_id,
                    message_type="m.room.message",
                    content={
                        "msgtype": "m.text",
                        "body": response
                    }
                )
                self.logger.info(f"✅ Sent response to {room.name}")
            else:
                self.logger.warning("❌ No response generated from MCP")
                
        except Exception as e:
            self.health_stats["matrix_errors"] += 1
            self.logger.log_exception("Error processing Matrix message", e)
    
    async def process_with_mcp(self, message: str, sender: str, room_id: str) -> Optional[str]:
        """Process message through MCP backend"""
        try:
            self.health_stats["mcp_requests"] += 1
            
            if not self.is_connected_to_mcp:
                self.logger.error("❌ Not connected to MCP")
                return "I'm having trouble connecting to my brain right now..."
            
            # Send message to MCP for processing
            request = {
                "jsonrpc": "2.0",
                "method": "conversation.send_message",
                "params": {
                    "content": message,
                    "sender": sender,
                    "room_id": room_id
                },
                "id": f"msg_{int(time.time())}"
            }
            
            self.logger.debug(f"🧠 Sending to MCP: {request['params']['content'][:50]}...")
            
            await self.mcp_websocket.send(json.dumps(request))
            response = await asyncio.wait_for(self.mcp_websocket.recv(), timeout=30)
            result = json.loads(response)
            
            if "error" in result:
                self.logger.error(f"❌ MCP error: {result['error']}")
                self.health_stats["mcp_errors"] += 1
                return "I encountered an error processing your message."
            
            response_text = result.get("result", {}).get("response", "")
            self.logger.debug(f"🧠 MCP response: {response_text[:50]}...")
            
            return response_text
            
        except asyncio.TimeoutError:
            self.logger.error("❌ MCP request timeout")
            self.health_stats["mcp_errors"] += 1
            return "I'm thinking a bit slowly right now..."
        except Exception as e:
            self.health_stats["mcp_errors"] += 1
            self.logger.log_exception("Error processing with MCP", e)
            return "I'm having trouble processing that right now."
    
    async def on_invite(self, room: MatrixRoom, event: InviteEvent):
        """Handle room invitations"""
        try:
            self.logger.info(f"📩 Invited to room {room.name} by {event.sender}")
            
            join_response = await self.matrix_client.join(room.room_id)
            if isinstance(join_response, JoinError):
                self.logger.error(f"❌ Failed to join room: {join_response}")
            else:
                self.logger.info(f"✅ Joined room {room.name}")
                
        except Exception as e:
            self.logger.log_exception("Error handling invite", e)
    
    async def health_check(self):
        """Periodic health check and stats logging"""
        while True:
            try:
                await asyncio.sleep(60)  # Check every minute
                
                current_time = time.time()
                uptime = current_time - self.start_time
                
                self.logger.info(f"📊 Health Check - Uptime: {uptime:.0f}s, "
                               f"Messages: {self.health_stats['messages_processed']}, "
                               f"MCP Requests: {self.health_stats['mcp_requests']}, "
                               f"Errors: Matrix={self.health_stats['matrix_errors']} MCP={self.health_stats['mcp_errors']}")
                
                # Test MCP connection
                if self.is_connected_to_mcp:
                    try:
                        # Send ping to MCP
                        await self.mcp_websocket.ping()
                        self.last_heartbeat = current_time
                    except Exception as e:
                        self.logger.warning(f"❌ MCP ping failed: {e}")
                        self.is_connected_to_mcp = False
                        # Attempt reconnect
                        await self.reconnect_mcp()
                        
            except Exception as e:
                self.logger.log_exception("Error in health check", e)
    
    async def reconnect_mcp(self):
        """Attempt to reconnect to MCP"""
        try:
            self.logger.info("🔄 Attempting MCP reconnection...")
            await self.connect_to_mcp()
            await self.initialize_persona()
        except Exception as e:
            self.logger.log_exception("MCP reconnection failed", e)
    
    async def run_with_monitoring(self):
        """Run bot with health monitoring"""
        self.logger.info("🚀 Bot fully initialized - starting main loop")
        
        # Start health monitoring
        health_task = asyncio.create_task(self.health_check())
        
        try:
            # Start Matrix sync
            await self.matrix_client.sync_forever(timeout=30000)
        finally:
            health_task.cancel()
            try:
                await health_task
            except asyncio.CancelledError:
                pass

async def main():
    parser = argparse.ArgumentParser(description='Universal MCP-Connected Persona Bot')
    parser.add_argument('--persona-id', required=True, help='Persona ID from database')
    parser.add_argument('--persona-name', required=True, help='Persona name')
    parser.add_argument('--log-file', help='Optional log file path')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    
    args = parser.parse_args()
    
    # Create log directory if using log file
    if args.log_file:
        import os
        os.makedirs(os.path.dirname(args.log_file), exist_ok=True)
    
    print(f"🤖 Starting Universal MCP Bot for {args.persona_name}")
    print(f"📝 Persona ID: {args.persona_id}")
    if args.log_file:
        print(f"📄 Logging to: {args.log_file}")
    print("Press Ctrl+C to stop")
    
    bot = UniversalMCPBot(
        persona_id=args.persona_id,
        persona_name=args.persona_name,
        log_file=args.log_file
    )
    
    try:
        await bot.start()
    except KeyboardInterrupt:
        print(f"\n🛑 Stopping {args.persona_name}...")
    except Exception as e:
        print(f"❌ Critical Error: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())