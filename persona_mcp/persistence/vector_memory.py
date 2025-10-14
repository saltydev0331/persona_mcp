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
                "visibility": getattr(memory, 'visibility', 'private'),  # Handle new field
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
                        visibility=metadata.get("visibility", "private"),  # Include visibility field
                        metadata={k: v for k, v in metadata.items() 
                                 if k not in {"memory_type", "importance", "emotional_valence", 
                                            "related_personas", "created_at", "accessed_count", "visibility"}},
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
            
            # Count memories created today
            from datetime import datetime, timezone
            today = datetime.now(timezone.utc).date()
            created_today = 0
            
            for metadata in metadatas:
                created_at_str = metadata.get("created_at")
                if created_at_str:
                    try:
                        created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                        if created_at.date() == today:
                            created_today += 1
                    except (ValueError, AttributeError):
                        # Skip invalid dates
                        pass
            
            stats_time = (time.time() - start_time) * 1000  # Convert to ms
            
            result = {
                "total_memories": count,
                "avg_importance": sum(importance_scores) / len(importance_scores) if importance_scores else 0,
                "memory_types": dict(type_counts),
                "high_importance_count": sum(1 for score in importance_scores if score >= 0.7),
                "created_today": created_today,
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

    async def search_cross_persona_memories(
        self, 
        requesting_persona_id: str,
        query: str,
        n_results: int = 5,
        min_importance: float = 0.6,
        include_shared: bool = True,
        include_public: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Search memories across all personas that are accessible to the requesting persona.
        
        Returns shared and public memories from other personas, plus all memories from
        personas listed in related_personas field.
        """
        try:
            all_results = []
            
            # First get the requesting persona's own memories
            own_memories = await self.search_memories(
                persona_id=requesting_persona_id,
                query=query,
                n_results=n_results,
                min_importance=min_importance
            )
            
            # Convert own memories to result dictionaries (apply visibility filtering)
            for memory in own_memories:
                # Apply visibility filtering consistently across all memories
                memory_visibility = memory.visibility
                should_include = False
                
                if include_shared and memory_visibility == "shared":
                    should_include = True
                elif include_public and memory_visibility == "public":
                    should_include = True
                # Note: Private memories are excluded even from own persona in cross-persona search
                # This makes the filtering consistent - cross-persona search only returns shared/public
                    
                if should_include:
                    result = {
                        "memory_id": memory.id,
                        "content": memory.content,
                        "similarity": 1.0,  # Own memories get perfect similarity
                        "importance": memory.importance,
                        "memory_type": memory.memory_type,
                        "created_at": memory.created_at.isoformat(),
                        "visibility": memory.visibility,
                        "source": "own",
                        "source_persona": requesting_persona_id
                    }
                    all_results.append(result)
            
            # Search across other personas for shared/public memories
            self.logger.debug(f"Cross-persona search: {len(self.collections)} collections, requesting persona: {requesting_persona_id}")
            for persona_id in self.collections.keys():
                if persona_id == requesting_persona_id:
                    continue
                self.logger.debug(f"Searching collection {persona_id}")
                    
                try:
                    collection = self.collections[persona_id]
                    
                    # ChromaDB doesn't support $or/$and operators, so do separate queries
                    all_persona_results = []
                    
                    # Query for shared memories
                    if include_shared:
                        try:
                            shared_results = await asyncio.to_thread(
                                collection.query,
                                query_texts=[query],
                                n_results=min(n_results, 10),
                                where={"visibility": "shared"},  # Simplified to single condition
                                include=['metadatas', 'documents', 'distances']
                            )
                            self.logger.debug(f"Shared query for {persona_id} found {len(shared_results.get('documents', [[]])[0]) if shared_results else 0} results")
                            if shared_results and shared_results.get('documents') and shared_results['documents'][0]:
                                all_persona_results.append(shared_results)
                        except Exception as e:
                            self.logger.debug(f"Shared query failed for {persona_id}: {e}")
                    
                    # Query for public memories
                    if include_public:
                        try:
                            public_results = await asyncio.to_thread(
                                collection.query,
                                query_texts=[query],
                                n_results=min(n_results, 10),
                                where={"visibility": "public"},  # Simplified to single condition
                                include=['metadatas', 'documents', 'distances']
                            )
                            self.logger.debug(f"Public query for {persona_id} found {len(public_results.get('documents', [[]])[0]) if public_results else 0} results")
                            if public_results and public_results.get('documents') and public_results['documents'][0]:
                                all_persona_results.append(public_results)
                        except Exception as e:
                            self.logger.debug(f"Public query failed for {persona_id}: {e}")
                    
                    # Process all results from this persona
                    for results in all_persona_results:
                        # Process results from this query
                        for i in range(len(results['documents'][0])):
                            metadata = results['metadatas'][0][i]
                            importance = metadata.get('importance', 0.5)
                            
                            # Filter by importance since we can't do it in ChromaDB query
                            if importance < min_importance:
                                continue
                                
                            content = results['documents'][0][i]
                            distance = results['distances'][0][i]
                            similarity = 1.0 - distance
                            
                            result = {
                                "memory_id": results['ids'][0][i],
                                "content": content,
                                "similarity": similarity,
                                "importance": importance,
                                "memory_type": metadata.get('memory_type', 'conversation'),
                                "created_at": metadata.get('created_at'),
                                "visibility": metadata.get('visibility', 'private'),
                                "source": "cross_persona",
                                "source_persona": persona_id
                            }
                            
                            all_results.append(result)
                
                except Exception as e:
                    self.logger.warning(f"Failed to search persona {persona_id} for cross-persona memories: {e}")
                    continue
            
            # Sort by similarity and limit results
            all_results.sort(key=lambda x: x['similarity'], reverse=True)
            return all_results[:n_results]
            
        except Exception as e:
            self.logger.error(f"Cross-persona memory search failed: {e}")
            return []

    async def get_shared_memory_stats(self) -> Dict[str, Any]:
        """Get statistics about shared memories across all personas"""
        try:
            stats = {
                "total_personas": len(self.collections),
                "shared_memories": 0,
                "public_memories": 0,
                "cross_references": 0,
                "by_persona": {}
            }
            
            for persona_id, collection in self.collections.items():
                try:
                    # Count shared memories
                    shared_result = await asyncio.to_thread(
                        collection.get,
                        where={"visibility": "shared"}
                    )
                    shared_count = len(shared_result['ids'])
                    
                    # Count public memories
                    public_result = await asyncio.to_thread(
                        collection.get,
                        where={"visibility": "public"}
                    )
                    public_count = len(public_result['ids'])
                    
                    # Count memories that reference other personas
                    cross_ref_result = await asyncio.to_thread(
                        collection.get,
                        where={"related_personas": {"$ne": ""}}  # ChromaDB stores empty as empty string
                    )
                    cross_ref_count = len(cross_ref_result['ids'])
                    
                    stats["shared_memories"] += shared_count
                    stats["public_memories"] += public_count
                    stats["cross_references"] += cross_ref_count
                    
                    stats["by_persona"][persona_id] = {
                        "shared": shared_count,
                        "public": public_count,
                        "cross_references": cross_ref_count
                    }
                    
                except Exception as e:
                    self.logger.warning(f"Failed to get shared memory stats for {persona_id}: {e}")
                    stats["by_persona"][persona_id] = {
                        "shared": 0,
                        "public": 0,
                        "cross_references": 0,
                        "error": str(e)
                    }
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Failed to get shared memory stats: {e}")
            return {"error": str(e)}

    async def close(self):
        """Clean up resources (optimized)"""
        try:
            # Clear collections cache
            self.collections.clear()
            
            # ChromaDB client cleanup is automatic
            self.logger.debug("VectorMemoryManager closed successfully")
        except Exception as e:
            self.logger.error(f"Error closing VectorMemoryManager: {e}")