"""
Unit tests for persona_mcp.core.memory module

Tests the new shared core MemoryManager that provides unified memory operations
for both MCP server and PersonaAPI server to ensure operational parity.
"""

import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any, List

from persona_mcp.core.memory import MemoryManager
from persona_mcp.core.models import Memory, Persona
from persona_mcp.persistence.vector_memory import VectorMemoryManager
from persona_mcp.memory.importance_scorer import MemoryImportanceScorer
from persona_mcp.memory.decay_system import MemoryDecaySystem
from persona_mcp.memory.pruning_system import MemoryPruningSystem


class TestMemoryManagerInitialization:
    """Test MemoryManager initialization and setup"""
    
    def test_memory_manager_creates_default_instances(self):
        """Test that MemoryManager creates default instances when none provided"""
        memory_manager = MemoryManager()
        
        assert memory_manager.vector_manager is not None
        assert memory_manager.importance_scorer is not None
        assert memory_manager.decay_system is not None
        assert memory_manager.pruning_system is not None
        assert memory_manager.logger is not None
    
    def test_memory_manager_with_custom_vector_manager(self):
        """Test MemoryManager with custom VectorMemoryManager"""
        mock_vector = MagicMock(spec=VectorMemoryManager)
        
        memory_manager = MemoryManager(vector_manager=mock_vector)
        
        assert memory_manager.vector_manager is mock_vector
        assert memory_manager.importance_scorer is not None
        assert memory_manager.decay_system is not None
        assert memory_manager.pruning_system is not None


class TestMemoryManagerLifecycle:
    """Test MemoryManager lifecycle methods"""
    
    @pytest.mark.asyncio
    async def test_initialization(self):
        """Test memory manager initialization"""
        mock_vector = AsyncMock(spec=VectorMemoryManager)
        
        memory_manager = MemoryManager(vector_manager=mock_vector)
        
        await memory_manager.initialize()
        
        # Initialization just logs success, no actual calls to dependencies
        assert True  # Test passes if no exceptions
    
    @pytest.mark.asyncio
    async def test_close(self):
        """Test memory manager cleanup"""
        mock_vector = AsyncMock(spec=VectorMemoryManager)
        mock_vector.close = AsyncMock()
        
        memory_manager = MemoryManager(vector_manager=mock_vector)
        
        await memory_manager.close()
        
        mock_vector.close.assert_called_once()


class TestMemoryManagerHealthCheck:
    """Test MemoryManager health monitoring"""
    
    @pytest.mark.asyncio
    async def test_health_check_success(self):
        """Test successful health check"""
        mock_vector = AsyncMock(spec=VectorMemoryManager)
        mock_vector.get_shared_memory_stats = AsyncMock(return_value={"total_memories": 250})
        
        memory_manager = MemoryManager(vector_manager=mock_vector)
        
        health = await memory_manager.health_check()
        
        assert health["overall"] is True
        assert health["vector_manager"]["healthy"] is True
        assert health["importance_scorer"]["healthy"] is True
        assert health["decay_system"]["healthy"] is True
        assert health["pruning_system"]["healthy"] is True
        assert "250 memories" in health["vector_manager"]["details"]
    
    @pytest.mark.asyncio
    async def test_health_check_vector_failure(self):
        """Test health check with vector manager failure"""
        mock_vector = AsyncMock(spec=VectorMemoryManager)
        mock_vector.get_shared_memory_stats = AsyncMock(side_effect=Exception("Vector error"))
        
        memory_manager = MemoryManager(vector_manager=mock_vector)
        
        health = await memory_manager.health_check()
        
        assert health["overall"] is False
        assert health["vector_manager"]["healthy"] is False
        assert "Error: Vector error" in health["vector_manager"]["details"]
        # Other systems should still be healthy
        assert health["importance_scorer"]["healthy"] is True
        assert health["decay_system"]["healthy"] is True
        assert health["pruning_system"]["healthy"] is True


class TestMemoryManagerStorage:
    """Test MemoryManager memory storage operations"""
    
    @pytest.mark.asyncio
    async def test_store_memory_with_provided_importance(self):
        """Test storing memory with provided importance score"""
        mock_vector = AsyncMock(spec=VectorMemoryManager)
        mock_vector.store_memory = AsyncMock(return_value=True)
        
        memory_manager = MemoryManager(vector_manager=mock_vector)
        
        result = await memory_manager.store_memory(
            persona_id="test-persona",
            content="Test memory content",
            memory_type="conversation",
            importance=0.8,
            emotional_valence=0.5,
            metadata={"test": "data"}
        )
        
        assert isinstance(result, Memory)
        assert result.persona_id == "test-persona"
        assert result.content == "Test memory content"
        assert result.importance == 0.8
        assert result.emotional_valence == 0.5
        
        mock_vector.store_memory.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_store_memory_with_auto_importance_scoring(self):
        """Test storing memory with automatic importance scoring"""
        mock_vector = AsyncMock(spec=VectorMemoryManager)
        mock_vector.store_memory = AsyncMock(return_value=True)
        
        memory_manager = MemoryManager(vector_manager=mock_vector)
        
        # Mock the importance scorer - use correct method name
        with patch.object(memory_manager.importance_scorer, 'calculate_importance', new_callable=AsyncMock) as mock_scorer:
            mock_scorer.return_value = 0.7
            
            result = await memory_manager.store_memory(
                persona_id="test-persona",
                content="Test memory content"
            )
            
            assert result.importance == 0.7
            mock_scorer.assert_called_once_with(
                content="Test memory content",
                speaker=None,
                listener=None,
                relationship=None,
                turn=None,
                context={}
            )
    
    @pytest.mark.asyncio
    async def test_store_memory_with_optional_parameters(self):
        """Test storing memory with all optional parameters"""
        mock_vector = AsyncMock(spec=VectorMemoryManager)
        mock_vector.store_memory = AsyncMock(return_value=True)
        
        memory_manager = MemoryManager(vector_manager=mock_vector)
        
        result = await memory_manager.store_memory(
            persona_id="test-persona",
            content="Test memory content",
            memory_type="relationship",
            importance=0.9,
            emotional_valence=-0.3,
            related_personas=["other-persona"],
            visibility="shared",
            metadata={"context": "test"}
        )
        
        assert result.memory_type == "relationship"
        assert result.emotional_valence == -0.3
        assert result.related_personas == ["other-persona"]
        assert result.visibility == "shared"
        assert result.metadata == {"context": "test"}


class TestMemoryManagerSearch:
    """Test MemoryManager memory search operations"""
    
    @pytest.mark.asyncio
    async def test_search_memories(self):
        """Test searching memories for a persona"""
        mock_vector = AsyncMock(spec=VectorMemoryManager)
        
        # Mock search results
        mock_results = [
            {
                "id": "memory-1",
                "content": "Test memory 1",
                "metadata": {
                    "persona_id": "test-persona",
                    "memory_type": "conversation",
                    "importance": 0.8,
                    "emotional_valence": 0.2
                }
            },
            {
                "id": "memory-2", 
                "content": "Test memory 2",
                "metadata": {
                    "persona_id": "test-persona",
                    "memory_type": "event",
                    "importance": 0.6,
                    "emotional_valence": -0.1
                }
            }
        ]
        
        mock_vector.search_memories = AsyncMock(return_value=mock_results)
        
        memory_manager = MemoryManager(vector_manager=mock_vector)
        
        results = await memory_manager.search_memories(
            persona_id="test-persona",
            query="test query",
            n_results=5,
            min_importance=0.5
        )
        
        assert len(results) == 2
        assert all(isinstance(m, Memory) for m in results)
        assert results[0].content == "Test memory 1"
        assert results[1].content == "Test memory 2"
        
        # Verify access was recorded
        assert results[0].accessed_count > 0
        assert results[1].accessed_count > 0
        
        mock_vector.search_memories.assert_called_once_with(
            persona_id="test-persona",
            query="test query",
            n_results=5,
            min_importance=0.5
        )
    
    @pytest.mark.asyncio
    async def test_search_cross_persona_memories(self):
        """Test searching memories across personas"""
        mock_vector = AsyncMock(spec=VectorMemoryManager)
        
        mock_results = [
            {
                "id": "shared-memory-1",
                "content": "Shared event",
                "metadata": {
                    "persona_id": "other-persona",
                    "memory_type": "event",
                    "importance": 0.9,
                    "visibility": "shared"
                }
            }
        ]
        
        mock_vector.search_cross_persona_memories = AsyncMock(return_value=mock_results)
        
        memory_manager = MemoryManager(vector_manager=mock_vector)
        
        results = await memory_manager.search_cross_persona_memories(
            query="shared event",
            requesting_persona_id="test-persona",
            n_results=10,
            min_importance=0.7
        )
        
        assert len(results) == 1
        assert results[0].content == "Shared event"
        assert results[0].visibility == "shared"
        
        mock_vector.search_cross_persona_memories.assert_called_once_with(
            query="shared event",
            requesting_persona_id="test-persona",
            n_results=10,
            min_importance=0.7
        )


class TestMemoryManagerStatistics:
    """Test MemoryManager statistics and reporting"""
    
    @pytest.mark.asyncio
    async def test_get_memory_stats(self):
        """Test getting memory statistics for a persona"""
        mock_vector = AsyncMock(spec=VectorMemoryManager)
        expected_stats = {
            "total_memories": 150,
            "avg_importance": 0.65,
            "memory_types": {"conversation": 100, "event": 30, "relationship": 20}
        }
        mock_vector.get_memory_stats = AsyncMock(return_value=expected_stats)
        
        memory_manager = MemoryManager(vector_manager=mock_vector)
        
        stats = await memory_manager.get_memory_stats("test-persona")
        
        assert stats == expected_stats
        mock_vector.get_memory_stats.assert_called_once_with("test-persona")
    
    @pytest.mark.asyncio
    async def test_get_shared_memory_stats(self):
        """Test getting shared memory statistics"""
        mock_vector = AsyncMock(spec=VectorMemoryManager)
        expected_stats = {
            "total_shared_memories": 50,
            "participating_personas": 5,
            "avg_importance": 0.8
        }
        mock_vector.get_shared_memory_stats = AsyncMock(return_value=expected_stats)
        
        memory_manager = MemoryManager(vector_manager=mock_vector)
        
        stats = await memory_manager.get_shared_memory_stats()
        
        assert stats == expected_stats
        mock_vector.get_shared_memory_stats.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_system_stats(self):
        """Test getting comprehensive system statistics"""
        mock_vector = AsyncMock(spec=VectorMemoryManager)
        mock_vector.get_stats = AsyncMock(return_value={"vector": "stats"})
        
        memory_manager = MemoryManager(vector_manager=mock_vector)
        
        # Mock the subsystem stats
        with patch.object(memory_manager.decay_system, 'get_decay_stats') as mock_decay, \
             patch.object(memory_manager.pruning_system, 'get_pruning_stats') as mock_pruning:
            
            mock_decay.return_value = {"decay": "stats"}
            mock_pruning.return_value = {"pruning": "stats"}
            
            stats = await memory_manager.get_system_stats()
            
            assert "vector_memory" in stats
            assert "decay_system" in stats
            assert "pruning_system" in stats
            assert stats["vector_memory"] == {"vector": "stats"}
            assert stats["decay_system"] == {"decay": "stats"}
            assert stats["pruning_system"] == {"pruning": "stats"}


class TestMemoryManagerPruning:
    """Test MemoryManager pruning operations"""
    
    @pytest.mark.asyncio
    async def test_prune_memories(self):
        """Test pruning memories for a persona"""
        mock_vector = AsyncMock(spec=VectorMemoryManager)
        memory_manager = MemoryManager(vector_manager=mock_vector)
        
        expected_result = {"pruned_count": 25, "remaining_count": 1000}
        
        with patch.object(memory_manager.pruning_system, 'prune_persona_memories', new_callable=AsyncMock) as mock_prune:
            mock_prune.return_value = expected_result
            
            result = await memory_manager.prune_memories(
                persona_id="test-persona",
                max_memories=1000,
                strategy="importance_based"
            )
            
            assert result == expected_result
            mock_prune.assert_called_once_with(
                persona_id="test-persona",
                max_memories=1000,
                strategy="importance_based"
            )
    
    @pytest.mark.asyncio
    async def test_prune_all_memories(self):
        """Test pruning memories for all personas"""
        mock_vector = AsyncMock(spec=VectorMemoryManager)
        memory_manager = MemoryManager(vector_manager=mock_vector)
        
        expected_result = {"total_pruned": 100, "personas_processed": 5}
        
        with patch.object(memory_manager.pruning_system, 'prune_all_personas', new_callable=AsyncMock) as mock_prune:
            mock_prune.return_value = expected_result
            
            result = await memory_manager.prune_all_memories(max_memories_per_persona=1000)
            
            assert result == expected_result
            mock_prune.assert_called_once_with()
    
    @pytest.mark.asyncio
    async def test_get_pruning_recommendations(self):
        """Test getting pruning recommendations"""
        mock_vector = AsyncMock(spec=VectorMemoryManager)
        memory_manager = MemoryManager(vector_manager=mock_vector)
        
        expected_result = {"recommended_pruning": 50, "candidates": ["id1", "id2"]}
        
        with patch.object(memory_manager.pruning_system, 'get_pruning_recommendations', new_callable=AsyncMock) as mock_rec:
            mock_rec.return_value = expected_result
            
            result = await memory_manager.get_pruning_recommendations("test-persona")
            
            assert result == expected_result
            mock_rec.assert_called_once_with("test-persona")
    
    @pytest.mark.asyncio
    async def test_get_pruning_stats(self):
        """Test getting pruning system statistics"""
        mock_vector = AsyncMock(spec=VectorMemoryManager)
        memory_manager = MemoryManager(vector_manager=mock_vector)
        
        expected_stats = {"total_pruned": 500, "avg_pruning_time": 2.5}
        
        with patch.object(memory_manager.pruning_system, 'get_pruning_stats') as mock_stats:
            mock_stats.return_value = expected_stats
            
            result = await memory_manager.get_pruning_stats()
            
            assert result == expected_stats
            mock_stats.assert_called_once()


class TestMemoryManagerDecay:
    """Test MemoryManager decay system operations"""
    
    @pytest.mark.asyncio
    async def test_start_decay_system(self):
        """Test starting the decay system"""
        mock_vector = AsyncMock(spec=VectorMemoryManager)
        memory_manager = MemoryManager(vector_manager=mock_vector)
        
        with patch.object(memory_manager.decay_system, 'start_background_decay', new_callable=AsyncMock) as mock_start:
            mock_start.return_value = True
            
            result = await memory_manager.start_decay_system()
            
            assert result is True
            mock_start.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_stop_decay_system(self):
        """Test stopping the decay system"""
        mock_vector = AsyncMock(spec=VectorMemoryManager)
        memory_manager = MemoryManager(vector_manager=mock_vector)
        
        with patch.object(memory_manager.decay_system, 'stop_background_decay', new_callable=AsyncMock) as mock_stop:
            mock_stop.return_value = True
            
            result = await memory_manager.stop_decay_system()
            
            assert result is True
            mock_stop.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_decay_stats(self):
        """Test getting decay system statistics"""
        mock_vector = AsyncMock(spec=VectorMemoryManager)
        memory_manager = MemoryManager(vector_manager=mock_vector)
        
        expected_stats = {"running": True, "decay_rate": 0.1, "memories_processed": 1000}
        
        with patch.object(memory_manager.decay_system, 'get_decay_stats') as mock_stats:
            mock_stats.return_value = expected_stats
            
            result = await memory_manager.get_decay_stats()
            
            assert result == expected_stats
            mock_stats.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_force_decay(self):
        """Test forcing decay processing"""
        mock_vector = AsyncMock(spec=VectorMemoryManager)
        memory_manager = MemoryManager(vector_manager=mock_vector)
        
        expected_result = {"memories_decayed": 50, "avg_decay": 0.15}
        
        with patch.object(memory_manager.decay_system, 'force_decay_persona', new_callable=AsyncMock) as mock_decay:
            mock_decay.return_value = expected_result
            
            result = await memory_manager.force_decay(
                persona_id="test-persona",
                decay_rate=0.2,
                time_factor=1.5
            )
            
            assert result == expected_result
            mock_decay.assert_called_once_with("test-persona", 0.2)


class TestMemoryManagerDeletion:
    """Test MemoryManager deletion operations"""
    
    @pytest.mark.asyncio
    async def test_delete_persona_memories(self):
        """Test deleting all memories for a persona"""
        mock_vector = AsyncMock(spec=VectorMemoryManager)
        mock_vector.delete_persona_memories = AsyncMock(return_value=True)
        
        memory_manager = MemoryManager(vector_manager=mock_vector)
        
        result = await memory_manager.delete_persona_memories("test-persona")
        
        assert result is True
        mock_vector.delete_persona_memories.assert_called_once_with("test-persona")
    
    @pytest.mark.asyncio
    async def test_delete_persona_memories_failure(self):
        """Test failure when deleting persona memories"""
        mock_vector = AsyncMock(spec=VectorMemoryManager)
        mock_vector.delete_persona_memories = AsyncMock(return_value=False)
        
        memory_manager = MemoryManager(vector_manager=mock_vector)
        
        result = await memory_manager.delete_persona_memories("test-persona")
        
        assert result is False
        mock_vector.delete_persona_memories.assert_called_once_with("test-persona")


class TestMemoryManagerEdgeCases:
    """Test MemoryManager edge cases and error handling"""
    
    @pytest.mark.asyncio
    async def test_search_memories_empty_results(self):
        """Test searching memories with empty results"""
        mock_vector = AsyncMock(spec=VectorMemoryManager)
        mock_vector.search_memories = AsyncMock(return_value=[])
        
        memory_manager = MemoryManager(vector_manager=mock_vector)
        
        results = await memory_manager.search_memories("test-persona", "nonexistent query")
        
        assert results == []
    
    @pytest.mark.asyncio
    async def test_search_memories_malformed_results(self):
        """Test handling malformed search results"""
        mock_vector = AsyncMock(spec=VectorMemoryManager)
        
        # Malformed result missing required fields
        mock_results = [
            {
                "id": "memory-1",
                # Missing content and metadata
            }
        ]
        
        mock_vector.search_memories = AsyncMock(return_value=mock_results)
        
        memory_manager = MemoryManager(vector_manager=mock_vector)
        
        results = await memory_manager.search_memories("test-persona", "test query")
        
        # Should handle gracefully with defaults
        assert len(results) == 1
        assert results[0].content == ""  # Default empty content
        assert results[0].importance == 0.5  # Default importance
    
    @pytest.mark.asyncio
    async def test_store_memory_vector_failure(self):
        """Test storing memory when vector storage fails"""
        mock_vector = AsyncMock(spec=VectorMemoryManager)
        mock_vector.store_memory = AsyncMock(return_value=False)
        
        memory_manager = MemoryManager(vector_manager=mock_vector)
        
        # Should still return Memory object even if storage fails
        result = await memory_manager.store_memory(
            persona_id="test-persona",
            content="Test content",
            importance=0.8
        )
        
        assert isinstance(result, Memory)
        assert result.content == "Test content"
        assert result.importance == 0.8


class TestMemoryManagerIntegration:
    """Integration tests for MemoryManager with realistic scenarios"""
    
    @pytest.mark.asyncio
    async def test_full_memory_workflow(self):
        """Test complete memory workflow from storage to retrieval"""
        mock_vector = AsyncMock(spec=VectorMemoryManager)
        mock_vector.store_memory = AsyncMock(return_value=True)
        
        # Mock search returning the stored memory
        mock_search_results = [
            {
                "id": "stored-memory",
                "content": "Important conversation about project",
                "metadata": {
                    "persona_id": "test-persona",
                    "memory_type": "conversation",
                    "importance": 0.9,
                    "emotional_valence": 0.3
                }
            }
        ]
        mock_vector.search_memories = AsyncMock(return_value=mock_search_results)
        
        memory_manager = MemoryManager(vector_manager=mock_vector)
        
        # Store memory
        stored_memory = await memory_manager.store_memory(
            persona_id="test-persona",
            content="Important conversation about project",
            importance=0.9,
            emotional_valence=0.3
        )
        
        assert stored_memory.importance == 0.9
        
        # Search for stored memory
        search_results = await memory_manager.search_memories(
            persona_id="test-persona",
            query="project conversation"
        )
        
        assert len(search_results) == 1
        assert search_results[0].content == "Important conversation about project"
        assert search_results[0].importance == 0.9