# Persona-MCP Architecture Vision

## Overview

The Persona-MCP system is designed as a **universal AI persona intelligence platform** that can power conversations across multiple frontends - from Matrix chat bots to Unreal Engine NPCs. The architecture emphasizes clean separation of concerns and universal accessibility.

## Core Principles

1. **MCP Server as Pure Intelligence** - The MCP server focuses solely on persona intelligence, memory, and conversation
2. **Frontend Agnostic Design** - Any application can connect via WebSocket to access persona intelligence
3. **External Tooling for Management** - Administrative interfaces are separate services that consume MCP
4. **Universal Protocol Access** - Same intelligence available to chat bots, games, and web applications
5. **Clean Separation with Parity** - Services maintain distinct responsibilities while supporting equivalent core operations through shared data and libraries

## Architecture Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Unreal Engine │    │  Mobile Apps    │    │  Dashboard Web  │    │  Matrix Bots    │
│                 │    │                 │    │    (port 8080)  │    │                 │
│  Game Clients   │    │  Unity Games    │    │  Admin Interface│    │  Chat Bots      │
│  NPCs           │    │  Web Browsers   │    │  Management     │    │  Assistants     │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │                      │
          │WebSocket             │WebSocket             │WebSocket             │WebSocket
          │(MCP Protocol)        │(MCP Protocol)        │(MCP Protocol)        │(MCP Protocol)
          │                      │                      │                      │
          └──────────────────────┼──────────────────────┼──────────────────────┘
                                 │                      │
                                 │              ┌───────▼───────┐
                                 │              │ HTTP/REST API │
                                 │              │ (Management)  │
                                 │              └───────┬───────┘
                                 │                      │
                    ┌────────────▼──────────────────────▼─────────────┐
                    │            MCP Server (port 8000)              │
                    │                                                 │
                    │  🧠 Persona Intelligence    💾 Memory System   │
                    │  🤝 Relationship Management 💬 Conversations   │
                    │  🎭 Personality Engine      📚 Learning        │
                    │  🔄 Real-time Sync          🛡️  Session Mgmt   │
                    └─────────────────────────────────────────────────┘
```

## Service Responsibilities

### MCP Server (port 8000) - **Intelligence Core**

**Primary Function:** Pure AI persona intelligence and conversation management

**Responsibilities:**

- Persona intelligence and personality simulation
- Memory management and retrieval
- Conversation processing and context
- Relationship tracking between personas
- Real-time session management
- Learning and adaptation

**Protocol:** WebSocket with JSON-RPC 2.0 (MCP Protocol)

**Key Methods:**

```json
{
  "persona.list": "Get all available personas",
  "persona.switch": "Set active persona for session",
  "conversation.send_message": "Process message and generate response",
  "memory.search": "Search persona memories",
  "relationship.get": "Get relationships for persona"
}
```

### PersonaAPI Server (port 8080) - **Management Interface**

**Primary Function:** Administrative interface and bot process management

**Responsibilities:**

- Web-based admin dashboard
- Bot process lifecycle management
- Matrix profile management (avatars, display names)
- Channel configuration and moderation
- User management and permissions
- System monitoring and analytics
- File uploads and media management

**Protocols:**

- HTTP/REST API for web interface
- WebSocket client to MCP server for data

**Key Features:**

- Persona CRUD operations
- Bot start/stop/restart controls
- Real-time log viewing
- Performance monitoring
- Matrix room management
- User access controls

## Service Parity and Shared Components

### Shared Foundation

Both MCP and PersonaAPI servers maintain **operational parity** through shared components:

**Shared Libraries:**

- **Database Layer** - Common SQLiteManager and VectorMemoryManager
- **Model Definitions** - Shared Persona, Memory, and Relationship models
- **Configuration Management** - Unified configuration system
- **Logging Framework** - Consistent logging patterns and formats

**Data Consistency:**

- **Single Source of Truth** - Both services access the same database files
- **Atomic Operations** - Database transactions ensure consistency
- **Real-time Sync** - Changes from either service are immediately visible to the other

**Equivalent Operations:**
| Operation | MCP Method | Dashboard HTTP | Shared Implementation |
|-----------|------------|----------------|----------------------|
| List Personas | `persona.list` | `GET /api/personas` | `db.list_personas()` |
| Create Persona | `persona.create` | `POST /api/personas` | `db.create_persona()` |  
| Delete Persona | `persona.delete` | `DELETE /api/personas/{id}` | `db.delete_persona()` |
| Search Memory | `memory.search` | `GET /api/memory/search` | `memory.search_memories()` |

### Service-Specific Extensions

While maintaining parity for core operations, each service provides unique capabilities:

**MCP Server Specializations:**

- Real-time conversation processing
- Session state management
- WebSocket connection handling
- Game engine optimizations

**PersonaAPI Server Specializations:**

- File upload handling (avatars, media)
- Complex web forms and validation
- Bot process lifecycle management
- Rich analytics and monitoring UIs

## Frontend Integration Patterns

### Matrix Chat Bots

```python
# Matrix bot connects directly to MCP
class MCPPersonaBot:
    def __init__(self, persona_id):
        self.mcp_ws = websockets.connect("ws://localhost:8000/mcp")

    async def on_message(self, message):
        response = await self.mcp_call("conversation.send_message", {
            "content": message,
            "sender": sender_id
        })
        await self.matrix_client.send(response["result"]["response"])
```

### Unreal Engine Integration

```cpp
// Unreal Engine connects directly to MCP
class APersonaNPC : public AActor {
    TSharedPtr<IWebSocket> MCPSocket;

    void StartConversation(FString PlayerMessage) {
        FString Request = CreateMCPRequest("conversation.send_message", {
            {"content", PlayerMessage},
            {"persona_id", PersonaID},
            {"context", GetGameContext()}
        });
        MCPSocket->Send(Request);
    }

    void OnMCPResponse(const FString& Response) {
        // Parse response and trigger NPC dialogue/animation
        PlayDialogue(ParseMCPResponse(Response));
    }
};
```

### Web Dashboard

```javascript
// Dashboard uses both HTTP API and MCP WebSocket
class DashboardClient {
  constructor() {
    this.mcp_ws = new WebSocket("ws://localhost:8000/mcp");
    this.api_base = "http://localhost:8080/api";
  }

  // Bot management via HTTP
  async startBot(personaId) {
    return fetch(`${this.api_base}/bots/${personaId}/start`, {
      method: "POST",
    });
  }

  // Real-time data via MCP
  async getPersonaList() {
    return this.mcpCall("persona.list", {});
  }
}
```

## Development Phases

### Phase 1: Current State ✅

- MCP server with persona intelligence
- Matrix bot integration
- Basic web widgets for persona creation

### Phase 2: Clean Architecture (In Progress)

- Separate PersonaAPI server from MCP server
- Pure MCP protocol for intelligence
- HTTP/REST for administrative functions
- Enhanced bot management and logging

### Phase 3: Advanced Dashboard

- Matrix profile management (avatars, names)
- Channel configuration and moderation
- User permissions and access controls
- Analytics and monitoring dashboards

### Phase 4: Game Engine Integration

- Unreal Engine persona components
- Unity integration packages
- Real-time spatial awareness
- Multi-persona scene management

### Phase 5: Enterprise Features

- Cloud deployment and scaling
- Multi-tenant persona isolation
- Advanced analytics and AI training
- Enterprise security and compliance

## Technical Benefits

### Universal Access

- **Single Protocol:** Any client can access full persona intelligence via MCP WebSocket
- **No Vendor Lock-in:** Not tied to any specific frontend framework
- **Real-time by Design:** WebSocket enables instant responses and live updates

### Clean Separation with Parity

- **MCP Server:** Pure intelligence, no UI concerns, optimized for real-time operations
- **PersonaAPI Server:** Rich web features without affecting core intelligence
- **Shared Foundation:** Common data access, models, and business logic
- **Operational Equivalence:** Both services can perform the same core operations
- **Independent Scaling:** Scale intelligence and management separately while maintaining consistency

### Developer Experience

- **Familiar Patterns:** HTTP/REST for web, WebSocket for real-time
- **Tool Flexibility:** Use best tools for each concern (FastAPI for web, custom for MCP)
- **Clear Boundaries:** Easy to debug and maintain separate services

## Deployment Scenarios

### Development

```bash
# Terminal 1: Start MCP intelligence server
python -m persona_mcp.mcp.server

# Terminal 2: Start dashboard management server
python -m persona_mcp.dashboard.server

# Terminal 3: Start Matrix bots
python matrix/bots/universal_mcp_bot.py --persona-id alice_id --persona-name Alice
```

### Production

```yaml
# Docker Compose
services:
  mcp-server:
    image: persona-mcp:latest
    ports: ["8000:8000"]
    environment:
      - MODE=production

  dashboard:
    image: persona-dashboard:latest
    ports: ["8080:8080"]
    depends_on: [mcp-server]

  nginx:
    image: nginx:alpine
    ports: ["80:80", "443:443"]
    # Proxy dashboard web interface, expose MCP WebSocket
```

### Game Server

```yaml
# Dedicated game server deployment
services:
  mcp-intelligence:
    image: persona-mcp:gaming
    ports: ["8000:8000"] # Private network only
    resources:
      memory: 4GB
      cpu: 2.0

  game-admin:
    image: persona-dashboard:gaming
    ports: ["8080:8080"] # Admin access only
    environment:
      - MCP_SERVER=mcp-intelligence:8000
      - AUTH_REQUIRED=true
```

## Future Considerations

### Scalability

- **Horizontal Scaling:** Multiple MCP server instances behind load balancer
- **Database Sharding:** Partition personas across multiple databases
- **Memory Caching:** Redis for frequently accessed persona data
- **CDN Integration:** Asset delivery for profile images and media

### Security

- **Authentication:** JWT tokens for dashboard access
- **Authorization:** Role-based permissions for persona access
- **Rate Limiting:** Prevent abuse of intelligence APIs
- **Audit Logging:** Track all persona interactions and changes

### Monitoring

- **Health Checks:** Automatic detection of failed services
- **Performance Metrics:** Response times and throughput monitoring
- **Error Tracking:** Centralized logging and alerting
- **Resource Usage:** CPU, memory, and storage monitoring

This architecture provides a solid foundation that can grow from simple chat bots to complex game NPCs while maintaining clean separation of concerns and universal accessibility.
