"""
ChromaDB vector memory management for long-term persona memory
"""

import chromadb
from chromadb.config import Settings
from typing import List, Dict, Any, Optional
import uuid
from pathlib import Path
import asyncio
from concurrent.futures import ThreadPoolExecutor

from ..models import Memory


class VectorMemoryManager:
    """Manages vector-based memory storage using ChromaDB"""

    def __init__(self, persist_directory: str = "data/vector_memory"):
        self.persist_directory = Path(persist_directory)
        self.persist_directory.mkdir(parents=True, exist_ok=True)
        
        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(
            path=str(self.persist_directory),
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # Thread pool for async operations
        self.executor = ThreadPoolExecutor(max_workers=4)
        
        # Memory collections by persona
        self.collections = {}

    def _get_collection_name(self, persona_id: str) -> str:
        """Generate collection name for persona"""
        return f"persona_{persona_id.replace('-', '_')}"

    async def initialize_persona_memory(self, persona_id: str) -> bool:
        """Initialize memory collection for a persona"""
        try:
            collection_name = self._get_collection_name(persona_id)
            
            # Run in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            collection = await loop.run_in_executor(
                self.executor,
                self._create_collection,
                collection_name
            )
            
            self.collections[persona_id] = collection
            return True
            
        except Exception as e:
            print(f"Error initializing memory for persona {persona_id}: {e}")
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
        """Store a memory with vector embedding"""
        try:
            # Ensure collection exists
            if memory.persona_id not in self.collections:
                await self.initialize_persona_memory(memory.persona_id)

            collection = self.collections[memory.persona_id]
            
            # Prepare metadata
            metadata = {
                "memory_type": memory.memory_type,
                "importance": memory.importance,
                "emotional_valence": memory.emotional_valence,
                "related_personas": ",".join(memory.related_personas),
                "created_at": memory.created_at.isoformat(),
                "accessed_count": memory.accessed_count,
                **memory.metadata
            }

            # Store in ChromaDB (embeddings auto-generated)
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                self.executor,
                lambda: collection.add(
                    documents=[memory.content],
                    metadatas=[metadata],
                    ids=[memory.id]
                )
            )
            
            return True
            
        except Exception as e:
            print(f"Error storing memory {memory.id}: {e}")
            return False

    async def search_memories(
        self, 
        persona_id: str, 
        query: str, 
        n_results: int = 5,
        memory_type: Optional[str] = None,
        min_importance: float = 0.0
    ) -> List[Memory]:
        """Search for relevant memories"""
        try:
            if persona_id not in self.collections:
                await self.initialize_persona_memory(persona_id)
                return []

            collection = self.collections[persona_id]
            
            # Build where clause for filtering
            where_clause = {"importance": {"$gte": min_importance}}
            if memory_type:
                where_clause["memory_type"] = memory_type

            # Perform vector search
            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(
                self.executor,
                lambda: collection.query(
                    query_texts=[query],
                    n_results=n_results,
                    where=where_clause if where_clause else None
                )
            )

            # Convert results to Memory objects
            memories = []
            if results and results["documents"]:
                for i, doc in enumerate(results["documents"][0]):
                    metadata = results["metadatas"][0][i]
                    memory_id = results["ids"][0][i]
                    
                    memory = Memory(
                        id=memory_id,
                        persona_id=persona_id,
                        content=doc,
                        memory_type=metadata.get("memory_type", "conversation"),
                        importance=metadata.get("importance", 0.5),
                        emotional_valence=metadata.get("emotional_valence", 0.0),
                        related_personas=metadata.get("related_personas", "").split(",") if metadata.get("related_personas") else [],
                        metadata={k: v for k, v in metadata.items() if k not in ["memory_type", "importance", "emotional_valence", "related_personas", "created_at", "accessed_count"]},
                        accessed_count=metadata.get("accessed_count", 0)
                    )
                    memories.append(memory)

            return memories
            
        except Exception as e:
            print(f"Error searching memories for persona {persona_id}: {e}")
            return []

    async def update_memory_access(self, persona_id: str, memory_id: str) -> bool:
        """Update memory access tracking"""
        try:
            if persona_id not in self.collections:
                return False

            collection = self.collections[persona_id]
            
            # Get current memory
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self.executor,
                lambda: collection.get(ids=[memory_id])
            )
            
            if not result["metadatas"]:
                return False

            # Update access count
            metadata = result["metadatas"][0]
            metadata["accessed_count"] = metadata.get("accessed_count", 0) + 1
            metadata["last_accessed"] = str(uuid.uuid4())  # Placeholder for timestamp

            # Update in collection
            await loop.run_in_executor(
                self.executor,
                lambda: collection.update(
                    ids=[memory_id],
                    metadatas=[metadata]
                )
            )
            
            return True
            
        except Exception as e:
            print(f"Error updating memory access for {memory_id}: {e}")
            return False

    async def get_memory_stats(self, persona_id: str) -> Dict[str, Any]:
        """Get memory statistics for a persona"""
        try:
            if persona_id not in self.collections:
                return {"total_memories": 0}

            collection = self.collections[persona_id]
            
            loop = asyncio.get_event_loop()
            count = await loop.run_in_executor(
                self.executor,
                lambda: collection.count()
            )
            
            # Get all memories to calculate stats
            all_memories = await loop.run_in_executor(
                self.executor,
                lambda: collection.get()
            )
            
            if not all_memories["metadatas"]:
                return {"total_memories": 0}

            # Calculate statistics
            importance_scores = [float(m.get("importance", 0.5)) for m in all_memories["metadatas"]]
            memory_types = [m.get("memory_type", "conversation") for m in all_memories["metadatas"]]
            
            return {
                "total_memories": count,
                "avg_importance": sum(importance_scores) / len(importance_scores) if importance_scores else 0,
                "memory_types": {t: memory_types.count(t) for t in set(memory_types)},
                "high_importance_count": sum(1 for score in importance_scores if score >= 0.7)
            }
            
        except Exception as e:
            print(f"Error getting memory stats for persona {persona_id}: {e}")
            return {"total_memories": 0, "error": str(e)}

    async def cleanup_old_memories(self, persona_id: str, max_memories: int = 1000) -> int:
        """Remove least important/accessed memories to stay under limit"""
        try:
            if persona_id not in self.collections:
                return 0

            collection = self.collections[persona_id]
            
            loop = asyncio.get_event_loop()
            count = await loop.run_in_executor(
                self.executor,
                lambda: collection.count()
            )
            
            if count <= max_memories:
                return 0

            # Get all memories with metadata
            all_memories = await loop.run_in_executor(
                self.executor,
                lambda: collection.get()
            )
            
            # Calculate removal priority (lower is removed first)
            memory_priorities = []
            for i, metadata in enumerate(all_memories["metadatas"]):
                importance = float(metadata.get("importance", 0.5))
                access_count = int(metadata.get("accessed_count", 0))
                
                # Priority = importance + access_frequency_bonus
                priority = importance + (access_count * 0.1)
                memory_priorities.append((priority, all_memories["ids"][i]))

            # Sort by priority and remove lowest ones
            memory_priorities.sort()
            to_remove = memory_priorities[:count - max_memories]
            remove_ids = [memory_id for _, memory_id in to_remove]
            
            if remove_ids:
                await loop.run_in_executor(
                    self.executor,
                    lambda: collection.delete(ids=remove_ids)
                )
            
            return len(remove_ids)
            
        except Exception as e:
            print(f"Error cleaning up memories for persona {persona_id}: {e}")
            return 0

    async def close(self):
        """Clean up resources"""
        self.executor.shutdown(wait=True)