"""
Centralized logging configuration for Persona MCP Server
=====================================================

Provides standardized logging with:
- Consistent logger instances across all modules
- Structured JSON logging for production
- Request/response correlation IDs  
- Configurable log levels and formats
- Automatic cleanup of debug code
"""

import logging
import logging.config
import json
import sys
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from contextvars import ContextVar
from pathlib import Path

from ..config import get_config

# Context variable for correlation ID tracking
correlation_id: ContextVar[Optional[str]] = ContextVar('correlation_id', default=None)


class CorrelationFilter(logging.Filter):
    """Add correlation ID to log records for request tracing"""
    
    def filter(self, record):
        record.correlation_id = correlation_id.get() or 'none'
        return True


class StructuredFormatter(logging.Formatter):
    """JSON structured logging formatter for production monitoring"""
    
    def format(self, record):
        log_entry = {
            'timestamp': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
            'correlation_id': getattr(record, 'correlation_id', 'none')
        }
        
        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        
        # Add extra fields from record
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 
                          'filename', 'module', 'lineno', 'funcName', 'created', 
                          'msecs', 'relativeCreated', 'thread', 'threadName', 
                          'processName', 'process', 'message', 'exc_info', 
                          'exc_text', 'stack_info', 'correlation_id']:
                log_entry[key] = value
        
        return json.dumps(log_entry)


class ConsoleFormatter(logging.Formatter):
    """Human-readable console formatter for development"""
    
    # Color codes
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green  
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
        'RESET': '\033[0m'      # Reset
    }
    
    def format(self, record):
        # Get correlation ID
        corr_id = getattr(record, 'correlation_id', 'none')
        corr_display = f"[{corr_id[:8]}]" if corr_id != 'none' else ""
        
        # Color the level name
        color = self.COLORS.get(record.levelname, '')
        reset = self.COLORS['RESET']
        colored_level = f"{color}{record.levelname:8s}{reset}"
        
        # Format the message
        timestamp = datetime.fromtimestamp(record.created).strftime('%H:%M:%S.%f')[:-3]
        
        return f"{timestamp} {colored_level} {record.name:30s} {corr_display} {record.getMessage()}"


class LoggingManager:
    """
    Centralized logging configuration manager
    
    Handles:
    - Logger creation with consistent naming
    - Configuration from environment settings
    - Correlation ID management for request tracing
    - Structured vs console output selection
    """
    
    def __init__(self):
        self.config = get_config()
        self.loggers: Dict[str, logging.Logger] = {}
        self._setup_root_logging()
    
    def _setup_root_logging(self):
        """Configure root logging with appropriate handlers and formatters"""
        
        # Determine log level from config
        log_level_str = getattr(self.config.server, 'log_level', 'INFO')
        log_level = getattr(logging, log_level_str.upper(), logging.INFO)
        
        # Clear existing handlers
        root_logger = logging.getLogger()
        root_logger.handlers.clear()
        root_logger.setLevel(log_level)
        
        # Add correlation filter to all handlers
        correlation_filter = CorrelationFilter()
        
        # Console handler with colored output for development
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)
        
        if self.config.server.debug_mode:
            console_formatter = ConsoleFormatter()
        else:
            # Use structured JSON logging in production
            console_formatter = StructuredFormatter()
        
        console_handler.setFormatter(console_formatter)
        console_handler.addFilter(correlation_filter)
        root_logger.addHandler(console_handler)
        
        # File handler if configured
        log_file = getattr(self.config.server, 'log_file', None)
        if log_file:
            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            
            file_handler = logging.FileHandler(log_path)
            file_handler.setLevel(log_level)
            
            # Always use structured format for file output
            file_formatter = StructuredFormatter()
            file_handler.setFormatter(file_formatter)
            file_handler.addFilter(correlation_filter)
            root_logger.addHandler(file_handler)
        
        # Suppress noisy third-party loggers
        self._configure_third_party_loggers()
    
    def _configure_third_party_loggers(self):
        """Suppress verbose third-party logging"""
        suppressed_loggers = [
            'aiohttp.access',
            'aiohttp.server', 
            'aiohttp.web',
            'chromadb',
            'httpcore',
            'httpx',
            'asyncio',
            'websockets',
            'sqlite3'
        ]
        
        for logger_name in suppressed_loggers:
            logging.getLogger(logger_name).setLevel(logging.WARNING)
    
    def get_logger(self, name: str) -> logging.Logger:
        """
        Get a standardized logger instance
        
        Args:
            name: Logger name (typically __name__ from calling module)
            
        Returns:
            Configured logger instance
        """
        if name not in self.loggers:
            logger = logging.getLogger(name)
            self.loggers[name] = logger
        
        return self.loggers[name]
    
    def set_correlation_id(self, corr_id: Optional[str] = None) -> str:
        """
        Set correlation ID for request tracing
        
        Args:
            corr_id: Optional correlation ID. If None, generates a new UUID
            
        Returns:
            The correlation ID that was set
        """
        if corr_id is None:
            corr_id = str(uuid.uuid4())
        
        correlation_id.set(corr_id)
        return corr_id
    
    def clear_correlation_id(self):
        """Clear the current correlation ID"""
        correlation_id.set(None)
    
    def get_correlation_id(self) -> Optional[str]:
        """Get the current correlation ID"""
        return correlation_id.get()


# Global logging manager instance
_logging_manager: Optional[LoggingManager] = None


def get_logger(name: str) -> logging.Logger:
    """
    Get a standardized logger instance
    
    Usage:
        from persona_mcp.logging import get_logger
        logger = get_logger(__name__)
        logger.info("This is a test message")
    
    Args:
        name: Logger name (typically __name__ from calling module)
        
    Returns:
        Configured logger instance
    """
    global _logging_manager
    if _logging_manager is None:
        _logging_manager = LoggingManager()
    
    return _logging_manager.get_logger(name)


def set_correlation_id(corr_id: Optional[str] = None) -> str:
    """
    Set correlation ID for request tracing
    
    Args:
        corr_id: Optional correlation ID. If None, generates a new UUID
        
    Returns:
        The correlation ID that was set
    """
    global _logging_manager
    if _logging_manager is None:
        _logging_manager = LoggingManager()
    
    return _logging_manager.set_correlation_id(corr_id)


def clear_correlation_id():
    """Clear the current correlation ID"""
    global _logging_manager
    if _logging_manager is not None:
        _logging_manager.clear_correlation_id()


def get_correlation_id() -> Optional[str]:
    """Get the current correlation ID"""
    global _logging_manager
    if _logging_manager is not None:
        return _logging_manager.get_correlation_id()
    return None


# Convenience function for WebSocket connection correlation
def with_connection_id(connection_id: str):
    """
    Context manager for setting correlation ID based on WebSocket connection
    
    Usage:
        with with_connection_id(connection_id):
            logger.info("Processing WebSocket message")
    """
    from contextlib import contextmanager
    
    @contextmanager
    def correlation_context():
        old_id = get_correlation_id()
        set_correlation_id(connection_id)
        try:
            yield
        finally:
            if old_id:
                set_correlation_id(old_id)
            else:
                clear_correlation_id()
    
    return correlation_context()


# Migration helpers for converting existing logging
def replace_print_with_logger(func):
    """
    Decorator to automatically replace print() calls with logger calls
    
    Usage:
        @replace_print_with_logger
        def some_function():
            print("This will be logged instead")
    """
    import functools
    
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        logger = get_logger(func.__module__)
        
        # Monkey patch print for this function
        original_print = print
        def log_print(*args, **kwargs):
            message = ' '.join(str(arg) for arg in args)
            logger.info(message)
        
        # Temporarily replace print
        import builtins
        builtins.print = log_print
        
        try:
            return func(*args, **kwargs)
        finally:
            builtins.print = original_print
    
    return wrapper