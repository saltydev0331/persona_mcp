#!/usr/bin/env python3
"""
Persona MCP Server - Main Entry Point

A local-first MCP server for AI persona interactions.
Runs entirely offline using SQLite, ChromaDB, and local Ollama.

Usage:
    python server.py [--host HOST] [--port PORT] [--debug]

Example:
    python server.py --host localhost --port 8000 --debug
"""

import asyncio
import argparse
import logging
import os
import signal
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from persona_mcp.mcp import create_server
from persona_mcp.simulation import run_chatroom_simulation


def setup_logging(debug: bool = False):
    """Configure logging"""
    
    # Create logs directory
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    
    # Set log level
    log_level = logging.DEBUG if debug else logging.INFO
    
    # Configure logging
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(logs_dir / "persona_server.log")
        ]
    )
    
    # Set library log levels
    logging.getLogger("aiohttp").setLevel(logging.WARNING)
    logging.getLogger("chromadb").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)


def create_data_directories():
    """Create necessary data directories"""
    
    directories = [
        "data",
        "data/vector_memory", 
        "logs"
    ]
    
    for dir_path in directories:
        Path(dir_path).mkdir(parents=True, exist_ok=True)


async def main_server(host: str, port: int, debug: bool):
    """Main server function"""
    
    setup_logging(debug)
    create_data_directories()
    
    logger = logging.getLogger(__name__)
    logger.info("Starting Persona MCP Server...")
    
    # Check environment
    if not await check_dependencies():
        logger.error("Dependency check failed")
        return 1
    
    # Create and start server
    server = await create_server(host, port)
    runner = None
    
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, shutting down...")
        asyncio.create_task(shutdown_server(server, runner))
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Start the server
        runner = await server.start_server()
        
        logger.info("=" * 50)
        logger.info(f"[READY] Persona MCP Server is running!")
        logger.info(f"[WEBSOCKET] WebSocket: ws://{host}:{port}/mcp")
        logger.info(f"[HEALTH] Health Check: http://{host}:{port}/")
        logger.info(f"[DEBUG] Debug Mode: {'Enabled' if debug else 'Disabled'}")
        logger.info("=" * 50)
        logger.info("[QUICK START] Quick Start:")
        logger.info("   1. Connect to WebSocket endpoint")
        logger.info("   2. Send: {'jsonrpc':'2.0','method':'persona.list','id':'1'}")
        logger.info("   3. Switch persona: {'jsonrpc':'2.0','method':'persona.switch','params':{'persona_id':'<id>'},'id':'2'}")
        logger.info("   4. Chat: {'jsonrpc':'2.0','method':'persona.chat','params':{'message':'Hello!'},'id':'3'}")
        logger.info("=" * 50)
        logger.info("Press Ctrl+C to stop the server")
        
        # Keep server running
        while True:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error(f"Server error: {e}")
        return 1
    finally:
        await shutdown_server(server, runner)
    
    return 0


async def shutdown_server(server, runner):
    """Gracefully shutdown the server"""
    
    logger = logging.getLogger(__name__)
    logger.info("Shutting down server...")
    
    try:
        await server.stop_server()
        
        if runner:
            await runner.cleanup()
        
        logger.info("Server shutdown complete")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")


async def check_dependencies():
    """Check if required dependencies are available"""
    
    logger = logging.getLogger(__name__)
    
    # Check if Ollama is running (optional)
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:11434/api/tags", timeout=5.0)
            if response.status_code == 200:
                models = response.json().get("models", [])
                logger.info(f"[OK] Ollama connected - {len(models)} models available")
            else:
                logger.warning("[WARN] Ollama not responding properly")
    except Exception:
        logger.warning("[WARN] Ollama not available - will use fallback responses")
    
    # Check database directory
    data_dir = Path("data")
    if data_dir.exists():
        logger.info("[OK] Data directory exists")
    else:
        logger.info("📁 Creating data directory")
        data_dir.mkdir(parents=True, exist_ok=True)
    
    # Check ChromaDB (it will be created on first use)
    try:
        import chromadb
        logger.info("[OK] ChromaDB available")
    except ImportError:
        logger.error("❌ ChromaDB not installed")
        return False
    
    # Check other dependencies
    required_modules = ['aiohttp', 'pydantic', 'sqlalchemy']
    for module in required_modules:
        try:
            __import__(module)
            logger.info(f"[OK] {module} available")
        except ImportError:
            logger.error(f"❌ {module} not installed")
            return False
    
    return True


async def run_simulation_mode(duration: int):
    """Run in simulation mode for testing"""
    
    setup_logging(debug=True)
    create_data_directories()
    
    logger = logging.getLogger(__name__)
    logger.info("Starting simulation mode...")
    
    await run_chatroom_simulation(duration)


def main():
    """CLI entry point"""
    
    parser = argparse.ArgumentParser(
        description="Persona MCP Server - Local AI persona interaction system",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python server.py                           # Start server on localhost:8000
  python server.py --host 0.0.0.0 --port 9000 --debug  # Custom host/port with debug
  python server.py --simulate 5             # Run 5-minute simulation test
  
Environment Variables:
  SERVER_HOST     Server host (default: localhost)
  SERVER_PORT     Server port (default: 8000)
  OLLAMA_HOST     Ollama host (default: http://localhost:11434)
  LOG_LEVEL       Log level (default: INFO)
        """
    )
    
    parser.add_argument(
        "--host",
        default=os.getenv("SERVER_HOST", "localhost"),
        help="Server host (default: localhost)"
    )
    
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("SERVER_PORT", "8000")),
        help="Server port (default: 8000)"
    )
    
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging"
    )
    
    parser.add_argument(
        "--simulate",
        type=int,
        metavar="MINUTES",
        help="Run simulation mode for specified minutes instead of starting server"
    )
    
    args = parser.parse_args()
    
    # Run simulation if requested
    if args.simulate:
        try:
            asyncio.run(run_simulation_mode(args.simulate))
        except KeyboardInterrupt:
            print("\nSimulation interrupted")
        return
    
    # Run main server
    try:
        exit_code = asyncio.run(main_server(args.host, args.port, args.debug))
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\nServer stopped")
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()