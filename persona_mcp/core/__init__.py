"""
Shared core foundation for Persona-MCP system.

This module provides the shared components used by both MCP server and PersonaAPI server
to ensure operational parity and clean separation of concerns.

Components:
- models: Shared data models (Persona, Memory, Relationship, etc.)
- database: Unified database manager with SQLite and ChromaDB integration
- memory: Shared memory management system
- config: Unified configuration management
"""

from .models import (
    Persona,
    PersonaBase,
    PersonaInteractionState,
    Memory,
    Relationship,
    RelationshipType,
    EmotionalState,
    ConversationContext,
    ConversationTurn,
    MCPRequest,
    MCPResponse,
    MCPError,
    SimulationState,
    Priority
)

from .database import DatabaseManager
from .memory import MemoryManager
from .config import ConfigManager

__all__ = [
    # Data models
    "Persona",
    "PersonaBase", 
    "PersonaInteractionState",
    "Memory",
    "Relationship",
    "RelationshipType",
    "EmotionalState",
    "ConversationContext",
    "ConversationTurn",
    "MCPRequest",
    "MCPResponse",
    "MCPError",
    "SimulationState",
    "Priority",
    
    # Core managers
    "DatabaseManager",
    "MemoryManager",
    "ConfigManager"
]