"""
Unit tests for persona_mcp.core.config module

Tests the shared ConfigManager class that provides unified configuration 
management for both MCP server and PersonaAPI server.
"""

import pytest
import os
import tempfile
from unittest.mock import patch, MagicMock
from pathlib import Path

from persona_mcp.core.config import ConfigManager


class TestConfigManagerInitialization:
    """Test ConfigManager initialization"""
    
    def test_config_manager_initializes_successfully(self):
        """Test that ConfigManager initializes without errors"""
        config_manager = ConfigManager()
        
        assert config_manager is not None
        assert hasattr(config_manager, 'config')
        assert hasattr(config_manager, 'logger')
    
    def test_config_manager_logs_initialization(self):
        """Test that ConfigManager logs its initialization"""
        with patch('persona_mcp.core.config.get_logger') as mock_get_logger:
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger
            
            config_manager = ConfigManager()
            
            mock_logger.info.assert_called_with("ConfigManager initialized")


class TestServerConfiguration:
    """Test server configuration methods"""
    
    def test_get_server_config_returns_dict(self):
        """Test get_server_config returns a dictionary with expected keys"""
        config_manager = ConfigManager()
        server_config = config_manager.get_server_config()
        
        assert isinstance(server_config, dict)
        assert "host" in server_config
        assert "port" in server_config
        assert "debug" in server_config
        assert "cors_origins" in server_config
        assert "max_connections" in server_config
    
    def test_get_server_config_default_values(self):
        """Test server config contains expected default values"""
        config_manager = ConfigManager()
        server_config = config_manager.get_server_config()
        
        # Test reasonable defaults
        assert isinstance(server_config["host"], str)
        assert isinstance(server_config["port"], int)
        assert isinstance(server_config["debug"], bool)
        assert isinstance(server_config["cors_origins"], list)
        assert isinstance(server_config["max_connections"], int)
        assert server_config["max_connections"] > 0
    
    def test_get_mcp_config_returns_dict(self):
        """Test get_mcp_config returns a dictionary with expected keys"""
        config_manager = ConfigManager()
        mcp_config = config_manager.get_mcp_config()
        
        assert isinstance(mcp_config, dict)
        assert "host" in mcp_config
        assert "port" in mcp_config
        assert "path" in mcp_config
        assert "max_message_size" in mcp_config
        assert "heartbeat_interval" in mcp_config
    
    def test_get_mcp_config_values(self):
        """Test MCP config contains expected values"""
        config_manager = ConfigManager()
        mcp_config = config_manager.get_mcp_config()
        
        assert mcp_config["path"] == "/mcp"
        assert isinstance(mcp_config["max_message_size"], int)
        assert isinstance(mcp_config["heartbeat_interval"], int)
        assert mcp_config["max_message_size"] > 0
        assert mcp_config["heartbeat_interval"] > 0
    
    def test_get_personaapi_config_returns_dict(self):
        """Test get_personaapi_config returns a dictionary with expected keys"""
        config_manager = ConfigManager()
        personaapi_config = config_manager.get_personaapi_config()
        
        assert isinstance(personaapi_config, dict)
        assert "host" in personaapi_config
        assert "port" in personaapi_config
        assert "cors_origins" in personaapi_config
        assert "title" in personaapi_config
        assert "description" in personaapi_config
        assert "version" in personaapi_config
        assert "docs_url" in personaapi_config
        assert "redoc_url" in personaapi_config
    
    def test_get_personaapi_config_values(self):
        """Test PersonaAPI config contains expected values"""
        config_manager = ConfigManager()
        personaapi_config = config_manager.get_personaapi_config()
        
        assert personaapi_config["port"] == 8081
        assert personaapi_config["cors_origins"] == ["*"]
        assert "PersonaAPI" in personaapi_config["title"]
        assert personaapi_config["docs_url"] == "/docs"
        assert personaapi_config["redoc_url"] == "/redoc"


class TestDatabaseConfiguration:
    """Test database configuration methods"""
    
    def test_get_database_config_returns_dict(self):
        """Test get_database_config returns a dictionary with expected keys"""
        config_manager = ConfigManager()
        database_config = config_manager.get_database_config()
        
        assert isinstance(database_config, dict)
        assert "sqlite_path" in database_config
        assert "vector_path" in database_config
        assert "connection_pool_size" in database_config
        assert "enable_wal" in database_config
    
    def test_get_database_config_values(self):
        """Test database config contains reasonable values"""
        config_manager = ConfigManager()
        database_config = config_manager.get_database_config()
        
        assert isinstance(database_config["sqlite_path"], str)
        assert isinstance(database_config["vector_path"], str)
        assert isinstance(database_config["connection_pool_size"], int)
        assert isinstance(database_config["enable_wal"], bool)
        assert database_config["connection_pool_size"] > 0


class TestMemoryConfiguration:
    """Test memory configuration methods"""
    
    def test_get_memory_config_returns_dict(self):
        """Test get_memory_config returns a dictionary with expected keys"""
        config_manager = ConfigManager()
        memory_config = config_manager.get_memory_config()
        
        assert isinstance(memory_config, dict)
        assert "max_memories_per_persona" in memory_config
        assert "importance_threshold" in memory_config
        assert "decay_enabled" in memory_config
        assert "decay_interval" in memory_config
        assert "pruning_enabled" in memory_config
        assert "pruning_interval" in memory_config
    
    def test_get_memory_config_values(self):
        """Test memory config contains reasonable values"""
        config_manager = ConfigManager()
        memory_config = config_manager.get_memory_config()
        
        assert isinstance(memory_config["max_memories_per_persona"], int)
        assert isinstance(memory_config["importance_threshold"], float)
        assert isinstance(memory_config["decay_enabled"], bool)
        assert isinstance(memory_config["decay_interval"], int)
        assert isinstance(memory_config["pruning_enabled"], bool)
        assert isinstance(memory_config["pruning_interval"], int)
        
        assert memory_config["max_memories_per_persona"] > 0
        assert 0.0 <= memory_config["importance_threshold"] <= 1.0
        assert memory_config["decay_interval"] > 0
        assert memory_config["pruning_interval"] > 0


class TestLLMConfiguration:
    """Test LLM configuration methods"""
    
    def test_get_llm_config_returns_dict(self):
        """Test get_llm_config returns a dictionary with expected keys"""
        config_manager = ConfigManager()
        llm_config = config_manager.get_llm_config()
        
        assert isinstance(llm_config, dict)
        assert "provider" in llm_config
        assert "base_url" in llm_config
        assert "model" in llm_config
        assert "temperature" in llm_config
        assert "max_tokens" in llm_config
        assert "timeout" in llm_config
        assert "stream" in llm_config
    
    def test_get_llm_config_values(self):
        """Test LLM config contains reasonable values"""
        config_manager = ConfigManager()
        llm_config = config_manager.get_llm_config()
        
        assert isinstance(llm_config["provider"], str)
        assert isinstance(llm_config["base_url"], str)
        assert isinstance(llm_config["model"], str)
        assert isinstance(llm_config["temperature"], float)
        assert isinstance(llm_config["max_tokens"], int)
        assert isinstance(llm_config["timeout"], int)
        assert isinstance(llm_config["stream"], bool)
        
        assert 0.0 <= llm_config["temperature"] <= 2.0
        assert llm_config["max_tokens"] > 0
        assert llm_config["timeout"] > 0


class TestLoggingConfiguration:
    """Test logging configuration methods"""
    
    def test_get_logging_config_returns_dict(self):
        """Test get_logging_config returns a dictionary with expected keys"""
        config_manager = ConfigManager()
        logging_config = config_manager.get_logging_config()
        
        assert isinstance(logging_config, dict)
        assert "level" in logging_config
        assert "format" in logging_config
        assert "file_path" in logging_config
        assert "max_file_size" in logging_config
        assert "backup_count" in logging_config
        assert "enable_correlation_id" in logging_config
    
    def test_get_logging_config_values(self):
        """Test logging config contains reasonable values"""
        config_manager = ConfigManager()
        logging_config = config_manager.get_logging_config()
        
        assert isinstance(logging_config["level"], str)
        assert isinstance(logging_config["format"], str)
        assert isinstance(logging_config["file_path"], str)
        assert isinstance(logging_config["max_file_size"], int)
        assert isinstance(logging_config["backup_count"], int)
        assert isinstance(logging_config["enable_correlation_id"], bool)
        
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        assert logging_config["level"] in valid_levels
        assert logging_config["max_file_size"] > 0
        assert logging_config["backup_count"] >= 0


class TestBotConfiguration:
    """Test bot configuration methods"""
    
    def test_get_bot_config_returns_dict(self):
        """Test get_bot_config returns a dictionary with expected keys"""
        config_manager = ConfigManager()
        bot_config = config_manager.get_bot_config()
        
        assert isinstance(bot_config, dict)
        assert "log_directory" in bot_config
        assert "max_log_file_size" in bot_config
        assert "log_retention_days" in bot_config
        assert "startup_timeout" in bot_config
        assert "shutdown_timeout" in bot_config
        assert "restart_delay" in bot_config
        assert "max_restart_attempts" in bot_config
    
    def test_get_bot_config_values(self):
        """Test bot config contains reasonable values"""
        config_manager = ConfigManager()
        bot_config = config_manager.get_bot_config()
        
        assert isinstance(bot_config["log_directory"], str)
        assert isinstance(bot_config["max_log_file_size"], int)
        assert isinstance(bot_config["log_retention_days"], int)
        assert isinstance(bot_config["startup_timeout"], int)
        assert isinstance(bot_config["shutdown_timeout"], int)
        assert isinstance(bot_config["restart_delay"], int)
        assert isinstance(bot_config["max_restart_attempts"], int)
        
        assert bot_config["max_log_file_size"] > 0
        assert bot_config["log_retention_days"] > 0
        assert bot_config["startup_timeout"] > 0
        assert bot_config["shutdown_timeout"] > 0
        assert bot_config["restart_delay"] >= 0
        assert bot_config["max_restart_attempts"] >= 0


class TestSecurityConfiguration:
    """Test security configuration methods"""
    
    def test_get_security_config_returns_dict(self):
        """Test get_security_config returns a dictionary with expected keys"""
        config_manager = ConfigManager()
        security_config = config_manager.get_security_config()
        
        assert isinstance(security_config, dict)
        assert "enable_cors" in security_config
        assert "cors_origins" in security_config
        assert "cors_methods" in security_config
        assert "cors_headers" in security_config
        assert "rate_limit_enabled" in security_config
        assert "rate_limit_requests" in security_config
        assert "rate_limit_window" in security_config
        assert "api_key_required" in security_config
    
    def test_get_security_config_values(self):
        """Test security config contains reasonable values"""
        config_manager = ConfigManager()
        security_config = config_manager.get_security_config()
        
        assert isinstance(security_config["enable_cors"], bool)
        assert isinstance(security_config["cors_origins"], list)
        assert isinstance(security_config["cors_methods"], list)
        assert isinstance(security_config["cors_headers"], list)
        assert isinstance(security_config["rate_limit_enabled"], bool)
        assert isinstance(security_config["rate_limit_requests"], int)
        assert isinstance(security_config["rate_limit_window"], int)
        assert isinstance(security_config["api_key_required"], bool)
        
        assert security_config["rate_limit_requests"] > 0
        assert security_config["rate_limit_window"] > 0


class TestMonitoringConfiguration:
    """Test monitoring configuration methods"""
    
    def test_get_monitoring_config_returns_dict(self):
        """Test get_monitoring_config returns a dictionary with expected keys"""
        config_manager = ConfigManager()
        monitoring_config = config_manager.get_monitoring_config()
        
        assert isinstance(monitoring_config, dict)
        assert "enable_metrics" in monitoring_config
        assert "metrics_port" in monitoring_config
        assert "health_check_interval" in monitoring_config
        assert "performance_tracking" in monitoring_config
        assert "error_tracking" in monitoring_config
    
    def test_get_monitoring_config_values(self):
        """Test monitoring config contains reasonable values"""
        config_manager = ConfigManager()
        monitoring_config = config_manager.get_monitoring_config()
        
        assert isinstance(monitoring_config["enable_metrics"], bool)
        assert isinstance(monitoring_config["metrics_port"], int)
        assert isinstance(monitoring_config["health_check_interval"], int)
        assert isinstance(monitoring_config["performance_tracking"], bool)
        assert isinstance(monitoring_config["error_tracking"], bool)
        
        assert monitoring_config["metrics_port"] > 0
        assert monitoring_config["health_check_interval"] > 0


class TestConfigValidation:
    """Test configuration validation"""
    
    def test_validate_config_returns_dict(self):
        """Test validate_config returns a dictionary with expected structure"""
        config_manager = ConfigManager()
        validation_result = config_manager.validate_config()
        
        assert isinstance(validation_result, dict)
        assert "valid" in validation_result
        assert "errors" in validation_result
        assert "warnings" in validation_result
        assert isinstance(validation_result["valid"], bool)
        assert isinstance(validation_result["errors"], list)
        assert isinstance(validation_result["warnings"], list)
    
    def test_validate_config_with_valid_config(self):
        """Test validate_config with valid configuration"""
        config_manager = ConfigManager()
        validation_result = config_manager.validate_config()
        
        # Should be valid by default
        assert validation_result["valid"] == True
    
    def test_validate_config_detects_port_conflicts(self):
        """Test validate_config detects port conflicts between MCP and PersonaAPI"""
        with patch.object(ConfigManager, 'get_server_config') as mock_server_config:
            with patch.object(ConfigManager, 'get_personaapi_config') as mock_personaapi_config:
                # Set same port for both services
                mock_server_config.return_value = {"port": 8080}
                mock_personaapi_config.return_value = {"port": 8080}
                
                config_manager = ConfigManager()
                validation_result = config_manager.validate_config()
                
                assert validation_result["valid"] == False
                assert any("port cannot be the same" in error for error in validation_result["errors"])
    
    def test_validate_config_detects_invalid_port(self):
        """Test validate_config detects invalid port numbers"""
        with patch.object(ConfigManager, 'get_server_config') as mock_server_config:
            mock_server_config.return_value = {"port": -1}
            
            config_manager = ConfigManager()
            validation_result = config_manager.validate_config()
            
            assert validation_result["valid"] == False
            assert any("port must be a positive integer" in error for error in validation_result["errors"])
    
    def test_validate_config_detects_missing_database_path(self):
        """Test validate_config detects missing database path"""
        with patch.object(ConfigManager, 'get_database_config') as mock_db_config:
            mock_db_config.return_value = {"sqlite_path": ""}
            
            config_manager = ConfigManager()
            validation_result = config_manager.validate_config()
            
            assert validation_result["valid"] == False
            assert any("SQLite database path not configured" in error for error in validation_result["errors"])
    
    def test_validate_config_warns_about_missing_llm_url(self):
        """Test validate_config warns about missing LLM base URL"""
        with patch.object(ConfigManager, 'get_llm_config') as mock_llm_config:
            mock_llm_config.return_value = {"base_url": ""}
            
            config_manager = ConfigManager()
            validation_result = config_manager.validate_config()
            
            assert any("LLM base URL not configured" in warning for warning in validation_result["warnings"])


class TestCompleteConfiguration:
    """Test complete configuration methods"""
    
    def test_get_all_config_returns_dict(self):
        """Test get_all_config returns a dictionary with all sections"""
        config_manager = ConfigManager()
        all_config = config_manager.get_all_config()
        
        assert isinstance(all_config, dict)
        assert "server" in all_config
        assert "mcp" in all_config
        assert "personaapi" in all_config
        assert "database" in all_config
        assert "memory" in all_config
        assert "llm" in all_config
        assert "logging" in all_config
        assert "bot" in all_config
        assert "security" in all_config
        assert "monitoring" in all_config
    
    def test_get_all_config_structure(self):
        """Test get_all_config returns properly structured configuration"""
        config_manager = ConfigManager()
        all_config = config_manager.get_all_config()
        
        # Each section should be a dictionary
        for section_name, section_config in all_config.items():
            assert isinstance(section_config, dict), f"Section {section_name} should be a dict"
            assert len(section_config) > 0, f"Section {section_name} should not be empty"


class TestConfigurationUpdates:
    """Test configuration update functionality"""
    
    def test_update_config_returns_bool(self):
        """Test update_config returns a boolean result"""
        config_manager = ConfigManager()
        
        # Mock config object with server section
        mock_server_section = MagicMock()
        mock_server_section.host = "localhost"
        config_manager.config.server = mock_server_section
        
        result = config_manager.update_config("server", {"host": "0.0.0.0"})
        
        assert isinstance(result, bool)
    
    def test_update_config_success(self):
        """Test successful configuration update"""
        config_manager = ConfigManager()
        
        # Mock config object with server section
        mock_server_section = MagicMock()
        mock_server_section.host = "localhost"
        config_manager.config.server = mock_server_section
        
        result = config_manager.update_config("server", {"host": "0.0.0.0"})
        
        assert result == True
        # Verify the update was applied
        assert mock_server_section.host == "0.0.0.0"
    
    def test_update_config_invalid_section(self):
        """Test update_config with invalid section"""
        config_manager = ConfigManager()
        
        result = config_manager.update_config("nonexistent_section", {"key": "value"})
        
        assert result == False
    
    def test_update_config_invalid_key(self):
        """Test update_config with invalid key in valid section"""
        with patch.object(ConfigManager, '__init__', return_value=None):
            config_manager = ConfigManager()
            config_manager.logger = MagicMock()
            
            # Mock config object with server section
            mock_server_section = MagicMock()
            config_manager.config = MagicMock()
            config_manager.config.server = mock_server_section
            
            # Mock hasattr to return False for nonexistent key
            with patch('builtins.hasattr') as mock_hasattr:
                mock_hasattr.side_effect = lambda obj, attr: attr != "nonexistent_key"
                
                result = config_manager.update_config("server", {"nonexistent_key": "value"})
                
                assert result == True  # Still returns True but logs warning
                config_manager.logger.warning.assert_called()
    
    def test_update_config_logs_changes(self):
        """Test that config updates are logged"""
        with patch.object(ConfigManager, '__init__', return_value=None):
            config_manager = ConfigManager()
            config_manager.logger = MagicMock()
            
            # Mock config object with server section
            mock_server_section = MagicMock()
            mock_server_section.host = "localhost"
            config_manager.config = MagicMock()
            config_manager.config.server = mock_server_section
            
            config_manager.update_config("server", {"host": "0.0.0.0"})
            
            config_manager.logger.info.assert_called_with("Updated config server.host = 0.0.0.0")
    
    def test_update_config_handles_exceptions(self):
        """Test update_config handles exceptions gracefully"""
        with patch.object(ConfigManager, '__init__', return_value=None):
            config_manager = ConfigManager()
            config_manager.logger = MagicMock()
            
            # Mock config to raise an exception during hasattr check
            config_manager.config = MagicMock()
            
            # Make hasattr raise an exception
            with patch('builtins.hasattr') as mock_hasattr:
                mock_hasattr.side_effect = Exception("Test exception")
                
                result = config_manager.update_config("server", {"host": "0.0.0.0"})
                
                assert result == False
                config_manager.logger.error.assert_called()


class TestConfigManagerIntegration:
    """Test ConfigManager integration with original config system"""
    
    def test_config_manager_uses_original_config(self):
        """Test that ConfigManager properly integrates with original config system"""
        with patch('persona_mcp.core.config.get_original_config') as mock_get_config:
            with patch('persona_mcp.core.config.get_logger') as mock_get_logger:
                mock_config = MagicMock()
                mock_logger = MagicMock()
                mock_get_config.return_value = mock_config
                mock_get_logger.return_value = mock_logger
                
                config_manager = ConfigManager()
                
                assert config_manager.config == mock_config
                mock_get_config.assert_called_once()
    
    def test_config_manager_handles_missing_attributes(self):
        """Test ConfigManager handles missing attributes gracefully"""
        with patch.object(ConfigManager, '__init__', return_value=None):
            config_manager = ConfigManager()
            config_manager.logger = MagicMock()
            
            # Mock config with minimal attributes
            config_manager.config = MagicMock()
            config_manager.config.server = MagicMock()
            config_manager.config.server.host = "localhost"
            config_manager.config.server.port = 8080
            config_manager.config.database = MagicMock()
            config_manager.config.database.path = "/tmp/test.db"
            
            # Should not raise an error even if attributes are missing
            server_config = config_manager.get_server_config()
            assert isinstance(server_config, dict)
            
            # Test with getattr defaults
            memory_config = config_manager.get_memory_config()
            assert isinstance(memory_config, dict)


class TestConfigManagerEdgeCases:
    """Test edge cases and error handling"""
    
    def test_config_manager_with_none_config_attributes(self):
        """Test ConfigManager when config attributes are None"""
        with patch.object(ConfigManager, '__init__', return_value=None):
            config_manager = ConfigManager()
            config_manager.logger = MagicMock()
            
            # Mock config with None attributes
            config_manager.config = MagicMock()
            config_manager.config.server = None
            
            # Should handle gracefully using getattr defaults
            server_config = config_manager.get_server_config()
            assert isinstance(server_config, dict)
    
    def test_config_sections_are_consistent(self):
        """Test that all configuration sections are internally consistent"""
        with patch.object(ConfigManager, '__init__', return_value=None):
            config_manager = ConfigManager()
            config_manager.logger = MagicMock()
            
            # Mock config with consistent host
            config_manager.config = MagicMock()
            config_manager.config.server = MagicMock()
            config_manager.config.server.host = "test-host"
            config_manager.config.server.port = 8080
            config_manager.config.server.mcp_port = 8081
            config_manager.config.server.personaapi_port = 8082
            
            # Test that MCP and PersonaAPI configs use same host from server config
            server_config = config_manager.get_server_config()
            mcp_config = config_manager.get_mcp_config()
            personaapi_config = config_manager.get_personaapi_config()
            
            assert mcp_config["host"] == server_config["host"]
            assert personaapi_config["host"] == server_config["host"]
    
    def test_all_config_methods_return_dicts(self):
        """Test that all config methods return dictionaries"""
        with patch.object(ConfigManager, '__init__', return_value=None):
            config_manager = ConfigManager()
            config_manager.logger = MagicMock()
            
            # Mock config with all required attributes
            config_manager.config = MagicMock()
            config_manager.config.server = MagicMock()
            config_manager.config.server.host = "localhost"
            config_manager.config.server.port = 8080
            config_manager.config.server.mcp_port = 8081
            config_manager.config.server.personaapi_port = 8082
            config_manager.config.database = MagicMock()
            config_manager.config.database.path = "/tmp/test.db"
            config_manager.config.memory = MagicMock()
            config_manager.config.memory.max_entries = 1000
            config_manager.config.ollama = MagicMock()
            config_manager.config.ollama.url = "http://localhost:11434"
            config_manager.config.persona = MagicMock()
            config_manager.config.persona.name = "TestBot"
            config_manager.config.session = MagicMock()
            config_manager.config.session.max_age = 3600
            config_manager.config.conversation = MagicMock()
            config_manager.config.conversation.max_history = 50
            config_manager.config.simulation = MagicMock()
            config_manager.config.simulation.enabled = True
            
            config_methods = [
                config_manager.get_server_config,
                config_manager.get_mcp_config,
                config_manager.get_personaapi_config,
                config_manager.get_database_config,
                config_manager.get_memory_config,
                config_manager.get_llm_config,
                config_manager.get_logging_config,
                config_manager.get_bot_config,
                config_manager.get_security_config,
                config_manager.get_monitoring_config,
                config_manager.get_all_config
            ]
            
            for method in config_methods:
                result = method()
                assert isinstance(result, dict), f"{method.__name__} should return a dict"
                assert len(result) > 0, f"{method.__name__} should return non-empty dict"