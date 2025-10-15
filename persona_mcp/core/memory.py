"""
Shared memory manager for Persona-MCP system.

Provides unified memory operations for both MCP server and PersonaAPI server
to ensure operational parity and consistent memory management.
"""

from typing import Dict, List, Any, Optional
from ..persistence import VectorMemoryManager
from ..memory.importance_scorer import MemoryImportanceScorer
from ..memory.decay_system import MemoryDecaySystem
from ..memory.pruning_system import MemoryPruningSystem
from ..logging import get_logger
from .models import Memory, Persona


class MemoryManager:
    """Unified memory management system for both services"""
    
    def __init__(self, vector_manager: Optional[VectorMemoryManager] = None):
        self.vector_manager = vector_manager or VectorMemoryManager()
        self.importance_scorer = MemoryImportanceScorer()
        
        # Create pruning system first (no dependencies)
        self.pruning_system = MemoryPruningSystem(vector_memory=self.vector_manager)
        
        # Create decay system (depends on pruning system)
        self.decay_system = MemoryDecaySystem(
            vector_memory=self.vector_manager,
            pruning_system=self.pruning_system
        )
        
        self.logger = get_logger(__name__)
    
    async def initialize(self):
        """Initialize memory systems"""
        # Vector memory manager doesn't need initialization in current implementation
        self.logger.info("Memory systems initialized successfully")
    
    async def close(self):
        """Close memory system connections"""
        await self.vector_manager.close()
        # Note: decay_system and pruning_system don't have close methods
        self.logger.info("Memory systems closed")

    async def health_check(self) -> Dict[str, Any]:
        """Check health of memory management systems"""
        try:
            # Test vector memory manager by getting stats
            stats = await self.vector_manager.get_shared_memory_stats()
            vector_health = True
            vector_details = f"Connected, {stats.get('total_memories', 0)} memories"
        except Exception as e:
            vector_health = False
            vector_details = f"Error: {str(e)}"
        
        # Memory systems are always healthy if no exceptions (no external dependencies)
        importance_health = True
        decay_health = True
        pruning_health = True
        
        overall_health = vector_health and importance_health and decay_health and pruning_health
        
        return {
            "overall": overall_health,
            "vector_manager": {"healthy": vector_health, "details": vector_details},
            "importance_scorer": {"healthy": importance_health, "details": "Operational"},
            "decay_system": {"healthy": decay_health, "details": "Operational"},
            "pruning_system": {"healthy": pruning_health, "details": "Operational"}
        }

    async def store_memory(self, persona_id: str, content: str, 
                          memory_type: str = "conversation",
                          importance: Optional[float] = None,
                          emotional_valence: float = 0.0,
                          related_personas: Optional[List[str]] = None,
                          visibility: str = "private",
                          metadata: Optional[Dict[str, Any]] = None) -> Memory:
        """Store a memory with automatic importance scoring if not provided"""
        
        # Auto-score importance if not provided
        if importance is None:
            importance = await self.importance_scorer.calculate_importance(
                content=content,
                speaker=None,  # We don't have speaker/listener context here
                listener=None,
                relationship=None,
                turn=None,
                context=metadata or {}
            )

        # Create memory object
        memory = Memory(
            persona_id=persona_id,
            content=content,
            memory_type=memory_type,
            importance=importance,
            emotional_valence=emotional_valence,
            related_personas=related_personas or [],
            visibility=visibility,
            metadata=metadata or {}
        )

        # Store in vector database
        success = await self.vector_manager.store_memory(
            persona_id=persona_id,
            content=content,
            memory_type=memory_type,
            importance=importance,
            metadata=memory.dict()
        )

        if success:
            self.logger.debug(f"Stored memory for persona {persona_id} (importance: {importance:.2f})")
        
        return memory

    async def search_memories(self, persona_id: str, query: str,
                            n_results: int = 5, min_importance: float = 0.0) -> List[Memory]:
        """Search memories using semantic similarity"""
        results = await self.vector_manager.search_memories(
            persona_id=persona_id,
            query=query,
            n_results=n_results,
            min_importance=min_importance
        )

        memories = []
        for result in results:
            metadata = result.get('metadata', {})
            memory = Memory(
                id=result.get('id', ''),
                content=result.get('content', ''),
                persona_id=metadata.get('persona_id', persona_id),
                memory_type=metadata.get('memory_type', 'conversation'),
                importance=metadata.get('importance', 0.5),
                emotional_valence=metadata.get('emotional_valence', 0.0),
                related_personas=metadata.get('related_personas', []),
                visibility=metadata.get('visibility', 'private'),
                metadata=metadata
            )
            memory.access()  # Record access
            memories.append(memory)

        return memories

    async def search_cross_persona_memories(self, query: str, 
                                          requesting_persona_id: str,
                                          n_results: int = 5,
                                          min_importance: float = 0.3) -> List[Memory]:
        """Search shared/public memories across all personas"""
        results = await self.vector_manager.search_cross_persona_memories(
            query=query,
            requesting_persona_id=requesting_persona_id,
            n_results=n_results,
            min_importance=min_importance
        )

        memories = []
        for result in results:
            metadata = result.get('metadata', {})
            memory = Memory(
                id=result.get('id', ''),
                content=result.get('content', ''),
                persona_id=metadata.get('persona_id', ''),
                memory_type=metadata.get('memory_type', 'conversation'),
                importance=metadata.get('importance', 0.5),
                emotional_valence=metadata.get('emotional_valence', 0.0),
                related_personas=metadata.get('related_personas', []),
                visibility=metadata.get('visibility', 'shared'),
                metadata=metadata
            )
            memories.append(memory)

        return memories

    async def get_memory_stats(self, persona_id: str) -> Dict[str, Any]:
        """Get detailed memory statistics for a persona"""
        return await self.vector_manager.get_memory_stats(persona_id)

    async def get_shared_memory_stats(self) -> Dict[str, Any]:
        """Get statistics for shared memories across personas"""
        return await self.vector_manager.get_shared_memory_stats()

    async def prune_memories(self, persona_id: str, max_memories: int = 1000,
                           strategy: str = "importance_based") -> Dict[str, Any]:
        """Intelligently prune memories for a persona"""
        return await self.pruning_system.prune_persona_memories(
            persona_id=persona_id,
            max_memories=max_memories,
            strategy=strategy
        )

    async def prune_all_memories(self, max_memories_per_persona: int = 1000) -> Dict[str, Any]:
        """Prune memories for all personas"""
        return await self.pruning_system.prune_all_personas()

    async def get_pruning_recommendations(self, persona_id: str) -> Dict[str, Any]:
        """Get recommendations for memory pruning without actually pruning"""
        return await self.pruning_system.get_pruning_recommendations(persona_id)

    async def get_pruning_stats(self) -> Dict[str, Any]:
        """Get pruning system performance statistics"""
        return self.pruning_system.get_pruning_stats()

    async def start_decay_system(self) -> bool:
        """Start background memory decay processing"""
        await self.decay_system.start_background_decay()
        return True

    async def stop_decay_system(self) -> bool:
        """Stop background memory decay processing"""
        await self.decay_system.stop_background_decay()
        return True

    async def get_decay_stats(self) -> Dict[str, Any]:
        """Get decay system status and statistics"""
        return self.decay_system.get_decay_stats()

    async def force_decay(self, persona_id: Optional[str] = None,
                         decay_rate: float = 0.1, time_factor: float = 1.0) -> Dict[str, Any]:
        """Force decay processing with custom parameters"""
        if persona_id:
            return await self.decay_system.force_decay_persona(persona_id, decay_rate)
        else:
            return await self.decay_system.run_decay_cycle()

    async def delete_persona_memories(self, persona_id: str) -> bool:
        """Delete all memories for a persona"""
        success = await self.vector_manager.delete_persona_memories(persona_id)
        if success:
            self.logger.info(f"Deleted all memories for persona {persona_id}")
        return success

    async def get_system_stats(self) -> Dict[str, Any]:
        """Get comprehensive memory system statistics"""
        vector_stats = await self.vector_manager.get_stats()
        decay_stats = self.decay_system.get_decay_stats()
        pruning_stats = self.pruning_system.get_pruning_stats()

        return {
            "vector_memory": vector_stats,
            "decay_system": decay_stats,
            "pruning_system": pruning_stats
        }