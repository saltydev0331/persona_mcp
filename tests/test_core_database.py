"""
Unit tests for persona_mcp.core.database module

Tests the new shared core DatabaseManager that provides unified access 
to both SQLite and ChromaDB for operational parity between MCP and PersonaAPI servers.
"""

import pytest
import tempfile
import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any

from persona_mcp.core.database import DatabaseManager
from persona_mcp.core.models import Persona, Memory, Relationship, RelationshipType, EmotionalState
from persona_mcp.persistence.sqlite_manager import SQLiteManager
from persona_mcp.persistence.vector_memory import VectorMemoryManager


class TestDatabaseManagerInitialization:
    """Test DatabaseManager initialization and setup"""
    
    def test_database_manager_creates_instances(self):
        """Test that DatabaseManager creates default instances when none provided"""
        db_manager = DatabaseManager()
        
        assert db_manager.sqlite is not None
        assert db_manager.vector is not None
        assert db_manager.logger is not None
        assert db_manager.engine is not None
        assert db_manager.async_session is not None
    
    def test_database_manager_with_custom_instances(self):
        """Test DatabaseManager with custom SQLite and Vector managers"""
        mock_sqlite = MagicMock(spec=SQLiteManager)
        mock_sqlite.db_path = Path("/test/path/test.db")
        mock_vector = MagicMock(spec=VectorMemoryManager)
        
        db_manager = DatabaseManager(sqlite_manager=mock_sqlite, vector_manager=mock_vector)
        
        assert db_manager.sqlite is mock_sqlite
        assert db_manager.vector is mock_vector


class TestDatabaseManagerLifecycle:
    """Test DatabaseManager lifecycle methods"""
    
    @pytest.mark.asyncio
    async def test_initialization(self):
        """Test database manager initialization"""
        mock_sqlite = AsyncMock(spec=SQLiteManager)
        mock_vector = AsyncMock(spec=VectorMemoryManager)
        mock_sqlite.db_path = Path("/test/path/test.db")
        
        # Add the initialize method to SQLite mock (only SQLite is initialized, not vector)
        mock_sqlite.initialize = AsyncMock()
        
        db_manager = DatabaseManager(sqlite_manager=mock_sqlite, vector_manager=mock_vector)
        
        await db_manager.initialize()
        
        # Only SQLite initialize is called in the actual implementation
        mock_sqlite.initialize.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_close(self):
        """Test database manager cleanup"""
        mock_sqlite = AsyncMock(spec=SQLiteManager)
        mock_vector = AsyncMock(spec=VectorMemoryManager)
        mock_sqlite.db_path = Path("/test/path/test.db")
        
        # Add the close method to vector mock (only vector is closed, not SQLite)
        mock_vector.close = AsyncMock()
        
        db_manager = DatabaseManager(sqlite_manager=mock_sqlite, vector_manager=mock_vector)
        
        await db_manager.close()
        
        # Only vector close is called in the actual implementation
        mock_vector.close.assert_called_once()


class TestDatabaseManagerHealthCheck:
    """Test DatabaseManager health monitoring"""
    
    @pytest.mark.asyncio
    async def test_health_check_success(self):
        """Test successful health check"""
        mock_sqlite = AsyncMock(spec=SQLiteManager)
        mock_vector = AsyncMock(spec=VectorMemoryManager)
        mock_sqlite.db_path = Path("/test/path/test.db")
        
        # Mock list_personas and get_shared_memory_stats methods which health_check actually calls
        mock_sqlite.list_personas = AsyncMock(return_value=[])
        mock_vector.get_shared_memory_stats = AsyncMock(return_value={"total_memories": 150})
        
        db_manager = DatabaseManager(sqlite_manager=mock_sqlite, vector_manager=mock_vector)
        
        health = await db_manager.health_check()
        
        assert health["overall"] is True
        assert "sqlite" in health
        assert "vector" in health
        assert health["sqlite"]["healthy"] is True
        assert health["vector"]["healthy"] is True
    
    @pytest.mark.asyncio
    async def test_health_check_failure(self):
        """Test health check with failures"""
        mock_sqlite = AsyncMock(spec=SQLiteManager)
        mock_vector = AsyncMock(spec=VectorMemoryManager)
        mock_sqlite.db_path = Path("/test/path/test.db")
        
        # Mock failures in the methods that health_check actually calls
        mock_sqlite.list_personas = AsyncMock(side_effect=Exception("Connection failed"))
        mock_vector.get_shared_memory_stats = AsyncMock(return_value={"total_memories": 150})
        
        db_manager = DatabaseManager(sqlite_manager=mock_sqlite, vector_manager=mock_vector)
        
        health = await db_manager.health_check()
        
        assert health["overall"] is False
        assert health["sqlite"]["healthy"] is False
        assert health["vector"]["healthy"] is True


class TestDatabaseManagerPersonaOperations:
    """Test DatabaseManager persona CRUD operations"""
    
    @pytest.mark.asyncio
    async def test_create_persona(self):
        """Test persona creation"""
        mock_sqlite = AsyncMock(spec=SQLiteManager)
        mock_vector = AsyncMock(spec=VectorMemoryManager)
        mock_sqlite.db_path = Path("/test/path/test.db")
        
        persona_data = {
            "name": "TestPersona",
            "description": "A test persona",
            "personality_traits": {"trait": "friendly"}
        }
        
        # Mock the store_persona method which create_persona actually calls
        mock_sqlite.store_persona = AsyncMock(return_value=True)
        
        db_manager = DatabaseManager(sqlite_manager=mock_sqlite, vector_manager=mock_vector)
        
        result = await db_manager.create_persona(persona_data)
        
        mock_sqlite.store_persona.assert_called_once()
        assert result is not None
        assert result.name == "TestPersona"
        assert result.description == "A test persona"
    
    @pytest.mark.asyncio
    async def test_get_persona(self):
        """Test getting persona by ID"""
        mock_sqlite = AsyncMock(spec=SQLiteManager)
        mock_vector = AsyncMock(spec=VectorMemoryManager)
        mock_sqlite.db_path = Path("/test/path/test.db")
        
        persona_id = "test-persona-id"
        expected_persona_data = {
            "id": persona_id,
            "name": "TestPersona",
            "description": "A test persona"
        }
        
        # Mock the get_persona method which the DatabaseManager calls
        mock_sqlite.get_persona = AsyncMock(return_value=expected_persona_data)
        
        db_manager = DatabaseManager(sqlite_manager=mock_sqlite, vector_manager=mock_vector)
        
        result = await db_manager.get_persona(persona_id)
        
        mock_sqlite.get_persona.assert_called_once_with(persona_id)
        assert result is not None
        assert result.name == "TestPersona"
    
    @pytest.mark.asyncio
    async def test_list_personas(self):
        """Test listing all personas"""
        mock_sqlite = AsyncMock(spec=SQLiteManager)
        mock_vector = AsyncMock(spec=VectorMemoryManager)
        mock_sqlite.db_path = Path("/test/path/test.db")
        
        expected_personas = [
            Persona(id="1", name="Persona1", description="First persona"),
            Persona(id="2", name="Persona2", description="Second persona")
        ]
        
        # list_personas actually returns Persona objects directly
        mock_sqlite.list_personas = AsyncMock(return_value=expected_personas)
        
        db_manager = DatabaseManager(sqlite_manager=mock_sqlite, vector_manager=mock_vector)
        
        result = await db_manager.list_personas()
        
        mock_sqlite.list_personas.assert_called_once()
        assert result == expected_personas
    
    @pytest.mark.asyncio
    async def test_update_persona(self):
        """Test persona updates"""
        mock_sqlite = AsyncMock(spec=SQLiteManager)
        mock_vector = AsyncMock(spec=VectorMemoryManager)
        mock_sqlite.db_path = Path("/test/path/test.db")
        
        persona_id = "test-persona-id"
        updates = {"name": "UpdatedName", "description": "Updated description"}
        
        # Mock the update_persona method which the DatabaseManager calls
        mock_sqlite.update_persona = AsyncMock(return_value=True)
        
        db_manager = DatabaseManager(sqlite_manager=mock_sqlite, vector_manager=mock_vector)
        
        result = await db_manager.update_persona(persona_id, updates)
        
        mock_sqlite.update_persona.assert_called_once_with(persona_id, updates)
        assert result is True
    
    @pytest.mark.asyncio
    async def test_delete_persona(self):
        """Test persona deletion"""
        mock_sqlite = AsyncMock(spec=SQLiteManager)
        mock_vector = AsyncMock(spec=VectorMemoryManager)
        mock_sqlite.db_path = Path("/test/path/test.db")
        
        persona_id = "test-persona-id"
        
        mock_sqlite.delete_persona.return_value = True
        
        db_manager = DatabaseManager(sqlite_manager=mock_sqlite, vector_manager=mock_vector)
        
        result = await db_manager.delete_persona(persona_id)
        
        mock_sqlite.delete_persona.assert_called_once_with(persona_id)
        assert result is True


class TestDatabaseManagerMemoryOperations:
    """Test DatabaseManager memory operations"""
    
    @pytest.mark.asyncio
    async def test_store_memory(self):
        """Test memory storage"""
        mock_sqlite = AsyncMock(spec=SQLiteManager)
        mock_vector = AsyncMock(spec=VectorMemoryManager)
        mock_sqlite.db_path = Path("/test/path/test.db")
        
        memory = Memory(
            id="test-memory-id",
            persona_id="test-persona-id",
            content="Test memory content",
            importance=0.8
        )
        
        # Mock both vector.store_memory and sqlite.store_memory as per the actual implementation
        mock_vector.store_memory = AsyncMock(return_value=True)
        mock_sqlite.store_memory = AsyncMock(return_value=True)
        
        db_manager = DatabaseManager(sqlite_manager=mock_sqlite, vector_manager=mock_vector)
        
        result = await db_manager.store_memory(memory)
        
        # Check that both backends were called
        mock_vector.store_memory.assert_called_once()
        mock_sqlite.store_memory.assert_called_once()
        assert result is True
    
    @pytest.mark.asyncio
    async def test_search_memories(self):
        """Test memory search"""
        mock_sqlite = AsyncMock(spec=SQLiteManager)
        mock_vector = AsyncMock(spec=VectorMemoryManager)
        mock_sqlite.db_path = Path("/test/path/test.db")
        
        persona_id = "test-persona-id"
        query = "test query"
        
        # Mock vector search results in the format the implementation expects
        mock_results = [
            {
                "id": "1",
                "content": "Memory 1",
                "metadata": {
                    "persona_id": persona_id,
                    "memory_type": "conversation",
                    "importance": 0.8
                }
            },
            {
                "id": "2", 
                "content": "Memory 2",
                "metadata": {
                    "persona_id": persona_id,
                    "memory_type": "conversation",
                    "importance": 0.6
                }
            }
        ]
        
        mock_vector.search_memories = AsyncMock(return_value=mock_results)
        
        db_manager = DatabaseManager(sqlite_manager=mock_sqlite, vector_manager=mock_vector)
        
        result = await db_manager.search_memories(persona_id, query)
        
        mock_vector.search_memories.assert_called_once_with(
            persona_id=persona_id, query=query, n_results=5, min_importance=0.0
        )
        assert len(result) == 2
        assert all(isinstance(m, Memory) for m in result)
    
    @pytest.mark.asyncio
    async def test_get_memory_stats(self):
        """Test memory statistics retrieval"""
        mock_sqlite = AsyncMock(spec=SQLiteManager)
        mock_vector = AsyncMock(spec=VectorMemoryManager)
        mock_sqlite.db_path = Path("/test/path/test.db")
        
        persona_id = "test-persona-id"
        expected_stats = {"total_memories": 150, "avg_importance": 0.75}
        
        mock_vector.get_memory_stats = AsyncMock(return_value=expected_stats)
        
        db_manager = DatabaseManager(sqlite_manager=mock_sqlite, vector_manager=mock_vector)
        
        result = await db_manager.get_memory_stats(persona_id)
        
        mock_vector.get_memory_stats.assert_called_once_with(persona_id)
        assert result == expected_stats
    
    @pytest.mark.asyncio
    async def test_prune_memories(self):
        """Test memory pruning"""
        mock_sqlite = AsyncMock(spec=SQLiteManager)
        mock_vector = AsyncMock(spec=VectorMemoryManager)
        mock_sqlite.db_path = Path("/test/path/test.db")
        
        persona_id = "test-persona-id"
        max_memories = 1000
        expected_result = {"pruned_count": 50, "remaining_count": 1000}
        
        mock_vector.prune_memories = AsyncMock(return_value=expected_result)
        
        db_manager = DatabaseManager(sqlite_manager=mock_sqlite, vector_manager=mock_vector)
        
        result = await db_manager.prune_memories(persona_id, max_memories)
        
        mock_vector.prune_memories.assert_called_once_with(persona_id, max_memories)
        assert result == expected_result


class TestDatabaseManagerRelationshipOperations:
    """Test DatabaseManager relationship operations"""
    
    @pytest.mark.asyncio
    async def test_get_relationship(self):
        """Test getting relationship between personas"""
        mock_sqlite = AsyncMock(spec=SQLiteManager)
        mock_vector = AsyncMock(spec=VectorMemoryManager)
        mock_sqlite.db_path = Path("/test/path/test.db")
        
        persona1_id = "persona-1"
        persona2_id = "persona-2"
        expected_relationship_data = {
            "persona1_id": persona1_id,
            "persona2_id": persona2_id,
            "relationship_type": RelationshipType.FRIEND,
            "affinity": 0.8
        }
        
        # Mock the get_relationship method which returns raw dict data
        mock_sqlite.get_relationship = AsyncMock(return_value=expected_relationship_data)
        
        db_manager = DatabaseManager(sqlite_manager=mock_sqlite, vector_manager=mock_vector)
        
        result = await db_manager.get_relationship(persona1_id, persona2_id)
        
        mock_sqlite.get_relationship.assert_called_once_with(persona1_id, persona2_id)
        assert result is not None
        assert result.persona1_id == persona1_id
        assert result.persona2_id == persona2_id
    
    @pytest.mark.asyncio
    async def test_create_relationship(self):
        """Test relationship creation"""
        mock_sqlite = AsyncMock(spec=SQLiteManager)
        mock_vector = AsyncMock(spec=VectorMemoryManager)
        mock_sqlite.db_path = Path("/test/path/test.db")
        
        relationship = Relationship(
            persona1_id="persona-1",
            persona2_id="persona-2",
            relationship_type=RelationshipType.FRIEND,
            affinity=0.8
        )
        
        # Mock the create_relationship method which the DatabaseManager calls
        mock_sqlite.create_relationship = AsyncMock(return_value=True)
        
        db_manager = DatabaseManager(sqlite_manager=mock_sqlite, vector_manager=mock_vector)
        
        result = await db_manager.create_relationship(relationship)
        
        mock_sqlite.create_relationship.assert_called_once()
        assert result is True
    
    @pytest.mark.asyncio
    async def test_list_relationships(self):
        """Test listing persona relationships"""
        mock_sqlite = AsyncMock(spec=SQLiteManager)
        mock_vector = AsyncMock(spec=VectorMemoryManager)
        mock_sqlite.db_path = Path("/test/path/test.db")
        
        persona_id = "test-persona-id"
        
        # Mock raw relationship data as returned by get_persona_relationships
        expected_relationships_data = [
            {
                "persona1_id": persona_id,
                "persona2_id": "other-1",
                "relationship_type": RelationshipType.FRIEND,
                "affinity": 0.7
            },
            {
                "persona1_id": persona_id,
                "persona2_id": "other-2", 
                "relationship_type": RelationshipType.ACQUAINTANCE,
                "affinity": 0.3
            }
        ]
        
        mock_sqlite.get_persona_relationships = AsyncMock(return_value=expected_relationships_data)
        
        db_manager = DatabaseManager(sqlite_manager=mock_sqlite, vector_manager=mock_vector)
        
        result = await db_manager.list_relationships(persona_id)
        
        mock_sqlite.get_persona_relationships.assert_called_once_with(persona_id)
        assert len(result) == 2
        assert all(isinstance(r, Relationship) for r in result)


class TestDatabaseManagerSessionManagement:
    """Test DatabaseManager async session management"""
    
    @pytest.mark.asyncio
    async def test_get_session_success(self):
        """Test successful session acquisition and commit"""
        mock_sqlite = AsyncMock(spec=SQLiteManager)
        mock_vector = AsyncMock(spec=VectorMemoryManager)
        mock_sqlite.db_path = Path("/test/path/test.db")
        
        db_manager = DatabaseManager(sqlite_manager=mock_sqlite, vector_manager=mock_vector)
        
        # This is a basic test to ensure the session context manager works
        # In a real test environment, we'd use a test database
        async with db_manager.get_session() as session:
            assert session is not None
    
    @pytest.mark.asyncio
    async def test_get_session_rollback_on_error(self):
        """Test session rollback on exceptions"""
        mock_sqlite = AsyncMock(spec=SQLiteManager)
        mock_vector = AsyncMock(spec=VectorMemoryManager)
        mock_sqlite.db_path = Path("/test/path/test.db")
        
        db_manager = DatabaseManager(sqlite_manager=mock_sqlite, vector_manager=mock_vector)
        
        # Test that exceptions are properly handled
        with pytest.raises(ValueError):
            async with db_manager.get_session() as session:
                assert session is not None
                raise ValueError("Test exception")


class TestDatabaseManagerEdgeCases:
    """Test DatabaseManager edge cases and error handling"""
    
    @pytest.mark.asyncio
    async def test_health_check_with_exceptions(self):
        """Test health check when underlying managers raise exceptions"""
        mock_sqlite = AsyncMock(spec=SQLiteManager)
        mock_vector = AsyncMock(spec=VectorMemoryManager)
        mock_sqlite.db_path = Path("/test/path/test.db")
        
        # Mock exceptions in the methods that health_check actually calls
        mock_sqlite.list_personas = AsyncMock(side_effect=Exception("SQLite error"))
        mock_vector.get_shared_memory_stats = AsyncMock(return_value={"total_memories": 100})
        
        db_manager = DatabaseManager(sqlite_manager=mock_sqlite, vector_manager=mock_vector)
        
        health = await db_manager.health_check()
        
        assert health["overall"] is False
        assert health["sqlite"]["healthy"] is False
        assert "Error: SQLite error" in health["sqlite"]["details"]
        assert health["vector"]["healthy"] is True
    
    @pytest.mark.asyncio
    async def test_memory_storage_partial_failure(self):
        """Test memory storage when vector backend fails"""
        mock_sqlite = AsyncMock(spec=SQLiteManager)
        mock_vector = AsyncMock(spec=VectorMemoryManager)
        mock_sqlite.db_path = Path("/test/path/test.db")
        
        memory = Memory(
            id="test-memory-id",
            persona_id="test-persona-id",
            content="Test memory content",
            importance=0.8
        )
        
        # Mock partial failure - vector fails but sqlite succeeds
        mock_vector.store_memory = AsyncMock(return_value=False)
        mock_sqlite.store_memory = AsyncMock(return_value=True)
        
        db_manager = DatabaseManager(sqlite_manager=mock_sqlite, vector_manager=mock_vector)
        
        result = await db_manager.store_memory(memory)
        
        # Should return False if any backend fails
        assert result is False


class TestDatabaseManagerIntegration:
    """Integration tests for DatabaseManager with real components"""
    
    @pytest.mark.asyncio
    async def test_full_workflow_with_temp_db(self):
        """Test complete workflow with temporary database"""
        # This test would use a temporary database file for full integration testing
        # For now, we'll skip this but it should be implemented for complete coverage
        pytest.skip("Integration test with real database - implement when ready for full testing")