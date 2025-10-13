"""
Configuration management package for Persona MCP Server

Provides centralized configuration management with:
- Environment variable loading from .env files
- Runtime configuration validation 
- Type-safe configuration classes
- Global configuration access patterns

Usage:
    from persona_mcp.config import get_config
    
    config = get_config()
    print(f"Server running on {config.server.host}:{config.server.port}")
    print(f"Using model: {config.ollama.default_model}")
"""

from .manager import (
    ConfigManager,
    ServerConfig, 
    OllamaConfig,
    SessionConfig,
    MemoryConfig,
    PersonaConfig,
    ConversationConfig,
    DatabaseConfig,
    SimulationConfig,
    DecayMode,
    Priority,
    get_config,
    init_config
)

__all__ = [
    "ConfigManager",
    "ServerConfig",
    "OllamaConfig", 
    "SessionConfig",
    "MemoryConfig",
    "PersonaConfig",
    "ConversationConfig",
    "DatabaseConfig",
    "SimulationConfig",
    "DecayMode",
    "Priority",
    "get_config",
    "init_config"
]