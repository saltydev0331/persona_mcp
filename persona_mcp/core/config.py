"""
Shared configuration manager for Persona-MCP system.

Provides unified configuration management for both MCP server and PersonaAPI server
to ensure consistent settings and operational parity.
"""

from typing import Dict, Any, Optional
from ..config import get_config as get_original_config, ConfigManager as OriginalConfigManager
from ..logging import get_logger


class ConfigManager:
    """Unified configuration manager for both services"""
    
    def __init__(self):
        self.config = get_original_config()
        self.logger = get_logger(__name__)
        self.logger.info("ConfigManager initialized")

    def get_server_config(self) -> Dict[str, Any]:
        """Get server configuration settings"""
        server = getattr(self.config, 'server', None)
        return {
            "host": getattr(server, 'host', 'localhost') if server else 'localhost',
            "port": getattr(server, 'port', 8080) if server else 8080,
            "debug": getattr(server, 'debug_mode', False) if server else False,
            "cors_origins": getattr(server, 'cors_origins', ['*']) if server else ['*'],
            "max_connections": getattr(server, 'max_connections', 100) if server else 100
        }

    def get_mcp_config(self) -> Dict[str, Any]:
        """Get MCP-specific configuration"""
        server = getattr(self.config, 'server', None)
        return {
            "host": getattr(server, 'host', 'localhost') if server else 'localhost',
            "port": getattr(server, 'port', 8080) if server else 8080,
            "path": "/mcp",
            "max_message_size": getattr(server, 'max_message_size', 1024 * 1024) if server else 1024 * 1024,
            "heartbeat_interval": getattr(server, 'heartbeat_interval', 30) if server else 30
        }

    def get_personaapi_config(self) -> Dict[str, Any]:
        """Get PersonaAPI-specific configuration"""
        server = getattr(self.config, 'server', None)
        return {
            "host": getattr(server, 'host', 'localhost') if server else 'localhost',
            "port": 8081,  # Default PersonaAPI port (changed from 8080 to avoid Docker conflict)
            "cors_origins": ["*"],
            "title": "Persona MCP - PersonaAPI Server",
            "description": "HTTP REST API for persona management and monitoring",
            "version": "0.3.0",
            "docs_url": "/docs",
            "redoc_url": "/redoc"
        }

    def get_database_config(self) -> Dict[str, Any]:
        """Get database configuration settings"""
        return {
            "sqlite_path": getattr(self.config.database, 'path', 'data/personas.db'),
            "vector_path": getattr(self.config.database, 'vector_path', 'data/vector_memory'),
            "connection_pool_size": getattr(self.config.database, 'pool_size', 10),
            "enable_wal": getattr(self.config.database, 'enable_wal', True)
        }

    def get_memory_config(self) -> Dict[str, Any]:
        """Get memory management configuration"""
        return {
            "max_memories_per_persona": getattr(self.config.memory, 'max_per_persona', 1000),
            "importance_threshold": getattr(self.config.memory, 'importance_threshold', 0.3),
            "decay_enabled": getattr(self.config.memory, 'decay_enabled', True),
            "decay_interval": getattr(self.config.memory, 'decay_interval', 3600),  # 1 hour
            "pruning_enabled": getattr(self.config.memory, 'pruning_enabled', True),
            "pruning_interval": getattr(self.config.memory, 'pruning_interval', 86400)  # 24 hours
        }

    def get_llm_config(self) -> Dict[str, Any]:
        """Get LLM configuration settings"""
        return {
            "provider": getattr(self.config.ollama, 'provider', 'ollama'),
            "base_url": getattr(self.config.ollama, 'host', 'http://localhost:11434'),
            "model": getattr(self.config.ollama, 'default_model', 'llama3.2:latest'),
            "temperature": getattr(self.config.ollama, 'temperature', 0.7),
            "max_tokens": getattr(self.config.ollama, 'max_tokens', 2048),
            "timeout": getattr(self.config.ollama, 'timeout_seconds', 30),
            "stream": getattr(self.config.ollama, 'stream', True)
        }

    def get_logging_config(self) -> Dict[str, Any]:
        """Get logging configuration settings"""
        return {
            "level": getattr(self.config.server, 'log_level', 'INFO'),
            "format": getattr(self.config.server, 'log_format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s'),
            "file_path": getattr(self.config.server, 'log_file', 'logs/persona_mcp.log'),
            "max_file_size": getattr(self.config.server, 'max_file_size', 10 * 1024 * 1024),  # 10MB
            "backup_count": getattr(self.config.server, 'backup_count', 5),
            "enable_correlation_id": getattr(self.config.server, 'structured_logging', True)
        }

    def get_bot_config(self) -> Dict[str, Any]:
        """Get bot management configuration"""
        return {
            "log_directory": "logs/bots",
            "max_log_file_size": 5 * 1024 * 1024,  # 5MB
            "log_retention_days": 7,
            "startup_timeout": 30,  # seconds
            "shutdown_timeout": 10,  # seconds
            "restart_delay": 5,  # seconds between restart attempts
            "max_restart_attempts": 3
        }

    def get_security_config(self) -> Dict[str, Any]:
        """Get security configuration settings"""
        return {
            "enable_cors": True,
            "cors_origins": ["*"],
            "cors_methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "cors_headers": ["*"],
            "rate_limit_enabled": False,
            "rate_limit_requests": 100,
            "rate_limit_window": 3600,  # 1 hour
            "api_key_required": False
        }

    def get_monitoring_config(self) -> Dict[str, Any]:
        """Get monitoring and metrics configuration"""
        return {
            "enable_metrics": True,
            "metrics_port": 9090,
            "health_check_interval": 60,
            "performance_tracking": True,
            "error_tracking": True
        }

    def validate_config(self) -> Dict[str, Any]:
        """Validate configuration settings and return validation results"""
        validation_results = {
            "valid": True,
            "errors": [],
            "warnings": []
        }

        # Validate server config
        server_config = self.get_server_config()
        if not isinstance(server_config.get("port"), int) or server_config.get("port") <= 0:
            validation_results["errors"].append("Server port must be a positive integer")
            validation_results["valid"] = False

        # Validate PersonaAPI port
        personaapi_config = self.get_personaapi_config()
        if personaapi_config.get("port") == server_config.get("port"):
            validation_results["errors"].append("PersonaAPI port cannot be the same as MCP server port")
            validation_results["valid"] = False

        # Validate LLM config
        llm_config = self.get_llm_config()
        if not llm_config.get("base_url"):
            validation_results["warnings"].append("LLM base URL not configured")

        # Validate database paths
        db_config = self.get_database_config()
        if not db_config.get("sqlite_path"):
            validation_results["errors"].append("SQLite database path not configured")
            validation_results["valid"] = False

        return validation_results

    def get_all_config(self) -> Dict[str, Any]:
        """Get complete configuration for debugging/display purposes"""
        return {
            "server": self.get_server_config(),
            "mcp": self.get_mcp_config(),
            "personaapi": self.get_personaapi_config(),
            "database": self.get_database_config(),
            "memory": self.get_memory_config(),
            "llm": self.get_llm_config(),
            "logging": self.get_logging_config(),
            "bot": self.get_bot_config(),
            "security": self.get_security_config(),
            "monitoring": self.get_monitoring_config()
        }

    def update_config(self, section: str, updates: Dict[str, Any]) -> bool:
        """Update configuration section (for runtime configuration changes)"""
        try:
            if hasattr(self.config, section):
                section_obj = getattr(self.config, section)
                for key, value in updates.items():
                    if hasattr(section_obj, key):
                        setattr(section_obj, key, value)
                        self.logger.info(f"Updated config {section}.{key} = {value}")
                    else:
                        self.logger.warning(f"Unknown config key: {section}.{key}")
                return True
            else:
                self.logger.error(f"Unknown config section: {section}")
                return False
        except Exception as e:
            self.logger.error(f"Failed to update config: {e}")
            return False