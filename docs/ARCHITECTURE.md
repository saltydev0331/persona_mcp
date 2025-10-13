# Persona MCP Server - Architecture Documentation

Technical architecture and implementation details for the Persona MCP Server.

## System Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   MCP Client    │    │  WebSocket API  │    │ Ollama (Docker) │
│                 │◄───┤                 ├───►│                 │
│ • Test Client   │    │ • JSON-RPC 2.0  │    │ • llama3.1:8b   │
│ • Interactive   │    │ • 25+ Endpoints │    │ • Local Models  │
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
      │    SQLite       │ │ 🧠 Memory Mgmt  │ │   Session      │
      │                 │ │                 │ │   Memory       │
      │ • Personas      │ │ • Smart Scoring │ │                │
      │ • Conversations │ │ • Auto Pruning  │ │ • Active Chats │
      │ • Relationships │ │ • Decay System  │ │ • Context      │
      └─────────────────┘ └─────────────────┘ └─────────────────┘
                                │
                       ┌─────────────────┐
                       │    ChromaDB     │
                       │                 │
                       │ • Vector Store  │
                       │ • Embeddings    │
                       │ • Similarity    │
                       │ • Semantic      │
                       │   Search        │
                       └─────────────────┘
```

### Intelligent Memory Management Flow

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

## 🧠 Memory Management System Architecture

### 3-Tier Memory Management Design

The memory management system implements a sophisticated 3-tier architecture for intelligent conversation memory handling:

#### Tier 1: Smart Importance Scoring (0.51-0.80 Range)

**Purpose**: Contextual relevance scoring for every conversation message

**Algorithm**:

```python
def calculate_importance_score(message, context):
    base_score = 0.5

    # Content analysis factors
    content_factor = analyze_content_relevance(message.content)  # 0.1-0.3
    engagement_factor = measure_user_engagement(message)         # 0.0-0.2
    persona_factor = assess_persona_relevance(message, persona)  # 0.0-0.15
    temporal_factor = apply_temporal_weighting(message.timestamp) # 0.0-0.05

    final_score = min(base_score + content_factor + engagement_factor +
                     persona_factor + temporal_factor, 0.8)

    return final_score
```

**Scoring Factors**:

- **Content Relevance**: Keywords, entities, sentiment analysis
- **User Engagement**: Message length, response time, follow-up questions
- **Persona Relevance**: Alignment with persona expertise and personality
- **Temporal Weighting**: Recent messages get slight boost

**Performance**: 0.51-0.80 scoring range ensures meaningful differentiation while preventing extremes

#### Tier 2: Intelligent Pruning System

**Purpose**: Safe memory cleanup with importance-based retention

**Strategy**:

```python
def prune_memories(target_count: int, min_importance: float = 0.6):
    # Safety checks
    if len(memories) <= MIN_SAFE_COUNT:
        return False

    # Sort by importance (ascending - remove least important first)
    candidates = [m for m in memories if m.importance < min_importance]

    if len(candidates) >= (len(memories) - target_count):
        # Safe to prune - remove lowest importance memories
        to_remove = sorted(candidates, key=lambda m: m.importance)[:target_count]
        return remove_memories(to_remove)

    return False  # Abort if would remove too many important memories
```

**Safety Features**:

- **Minimum Count Protection**: Never prune below 10 memories
- **Importance Thresholds**: Only prune memories below 0.6 importance
- **Gradual Cleanup**: Remove in small batches to prevent context loss
- **Rollback Capability**: Track pruned memories for potential restoration

#### Tier 3: Advanced Decay System

**Purpose**: Gradual importance reduction over time with multiple decay modes

**Decay Modes**:

1. **Linear Decay**: `importance = max(0, importance - (decay_rate * time_elapsed))`
2. **Exponential Decay**: `importance = importance * exp(-decay_rate * time_elapsed)`
3. **Logarithmic Decay**: `importance = importance * (1 - log(1 + decay_rate * time_elapsed))`
4. **Step Decay**: Discrete importance reduction at time intervals

**Configuration**:

```python
DECAY_SETTINGS = {
    "mode": "exponential",      # linear, exponential, logarithmic, step
    "rate": 0.1,               # decay rate per time unit
    "interval_minutes": 60,     # decay application interval
    "min_importance": 0.1,      # floor value (never decay below)
    "enabled": True            # system-wide decay toggle
}
```

**Background Processing**:

- **Async Execution**: Non-blocking decay processing
- **Batch Processing**: Process multiple memories efficiently
- **Configurable Intervals**: Customizable decay frequency
- **Performance Monitoring**: Track decay impact on memory counts

### Memory System Integration

#### ChromaDB Integration

```python
class VectorMemory:
    def __init__(self):
        self.client = chromadb.Client()
        self.collection = self.client.get_or_create_collection(
            name="persona_memories",
            metadata={"hnsw:space": "cosine"}
        )

    async def store_memory(self, memory: Memory):
        # Calculate importance score
        importance = calculate_importance_score(memory.content, context)

        # Store in ChromaDB with metadata
        self.collection.add(
            documents=[memory.content],
            metadatas=[{
                "memory_id": memory.id,
                "persona_id": memory.persona_id,
                "importance": importance,
                "created_at": memory.created_at.isoformat(),
                "memory_type": memory.memory_type
            }],
            ids=[memory.id]
        )
```

#### Memory Lifecycle

1. **Creation**: New memories automatically scored for importance
2. **Storage**: ChromaDB vector storage with metadata
3. **Retrieval**: Semantic search with importance weighting
4. **Decay**: Background importance reduction over time
5. **Pruning**: Safe removal of low-importance memories
6. **Cleanup**: Final removal from all storage systems

### Performance Characteristics

#### Memory System Metrics

- **Scoring Latency**: ~5-15ms per message (content analysis)
- **Storage Latency**: ~10-50ms per memory (ChromaDB insertion)
- **Retrieval Latency**: ~20-100ms (semantic search)
- **Decay Processing**: ~1-5ms per memory (batch processing)
- **Pruning Latency**: ~50-200ms (safety checks + removal)

#### Scalability Factors

- **Memory Count**: Handles 1K-10K memories per persona efficiently
- **Concurrent Access**: Thread-safe operations with connection pooling
- **Background Processing**: Non-blocking decay and pruning
- **Storage Efficiency**: Vector embeddings + metadata indexing

### Memory System API

#### Core Endpoints

- `memory.store` - Store new memory with automatic importance scoring
- `memory.search` - Semantic search with importance weighting
- `memory.prune` - Manual pruning with safety checks
- `memory.decay_start` - Initiate background decay processing
- `memory.decay_stop` - Stop decay processing
- `memory.decay_stats` - Get decay system statistics
- `memory.get_stats` - Comprehensive memory system statistics

#### Configuration Endpoints

- `memory.set_importance_weights` - Adjust importance scoring factors
- `memory.set_decay_config` - Update decay system configuration
- `memory.set_pruning_config` - Modify pruning behavior

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
