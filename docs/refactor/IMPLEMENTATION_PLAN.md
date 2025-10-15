# Persona-MCP Implementation Plan

## Current State Analysis

### What We Have ✅

- **MCP Server** with persona intelligence (port 8000)
- **Matrix Bot Integration** with universal_mcp_bot.py
- **Basic Web Widgets** embedded in MCP server
- **Persona CRUD Operations** via MCP protocol
- **Memory and Relationship Systems** working

### What Needs Refactoring ⚠️

- **Mixed Responsibilities** - MCP server has HTTP endpoints for PersonaAPI
- **Tight Coupling** - Web interface embedded in intelligence server
- **Limited Scalability** - Everything in one service

## Refactoring Plan

The refactoring follows the **"Clean Separation with Parity"** principle:

- **Clean Separation**: MCP server handles pure intelligence, PersonaAPI server handles management
- **Maintained Parity**: Both services support equivalent core operations through shared libraries
- **Shared Foundation**: Common data access, models, and business logic ensure consistency

### Phase 1: Service Separation with Shared Foundation (Weeks 1-2)

#### Clean Separation with Parity Implementation

Following the "Clean Separation with Parity" principle established in our architecture vision:

1. **Shared Core Foundation**: Create `persona_mcp/core/` containing all shared models, database operations, and business logic
2. **Service Specialization**: Each service specializes in its interface while using identical core implementations
3. **Operational Equivalence**: Both services provide the same capabilities through their respective interfaces (WebSocket vs HTTP)
4. **Deployment Flexibility**: Services can run together or separately with identical functionality

This approach ensures clean separation while maintaining complete operational parity between services.

#### Step 1.1: Create Shared Core and PersonaAPI Server Structure

```
persona_mcp/
├── core/                      # NEW: Shared foundation
│   ├── __init__.py
│   ├── models.py             # Shared Persona, Memory, Relationship models
│   ├── database.py           # Common database operations
│   ├── memory.py             # Shared memory management
│   └── config.py             # Unified configuration
├── mcp/
│   └── server.py             # Pure MCP WebSocket server (uses core/)
├── dashboard/
│   ├── __init__.py
│   ├── server.py             # New dashboard web server (uses core/)
│   ├── mcp_client.py         # MCP client for dashboard
│   ├── bot_manager.py        # Bot process management
│   └── templates/
│       ├── dashboard.html    # Admin dashboard
│       └── widgets/
│           └── persona_creator.html
└── api/
    ├── __init__.py
    ├── personas.py           # Persona management endpoints
    ├── bots.py               # Bot control endpoints
    └── system.py             # System monitoring endpoints
```

```
persona_mcp/
├── mcp/
│   └── server.py              # Pure MCP WebSocket server
├── dashboard/
│   ├── __init__.py
│   ├── server.py              # New dashboard web server
│   ├── mcp_client.py          # MCP client for dashboard
│   ├── bot_manager.py         # Bot process management
│   └── templates/
│       ├── dashboard.html     # Admin dashboard
│       └── widgets/
│           └── persona_creator.html
└── api/
    ├── __init__.py
    ├── personas.py            # Persona management endpoints
    ├── bots.py                # Bot control endpoints
    └── system.py              # System monitoring endpoints
```

#### Step 1.2: Implement Shared Core Components

Create foundational components that both services will use:

**persona_mcp/core/models.py**

```python
# Shared data models used by both MCP and PersonaAPI services
class Persona(BaseModel):
    # Unified persona model with complete functionality

class Memory(BaseModel):
    # Shared memory model

class Relationship(BaseModel):
    # Shared relationship model
```

**persona_mcp/core/database.py**

```python
# Unified database operations
class DatabaseManager:
    def __init__(self, db_path: str):
        # Shared database connection and operations

    async def create_persona(self, persona_data: dict) -> Persona:
        # Same implementation used by both services

    async def get_personas(self) -> List[Persona]:
        # Identical functionality for both interfaces
```

**persona_mcp/core/memory.py**

```python
# Shared memory management
class MemoryManager:
    # Identical memory operations for both services
```

#### Step 1.3: Create MCP Client Library

```python
# persona_mcp/dashboard/mcp_client.py
class MCPClient:
    """Client for communicating with MCP server from dashboard"""

    def __init__(self, mcp_uri: str = "ws://localhost:8000/mcp"):
        self.mcp_uri = mcp_uri
        self.websocket = None

    async def connect(self):
        """Connect to MCP server"""
        self.websocket = await websockets.connect(self.mcp_uri)

    async def call(self, method: str, params: dict = None) -> dict:
        """Make MCP JSON-RPC call"""
        request = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {},
            "id": str(uuid.uuid4())
        }

        await self.websocket.send(json.dumps(request))
        response = await self.websocket.recv()
        return json.loads(response)

    async def list_personas(self) -> List[dict]:
        """Get all personas via MCP"""
        result = await self.call("persona.list")
        return result["result"]["personas"]

    async def delete_persona(self, persona_id: str) -> dict:
        """Delete persona via MCP"""
        return await self.call("persona.delete", {"persona_id": persona_id})
```

#### Step 1.4: Refactor MCP Server to Use Shared Core

```python
# persona_mcp/mcp/server.py - Updated to use shared components
from ..core.database import DatabaseManager
from ..core.models import Persona, Memory, Relationship
from ..core.memory import MemoryManager

class MCPServer:
    def __init__(self):
        # Use shared core components
        self.db = DatabaseManager("data/personas.db")
        self.memory = MemoryManager()

    async def handle_create_persona(self, params: dict) -> dict:
        # Use shared database operations
        persona = await self.db.create_persona(params)
        return {"success": True, "persona": persona.dict()}
```

#### Step 1.5: Implement PersonaAPI Server Using Shared Core

```python
# persona_mcp/dashboard/server.py
from fastapi import FastAPI
from ..core.database import DatabaseManager
from ..core.models import Persona
from ..core.memory import MemoryManager

app = FastAPI()

# Use same shared components as MCP server
db = DatabaseManager("data/personas.db")
memory = MemoryManager()

@app.get("/api/personas")
async def get_personas():
    # Identical implementation to MCP server
    personas = await db.get_personas()
    return [p.dict() for p in personas]

@app.post("/api/personas")
async def create_persona(persona_data: dict):
    # Same business logic as MCP server
    persona = await db.create_persona(persona_data)
    return {"success": True, "persona": persona.dict()}
```

#### Step 1.6: Create Bot Process Manager

```python
# persona_mcp/dashboard/bot_manager.py
class BotProcessManager:
    """Manages Matrix bot processes independently of MCP"""

    def __init__(self):
        self.running_bots: Dict[str, BotProcess] = {}
        self.log_directory = Path("logs/bots")
        self.log_directory.mkdir(parents=True, exist_ok=True)

    async def start_bot(self, persona_id: str, persona_name: str) -> BotProcess:
        """Start a Matrix bot for a persona"""
        if persona_id in self.running_bots:
            raise ValueError("Bot already running for this persona")

        # Create log file
        log_file = self.log_directory / f"{persona_name.lower()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

        # Start bot process
        process = subprocess.Popen([
            sys.executable, "matrix/bots/universal_mcp_bot.py",
            "--persona-id", persona_id,
            "--persona-name", persona_name,
            "--log-file", str(log_file)
        ], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

        bot_process = BotProcess(
            persona_id=persona_id,
            persona_name=persona_name,
            process=process,
            log_file=log_file,
            start_time=datetime.now()
        )

        self.running_bots[persona_id] = bot_process
        return bot_process

    async def stop_bot(self, persona_id: str) -> bool:
        """Stop a Matrix bot"""
        if persona_id not in self.running_bots:
            return False

        bot_process = self.running_bots[persona_id]
        bot_process.process.terminate()

        try:
            bot_process.process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            bot_process.process.kill()

        del self.running_bots[persona_id]
        return True

    def get_bot_status(self) -> List[dict]:
        """Get status of all bots"""
        status_list = []
        for persona_id, bot_process in self.running_bots.items():
            status_list.append({
                "persona_id": persona_id,
                "persona_name": bot_process.persona_name,
                "running": bot_process.process.poll() is None,
                "pid": bot_process.process.pid,
                "start_time": bot_process.start_time.isoformat(),
                "log_file": str(bot_process.log_file)
            })
        return status_list
```

#### Step 1.4: Create Dashboard Web Server

```python
# persona_mcp/dashboard/server.py
from fastapi import FastAPI, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from .mcp_client import MCPClient
from .bot_manager import BotProcessManager

class DashboardServer:
    """Web dashboard for persona management"""

    def __init__(self, port: int = 8080):
        self.app = FastAPI(title="Persona Dashboard")
        self.port = port
        self.mcp_client = MCPClient()
        self.bot_manager = BotProcessManager()
        self.templates = Jinja2Templates(directory="dashboard/templates")

        self.setup_routes()

    def setup_routes(self):
        """Setup FastAPI routes"""

        # Dashboard UI
        @self.app.get("/")
        async def dashboard():
            return self.templates.TemplateResponse("dashboard.html")

        @self.app.get("/widgets/persona-creator")
        async def persona_creator_widget():
            return self.templates.TemplateResponse("widgets/persona_creator.html")

        # Persona API
        @self.app.get("/api/personas")
        async def list_personas():
            personas = await self.mcp_client.list_personas()
            return {"success": True, "personas": personas}

        @self.app.delete("/api/personas/{persona_id}")
        async def delete_persona(persona_id: str):
            result = await self.mcp_client.delete_persona(persona_id)
            return {"success": True, "message": result["result"]["message"]}

        # Bot Management API
        @self.app.post("/api/bots/{persona_id}/start")
        async def start_bot(persona_id: str):
            # Get persona details from MCP
            personas = await self.mcp_client.list_personas()
            persona = next((p for p in personas if p["id"] == persona_id), None)

            if not persona:
                raise HTTPException(404, "Persona not found")

            bot_process = await self.bot_manager.start_bot(persona_id, persona["name"])
            return {
                "success": True,
                "message": f"Bot started for {persona['name']}",
                "pid": bot_process.process.pid
            }

        @self.app.post("/api/bots/{persona_id}/stop")
        async def stop_bot(persona_id: str):
            success = await self.bot_manager.stop_bot(persona_id)
            if not success:
                raise HTTPException(404, "Bot not found or not running")
            return {"success": True, "message": "Bot stopped"}

        @self.app.get("/api/bots/status")
        async def bot_status():
            status = self.bot_manager.get_bot_status()
            return {"success": True, "bots": status}
```

### Phase 2: Clean Up MCP Server (Priority: HIGH)

#### Step 2.1: Remove HTTP Routes from MCP Server

```python
# Remove these from persona_mcp/mcp/server.py:
- self.app.router.add_get("/widget/persona-creator", ...)
- self.app.router.add_get("/widget/admin-dashboard", ...)
- self.app.router.add_post("/api/create-persona", ...)
- self.app.router.add_delete("/api/personas/{persona_id}", ...)
- All HTTP/REST endpoints
```

#### Step 2.2: Pure MCP Server

```python
# persona_mcp/mcp/server.py (cleaned up)
class MCPWebSocketServer:
    """Pure MCP WebSocket server for persona intelligence"""

    def __init__(self, host: str = "localhost", port: int = 8000, path: str = "/mcp"):
        self.host = host
        self.port = port
        self.path = path

        # Only WebSocket application
        self.app = web.Application()
        self.app.router.add_get(self.path, self.websocket_handler)
        self.app.router.add_get("/", self.health_check)  # Simple health check only

        # Remove bot management from MCP server
        # self.running_bots = {}  # DELETE THIS

    # Keep only MCP protocol handlers
    # Remove all HTTP API methods
```

### Phase 3: Update Deployment (Priority: MEDIUM)

#### Step 3.1: Development Scripts

```bash
# scripts/dev-start.sh
#!/bin/bash
echo "Starting Persona-MCP Development Environment"

# Start MCP server in background
echo "Starting MCP Intelligence Server..."
python -m persona_mcp.mcp.server &
MCP_PID=$!

# Wait for MCP to be ready
sleep 2

# Start PersonaAPI server
echo "Starting PersonaAPI Server..."
python -m persona_mcp.dashboard.server &
DASHBOARD_PID=$!

echo "Services started:"
echo "  MCP Server: http://localhost:8000/mcp (PID: $MCP_PID)"
echo "  Dashboard:  http://localhost:8080 (PID: $DASHBOARD_PID)"
echo ""
echo "Press Ctrl+C to stop all services"

# Wait for interrupt
trap "kill $MCP_PID $DASHBOARD_PID; exit" INT
wait
```

#### Step 3.2: Docker Compose

```yaml
# docker-compose.yml
version: "3.8"

services:
  mcp-server:
    build:
      context: .
      target: mcp-server
    ports:
      - "8000:8000"
    environment:
      - LOG_LEVEL=INFO
    volumes:
      - ./data:/app/data
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/"]
      interval: 30s
      timeout: 10s
      retries: 3

  dashboard:
    build:
      context: .
      target: dashboard
    ports:
      - "8080:8080"
    depends_on:
      - mcp-server
    environment:
      - MCP_SERVER_URI=ws://mcp-server:8000/mcp
    volumes:
      - ./logs:/app/logs
      - ./matrix/bots:/app/matrix/bots

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
    depends_on:
      - dashboard
```

### Phase 4: Documentation Updates (Priority: LOW)

#### Step 4.1: Update README

- Remove references to embedded dashboard
- Add multi-service startup instructions
- Update architecture diagrams

#### Step 4.2: Update API Documentation

- Separate MCP protocol docs from HTTP API docs
- Create OpenAPI spec for dashboard HTTP APIs
- Add integration examples for each frontend type

## Migration Strategy

### Step-by-Step Migration

1. **Create PersonaAPI server alongside existing MCP server**
2. **Test PersonaAPI server with current personas/bots**
3. **Update bot startup to use PersonaAPI server**
4. **Remove HTTP routes from MCP server**
5. **Update documentation and examples**

### Rollback Plan

- Keep current MCP server unchanged until dashboard is fully tested
- Feature flags to switch between embedded and external dashboard
- Database/data compatibility maintained throughout

### Testing Strategy

- **Unit tests** for MCP client and bot manager
- **Integration tests** for dashboard API endpoints
- **End-to-end tests** for full persona conversation flow
- **Load tests** for MCP server performance

## Success Metrics

### Performance

- **MCP Response Time** < 500ms for conversation requests
- **Dashboard Load Time** < 2s for admin interface
- **Bot Startup Time** < 10s from dashboard request to Matrix ready

### Reliability

- **MCP Uptime** > 99.9%
- **Dashboard Availability** > 99% (can be down without affecting conversations)
- **Bot Crash Recovery** < 30s automatic restart

### Developer Experience

- **Local Setup** < 5 minutes from clone to running
- **New Frontend Integration** < 1 hour for basic MCP connection
- **Dashboard Extension** Easy to add new admin features

This plan provides a clear path from the current mixed architecture to a clean, scalable system that supports the full vision from Matrix bots to Unreal Engine NPCs.
