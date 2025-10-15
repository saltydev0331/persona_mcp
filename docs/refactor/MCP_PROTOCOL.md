# MCP Protocol Reference

## Overview

The Persona MCP system implements a clean separation with parity architecture, providing identical functionality through two specialized interfaces:

1. **MCP Server**: WebSocket-based Model Context Protocol server for AI agent integration
2. **PersonaAPI Server**: HTTP REST API for web-based management and monitoring

Both services share a common core foundation ensuring operational equivalence while specializing in their respective protocols.

## Architecture Principles

### Clean Separation with Parity

- **Shared Core**: Both services use identical business logic from `persona_mcp/core/`
- **Interface Specialization**: Each service optimizes for its protocol (WebSocket vs HTTP)
- **Operational Equivalence**: Same capabilities available through both interfaces
- **Deployment Flexibility**: Services can run independently or together

## MCP Server Protocol

The Model Context Protocol (MCP) for Persona-MCP uses JSON-RPC 2.0 over WebSocket to provide universal access to AI persona intelligence. This protocol is designed to be frontend-agnostic and support everything from chat bots to game engines.

## MCP Connection

**Endpoint:** `ws://localhost:8000/mcp`  
**Protocol:** WebSocket with JSON-RPC 2.0  
**Content-Type:** `application/json`

### Basic Connection Example

```javascript
const ws = new WebSocket("ws://localhost:8000/mcp");

ws.onopen = () => {
  console.log("Connected to MCP server");
};

ws.onmessage = (event) => {
  const response = JSON.parse(event.data);
  console.log("MCP Response:", response);
};
```

## PersonaAPI Reference

**Base URL:** `http://localhost:8080`  
**Protocol:** HTTP REST API  
**Content-Type:** `application/json`

### PersonaAPI Connection Example

```javascript
// Same functionality as MCP, different interface
const response = await fetch("http://localhost:8080/api/personas");
const personas = await response.json();
```

Both interfaces provide identical capabilities with the same underlying business logic.

## Request Format

All requests follow JSON-RPC 2.0 format:

```json
{
  "jsonrpc": "2.0",
  "method": "method_name",
  "params": {
    "param1": "value1",
    "param2": "value2"
  },
  "id": "unique_request_id"
}
```

## Response Format

Success responses:

```json
{
  "jsonrpc": "2.0",
  "result": {
    "data": "response_data"
  },
  "id": "unique_request_id"
}
```

Error responses:

```json
{
  "jsonrpc": "2.0",
  "error": {
    "code": -32601,
    "message": "Method not found"
  },
  "id": "unique_request_id"
}
```

## Available Methods

### Persona Management

#### `persona.list`

Get all available personas.

**Parameters:** None

**Response:**

```json
{
  "result": {
    "personas": [
      {
        "id": "22152f32-8668-4830-bd5e-c3918dcbc68f",
        "name": "alice",
        "description": "A curious and helpful AI assistant",
        "personality_traits": {
          "openness": 0.8,
          "conscientiousness": 0.7,
          "extraversion": 0.6,
          "agreeableness": 0.9,
          "neuroticism": 0.3
        },
        "created_at": "2025-10-15T10:30:00Z"
      }
    ]
  }
}
```

#### `persona.get`

Get details for a specific persona.

**Parameters:**

- `persona_id` (string): UUID of the persona

**Response:**

```json
{
    "result": {
        "persona": {
            "id": "22152f32-8668-4830-bd5e-c3918dcbc68f",
            "name": "alice",
            "description": "A curious and helpful AI assistant",
            "personality_traits": {...},
            "memory_stats": {
                "total_memories": 150,
                "recent_interactions": 23
            }
        }
    }
}
```

#### `persona.switch`

Set the active persona for the current session.

**Parameters:**

- `persona_id` (string): UUID of the persona to activate

**Response:**

```json
{
  "result": {
    "message": "Switched to persona: alice",
    "persona_id": "22152f32-8668-4830-bd5e-c3918dcbc68f",
    "session_id": "session_123"
  }
}
```

#### `persona.create`

Create a new persona.

**Parameters:**

- `name` (string): Persona name
- `description` (string): Persona description
- `personality_traits` (object): Big Five personality scores (0.0-1.0)
- `backstory` (string, optional): Persona backstory
- `goals` (array, optional): Persona goals

**Response:**

```json
{
  "result": {
    "persona_id": "new-uuid-here",
    "message": "Persona created successfully"
  }
}
```

#### `persona.delete`

Delete a persona and all associated data.

**Parameters:**

- `persona_id` (string): UUID of the persona to delete

**Response:**

```json
{
  "result": {
    "message": "Persona 'alice' and all associated data deleted successfully"
  }
}
```

### Conversation

#### `conversation.send_message`

Send a message to the active persona and get a response.

**Parameters:**

- `content` (string): The message content
- `sender` (string, optional): Identifier for the sender
- `room_id` (string, optional): Room/channel identifier
- `context` (object, optional): Additional context information

**Response:**

```json
{
  "result": {
    "response": "Hello! How can I help you today?",
    "persona_id": "22152f32-8668-4830-bd5e-c3918dcbc68f",
    "response_time_ms": 580,
    "memory_stored": true
  }
}
```

#### `conversation.get_history`

Get conversation history for the current session.

**Parameters:**

- `limit` (integer, optional): Maximum number of messages (default: 20)
- `before_id` (string, optional): Get messages before this ID

**Response:**

```json
{
  "result": {
    "messages": [
      {
        "id": "msg_123",
        "content": "Hello!",
        "sender": "user_456",
        "timestamp": "2025-10-15T10:30:00Z",
        "persona_response": "Hi there! How are you?"
      }
    ],
    "has_more": false
  }
}
```

### Memory Management

#### `memory.search`

Search persona memories.

**Parameters:**

- `query` (string): Search query
- `persona_id` (string, optional): Specific persona (uses active if not provided)
- `n_results` (integer, optional): Maximum results (default: 5)
- `min_importance` (float, optional): Minimum importance score (default: 0.0)

**Response:**

```json
{
  "result": {
    "memories": [
      {
        "id": "memory_123",
        "content": "User mentioned they like coffee",
        "importance": 0.7,
        "created_at": "2025-10-15T10:30:00Z",
        "related_personas": ["alice"]
      }
    ]
  }
}
```

#### `memory.get_stats`

Get memory statistics for a persona.

**Parameters:**

- `persona_id` (string, optional): Specific persona (uses active if not provided)

**Response:**

```json
{
  "result": {
    "total_memories": 150,
    "memory_types": {
      "conversation": 120,
      "observation": 20,
      "reflection": 10
    },
    "average_importance": 0.65,
    "oldest_memory": "2025-10-01T00:00:00Z",
    "newest_memory": "2025-10-15T10:30:00Z"
  }
}
```

### Relationship Management

#### `relationship.get`

Get relationships for a persona.

**Parameters:**

- `persona_id` (string, optional): Specific persona (uses active if not provided)

**Response:**

```json
{
  "result": {
    "relationships": [
      {
        "target_persona_id": "bob_uuid",
        "target_persona_name": "bob",
        "relationship_type": "friend",
        "strength": 0.8,
        "last_interaction": "2025-10-15T09:00:00Z"
      }
    ]
  }
}
```

#### `relationship.update`

Update relationship between personas.

**Parameters:**

- `persona_id` (string): Source persona
- `target_persona_id` (string): Target persona
- `relationship_type` (string): Type of relationship
- `strength` (float): Relationship strength (0.0-1.0)

**Response:**

```json
{
  "result": {
    "message": "Relationship updated successfully"
  }
}
```

## Session Management

### Session Context

Each WebSocket connection maintains a session that can have:

- Active persona
- Conversation history
- Temporary context

### Session Methods

#### `session.get_info`

Get current session information.

**Response:**

```json
{
  "result": {
    "session_id": "session_123",
    "active_persona_id": "alice_uuid",
    "active_persona_name": "alice",
    "connection_time": "2025-10-15T10:00:00Z",
    "message_count": 15
  }
}
```

#### `session.clear`

Clear session context (keeps connection open).

**Response:**

```json
{
  "result": {
    "message": "Session cleared successfully"
  }
}
```

## Error Codes

| Code   | Message           | Description                     |
| ------ | ----------------- | ------------------------------- |
| -32700 | Parse error       | Invalid JSON                    |
| -32600 | Invalid Request   | Invalid JSON-RPC                |
| -32601 | Method not found  | Method doesn't exist            |
| -32602 | Invalid params    | Invalid method parameters       |
| -32603 | Internal error    | Server internal error           |
| -32000 | Persona not found | Specified persona doesn't exist |
| -32001 | No active persona | No persona set for session      |
| -32002 | Memory error      | Memory system error             |
| -32003 | LLM error         | Language model error            |

## Usage Examples

### JavaScript/Web Browser

```javascript
class MCPClient {
  constructor(uri = "ws://localhost:8000/mcp") {
    this.ws = new WebSocket(uri);
    this.requestId = 0;
    this.pendingRequests = new Map();

    this.ws.onmessage = (event) => {
      const response = JSON.parse(event.data);
      const promise = this.pendingRequests.get(response.id);
      if (promise) {
        this.pendingRequests.delete(response.id);
        if (response.error) {
          promise.reject(new Error(response.error.message));
        } else {
          promise.resolve(response.result);
        }
      }
    };
  }

  async call(method, params = {}) {
    return new Promise((resolve, reject) => {
      const id = String(++this.requestId);
      this.pendingRequests.set(id, { resolve, reject });

      this.ws.send(
        JSON.stringify({
          jsonrpc: "2.0",
          method,
          params,
          id,
        })
      );
    });
  }

  async switchPersona(personaId) {
    return this.call("persona.switch", { persona_id: personaId });
  }

  async sendMessage(content, sender = "user") {
    return this.call("conversation.send_message", { content, sender });
  }
}

// Usage
const mcp = new MCPClient();
await mcp.switchPersona("alice_uuid");
const response = await mcp.sendMessage("Hello Alice!");
console.log(response.response); // Alice's reply
```

### Python Client

```python
import asyncio
import json
import websockets

class MCPClient:
    def __init__(self, uri="ws://localhost:8000/mcp"):
        self.uri = uri
        self.websocket = None
        self.request_id = 0

    async def connect(self):
        self.websocket = await websockets.connect(self.uri)

    async def call(self, method, params=None):
        self.request_id += 1
        request = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {},
            "id": str(self.request_id)
        }

        await self.websocket.send(json.dumps(request))
        response = await self.websocket.recv()
        result = json.loads(response)

        if "error" in result:
            raise Exception(result["error"]["message"])
        return result["result"]

    async def switch_persona(self, persona_id):
        return await self.call("persona.switch", {"persona_id": persona_id})

    async def send_message(self, content, sender="user"):
        return await self.call("conversation.send_message", {
            "content": content,
            "sender": sender
        })

# Usage
async def main():
    mcp = MCPClient()
    await mcp.connect()

    await mcp.switch_persona("alice_uuid")
    response = await mcp.send_message("Hello Alice!")
    print(response["response"])  # Alice's reply

asyncio.run(main())
```

This protocol provides the foundation for universal access to persona intelligence across all frontend types, from web browsers to game engines.
