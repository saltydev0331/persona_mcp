# Persona MCP Server

A local-first MCP (Model Context Protocol) server for managing AI persona interactions. Runs entirely offline using open-source components.

## Features

- **Local-first**: No cloud dependencies, runs entirely on your workstation
- **MCP Compliant**: Implements JSON-RPC 2.0 over WebSocket
- **Persona Management**: Dynamic persona switching and conversation state
- **Memory System**: Vector memory using ChromaDB for long-term context
- **Relationship Dynamics**: Social compatibility and interaction history
- **Continue Score System**: Intelligent conversation flow management
- **Simulation Harness**: Built-in testing with chatroom scenarios

## Quick Start

1. **Install Dependencies**

   ```bash
   pip install -r requirements.txt
   ```

2. **Start Ollama** (if not running)

   ```bash
   ollama serve
   ollama pull llama3.1:8b
   ```

3. **Run the Server**

   ```bash
   python server.py
   ```

4. **Connect via WebSocket**
   ```
   ws://localhost:8000/mcp
   ```

## Architecture

```
persona-mcp/
├── persona_mcp/           # Core server package
│   ├── models/           # Pydantic data models
│   ├── persistence/      # SQLite + ChromaDB storage
│   ├── conversation/     # Conversation engine
│   ├── llm/             # Ollama integration
│   ├── mcp/             # MCP protocol handlers
│   └── simulation/      # Testing harness
├── tests/               # Test suite
├── data/               # Local database files
├── logs/               # Server logs
└── server.py           # Main entry point
```

## MCP Protocol Endpoints

### Core Operations

- `persona.switch` - Change active persona
- `persona.chat` - Send message to persona
- `persona.list` - Get available personas
- `visual.update` - Update visual context

### State Management

- `state.save` - Persist current state
- `state.load` - Restore previous state
- `memory.search` - Query vector memory

## Configuration

Edit `.env` file:

```env
SERVER_HOST=localhost
SERVER_PORT=8000
OLLAMA_HOST=http://localhost:11434
DEFAULT_MODEL=llama3.1:8b
```

## Performance

**Current**: ~50 concurrent WebSocket connections, 1-7s response times  
**Optimized**: 500+ connections, 2-3x faster processing with targeted improvements

WebSocket MCP provides superior performance vs HTTP for conversational AI:

- Persistent connections eliminate handshake overhead
- Stateful session management keeps context in memory
- Real-time bidirectional communication
- Optimized for interactive persona conversations

See [`docs/PERFORMANCE.md`](docs/PERFORMANCE.md) for detailed optimization guide.

## Testing

```bash
# Run unit tests
python -m pytest tests/

# Start simulation
python -m persona_mcp.simulation.chatroom

# Performance testing
python client/mcp_client.py --auto-test
```

## License

MIT License - see LICENSE file for details.
