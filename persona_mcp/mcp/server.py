"""
WebSocket server for MCP JSON-RPC 2.0 protocol
"""

import asyncio
import subprocess
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

# Import shared core components
from ..core import DatabaseManager, MemoryManager, ConfigManager


class MCPWebSocketServer:
    """WebSocket server implementing MCP JSON-RPC 2.0 protocol"""
    
    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        path: str = "/mcp"
    ):
        # Initialize shared core components
        self.core_config = ConfigManager()
        self.logger = get_logger(__name__)
        
        # Get MCP-specific configuration
        mcp_config = self.core_config.get_mcp_config()
        self.host = host or mcp_config["host"]
        self.port = port or mcp_config["port"]
        self.path = path
        
        # Initialize shared core managers
        self.db_manager = DatabaseManager()
        self.memory_manager = MemoryManager()
        self.llm_manager = LLMManager()
        
        # Initialize conversation engine with shared components
        self.conversation_engine = ConversationEngine(
            self.db_manager.sqlite,  # Use underlying SQLite manager for compatibility
            self.db_manager.vector,  # Use underlying vector manager for compatibility
            self.llm_manager
        )
        
        # Initialize session manager for shared state
        self.session_manager = MCPSessionManager()
        
        # Initialize MCP handlers with shared core components
        self.mcp_handlers = MCPHandlers(
            self.conversation_engine,
            self.db_manager,  # Pass shared DatabaseManager
            self.memory_manager,  # Pass shared MemoryManager
            self.llm_manager,
            self.session_manager
        )
        
        # Initialize streaming handlers with shared core components
        self.streaming_handlers = StreamingMCPHandlers(
            self.conversation_engine,
            self.db_manager,  # Pass shared DatabaseManager
            self.memory_manager,  # Pass shared MemoryManager
            self.llm_manager,
            self.session_manager
        )        # Web application
        self.app = web.Application()
        self.app.router.add_get(self.path, self.websocket_handler)
        self.app.router.add_get("/", self.health_check)
        
        # Universal Widget Routes
        self.app.router.add_get("/widget/persona-creator", self.persona_creator_widget)
        self.app.router.add_get("/widget/admin-dashboard", self.admin_dashboard_widget)
        
        # API Routes
        self.app.router.add_post("/api/create-persona", self.api_create_persona)
        self.app.router.add_post("/api/deploy-bot", self.api_deploy_bot)
        self.app.router.add_get("/api/personas", self.api_list_personas)
        self.app.router.add_delete("/api/personas/{persona_id}", self.api_delete_persona)
        self.app.router.add_post("/api/bot/start/{persona_id}", self.api_start_bot)
        self.app.router.add_post("/api/bot/stop/{persona_id}", self.api_stop_bot)
        self.app.router.add_get("/api/bot/status", self.api_bot_status)
        self.app.router.add_get("/api/bot/logs/{persona_id}", self.api_get_bot_logs)
        
        # Active connections
        self.connections: Dict[str, web.WebSocketResponse] = {}
        
        # Bot process management
        self.running_bots: Dict[str, Dict[str, Any]] = {}  # persona_id -> {process, start_time, status}
        
        # Background tasks
        self.background_tasks = []
    
    async def initialize(self):
        """Initialize all components using shared core"""
        
        self.logger.info("Initializing Persona MCP Server with shared core components...")
        
        # Initialize shared core components
        await self.db_manager.initialize()
        self.logger.info("Shared DatabaseManager initialized")
        
        await self.memory_manager.initialize()
        self.logger.info("Shared MemoryManager initialized")
        
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
        
        self.logger.info("Persona MCP Server initialization complete with shared core")
    
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

    async def persona_creator_widget(self, request):
        """Serve the Matrix widget form for persona creation"""
        html_content = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Persona Creator</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 20px;
            background: #f5f5f5;
            min-height: 100vh;
        }
        .container {
            max-width: 600px;
            margin: 0 auto;
            background: white;
            border-radius: 8px;
            padding: 24px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        .header {
            text-align: center;
            margin-bottom: 24px;
        }
        .header h1 {
            color: #333;
            margin: 0 0 8px 0;
            font-size: 24px;
        }
        .header p {
            color: #666;
            margin: 0;
        }
        .form-group {
            margin-bottom: 20px;
        }
        label {
            display: block;
            margin-bottom: 6px;
            font-weight: 500;
            color: #333;
        }
        input, textarea, select {
            width: 100%;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 14px;
            box-sizing: border-box;
        }
        textarea {
            height: 80px;
            resize: vertical;
        }
        .personality-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 15px;
        }
        .trait-input {
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .trait-input label {
            margin: 0;
            min-width: 100px;
            font-size: 13px;
        }
        .trait-input input[type="range"] {
            flex: 1;
        }
        .trait-value {
            min-width: 40px;
            font-weight: bold;
            color: #0066cc;
        }
        .button-group {
            display: flex;
            gap: 12px;
            margin-top: 24px;
        }
        button {
            flex: 1;
            padding: 12px 20px;
            border: none;
            border-radius: 4px;
            font-size: 14px;
            font-weight: 500;
            cursor: pointer;
            transition: background-color 0.2s;
        }
        .btn-primary {
            background: #0066cc;
            color: white;
        }
        .btn-primary:hover {
            background: #0052a3;
        }
        .btn-secondary {
            background: #e9ecef;
            color: #495057;
        }
        .btn-secondary:hover {
            background: #dee2e6;
        }
        .status {
            margin-top: 16px;
            padding: 12px;
            border-radius: 4px;
            text-align: center;
            font-weight: 500;
        }
        .status.success {
            background: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }
        .status.error {
            background: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }
        .hidden {
            display: none;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🤖 Create New Persona</h1>
            <p>Design an AI persona for your Matrix chatroom</p>
        </div>
        
        <form id="personaForm">
            <div class="form-group">
                <label for="name">Persona Name *</label>
                <input type="text" id="name" name="name" required placeholder="e.g., Alice, Bob, Charlie">
            </div>
            
            <div class="form-group">
                <label for="description">Description</label>
                <textarea id="description" name="description" placeholder="Brief description of this persona's role or purpose..."></textarea>
            </div>
            
            <div class="form-group">
                <label for="background">Background Story</label>
                <textarea id="background" name="background" placeholder="Tell us about this persona's history, interests, and experiences..."></textarea>
            </div>
            
            <div class="form-group">
                <label for="speaking_style">Speaking Style</label>
                <select id="speaking_style" name="speaking_style">
                    <option value="casual and warm">Casual & Warm</option>
                    <option value="professional and helpful">Professional & Helpful</option>
                    <option value="playful and energetic">Playful & Energetic</option>
                    <option value="thoughtful and wise">Thoughtful & Wise</option>
                    <option value="direct and honest">Direct & Honest</option>
                    <option value="creative and artistic">Creative & Artistic</option>
                </select>
            </div>
            
            <div class="form-group">
                <label>Personality Traits</label>
                <div class="personality-grid">
                    <div class="trait-input">
                        <label>Friendliness</label>
                        <input type="range" id="friendliness" min="1" max="10" value="7" oninput="updateTraitValue('friendliness')">
                        <span class="trait-value" id="friendliness-value">7</span>
                    </div>
                    <div class="trait-input">
                        <label>Curiosity</label>
                        <input type="range" id="curiosity" min="1" max="10" value="6" oninput="updateTraitValue('curiosity')">
                        <span class="trait-value" id="curiosity-value">6</span>
                    </div>
                    <div class="trait-input">
                        <label>Helpfulness</label>
                        <input type="range" id="helpfulness" min="1" max="10" value="8" oninput="updateTraitValue('helpfulness')">
                        <span class="trait-value" id="helpfulness-value">8</span>
                    </div>
                    <div class="trait-input">
                        <label>Humor</label>
                        <input type="range" id="humor" min="1" max="10" value="5" oninput="updateTraitValue('humor')">
                        <span class="trait-value" id="humor-value">5</span>
                    </div>
                </div>
            </div>
            
            <div class="button-group">
                <button type="button" class="btn-secondary" onclick="resetForm()">Reset</button>
                <button type="submit" class="btn-primary">Create Persona</button>
            </div>
        </form>
        
        <div id="status" class="status hidden"></div>
    </div>

    <script>
        function updateTraitValue(traitName) {
            const slider = document.getElementById(traitName);
            const valueSpan = document.getElementById(traitName + '-value');
            valueSpan.textContent = slider.value;
        }
        
        function resetForm() {
            document.getElementById('personaForm').reset();
            // Reset trait values
            ['friendliness', 'curiosity', 'helpfulness', 'humor'].forEach(trait => {
                updateTraitValue(trait);
            });
            hideStatus();
        }
        
        function showStatus(message, isError = false) {
            const status = document.getElementById('status');
            status.textContent = message;
            status.className = 'status ' + (isError ? 'error' : 'success');
            status.classList.remove('hidden');
        }
        
        function hideStatus() {
            document.getElementById('status').classList.add('hidden');
        }
        
        document.getElementById('personaForm').addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const formData = new FormData(e.target);
            const personaData = {
                name: formData.get('name'),
                description: formData.get('description'),
                background: formData.get('background'),
                speaking_style: formData.get('speaking_style'),
                personality_traits: {
                    friendliness: parseInt(document.getElementById('friendliness').value),
                    curiosity: parseInt(document.getElementById('curiosity').value),
                    helpfulness: parseInt(document.getElementById('helpfulness').value),
                    humor: parseInt(document.getElementById('humor').value)
                }
            };
            
            try {
                showStatus('Creating persona...', false);
                
                const response = await fetch('/api/create-persona', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(personaData)
                });
                
                const result = await response.json();
                
                if (response.ok) {
                    showStatus(`✅ Persona "${personaData.name}" created successfully! ID: ${result.persona_id}`, false);
                    setTimeout(resetForm, 3000);
                } else {
                    showStatus(`❌ Error: ${result.error || 'Failed to create persona'}`, true);
                }
            } catch (error) {
                showStatus(`❌ Network error: ${error.message}`, true);
            }
        });
    </script>
</body>
</html>
        """
        return web.Response(text=html_content, content_type='text/html')

    async def api_create_persona(self, request):
        """API endpoint to create a new persona"""
        try:
            data = await request.json()
            
            # Validate required fields
            if not data.get('name'):
                return web.json_response(
                    {"error": "Name is required"}, 
                    status=400
                )
            
            # Create persona using MCP handlers
            create_params = {
                "name": data['name'].lower(),
                "full_name": data['name'],
                "background": data.get('background', f"I am {data['name']}, an AI persona."),
                "personality_traits": data.get('personality_traits', {
                    "friendliness": 7,
                    "curiosity": 6,
                    "helpfulness": 8,
                    "humor": 5
                }),
                "speaking_style": data.get('speaking_style', "casual and warm"),
                "interests": ["conversation", "learning", "helping others"]
            }
            
            if data.get('description'):
                create_params["description"] = data['description']
            
            # Use the MCP handlers to create persona
            result = await self.mcp_handlers.handle_persona_create(create_params)
            
            return web.json_response({
                "success": True,
                "persona_id": result["id"],
                "name": result["name"],
                "message": f"Persona {data['name']} created successfully!"
            })
            
        except Exception as e:
            self.logger.error(f"Error creating persona via API: {e}")
            return web.json_response(
                {"error": str(e)}, 
                status=500
            )

    async def api_deploy_bot(self, request):
        """API endpoint to deploy a persona bot to Matrix"""
        try:
            data = await request.json()
            persona_id = data.get('persona_id')
            
            if not persona_id:
                return web.json_response(
                    {"error": "persona_id is required"}, 
                    status=400
                )
            
            # TODO: Implement bot deployment logic
            # This would start a new Matrix bot process for the persona
            
            return web.json_response({
                "success": True,
                "message": f"Bot deployment for persona {persona_id} initiated"
            })
            
        except Exception as e:
            self.logger.error(f"Error deploying bot via API: {e}")
            return web.json_response(
                {"error": str(e)}, 
                status=500
            )

    async def api_list_personas(self, request):
        """API endpoint to list all personas"""
        try:
            # Use MCP handlers to list personas
            result = await self.mcp_handlers.handle_persona_list({})
            
            return web.json_response({
                "success": True,
                "personas": result["personas"]
            })
            
        except Exception as e:
            self.logger.error(f"Error listing personas via API: {e}")
            return web.json_response(
                {"error": str(e)}, 
                status=500
            )

    async def api_delete_persona(self, request):
        """API endpoint to delete a persona"""
        try:
            persona_id = request.match_info['persona_id']
            
            # Use MCP handlers to delete persona
            result = await self.mcp_handlers.handle_persona_delete({
                "persona_id": persona_id
            })
            
            return web.json_response({
                "success": True,
                "message": result["message"]
            })
            
        except Exception as e:
            self.logger.error(f"Error deleting persona via API: {e}")
            return web.json_response(
                {"error": str(e)}, 
                status=500
            )

    async def api_start_bot(self, request):
        """API endpoint to start a bot for a persona"""
        try:
            persona_id = request.match_info['persona_id']
            
            # Check if bot is already running
            if persona_id in self.running_bots:
                return web.json_response({
                    "success": False,
                    "error": "Bot is already running for this persona"
                })
            
            # Load persona to get details
            persona = await self.db_manager.load_persona(persona_id)
            if not persona:
                return web.json_response({
                    "error": "Persona not found"
                }, status=404)
            
            # Start the bot process with enhanced logging
            import subprocess
            import sys
            from datetime import datetime
            import os
            
            # Create logs directory
            log_dir = "d:/git/persona-mcp/logs/bots"
            os.makedirs(log_dir, exist_ok=True)
            
            log_file = f"{log_dir}/{persona.name.lower()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
            bot_script = "d:/git/persona-mcp/matrix/bots/universal_mcp_bot.py"
            
            # Start the universal bot with proper arguments
            process = subprocess.Popen([
                sys.executable, bot_script,
                "--persona-id", persona_id,
                "--persona-name", persona.name,
                "--log-file", log_file
            ], 
            stdout=subprocess.PIPE, 
            stderr=subprocess.STDOUT,  # Redirect stderr to stdout
            universal_newlines=True,
            bufsize=1)  # Line buffered
            
            # Track the running bot
            self.running_bots[persona_id] = {
                "process": process,
                "start_time": datetime.now(),
                "status": "running",
                "persona_name": persona.name,
                "log_file": log_file,
                "pid": process.pid
            }
            
            self.logger.info(f"Started bot for persona {persona.name} (ID: {persona_id}) - PID: {process.pid}")
            self.logger.info(f"Bot logs: {log_file}")
            
            return web.json_response({
                "success": True,
                "message": f"Bot started for {persona.name}",
                "pid": process.pid,
                "log_file": log_file
            })
            
        except Exception as e:
            self.logger.error(f"Error starting bot: {e}")
            return web.json_response(
                {"error": str(e)}, 
                status=500
            )

    async def api_stop_bot(self, request):
        """API endpoint to stop a bot for a persona"""
        try:
            persona_id = request.match_info['persona_id']
            
            # Check if bot is running
            if persona_id not in self.running_bots:
                return web.json_response({
                    "success": False,
                    "error": "No bot running for this persona"
                })
            
            bot_info = self.running_bots[persona_id]
            process = bot_info["process"]
            
            # Terminate the process
            process.terminate()
            
            # Wait for it to finish (with timeout)
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                # Force kill if it doesn't terminate gracefully
                process.kill()
                process.wait()
            
            # Remove from running bots
            persona_name = bot_info["persona_name"]
            del self.running_bots[persona_id]
            
            self.logger.info(f"Stopped bot for persona {persona_name} (ID: {persona_id})")
            
            return web.json_response({
                "success": True,
                "message": f"Bot stopped for {persona_name}"
            })
            
        except Exception as e:
            self.logger.error(f"Error stopping bot: {e}")
            return web.json_response(
                {"error": str(e)}, 
                status=500
            )

    async def api_bot_status(self, request):
        """API endpoint to get status of all bots"""
        try:
            status_list = []
            
            # Get all personas
            personas_result = await self.mcp_handlers.handle_persona_list({})
            all_personas = personas_result["personas"]
            
            for persona in all_personas:
                persona_id = persona["id"]
                bot_status = {
                    "persona_id": persona_id,
                    "persona_name": persona["name"],
                    "bot_running": False,
                    "start_time": None,
                    "pid": None,
                    "log_file": None,
                    "has_logs": False
                }
                
                if persona_id in self.running_bots:
                    bot_info = self.running_bots[persona_id]
                    process = bot_info["process"]
                    
                    # Check if process is still alive
                    if process.poll() is None:  # Still running
                        bot_status.update({
                            "bot_running": True,
                            "start_time": bot_info["start_time"].isoformat(),
                            "pid": process.pid,
                            "log_file": bot_info.get("log_file"),
                            "has_logs": bool(bot_info.get("log_file"))
                        })
                    else:
                        # Process died, but keep log file info
                        bot_status.update({
                            "log_file": bot_info.get("log_file"),
                            "has_logs": bool(bot_info.get("log_file"))
                        })
                        # Remove from tracking but keep log reference
                        del self.running_bots[persona_id]
                
                status_list.append(bot_status)
            
            return web.json_response({
                "success": True,
                "bots": status_list
            })
            
        except Exception as e:
            self.logger.error(f"Error getting bot status: {e}")
            return web.json_response(
                {"error": str(e)}, 
                status=500
            )

    async def api_get_bot_logs(self, request):
        """API endpoint to get bot logs for a persona"""
        try:
            persona_id = request.match_info['persona_id']
            lines = int(request.query.get('lines', 100))  # Default to last 100 lines
            
            # Check if bot has/had logs
            log_file = None
            if persona_id in self.running_bots:
                log_file = self.running_bots[persona_id].get("log_file")
            
            if not log_file:
                return web.json_response({
                    "success": False,
                    "error": "No log file found for this persona"
                })
            
            # Read log file
            import os
            if not os.path.exists(log_file):
                return web.json_response({
                    "success": False,
                    "error": "Log file does not exist"
                })
            
            try:
                # Read last N lines efficiently
                with open(log_file, 'r', encoding='utf-8') as f:
                    file_lines = f.readlines()
                    
                # Get last N lines
                log_lines = file_lines[-lines:] if len(file_lines) > lines else file_lines
                
                return web.json_response({
                    "success": True,
                    "log_file": log_file,
                    "total_lines": len(file_lines),
                    "returned_lines": len(log_lines),
                    "logs": [line.rstrip() for line in log_lines]
                })
                
            except Exception as e:
                return web.json_response({
                    "success": False,
                    "error": f"Error reading log file: {str(e)}"
                })
            
        except Exception as e:
            self.logger.error(f"Error getting bot logs: {e}")
            return web.json_response(
                {"error": str(e)}, 
                status=500
            )

    async def admin_dashboard_widget(self, request):
        """Serve the admin dashboard widget"""
        
        html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Persona Admin Dashboard</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            overflow: hidden;
        }
        .header {
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }
        .header h1 {
            font-size: 28px;
            margin-bottom: 8px;
        }
        .header p {
            opacity: 0.9;
            font-size: 16px;
        }
        .content {
            padding: 30px;
        }
        .refresh-btn {
            background: #28a745;
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 6px;
            font-size: 14px;
            font-weight: 500;
            cursor: pointer;
            margin-bottom: 20px;
            transition: background-color 0.2s;
        }
        .refresh-btn:hover {
            background: #218838;
        }
        .personas-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(400px, 1fr));
            gap: 20px;
        }
        .persona-card {
            border: 1px solid #e9ecef;
            border-radius: 8px;
            padding: 20px;
            background: #f8f9fa;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        .persona-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        }
        .persona-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 12px;
        }
        .persona-name {
            font-size: 18px;
            font-weight: 600;
            color: #495057;
        }
        .bot-status {
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 500;
            text-transform: uppercase;
        }
        .status-running {
            background: #d4edda;
            color: #155724;
        }
        .status-stopped {
            background: #f8d7da;
            color: #721c24;
        }
        .persona-description {
            color: #6c757d;
            margin-bottom: 16px;
            line-height: 1.4;
        }
        .persona-id {
            font-family: monospace;
            font-size: 11px;
            color: #999;
            margin-bottom: 16px;
        }
        .bot-controls {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 8px;
            margin-bottom: 12px;
        }
        .btn {
            padding: 8px 16px;
            border: none;
            border-radius: 4px;
            font-size: 12px;
            font-weight: 500;
            cursor: pointer;
            transition: background-color 0.2s;
            flex: 1;
        }
        .btn-start {
            background: #28a745;
            color: white;
        }
        .btn-start:hover {
            background: #218838;
        }
        .btn-start:disabled {
            background: #6c757d;
            cursor: not-allowed;
        }
        .btn-stop {
            background: #dc3545;
            color: white;
        }
        .btn-stop:hover {
            background: #c82333;
        }
        .btn-stop:disabled {
            background: #6c757d;
            cursor: not-allowed;
        }
        .btn-delete {
            background: #ffc107;
            color: #212529;
        }
        .btn-delete:hover {
            background: #e0a800;
        }
        .btn-logs {
            background: #17a2b8;
            color: white;
        }
        .btn-logs:hover {
            background: #138496;
        }
        .btn-logs:disabled {
            background: #6c757d;
            cursor: not-allowed;
        }
        .bot-info {
            font-size: 11px;
            color: #6c757d;
            background: white;
            padding: 8px;
            border-radius: 4px;
            margin-top: 8px;
        }
        .loading {
            text-align: center;
            padding: 40px;
            color: #6c757d;
        }
        .error {
            background: #f8d7da;
            color: #721c24;
            padding: 12px;
            border-radius: 4px;
            margin-bottom: 20px;
        }
        .success {
            background: #d4edda;
            color: #155724;
            padding: 12px;
            border-radius: 4px;
            margin-bottom: 20px;
        }
        .modal {
            display: none;
            position: fixed;
            z-index: 1000;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0,0,0,0.5);
        }
        .modal-content {
            background-color: white;
            margin: 5% auto;
            padding: 20px;
            border-radius: 8px;
            width: 90%;
            max-width: 1000px;
            max-height: 80vh;
            overflow-y: auto;
        }
        .modal-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 1px solid #e9ecef;
        }
        .modal-header h2 {
            color: #495057;
            margin: 0;
        }
        .close {
            font-size: 28px;
            font-weight: bold;
            cursor: pointer;
            color: #aaa;
        }
        .close:hover {
            color: #000;
        }
        .log-container {
            background: #f8f9fa;
            border: 1px solid #e9ecef;
            border-radius: 4px;
            padding: 15px;
            font-family: 'Courier New', monospace;
            font-size: 12px;
            line-height: 1.4;
            height: 400px;
            overflow-y: auto;
            white-space: pre-wrap;
        }
        .log-controls {
            margin-bottom: 15px;
            display: flex;
            gap: 10px;
            align-items: center;
        }
        .log-controls input {
            padding: 5px 10px;
            border: 1px solid #ced4da;
            border-radius: 4px;
            width: 100px;
        }
        .log-controls button {
            padding: 5px 15px;
            background: #007bff;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
        }
        .log-controls button:hover {
            background: #0056b3;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🤖 Persona Admin Dashboard</h1>
            <p>Manage your AI personas and their Matrix bots</p>
        </div>
        
        <div class="content">
            <button class="refresh-btn" onclick="loadDashboard()">🔄 Refresh Status</button>
            
            <div id="messages"></div>
            <div id="personas-container">
                <div class="loading">Loading personas...</div>
            </div>
        </div>
    </div>

    <!-- Logs Modal -->
    <div id="logsModal" class="modal">
        <div class="modal-content">
            <div class="modal-header">
                <h2 id="modalTitle">Bot Logs</h2>
                <span class="close" onclick="closeLogsModal()">&times;</span>
            </div>
            <div class="log-controls">
                <label>Lines: <input type="number" id="logLines" value="100" min="10" max="1000"></label>
                <button onclick="refreshLogs()">Refresh</button>
                <button onclick="downloadLogs()">Download Full Log</button>
            </div>
            <div id="logContainer" class="log-container">
                <div class="loading">Loading logs...</div>
            </div>
        </div>
    </div>

    <script>
        let personas = [];
        let botStatus = [];

        async function loadDashboard() {
            try {
                showMessage('Loading data...', 'info');
                
                // Load personas and bot status in parallel
                const [personasResponse, statusResponse] = await Promise.all([
                    fetch('/api/personas'),
                    fetch('/api/bot/status')
                ]);
                
                const personasData = await personasResponse.json();
                const statusData = await statusResponse.json();
                
                if (personasData.success && statusData.success) {
                    personas = personasData.personas;
                    botStatus = statusData.bots;
                    renderDashboard();
                    clearMessages();
                } else {
                    showMessage('Error loading data', 'error');
                }
            } catch (error) {
                showMessage('Error: ' + error.message, 'error');
            }
        }

        function renderDashboard() {
            const container = document.getElementById('personas-container');
            
            if (personas.length === 0) {
                container.innerHTML = '<div class="loading">No personas found</div>';
                return;
            }
            
            const grid = document.createElement('div');
            grid.className = 'personas-grid';
            
            personas.forEach(persona => {
                const botInfo = botStatus.find(b => b.persona_id === persona.id) || {};
                const isRunning = botInfo.bot_running || false;
                
                const card = document.createElement('div');
                card.className = 'persona-card';
                card.innerHTML = `
                    <div class="persona-header">
                        <div class="persona-name">${escapeHtml(persona.name)}</div>
                        <div class="bot-status ${isRunning ? 'status-running' : 'status-stopped'}">
                            ${isRunning ? 'Running' : 'Stopped'}
                        </div>
                    </div>
                    
                    <div class="persona-description">
                        ${escapeHtml(persona.description || 'No description')}
                    </div>
                    
                    <div class="persona-id">ID: ${persona.id}</div>
                    
                    <div class="bot-controls">
                        <button class="btn btn-start" ${isRunning ? 'disabled' : ''} 
                                onclick="startBot('${persona.id}', '${escapeHtml(persona.name)}')">
                            Start Bot
                        </button>
                        <button class="btn btn-stop" ${!isRunning ? 'disabled' : ''} 
                                onclick="stopBot('${persona.id}', '${escapeHtml(persona.name)}')">
                            Stop Bot
                        </button>
                        <button class="btn btn-logs" ${!botInfo.has_logs ? 'disabled' : ''} 
                                onclick="viewLogs('${persona.id}', '${escapeHtml(persona.name)}')">
                            View Logs
                        </button>
                        <button class="btn btn-delete" 
                                onclick="deletePersona('${persona.id}', '${escapeHtml(persona.name)}')">
                            Delete
                        </button>
                    </div>
                    
                    ${isRunning ? `
                        <div class="bot-info">
                            <div>PID: ${botInfo.pid}</div>
                            <div>Started: ${new Date(botInfo.start_time).toLocaleString()}</div>
                        </div>
                    ` : ''}
                `;
                
                grid.appendChild(card);
            });
            
            container.innerHTML = '';
            container.appendChild(grid);
        }

        async function startBot(personaId, personaName) {
            try {
                showMessage(`Starting bot for ${personaName}...`, 'info');
                
                const response = await fetch(`/api/bot/start/${personaId}`, {
                    method: 'POST'
                });
                
                const data = await response.json();
                
                if (data.success) {
                    showMessage(data.message, 'success');
                    setTimeout(loadDashboard, 1000); // Refresh after 1 second
                } else {
                    showMessage('Error: ' + data.error, 'error');
                }
            } catch (error) {
                showMessage('Error: ' + error.message, 'error');
            }
        }

        async function stopBot(personaId, personaName) {
            try {
                showMessage(`Stopping bot for ${personaName}...`, 'info');
                
                const response = await fetch(`/api/bot/stop/${personaId}`, {
                    method: 'POST'
                });
                
                const data = await response.json();
                
                if (data.success) {
                    showMessage(data.message, 'success');
                    setTimeout(loadDashboard, 1000); // Refresh after 1 second
                } else {
                    showMessage('Error: ' + data.error, 'error');
                }
            } catch (error) {
                showMessage('Error: ' + error.message, 'error');
            }
        }

        async function deletePersona(personaId, personaName) {
            if (!confirm(`Are you sure you want to delete ${personaName}? This action cannot be undone.`)) {
                return;
            }
            
            try {
                showMessage(`Deleting ${personaName}...`, 'info');
                
                const response = await fetch(`/api/personas/${personaId}`, {
                    method: 'DELETE'
                });
                
                const data = await response.json();
                
                if (data.success) {
                    showMessage(data.message, 'success');
                    setTimeout(loadDashboard, 1000); // Refresh after 1 second
                } else {
                    showMessage('Error: ' + data.error, 'error');
                }
            } catch (error) {
                showMessage('Error: ' + error.message, 'error');
            }
        }

        let currentPersonaId = null;
        let currentPersonaName = null;

        async function viewLogs(personaId, personaName) {
            currentPersonaId = personaId;
            currentPersonaName = personaName;
            
            document.getElementById('modalTitle').textContent = `Bot Logs - ${personaName}`;
            document.getElementById('logsModal').style.display = 'block';
            
            await refreshLogs();
        }

        async function refreshLogs() {
            if (!currentPersonaId) return;
            
            try {
                const lines = document.getElementById('logLines').value || 100;
                const response = await fetch(`/api/bot/logs/${currentPersonaId}?lines=${lines}`);
                const data = await response.json();
                
                const logContainer = document.getElementById('logContainer');
                
                if (data.success) {
                    if (data.logs && data.logs.length > 0) {
                        logContainer.innerHTML = data.logs.join('\\n');
                        // Scroll to bottom
                        logContainer.scrollTop = logContainer.scrollHeight;
                    } else {
                        logContainer.innerHTML = 'No logs available';
                    }
                } else {
                    logContainer.innerHTML = `Error: ${data.error}`;
                }
            } catch (error) {
                document.getElementById('logContainer').innerHTML = `Error loading logs: ${error.message}`;
            }
        }

        function closeLogsModal() {
            document.getElementById('logsModal').style.display = 'none';
            currentPersonaId = null;
            currentPersonaName = null;
        }

        async function downloadLogs() {
            if (!currentPersonaId) return;
            
            try {
                const response = await fetch(`/api/bot/logs/${currentPersonaId}?lines=10000`);
                const data = await response.json();
                
                if (data.success && data.logs) {
                    const blob = new Blob([data.logs.join('\\n')], { type: 'text/plain' });
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = `${currentPersonaName.toLowerCase()}_bot_logs.txt`;
                    document.body.appendChild(a);
                    a.click();
                    document.body.removeChild(a);
                    window.URL.revokeObjectURL(url);
                } else {
                    showMessage('Error downloading logs: ' + (data.error || 'Unknown error'), 'error');
                }
            } catch (error) {
                showMessage('Error downloading logs: ' + error.message, 'error');
            }
        }

        // Close modal when clicking outside
        window.onclick = function(event) {
            const modal = document.getElementById('logsModal');
            if (event.target === modal) {
                closeLogsModal();
            }
        }

        function showMessage(message, type) {
            const messagesDiv = document.getElementById('messages');
            messagesDiv.innerHTML = `<div class="${type}">${escapeHtml(message)}</div>`;
        }

        function clearMessages() {
            document.getElementById('messages').innerHTML = '';
        }

        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }

        // Auto-refresh every 30 seconds
        setInterval(loadDashboard, 30000);

        // Load dashboard on page load
        loadDashboard();
    </script>
</body>
</html>
        """
        
        return web.Response(text=html_content, content_type='text/html')
    
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


async def main():
    """Main entry point when running as a module"""
    import logging
    import signal
    import sys
    
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    # Create and start server
    server = await create_server()
    runner = None
    
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, shutting down...")
        if runner:
            asyncio.create_task(runner.cleanup())
        sys.exit(0)
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Start the server
        runner = await server.start_server()
        
        logger.info("=" * 50)
        logger.info(f"[READY] Persona MCP Server is running!")
        logger.info(f"[WEBSOCKET] WebSocket: ws://localhost:8000/mcp")
        logger.info("=" * 50)
        logger.info("Press Ctrl+C to stop the server")
        
        # Keep server running
        while True:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error(f"Server error: {e}")
        return 1
    finally:
        if runner:
            await runner.cleanup()
        await server.stop_server()
    
    return 0


if __name__ == "__main__":
    import asyncio
    exit_code = asyncio.run(main())
    exit(exit_code)
