"""
Integration tests for Persona MCP Server

These tests require a running MCP server and test complete workflows
including WebSocket communication, memory persistence, and system integration.

To run integration tests:
    pytest tests/integration/ -m integration -v

To run specific integration test modules:
    pytest tests/integration/test_streaming_chat_integration.py -v
    pytest tests/integration/test_memory_workflow_integration.py -v
"""

# Mark this directory as a Python package