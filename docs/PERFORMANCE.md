# Performance Optimization Guide

## Current Performance Baseline

### Measured Performance (October 2025)

- **Response Time**: 1-7 seconds (dominated by LLM generation)
- **Concurrent Connections**: ~50 connections (aiohttp WebSocket limitation)
- **Memory Usage**: Minimal (~50MB base + conversation state)
- **Throughput**: Limited by single-threaded request processing
- **JSON Processing**: Standard library `json` module
- **Database**: Single SQLite connection, default journal mode

### Protocol Comparison Analysis

**WebSocket MCP vs FastAPI HTTP**:

- ✅ **WebSocket Advantages**: Persistent connections, stateful sessions, real-time bidirectionality
- ✅ **Better for**: Conversational AI, real-time interactions, reduced connection overhead
- ❌ **FastAPI Advantages**: Better horizontal scaling, mature ecosystem, production features
- **Conclusion**: WebSocket MCP is optimal for persona interaction use case

## Performance Bottlenecks Identified

### 1. **Handler Contention**

- **Issue**: All connections share single MCPHandlers instance
- **Impact**: Sequential request processing, resource contention
- **Solution**: Handler pooling per connection

### 2. **Synchronous JSON Processing**

- **Issue**: `json.loads()` blocks event loop
- **Impact**: Request latency spikes under load
- **Solution**: Fast JSON library + background processing

### 3. **Database Limitations**

- **Issue**: Single SQLite connection, default journal mode
- **Impact**: Database operations become bottleneck
- **Solution**: Connection pooling + WAL mode

### 4. **Connection Management**

- **Issue**: Simple dict-based connection tracking
- **Impact**: Limited concurrent connection handling
- **Solution**: Semaphore-based limits + optimized data structures

## Optimization Implementation Plan

### Phase 1: Quick Wins (1-2 days implementation)

#### 1.1 Fast JSON Processing

```bash
pip install orjson
```

**Expected Gain**: 2-3x JSON parsing performance

**Implementation**:

```python
import orjson

# Replace json.loads() with orjson.loads()
# Replace json.dumps() with orjson.dumps()
```

#### 1.2 Connection Limits

**Expected Gain**: Prevents server overload, graceful degradation

**Implementation**:

```python
self.connection_semaphore = asyncio.Semaphore(100)

async def websocket_handler(self, request):
    async with self.connection_semaphore:
        # Handle connection
```

#### 1.3 SQLite WAL Mode

**Expected Gain**: 3-5x better concurrent database access

**Implementation**:

```python
await conn.execute("PRAGMA journal_mode=WAL")
await conn.execute("PRAGMA synchronous=NORMAL")
await conn.execute("PRAGMA cache_size=10000")
```

### Phase 2: Medium Impact (3-5 days implementation)

#### 2.1 Handler Pooling

**Expected Gain**: 5-10x concurrent request handling

**Architecture**:

```python
class HandlerPool:
    def __init__(self, pool_size=50):
        self.pool = asyncio.Queue(maxsize=pool_size)
        # Pre-populate with handlers

    async def get_handler(self) -> MCPHandlers:
        return await self.pool.get()

    def return_handler(self, handler: MCPHandlers):
        handler.reset_session()  # Clear connection-specific state
        self.pool.put_nowait(handler)
```

#### 2.2 Database Connection Pooling

**Expected Gain**: 3-5x database throughput

**Architecture**:

```python
class SQLitePool:
    def __init__(self, db_path: str, pool_size: int = 10):
        self.pool = asyncio.Queue(maxsize=pool_size)

    async def get_connection(self):
        return await self.pool.get()

    def return_connection(self, conn):
        self.pool.put_nowait(conn)
```

#### 2.3 Optimized Broadcasting

**Expected Gain**: 50-80% reduction in broadcast latency

**Implementation**:

```python
async def optimized_broadcast(self, message: Dict[str, Any]):
    # Serialize once
    message_bytes = orjson.dumps(message)

    # Send concurrently to all connections
    tasks = [
        self._safe_send(conn_id, ws, message_bytes)
        for conn_id, ws in self.connections.items()
    ]
    await asyncio.gather(*tasks, return_exceptions=True)
```

### Phase 3: Advanced Optimization (1-2 weeks implementation)

#### 3.1 Background Message Processing

**Expected Gain**: Near-elimination of blocking operations

**Architecture**:

```python
class MessageProcessor:
    def __init__(self, num_workers=4):
        self.message_queue = asyncio.Queue(maxsize=1000)
        self.workers = []

    async def start_workers(self):
        for _ in range(self.num_workers):
            worker = asyncio.create_task(self._message_worker())
            self.workers.append(worker)

    async def _message_worker(self):
        while True:
            connection_id, raw_message, handler = await self.message_queue.get()
            # Process in background thread if needed
            response = await handler.handle_request(orjson.loads(raw_message))
            # Send response via connection-specific queue
```

#### 3.2 Resource Monitoring

**Expected Gain**: Proactive resource management, better stability

**Features**:

- Memory usage tracking per connection
- Request rate monitoring and limiting
- Connection health checks
- Automatic cleanup of dead connections

#### 3.3 Performance Metrics

**Implementation**:

```python
class PerformanceMonitor:
    def __init__(self):
        self.metrics = {
            'connections_active': 0,
            'requests_per_second': 0,
            'avg_response_time': 0,
            'memory_usage': 0,
            'db_pool_utilization': 0
        }

    async def collect_metrics(self):
        # Collect and expose metrics
        pass
```

## Expected Performance Results

### After Phase 1 (Quick Wins)

- **Concurrent Connections**: 50 → 100+
- **JSON Processing**: 2-3x faster
- **Database Performance**: 3x improvement
- **Implementation Time**: 1-2 days

### After Phase 2 (Medium Impact)

- **Concurrent Connections**: 100 → 300+
- **Request Throughput**: 5-10x improvement
- **Memory Efficiency**: 50-80% better per connection
- **Implementation Time**: +3-5 days

### After Phase 3 (Advanced)

- **Concurrent Connections**: 300 → 500+
- **Response Latency**: Near-zero blocking operations
- **Production Readiness**: Full monitoring and resource management
- **Implementation Time**: +1-2 weeks

## Monitoring and Testing

### Performance Testing Tools

#### Load Testing Script

```python
import asyncio
import websockets
import time

async def connection_test(uri, num_connections=100):
    connections = []
    start_time = time.time()

    for i in range(num_connections):
        ws = await websockets.connect(uri)
        connections.append(ws)

    # Send concurrent messages
    tasks = []
    for ws in connections:
        task = asyncio.create_task(send_test_message(ws))
        tasks.append(task)

    await asyncio.gather(*tasks)

    # Cleanup
    for ws in connections:
        await ws.close()
```

#### Metrics Collection

- Response time percentiles (p50, p95, p99)
- Memory usage trends
- Connection success rates
- Database query performance
- Error rates and types

### Benchmarking Methodology

1. **Baseline Measurement**: Current implementation performance
2. **Incremental Testing**: Test each optimization phase
3. **Load Testing**: Gradual connection increase (10, 50, 100, 500+)
4. **Stress Testing**: Resource exhaustion scenarios
5. **Regression Testing**: Ensure optimizations don't break functionality

## Production Deployment Considerations

### Recommended Configuration

```python
# High-performance production settings
WEBSOCKET_MAX_CONNECTIONS = 500
HANDLER_POOL_SIZE = 100
DB_CONNECTION_POOL_SIZE = 20
MESSAGE_QUEUE_SIZE = 2000
BACKGROUND_WORKERS = 8
RATE_LIMIT_PER_CONNECTION = 100  # messages per minute
MEMORY_LIMIT_MB = 2000
```

### Monitoring Dashboard Metrics

- Active connections count
- Requests per second
- Average/P95 response times
- Memory usage and growth rate
- Database connection pool utilization
- Error rates by type
- LLM generation time distribution

### Scaling Beyond Single Machine

When single-machine optimization limits are reached:

- **Load Balancer**: Distribute connections across multiple instances
- **Shared State**: Redis for session storage
- **Database**: PostgreSQL with connection pooling
- **Message Queue**: RabbitMQ or Apache Kafka for inter-service communication

## Implementation Checklist

### Phase 1: Quick Wins ✅

- [ ] Install and integrate orjson
- [ ] Add connection semaphore limits
- [ ] Enable SQLite WAL mode and optimization pragmas
- [ ] Implement basic rate limiting per connection
- [ ] Add connection count monitoring

### Phase 2: Medium Impact 🔄

- [ ] Design and implement handler pooling system
- [ ] Create database connection pool
- [ ] Optimize message broadcasting
- [ ] Add memory usage monitoring
- [ ] Implement graceful connection cleanup

### Phase 3: Advanced 🚧

- [ ] Background message processing workers
- [ ] Comprehensive performance metrics
- [ ] Resource monitoring and alerting
- [ ] Load testing suite
- [ ] Production deployment configuration

---

**Last Updated**: October 13, 2025
**Next Review**: After Phase 1 implementation completion
