"""
PersonaAPI Server - HTTP REST API for persona management.

Provides web-based interface for persona management, bot control,
and monitoring using shared core components.
"""

import asyncio
from typing import Dict, Any, Optional, List
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, status, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from ..logging import get_logger
from ..core import DatabaseManager, MemoryManager, ConfigManager
from .mcp_client import MCPClient
from .bot_manager import BotProcessManager


class PersonaAPIServer:
    """FastAPI server for persona management and monitoring"""

    def __init__(self, host: Optional[str] = None, port: Optional[int] = None):
        # Initialize shared core components
        self.core_config = ConfigManager()
        self.logger = get_logger(__name__)
        
        # Get PersonaAPI configuration
        api_config = self.core_config.get_personaapi_config()
        security_config = self.core_config.get_security_config()
        
        self.host = host or api_config["host"]
        self.port = port or api_config["port"]
        
        # Initialize shared core managers (for direct access when needed)
        self.db_manager = DatabaseManager()
        self.memory_manager = MemoryManager()
        
        # Initialize MCP client for operational parity
        self.mcp_client = MCPClient()
        
        # Initialize bot process manager
        self.bot_manager = BotProcessManager()
        
        # Create FastAPI application
        self.app = FastAPI(
            title=api_config["title"],
            description=api_config["description"],
            version=api_config["version"],
            docs_url=api_config["docs_url"],
            redoc_url=api_config["redoc_url"]
        )
        
        # Add CORS middleware
        if security_config["enable_cors"]:
            self.app.add_middleware(
                CORSMiddleware,
                allow_origins=security_config["cors_origins"],
                allow_methods=security_config["cors_methods"],
                allow_headers=security_config["cors_headers"],
                allow_credentials=True
            )
        
        # Setup routes
        self._setup_routes()

    async def initialize(self):
        """Initialize all components"""
        self.logger.info("Initializing PersonaAPI Server with shared core components...")
        
        # Initialize shared core components
        await self.db_manager.initialize()
        self.logger.info("Shared DatabaseManager initialized")
        
        await self.memory_manager.initialize()
        self.logger.info("Shared MemoryManager initialized")
        
        # Initialize MCP client
        await self.mcp_client.connect()
        self.logger.info("MCP client connected")
        
        # Initialize bot manager
        await self.bot_manager.initialize()
        self.logger.info("BotProcessManager initialized")
        
        self.logger.info("PersonaAPI Server initialization complete")

    async def shutdown(self):
        """Shutdown all components"""
        self.logger.info("Shutting down PersonaAPI Server...")
        
        # Shutdown in reverse order
        await self.bot_manager.shutdown()
        await self.mcp_client.disconnect()
        await self.memory_manager.close()
        await self.db_manager.close()
        
        self.logger.info("PersonaAPI Server shutdown complete")

    def _setup_routes(self):
        """Setup FastAPI routes"""

        # Health check
        @self.app.get("/", response_class=HTMLResponse)
        async def root():
            return """
            <html>
                <head><title>Persona MCP - PersonaAPI Server</title></head>
                <body>
                    <h1>Persona MCP - PersonaAPI Server</h1>
                    <p>HTTP REST API for persona management and monitoring</p>
                    <ul>
                        <li><a href="/docs">API Documentation</a></li>
                        <li><a href="/api/health">Health Check</a></li>
                        <li><a href="/api/personas">List Personas</a></li>
                    </ul>
                </body>
            </html>
            """

        @self.app.get("/api/health")
        async def health_check():
            """Health check endpoint"""
            try:
                # Check core components
                db_health = await self.db_manager.health_check()
                memory_health = await self.memory_manager.health_check()
                mcp_health = await self.mcp_client.health_check()
                
                overall_health = db_health["overall"] and memory_health["overall"] and mcp_health
                
                return {
                    "status": "healthy" if overall_health else "unhealthy",
                    "components": {
                        "database": db_health,
                        "memory": memory_health,
                        "mcp_connection": mcp_health
                    },
                    "timestamp": asyncio.get_event_loop().time()
                }
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Health check failed: {e}")

        # Persona management endpoints (using MCP for operational parity)
        @self.app.get("/api/personas")
        async def list_personas():
            """List all personas (via MCP)"""
            try:
                personas = await self.mcp_client.list_personas()
                return {"success": True, "personas": personas}
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to list personas: {e}")

        @self.app.get("/api/personas/{persona_id}")
        async def get_persona(persona_id: str):
            """Get persona by ID (via MCP)"""
            try:
                persona = await self.mcp_client.get_persona(persona_id)
                if not persona:
                    raise HTTPException(status_code=404, detail="Persona not found")
                return {"success": True, "persona": persona}
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to get persona: {e}")

        @self.app.post("/api/personas")
        async def create_persona(persona_data: Dict[str, Any]):
            """Create new persona (via MCP)"""
            try:
                result = await self.mcp_client.create_persona(persona_data)
                return {"success": True, "result": result}
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to create persona: {e}")

        @self.app.delete("/api/personas/{persona_id}")
        async def delete_persona(persona_id: str):
            """Delete persona (via MCP)"""
            try:
                result = await self.mcp_client.delete_persona(persona_id)
                return {"success": True, "result": result}
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to delete persona: {e}")

        # Memory management endpoints (using MCP for operational parity)
        @self.app.get("/api/memory/{persona_id}/search")
        async def search_memories(persona_id: str, query: str, n_results: int = 5, min_importance: float = 0.0):
            """Search persona memories (via MCP)"""
            try:
                memories = await self.mcp_client.search_memories(
                    persona_id=persona_id,
                    query=query,
                    n_results=n_results,
                    min_importance=min_importance
                )
                return {"success": True, "memories": memories}
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to search memories: {e}")

        @self.app.get("/api/memory/{persona_id}/stats")
        async def get_memory_stats(persona_id: str):
            """Get memory statistics (via MCP)"""
            try:
                stats = await self.mcp_client.get_memory_stats(persona_id)
                return {"success": True, "stats": stats}
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to get memory stats: {e}")

        @self.app.post("/api/memory/{persona_id}/prune")
        async def prune_memories(persona_id: str, max_memories: int = 1000):
            """Prune persona memories (via MCP)"""
            try:
                result = await self.mcp_client.prune_memories(persona_id, max_memories)
                return {"success": True, "result": result}
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to prune memories: {e}")

        # Bot management endpoints (using BotProcessManager)
        @self.app.post("/api/bots/{persona_id}/start")
        async def start_bot(persona_id: str):
            """Start Matrix bot for persona"""
            try:
                # Get persona details first
                persona = await self.mcp_client.get_persona(persona_id)
                if not persona:
                    raise HTTPException(status_code=404, detail="Persona not found")

                # Start bot process
                bot_process = await self.bot_manager.start_bot(
                    persona_id=persona_id,
                    persona_name=persona["name"]
                )
                
                return {
                    "success": True,
                    "message": f"Bot started for persona {persona['name']}",
                    "bot_info": {
                        "persona_id": persona_id,
                        "persona_name": persona["name"],
                        "pid": bot_process.process.pid,
                        "start_time": bot_process.start_time.isoformat(),
                        "log_file": str(bot_process.log_file)
                    }
                }
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e))
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to start bot: {e}")

        @self.app.post("/api/bots/{persona_id}/stop")
        async def stop_bot(persona_id: str):
            """Stop Matrix bot for persona"""
            try:
                success = await self.bot_manager.stop_bot(persona_id)
                if success:
                    return {"success": True, "message": "Bot stopped successfully"}
                else:
                    raise HTTPException(status_code=404, detail="Bot not found or not running")
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to stop bot: {e}")

        @self.app.post("/api/bots/{persona_id}/restart")
        async def restart_bot(persona_id: str):
            """Restart Matrix bot for persona"""
            try:
                success = await self.bot_manager.restart_bot(persona_id)
                if success:
                    return {"success": True, "message": "Bot restarted successfully"}
                else:
                    raise HTTPException(status_code=500, detail="Failed to restart bot")
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to restart bot: {e}")

        @self.app.get("/api/bots/status")
        async def get_bot_status():
            """Get status of all bots"""
            try:
                status = self.bot_manager.get_bot_status()
                return {"success": True, "bots": status}
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to get bot status: {e}")

        @self.app.get("/api/bots/{persona_id}/logs")
        async def get_bot_logs(persona_id: str, lines: int = 100):
            """Get recent bot logs"""
            try:
                logs = await self.bot_manager.get_bot_logs(persona_id, lines)
                return {"success": True, "logs": logs}
            except ValueError as e:
                raise HTTPException(status_code=404, detail=str(e))
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to get bot logs: {e}")

        # System information endpoints
        @self.app.get("/api/system/status")
        async def get_system_status():
            """Get comprehensive system status"""
            try:
                # Get stats from shared components
                db_stats = await self.db_manager.get_system_stats()
                memory_stats = await self.memory_manager.get_system_stats()
                
                # Get MCP system status
                mcp_status = await self.mcp_client.get_system_status()
                
                # Get bot status
                bot_status = self.bot_manager.get_bot_status()
                
                return {
                    "success": True,
                    "system": {
                        "database": db_stats,
                        "memory": memory_stats,
                        "mcp_server": mcp_status,
                        "bots": {
                            "count": len(bot_status),
                            "running": len([b for b in bot_status if b["status"] == "running"]),
                            "details": bot_status
                        }
                    }
                }
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to get system status: {e}")

    async def run(self):
        """Run the PersonaAPI server"""
        await self.initialize()
        
        try:
            config = uvicorn.Config(
                app=self.app,
                host=self.host,
                port=self.port,
                log_level="info",
                access_log=True
            )
            server = uvicorn.Server(config)
            
            self.logger.info(f"Starting PersonaAPI server on http://{self.host}:{self.port}")
            await server.serve()
            
        except Exception as e:
            self.logger.error(f"PersonaAPI server error: {e}")
            raise
        finally:
            await self.shutdown()


# Application lifecycle management
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle"""
    # This would be used if running via uvicorn directly
    yield


# For direct execution
if __name__ == "__main__":
    async def main():
        server = PersonaAPIServer()
        await server.run()
    
    asyncio.run(main())