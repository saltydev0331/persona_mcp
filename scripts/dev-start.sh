#!/bin/bash
# Development startup script for Persona-MCP dual-service architecture
# 
# Starts both MCP server and PersonaAPI server for testing

echo "🚀 Starting Persona-MCP Development Environment"
echo "================================================"
echo ""

# Function to cleanup background processes
cleanup() {
    echo ""
    echo "🛑 Shutting down services..."
    if [ ! -z "$MCP_PID" ]; then
        kill $MCP_PID 2>/dev/null
        echo "   ✓ MCP Server stopped"
    fi
    if [ ! -z "$PERSONAAPI_PID" ]; then
        kill $PERSONAAPI_PID 2>/dev/null
        echo "   ✓ PersonaAPI Server stopped"
    fi
    echo "   ✓ Cleanup complete"
    exit 0
}

# Set trap for cleanup
trap cleanup INT TERM

# Check if virtual environment is activated and get Python path
if [ ! -z "$VIRTUAL_ENV" ]; then
    echo "✓ Virtual environment detected: $VIRTUAL_ENV"
    PYTHON_PATH="$VIRTUAL_ENV/bin/python"
elif [ -f "venv/bin/python" ]; then
    echo "⚠️  Virtual environment not activated but found. Using venv Python..."
    PYTHON_PATH="venv/bin/python"
    export VIRTUAL_ENV="$(pwd)/venv"
elif [ -f "venv/Scripts/python.exe" ]; then
    echo "⚠️  Virtual environment not activated but found. Using venv Python..."
    PYTHON_PATH="venv/Scripts/python.exe"
    export VIRTUAL_ENV="$(pwd)/venv"
else
    echo "❌ No virtual environment found. Please activate your venv first:"
    echo "   source venv/bin/activate  # Linux/Mac"
    echo "   venv\\Scripts\\activate     # Windows"
    exit 1
fi

echo "Using Python: $PYTHON_PATH"

# Start MCP Intelligence Server
echo "🧠 Starting MCP Intelligence Server (port 8000)..."
$PYTHON_PATH -m persona_mcp.mcp.server &
MCP_PID=$!

# Wait for MCP server to initialize
echo "   ⏳ Waiting for MCP server to initialize..."
sleep 3

# Check if MCP server started successfully
if ! kill -0 $MCP_PID 2>/dev/null; then
    echo "   ❌ MCP server failed to start"
    exit 1
fi
echo "   ✓ MCP server started (PID: $MCP_PID)"

# Start PersonaAPI Server
echo "🌐 Starting PersonaAPI Server (port 8080)..."
$PYTHON_PATH -m persona_mcp.dashboard.server &
PERSONAAPI_PID=$!

# Wait for PersonaAPI server to initialize
echo "   ⏳ Waiting for PersonaAPI server to initialize..."
sleep 3

# Check if PersonaAPI server started successfully
if ! kill -0 $PERSONAAPI_PID 2>/dev/null; then
    echo "   ❌ PersonaAPI server failed to start"
    cleanup
    exit 1
fi
echo "   ✓ PersonaAPI server started (PID: $PERSONAAPI_PID)"

echo ""
echo "🎉 Persona-MCP Development Environment Ready!"
echo "=============================================="
echo ""
echo "Services:"
echo "  🧠 MCP Intelligence Server:  ws://localhost:8000/mcp"
echo "  🌐 PersonaAPI Server:        http://localhost:8080"
echo "  📚 API Documentation:        http://localhost:8080/docs"
echo ""
echo "Quick Tests:"
echo "  • Test MCP:        python -c \"import asyncio; import websockets; import json; async def test(): ws = await websockets.connect('ws://localhost:8000/mcp'); await ws.send(json.dumps({'jsonrpc':'2.0','method':'persona.list','id':'1'})); print(await ws.recv()); asyncio.run(test())\""
echo "  • Test PersonaAPI: curl http://localhost:8080/api/personas"
echo "  • Health Check:    curl http://localhost:8080/api/health"
echo ""
echo "Architecture:"
echo "  ┌─────────────────┐    ┌─────────────────┐"
echo "  │  PersonaAPI     │    │   MCP Server    │"
echo "  │   (port 8080)   │◄──►│  (port 8000)    │"
echo "  │                 │    │                 │"
echo "  │ • HTTP/REST API │    │ • WebSocket     │"
echo "  │ • Bot Management│    │ • Intelligence  │"
echo "  │ • Admin UI      │    │ • Pure MCP      │"
echo "  └─────────────────┘    └─────────────────┘"
echo "           │                        │"
echo "           └────────┬───────────────┘"
echo "                    │"
echo "           ┌────────▼────────┐"
echo "           │  Shared Core    │"
echo "           │  Foundation     │"
echo "           │                 │"
echo "           │ • DatabaseMgr   │"
echo "           │ • MemoryMgr     │"
echo "           │ • ConfigMgr     │"
echo "           └─────────────────┘"
echo ""
echo "Press Ctrl+C to stop all services"
echo ""

# Wait for interrupt
wait