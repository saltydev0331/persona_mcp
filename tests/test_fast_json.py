"""
Unit tests for persona_mcp.utils.fast_json module

Tests JSON serialization/deserialization with orjson optimization
and fallback to standard json.
"""

import pytest
from datetime import datetime, timezone
from typing import Dict, Any

from persona_mcp.utils.fast_json import (
    dumps,
    loads,
    dumps_bytes,
    JSONBenchmark,
    HAS_ORJSON,
    JSONDecodeError
)


class TestBasicSerialization:
    """Test basic JSON serialization/deserialization"""
    
    def test_dumps_simple_dict(self):
        """Test serializing a simple dictionary"""
        data = {"key": "value", "number": 42}
        result = dumps(data)
        
        assert isinstance(result, str)
        assert "key" in result
        assert "value" in result
        assert "42" in result
    
    def test_dumps_nested_dict(self):
        """Test serializing nested dictionaries"""
        data = {
            "level1": {
                "level2": {
                    "level3": "deep value"
                }
            }
        }
        result = dumps(data)
        
        assert isinstance(result, str)
        parsed = loads(result)
        assert parsed["level1"]["level2"]["level3"] == "deep value"
    
    def test_dumps_list(self):
        """Test serializing lists"""
        data = [1, 2, 3, "four", {"five": 5}]
        result = dumps(data)
        
        assert isinstance(result, str)
        parsed = loads(result)
        assert parsed == data
    
    def test_dumps_empty(self):
        """Test serializing empty structures"""
        assert dumps({}) == "{}"
        assert dumps([]) == "[]"
        assert dumps("") == '""'
    
    def test_dumps_none(self):
        """Test serializing None"""
        result = dumps(None)
        assert result == "null"
    
    def test_dumps_boolean(self):
        """Test serializing booleans"""
        assert "true" in dumps(True).lower()
        assert "false" in dumps(False).lower()
    
    def test_dumps_numbers(self):
        """Test serializing various number types"""
        assert dumps(42) == "42"
        assert dumps(3.14) == "3.14"
        assert dumps(0) == "0"
        assert dumps(-100) == "-100"


class TestDeserialization:
    """Test JSON deserialization"""
    
    def test_loads_from_string(self):
        """Test deserializing from string"""
        json_str = '{"key": "value", "number": 42}'
        result = loads(json_str)
        
        assert isinstance(result, dict)
        assert result["key"] == "value"
        assert result["number"] == 42
    
    def test_loads_from_bytes(self):
        """Test deserializing from bytes"""
        json_bytes = b'{"key": "value"}'
        result = loads(json_bytes)
        
        assert isinstance(result, dict)
        assert result["key"] == "value"
    
    def test_loads_list(self):
        """Test deserializing lists"""
        json_str = '[1, 2, 3, "four"]'
        result = loads(json_str)
        
        assert isinstance(result, list)
        assert result == [1, 2, 3, "four"]
    
    def test_loads_nested(self):
        """Test deserializing nested structures"""
        json_str = '{"a": {"b": {"c": 123}}}'
        result = loads(json_str)
        
        assert result["a"]["b"]["c"] == 123
    
    def test_loads_invalid_json(self):
        """Test that invalid JSON raises an error"""
        with pytest.raises((JSONDecodeError, ValueError, Exception)):
            loads("{invalid json}")
    
    def test_loads_empty_string(self):
        """Test that empty string raises an error"""
        with pytest.raises((JSONDecodeError, ValueError, Exception)):
            loads("")


class TestDumpsBytes:
    """Test dumps_bytes function"""
    
    def test_dumps_bytes_returns_bytes(self):
        """Test that dumps_bytes returns bytes"""
        data = {"key": "value"}
        result = dumps_bytes(data)
        
        assert isinstance(result, bytes)
    
    def test_dumps_bytes_valid_json(self):
        """Test that dumps_bytes produces valid JSON"""
        data = {"key": "value", "number": 42}
        result = dumps_bytes(data)
        
        # Should be deserializable
        parsed = loads(result)
        assert parsed == data
    
    def test_dumps_bytes_complex_data(self):
        """Test dumps_bytes with complex data"""
        data = {
            "list": [1, 2, 3],
            "nested": {"a": "b"},
            "null": None,
            "bool": True
        }
        result = dumps_bytes(data)
        
        assert isinstance(result, bytes)
        parsed = loads(result)
        assert parsed == data


class TestRoundTrip:
    """Test serialization/deserialization round trips"""
    
    def test_roundtrip_dict(self):
        """Test dict round trip"""
        original = {"key": "value", "number": 42, "nested": {"a": 1}}
        serialized = dumps(original)
        deserialized = loads(serialized)
        
        assert deserialized == original
    
    def test_roundtrip_list(self):
        """Test list round trip"""
        original = [1, "two", 3.0, None, True, {"key": "value"}]
        serialized = dumps(original)
        deserialized = loads(serialized)
        
        assert deserialized == original
    
    def test_roundtrip_unicode(self):
        """Test Unicode string round trip"""
        original = {"emoji": "🎉", "chinese": "你好", "arabic": "مرحبا"}
        serialized = dumps(original)
        deserialized = loads(serialized)
        
        assert deserialized == original
    
    def test_roundtrip_bytes_format(self):
        """Test round trip with bytes"""
        original = {"test": "data"}
        bytes_serialized = dumps_bytes(original)
        deserialized = loads(bytes_serialized)
        
        assert deserialized == original


class TestEdgeCases:
    """Test edge cases and special scenarios"""
    
    def test_special_characters(self):
        """Test handling of special characters"""
        data = {
            "quotes": 'He said "hello"',
            "newline": "line1\nline2",
            "tab": "col1\tcol2",
            "backslash": "path\\to\\file"
        }
        serialized = dumps(data)
        deserialized = loads(serialized)
        
        assert deserialized == data
    
    def test_large_numbers(self):
        """Test handling of large numbers"""
        data = {
            "big_int": 9999999999999999,
            "big_float": 3.141592653589793
        }
        serialized = dumps(data)
        deserialized = loads(serialized)
        
        assert deserialized["big_int"] == data["big_int"]
        assert abs(deserialized["big_float"] - data["big_float"]) < 0.0000001
    
    def test_empty_structures(self):
        """Test empty structures"""
        test_cases = [
            {},
            [],
            {"empty_dict": {}, "empty_list": []},
        ]
        
        for data in test_cases:
            serialized = dumps(data)
            deserialized = loads(serialized)
            assert deserialized == data
    
    def test_deeply_nested(self):
        """Test deeply nested structures"""
        # Create a deeply nested structure
        data = {"level": 0}
        current = data
        for i in range(1, 20):
            current["nested"] = {"level": i}
            current = current["nested"]
        
        serialized = dumps(data)
        deserialized = loads(serialized)
        
        # Verify structure is preserved
        assert deserialized["level"] == 0
        current = deserialized
        for i in range(1, 20):
            assert "nested" in current
            assert current["nested"]["level"] == i
            current = current["nested"]


class TestJSONBenchmark:
    """Test JSON benchmarking utilities"""
    
    def test_compare_performance_runs(self):
        """Test that performance comparison runs without error"""
        data = {"key": "value", "number": 42, "list": [1, 2, 3]}
        results = JSONBenchmark.compare_performance(data, iterations=100)
        
        assert isinstance(results, dict)
        assert "standard_json" in results
        assert results["standard_json"] >= 0  # Allow zero for very fast operations
    
    def test_compare_performance_with_orjson(self):
        """Test performance comparison when orjson is available"""
        data = {"test": "data"}
        results = JSONBenchmark.compare_performance(data, iterations=10)
        
        if HAS_ORJSON:
            assert "orjson" in results
            assert "speedup" in results
            assert "improvement_percent" in results
            assert results["speedup"] > 0
    
    def test_compare_performance_complex_data(self):
        """Test benchmarking with complex data"""
        data = {
            "users": [
                {"id": i, "name": f"User{i}", "active": i % 2 == 0}
                for i in range(100)
            ]
        }
        results = JSONBenchmark.compare_performance(data, iterations=5)
        
        assert results["standard_json"] > 0


class TestCompatibility:
    """Test compatibility features"""
    
    def test_has_orjson_flag(self):
        """Test that HAS_ORJSON flag is a boolean"""
        assert isinstance(HAS_ORJSON, bool)
    
    def test_json_decode_error_exists(self):
        """Test that JSONDecodeError is available"""
        assert JSONDecodeError is not None
        # Should be catchable when raised by loads()
        with pytest.raises(JSONDecodeError):
            loads("{invalid}")


class TestRealWorldData:
    """Test with real-world-like data structures"""
    
    def test_persona_like_data(self):
        """Test with persona-like data structure"""
        persona_data = {
            "id": "persona_123",
            "name": "Test Persona",
            "personality_traits": {
                "openness": 0.8,
                "conscientiousness": 0.6,
                "extraversion": 0.7
            },
            "topic_preferences": {
                "technology": 90,
                "sports": 30,
                "arts": 75
            },
            "interaction_state": {
                "social_energy": 100,
                "available_time": 300,
                "cooldown_until": 0.0
            }
        }
        
        serialized = dumps(persona_data)
        deserialized = loads(serialized)
        
        assert deserialized == persona_data
        assert deserialized["personality_traits"]["openness"] == 0.8
    
    def test_conversation_like_data(self):
        """Test with conversation-like data structure"""
        conversation_data = {
            "id": "conv_456",
            "participants": ["persona_1", "persona_2"],
            "messages": [
                {
                    "role": "user",
                    "content": "Hello!",
                    "timestamp": "2025-10-14T10:30:00Z"
                },
                {
                    "role": "assistant",
                    "content": "Hi there!",
                    "timestamp": "2025-10-14T10:30:05Z"
                }
            ],
            "turn_count": 2,
            "continue_score": 85.5
        }
        
        serialized = dumps(conversation_data)
        deserialized = loads(serialized)
        
        assert deserialized == conversation_data
        assert len(deserialized["messages"]) == 2
    
    def test_memory_like_data(self):
        """Test with memory-like data structure"""
        memory_data = {
            "id": "mem_789",
            "persona_id": "persona_123",
            "content": "Had an interesting conversation about AI ethics",
            "importance": 0.85,
            "emotional_valence": 0.6,
            "metadata": {
                "tags": ["conversation", "philosophy", "AI"],
                "duration": 300,
                "participants": 2
            }
        }
        
        serialized = dumps(memory_data)
        deserialized = loads(serialized)
        
        assert deserialized == memory_data
        assert deserialized["importance"] == 0.85
