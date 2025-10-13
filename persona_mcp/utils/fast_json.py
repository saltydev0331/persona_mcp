"""
Fast JSON utility module with orjson optimization

Provides 2x faster JSON serialization/deserialization with orjson,
falling back to standard json if orjson is not available.
"""

try:
    import orjson
    HAS_ORJSON = True
except ImportError:
    import json
    HAS_ORJSON = False

import logging
from typing import Any, Dict, Union


logger = logging.getLogger(__name__)

if HAS_ORJSON:
    logger.info("🚀 Using orjson for 2x faster JSON performance")
else:
    logger.warning("📦 orjson not available, falling back to standard json")


def dumps(obj: Any, **kwargs) -> str:
    """
    Fast JSON serialization with orjson optimization.
    
    Args:
        obj: Object to serialize
        **kwargs: Additional arguments (for compatibility)
    
    Returns:
        JSON string
    """
    if HAS_ORJSON:
        # orjson returns bytes, convert to string
        # orjson is 2-5x faster than standard json
        return orjson.dumps(obj).decode('utf-8')
    else:
        # Fallback to standard json
        return json.dumps(obj, **kwargs)


def loads(s: Union[str, bytes]) -> Any:
    """
    Fast JSON deserialization with orjson optimization.
    
    Args:
        s: JSON string or bytes to deserialize
    
    Returns:
        Parsed object
    """
    if HAS_ORJSON:
        # orjson can handle both str and bytes
        if isinstance(s, str):
            s = s.encode('utf-8')
        return orjson.loads(s)
    else:
        # Standard json only handles strings
        if isinstance(s, bytes):
            s = s.decode('utf-8')
        return json.loads(s)


def dumps_bytes(obj: Any) -> bytes:
    """
    Fast JSON serialization returning bytes (orjson native format).
    
    Args:
        obj: Object to serialize
    
    Returns:
        JSON bytes
    """
    if HAS_ORJSON:
        return orjson.dumps(obj)
    else:
        return json.dumps(obj).encode('utf-8')


# Performance comparison utilities
class JSONBenchmark:
    """Benchmark JSON performance improvements"""
    
    @staticmethod
    def compare_performance(data: Dict[str, Any], iterations: int = 1000) -> Dict[str, float]:
        """
        Compare orjson vs standard json performance.
        
        Args:
            data: Test data to serialize/deserialize
            iterations: Number of test iterations
            
        Returns:
            Performance comparison results
        """
        import time
        
        results = {}
        
        # Test standard json
        start_time = time.time()
        for _ in range(iterations):
            json_str = json.dumps(data)
            json.loads(json_str)
        std_time = time.time() - start_time
        results['standard_json'] = std_time
        
        if HAS_ORJSON:
            # Test orjson
            start_time = time.time()
            for _ in range(iterations):
                json_bytes = orjson.dumps(data)
                orjson.loads(json_bytes)
            orjson_time = time.time() - start_time
            results['orjson'] = orjson_time
            results['speedup'] = std_time / orjson_time
            results['improvement_percent'] = ((std_time - orjson_time) / std_time) * 100
        
        return results


# Export standard interface
__all__ = ['dumps', 'loads', 'dumps_bytes', 'JSONBenchmark', 'HAS_ORJSON']


# Compatibility for drop-in replacement
class JSONDecodeError(Exception):
    """JSON decode error (for compatibility)"""
    pass


# Add standard json errors for compatibility
if HAS_ORJSON:
    # Map orjson errors to standard names
    try:
        import json as _std_json
        JSONDecodeError = _std_json.JSONDecodeError
    except:
        pass
else:
    JSONDecodeError = json.JSONDecodeError