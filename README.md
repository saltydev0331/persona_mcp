# Persona MCP Server

A production-ready, local-first MCP (Model Context Protocol) server for managing AI persona interactions with intelligent memory management. Runs entirely offline using open-source components with enterprise-grade memory systems.

## ✨ Key Features

### 🧠 **Intelligent Memory Management**

- **Smart Importance Scoring**: Context-aware scoring (0.51-0.80) replacing hardcoded values
- **Automatic Pruning**: Protects valuable memories while cleaning low-importance content
- **Memory Decay**: Background aging with graduated decay (16.4%-66.7%) over time
- **Self-Managing**: Maintains memory quality and performance automatically

### 🎭 **Advanced Persona System**

- **Dynamic Personas**: Seamless switching with persistent conversation state
- **Relationship Dynamics**: Social compatibility and interaction history tracking
- **Continue Score System**: Intelligent conversation flow management
- **Topic Preferences**: Personalized content relevance scoring

### 🏗️ **Production Architecture**

- **Local-first**: Zero cloud dependencies, complete offline operation
- **MCP Compliant**: Full JSON-RPC 2.0 over WebSocket implementation
- **Vector Memory**: ChromaDB for semantic search and long-term context
- **Performance Optimized**: Handles 50+ concurrent connections efficiently

### 🧪 **Testing & Simulation**

- **Comprehensive Test Suite**: Memory, pruning, and decay system validation
- **Chatroom Simulation**: Multi-persona interaction testing harness
- **API Testing**: Complete MCP endpoint validation tools

## Quick Start

1. **Create Virtual Environment**

   ```bash
   python -m venv venv

   # Windows (PowerShell)
   venv\Scripts\activate

   # macOS/Linux
   source venv/bin/activate
   ```

2. **Install Dependencies**

   ```bash
   pip install -r requirements.txt
   ```

3. **Start Ollama** (if not running)

   ```bash
   ollama serve
   ollama pull llama3.1:8b
   ```

4. **Run the Server**

   ```bash
   # Ensure venv is activated first
   python server.py
   ```

5. **Connect via WebSocket**
   ```
   ws://localhost:8000/mcp
   ```

## Architecture

```
persona-mcp/
├── persona_mcp/           # Core server package
│   ├── memory/           # 🧠 Intelligent memory management
│   │   ├── importance_scorer.py   # Context-aware importance scoring
│   │   ├── pruning_system.py     # Automatic memory cleanup
│   │   └── decay_system.py       # Background memory aging
│   ├── models/           # Pydantic data models & database schemas
│   ├── persistence/      # SQLite + ChromaDB dual storage
│   ├── conversation/     # Advanced conversation engine
│   ├── llm/             # Ollama integration with async support
│   ├── mcp/             # Full MCP protocol implementation
│   └── simulation/      # Multi-persona testing harness
├── tests/               # Comprehensive test suite
├── docs/                # Documentation and design specs
├── client/              # Reference MCP client implementation
├── data/               # Local SQLite databases
├── logs/               # Structured logging output
└── server.py           # Production server entry point
```

### Memory Management Flow

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   User Chat     │───▶│ Importance Scorer │───▶│  ChromaDB       │
│                 │    │  (0.51-0.80)     │    │  Storage        │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                                        │
       ┌─────────────────────────────────────────────────┤
       │                                                 │
       ▼                                                 ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│ Decay System    │───▶│ Pruning System   │───▶│   Optimized     │
│ (Background)    │    │ (Smart Cleanup)  │    │   Performance   │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## MCP Protocol Endpoints

### 🎭 Persona Operations

- `persona.switch` - Change active persona with context preservation
- `persona.chat` - Send message with intelligent memory storage
- `persona.list` - Get available personas with status info
- `persona.create` - Create new personas dynamically
- `persona.status` - Get detailed persona state information

### 🧠 Memory Management

- `memory.search` - Semantic vector search across memories
- `memory.store` - Manual memory storage with importance scoring
- `memory.stats` - Memory collection statistics and health
- `memory.prune` - Intelligent memory cleanup (single persona)
- `memory.prune_all` - Global memory optimization
- `memory.prune_recommendations` - Preview pruning suggestions
- `memory.prune_stats` - Pruning system performance metrics

### ⏰ Memory Decay System

- `memory.decay_start` - Begin background memory aging
- `memory.decay_stop` - Halt decay processing
- `memory.decay_stats` - Decay system status and metrics
- `memory.decay_force` - Force decay with custom parameters

### 💬 Conversation Management

- `conversation.start` - Initialize new conversation context
- `conversation.end` - Finalize and store conversation
- `conversation.status` - Get active conversation state

### 🔧 System Operations

- `system.status` - Server health and performance metrics
- `system.models` - Available Ollama models
- `state.save` - Persist complete system state
- `state.load` - Restore previous system state
- `visual.update` - Update visual context information

## ⚙️ Configuration

### Environment Setup

Create `.env` file in project root:

```env
# Server Configuration
SERVER_HOST=localhost
SERVER_PORT=8000
DEBUG_MODE=false

# LLM Configuration
OLLAMA_HOST=http://localhost:11434
DEFAULT_MODEL=llama3.1:8b

# Memory System Configuration
MAX_MEMORIES_PER_PERSONA=1000
PRUNING_THRESHOLD=900
DECAY_INTERVAL_HOURS=6
BACKGROUND_PROCESSING=true

# Database Configuration
DATABASE_PATH=data/persona_memory.db
CHROMADB_PATH=data/chromadb
```

### Memory System Tuning

```python
# Advanced memory configuration
IMPORTANCE_WEIGHTS = {
    "emotional": 0.25,      # Emotional content detection
    "context": 0.20,        # Significance patterns
    "interests": 0.15,      # Persona alignment
    "engagement": 0.10,     # User interaction quality
    "relationship": 0.10,   # Social factors
    "recency": 0.05        # Time-based bonus
}

DECAY_MODES = ["linear", "exponential", "logarithmic", "access_based"]
PRUNING_STRATEGIES = ["importance_only", "importance_access", "importance_access_age"]
```

## 🚀 Performance & Scaling

### Current Production Metrics

- **Connections**: ~50 concurrent WebSocket connections
- **Response Times**: 1-7s for complex conversations
- **Memory Processing**: 14 memories analyzed in 0.001s (pruning)
- **Background Tasks**: Automatic decay every 6 hours
- **Storage**: SQLite + ChromaDB hybrid architecture

### Optimization Targets

- **Target**: 500+ concurrent connections
- **Goal**: 2-3x faster LLM response processing
- **Memory**: Sub-millisecond importance scoring
- **Scalability**: Distributed persona deployment ready

### Architecture Advantages

- **WebSocket MCP**: Superior to HTTP for conversational AI
- **Persistent Connections**: Eliminates handshake overhead
- **Stateful Sessions**: Context retained in memory
- **Real-time Communication**: Bidirectional streaming
- **Self-Managing Memory**: Automated quality maintenance

### Memory System Performance

```
Operation                    | Performance      | Safety
----------------------------|------------------|------------------
Importance Scoring          | 0.51-0.80 range | Context-aware
Memory Pruning             | 0.001s / 14 mem  | Protects valuable
Background Decay           | 6hr intervals    | Graduated aging
Auto-Pruning Trigger       | 1000+ memories   | Smart thresholds
```

## 🧪 Testing & Validation

### Comprehensive Test Suite

```bash
# Activate virtual environment first
venv\Scripts\activate  # Windows
# source venv/bin/activate  # macOS/Linux

# Run complete test suite
python -m pytest tests/ -v

# Test memory management systems
python test_importance_scoring.py      # Smart importance scoring
python test_memory_pruning.py          # Pruning system validation
python test_memory_decay.py           # Decay system testing
python test_importance_integration.py  # Integration testing

# API endpoint testing
python test_pruning_api.py            # MCP API validation
python test_memory_workflow.py        # End-to-end workflow
```

### Simulation & Performance Testing

```bash
# Activate virtual environment first
venv\Scripts\activate  # Windows
# source venv/bin/activate  # macOS/Linux

# Multi-persona chatroom simulation
python -m persona_mcp.simulation.chatroom

# Interactive API testing
python client/mcp_client.py --auto-test

# Memory system stress testing
python examples.py                     # Interactive examples

# Production server with simulation
python server.py --simulate 5 --debug
```

### Memory System Validation

- ✅ **Importance Scoring**: 0.51-0.80 contextual scores vs hardcoded 0.8
- ✅ **Pruning Safety**: Protects high-importance (0.8+) and accessed (8+) memories
- ✅ **Decay Graduation**: 16.4% → 66.7% aging based on access patterns
- ✅ **Auto-Integration**: Pruning triggers at 1000+ memories automatically
- ✅ **Background Processing**: 6-hour decay cycles with error handling

## 📈 Recent Updates & Development Status

### ✅ Completed (Production Ready)

- **Smart Importance Scoring**: Context-aware memory importance (0.51-0.80 range)
- **Memory Pruning System**: Intelligent cleanup with safety protections
- **Memory Decay System**: Automated aging with 4 decay modes
- **ChromaDB Integration**: Fixed and optimized vector memory storage
- **Database Models**: Aligned with SQLite implementation
- **Comprehensive Testing**: Full test coverage for memory systems
- **MCP API Extensions**: 11 new memory management endpoints

### 🔄 In Progress

- **ChromaDB Performance Optimization**: Remove ThreadPoolExecutor overhead, implement lazy loading

### 📋 Roadmap

- **Agent-to-Agent Communication**: Multi-persona collaboration system
- **Persona Interaction Management**: Advanced social dynamics and conversation flow
- **Distributed Architecture**: Scale beyond single-server deployment
- **Advanced Analytics**: Memory usage patterns and optimization insights

## 🏗️ Technical Architecture

### Memory Management Philosophy

The system implements a **3-tier memory management approach**:

1. **Intelligence Layer**: Context-aware importance scoring
2. **Maintenance Layer**: Automatic pruning and cleanup
3. **Aging Layer**: Background decay and optimization

This ensures memory collections remain high-quality and performant while preserving valuable context automatically.

### Production Deployment

```bash
# Activate virtual environment first
venv\Scripts\activate  # Windows
# source venv/bin/activate  # macOS/Linux

# Production startup
python server.py --host 0.0.0.0 --port 8000

# With memory system monitoring
python server.py --debug --memory-stats

# Background services only
python -m persona_mcp.memory.decay_system --daemon
```

## 📚 Documentation

- [`QUICKSTART.md`](QUICKSTART.md) - Quick setup and basic usage
- [`docs/ideas/`](docs/ideas/) - Advanced features and design specifications
- [`IMPORTANCE_SCORING_SUMMARY.md`](IMPORTANCE_SCORING_SUMMARY.md) - Memory scoring system details
- Test files - Comprehensive usage examples and validation

## License

MIT License - see LICENSE file for details.
