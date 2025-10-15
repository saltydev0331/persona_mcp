"""
Shared database manager for Persona-MCP system.

Provides unified access to both SQLite (structured data) and ChromaDB (vector embeddings)
for both MCP server and PersonaAPI server to ensure operational parity.
"""

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from ..persistence import SQLiteManager, VectorMemoryManager
from ..logging import get_logger
from .models import Persona, Memory, Relationship, EmotionalState


class Base(DeclarativeBase):
    """Base class for SQLAlchemy models"""
    pass


class DatabaseManager:
    """Unified database manager for both SQLite and ChromaDB operations"""
    
    def __init__(self, sqlite_manager: Optional[SQLiteManager] = None, 
                 vector_manager: Optional[VectorMemoryManager] = None):
        self.sqlite = sqlite_manager or SQLiteManager()
        self.vector = vector_manager or VectorMemoryManager()
        self.logger = get_logger(__name__)
        
        # Create async engine for relationship data
        db_path = str(self.sqlite.db_path)
        self.engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
        self.async_session = async_sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )

    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get async database session"""
        async with self.async_session() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    async def initialize(self):
        """Initialize database systems"""
        # Initialize SQLite database
        await self.sqlite.initialize()
        self.logger.info("Database systems initialized successfully")
    
    async def close(self):
        """Close database connections"""
        if hasattr(self, 'engine'):
            await self.engine.dispose()
        await self.vector.close()
        self.logger.info("Database connections closed")

    async def initialize(self):
        """Initialize database systems"""
        # Initialize SQLite database
        await self.sqlite.initialize()
        self.logger.info("Database systems initialized successfully")

    async def close(self):
        """Close database connections"""
        # Note: SQLiteManager doesn't have a close method
        await self.vector.close()
        if hasattr(self, 'engine'):
            await self.engine.dispose()
        self.logger.info("DatabaseManager closed")

    async def health_check(self) -> Dict[str, Any]:
        """Check health of database components"""
        try:
            # Test SQLite connection by counting personas
            personas = await self.list_personas()
            sqlite_health = True
            sqlite_details = f"Connected, {len(personas)} personas"
        except Exception as e:
            sqlite_health = False
            sqlite_details = f"Error: {str(e)}"
        
        try:
            # Test vector memory connection
            stats = await self.vector.get_shared_memory_stats()
            vector_health = True
            vector_details = f"Connected, {stats.get('total_memories', 0)} memories"
        except Exception as e:
            vector_health = False
            vector_details = f"Error: {str(e)}"
        
        overall_health = sqlite_health and vector_health
        
        return {
            "overall": overall_health,
            "sqlite": {"healthy": sqlite_health, "details": sqlite_details},
            "vector": {"healthy": vector_health, "details": vector_details}
        }

    # Persona operations
    async def create_persona(self, persona_data: Dict[str, Any]) -> Persona:
        """Create a new persona"""
        persona = Persona(**persona_data)
        await self.sqlite.store_persona(persona.dict())
        self.logger.info(f"Created persona: {persona.name} ({persona.id})")
        return persona

    async def get_persona(self, persona_id: str) -> Optional[Persona]:
        """Get persona by ID"""
        persona_data = await self.sqlite.get_persona(persona_id)
        if persona_data:
            return Persona(**persona_data)
        return None

    async def get_persona_by_name(self, name: str) -> Optional[Persona]:
        """Get persona by name"""
        persona_data = await self.sqlite.get_persona_by_name(name)
        if persona_data:
            return Persona(**persona_data)
        return None

    async def list_personas(self) -> List[Persona]:
        """Get all personas"""
        personas_data = await self.sqlite.list_personas()
        return personas_data

    async def update_persona(self, persona_id: str, updates: Dict[str, Any]) -> bool:
        """Update persona data"""
        success = await self.sqlite.update_persona(persona_id, updates)
        if success:
            self.logger.info(f"Updated persona: {persona_id}")
        return success

    async def delete_persona(self, persona_id: str) -> bool:
        """Delete persona and all associated data"""
        # Delete from vector memory
        await self.vector.delete_persona_memories(persona_id)
        
        # Delete from SQLite
        success = await self.sqlite.delete_persona(persona_id)
        
        if success:
            self.logger.info(f"Deleted persona and all associated data: {persona_id}")
        
        return success

    # Memory operations
    async def store_memory(self, memory: Memory) -> bool:
        """Store memory in both vector and structured storage"""
        # Store in vector database
        vector_success = await self.vector.store_memory(
            persona_id=memory.persona_id,
            content=memory.content,
            memory_type=memory.memory_type,
            importance=memory.importance,
            metadata=memory.metadata
        )
        
        # Store in SQLite for structured queries
        sqlite_success = await self.sqlite.store_memory(memory.dict())
        
        success = vector_success and sqlite_success
        if success:
            self.logger.debug(f"Stored memory for persona {memory.persona_id}")
        
        return success

    async def search_memories(self, persona_id: str, query: str, 
                            n_results: int = 5, min_importance: float = 0.0) -> List[Memory]:
        """Search memories using vector similarity"""
        results = await self.vector.search_memories(
            persona_id=persona_id,
            query=query,
            n_results=n_results,
            min_importance=min_importance
        )
        
        # Convert to Memory objects
        memories = []
        for result in results:
            memory_data = result.get('metadata', {})
            memory_data['content'] = result.get('content', '')
            memory_data['id'] = result.get('id', '')
            memories.append(Memory(**memory_data))
        
        return memories

    async def get_memory_stats(self, persona_id: str) -> Dict[str, Any]:
        """Get memory statistics for a persona"""
        return await self.vector.get_memory_stats(persona_id)

    async def prune_memories(self, persona_id: str, max_memories: int = 1000) -> Dict[str, Any]:
        """Prune old/unimportant memories"""
        return await self.vector.prune_memories(persona_id, max_memories)

    # Relationship operations  
    async def get_relationship(self, persona1_id: str, persona2_id: str) -> Optional[Relationship]:
        """Get relationship between two personas"""
        relationship_data = await self.sqlite.get_relationship(persona1_id, persona2_id)
        if relationship_data:
            return Relationship(**relationship_data)
        return None

    async def create_relationship(self, relationship: Relationship) -> bool:
        """Create a new relationship"""
        success = await self.sqlite.create_relationship(relationship.dict())
        if success:
            self.logger.info(f"Created relationship: {relationship.persona1_id} <-> {relationship.persona2_id}")
        return success

    async def update_relationship(self, persona1_id: str, persona2_id: str, 
                                updates: Dict[str, Any]) -> bool:
        """Update relationship data"""
        success = await self.sqlite.update_relationship(persona1_id, persona2_id, updates)
        if success:
            self.logger.info(f"Updated relationship: {persona1_id} <-> {persona2_id}")
        return success

    async def list_relationships(self, persona_id: str) -> List[Relationship]:
        """Get all relationships for a persona"""
        relationships_data = await self.sqlite.get_persona_relationships(persona_id)
        return [Relationship(**r) for r in relationships_data]

    async def delete_relationship(self, persona1_id: str, persona2_id: str) -> bool:
        """Delete a relationship"""
        success = await self.sqlite.delete_relationship(persona1_id, persona2_id)
        if success:
            self.logger.info(f"Deleted relationship: {persona1_id} <-> {persona2_id}")
        return success

    # Emotional state operations
    async def get_emotional_state(self, persona_id: str) -> Optional[EmotionalState]:
        """Get emotional state for a persona"""
        state_data = await self.sqlite.get_emotional_state(persona_id)
        if state_data:
            return EmotionalState(**state_data)
        return None

    async def update_emotional_state(self, persona_id: str, state: EmotionalState) -> bool:
        """Update emotional state for a persona"""
        success = await self.sqlite.update_emotional_state(persona_id, state.dict())
        if success:
            self.logger.debug(f"Updated emotional state for persona {persona_id}")
        return success

    # System operations
    async def get_system_stats(self) -> Dict[str, Any]:
        """Get overall system statistics"""
        sqlite_stats = await self.sqlite.get_stats()
        vector_stats = await self.vector.get_stats()
        
        return {
            "personas": sqlite_stats.get("personas", 0),
            "memories": vector_stats.get("total_memories", 0),
            "relationships": sqlite_stats.get("relationships", 0),
            "database_size": sqlite_stats.get("size_mb", 0),
            "vector_collections": vector_stats.get("collections", 0)
        }