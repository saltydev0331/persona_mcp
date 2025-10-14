# Integration Tests

This directory contains integration tests for the Persona MCP Server that test complete workflows and system interactions.

## Test Categories

### Core Integration Tests

- **`test_streaming_chat_integration.py`** - WebSocket streaming chat functionality
- **`test_memory_workflow_integration.py`** - Memory storage, retrieval, and persistence
- **`test_config_integration.py`** - Configuration system validation
- **`test_importance_scoring_integration.py`** - Memory importance scoring system

## Running Integration Tests

### Prerequisites

1. **Start the MCP Server** (required for WebSocket tests):

   ```bash
   cd persona-mcp
   python -m persona_mcp.mcp.server
   ```

2. **Ensure Dependencies are Available**:
   - Ollama running with available model
   - ChromaDB accessible
   - SQLite database initialized

### Running Tests

**All Integration Tests:**

```bash
pytest tests/integration/ -m integration -v
```

**Specific Test Categories:**

```bash
# Configuration tests (no server required)
pytest tests/integration/test_config_integration.py -v

# Memory importance tests (no server required)
pytest tests/integration/test_importance_scoring_integration.py -v

# WebSocket functionality (requires running server)
pytest tests/integration/test_streaming_chat_integration.py -v

# Memory workflow (requires running server)
pytest tests/integration/test_memory_workflow_integration.py -v
```

**Run with Coverage:**

```bash
pytest tests/integration/ -m integration --cov=persona_mcp --cov-report=html
```

## Test Markers

Integration tests use pytest markers for organization:

- `@pytest.mark.integration` - All integration tests
- `@pytest.mark.slow` - Tests that take significant time
- `@pytest.mark.streaming` - WebSocket streaming tests
- `@pytest.mark.memory` - Memory system tests
- `@pytest.mark.config` - Configuration tests

## Test Structure

### Helper Classes

Each test module includes helper classes for common operations:

- **`StreamingChatTester`** - WebSocket connection and streaming operations
- **`MemoryWorkflowTester`** - Memory workflow operations and validation

### Test Patterns

```python
@pytest.mark.asyncio
@pytest.mark.integration
async def test_something():
    async with SomeTestHelper() as helper:
        # Test implementation
        result = await helper.do_something()
        assert result == expected
```

## Expected Behavior

### Streaming Chat Tests

- Verify WebSocket connection establishment
- Test persona listing and switching
- Validate streaming event sequence (start → chunks → complete)
- Check response quality and token usage
- Test conversation context preservation

### Memory Workflow Tests

- Test memory creation through conversations
- Verify memory search functionality
- Check memory persistence across sessions
- Validate importance scoring accuracy
- Test memory statistics and management

### Configuration Tests

- Validate all configuration sections
- Test environment variable overrides
- Check configuration validation
- Verify default value handling

## Troubleshooting

### Common Issues

**Connection Refused:**

- Ensure MCP server is running on localhost:8000
- Check server logs for startup errors

**Import Errors:**

- Verify PYTHONPATH includes project root
- Ensure all dependencies are installed

**Test Timeouts:**

- Increase timeout values for slower systems
- Check Ollama model availability and response time

**Memory Test Failures:**

- Clear ChromaDB data between test runs
- Verify database permissions

### Debug Mode

Run tests with debug output:

```bash
pytest tests/integration/ -v -s --log-cli-level=DEBUG
```

## Development

### Adding New Integration Tests

1. Create test file in `tests/integration/`
2. Use appropriate markers (`@pytest.mark.integration`)
3. Include helper classes for common operations
4. Add documentation for new test scenarios
5. Update this README with new test information

### Test Data Management

- Use temporary directories for test databases
- Clean up resources in test teardown
- Use fixtures for reusable test data
- Mock external dependencies when appropriate

## Performance Considerations

Integration tests are slower than unit tests because they:

- Require real WebSocket connections
- Perform actual database operations
- Execute full LLM inference
- Test complete system workflows

Run integration tests separately from unit tests in CI/CD pipelines.
