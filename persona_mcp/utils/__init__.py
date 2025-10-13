"""
Utility modules for performance optimization
"""

from .fast_json import dumps, loads, JSONDecodeError, JSONBenchmark, HAS_ORJSON

__all__ = ['dumps', 'loads', 'JSONDecodeError', 'JSONBenchmark', 'HAS_ORJSON']