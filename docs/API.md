# Persona MCP Server - API Reference

Complete API documentation for the Persona MCP Server.

## Protocol

- **Transport**: WebSocket
- **Protocol**: JSON-RPC 2.0
- **Endpoint**: `ws://localhost:8000/mcp`

## Request Format

```json
{
  "jsonrpc": "2.0",
  "method": "method_name",
  "params": {
    "parameter": "value"
  },
  "id": "unique_request_id"
}
```

## Response Format

```json
{
  "jsonrpc": "2.0",
  "result": {
    "response_data": "value"
  },
  "error": null,
  "id": "matching_request_id"
}
```

## Implemented Methods (25+ Endpoints)

### Persona Operations

#### persona.list

List all available personas with their current status.

**Parameters**: None

**Example Request**:

```json
{
  "jsonrpc": "2.0",
  "method": "persona.list",
  "id": "1"
}
```

**Example Response**:

```json
{
  "jsonrpc": "2.0",
  "result": {
    "personas": [
      {
        "id": "fb8c7404-48dd-4a68-a8b3-9e9b4226509d",
        "name": "Aria",
        "description": "A vibrant elven bard with sparkling eyes and an infectious laugh.",
        "available": true,
        "social_energy": 150,
        "current_priority": "social",
        "cooldown_remaining": 0
      }
    ],
    "total_count": 2,
    "available_count": 2
  },
  "id": "1"
}
```

#### persona.switch

Switch to a different persona for conversation.

**Parameters**:

- `persona_id` (string): Persona ID or name to switch to

**Example Request**:

```json
{
  "jsonrpc": "2.0",
  "method": "persona.switch",
  "params": {
    "persona_id": "aria"
  },
  "id": "2"
}
```

**Example Response**:

```json
{
  "jsonrpc": "2.0",
  "result": {
    "persona_id": "fb8c7404-48dd-4a68-a8b3-9e9b4226509d",
    "name": "Aria",
    "description": "A vibrant elven bard with sparkling eyes and an infectious laugh.",
    "status": "active",
    "social_energy": 150,
    "available_time": 600,
    "current_priority": "social"
  },
  "id": "2"
}
```

#### persona.chat

Send a message to the currently active persona.

**Parameters**:

- `message` (string): Message to send to the persona
- `token_budget` (integer, optional): Maximum tokens for response (default: 500)

**Example Request**:

```json
{
  "jsonrpc": "2.0",
  "method": "persona.chat",
  "params": {
    "message": "Hello! What's your favorite song?",
    "token_budget": 500
  },
  "id": "3"
}
```

**Example Response**:

```json
{
  "jsonrpc": "2.0",
  "result": {
    "response": "*eyes sparkle* Oh, I just adore 'Moonlit Serenade'! It's one of my own compositions...",
    "response_type": "direct",
    "continue_score": 50.0,
    "tokens_used": 76,
    "processing_time": 1.2,
    "persona_state": {
      "social_energy": 150,
      "available_time": 600,
      "interaction_fatigue": 0
    }
  },
  "id": "3"
}
```

#### persona.status

Get the current status of the active persona.

**Parameters**: None

**Example Request**:

```json
{
  "jsonrpc": "2.0",
  "method": "persona.status",
  "id": "4"
}
```

**Example Response**:

```json
{
  "jsonrpc": "2.0",
  "result": {
    "persona_id": "fb8c7404-48dd-4a68-a8b3-9e9b4226509d",
    "name": "Aria",
    "social_energy": 150,
    "available_time": 600,
    "interaction_fatigue": 0,
    "current_priority": "social",
    "is_available": true
  },
  "id": "4"
}
```

#### persona.create

Create a new persona dynamically.

**Parameters**:

- `name` (string): Persona name
- `description` (string): Persona description
- `personality_traits` (array, optional): List of personality traits
- `topic_preferences` (object, optional): Topic preference scores

**Example Request**:

```json
{
  "jsonrpc": "2.0",
  "method": "persona.create",
  "params": {
    "name": "Marcus",
    "description": "A wise old wizard with deep knowledge of magic",
    "personality_traits": ["wise", "patient", "scholarly"],
    "topic_preferences": {
      "magic": 95,
      "knowledge": 90,
      "teaching": 85
    }
  },
  "id": "5"
}
```

### Memory Management

#### memory.search

Search memories using semantic vector search.

**Parameters**:

- `query` (string): Search query
- `n_results` (integer, optional): Maximum results to return (default: 5)
- `min_importance` (float, optional): Minimum importance threshold (0.0-1.0)
- `persona_id` (string, optional): Search specific persona's memories

**Example Request**:

```json
{
  "jsonrpc": "2.0",
  "method": "memory.search",
  "params": {
    "query": "magic spells",
    "n_results": 10,
    "min_importance": 0.5
  },
  "id": "6"
}
```

**Example Response**:

```json
{
  "jsonrpc": "2.0",
  "result": {
    "memories": [
      {
        "id": "mem_123",
        "content": "User asked about fire magic spells...",
        "importance": 0.75,
        "similarity": 0.89,
        "created_at": "2025-10-13T10:30:00Z"
      }
    ],
    "total_results": 3
  },
  "id": "6"
}
```

#### memory.stats

Get memory collection statistics and health information.

**Parameters**: None

**Example Response**:

```json
{
  "jsonrpc": "2.0",
  "result": {
    "total_memories": 1247,
    "memories_by_persona": {
      "aria": 623,
      "kira": 624
    },
    "importance_distribution": {
      "high": 124,
      "medium": 623,
      "low": 500
    },
    "avg_importance": 0.62,
    "storage_size_mb": 12.4
  },
  "id": "7"
}
```

#### memory.prune

Intelligently prune memories for a specific persona.

**Parameters**:

- `persona_id` (string, optional): Persona to prune (defaults to current)
- `force` (boolean, optional): Force pruning even if not needed

**Example Request**:

```json
{
  "jsonrpc": "2.0",
  "method": "memory.prune",
  "params": {
    "force": false
  },
  "id": "8"
}
```

**Example Response**:

```json
{
  "jsonrpc": "2.0",
  "result": {
    "memories_before": 1247,
    "memories_pruned": 198,
    "memories_after": 1049,
    "avg_importance_pruned": 0.42,
    "processing_time": 0.003,
    "recommendation": "Pruned low-importance memories while protecting valuable content"
  },
  "id": "8"
}
```

#### memory.prune_recommendations

Get pruning recommendations without executing.

**Parameters**:

- `persona_id` (string, optional): Persona to analyze

**Example Response**:

```json
{
  "jsonrpc": "2.0",
  "result": {
    "recommendations": {
      "needs_pruning": true,
      "current_count": 1247,
      "would_prune": 198,
      "average_importance_to_prune": 0.42,
      "recommendation": "Would prune 198 memories with average importance 0.42"
    }
  },
  "id": "9"
}
```

### Memory Decay System

#### memory.decay_start

Start the background memory decay processing.

**Parameters**: None

**Example Response**:

```json
{
  "jsonrpc": "2.0",
  "result": {
    "status": "started",
    "message": "Background memory decay started",
    "interval_hours": 6,
    "decay_mode": "access_based"
  },
  "id": "10"
}
```

#### memory.decay_stats

Get memory decay system statistics.

**Example Response**:

```json
{
  "jsonrpc": "2.0",
  "result": {
    "background_running": true,
    "last_run": "2025-10-13T04:00:00Z",
    "total_decay_cycles": 15,
    "total_memories_decayed": 3247,
    "recent_cycle": {
      "personas_processed": 2,
      "memories_decayed": 52,
      "average_decay": 0.08,
      "processing_time": 0.15
    }
  },
  "id": "11"
}
```

### Conversation Management

#### conversation.start

Initialize a new conversation context.

**Parameters**:

- `persona_id` (string, optional): Persona for conversation
- `context` (string, optional): Initial context

#### conversation.status

Get active conversation state and statistics.

**Example Response**:

```json
{
  "jsonrpc": "2.0",
  "result": {
    "active_conversations": 1,
    "current_persona": "aria",
    "turn_count": 12,
    "total_tokens": 2456,
    "conversation_duration": 1842
  },
  "id": "12"
}
```

### System Operations

#### system.status

Get server health and performance metrics.

**Example Response**:

```json
{
  "jsonrpc": "2.0",
  "result": {
    "status": "healthy",
    "uptime_seconds": 86400,
    "active_connections": 3,
    "total_requests": 1247,
    "avg_response_time": 1.2,
    "memory_usage_mb": 156,
    "ollama_status": "connected"
  },
  "id": "13"
}
```

## Legacy Methods (Deprecated)

### persona.memory (DEPRECATED)

**Note**: This method has been replaced by the more powerful `memory.search` endpoint.

### persona.relationship (DEPRECATED)

**Note**: Relationship functionality is now integrated into the persona system.

## Error Responses

All errors follow the JSON-RPC 2.0 error format:

```json
{
  "jsonrpc": "2.0",
  "result": null,
  "error": {
    "code": -32603,
    "message": "Internal error: Description of what went wrong"
  },
  "id": "request_id"
}
```

### Common Error Codes

- `-32600`: Invalid Request
- `-32601`: Method not found
- `-32602`: Invalid params
- `-32603`: Internal error
- `-32700`: Parse error

## Session Management

The server maintains conversation sessions per WebSocket connection:

- **Session ID**: Generated per connection
- **Conversation Context**: Maintained separately per persona
- **Message History**: Last 20 messages kept active, older messages summarized
- **Session Timeout**: 24 hours of inactivity
- **Auto-cleanup**: Expired sessions automatically removed

## Configuration

Current configuration is hardcoded but will support:

```env
SERVER_HOST=localhost
SERVER_PORT=8000
OLLAMA_HOST=http://localhost:11434
DEFAULT_MODEL=llama3.1:8b
MAX_CONTEXT_MESSAGES=20
SESSION_TIMEOUT_HOURS=24
DEBUG_MODE=false
```

## Rate Limiting

Currently no rate limiting implemented. Planned for production:

- Per-connection message rate limits
- Token budget enforcement
- Conversation length limits
- Resource usage monitoring
