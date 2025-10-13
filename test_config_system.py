#!/usr/bin/env python3
"""
Test configuration system functionality
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from persona_mcp.config import get_config, init_config

def test_configuration():
    """Test the configuration system"""
    print("Testing Persona MCP Configuration System")
    print("=" * 50)
    
    # Test configuration loading
    try:
        config = get_config()
        print("✅ Configuration loaded successfully")
    except Exception as e:
        print(f"❌ Configuration loading failed: {e}")
        return False
    
    # Test configuration values
    print(f"Server: {config.server.host}:{config.server.port}")
    print(f"Ollama: {config.ollama.host} (model: {config.ollama.default_model})")
    print(f"Memory: {config.memory.importance_min}-{config.memory.importance_max}")
    print(f"Session: {config.session.max_context_messages} messages max")
    print(f"Persona: continue threshold = {config.persona.continue_threshold}")
    print(f"Database: {config.database.sqlite_path}")
    
    # Test configuration summary
    summary = config.get_summary()
    print("\nConfiguration Summary:")
    for section, values in summary.items():
        print(f"  {section}: {values}")
    
    # Test validation
    try:
        config._validate_configuration()
        print("✅ Configuration validation passed")
    except Exception as e:
        print(f"❌ Configuration validation failed: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = test_configuration()
    sys.exit(0 if success else 1)