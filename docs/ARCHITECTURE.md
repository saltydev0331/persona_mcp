# Persona MCP Server - Architecture Documentation

Technical architecture and implementation details for the Persona MCP Server.

## System Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   MCP Client    │    │  WebSocket API  │    │ Ollama (Docker) │
│                 │◄───┤                 ├───►│                 │
│ • Test Client   │    │ • JSON-RPC 2.0  │    │ • llama3.1:8b   │
│ • Interactive   │    │ • Session Mgmt  │    │ • Local Models  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                       ┌─────────────────┐
                       │ Persona Engine  │
                       │                 │
                       │ • Aria (Bard)   │
                       │ • Kira (Scholar)│
                       │ • Conversation  │
                       │   Context       │
                       └─────────────────┘
                                │
                ┌───────────────┼───────────────┐
                │               │               │
      ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
      │    SQLite       │ │    ChromaDB     │ │   Session      │
      │                 │ │                 │ │   Memory       │
      │ • Personas      │ │ • Vector Store  │ │                │
      │ • Conversations │ │ • Embeddings    │ │ • Active Chats │
      │ • Relationships │ │ • Similarity    │ │ • Context      │
      └─────────────────┘ └─────────────────┘ └─────────────────┘
```

## Core Components

### 1. MCP Protocol Layer (`persona_mcp/mcp/`)

**Purpose**: Handles WebSocket connections and JSON-RPC 2.0 protocol

**Key Files**:

- `server.py` - Main WebSocket server and request routing
- `handlers.py` - MCP method implementations
- `protocol.py` - JSON-RPC message handling

**Features**:

- WebSocket connection management
- JSON-RPC 2.0 compliance
- Error handling and validation
- Session lifecycle management

### 2. Persona Management (`persona_mcp/models/`)

**Purpose**: Core persona data models and behavior

**Key Files**:

- `__init__.py` - All Pydantic models (Persona, Memory, ConversationTurn, etc.)
- Model definitions with validation and constraints

**Features**:

- Two hardcoded personas (Aria, Kira) with distinct personalities
- Persona state tracking (energy, availability, priorities)
- Interaction state management
- Validation with Pydantic models

### 3. Conversation Engine (`persona_mcp/conversation/`)

**Purpose**: Manages conversation flow and context

**Key Files**:

- `engine.py` - Main conversation coordination
- `context_manager.py` - Conversation context handling

**Features**:

- **Session-based conversations**: Each persona maintains separate conversation history
- **Smart context management**: Keeps 20 recent messages, summarizes older ones
- **Anti-bloat measures**: Automatic cleanup after 24 hours
- **Persistent memory**: Conversations survive persona switching

### 4. LLM Integration (`persona_mcp/llm/`)

**Purpose**: Interface with Ollama for text generation

**Key Files**:

- `ollama_provider.py` - Ollama API client and model management
- `manager.py` - LLM provider abstraction

**Features**:

- **Docker Ollama integration**: Connects to Ollama container on port 11434
- **Model verification**: Confirms specified model usage with logging
- **Fallback handling**: Graceful degradation when LLM unavailable
- **Persona-aware prompting**: Builds persona-specific prompts

### 5. Storage Layer (`persona_mcp/persistence/`)

**Purpose**: Data persistence and retrieval

**Key Files**:

- `sqlite_manager.py` - Structured data storage
- `vector_memory.py` - ChromaDB integration for semantic memory

**Features**:

- **SQLite database**: Personas, conversations, relationships
- **ChromaDB vectors**: Semantic memory search (partially implemented)
- **Local-only storage**: No cloud dependencies
- **Automatic schema management**: Database initialization and migrations

## Data Models

### Core Models

```python
class Persona(BaseModel):
    id: str
    name: str
    description: str
    personality_traits: List[str]
    backstory: str
    interaction_state: PersonaInteractionState

class PersonaInteractionState(BaseModel):
    social_energy: int
    available_time: int  # minutes
    interaction_fatigue: int
    current_priority: Priority
    last_interaction: Optional[datetime]

class ConversationTurn(BaseModel):
    conversation_id: str
    speaker_id: str
    turn_number: int
    content: str
    response_type: str
    continue_score: float
    tokens_used: int
    processing_time: float

class Memory(BaseModel):
    id: str
    persona_id: str
    content: str
    memory_type: str
    importance: float  # 0.0 to 1.0
    emotional_valence: float  # -1.0 to 1.0
    created_at: datetime
```

## Session Management Architecture

### Session Lifecycle

1. **Connection**: Client connects to WebSocket endpoint
2. **Session Creation**: Unique session ID generated
3. **Persona Selection**: Client switches to desired persona
4. **Conversation**: Messages exchanged with context retention
5. **Context Management**: Automatic cleanup and summarization
6. **Session Expiry**: 24-hour timeout with cleanup

### Context Management Strategy

```python
# Session state per connection
{
    "session_id": "uuid",
    "conversations": {
        "persona_id": {
            "messages": [recent_messages],  # Last 20 messages
            "context_summary": "summary_of_older_messages",
            "turn_count": 42,
            "last_activity": datetime
        }
    }
}
```

### Anti-Bloat Measures

- **Message Limit**: Maximum 20 active messages per persona
- **Summarization**: When > 50 messages, older ones get summarized
- **Session Timeout**: 24-hour inactivity timeout
- **Automatic Cleanup**: Background cleanup of expired sessions

## Configuration Management

### Current Implementation (Hardcoded)

```python
# Default settings
OLLAMA_HOST = "http://localhost:11434"
DEFAULT_MODEL = "llama3.1:8b"
MAX_CONTEXT_MESSAGES = 20
CONTEXT_SUMMARY_THRESHOLD = 50
SESSION_TIMEOUT_HOURS = 24
```

### Planned Configuration System

```python
# config.json
{
    "server": {
        "host": "localhost",
        "port": 8000,
        "debug": false
    },
    "ollama": {
        "host": "http://localhost:11434",
        "default_model": "llama3.1:8b",
        "timeout": 60
    },
    "session": {
        "max_context_messages": 20,
        "summary_threshold": 50,
        "timeout_hours": 24
    }
}
```

## Error Handling Strategy

### Graceful Degradation

- **Ollama Unavailable**: Falls back to hardcoded responses
- **Database Errors**: Logs error, continues with memory-only session
- **ChromaDB Issues**: Memory storage fails silently, conversation continues
- **Model Loading Failures**: Uses fallback responses with error logging

### Validation Layers

1. **Pydantic Models**: Type validation and constraints
2. **MCP Protocol**: JSON-RPC 2.0 compliance checking
3. **Business Logic**: Persona availability and state validation
4. **LLM Integration**: Model existence and response validation

## Performance Considerations

### Current Performance

- **Response Time**: 1-7 seconds (depends on model loading)
- **Memory Usage**: Minimal (local SQLite + in-memory sessions)
- **Concurrent Connections**: ~50 connections (single-threaded WebSocket handling)
- **Model Loading**: Cold start penalty for first request
- **Throughput**: Bottlenecked by LLM generation, not protocol layer

### Performance vs FastAPI Analysis

**WebSocket MCP Advantages:**

- Persistent connections eliminate HTTP handshake overhead
- Stateful session management keeps conversation context in memory
- Single process architecture reduces serialization overhead
- Efficient for real-time conversational interactions

**Current Limitations:**

- Single MCPHandlers instance creates contention
- Synchronous JSON parsing blocks event loop
- Simple dict-based connection management
- No connection pooling or resource limits

### High-Impact Optimization Opportunities

#### 1. **Connection & Handler Optimization**

- **Handler Pooling**: Pool MCPHandlers instances per connection (5-10x concurrency)
- **Connection Limits**: Semaphore-based connection limiting (prevent overload)
- **Resource Sharing**: Thread-safe shared DB/Memory/LLM managers

#### 2. **Async Processing Pipeline**

- **Background Workers**: Queue message processing in background (2-3x throughput)
- **Fast JSON**: Replace `json` with `orjson` for 2x parsing speed
- **Message Queuing**: Non-blocking request/response handling

#### 3. **Database Optimization**

- **Connection Pooling**: Multiple SQLite connections with WAL mode (3-5x DB performance)
- **Prepared Statements**: Cache frequently used queries
- **Batch Operations**: Group multiple DB operations

#### 4. **Memory & Broadcasting**

- **Efficient Broadcasting**: Serialize once, send to all connections
- **Rate Limiting**: Per-connection message rate limits
- **Memory Monitoring**: Track and limit resource usage

### Expected Performance Gains

With optimizations:

- **Concurrent Connections**: 50 → 500+ connections
- **JSON Processing**: 2-3x faster with orjson + background workers
- **Database Throughput**: 3-5x improvement with connection pooling
- **Memory Efficiency**: 50-80% reduction in per-connection overhead
- **Response Latency**: Near-elimination of blocking operations

### Implementation Priority

1. **Quick Wins** (1-2 days): orjson, connection limits, SQLite WAL
2. **Medium Impact** (3-5 days): Handler pooling, database connection pooling
3. **Advanced** (1-2 weeks): Background message processing, comprehensive monitoring

## Security Considerations

### Current Security

- **Local-only**: No external network access required
- **No Authentication**: Open WebSocket (development only)
- **Input Validation**: Pydantic model validation
- **Resource Limits**: Token budgets and message limits

### Production Security Needs

- **Authentication**: API keys or JWT tokens
- **Rate Limiting**: Per-client request limits
- **Input Sanitization**: Prevent prompt injection
- **HTTPS/WSS**: Encrypted connections
- **Resource Monitoring**: Prevent resource exhaustion

## Testing Architecture

### Current Test Suite

- `client/quick_test.py` - Automated MCP method testing
- `client/mcp_client.py` - Interactive testing interface
- Manual testing with conversation scenarios

### Planned Testing Expansion

- **Unit Tests**: Individual component testing
- **Integration Tests**: Full workflow testing
- **Performance Tests**: Load and stress testing
- **Regression Tests**: Automated CI/CD pipeline

## Deployment Considerations

### Current Deployment

- **Development Only**: Manual server.py execution
- **Local Dependencies**: SQLite, ChromaDB, Ollama Docker
- **No Containerization**: Direct Python execution

### Production Deployment Needs

- **Docker Containerization**: Full application container
- **Docker Compose**: Multi-service orchestration
- **Health Checks**: Monitoring and alerting
- **Scaling**: Multiple server instances
- **Load Balancing**: WebSocket-aware load balancing
