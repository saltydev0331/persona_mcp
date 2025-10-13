# Persona MCP Server - Quick Start Guide

## Installation

1. **Clone the repository**

   ```bash
   git clone <repository-url>
   cd persona-mcp
   ```

2. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

3. **Install Ollama (for local LLM)**
   ```bash
   # Install Ollama from https://ollama.ai
   ollama serve
   ollama pull llama3.1:8b
   ```

## Quick Start

1. **Start the server**

   ```bash
   python server.py
   ```

2. **Connect via WebSocket**

   ```
   ws://localhost:8000/mcp
   ```

3. **Send JSON-RPC 2.0 messages**
   ```json
   { "jsonrpc": "2.0", "method": "persona.list", "id": "1" }
   ```

## Example Usage

```bash
# Run interactive examples
python examples.py

# Run simulation test
python server.py --simulate 5

# Start with debug logging
python server.py --debug
```

## Core MCP Methods

- `persona.list` - List available personas
- `persona.switch` - Switch to persona
- `persona.chat` - Send message
- `system.status` - Get server status
- `memory.search` - Search memories

## Testing

```bash
# Run test suite
python -m pytest tests/

# Run specific tests
python -m pytest tests/test_models.py -v
```

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   MCP Client    │───▶│  WebSocket API   │───▶│ Conversation    │
│  (Your App)     │    │  JSON-RPC 2.0    │    │    Engine       │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                                        │
                       ┌─────────────────┐              │
                       │  Local Ollama   │◀─────────────┤
                       │     LLM         │              │
                       └─────────────────┘              │
                                                        ▼
                       ┌─────────────────┐    ┌─────────────────┐
                       │    ChromaDB     │◀───│   Persistence   │
                       │  Vector Memory  │    │   SQLite + Vec  │
                       └─────────────────┘    └─────────────────┘
```

## Default Personas

- **Aria** - Energetic elven bard (social, creative)
- **Kira** - Focused human scholar (academic, analytical)

## Configuration

Edit `.env` file:

```env
SERVER_HOST=localhost
SERVER_PORT=8000
OLLAMA_HOST=http://localhost:11434
DEFAULT_MODEL=llama3.1:8b
```
