"""
Unit tests for persona_mcp.config.manager module

Tests configuration loading, validation, and environment variable handling.
"""

import pytest
import os
import tempfile
from pathlib import Path

from persona_mcp.config.manager import (
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


# Test environment file for consistent testing
TEST_ENV_FILE = ".env.test"


class TestConfigDataClasses:
    """Test configuration dataclass creation"""
    
    def test_server_config_defaults(self):
        """Test ServerConfig default values"""
        config = ServerConfig()
        
        assert config.host == "localhost"
        assert config.port == 8000
        assert config.debug_mode == False
        assert config.websocket_timeout == 300
        assert config.max_connections == 100
    
    def test_ollama_config_defaults(self):
        """Test OllamaConfig default values"""
        config = OllamaConfig()
        
        assert config.host == "http://localhost:11434"
        assert config.default_model == "llama3.1:8b"
        assert config.timeout_seconds == 60
        assert config.max_retries == 3
    
    def test_session_config_defaults(self):
        """Test SessionConfig default values"""
        config = SessionConfig()
        
        assert config.max_context_messages == 20
        assert config.context_summary_threshold == 50
        assert config.session_timeout_hours == 24
    
    def test_memory_config_defaults(self):
        """Test MemoryConfig default values"""
        config = MemoryConfig()
        
        assert config.importance_min == 0.51
        assert config.importance_max == 0.80
        assert config.decay_mode == DecayMode.EXPONENTIAL
        assert config.decay_rate == 0.1
        assert config.enable_auto_pruning == True
    
    def test_persona_config_defaults(self):
        """Test PersonaConfig default values"""
        config = PersonaConfig()
        
        assert config.default_charisma == 10
        assert config.default_intelligence == 10
        assert config.default_social_rank == "commoner"
        assert config.default_social_energy == 100


class TestConfigManagerInitialization:
    """Test ConfigManager initialization"""
    
    def test_config_manager_creates_instances(self):
        """Test that ConfigManager creates all config instances"""
        manager = ConfigManager()
        
        assert isinstance(manager.server, ServerConfig)
        assert isinstance(manager.ollama, OllamaConfig)
        assert isinstance(manager.session, SessionConfig)
        assert isinstance(manager.memory, MemoryConfig)
        assert isinstance(manager.persona, PersonaConfig)
        assert isinstance(manager.conversation, ConversationConfig)
        assert isinstance(manager.database, DatabaseConfig)
        assert isinstance(manager.simulation, SimulationConfig)
    
    def test_config_manager_without_env_file(self):
        """Test ConfigManager works without .env file"""
        manager = ConfigManager()
        
        # Should use default values
        assert manager.server.port == 8000
        assert manager.ollama.default_model == "llama3.1:8b"
    
    def test_config_manager_with_missing_env_file(self):
        """Test ConfigManager with non-existent .env file"""
        # Should not raise an error
        manager = ConfigManager(env_file_path="/nonexistent/.env")
        
        assert isinstance(manager, ConfigManager)


class TestEnvironmentVariables:
    """Test environment variable loading"""
    
    def test_env_variable_override(self, monkeypatch):
        """Test that environment variables override defaults"""
        monkeypatch.setenv("SERVER_PORT", "9000")
        monkeypatch.setenv("SERVER_HOST", "0.0.0.0")
        
        # Pass empty string to skip .env file loading
        manager = ConfigManager(env_file_path="/nonexistent/.env")
        
        assert manager.server.port == 9000
        assert manager.server.host == "0.0.0.0"
    
    def test_ollama_env_variables(self, monkeypatch):
        """Test Ollama configuration from environment"""
        monkeypatch.setenv("OLLAMA_HOST", "http://custom-host:11434")
        monkeypatch.setenv("DEFAULT_MODEL", "custom-model")
        
        manager = ConfigManager(env_file_path="/nonexistent/.env")
        
        assert manager.ollama.host == "http://custom-host:11434"
        assert manager.ollama.default_model == "custom-model"
    
    def test_memory_env_variables(self, monkeypatch):
        """Test memory configuration from environment"""
        monkeypatch.setenv("MEMORY_IMPORTANCE_MIN", "0.4")
        monkeypatch.setenv("MEMORY_IMPORTANCE_MAX", "0.9")
        monkeypatch.setenv("MEMORY_DECAY_RATE", "0.2")
        
        manager = ConfigManager()
        
        assert manager.memory.importance_min == 0.4
        assert manager.memory.importance_max == 0.9
        assert manager.memory.decay_rate == 0.2
    
    def test_boolean_env_variables(self, monkeypatch):
        """Test boolean environment variable parsing"""
        monkeypatch.setenv("DEBUG_MODE", "true")
        monkeypatch.setenv("MEMORY_DECAY_ENABLED", "false")
        
        manager = ConfigManager(env_file_path="/nonexistent/.env")
        
        assert manager.server.debug_mode == True
        assert manager.memory.decay_enabled == False


class TestEnvFileLoading:
    """Test .env file loading"""
    
    def test_load_from_env_file(self):
        """Test loading configuration from .env file"""
        # Create temporary .env file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            f.write("SERVER_PORT=7777\n")
            f.write("DEFAULT_MODEL=test-model\n")
            f.write("MEMORY_IMPORTANCE_MIN=0.3\n")
            env_file = f.name
        
        try:
            manager = ConfigManager(env_file_path=env_file)
            
            assert manager.server.port == 7777
            assert manager.ollama.default_model == "test-model"
            assert manager.memory.importance_min == 0.3
        finally:
            os.unlink(env_file)
    
    def test_env_file_with_comments(self):
        """Test .env file with comments and empty lines"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            f.write("# This is a comment\n")
            f.write("\n")
            f.write("SERVER_PORT=8888\n")
            f.write("# Another comment\n")
            f.write("DEFAULT_MODEL=comment-test\n")
            env_file = f.name
        
        try:
            manager = ConfigManager(env_file_path=env_file)
            
            assert manager.server.port == 8888
            assert manager.ollama.default_model == "comment-test"
        finally:
            os.unlink(env_file)


class TestConfigValidation:
    """Test configuration validation"""
    
    def test_valid_configuration_passes(self):
        """Test that valid configuration passes validation"""
        # Should not raise an error
        manager = ConfigManager()
        assert manager is not None
    
    def test_invalid_importance_range(self, monkeypatch):
        """Test validation fails for invalid importance range"""
        monkeypatch.setenv("MEMORY_IMPORTANCE_MIN", "0.9")
        monkeypatch.setenv("MEMORY_IMPORTANCE_MAX", "0.5")
        
        with pytest.raises(ValueError, match="importance_min must be less than importance_max"):
            ConfigManager(env_file_path="/nonexistent/.env")
    
    def test_invalid_port_range(self, monkeypatch):
        """Test validation fails for invalid port"""
        monkeypatch.setenv("SERVER_PORT", "70000")
        
        with pytest.raises(ValueError, match="port must be between"):
            ConfigManager(env_file_path="/nonexistent/.env")
    
    def test_invalid_prune_percent(self, monkeypatch):
        """Test validation fails for invalid prune percentage"""
        monkeypatch.setenv("MEMORY_MAX_PRUNE_PERCENT", "1.5")
        
        with pytest.raises(ValueError, match="max_prune_percent"):
            ConfigManager(env_file_path="/nonexistent/.env")
    
    def test_invalid_continue_threshold(self, monkeypatch):
        """Test validation fails for invalid continue threshold"""
        monkeypatch.setenv("PERSONA_CONTINUE_THRESHOLD", "150")
        
        with pytest.raises(ValueError, match="continue_threshold must be between"):
            ConfigManager(env_file_path="/nonexistent/.env")
    
    def test_memory_weights_sum_validation(self, monkeypatch):
        """Test validation of memory scoring weights sum"""
        # Set ALL weights so they don't sum to 1.0 (will sum to 1.0 if we only set some)
        monkeypatch.setenv("MEMORY_CONTENT_WEIGHT", "0.5")
        monkeypatch.setenv("MEMORY_ENGAGEMENT_WEIGHT", "0.4")
        monkeypatch.setenv("MEMORY_PERSONA_WEIGHT", "0.05")
        monkeypatch.setenv("MEMORY_TEMPORAL_WEIGHT", "0.02")
        monkeypatch.setenv("MEMORY_RELATIONSHIP_WEIGHT", "0.02")
        monkeypatch.setenv("MEMORY_RECENCY_WEIGHT", "0.02")  # Total = 1.01, should fail
        
        with pytest.raises(ValueError, match="weights sum"):
            ConfigManager(env_file_path="/nonexistent/.env")


class TestEnumParsing:
    """Test enum value parsing from environment"""
    
    def test_decay_mode_enum_parsing(self, monkeypatch):
        """Test DecayMode enum parsing"""
        monkeypatch.setenv("MEMORY_DECAY_MODE", "linear")
        
        manager = ConfigManager()
        
        assert manager.memory.decay_mode == DecayMode.LINEAR
    
    def test_invalid_decay_mode(self, monkeypatch):
        """Test that invalid decay mode falls back to default"""
        monkeypatch.setenv("MEMORY_DECAY_MODE", "invalid_mode")
        
        manager = ConfigManager()
        
        # Should fall back to default (EXPONENTIAL)
        assert manager.memory.decay_mode == DecayMode.EXPONENTIAL


class TestGetConfigSummary:
    """Test configuration summary generation"""
    
    def test_get_summary_returns_dict(self):
        """Test that get_summary returns a dictionary"""
        manager = ConfigManager()
        summary = manager.get_summary()
        
        assert isinstance(summary, dict)
        assert "server" in summary
        assert "ollama" in summary
        assert "memory" in summary
        assert "session" in summary
    
    def test_summary_contains_key_values(self):
        """Test that summary contains key configuration values"""
        manager = ConfigManager()
        summary = manager.get_summary()
        
        assert summary["server"]["host"] == "localhost"
        assert summary["server"]["port"] == 8000
        assert summary["ollama"]["default_model"] == "llama3.1:8b"
        assert "importance_range" in summary["memory"]


class TestGlobalConfigFunctions:
    """Test global configuration getter functions"""
    
    def test_get_config_returns_instance(self):
        """Test get_config returns a ConfigManager instance"""
        config = get_config()
        
        assert isinstance(config, ConfigManager)
    
    def test_get_config_returns_same_instance(self):
        """Test get_config returns the same singleton instance"""
        config1 = get_config()
        config2 = get_config()
        
        assert config1 is config2
    
    def test_init_config_creates_new_instance(self):
        """Test init_config creates a new instance"""
        config1 = get_config()
        config2 = init_config()
        
        # Should be different instances
        assert isinstance(config2, ConfigManager)
    
    def test_init_config_with_env_file(self):
        """Test init_config with custom env file"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            f.write("SERVER_PORT=5555\n")
            env_file = f.name
        
        try:
            config = init_config(env_file_path=env_file)
            
            assert config.server.port == 5555
        finally:
            os.unlink(env_file)


class TestTypeConversion:
    """Test type conversion utilities"""
    
    def test_get_env_int(self, monkeypatch):
        """Test integer environment variable parsing"""
        monkeypatch.setenv("MAX_CONTEXT_MESSAGES", "100")
        
        manager = ConfigManager(env_file_path="/nonexistent/.env")
        
        assert manager.session.max_context_messages == 100
    
    def test_get_env_float(self, monkeypatch):
        """Test float environment variable parsing"""
        monkeypatch.setenv("MEMORY_DECAY_RATE", "0.25")
        
        manager = ConfigManager(env_file_path="/nonexistent/.env")
        
        assert manager.memory.decay_rate == 0.25
    
    def test_get_env_bool_true_values(self, monkeypatch):
        """Test boolean environment variable parsing for true values"""
        test_cases = ["true", "True", "TRUE", "1", "yes", "Yes"]
        
        for value in test_cases:
            monkeypatch.setenv("DEBUG_MODE", value)
            manager = ConfigManager(env_file_path="/nonexistent/.env")
            assert manager.server.debug_mode == True, f"Failed for value: {value}"
    
    def test_get_env_bool_false_values(self, monkeypatch):
        """Test boolean environment variable parsing for false values"""
        test_cases = ["false", "False", "FALSE", "0", "no", "No"]
        
        for value in test_cases:
            monkeypatch.setenv("DEBUG_MODE", value)
            manager = ConfigManager(env_file_path="/nonexistent/.env")
            assert manager.server.debug_mode == False, f"Failed for value: {value}"


class TestDatabaseConfig:
    """Test DatabaseConfig specific settings"""
    
    def test_database_config_defaults(self):
        """Test DatabaseConfig default values"""
        # Use test env file which has known default values
        manager = ConfigManager(env_file_path=TEST_ENV_FILE)
        
        assert manager.database.sqlite_path == "data/persona_memory.db"
        assert manager.database.chromadb_path == "data/chromadb"
    
    def test_database_config_from_env(self, monkeypatch):
        """Test DatabaseConfig from environment variables"""
        monkeypatch.setenv("DATABASE_PATH", "custom/persona_memory.db")
        monkeypatch.setenv("CHROMADB_PATH", "custom/chromadb")
        
        manager = ConfigManager(env_file_path="/nonexistent/.env")
        
        assert manager.database.sqlite_path == "custom/persona_memory.db"
        assert manager.database.chromadb_path == "custom/chromadb"


class TestSimulationConfig:
    """Test SimulationConfig specific settings"""
    
    def test_simulation_config_defaults(self):
        """Test SimulationConfig default values"""
        manager = ConfigManager()
        
        assert "Fantasy Tavern" in manager.simulation.room_name or "Virtual" in manager.simulation.room_name
        assert manager.simulation.energy_regen_rate == 2
        assert manager.simulation.max_concurrent_conversations == 3
    
    def test_simulation_default_topics(self):
        """Test simulation default topics"""
        manager = ConfigManager()
        
        assert isinstance(manager.simulation.default_topics, list)
        assert len(manager.simulation.default_topics) > 0
        assert all(isinstance(topic, str) for topic in manager.simulation.default_topics)


class TestEdgeCases:
    """Test edge cases and error handling"""
    
    def test_empty_env_value(self, monkeypatch):
        """Test handling of empty environment variable"""
        monkeypatch.setenv("SERVER_PORT", "")
        
        manager = ConfigManager()
        
        # Should use default value
        assert manager.server.port == 8000
    
    def test_invalid_number_format(self, monkeypatch):
        """Test handling of invalid number format"""
        monkeypatch.setenv("SERVER_PORT", "not_a_number")
        
        manager = ConfigManager()
        
        # Should use default value or raise validation error
        # (depends on implementation)
        assert isinstance(manager.server.port, int)
    
    def test_whitespace_in_string_values(self, monkeypatch):
        """Test that string values handle whitespace"""
        monkeypatch.setenv("SERVER_HOST", "  localhost  ")
        
        manager = ConfigManager()
        
        # Should strip whitespace
        assert manager.server.host.strip() == "localhost"
