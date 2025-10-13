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

## Implemented Methods

### persona.list

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

### persona.switch

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

### persona.chat

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

### persona.status

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

## Stubbed Methods (Partial Implementation)

### persona.memory

Search conversation memory for specific content.

**Parameters**:

- `query` (string): Search query
- `min_importance` (float, optional): Minimum importance threshold (0.0-1.0)
- `limit` (integer, optional): Maximum results to return

**Current Status**: Returns placeholder response, full implementation planned.

### persona.relationship

Check relationship status with current persona.

**Parameters**:

- `target` (string, optional): Target persona to check relationship with

**Current Status**: Returns placeholder response, full implementation planned.

## Planned Methods (Not Yet Implemented)

### conversation.start

Start a new conversation context.

### conversation.end

End the current conversation context.

### conversation.status

Get conversation statistics and status.

### memory.search

Advanced memory search across all personas.

### memory.store

Manually store a memory entry.

### memory.stats

Get memory system statistics.

### state.save

Save current server state to file.

### state.load

Load server state from file.

### visual.update

Update visual context for conversations.

### system.status

Get server system status and health.

### system.models

Get available LLM models and their status.

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
