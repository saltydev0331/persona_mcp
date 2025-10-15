"""
MCP Client for PersonaAPI server communication.

This client allows the PersonaAPI server to communicate with the MCP server
via WebSocket to maintain operational parity.
"""

import asyncio
import json
import websockets
import uuid
from typing import Dict, Any, Optional, List
from contextlib import asynccontextmanager

from ..logging import get_logger
from ..core import ConfigManager


class MCPClient:
    """WebSocket client for communicating with MCP server from PersonaAPI"""

    def __init__(self, mcp_uri: Optional[str] = None):
        self.config = ConfigManager()
        
        # Get MCP configuration
        mcp_config = self.config.get_mcp_config()
        self.mcp_uri = mcp_uri or f"ws://{mcp_config['host']}:{mcp_config['port']}{mcp_config['path']}"
        
        self.websocket = None
        self.logger = get_logger(__name__)
        self.request_id = 0
        self.pending_requests = {}

    async def connect(self):
        """Connect to MCP server"""
        try:
            self.websocket = await websockets.connect(self.mcp_uri)
            self.logger.info(f"Connected to MCP server at {self.mcp_uri}")
            
            # Start response handler
            asyncio.create_task(self._handle_responses())
            
        except Exception as e:
            self.logger.error(f"Failed to connect to MCP server: {e}")
            raise

    async def disconnect(self):
        """Disconnect from MCP server"""
        if self.websocket:
            await self.websocket.close()
            self.websocket = None
            self.logger.info("Disconnected from MCP server")

    async def _handle_responses(self):
        """Handle incoming WebSocket responses"""
        try:
            async for message in self.websocket:
                if not message:
                    continue
                    
                try:
                    response = json.loads(message)
                except json.JSONDecodeError as e:
                    self.logger.error(f"Failed to parse JSON response: {message[:100]}... Error: {e}")
                    continue
                    
                if not response:
                    self.logger.warning(f"Empty response received: {message}")
                    continue
                    
                request_id = response.get("id")
                
                if request_id in self.pending_requests:
                    future = self.pending_requests.pop(request_id)
                    if "error" in response and response["error"]:
                        error_info = response["error"]
                        if isinstance(error_info, dict) and "message" in error_info:
                            future.set_exception(Exception(error_info["message"]))
                        else:
                            future.set_exception(Exception(f"MCP error: {error_info}"))
                    else:
                        future.set_result(response.get("result"))
                        
        except websockets.exceptions.ConnectionClosed:
            self.logger.info("MCP WebSocket connection closed")
        except Exception as e:
            self.logger.error(f"Error handling MCP responses: {e}")
            import traceback
            self.logger.error(f"Full traceback: {traceback.format_exc()}")

    async def call(self, method: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """Make MCP JSON-RPC call"""
        if not self.websocket:
            await self.connect()

        self.request_id += 1
        request_id = str(self.request_id)
        
        request = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {},
            "id": request_id
        }

        # Create future for response
        future = asyncio.Future()
        self.pending_requests[request_id] = future

        try:
            await self.websocket.send(json.dumps(request))
            result = await asyncio.wait_for(future, timeout=30.0)
            return result
            
        except asyncio.TimeoutError:
            self.pending_requests.pop(request_id, None)
            raise Exception(f"MCP call timeout: {method}")
        except Exception as e:
            self.pending_requests.pop(request_id, None)
            raise Exception(f"MCP call failed: {e}")

    @asynccontextmanager
    async def connection(self):
        """Context manager for automatic connection management"""
        await self.connect()
        try:
            yield self
        finally:
            await self.disconnect()

    # Persona operations
    async def list_personas(self) -> List[Dict[str, Any]]:
        """Get all personas via MCP"""
        result = await self.call("persona.list")
        return result.get("personas", [])

    async def get_persona(self, persona_id: str) -> Optional[Dict[str, Any]]:
        """Get persona by ID via MCP"""
        try:
            result = await self.call("persona.get", {"persona_id": persona_id})
            return result.get("persona")
        except Exception:
            return None

    async def create_persona(self, persona_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create persona via MCP"""
        return await self.call("persona.create", persona_data)

    async def delete_persona(self, persona_id: str) -> Dict[str, Any]:
        """Delete persona via MCP"""
        return await self.call("persona.delete", {"persona_id": persona_id})

    async def switch_persona(self, persona_id: str) -> Dict[str, Any]:
        """Switch active persona via MCP"""
        return await self.call("persona.switch", {"persona_id": persona_id})

    # Memory operations
    async def search_memories(self, persona_id: str, query: str, 
                            n_results: int = 5, min_importance: float = 0.0) -> List[Dict[str, Any]]:
        """Search memories via MCP"""
        result = await self.call("memory.search", {
            "persona_id": persona_id,
            "query": query,
            "n_results": n_results,
            "min_importance": min_importance
        })
        return result.get("memories", [])

    async def get_memory_stats(self, persona_id: str) -> Dict[str, Any]:
        """Get memory statistics via MCP"""
        return await self.call("memory.stats", {"persona_id": persona_id})

    async def prune_memories(self, persona_id: str, max_memories: int = 1000) -> Dict[str, Any]:
        """Prune memories via MCP"""
        return await self.call("memory.prune", {
            "persona_id": persona_id,
            "max_memories": max_memories
        })

    # Relationship operations
    async def get_relationships(self, persona_id: str) -> List[Dict[str, Any]]:
        """Get relationships via MCP"""
        result = await self.call("relationship.list", {"persona_id": persona_id})
        return result.get("relationships", [])

    async def get_relationship_stats(self) -> Dict[str, Any]:
        """Get relationship statistics via MCP"""
        return await self.call("relationship.stats")

    # System operations
    async def get_system_status(self) -> Dict[str, Any]:
        """Get system status via MCP"""
        return await self.call("system.status")

    async def send_message(self, content: str, sender: str = "user", 
                          room_id: Optional[str] = None, 
                          context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Send message to active persona via MCP"""
        params = {
            "content": content,
            "sender": sender
        }
        if room_id:
            params["room_id"] = room_id
        if context:
            params["context"] = context
            
        return await self.call("conversation.send_message", params)

    # Health check
    async def health_check(self) -> bool:
        """Check if MCP server is healthy"""
        try:
            await self.call("system.status")
            return True
        except Exception as e:
            self.logger.error(f"MCP health check failed: {e}")
            return False