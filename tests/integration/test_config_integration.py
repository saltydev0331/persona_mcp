#!/usr/bin/env python3
"""
Integration tests for configuration system functionality

Tests the configuration loading, validation, and environment variable handling.
"""

import pytest
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

from persona_mcp.config.manager import ConfigManager, get_config, init_config, DecayMode


class TestConfigurationSystem:
    """Test configuration system functionality"""
    
    def test_config_loading_default(self):
        """Test that configuration loads with default values"""
        config = get_config()
        
        # Test that config object exists and has expected sections
        assert hasattr(config, 'server'), "Config should have server section"
        assert hasattr(config, 'ollama'), "Config should have ollama section"
        assert hasattr(config, 'memory'), "Config should have memory section"
        assert hasattr(config, 'session'), "Config should have session section"
        assert hasattr(config, 'persona'), "Config should have persona section"
        assert hasattr(config, 'database'), "Config should have database section"
        assert hasattr(config, 'conversation'), "Config should have conversation section"
        assert hasattr(config, 'simulation'), "Config should have simulation section"
    
    def test_config_server_values(self):
        """Test server configuration values"""
        config = get_config()
        
        # Server configuration - use correct attribute names
        assert isinstance(config.server.host, str)
        assert isinstance(config.server.port, int)
        assert 1 <= config.server.port <= 65535
        assert isinstance(config.server.debug_mode, bool)  # Correct attribute name
        assert isinstance(config.server.websocket_timeout, int)
        assert isinstance(config.server.log_level, str)
    
    def test_config_ollama_values(self):
        """Test Ollama configuration values"""
        config = get_config()
        
        # Ollama configuration
        assert isinstance(config.ollama.host, str)
        assert isinstance(config.ollama.default_model, str)
        assert len(config.ollama.default_model) > 0
        assert isinstance(config.ollama.timeout_seconds, int)  # Correct attribute name
        assert config.ollama.timeout_seconds > 0
        assert isinstance(config.ollama.max_retries, int)
    
    def test_config_memory_values(self):
        """Test memory configuration values"""
        config = get_config()
        
        # Memory configuration - use correct attribute names
        assert isinstance(config.memory.importance_min, float)
        assert isinstance(config.memory.importance_max, float)
        assert 0.0 <= config.memory.importance_min <= 1.0
        assert 0.0 <= config.memory.importance_max <= 1.0
        assert config.memory.importance_min <= config.memory.importance_max
        
        assert isinstance(config.memory.max_memories_per_persona, int)  # Correct attribute name
        assert config.memory.max_memories_per_persona > 0
        
        # Test decay mode enum
        assert isinstance(config.memory.decay_mode, DecayMode)
        assert isinstance(config.memory.decay_rate, float)
        assert config.memory.decay_rate > 0
    
    def test_config_session_values(self):
        """Test session configuration values"""
        config = get_config()
        
        # Session configuration  
        assert isinstance(config.session.max_context_messages, int)
        assert config.session.max_context_messages > 0
        
        assert isinstance(config.session.context_summary_threshold, int)
        assert config.session.context_summary_threshold > 0
        
        assert isinstance(config.session.session_timeout_hours, int)
        assert config.session.session_timeout_hours > 0
        
        assert isinstance(config.session.tick_interval_seconds, int)
        assert config.session.tick_interval_seconds > 0
    
    def test_config_persona_values(self):
        """Test persona configuration values"""
        config = get_config()
        
        # Persona configuration - use correct attribute names
        assert isinstance(config.persona.continue_threshold, int)  # It's an int, not float
        assert 0 <= config.persona.continue_threshold <= 100
        
        assert isinstance(config.persona.default_charisma, int)
        assert isinstance(config.persona.default_intelligence, int)
        assert isinstance(config.persona.default_social_rank, str)
        assert isinstance(config.persona.default_cooldown_seconds, int)
    
    def test_config_database_values(self):
        """Test database configuration values"""
        config = get_config()
        
        # Database configuration - use correct attribute names
        assert isinstance(config.database.sqlite_path, str)
        assert len(config.database.sqlite_path) > 0
        
        assert isinstance(config.database.chromadb_path, str)  # Correct attribute name
        assert len(config.database.chromadb_path) > 0
        
        # Check that we get the expected values from .env file
        assert "data/" in config.database.sqlite_path  # Should contain data path
        assert "data/" in config.database.chromadb_path  # Should contain data path
        
        assert isinstance(config.database.enable_wal_mode, bool)
        assert isinstance(config.database.connection_timeout, int)
    
    def test_config_validation(self):
        """Test configuration validation"""
        config = get_config()
        
        # Should not raise exception
        try:
            config._validate_configuration()
        except Exception as e:
            pytest.fail(f"Configuration validation failed: {e}")
    
    def test_config_summary(self):
        """Test configuration summary generation"""
        config = get_config()
        
        summary = config.get_summary()
        assert isinstance(summary, dict)
        
        # Should have all major sections in summary
        expected_sections = ["server", "ollama", "memory", "session"]
        for section in expected_sections:
            assert section in summary, f"Summary missing section: {section}"
            assert isinstance(summary[section], dict), f"Section {section} should be dict"
    
    def test_config_environment_override(self):
        """Test that configuration loads from .env file as expected"""
        config = get_config()
        
        # Test that values from .env file are loaded correctly
        # (These are the actual values from the .env file in the repo)
        assert config.server.host == "localhost"  # From .env file
        assert config.server.port == 8000  # From .env file
        assert config.ollama.default_model == "llama3.1:8b"  # From .env file
        assert config.database.chromadb_path == "data/vector_memory"  # From .env file
        
        # Test that memory weights from .env are loaded correctly
        assert config.memory.content_weight == 0.3
        assert config.memory.engagement_weight == 0.2
        assert config.memory.persona_weight == 0.15
        assert config.memory.temporal_weight == 0.05
        assert config.memory.relationship_weight == 0.1
        assert config.memory.recency_weight == 0.2
    
    def test_config_singleton_behavior(self):
        """Test that get_config returns the same instance"""
        config1 = get_config()
        config2 = get_config()
        
        # Should be the same object
        assert config1 is config2, "get_config() should return singleton instance"
    
    def test_config_conversation_settings(self):
        """Test conversation configuration values"""
        config = get_config()
        
        # Conversation configuration
        assert hasattr(config, 'conversation'), "Should have conversation config"
        
        conv_config = config.conversation
        assert isinstance(conv_config.max_time_score, float)
        assert isinstance(conv_config.max_topic_score, float) 
        assert isinstance(conv_config.max_social_score, float)
        assert isinstance(conv_config.max_resource_score, float)
        
        # All scores should be positive
        assert conv_config.max_time_score > 0
        assert conv_config.max_topic_score > 0
        assert conv_config.max_social_score > 0
        assert conv_config.max_resource_score > 0
        
        # Test status hierarchy
        assert isinstance(conv_config.status_hierarchy, dict)
        assert "commoner" in conv_config.status_hierarchy
        assert "royalty" in conv_config.status_hierarchy
    
    def test_config_simulation_settings(self):
        """Test simulation configuration values"""
        config = get_config()
        
        # Simulation configuration
        assert hasattr(config, 'simulation'), "Should have simulation config"
        
        sim_config = config.simulation
        assert isinstance(sim_config.room_name, str)
        assert isinstance(sim_config.room_description, str)
        assert isinstance(sim_config.default_topics, list)
        assert len(sim_config.default_topics) > 0
        assert isinstance(sim_config.energy_regen_rate, int)
        assert sim_config.energy_regen_rate > 0
    
    @patch.dict(os.environ, {"SERVER_PORT": "invalid"})
    def test_config_invalid_environment_handling(self):
        """Test handling of invalid environment variables"""
        # Should handle invalid values gracefully
        try:
            config_manager = ConfigManager()
            # Should fall back to default port since "invalid" can't be parsed as int
            assert isinstance(config_manager.server.port, int)
            assert 1 <= config_manager.server.port <= 65535
        except Exception as e:
            # If it raises an exception, it should be informative
            assert "port" in str(e).lower(), f"Error should mention port: {e}"
    
    def test_memory_weights_sum_validation(self):
        """Test that memory scoring weights sum to 1.0"""
        config = get_config()
        
        total_weights = (
            config.memory.content_weight +
            config.memory.engagement_weight +
            config.memory.persona_weight +
            config.memory.temporal_weight +
            config.memory.relationship_weight +
            config.memory.recency_weight
        )
        
        # Should be approximately 1.0 (within tolerance)
        assert abs(total_weights - 1.0) <= 0.01, f"Weights sum to {total_weights}, should be 1.0"


@pytest.mark.integration
class TestConfigurationIntegration:
    """Integration tests for configuration system"""
    
    def test_config_with_custom_env_file(self):
        """Test configuration with custom environment file"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            # Create custom env file with different values
            f.write("SERVER_HOST=custom.test.host\n")
            f.write("SERVER_PORT=9999\n")
            f.write("DEFAULT_MODEL=custom-model\n")
            f.write("DATABASE_PATH=custom/test.db\n")
            f.write("CHROMADB_PATH=custom/chromadb\n")
            # Include memory weights that sum to 1.0 to pass validation
            f.write("MEMORY_CONTENT_WEIGHT=0.3\n")
            f.write("MEMORY_ENGAGEMENT_WEIGHT=0.2\n")
            f.write("MEMORY_PERSONA_WEIGHT=0.15\n")
            f.write("MEMORY_TEMPORAL_WEIGHT=0.05\n")
            f.write("MEMORY_RELATIONSHIP_WEIGHT=0.1\n")
            f.write("MEMORY_RECENCY_WEIGHT=0.2\n")
            custom_env_path = f.name
        
        try:
            # Create config manager with custom env file
            config_manager = ConfigManager(env_file_path=custom_env_path)
            
            # Test that custom values are loaded
            assert config_manager.server.host == "custom.test.host"
            assert config_manager.server.port == 9999
            assert config_manager.ollama.default_model == "custom-model"
            assert config_manager.database.sqlite_path == "custom/test.db"
            assert config_manager.database.chromadb_path == "custom/chromadb"
            
        finally:
            os.unlink(custom_env_path)
    
    def test_config_initialization_with_init(self):
        """Test configuration initialization using init_config"""
        # Should be able to initialize without errors
        try:
            init_config()
        except Exception as e:
            pytest.fail(f"Configuration initialization failed: {e}")
        
        # Should still be able to get config after init
        config = get_config()
        assert config is not None
    
    def test_config_decay_mode_validation(self):
        """Test decay mode enum validation"""
        config = get_config()
        
        # Should be a valid DecayMode enum
        assert config.memory.decay_mode in DecayMode
        assert isinstance(config.memory.decay_mode, DecayMode)
        
        # Test with environment override
        with patch.dict(os.environ, {"MEMORY_DECAY_MODE": "linear"}):
            config_manager = ConfigManager()
            assert config_manager.memory.decay_mode == DecayMode.LINEAR
    
    def test_config_boolean_parsing(self):
        """Test boolean environment variable parsing"""
        # Test various boolean representations
        test_cases = [
            ("true", True),
            ("True", True),
            ("TRUE", True),
            ("1", True),
            ("yes", True),
            ("on", True),
            ("false", False),
            ("False", False),
            ("FALSE", False),
            ("0", False),
            ("no", False),
            ("off", False),
        ]
        
        for env_value, expected in test_cases:
            with patch.dict(os.environ, {"DEBUG_MODE": env_value}):
                config_manager = ConfigManager()
                assert config_manager.server.debug_mode == expected, f"Failed for env_value: {env_value}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])