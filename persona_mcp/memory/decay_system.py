"""
Memory Decay System for Persona MCP

Implements automatic memory aging, decay, and background cleanup.
Gradually reduces importance of old, unaccessed memories and triggers
automatic pruning when needed.
"""

import asyncio
import time
import math
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import logging

from ..models import Memory
from ..persistence import VectorMemoryManager
from .pruning_system import MemoryPruningSystem, PruningConfig


class DecayMode(str, Enum):
    """Memory decay modes"""
    NONE = "none"                    # No decay
    LINEAR = "linear"                # Linear importance reduction over time
    EXPONENTIAL = "exponential"      # Exponential decay (rapid initial decay)
    LOGARITHMIC = "logarithmic"      # Logarithmic decay (slow then fast)
    ACCESS_BASED = "access_based"    # Decay based on access patterns


@dataclass 
class DecayConfig:
    """Configuration for memory decay behavior"""
    # Decay mode and timing
    mode: DecayMode = DecayMode.ACCESS_BASED
    decay_interval_hours: int = 6          # How often to run decay updates
    
    # Decay parameters
    max_decay_days: int = 90              # Full decay after this many days
    min_importance_floor: float = 0.1     # Never decay below this importance
    protected_importance: float = 0.8     # Don't decay memories above this
    
    # Access-based decay
    access_protection_days: int = 7       # Recent access protects from decay
    high_access_threshold: int = 3        # Frequently accessed memories
    zero_access_decay_multiplier: float = 2.0  # Faster decay for never-accessed
    
    # Linear decay parameters
    linear_decay_rate: float = 0.01       # Importance lost per day (linear)
    
    # Exponential decay parameters  
    exponential_half_life_days: int = 30  # Half importance after this many days
    
    # Auto-pruning triggers
    enable_auto_pruning: bool = True      # Enable automatic pruning
    auto_prune_threshold: int = 1000      # Auto-prune when this many memories
    auto_prune_importance_threshold: float = 0.3  # Only auto-prune below this
    
    # Background processing
    max_personas_per_cycle: int = 5       # Process this many personas per cycle
    max_memories_per_batch: int = 100     # Update this many memories at once


@dataclass
class DecayMetrics:
    """Metrics from decay processing"""
    personas_processed: int = 0
    memories_processed: int = 0
    memories_decayed: int = 0
    average_decay_amount: float = 0.0
    auto_prunes_triggered: int = 0
    processing_time_seconds: float = 0.0
    errors_encountered: int = 0
    last_run_time: Optional[datetime] = None


class MemoryDecaySystem:
    """Automatic memory decay and aging system"""
    
    def __init__(
        self,
        vector_memory: VectorMemoryManager,
        pruning_system: MemoryPruningSystem,
        config: Optional[DecayConfig] = None
    ):
        self.vector_memory = vector_memory
        self.pruning_system = pruning_system
        self.config = config or DecayConfig()
        self.logger = logging.getLogger(__name__)
        
        # Decay state tracking
        self.last_decay_run: Optional[datetime] = None
        self.persona_last_decayed: Dict[str, datetime] = {}
        self.decay_in_progress: bool = False
        
        # Metrics and history
        self.decay_history: List[DecayMetrics] = []
        self.background_task: Optional[asyncio.Task] = None
        self.running: bool = False

    async def start_background_decay(self):
        """Start the background decay processing task"""
        if self.background_task and not self.background_task.done():
            self.logger.warning("Background decay already running")
            return
        
        self.running = True
        self.background_task = asyncio.create_task(self._background_decay_loop())
        self.logger.info(f"Started background memory decay (interval: {self.config.decay_interval_hours}h)")

    async def stop_background_decay(self):
        """Stop the background decay processing"""
        self.running = False
        if self.background_task:
            self.background_task.cancel()
            try:
                await self.background_task
            except asyncio.CancelledError:
                pass
        self.logger.info("Stopped background memory decay")

    async def _background_decay_loop(self):
        """Main background loop for memory decay processing"""
        while self.running:
            try:
                # Wait for the configured interval
                await asyncio.sleep(self.config.decay_interval_hours * 3600)
                
                if not self.running:
                    break
                
                # Run decay cycle
                self.logger.info("Starting background memory decay cycle")
                await self.run_decay_cycle()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in background decay loop: {e}")
                # Continue running despite errors
                await asyncio.sleep(300)  # Wait 5 minutes before retrying

    async def run_decay_cycle(self) -> DecayMetrics:
        """Run a complete decay cycle across eligible personas"""
        if self.decay_in_progress:
            self.logger.warning("Decay cycle already in progress")
            return DecayMetrics()
        
        self.decay_in_progress = True
        metrics = DecayMetrics()
        start_time = time.time()
        
        try:
            # Get all persona collections
            persona_ids = list(self.vector_memory.collections.keys())
            
            # Limit personas processed per cycle to avoid overwhelming system
            if len(persona_ids) > self.config.max_personas_per_cycle:
                # Rotate through personas based on last decay time
                persona_ids = self._select_personas_for_decay(persona_ids)
            
            self.logger.info(f"Running decay cycle for {len(persona_ids)} personas")
            
            for persona_id in persona_ids:
                try:
                    persona_metrics = await self.decay_persona_memories(persona_id)
                    
                    # Aggregate metrics
                    metrics.personas_processed += 1
                    metrics.memories_processed += persona_metrics.memories_processed
                    metrics.memories_decayed += persona_metrics.memories_decayed
                    if persona_metrics.memories_decayed > 0:
                        metrics.average_decay_amount += persona_metrics.average_decay_amount
                    metrics.auto_prunes_triggered += persona_metrics.auto_prunes_triggered
                    metrics.errors_encountered += persona_metrics.errors_encountered
                    
                except Exception as e:
                    self.logger.error(f"Error decaying memories for {persona_id}: {e}")
                    metrics.errors_encountered += 1
            
            # Calculate average decay amount
            if metrics.memories_decayed > 0:
                metrics.average_decay_amount /= len([p for p in persona_ids 
                                                   if p in self.persona_last_decayed])
            
            self.last_decay_run = datetime.utcnow()
            metrics.last_run_time = self.last_decay_run
            
            self.logger.info(
                f"Decay cycle completed: {metrics.personas_processed} personas, "
                f"{metrics.memories_decayed} memories decayed, "
                f"{metrics.auto_prunes_triggered} auto-prunes triggered"
            )
            
        except Exception as e:
            self.logger.error(f"Error in decay cycle: {e}")
            metrics.errors_encountered += 1
            
        finally:
            metrics.processing_time_seconds = time.time() - start_time
            self.decay_in_progress = False
            self.decay_history.append(metrics)
        
        return metrics

    def _select_personas_for_decay(self, persona_ids: List[str]) -> List[str]:
        """Select personas for decay based on last decay time"""
        # Sort by last decay time (oldest first, never decayed first)
        def decay_priority(persona_id: str) -> float:
            last_decay = self.persona_last_decayed.get(persona_id)
            if not last_decay:
                return 0  # Highest priority - never decayed
            return (datetime.utcnow() - last_decay).total_seconds()
        
        sorted_personas = sorted(persona_ids, key=decay_priority, reverse=True)
        return sorted_personas[:self.config.max_personas_per_cycle]

    async def decay_persona_memories(self, persona_id: str) -> DecayMetrics:
        """Apply decay to memories for a specific persona"""
        metrics = DecayMetrics()
        
        try:
            # Get all memories for the persona
            memories = await self._get_all_persona_memories(persona_id)
            metrics.memories_processed = len(memories)
            
            if not memories:
                return metrics
            
            # Apply decay to each memory
            decayed_memories = []
            total_decay = 0.0
            
            for memory in memories:
                original_importance = memory.importance
                new_importance = self._calculate_decayed_importance(memory)
                
                if new_importance != original_importance:
                    memory.importance = new_importance
                    decayed_memories.append(memory)
                    total_decay += (original_importance - new_importance)
                    metrics.memories_decayed += 1
            
            # Update memories in ChromaDB if any decayed
            if decayed_memories:
                await self._update_memory_importance(persona_id, decayed_memories)
                metrics.average_decay_amount = total_decay / len(decayed_memories)
                
                self.logger.info(
                    f"Decayed {len(decayed_memories)} memories for {persona_id}, "
                    f"average decay: {metrics.average_decay_amount:.3f}"
                )
            
            # Check if auto-pruning should be triggered
            if self.config.enable_auto_pruning:
                stats = await self.vector_memory.get_memory_stats(persona_id)
                total_memories = stats.get("total_memories", 0)
                
                if total_memories >= self.config.auto_prune_threshold:
                    # Count low-importance memories
                    low_importance_count = sum(
                        1 for m in memories 
                        if m.importance <= self.config.auto_prune_importance_threshold
                    )
                    
                    if low_importance_count > 50:  # Only auto-prune if significant cleanup possible
                        self.logger.info(f"Triggering auto-prune for {persona_id}: {total_memories} memories")
                        await self.pruning_system.prune_persona_memories(persona_id)
                        metrics.auto_prunes_triggered = 1
            
            # Update tracking
            self.persona_last_decayed[persona_id] = datetime.utcnow()
            
        except Exception as e:
            self.logger.error(f"Error decaying persona {persona_id}: {e}")
            metrics.errors_encountered = 1
        
        return metrics

    def _calculate_decayed_importance(self, memory: Memory) -> float:
        """Calculate the decayed importance for a memory"""
        if self.config.mode == DecayMode.NONE:
            return memory.importance
        
        # Don't decay protected memories
        if memory.importance >= self.config.protected_importance:
            return memory.importance
        
        # Calculate age in days
        age_days = (datetime.utcnow() - memory.created_at).days
        
        # Check for recent access protection
        if hasattr(memory, 'last_accessed') and memory.last_accessed:
            days_since_access = (datetime.utcnow() - memory.last_accessed).days
            if days_since_access <= self.config.access_protection_days:
                return memory.importance  # Protected by recent access
        
        # Apply decay based on mode
        decay_factor = self._calculate_decay_factor(memory, age_days)
        
        # Apply access-based modifiers
        if self.config.mode == DecayMode.ACCESS_BASED:
            if memory.accessed_count == 0:
                decay_factor *= self.config.zero_access_decay_multiplier
            elif memory.accessed_count >= self.config.high_access_threshold:
                decay_factor *= 0.5  # Reduce decay for frequently accessed
        
        # Calculate new importance
        importance_loss = memory.importance * decay_factor
        new_importance = memory.importance - importance_loss
        
        # Apply floor
        new_importance = max(new_importance, self.config.min_importance_floor)
        
        return round(new_importance, 3)

    def _calculate_decay_factor(self, memory: Memory, age_days: int) -> float:
        """Calculate the decay factor based on age and mode"""
        if age_days <= 0:
            return 0.0
        
        if age_days >= self.config.max_decay_days:
            return 0.8  # Maximum decay but not complete elimination
        
        if self.config.mode == DecayMode.LINEAR:
            return min(age_days * self.config.linear_decay_rate, 0.8)
        
        elif self.config.mode == DecayMode.EXPONENTIAL:
            # Half-life exponential decay
            half_life = self.config.exponential_half_life_days
            return 1 - math.pow(0.5, age_days / half_life)
        
        elif self.config.mode == DecayMode.LOGARITHMIC:
            # Slow start, then faster decay
            return min(math.log(1 + age_days) / math.log(1 + self.config.max_decay_days), 0.8)
        
        elif self.config.mode == DecayMode.ACCESS_BASED:
            # Moderate exponential decay, modified by access patterns
            base_decay = 1 - math.pow(0.7, age_days / 30)  # 30-day half life at 70%
            return min(base_decay, 0.6)  # Gentler max decay for access-based
        
        return 0.0

    async def _get_all_persona_memories(self, persona_id: str) -> List[Memory]:
        """Get all memories for a persona"""
        try:
            return await self.vector_memory.search_memories(
                persona_id=persona_id,
                query="",  # Empty query to get all
                n_results=10000,  # Large number
                min_importance=0.0
            )
        except Exception as e:
            self.logger.error(f"Error getting memories for {persona_id}: {e}")
            return []

    async def _update_memory_importance(self, persona_id: str, memories: List[Memory]):
        """Update memory importance in ChromaDB"""
        try:
            if persona_id not in self.vector_memory.collections:
                return
            
            collection = self.vector_memory.collections[persona_id]
            
            # Process in batches
            batch_size = self.config.max_memories_per_batch
            for i in range(0, len(memories), batch_size):
                batch = memories[i:i + batch_size]
                
                # Prepare batch update data
                ids = [m.id for m in batch]
                metadatas = []
                
                for memory in batch:
                    metadata = {
                        "memory_type": memory.memory_type,
                        "importance": memory.importance,  # Updated importance
                        "emotional_valence": memory.emotional_valence,
                        "related_personas": ",".join(memory.related_personas),
                        "created_at": memory.created_at.isoformat(),
                        "accessed_count": memory.accessed_count,
                        **memory.metadata
                    }
                    metadatas.append(metadata)
                
                # Update in ChromaDB
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(
                    self.vector_memory.executor,
                    lambda: collection.update(ids=ids, metadatas=metadatas)
                )
                
                # Small delay between batches
                if i + batch_size < len(memories):
                    await asyncio.sleep(0.1)
                    
        except Exception as e:
            self.logger.error(f"Error updating memory importance for {persona_id}: {e}")

    async def force_decay_persona(self, persona_id: str, decay_factor: float = 0.1) -> DecayMetrics:
        """Force decay on a specific persona with custom factor"""
        memories = await self._get_all_persona_memories(persona_id)
        
        decayed_memories = []
        for memory in memories:
            if memory.importance > self.config.min_importance_floor:
                original = memory.importance
                memory.importance = max(
                    original * (1 - decay_factor),
                    self.config.min_importance_floor
                )
                if memory.importance != original:
                    decayed_memories.append(memory)
        
        if decayed_memories:
            await self._update_memory_importance(persona_id, decayed_memories)
        
        metrics = DecayMetrics()
        metrics.memories_processed = len(memories)
        metrics.memories_decayed = len(decayed_memories)
        if decayed_memories:
            metrics.average_decay_amount = decay_factor
        
        self.logger.info(f"Force decayed {len(decayed_memories)} memories for {persona_id}")
        return metrics

    def get_decay_stats(self) -> Dict[str, any]:
        """Get decay system statistics"""
        if not self.decay_history:
            return {
                "message": "No decay cycles have run yet",
                "background_running": self.running,
                "config": {
                    "mode": self.config.mode,
                    "interval_hours": self.config.decay_interval_hours,
                    "auto_pruning": self.config.enable_auto_pruning
                }
            }
        
        recent_metrics = self.decay_history[-1]
        total_cycles = len(self.decay_history)
        total_decayed = sum(m.memories_decayed for m in self.decay_history)
        total_auto_prunes = sum(m.auto_prunes_triggered for m in self.decay_history)
        
        return {
            "background_running": self.running,
            "last_run": recent_metrics.last_run_time.isoformat() if recent_metrics.last_run_time else None,
            "total_decay_cycles": total_cycles,
            "total_memories_decayed": total_decayed,
            "total_auto_prunes_triggered": total_auto_prunes,
            "recent_cycle": {
                "personas_processed": recent_metrics.personas_processed,
                "memories_decayed": recent_metrics.memories_decayed,
                "average_decay": recent_metrics.average_decay_amount,
                "processing_time": recent_metrics.processing_time_seconds
            },
            "config": {
                "mode": self.config.mode,
                "interval_hours": self.config.decay_interval_hours,
                "max_decay_days": self.config.max_decay_days,
                "auto_pruning": self.config.enable_auto_pruning,
                "auto_prune_threshold": self.config.auto_prune_threshold
            }
        }