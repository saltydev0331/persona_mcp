"""
ChromaDB vector memory management for long-term persona memory
"""

import chromadb
from chromadb.config import Settings
from typing import List, Dict, Any, Optional
import uuid
from pathlib import Path
import asyncio
import time
import logging

from ..models import Memory


class VectorMemoryManager:
    """Manages vector-based memory storage using ChromaDB"""

    def __init__(self, persist_directory: str = "data/vector_memory"):
        self.persist_directory = Path(persist_directory)
        self.persist_directory.mkdir(parents=True, exist_ok=True)
        
        # Initialize ChromaDB client with optimized settings
        self.client = chromadb.PersistentClient(
            path=str(self.persist_directory),
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True,
                # Optimize ChromaDB for async performance
                chroma_server_nofile=65536,  # Increase file descriptor limit
                chroma_segment_cache_policy="LRU"  # Optimize segment caching
            )
        )
        
        # Memory collections by persona (lazy loaded)
        self.collections = {}
        
        # Performance tracking
        self.logger = logging.getLogger(__name__)

    def _get_collection_name(self, persona_id: str) -> str:
        """Generate collection name for persona"""
        return f"persona_{persona_id.replace('-', '_')}"

    async def initialize_persona_memory(self, persona_id: str) -> bool:
        """Initialize memory collection for a persona (with lazy loading)"""
        try:
            # Check if already loaded
            if persona_id in self.collections:
                return True
                
            collection_name = self._get_collection_name(persona_id)
            
            # Direct ChromaDB call (no ThreadPoolExecutor overhead)
            # ChromaDB operations are fast enough for direct async usage
            start_time = time.time()
            collection = await asyncio.to_thread(self._create_collection, collection_name)
            
            load_time = (time.time() - start_time) * 1000  # Convert to ms
            self.logger.debug(f"Loaded collection '{collection_name}' in {load_time:.2f}ms")
            
            self.collections[persona_id] = collection
            return True
            
        except Exception as e:
            self.logger.error(f"Error initializing memory for persona {persona_id}: {e}")
            return False

    def _create_collection(self, collection_name: str):
        """Create or get ChromaDB collection (sync operation)"""
        try:
            # Try to get existing collection
            return self.client.get_collection(collection_name)
        except:
            # Create new collection if it doesn't exist
            return self.client.create_collection(
                name=collection_name,
                metadata={"description": f"Memory collection for persona"}
            )

    async def store_memory(self, memory: Memory) -> bool:
        """Store a memory with vector embedding (optimized)"""
        try:
            # Lazy load collection if needed
            if memory.persona_id not in self.collections:
                await self.initialize_persona_memory(memory.persona_id)

            collection = self.collections[memory.persona_id]
            
            # Prepare metadata (optimized structure)
            metadata = {
                "memory_type": memory.memory_type,
                "importance": memory.importance,
                "emotional_valence": memory.emotional_valence,
                "related_personas": ",".join(memory.related_personas) if memory.related_personas else "",
                "created_at": memory.created_at.isoformat(),
                "accessed_count": memory.accessed_count,
                **memory.metadata
            }

            # Direct ChromaDB operation (no ThreadPoolExecutor overhead)
            start_time = time.time()
            await asyncio.to_thread(
                collection.add,
                documents=[memory.content],
                metadatas=[metadata],
                ids=[memory.id]
            )
            
            store_time = (time.time() - start_time) * 1000  # Convert to ms
            self.logger.debug(f"Stored memory '{memory.id}' in {store_time:.2f}ms")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error storing memory {memory.id}: {e}")
            return False

    async def search_memories(
        self, 
        persona_id: str, 
        query: str, 
        n_results: int = 5,
        memory_type: Optional[str] = None,
        min_importance: float = 0.0
    ) -> List[Memory]:
        """Search for relevant memories (optimized)"""
        try:
            # Lazy load collection if needed
            if persona_id not in self.collections:
                await self.initialize_persona_memory(persona_id)
                return []

            collection = self.collections[persona_id]
            
            # Build optimized where clause for filtering
            where_clause = {}
            if min_importance > 0.0:
                where_clause["importance"] = {"$gte": min_importance}
            if memory_type:
                where_clause["memory_type"] = memory_type

            # Perform optimized vector search
            start_time = time.time()
            results = await asyncio.to_thread(
                collection.query,
                query_texts=[query],
                n_results=n_results,
                where=where_clause if where_clause else None
            )
            
            search_time = (time.time() - start_time) * 1000  # Convert to ms
            
            # Fast conversion to Memory objects
            memories = []
            if results and results["documents"] and results["documents"][0]:
                for i, doc in enumerate(results["documents"][0]):
                    metadata = results["metadatas"][0][i]
                    memory_id = results["ids"][0][i]
                    
                    # Optimized related_personas parsing
                    related_personas_str = metadata.get("related_personas", "")
                    related_personas = related_personas_str.split(",") if related_personas_str else []
                    
                    memory = Memory(
                        id=memory_id,
                        persona_id=persona_id,
                        content=doc,
                        memory_type=metadata.get("memory_type", "conversation"),
                        importance=float(metadata.get("importance", 0.5)),
                        emotional_valence=float(metadata.get("emotional_valence", 0.0)),
                        related_personas=related_personas,
                        metadata={k: v for k, v in metadata.items() 
                                 if k not in {"memory_type", "importance", "emotional_valence", 
                                            "related_personas", "created_at", "accessed_count"}},
                        accessed_count=int(metadata.get("accessed_count", 0))
                    )
                    memories.append(memory)

            self.logger.debug(f"Searched {len(memories)} memories for '{persona_id}' in {search_time:.2f}ms")
            return memories
            
        except Exception as e:
            self.logger.error(f"Error searching memories for persona {persona_id}: {e}")
            return []

    async def update_memory_access(self, persona_id: str, memory_id: str) -> bool:
        """Update memory access tracking (optimized)"""
        try:
            if persona_id not in self.collections:
                return False

            collection = self.collections[persona_id]
            
            # Get current memory (direct async call)
            result = await asyncio.to_thread(collection.get, ids=[memory_id])
            
            if not result["metadatas"]:
                return False

            # Update access count efficiently
            metadata = result["metadatas"][0].copy()  # Avoid mutation issues
            metadata["accessed_count"] = int(metadata.get("accessed_count", 0)) + 1
            metadata["last_accessed"] = time.time()  # Use actual timestamp

            # Optimized update operation
            await asyncio.to_thread(
                collection.update,
                ids=[memory_id],
                metadatas=[metadata]
            )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error updating memory access for {memory_id}: {e}")
            return False

    async def get_memory_stats(self, persona_id: str) -> Dict[str, Any]:
        """Get memory statistics for a persona (optimized)"""
        try:
            if persona_id not in self.collections:
                return {"total_memories": 0}

            collection = self.collections[persona_id]
            
            # Fast operations using direct async calls
            start_time = time.time()
            
            # Get count and all memories in parallel
            count_task = asyncio.to_thread(collection.count)
            memories_task = asyncio.to_thread(collection.get)
            
            count, all_memories = await asyncio.gather(count_task, memories_task)
            
            if not all_memories["metadatas"]:
                return {"total_memories": 0}

            # Efficient statistics calculation
            metadatas = all_memories["metadatas"]
            importance_scores = [float(m.get("importance", 0.5)) for m in metadatas]
            memory_types = [m.get("memory_type", "conversation") for m in metadatas]
            
            # Use collections.Counter for efficient counting
            from collections import Counter
            type_counts = Counter(memory_types)
            
            stats_time = (time.time() - start_time) * 1000  # Convert to ms
            
            result = {
                "total_memories": count,
                "avg_importance": sum(importance_scores) / len(importance_scores) if importance_scores else 0,
                "memory_types": dict(type_counts),
                "high_importance_count": sum(1 for score in importance_scores if score >= 0.7),
                "stats_calculation_time_ms": round(stats_time, 2)
            }
            
            self.logger.debug(f"Calculated stats for '{persona_id}' in {stats_time:.2f}ms")
            return result
            
        except Exception as e:
            self.logger.error(f"Error getting memory stats for persona {persona_id}: {e}")
            return {"total_memories": 0, "error": str(e)}

    async def cleanup_old_memories(self, persona_id: str, max_memories: int = 1000) -> int:
        """Remove least important/accessed memories to stay under limit (optimized)"""
        try:
            if persona_id not in self.collections:
                return 0

            collection = self.collections[persona_id]
            
            start_time = time.time()
            
            # Parallel operations for count and memory retrieval
            count_task = asyncio.to_thread(collection.count)
            memories_task = asyncio.to_thread(collection.get)
            
            count, all_memories = await asyncio.gather(count_task, memories_task)
            
            if count <= max_memories:
                return 0

            # Fast priority calculation
            memory_priorities = []
            metadatas = all_memories["metadatas"]
            ids = all_memories["ids"]
            
            for i, metadata in enumerate(metadatas):
                importance = float(metadata.get("importance", 0.5))
                access_count = int(metadata.get("accessed_count", 0))
                
                # Optimized priority calculation
                priority = importance + (access_count * 0.01)  # Reduced weight for faster calc
                memory_priorities.append((priority, ids[i]))

            # Efficient sorting and selection
            memory_priorities.sort()
            memories_to_remove = count - max_memories
            remove_ids = [memory_id for _, memory_id in memory_priorities[:memories_to_remove]]
            
            if remove_ids:
                # Batch deletion for efficiency
                await asyncio.to_thread(collection.delete, ids=remove_ids)
            
            cleanup_time = (time.time() - start_time) * 1000  # Convert to ms
            self.logger.info(f"Cleaned up {len(remove_ids)} memories for '{persona_id}' in {cleanup_time:.2f}ms")
            
            return len(remove_ids)
            
        except Exception as e:
            self.logger.error(f"Error cleaning up memories for persona {persona_id}: {e}")
            return 0

    async def close(self):
        """Clean up resources (optimized)"""
        try:
            # Clear collections cache
            self.collections.clear()
            
            # ChromaDB client cleanup is automatic
            self.logger.debug("VectorMemoryManager closed successfully")
        except Exception as e:
            self.logger.error(f"Error closing VectorMemoryManager: {e}")