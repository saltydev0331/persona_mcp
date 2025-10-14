"""
Database integration layer for the relationship system.

Provides unified access to both SQLite (structured data) and ChromaDB (vector embeddings)
for relationship and emotional state management.
"""

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from .persistence import SQLiteManager, VectorMemoryManager
from .logging import get_logger


class Base(DeclarativeBase):
    """Base class for SQLAlchemy models"""
    pass


class DatabaseManager:
    """Unified database manager for both SQLite and ChromaDB operations"""
    
    def __init__(self, sqlite_manager: SQLiteManager, vector_manager: VectorMemoryManager):
        self.sqlite = sqlite_manager
        self.vector = vector_manager
        self.logger = get_logger(__name__)
        
        # Create async engine for relationship data
        self.engine = create_async_engine(
            f"sqlite+aiosqlite:///{sqlite_manager.db_path}",
            echo=False
        )
        self.async_session = async_sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )
    
    async def initialize(self):
        """Initialize both SQLite and ChromaDB"""
        await self.sqlite.initialize()
        # Vector manager initialization handled separately
        
        # Create relationship tables if they don't exist
        await self._create_relationship_tables()
    
    async def _create_relationship_tables(self):
        """Create relationship-specific tables in SQLite"""
        import aiosqlite
        
        async with aiosqlite.connect(self.sqlite.db_path) as db:
            # Relationships table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS relationships (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    persona1_id TEXT NOT NULL,
                    persona2_id TEXT NOT NULL,
                    affinity REAL DEFAULT 0.5,
                    trust REAL DEFAULT 0.5,
                    respect REAL DEFAULT 0.5,
                    intimacy REAL DEFAULT 0.5,
                    relationship_type TEXT DEFAULT 'stranger',
                    interaction_count INTEGER DEFAULT 0,
                    total_interaction_time REAL DEFAULT 0.0,
                    first_meeting TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_interaction TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(persona1_id, persona2_id),
                    FOREIGN KEY (persona1_id) REFERENCES personas (id),
                    FOREIGN KEY (persona2_id) REFERENCES personas (id)
                )
            """)
            
            # Emotional states table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS emotional_states (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    persona_id TEXT NOT NULL UNIQUE,
                    mood REAL DEFAULT 0.5,
                    energy_level REAL DEFAULT 0.7,
                    stress_level REAL DEFAULT 0.3,
                    curiosity REAL DEFAULT 0.6,
                    social_battery REAL DEFAULT 0.8,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (persona_id) REFERENCES personas (id)
                )
            """)
            
            # Interaction history table for detailed tracking
            await db.execute("""
                CREATE TABLE IF NOT EXISTS interaction_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    persona1_id TEXT NOT NULL,
                    persona2_id TEXT NOT NULL,
                    interaction_quality REAL NOT NULL,
                    duration_minutes REAL DEFAULT 5.0,
                    context TEXT,
                    emotional_impact TEXT, -- JSON of emotional changes
                    memory_references TEXT, -- JSON of related memory IDs
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (persona1_id) REFERENCES personas (id),
                    FOREIGN KEY (persona2_id) REFERENCES personas (id)
                )
            """)
            
            # Create indexes for performance
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_relationships_personas 
                ON relationships (persona1_id, persona2_id)
            """)
            
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_emotional_states_persona 
                ON emotional_states (persona_id)
            """)
            
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_interaction_history_personas 
                ON interaction_history (persona1_id, persona2_id, timestamp)
            """)
            
            await db.commit()


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Get async database session for relationship operations"""
    # This is a placeholder - in practice you'd get this from your app's database manager
    # For now, we'll work directly with SQLite
    import aiosqlite
    from .persistence import SQLiteManager
    
    # Create a simple session-like object for compatibility
    class SimpleSession:
        def __init__(self, db_path):
            self.db_path = db_path
            self._connection = None
            
        async def __aenter__(self):
            self._connection = await aiosqlite.connect(self.db_path)
            return self
            
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            if self._connection:
                await self._connection.close()
                
        async def execute(self, query, params=None):
            if params is None:
                params = []
            return await self._connection.execute(query, params)
            
        async def fetchall(self, query, params=None):
            if params is None:
                params = []
            cursor = await self._connection.execute(query, params)
            return await cursor.fetchall()
            
        async def fetchone(self, query, params=None):
            if params is None:
                params = []
            cursor = await self._connection.execute(query, params)
            return await cursor.fetchone()
            
        async def commit(self):
            await self._connection.commit()
    
    # Use default SQLite path
    session = SimpleSession("data/personas.db")
    async with session:
        yield session


# Global database manager instance
_db_manager: Optional[DatabaseManager] = None

def initialize_database(sqlite_manager: SQLiteManager, vector_manager: VectorMemoryManager):
    """Initialize the global database manager"""
    global _db_manager
    _db_manager = DatabaseManager(sqlite_manager, vector_manager)
    return _db_manager

def get_database_manager() -> Optional[DatabaseManager]:
    """Get the global database manager instance"""
    return _db_manager