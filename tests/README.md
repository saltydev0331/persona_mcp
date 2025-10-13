# Test Suite for Persona MCP Server

This directory contains the test suite for the Persona MCP Server.

## Test Structure

- `test_models.py` - Unit tests for data models (Persona, ConversationContext, etc.)
- `test_conversation.py` - Integration tests for the conversation engine
- `test_mcp_protocol.py` - Tests for MCP JSON-RPC 2.0 protocol compliance
- `conftest.py` - Test configuration and fixtures

## Running Tests

Make sure you have the test dependencies installed:

```bash
pip install pytest pytest-asyncio
```

Run all tests:

```bash
python -m pytest tests/
```

Run specific test file:

```bash
python -m pytest tests/test_models.py -v
```

Run with coverage:

```bash
python -m pytest tests/ --cov=persona_mcp --cov-report=html
```

## Test Requirements

- Tests use async/await patterns extensively
- Temporary databases and memory stores are created for isolation
- Mock objects are used to test components in isolation
- Integration tests verify end-to-end functionality

## Test Data

Tests create their own temporary personas and data:

- **Aria** - Energetic bard who loves music and stories
- **Kira** - Focused scholar interested in research and magic

These personas have different topic preferences and interaction styles to test the conversation scoring system.

## Coverage Goals

- ✅ Data model validation and behavior
- ✅ Conversation engine scoring logic
- ✅ MCP protocol compliance
- ✅ Persona state management
- ✅ Relationship tracking
- ✅ Memory storage and retrieval
- ⏳ WebSocket server integration
- ⏳ Simulation harness validation
