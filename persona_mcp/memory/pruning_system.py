"""
Memory Pruning System for Persona MCP

Automatically manages memory collections by removing low-importance memories
when collections exceed size limits. Uses intelligent algorithms to preserve
the most valuable memories while maintaining performance.
"""

import asyncio
import time
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta, timezone
import logging
from dataclasses import dataclass
from enum import Enum

from ..models import Memory
from ..persistence import VectorMemoryManager


class PruningStrategy(str, Enum):
    """Memory pruning strategies"""
    IMPORTANCE_ONLY = "importance_only"           # Pure importance-based pruning
    IMPORTANCE_ACCESS = "importance_access"       # Importance + access frequency
    IMPORTANCE_ACCESS_AGE = "importance_access_age"  # Importance + access + age
    LRU = "lru"                                  # Least Recently Used
    FIFO = "fifo"                                # First In, First Out


@dataclass
class PruningConfig:
    """Configuration for memory pruning behavior"""
    # Collection size limits
    max_memories_per_persona: int = 1000          # Hard limit per persona
    target_memories_per_persona: int = 800        # Target after pruning
    pruning_threshold: int = 900                  # Start pruning at this count
    
    # Pruning strategy and weights
    strategy: PruningStrategy = PruningStrategy.IMPORTANCE_ACCESS_AGE
    importance_weight: float = 0.6                # How much importance matters
    access_weight: float = 0.3                    # How much access frequency matters  
    age_weight: float = 0.1                       # How much recency matters
    
    # Importance thresholds
    min_importance_to_keep: float = 0.3           # Never delete above this
    max_importance_to_delete: float = 0.7         # Never delete above this
    
    # Access frequency thresholds
    high_access_threshold: int = 5                # Frequently accessed memories
    zero_access_grace_days: int = 30              # Keep unaccessed memories this long
    
    # Age considerations
    recent_memory_days: int = 7                   # Protect recent memories
    ancient_memory_days: int = 90                 # Aggressive pruning for old memories
    
    # Batch processing
    batch_size: int = 100                         # Process memories in batches
    max_prune_per_batch: int = 50                 # Max memories to delete per batch


@dataclass
class PruningMetrics:
    """Metrics from pruning operations"""
    total_memories_before: int = 0
    total_memories_after: int = 0
    memories_pruned: int = 0
    personas_processed: int = 0
    processing_time_seconds: float = 0.0
    average_importance_pruned: float = 0.0
    average_importance_kept: float = 0.0
    errors_encountered: int = 0


class MemoryPruningSystem:
    """Intelligent memory pruning and cleanup system"""
    
    def __init__(
        self,
        vector_memory: VectorMemoryManager,
        config: Optional[PruningConfig] = None
    ):
        self.vector_memory = vector_memory
        self.config = config or PruningConfig()
        self.logger = logging.getLogger(__name__)
        
        # Pruning state
        self.last_global_prune: Optional[datetime] = None
        self.persona_last_pruned: Dict[str, datetime] = {}
        self.pruning_in_progress: Dict[str, bool] = {}
        
        # Metrics tracking
        self.pruning_history: List[PruningMetrics] = []

    async def should_prune_persona(self, persona_id: str) -> bool:
        """Check if a persona's memory collection needs pruning"""
        try:
            # Check if pruning already in progress
            if self.pruning_in_progress.get(persona_id, False):
                return False
            
            # Get current memory stats
            stats = await self.vector_memory.get_memory_stats(persona_id)
            total_memories = stats.get("total_memories", 0)
            
            # Check size threshold
            if total_memories < self.config.pruning_threshold:
                return False
            
            # Check time since last pruning
            last_pruned = self.persona_last_pruned.get(persona_id)
            if last_pruned:
                time_since_prune = datetime.now(timezone.utc) - last_pruned
                if time_since_prune < timedelta(hours=1):  # Minimum 1 hour between prunes
                    return False
            
            self.logger.info(f"Persona {persona_id} needs pruning: {total_memories} memories")
            return True
            
        except Exception as e:
            self.logger.error(f"Error checking pruning need for {persona_id}: {e}")
            return False

    async def prune_persona_memories(
        self, 
        persona_id: str,
        force: bool = False
    ) -> PruningMetrics:
        """Prune memories for a specific persona"""
        
        metrics = PruningMetrics()
        start_time = time.time()
        
        try:
            # Prevent concurrent pruning
            if self.pruning_in_progress.get(persona_id, False) and not force:
                self.logger.warning(f"Pruning already in progress for {persona_id}")
                return metrics
            
            self.pruning_in_progress[persona_id] = True
            
            # Get all memories for the persona
            memories = await self._get_all_persona_memories(persona_id)
            metrics.total_memories_before = len(memories)
            
            if metrics.total_memories_before == 0:
                return metrics
            
            self.logger.info(f"Starting pruning for {persona_id}: {len(memories)} memories")
            
            # Calculate pruning scores
            scored_memories = await self._calculate_pruning_scores(memories)
            
            # Determine how many to prune
            target_count = min(self.config.target_memories_per_persona, len(memories))
            prune_count = max(0, len(memories) - target_count)
            
            if prune_count == 0:
                self.logger.info(f"No pruning needed for {persona_id}")
                return metrics
            
            # Select memories to prune
            to_prune = await self._select_memories_to_prune(scored_memories, prune_count)
            
            # Execute pruning
            pruned_count = await self._execute_pruning(persona_id, to_prune)
            
            # Update metrics
            metrics.memories_pruned = pruned_count
            metrics.total_memories_after = metrics.total_memories_before - pruned_count
            metrics.personas_processed = 1
            
            # Calculate importance statistics
            if to_prune:
                metrics.average_importance_pruned = sum(mem[1].importance for mem in to_prune) / len(to_prune)
            
            remaining_memories = [mem for mem in scored_memories if mem not in to_prune]
            if remaining_memories:
                metrics.average_importance_kept = sum(mem[1].importance for mem in remaining_memories) / len(remaining_memories)
            
            # Update tracking
            self.persona_last_pruned[persona_id] = datetime.now(timezone.utc)
            
            self.logger.info(
                f"Pruning completed for {persona_id}: "
                f"removed {pruned_count} memories, {metrics.total_memories_after} remaining"
            )
            
        except Exception as e:
            self.logger.error(f"Error pruning memories for {persona_id}: {e}")
            metrics.errors_encountered = 1
            
        finally:
            metrics.processing_time_seconds = time.time() - start_time
            self.pruning_in_progress[persona_id] = False
            self.pruning_history.append(metrics)
        
        return metrics

    async def _get_all_persona_memories(self, persona_id: str) -> List[Memory]:
        """Get all memories for a persona from ChromaDB"""
        try:
            # Use search with very broad query to get all memories
            all_memories = await self.vector_memory.search_memories(
                persona_id=persona_id,
                query="",  # Empty query to get all
                n_results=10000,  # Large number to get everything
                min_importance=0.0  # Include all importance levels
            )
            return all_memories
            
        except Exception as e:
            self.logger.error(f"Error getting memories for {persona_id}: {e}")
            return []

    async def _calculate_pruning_scores(
        self, 
        memories: List[Memory]
    ) -> List[Tuple[float, Memory]]:
        """Calculate pruning scores for memories (lower = more likely to be pruned)"""
        
        scored_memories = []
        current_time = datetime.now(timezone.utc)
        
        for memory in memories:
            score = 0.0
            
            # Importance component (0.0-1.0, weighted by config)
            importance_score = memory.importance * self.config.importance_weight
            score += importance_score
            
            # Access frequency component
            if self.config.strategy != PruningStrategy.IMPORTANCE_ONLY:
                access_score = min(memory.accessed_count / 10.0, 1.0)  # Normalize to 0-1
                score += access_score * self.config.access_weight
            
            # Age component (recent memories score higher)
            if self.config.strategy == PruningStrategy.IMPORTANCE_ACCESS_AGE:
                memory_age = (current_time - memory.created_at).days
                
                if memory_age <= self.config.recent_memory_days:
                    age_score = 1.0  # Protect recent memories
                elif memory_age >= self.config.ancient_memory_days:
                    age_score = 0.1  # Aggressive pruning for old memories
                else:
                    # Linear interpolation between recent and ancient
                    age_range = self.config.ancient_memory_days - self.config.recent_memory_days
                    age_position = memory_age - self.config.recent_memory_days
                    age_score = 1.0 - (age_position / age_range) * 0.9
                
                score += age_score * self.config.age_weight
            
            scored_memories.append((score, memory))
        
        # Sort by score (ascending - lowest scores will be pruned first)
        scored_memories.sort(key=lambda x: x[0])
        
        return scored_memories

    async def _select_memories_to_prune(
        self,
        scored_memories: List[Tuple[float, Memory]],
        prune_count: int
    ) -> List[Tuple[float, Memory]]:
        """Select which memories to prune based on scores and safety rules"""
        
        to_prune = []
        candidates = scored_memories.copy()  # Start with lowest scores
        
        for score, memory in candidates:
            if len(to_prune) >= prune_count:
                break
            
            # Safety checks - never prune these
            if memory.importance >= self.config.max_importance_to_delete:
                continue
                
            if memory.accessed_count >= self.config.high_access_threshold:
                continue
            
            # Check age-based protection for unaccessed memories
            if memory.accessed_count == 0:
                age_days = (datetime.now(timezone.utc) - memory.created_at).days
                if age_days < self.config.zero_access_grace_days:
                    continue
            
            # Memory is safe to prune
            to_prune.append((score, memory))
        
        self.logger.info(
            f"Selected {len(to_prune)} memories for pruning "
            f"(requested {prune_count}, safety rules protected {prune_count - len(to_prune)})"
        )
        
        return to_prune

    async def _execute_pruning(
        self,
        persona_id: str,
        to_prune: List[Tuple[float, Memory]]
    ) -> int:
        """Execute the actual deletion of memories"""
        
        if not to_prune:
            return 0
        
        # Get collection
        if persona_id not in self.vector_memory.collections:
            await self.vector_memory.initialize_persona_memory(persona_id)
        
        collection = self.vector_memory.collections[persona_id]
        
        # Extract memory IDs to delete
        memory_ids = [memory.id for _, memory in to_prune]
        
        try:
            # Delete from ChromaDB in batches
            batch_size = self.config.batch_size
            deleted_count = 0
            
            for i in range(0, len(memory_ids), batch_size):
                batch_ids = memory_ids[i:i + batch_size]
                
                # Execute deletion
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(
                    self.vector_memory.executor,
                    lambda: collection.delete(ids=batch_ids)
                )
                
                deleted_count += len(batch_ids)
                
                # Small delay between batches to avoid overwhelming ChromaDB
                if i + batch_size < len(memory_ids):
                    await asyncio.sleep(0.1)
            
            self.logger.info(f"Successfully deleted {deleted_count} memories for {persona_id}")
            return deleted_count
            
        except Exception as e:
            self.logger.error(f"Error deleting memories for {persona_id}: {e}")
            return 0

    async def prune_all_personas(self) -> PruningMetrics:
        """Run pruning across all personas that need it"""
        
        total_metrics = PruningMetrics()
        start_time = time.time()
        
        try:
            # Get all persona collections
            persona_ids = list(self.vector_memory.collections.keys())
            
            self.logger.info(f"Starting global pruning for {len(persona_ids)} personas")
            
            for persona_id in persona_ids:
                if await self.should_prune_persona(persona_id):
                    persona_metrics = await self.prune_persona_memories(persona_id)
                    
                    # Aggregate metrics
                    total_metrics.total_memories_before += persona_metrics.total_memories_before
                    total_metrics.total_memories_after += persona_metrics.total_memories_after
                    total_metrics.memories_pruned += persona_metrics.memories_pruned
                    total_metrics.personas_processed += persona_metrics.personas_processed
                    total_metrics.errors_encountered += persona_metrics.errors_encountered
            
            # Update global pruning timestamp
            self.last_global_prune = datetime.now(timezone.utc)
            
        except Exception as e:
            self.logger.error(f"Error in global pruning: {e}")
            total_metrics.errors_encountered += 1
        
        finally:
            total_metrics.processing_time_seconds = time.time() - start_time
            
        self.logger.info(
            f"Global pruning completed: {total_metrics.personas_processed} personas, "
            f"{total_metrics.memories_pruned} memories pruned in "
            f"{total_metrics.processing_time_seconds:.2f}s"
        )
        
        return total_metrics

    async def get_pruning_recommendations(self, persona_id: str) -> Dict[str, any]:
        """Get pruning recommendations without executing"""
        
        try:
            memories = await self._get_all_persona_memories(persona_id)
            scored_memories = await self._calculate_pruning_scores(memories)
            
            if len(memories) <= self.config.target_memories_per_persona:
                return {
                    "needs_pruning": False,
                    "current_count": len(memories),
                    "target_count": self.config.target_memories_per_persona,
                    "recommendation": "No pruning needed"
                }
            
            prune_count = len(memories) - self.config.target_memories_per_persona
            to_prune = await self._select_memories_to_prune(scored_memories, prune_count)
            
            # Analyze what would be pruned
            if to_prune:
                avg_importance = sum(mem.importance for _, mem in to_prune) / len(to_prune)
                importance_range = (
                    min(mem.importance for _, mem in to_prune),
                    max(mem.importance for _, mem in to_prune)
                )
            else:
                avg_importance = 0.0
                importance_range = (0.0, 0.0)
            
            return {
                "needs_pruning": True,
                "current_count": len(memories),
                "target_count": self.config.target_memories_per_persona,
                "would_prune": len(to_prune),
                "average_importance_to_prune": avg_importance,
                "importance_range_to_prune": importance_range,
                "recommendation": f"Would prune {len(to_prune)} memories with average importance {avg_importance:.3f}"
            }
            
        except Exception as e:
            self.logger.error(f"Error getting pruning recommendations for {persona_id}: {e}")
            return {"error": str(e)}

    async def emergency_prune(self, persona_id: str, target_count: int) -> PruningMetrics:
        """Emergency pruning to drastically reduce memory count"""
        
        # Temporarily override config for aggressive pruning
        original_config = self.config
        emergency_config = PruningConfig(
            target_memories_per_persona=target_count,
            max_importance_to_delete=0.9,  # More aggressive
            min_importance_to_keep=0.7,   # Higher threshold
            importance_weight=0.8,         # Focus more on importance
            access_weight=0.2,
            age_weight=0.0
        )
        
        self.config = emergency_config
        
        try:
            metrics = await self.prune_persona_memories(persona_id, force=True)
            self.logger.warning(
                f"Emergency pruning completed for {persona_id}: "
                f"{metrics.memories_pruned} memories removed"
            )
            return metrics
            
        finally:
            self.config = original_config

    def get_pruning_stats(self) -> Dict[str, any]:
        """Get overall pruning system statistics"""
        
        if not self.pruning_history:
            return {"message": "No pruning operations performed yet"}
        
        total_pruned = sum(m.memories_pruned for m in self.pruning_history)
        total_processed = sum(m.personas_processed for m in self.pruning_history)
        avg_processing_time = sum(m.processing_time_seconds for m in self.pruning_history) / len(self.pruning_history)
        
        return {
            "total_pruning_operations": len(self.pruning_history),
            "total_memories_pruned": total_pruned,
            "total_personas_processed": total_processed,
            "average_processing_time": avg_processing_time,
            "last_global_prune": self.last_global_prune.isoformat() if self.last_global_prune else None,
            "personas_last_pruned": {
                pid: dt.isoformat() for pid, dt in self.persona_last_pruned.items()
            }
        }