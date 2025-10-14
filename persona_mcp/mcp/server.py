"""
WebSocket server for MCP JSON-RPC 2.0 protocol
"""

import asyncio
from typing import Dict, Any, Optional
from aiohttp import web, WSMsgType
import aiohttp

from ..config import get_config
from ..logging import get_logger, set_correlation_id, clear_correlation_id
from .handlers import MCPHandlers
from .streaming_handlers import StreamingMCPHandlers
from .session import MCPSessionManager
from ..conversation import ConversationEngine
from ..persistence import SQLiteManager, VectorMemoryManager
from ..llm import LLMManager
from ..utils import fast_json as json  # Use optimized JSON


class MCPWebSocketServer:
    """WebSocket server implementing MCP JSON-RPC 2.0 protocol"""
    
    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        path: str = "/mcp"
    ):
        # Get configuration instance and logger
        self.config = get_config()
        self.logger = get_logger(__name__)
        
        self.host = host or self.config.server.host
        self.port = port or self.config.server.port
        self.path = path
        
        # Initialize components
        self.db_manager = SQLiteManager()
        self.memory_manager = VectorMemoryManager()
        self.llm_manager = LLMManager()
        
        # Initialize conversation engine
        self.conversation_engine = ConversationEngine(
            self.db_manager,
            self.memory_manager,
            self.llm_manager
        )
        
        # Initialize session manager for shared state
        self.session_manager = MCPSessionManager()
        
        # Initialize MCP handlers with session manager
        self.mcp_handlers = MCPHandlers(
            self.conversation_engine,
            self.db_manager,
            self.memory_manager,
            self.llm_manager,
            self.session_manager
        )
        
        # Initialize streaming handlers with shared session manager
        self.streaming_handlers = StreamingMCPHandlers(
            self.conversation_engine,
            self.db_manager,
            self.memory_manager,
            self.llm_manager,
            self.session_manager
        )        # Web application
        self.app = web.Application()
        self.app.router.add_get(self.path, self.websocket_handler)
        self.app.router.add_get("/", self.health_check)
        
        # Active connections
        self.connections: Dict[str, web.WebSocketResponse] = {}
        
        # Background tasks
        self.background_tasks = []
    
    async def initialize(self):
        """Initialize all components"""
        
        self.logger.info("Initializing Persona MCP Server...")
        
        # Initialize database
        await self.db_manager.initialize()
        self.logger.info("Database initialized")
        
        # Initialize LLM manager
        llm_available = await self.llm_manager.initialize()
        if llm_available:
            self.logger.info("LLM (Ollama) connection established")
        else:
            self.logger.warning("LLM (Ollama) not available - using fallback responses")
        
        # Create default personas if none exist
        await self._create_default_personas()
        
        # Start background tasks
        self._start_background_tasks()
        
        # Start session manager cleanup task
        await self.session_manager.start_cleanup_task()
        
        self.logger.info("Persona MCP Server initialization complete")
    
    async def _create_default_personas(self):
        """Create default Aria and Kira personas for testing"""
        
        personas = await self.db_manager.list_personas()
        if len(personas) >= 2:
            self.logger.info(f"Found {len(personas)} existing personas")
            return
        
        self.logger.info("Creating default personas...")
        
        # Create Aria - energetic bard
        from ..models import Persona, Priority
        
        aria = Persona(
            name="Aria",
            description="A vibrant elven bard with sparkling eyes and an infectious laugh. She loves stories, music, and meeting new people.",
            personality_traits={
                "extroverted": 90,
                "creative": 85,
                "empathetic": 80,
                "curious": 75,
                "optimistic": 85
            },
            topic_preferences={
                "music": 95,
                "stories": 90,
                "travel": 85,
                "gossip": 80,
                "magic": 70,
                "adventure": 85,
                "art": 80,
                "local_news": 75
            },
            charisma=18,
            intelligence=14,
            social_rank="performer"
        )
        
        aria.interaction_state.current_priority = Priority.SOCIAL
        aria.interaction_state.social_energy = 150  # High energy
        aria.interaction_state.available_time = 600  # Lots of time to chat
        
        # Create Kira - focused researcher  
        kira = Persona(
            name="Kira",
            description="A brilliant human scholar with keen analytical mind. She prefers deep conversations about knowledge and discovery.",
            personality_traits={
                "introverted": 70,
                "analytical": 95,
                "focused": 90,
                "methodical": 85,
                "reserved": 75
            },
            topic_preferences={
                "research": 95,
                "magic": 90,
                "history": 85,
                "philosophy": 80,
                "books": 85,
                "discovery": 90,
                "gossip": 20,
                "small_talk": 25
            },
            charisma=12,
            intelligence=18,
            social_rank="scholar"
        )
        
        kira.interaction_state.current_priority = Priority.ACADEMIC
        kira.interaction_state.social_energy = 80  # Moderate energy
        kira.interaction_state.available_time = 300  # Limited time
        
        # Save personas
        await self.db_manager.save_persona(aria)
        await self.db_manager.save_persona(kira)
        
        # Initialize their memory systems
        await self.memory_manager.initialize_persona_memory(aria.id)
        await self.memory_manager.initialize_persona_memory(kira.id)
        
        self.logger.info("Default personas created: Aria (bard) and Kira (scholar)")
    
    def _start_background_tasks(self):
        """Start background maintenance tasks"""
        
        # Social energy regeneration task
        energy_task = asyncio.create_task(self._energy_regeneration_loop())
        self.background_tasks.append(energy_task)
        
        self.logger.info("Background tasks started")
    
    async def _energy_regeneration_loop(self):
        """Background task to regenerate persona social energy"""
        
        while True:
            try:
                await self.conversation_engine.regenerate_social_energy()
                await asyncio.sleep(60)  # Run every minute
            except Exception as e:
                self.logger.error(f"Error in energy regeneration: {e}")
                await asyncio.sleep(60)
    
    async def health_check(self, request):
        """Simple health check endpoint"""
        return web.json_response({
            "status": "healthy",
            "server": "Persona MCP Server",
            "version": "0.1.0"
        })
    
    async def websocket_handler(self, request):
        """Handle WebSocket connections for MCP protocol"""
        
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        
        # Generate connection ID
        connection_id = f"conn_{len(self.connections)}"
        self.connections[connection_id] = ws
        
        # Set up session for this WebSocket connection
        self.mcp_handlers.set_websocket_id(connection_id)
        
        # Set correlation ID for this WebSocket connection
        set_correlation_id(connection_id)
        self.logger.info(f"New WebSocket connection established: {connection_id}")
        
        try:
            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    try:
                        # Refresh correlation ID for each message
                        set_correlation_id(connection_id)
                        
                        # Parse JSON-RPC request
                        request_data = json.loads(msg.data)
                        
                        # Add websocket_id to request params for streaming
                        if "params" not in request_data:
                            request_data["params"] = {}
                        request_data["params"]["websocket_id"] = connection_id
                        
                        # Create WebSocket sender function for streaming
                        async def websocket_sender(message: str):
                            await ws.send_str(message)
                        
                        # Check if it's a streaming request first
                        handled_as_stream = await self.streaming_handlers.handle_streaming_request(
                            request_data, websocket_sender
                        )
                        
                        # If not handled as stream, use regular handler
                        if not handled_as_stream:
                            response = await self.mcp_handlers.handle_request(request_data)
                            await ws.send_str(response.model_dump_json())
                        
                    except json.JSONDecodeError as e:
                        # Invalid JSON
                        error_response = {
                            "jsonrpc": "2.0",
                            "error": {
                                "code": -32700,
                                "message": "Parse error",
                                "data": str(e)
                            },
                            "id": None
                        }
                        await ws.send_str(json.dumps(error_response))
                        
                    except Exception as e:
                        self.logger.error(f"Error processing WebSocket message: {e}")
                        error_response = {
                            "jsonrpc": "2.0",
                            "error": {
                                "code": -32603,
                                "message": "Internal error",
                                "data": str(e)
                            },
                            "id": None
                        }
                        await ws.send_str(json.dumps(error_response))
                
                elif msg.type == WSMsgType.ERROR:
                    self.logger.error(f"WebSocket error: {ws.exception()}")
                    break
        
        except Exception as e:
            self.logger.error(f"WebSocket connection error: {e}")
        
        finally:
            # Clean up connection and session data
            if connection_id in self.connections:
                del self.connections[connection_id]
            
            # Clean up session state for this WebSocket
            self.session_manager.cleanup_websocket_connection(connection_id)
            
            set_correlation_id(connection_id)
            self.logger.info(f"WebSocket connection closed: {connection_id}")
            clear_correlation_id()
        
        return ws
    
    async def broadcast_message(self, message: Dict[str, Any]):
        """Broadcast a message to all connected clients"""
        
        if not self.connections:
            return
        
        message_str = json.dumps(message)
        
        # Send to all active connections
        for connection_id, ws in list(self.connections.items()):
            try:
                await ws.send_str(message_str)
            except Exception as e:
                self.logger.error(f"Error broadcasting to {connection_id}: {e}")
                # Remove dead connection
                if connection_id in self.connections:
                    del self.connections[connection_id]
    
    async def start_server(self):
        """Start the web server"""
        
        await self.initialize()
        
        runner = web.AppRunner(self.app)
        await runner.setup()
        
        site = web.TCPSite(runner, self.host, self.port)
        await site.start()
        
        self.logger.info(f"Persona MCP Server started on ws://{self.host}:{self.port}{self.path}")
        return runner
    
    async def stop_server(self):
        """Stop the server and clean up resources"""
        
        self.logger.info("Stopping Persona MCP Server...")
        
        # Cancel background tasks
        for task in self.background_tasks:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        
        # Stop session manager cleanup task
        await self.session_manager.stop_cleanup_task()
        
        # Close LLM manager
        await self.llm_manager.close()
        
        # Close memory manager
        await self.memory_manager.close()
        
        self.logger.info("Persona MCP Server stopped")


async def create_server(
    host: str = "localhost",
    port: int = 8000,
    path: str = "/mcp"
) -> MCPWebSocketServer:
    """Factory function to create MCP server"""
    
    server = MCPWebSocketServer(host, port, path)
    return server
