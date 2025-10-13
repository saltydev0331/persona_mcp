"""
MCP JSON-RPC 2.0 protocol handlers for persona interactions
"""

import json
import logging
import time
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

from ..models import MCPRequest, MCPResponse, MCPError, Persona, ConversationContext, ConversationTurn, Memory, Priority
from ..conversation import ConversationEngine
from ..persistence import SQLiteManager, VectorMemoryManager
from ..llm import LLMManager
from ..memory import MemoryImportanceScorer, MemoryPruningSystem, PruningConfig, MemoryDecaySystem, DecayConfig


class MCPHandlers:
    """MCP protocol message handlers"""
    
    def __init__(
        self,
        conversation_engine: ConversationEngine,
        db_manager: SQLiteManager,
        memory_manager: VectorMemoryManager,
        llm_manager: LLMManager
    ):
        self.conversation = conversation_engine
        self.db = db_manager
        self.memory = memory_manager
        self.llm = llm_manager
        
        # Memory importance scoring
        self.importance_scorer = MemoryImportanceScorer()
        
        # Memory pruning system
        self.pruning_system = MemoryPruningSystem(memory_manager)
        
        # Memory decay system
        self.decay_system = MemoryDecaySystem(memory_manager, self.pruning_system)
        
        # Session management
        self.session_id: str = str(uuid.uuid4())
        self.session_created: datetime = datetime.utcnow()
        self.conversations: Dict[str, Dict] = {}  # persona_id -> conversation_data
        
        # Current session state
        self.current_persona_id: Optional[str] = None
        self.current_conversation_id: Optional[str] = None
        
        # Context management settings
        self.max_context_messages = 20  # Keep last 20 messages in active context
        self.context_summary_threshold = 50  # Summarize when > 50 messages
        self.session_timeout_hours = 24  # Sessions expire after 24 hours
        
        # Method registry
        self.handlers = {
            # Core persona operations
            "persona.switch": self.handle_persona_switch,
            "persona.chat": self.handle_persona_chat,
            "persona.list": self.handle_persona_list,
            "persona.create": self.handle_persona_create,
            "persona.status": self.handle_persona_status,
            "persona.memory": self.handle_persona_memory,
            "persona.relationship": self.handle_persona_relationship,
            
            # Conversation management
            "conversation.start": self.handle_conversation_start,
            "conversation.end": self.handle_conversation_end,
            "conversation.status": self.handle_conversation_status,
            
            # Memory operations
            "memory.search": self.handle_memory_search,
            "memory.store": self.handle_memory_store,
            "memory.stats": self.handle_memory_stats,
            "memory.prune": self.handle_memory_prune,
            "memory.prune_all": self.handle_memory_prune_all,
            "memory.prune_recommendations": self.handle_memory_prune_recommendations,
            "memory.prune_stats": self.handle_memory_prune_stats,
            "memory.decay_start": self.handle_memory_decay_start,
            "memory.decay_stop": self.handle_memory_decay_stop,
            "memory.decay_stats": self.handle_memory_decay_stats,
            "memory.decay_force": self.handle_memory_decay_force,
            
            # State management
            "state.save": self.handle_state_save,
            "state.load": self.handle_state_load,
            
            # Visual/UI updates
            "visual.update": self.handle_visual_update,
            
            # System operations
            "system.status": self.handle_system_status,
            "system.models": self.handle_system_models,
        }
    
    async def handle_request(self, request_data: Dict[str, Any]) -> MCPResponse:
        """Main request handler for MCP messages"""
        
        try:
            # Parse MCP request
            request = MCPRequest(**request_data)
            
            # Get handler for method
            handler = self.handlers.get(request.method)
            if not handler:
                return MCPResponse(
                    id=request.id,
                    error={
                        "code": -32601,
                        "message": f"Method not found: {request.method}"
                    }
                )
            
            # Execute handler
            result = await handler(request.params or {})
            
            return MCPResponse(
                id=request.id,
                result=result
            )
            
        except Exception as e:
            logging.error(f"Error handling MCP request: {e}")
            return MCPResponse(
                id=request_data.get("id"),
                error={
                    "code": -32603,
                    "message": f"Internal error: {str(e)}"
                }
            )
    
    # Session and Context Management
    def _get_or_create_conversation(self, persona_id: str) -> str:
        """Get or create conversation for persona in current session"""
        if persona_id not in self.conversations:
            conversation_id = f"{self.session_id}_{persona_id}"
            self.conversations[persona_id] = {
                "id": conversation_id,
                "persona_id": persona_id,
                "created": datetime.utcnow(),
                "messages": [],
                "turn_count": 0,
                "context_summary": None,
                "last_activity": datetime.utcnow()
            }
        else:
            # Update last activity
            self.conversations[persona_id]["last_activity"] = datetime.utcnow()
        
        return self.conversations[persona_id]["id"]
    
    async def _add_message_to_conversation(self, persona_id: str, role: str, content: str, metadata: Dict = None):
        """Add message to conversation history with context management"""
        if persona_id not in self.conversations:
            self._get_or_create_conversation(persona_id)
        
        conv = self.conversations[persona_id]
        message = {
            "role": role,  # "user" or "assistant"
            "content": content,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": metadata or {}
        }
        
        conv["messages"].append(message)
        conv["turn_count"] += 1
        
        # Context management: if too many messages, summarize older ones
        if len(conv["messages"]) > self.context_summary_threshold:
            await self._manage_conversation_context(persona_id)
    
    async def _manage_conversation_context(self, persona_id: str):
        """Manage conversation context to prevent bloat"""
        conv = self.conversations[persona_id]
        messages = conv["messages"]
        
        if len(messages) <= self.max_context_messages:
            return
        
        # Keep recent messages, summarize the rest
        recent_messages = messages[-self.max_context_messages:]
        older_messages = messages[:-self.max_context_messages]
        
        if older_messages and not conv["context_summary"]:
            # Create summary of older messages
            summary_content = "\n".join([
                f"{msg['role']}: {msg['content']}" for msg in older_messages[:10]
            ])
            
            try:
                persona = await self.db.load_persona(persona_id)
                summary_prompt = f"Summarize this conversation history concisely:\n{summary_content}"
                
                context = ConversationContext(
                    id="summary_context",
                    participants=[persona_id],
                    topic="conversation_summary",
                    context_type="casual",
                    turn_count=1,
                    urgency=Priority.NORMAL,
                    token_budget=200
                )
                
                summary = await self.llm.ollama.generate_response(
                    prompt=summary_prompt,
                    persona=persona,
                    context=context,
                    constraints={"max_tokens": 200}
                )
                
                conv["context_summary"] = summary
                
            except Exception as e:
                logging.warning(f"Failed to create conversation summary: {e}")
                conv["context_summary"] = f"Previous conversation with {len(older_messages)} exchanges."
        
        # Update conversation with managed context
        conv["messages"] = recent_messages
        logging.info(f"Managed context for persona {persona_id}: kept {len(recent_messages)} recent messages")
    
    def _get_conversation_context(self, persona_id: str) -> str:
        """Get formatted conversation context for LLM prompt"""
        if persona_id not in self.conversations:
            return ""
        
        conv = self.conversations[persona_id]
        context_parts = []
        
        # Add summary if available
        if conv["context_summary"]:
            context_parts.append(f"Previous conversation summary: {conv['context_summary']}")
        
        # Add recent messages
        recent_messages = conv["messages"][-self.max_context_messages:]
        if recent_messages:
            context_parts.append("Recent conversation:")
            for msg in recent_messages:
                role_label = "You" if msg["role"] == "assistant" else "User"
                context_parts.append(f"{role_label}: {msg['content']}")
        
        return "\n".join(context_parts)
    
    def _cleanup_expired_sessions(self):
        """Clean up old conversation data"""
        cutoff = datetime.utcnow() - timedelta(hours=self.session_timeout_hours)
        
        for persona_id in list(self.conversations.keys()):
            conv = self.conversations[persona_id]
            if conv["last_activity"] < cutoff:
                del self.conversations[persona_id]
                logging.info(f"Cleaned up expired conversation for persona {persona_id}")

    # Persona operations
    async def handle_persona_switch(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Switch to a different persona"""
        
        persona_id = params.get("persona_id")
        if not persona_id:
            raise ValueError("persona_id is required")
        
        # First try to load by ID, then by name if ID doesn't work
        persona = await self.db.load_persona(persona_id)
        if not persona:
            # Try to find by name
            personas = await self.db.list_personas()
            for p in personas:
                if p.name.lower() == persona_id.lower():
                    persona = p
                    persona_id = p.id
                    break
        
        if not persona:
            raise ValueError(f"Persona not found: {persona_id}")
        
        # Check if persona is available
        if not persona.interaction_state.is_available():
            raise ValueError(f"Persona {persona.name} is not available for interaction")
        
        # Switch to this persona
        self.current_persona_id = persona_id
        
        # Get or create conversation for this persona
        self.current_conversation_id = self._get_or_create_conversation(persona_id)
        
        # Cleanup expired sessions
        self._cleanup_expired_sessions()
        
        return {
            "persona_id": persona.id,
            "name": persona.name,
            "description": persona.description,
            "status": "active",
            "social_energy": persona.interaction_state.social_energy,
            "available_time": persona.interaction_state.available_time,
            "current_priority": persona.interaction_state.current_priority.value
        }
    
    async def handle_persona_chat(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Send a message to the current persona with conversation context"""
        
        message = params.get("message")
        token_budget = params.get("token_budget", 500)  # Default 500 tokens
        
        if not message:
            raise ValueError("message is required")
        
        if not self.current_persona_id:
            raise ValueError("No persona selected. Use persona.switch first")
        
        # Load current persona
        current_persona = await self.db.load_persona(self.current_persona_id)
        if not current_persona:
            raise ValueError("Current persona not found")
        
        # Get conversation context
        conversation_context = self._get_conversation_context(self.current_persona_id)
        
        # Build enhanced prompt with conversation history
        if conversation_context:
            enhanced_prompt = f"{conversation_context}\n\nUser: {message}"
        else:
            enhanced_prompt = f"User: {message}"
        
        # Create conversation context for this interaction
        conversation_data = self.conversations.get(self.current_persona_id, {})
        turn_count = conversation_data.get("turn_count", 0) + 1
        
        context = ConversationContext(
            id=self.current_conversation_id or "mcp_session",
            participants=[self.current_persona_id],
            topic="general",
            context_type="casual",
            turn_count=turn_count,
            urgency=Priority.IMPORTANT,
            token_budget=token_budget
        )
        
        start_time = time.time()
        
        # Generate response using LLM manager with conversation context
        try:
            response = await self.llm.ollama.generate_response(
                prompt=enhanced_prompt,
                persona=current_persona,
                context=context,
                constraints={"max_tokens": token_budget}
            )
            processing_time = time.time() - start_time
            
            # Add messages to conversation history
            await self._add_message_to_conversation(
                self.current_persona_id, 
                "user", 
                message,
                {"timestamp": datetime.utcnow().isoformat()}
            )
            
            await self._add_message_to_conversation(
                self.current_persona_id, 
                "assistant", 
                response,
                {
                    "processing_time": processing_time,
                    "tokens_used": int(len(response.split()) * 1.3),
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
            
            # Create a conversation turn record for persistent storage
            turn = ConversationTurn(
                conversation_id=self.current_conversation_id or "mcp_session",
                speaker_id=self.current_persona_id,
                turn_number=turn_count,
                content=response,
                response_type="direct",
                continue_score=50.0,
                tokens_used=int(len(response.split()) * 1.3),
                processing_time=processing_time
            )
            
            # Calculate intelligent importance for user conversation
            current_persona = await self.db.load_persona(self.current_persona_id)
            memory_content = f"User said: {message}. I responded: {response}"
            
            importance = self.importance_scorer.calculate_importance(
                content=memory_content,
                speaker=current_persona,
                listener=None,  # No specific listener for user conversations
                context={
                    'continue_score': 50.0,  # Default for direct user chat
                    'topic': 'user_conversation',
                    'response_type': 'direct'
                },
                turn=None,  # No specific turn object
                relationship=None  # No relationship with user (yet)
            )
            
            # Store memory of this interaction
            await self.memory.store_memory(Memory(
                persona_id=self.current_persona_id,
                content=memory_content,
                memory_type="conversation",
                importance=importance
            ))
            
        except Exception as e:
            raise ValueError(f"Failed to generate response: {str(e)}")
        
        return {
            "response": response,
            "response_type": "direct",
            "continue_score": 50.0,
            "tokens_used": int(len(response.split()) * 1.3),
            "processing_time": processing_time,
            "persona_state": {
                "social_energy": current_persona.interaction_state.social_energy,
                "available_time": current_persona.interaction_state.available_time,
                "interaction_fatigue": current_persona.interaction_state.interaction_fatigue
            }
        }
    
    async def handle_persona_list(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """List all available personas"""
        
        personas = await self.db.list_personas()
        
        persona_list = []
        for persona in personas:
            persona_list.append({
                "id": persona.id,
                "name": persona.name,
                "description": persona.description,
                "available": persona.interaction_state.is_available(),
                "social_energy": persona.interaction_state.social_energy,
                "current_priority": persona.interaction_state.current_priority.value,
                "cooldown_remaining": max(0, persona.interaction_state.cooldown_until - datetime.now().timestamp())
            })
        
        return {
            "personas": persona_list,
            "total_count": len(persona_list),
            "available_count": sum(1 for p in persona_list if p["available"])
        }
    
    async def handle_persona_create(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new persona"""
        
        name = params.get("name")
        description = params.get("description", "")
        
        if not name:
            raise ValueError("name is required")
        
        # Create new persona
        persona = Persona(
            name=name,
            description=description,
            personality_traits=params.get("personality_traits", {}),
            topic_preferences=params.get("topic_preferences", {}),
            charisma=params.get("charisma", 10),
            intelligence=params.get("intelligence", 10),
            social_rank=params.get("social_rank", "commoner")
        )
        
        # Save to database
        success = await self.db.save_persona(persona)
        if not success:
            raise ValueError("Failed to save persona")
        
        # Initialize vector memory
        await self.memory.initialize_persona_memory(persona.id)
        
        return {
            "persona_id": persona.id,
            "name": persona.name,
            "created": True
        }
    
    async def handle_persona_status(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get detailed status of a persona"""
        
        persona_id = params.get("persona_id", self.current_persona_id)
        if not persona_id:
            raise ValueError("persona_id is required")
        
        persona = await self.db.load_persona(persona_id)
        if not persona:
            raise ValueError(f"Persona not found: {persona_id}")
        
        # Get memory stats
        memory_stats = await self.memory.get_memory_stats(persona_id)
        
        return {
            "persona": {
                "id": persona.id,
                "name": persona.name,
                "description": persona.description,
                "personality_traits": persona.personality_traits,
                "topic_preferences": persona.topic_preferences,
                "charisma": persona.charisma,
                "intelligence": persona.intelligence,
                "social_rank": persona.social_rank
            },
            "interaction_state": {
                "interest_level": persona.interaction_state.interest_level,
                "interaction_fatigue": persona.interaction_state.interaction_fatigue,
                "current_priority": persona.interaction_state.current_priority.value,
                "available_time": persona.interaction_state.available_time,
                "social_energy": persona.interaction_state.social_energy,
                "cooldown_until": persona.interaction_state.cooldown_until,
                "is_available": persona.interaction_state.is_available()
            },
            "memory_stats": memory_stats
        }
    
    # Conversation operations
    async def handle_conversation_start(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Start a conversation between two personas"""
        
        persona1_id = params.get("persona1_id")
        persona2_id = params.get("persona2_id")
        topic = params.get("topic", "general")
        
        if not persona1_id or not persona2_id:
            raise ValueError("Both persona1_id and persona2_id are required")
        
        # Load personas
        persona1 = await self.db.load_persona(persona1_id)
        persona2 = await self.db.load_persona(persona2_id)
        
        if not persona1 or not persona2:
            raise ValueError("One or both personas not found")
        
        # Start conversation
        context = await self.conversation.initiate_conversation(
            persona1, persona2, topic, token_budget=params.get("token_budget", 1000)
        )
        
        if not context:
            raise ValueError("Failed to start conversation")
        
        return {
            "conversation_id": context.id,
            "participants": context.participants,
            "topic": context.topic,
            "started": True
        }
    
    async def handle_conversation_end(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """End a conversation"""
        
        conversation_id = params.get("conversation_id", self.current_conversation_id)
        reason = params.get("reason", "user_request")
        
        if not conversation_id:
            raise ValueError("conversation_id is required")
        
        context = self.conversation.active_conversations.get(conversation_id)
        if not context:
            raise ValueError(f"Conversation not found: {conversation_id}")
        
        await self.conversation._end_conversation(context, reason)
        
        if conversation_id == self.current_conversation_id:
            self.current_conversation_id = None
        
        return {
            "conversation_id": conversation_id,
            "ended": True,
            "reason": reason,
            "final_stats": {
                "duration": context.duration,
                "turns": context.turn_count,
                "tokens_used": context.tokens_used
            }
        }
    
    async def handle_conversation_status(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get conversation status"""
        
        conversation_id = params.get("conversation_id", self.current_conversation_id)
        if not conversation_id:
            raise ValueError("conversation_id is required")
        
        status = await self.conversation.get_conversation_status(conversation_id)
        if not status:
            raise ValueError(f"Conversation not found: {conversation_id}")
        
        return status
    
    # Memory operations
    async def handle_memory_search(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Search persona memory"""
        
        persona_id = params.get("persona_id", self.current_persona_id)
        query = params.get("query")
        
        if not persona_id:
            raise ValueError("persona_id is required")
        if not query:
            raise ValueError("query is required")
        
        memories = await self.memory.search_memories(
            persona_id,
            query,
            n_results=params.get("n_results", 5),
            memory_type=params.get("memory_type"),
            min_importance=params.get("min_importance", 0.0)
        )
        
        return {
            "memories": [
                {
                    "id": m.id,
                    "content": m.content,
                    "memory_type": m.memory_type,
                    "importance": m.importance,
                    "emotional_valence": m.emotional_valence,
                    "related_personas": m.related_personas,
                    "created_at": m.created_at.isoformat(),
                    "accessed_count": m.accessed_count
                }
                for m in memories
            ],
            "query": query,
            "result_count": len(memories)
        }
    
    async def handle_memory_store(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Store a new memory"""
        
        persona_id = params.get("persona_id", self.current_persona_id)
        content = params.get("content")
        
        if not persona_id:
            raise ValueError("persona_id is required")
        if not content:
            raise ValueError("content is required")
        
        from ..models import Memory
        
        memory = Memory(
            persona_id=persona_id,
            content=content,
            memory_type=params.get("memory_type", "user_input"),
            importance=params.get("importance", 0.5),
            emotional_valence=params.get("emotional_valence", 0.0),
            related_personas=params.get("related_personas", []),
            metadata=params.get("metadata", {})
        )
        
        success = await self.memory.store_memory(memory)
        
        return {
            "memory_id": memory.id,
            "stored": success
        }
    
    async def handle_memory_stats(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get memory statistics"""
        
        persona_id = params.get("persona_id", self.current_persona_id)
        if not persona_id:
            raise ValueError("persona_id is required")
        
        stats = await self.memory.get_memory_stats(persona_id)
        
        return stats
    
    # State management
    async def handle_state_save(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Save current session state"""
        
        state = {
            "current_persona_id": self.current_persona_id,
            "current_conversation_id": self.current_conversation_id,
            "active_conversations": len(self.conversation.active_conversations),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return {
            "state_saved": True,
            "state": state
        }
    
    async def handle_state_load(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Load previous session state"""
        
        # For now, just return current state
        # In a full implementation, this would restore from persistent storage
        return {
            "state_loaded": True,
            "current_persona_id": self.current_persona_id,
            "current_conversation_id": self.current_conversation_id
        }
    
    # Visual/UI operations
    async def handle_visual_update(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Update visual context or UI state"""
        
        update_type = params.get("type", "general")
        data = params.get("data", {})
        
        # This is a placeholder for visual updates
        # In a real implementation, this might update 3D environments,
        # character models, UI elements, etc.
        
        return {
            "visual_updated": True,
            "update_type": update_type,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    # System operations
    async def handle_system_status(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get overall system status"""
        
        # Check LLM availability
        llm_available = await self.llm.ollama.is_available()
        
        # Get persona counts
        personas = await self.db.list_personas()
        available_personas = [p for p in personas if p.interaction_state.is_available()]
        
        return {
            "system_status": "operational",
            "llm_available": llm_available,
            "total_personas": len(personas),
            "available_personas": len(available_personas),
            "active_conversations": len(self.conversation.active_conversations),
            "current_persona": self.current_persona_id,
            "current_conversation": self.current_conversation_id,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def handle_system_models(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get available LLM models"""
        
        models = await self.llm.ollama.list_available_models()
        
        return {
            "available_models": models,
            "current_model": self.llm.ollama.default_model,
            "provider": "ollama"
        }
    
    # Missing persona methods
    async def handle_persona_memory(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Search persona memory"""
        query = params.get("query", "")
        limit = params.get("limit", 5)
        
        if not self.current_persona_id:
            raise ValueError("No persona selected. Use persona.switch first")
        
        memories = await self.memory.search_memories(
            persona_id=self.current_persona_id,
            query=query,
            n_results=limit
        )
        
        return {
            "memories": [
                {
                    "content": memory.content,
                    "importance": memory.importance,
                    "memory_type": memory.memory_type,
                    "created_at": memory.created_at.isoformat()
                }
                for memory in memories
            ],
            "query": query,
            "total_found": len(memories)
        }
    
    async def handle_persona_relationship(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get relationship status with another persona"""
        target_persona = params.get("target_persona")
        
        if not self.current_persona_id:
            raise ValueError("No persona selected. Use persona.switch first")
        
        if target_persona:
            # Get relationship with specific persona
            relationship = await self.db.get_persona_relationship(
                self.current_persona_id, 
                target_persona
            )
            return {
                "current_persona": self.current_persona_id,
                "target_persona": target_persona,
                "relationship": relationship.model_dump() if relationship else None
            }
        else:
            # Get all relationships for current persona
            relationships = await self.db.get_persona_relationships(self.current_persona_id)
            return {
                "current_persona": self.current_persona_id,
                "relationships": [r.model_dump() for r in relationships]
            }

    async def handle_memory_prune(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Prune memories for current or specified persona"""
        persona_id = params.get("persona_id", self.current_persona_id)
        force = params.get("force", False)
        
        if not persona_id:
            raise ValueError("No persona specified and no current persona selected")
        
        # Check if pruning is needed
        needs_pruning = await self.pruning_system.should_prune_persona(persona_id)
        if not needs_pruning and not force:
            stats = await self.memory.get_memory_stats(persona_id)
            return {
                "status": "no_pruning_needed",
                "persona_id": persona_id,
                "current_memory_count": stats.get("total_memories", 0),
                "message": "Memory collection is within acceptable limits"
            }
        
        # Execute pruning
        metrics = await self.pruning_system.prune_persona_memories(persona_id, force=force)
        
        return {
            "status": "pruning_completed",
            "persona_id": persona_id,
            "memories_before": metrics.total_memories_before,
            "memories_after": metrics.total_memories_after,
            "memories_pruned": metrics.memories_pruned,
            "processing_time": metrics.processing_time_seconds,
            "average_importance_pruned": metrics.average_importance_pruned,
            "average_importance_kept": metrics.average_importance_kept
        }

    async def handle_memory_prune_all(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Prune memories for all personas that need it"""
        
        metrics = await self.pruning_system.prune_all_personas()
        
        return {
            "status": "global_pruning_completed",
            "personas_processed": metrics.personas_processed,
            "total_memories_before": metrics.total_memories_before,
            "total_memories_after": metrics.total_memories_after,
            "total_memories_pruned": metrics.memories_pruned,
            "processing_time": metrics.processing_time_seconds,
            "errors_encountered": metrics.errors_encountered
        }

    async def handle_memory_prune_recommendations(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get pruning recommendations without executing"""
        persona_id = params.get("persona_id", self.current_persona_id)
        
        if not persona_id:
            raise ValueError("No persona specified and no current persona selected")
        
        recommendations = await self.pruning_system.get_pruning_recommendations(persona_id)
        
        return {
            "persona_id": persona_id,
            "recommendations": recommendations
        }

    async def handle_memory_prune_stats(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get pruning system statistics"""
        
        stats = self.pruning_system.get_pruning_stats()
        
        return {
            "pruning_statistics": stats
        }

    async def handle_memory_decay_start(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Start background memory decay processing"""
        
        await self.decay_system.start_background_decay()
        
        return {
            "status": "background_decay_started",
            "interval_hours": self.decay_system.config.decay_interval_hours,
            "mode": self.decay_system.config.mode,
            "auto_pruning": self.decay_system.config.enable_auto_pruning
        }

    async def handle_memory_decay_stop(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Stop background memory decay processing"""
        
        await self.decay_system.stop_background_decay()
        
        return {
            "status": "background_decay_stopped"
        }

    async def handle_memory_decay_stats(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get memory decay system statistics"""
        
        stats = self.decay_system.get_decay_stats()
        
        return {
            "decay_statistics": stats
        }

    async def handle_memory_decay_force(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Force decay cycle or specific persona decay"""
        
        persona_id = params.get("persona_id", self.current_persona_id)
        decay_factor = params.get("decay_factor", 0.1)
        
        if persona_id:
            # Force decay on specific persona
            metrics = await self.decay_system.force_decay_persona(persona_id, decay_factor)
            return {
                "status": "persona_decay_completed",
                "persona_id": persona_id,
                "decay_factor": decay_factor,
                "memories_processed": metrics.memories_processed,
                "memories_decayed": metrics.memories_decayed
            }
        else:
            # Force global decay cycle
            metrics = await self.decay_system.run_decay_cycle()
            return {
                "status": "global_decay_cycle_completed",
                "personas_processed": metrics.personas_processed,
                "memories_decayed": metrics.memories_decayed,
                "auto_prunes_triggered": metrics.auto_prunes_triggered,
                "processing_time": metrics.processing_time_seconds
            }