# Persona MCP Server - Roadmap

This document captures the planned features and implementation roadmap for the Persona MCP Server.

## Current Status (v0.2.0)

### ✅ Implemented Features

- **Core MCP Protocol**: JSON-RPC 2.0 over WebSocket
- **Persona Management**: Two working personas (Aria - bard, Kira - scholar)
- **Persistent Conversations**: Session-based context retention across persona switches
- **Local Storage**: SQLite for structured data, ChromaDB for vector memory
- **LLM Integration**: Ollama with configurable models (currently llama3.1:8b)
- **Test Clients**: Interactive and automated testing tools
- **Session Management**: Smart context windows, auto-cleanup, anti-bloat measures
- **🧠 Intelligent Memory Management**: Production-ready 3-tier system
  - **Smart Importance Scoring**: Context-aware scoring (0.51-0.80) replacing hardcoded values
  - **Memory Pruning System**: Intelligent cleanup with safety protections
  - **Memory Decay System**: Background aging with graduated decay (16.4%-66.7%)
  - **Self-Managing**: Maintains memory quality and performance automatically

### ✅ Working MCP Methods (25+ endpoints)

**Persona Operations:**

- `persona.list` - List available personas with status
- `persona.switch` - Switch active persona (supports ID or name)
- `persona.chat` - Chat with current persona (with conversation history)
- `persona.status` - Get current persona state
- `persona.create` - Create new personas dynamically

**Memory Management:**

- `memory.search` - Semantic vector search across memories
- `memory.store` - Manual memory storage with importance scoring
- `memory.stats` - Memory collection statistics and health
- `memory.prune` - Intelligent memory cleanup (single persona)
- `memory.prune_all` - Global memory optimization
- `memory.prune_recommendations` - Preview pruning suggestions
- `memory.prune_stats` - Pruning system performance metrics

**Memory Decay System:**

- `memory.decay_start` - Begin background memory aging
- `memory.decay_stop` - Halt decay processing
- `memory.decay_stats` - Decay system status and metrics
- `memory.decay_force` - Force decay with custom parameters

**Conversation Management:**

- `conversation.start` - Initialize new conversation context
- `conversation.end` - Finalize and store conversation
- `conversation.status` - Get active conversation state

**System Operations:**

- `system.status` - Server health and performance metrics
- `system.models` - Available Ollama models
- `state.save` - Persist complete system state
- `state.load` - Restore previous system state

## Planned Features (Future Versions)

### ✅ Phase 2: Enhanced Memory System - **COMPLETED**

- ✅ **Advanced Memory Search**: Semantic search with ChromaDB vector storage
- ✅ **Memory Importance Scoring**: 6-factor contextual scoring (0.51-0.80 range)
- ✅ **Memory Pruning**: Intelligent cleanup with safety protections
- ✅ **Memory Decay**: Background aging with 4 decay modes
- ✅ **Auto-Management**: Self-managing ecosystem with background processing
- ✅ **Cross-Persona Memory**: Shared memories between personas when appropriate
- 🔄 **Performance Optimization**: ChromaDB async optimization (in progress)

### 🚧 Phase 3: Relationship Dynamics

- **Social Compatibility**: Persona-to-persona relationship modeling
- **Interaction History**: Track relationship changes over time
- **Group Conversations**: Multi-persona conversations with relationship awareness
- **Emotional State Tracking**: Mood and emotional context persistence

### ✅ Phase 4: Real-time Communication - **v0.2.2**

- ✅ **LLM Response Streaming**: Real-time response delivery over WebSocket
- ✅ **Progressive Response Updates**: Chunk-based streaming with JSON-RPC 2.0
- ✅ **Enhanced User Experience**: Sub-second time-to-first-token
- ✅ **Response Control**: Cancellation and early termination support

### 🚧 Phase 5: Advanced Conversation Management

- **Continue Score System**: Intelligent conversation flow prediction
- **Topic Threading**: Conversation branch management
- **Context Switching**: Smart context preservation across topic changes
- **Conversation Analytics**: Detailed interaction statistics

### 🚧 Phase 6: State Management

- **Full State Persistence**: Save/restore complete server state
- **State Export/Import**: Backup and migration capabilities
- **Configuration Management**: Runtime configuration updates
- **Session Recovery**: Restore sessions after server restart

### 🚧 Phase 7: Visual and UI Enhancements

- **Visual Context Updates**: Support for visual scene descriptions
- **Rich Media Support**: Handle images, audio in conversations
- **Persona Visualization**: Avatar and visual representation system
- **Real-time Updates**: Live conversation state broadcasting

### 🚧 Phase 8: Simulation and Testing

- **Chatroom Simulation**: Multi-persona conversation testing
- **Scenario Testing**: Predefined interaction scenarios
- **Performance Testing**: Load and stress testing tools
- **Automated Regression**: Continuous testing pipeline

### 🚧 Phase 9: Advanced LLM Features

- **Multi-Model Support**: Different models per persona
- **Model Selection Logic**: Automatic model selection based on context
- **Fine-tuning Integration**: Support for persona-specific fine-tuned models
- **Prompt Engineering**: Advanced prompt templates and optimization

## Immediate Next Steps (v0.2.3 - Refactor & Cleanup)

### 🚨 **Critical Refactors (High Priority - 3-4 days)**

#### 1. **Configuration Centralization**

- [ ] Create `ConfigManager` class with environment variable loading
- [ ] Move all hardcoded values to `.env` configuration (50+ magic numbers found)
- [ ] Extract constants: `tick_interval=30`, `MAX_CONTEXT_MESSAGES=20`, `charisma=18`, etc.
- [ ] Add runtime configuration validation and type checking
- [ ] Update all imports to use centralized config

#### 2. **Logging Standardization**

- [ ] Standardize on structured logging with consistent logger instances
- [ ] Fix mixed patterns: `logging.getLogger(__name__)` vs `logging.info()` direct calls
- [ ] Add request/response correlation IDs for debugging
- [ ] Clean up debug code in production files ("The Debug Tavern", test flags)

#### 3. **Streaming Handler Architecture**

- [ ] Fix hacky state sharing between regular and streaming handlers
- [ ] Implement proper dependency injection instead of `._regular_handlers = self.mcp_handlers`
- [ ] Create shared state manager for persona context
- [ ] Standardize async/sync patterns throughout codebase

### ⚠️ **Code Quality Improvements (Medium Priority - 2-3 days)**

#### 4. **Magic Numbers & Constants**

- [ ] Extract 50+ hardcoded values to named constants
- [ ] Create `constants.py` for scoring thresholds, timeouts, limits
- [ ] Move persona defaults, importance weights, decay rates to config
- [ ] Document reasoning for specific values

#### 5. **Exception Handling & Imports**

- [ ] Standardize exception handling patterns (bare except vs specific)
- [ ] Organize imports consistently (isort + black formatting)
- [ ] Fix relative vs absolute import mixing
- [ ] Add missing type hints for better IDE support

#### 6. **File Organization**

- [ ] Move test files from root to `/tests/integration/` and `/tests/unit/`
- [ ] Create abstract base classes for LLMProvider, MemoryManager interfaces
- [ ] Break large configuration classes into logical sub-configs

### 💡 **Quick Wins (< 1 day)**

- [ ] Add `.editorconfig` for consistent formatting
- [ ] Create `constants.py` for immediate magic number extraction
- [ ] Standardize all `logging.getLogger(__name__)` calls
- [ ] Clean up unused imports and debug strings
- [ ] Move test files to proper `/tests/` directory structure

## Technical Debt and Improvements

### 🔧 Code Quality (Post-Refactor)

- [ ] Comprehensive error handling and logging (standardized)
- [ ] Type safety improvements (enhanced)
- [ ] Performance optimization (streaming complete)
- [ ] Memory usage optimization (optimized)
- [ ] Connection pooling and resource management (improved)

### 🚀 WebSocket Performance Optimization

#### Quick Wins (1-2 days)

- [ ] Replace `json` with `orjson` for 2x JSON processing speed
- [ ] Add connection limits with asyncio.Semaphore
- [ ] Enable SQLite WAL mode for better concurrent access
- [ ] Implement basic rate limiting per connection

#### Medium Impact (3-5 days)

- [ ] Handler pooling system for MCPHandlers instances
- [ ] Database connection pooling with aiosqlite
- [ ] Optimized message broadcasting (serialize once, send to all)
- [ ] Resource monitoring and memory limits

#### Advanced Optimization (1-2 weeks)

- [ ] Background message processing workers
- [ ] Message queuing system with asyncio.Queue
- [ ] Comprehensive performance monitoring
- [ ] Load testing and benchmarking suite
- [ ] Production-grade resource management

### 🔧 Testing and Documentation

- [ ] Unit test coverage (currently minimal)
- [ ] Integration test suite
- [ ] API documentation generation
- [ ] Performance benchmarks
- [ ] Deployment guides

### 🔧 Production Readiness

- [ ] Configuration file support (.env, config.json)
- [ ] Health check endpoints
- [ ] Metrics and monitoring
- [ ] Docker containerization
- [ ] Scaling considerations

## Version Planning

### v0.2.0 - Enhanced Memory System - **COMPLETED** (October 2025)

- ✅ Full memory search implementation with ChromaDB
- ✅ Smart importance scoring with 6-factor analysis
- ✅ Memory pruning system with safety protections
- ✅ Memory decay system with background processing
- ✅ 25+ MCP endpoints for memory management
- ✅ Comprehensive test suite and validation

### v0.2.1 - ChromaDB Performance Optimization - **COMPLETED** (October 2025)

- ✅ Remove ThreadPoolExecutor overhead from ChromaDB operations (54.9% improvement)
- ✅ Implement lazy collection loading for better startup performance
- ✅ Optimize ChromaDB settings for async performance (LRU caching)
- ✅ Connection pooling and resource optimization (sub-ms checkout)
- ✅ orjson integration for fast JSON processing (76.8% improvement)
- ✅ SQLite WAL mode and database optimization (20ms init)

### v0.2.2 - LLM Response Streaming & UX Enhancement - **COMPLETED** (October 2025)

- ✅ **Real-time Response Streaming**: Live LLM response streaming over WebSocket
  - ✅ Ollama streaming API integration (`stream: true`) with AsyncGenerator
  - ✅ Progressive response chunks with JSON-RPC 2.0 compatibility (60+ chunks/response)
  - ✅ WebSocket streaming handlers with event types (start/chunk/complete/error)
  - ✅ Memory integration with streaming responses for conversation storage
- ✅ **Enhanced User Experience**: Sub-second time-to-first-token delivery
  - ✅ Time-to-first-token optimization (~50-100ms vs 3-7s)
  - ✅ Real-time chunk delivery (~17ms per chunk average)
  - ✅ Streaming-aware conversation management and memory integration
  - ✅ Production-ready streaming infrastructure (+967 lines)

### v0.2.3 - Refactor & Cleanup (Target: January 2026)

- Configuration centralization with ConfigManager
- Logging standardization across codebase
- Streaming handler architecture improvements
- Magic number extraction and constants management
- File organization and code quality improvements

### v0.3.0 - Advanced Features & Client Support (Target: Q1 2026)

- Client-side streaming support and UI integration
- Advanced streaming controls (pause/resume/cancel)
- Handler pooling system for MCPHandlers instances
- Database connection pooling with aiosqlite
- Background message processing workers
- Production-grade resource management

### v0.3.1 - Relationship Dynamics (Target: Q1 2026)

- Persona relationship modeling
- Group conversation support
- Emotional state tracking
- Social compatibility algorithms

### v0.4.0 - Advanced Conversation & State Management (Target: Q2 2026)

- Continue score system
- State management and persistence
- Topic threading and context switching
- Conversation analytics

### v0.5.0 - Visual & Multi-modal Features (Target: Q3 2026)

- Visual context support
- Rich media integration
- Persona visualization system
- Multi-model LLM support

### v1.0.0 - Production Ready (Target: Q4 2026)

- All core features complete
- Production deployment ready (500+ concurrent connections)
- Comprehensive documentation
- Full test coverage
- Performance benchmarks and optimization complete

## Contributing

When implementing new features:

1. Update this roadmap with progress
2. Maintain backward compatibility where possible
3. Add comprehensive tests for new functionality
4. Update API documentation
5. Consider performance implications

## Research Areas

- Advanced conversation flow algorithms
- Persona personality consistency models
- Efficient vector memory retrieval
- Real-time conversation state synchronization
- Multi-modal conversation support
