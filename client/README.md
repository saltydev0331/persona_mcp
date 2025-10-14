# MCP Test Client

A comprehensive WebSocket client for testing your Persona MCP server.

## Quick Start

1. **Install dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

2. **Make sure your MCP server is running:**

   ```bash
   # In the main project directory
   python server.py
   ```

3. **Run the test client:**

   ### Interactive Mode (Recommended)

   ```bash
   python mcp_client.py
   ```

   ### Automated Tests

   ```bash
   python mcp_client.py --auto-test
   ```

   ### Single Method Test

   ```bash
   python mcp_client.py --method persona.list
   python mcp_client.py --method persona.chat --params '{"message":"Hello!"}'
   ```

## Interactive Commands

Once in interactive mode, you can use these commands:

- `list` - List all available personas
- `switch aria` - Switch to Aria persona
- `switch kira` - Switch to Kira persona
- `chat Hello there!` - Chat with current persona
- `memory introduction` - Search semantic memory
- `memory-stats` - Show memory system statistics
- `prune` - Prune low-importance memories (safe)
- `prune --force` - Force memory pruning
- `status` - Get current persona status
- `raw persona.list` - Send raw MCP request
- `help` - Show all commands
- `quit` - Exit the client

## Example Session

```
mcp> list
[18:20:15] → Sending: persona.list
[18:20:15] ✓ Success
    Result: {
      "personas": [
        {"id": "aria", "name": "Aria", "description": "..."},
        {"id": "kira", "name": "Kira", "description": "..."}
      ]
    }

mcp> switch aria
[18:20:20] → Sending: persona.switch
    Params: {"persona_id": "aria"}
[18:20:20] ✓ Success

mcp> chat Hello Aria! How are you today?
[18:20:25] → Sending: persona.chat
    Params: {"message": "Hello Aria! How are you today?", "token_budget": 500}
[18:20:26] ✓ Success
    Result: {
      "response": "Hello! I'm doing wonderfully today...",
      "persona_state": {...}
    }

mcp> memory introduction
[18:20:30] → Sending: memory.search
    Params: {"query": "introduction", "n_results": 5, "min_importance": 0.0}
[18:20:30] ✓ Success
    Result: {
      "memories": [...],
      "total_results": 3
    }

mcp> memory-stats
[18:20:35] → Sending: memory.stats
[18:20:35] ✓ Success
    Result: {
      "total_memories": 150,
      "avg_importance": 0.65,
      "storage_size_mb": 2.3
    }
```

## Configuration

- **Default URI:** `ws://localhost:8000/mcp`
- **Custom URI:** `python mcp_client.py --uri ws://your-server:port/mcp`

## Features

✅ **Interactive CLI** - Easy command-line interface  
✅ **Automated Tests** - Complete 10-test suite with modern API methods  
✅ **All MCP Methods** - Supports 25+ MCP endpoints including memory management  
✅ **Modern Memory API** - Uses updated `memory.search`, `memory.stats`, `memory.prune`  
✅ **Real-time Logs** - Timestamped request/response logs  
✅ **Error Handling** - Graceful error reporting  
✅ **JSON Pretty Print** - Readable response formatting  
✅ **Raw Mode** - Send custom JSON-RPC requests  
✅ **Memory Management** - Test semantic search, pruning, and statistics

This client is perfect for developing and testing your MCP server integrations with full support for the enhanced memory system!
