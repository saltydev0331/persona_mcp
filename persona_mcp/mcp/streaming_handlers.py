"""
Streaming handlers for real-time LLM response delivery via WebSocket

Implements streaming versions of MCP methods with progressive response chunks.
"""

import asyncio
import logging
import time
import uuid
from typing import Dict, Any, Optional, AsyncGenerator, Callable
from datetime import datetime

from ..models import Persona, ConversationContext, Priority
from ..conversation import ConversationEngine
from ..persistence import SQLiteManager, VectorMemoryManager
from ..llm import LLMManager
from ..utils import fast_json as json


class StreamingEventTypes:
    """Event types for streaming responses"""
    START = "stream_start"
    CHUNK = "stream_chunk" 
    COMPLETE = "stream_complete"
    ERROR = "stream_error"
    CANCELLED = "stream_cancelled"


class StreamingMCPHandlers:
    """Streaming handlers for MCP protocol with progressive response delivery"""
    
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
        
        # Active streaming sessions
        self.active_streams: Dict[str, Dict[str, Any]] = {}
        
        # Streaming method registry
        self.streaming_handlers = {
            "persona.chat_stream": self.handle_persona_chat_stream,
        }
    
    def create_streaming_response(
        self, 
        request_id: str, 
        event_type: str, 
        data: Any = None,
        stream_id: Optional[str] = None,
        error: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Create a streaming JSON-RPC 2.0 response"""
        
        response = {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "event_type": event_type,
                "stream_id": stream_id or str(uuid.uuid4()),
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
        }
        
        if data is not None:
            response["result"]["data"] = data
            
        if error is not None:
            response["error"] = error
            
        return response
    
    async def handle_streaming_request(
        self, 
        request_data: Dict[str, Any],
        websocket_sender: Callable[[str], None]
    ) -> bool:
        """Handle streaming MCP requests"""
        
        method = request_data.get("method")
        request_id = request_data.get("id", str(uuid.uuid4()))
        
        if method not in self.streaming_handlers:
            return False  # Not a streaming method
        
        try:
            # Get handler
            handler = self.streaming_handlers[method]
            
            # Execute streaming handler
            await handler(
                request_data.get("params", {}),
                request_id,
                websocket_sender
            )
            
            return True
            
        except Exception as e:
            # Send error event
            error_response = self.create_streaming_response(
                request_id,
                StreamingEventTypes.ERROR,
                error={
                    "code": -32603,
                    "message": "Streaming error",
                    "data": str(e)
                }
            )
            await websocket_sender(json.dumps(error_response))
            return True
    
    async def handle_persona_chat_stream(
        self,
        params: Dict[str, Any],
        request_id: str,
        websocket_sender: Callable[[str], None]
    ):
        """Stream persona chat response progressively"""
        
        message = params.get("message")
        token_budget = params.get("token_budget", 500)
        
        if not message:
            raise ValueError("message is required")
        
        # Get current persona from regular handlers (shared state)
        current_persona_id = None
        if hasattr(self, '_regular_handlers') and hasattr(self._regular_handlers, 'current_persona_id'):
            current_persona_id = self._regular_handlers.current_persona_id
            
        if not current_persona_id:
            raise ValueError("No persona selected. Use persona.switch first")
        
        # Load persona
        current_persona = await self.db.load_persona(current_persona_id)
        if not current_persona:
            raise ValueError("Current persona not found")
        
        # Generate stream ID
        stream_id = str(uuid.uuid4())
        
        # Track streaming session
        self.active_streams[stream_id] = {
            "request_id": request_id,
            "persona_id": current_persona_id,
            "message": message,
            "start_time": time.time(),
            "cancelled": False
        }
        
        try:
            # Send stream start event
            start_response = self.create_streaming_response(
                request_id,
                StreamingEventTypes.START,
                data={
                    "persona_name": current_persona.name,
                    "message": message,
                    "token_budget": token_budget
                },
                stream_id=stream_id
            )
            await websocket_sender(json.dumps(start_response))
            
            # Get conversation context using regular handlers pattern
            conversation_data = {}
            current_conversation_id = "stream_session"
            
            if hasattr(self, '_regular_handlers'):
                conversation_data = self._regular_handlers.conversations.get(current_persona_id, {})
                current_conversation_id = self._regular_handlers.current_conversation_id or "stream_session"
            
            turn_count = conversation_data.get("turn_count", 0) + 1
            
            context = ConversationContext(
                id=current_conversation_id,
                participants=[current_persona_id],
                topic="general",
                context_type="casual",
                turn_count=turn_count,
                urgency=Priority.IMPORTANT,
                token_budget=token_budget
            )
            
            # Build enhanced prompt
            enhanced_prompt = f"User: {message}"
            
            # Stream response chunks
            full_response = ""
            chunk_count = 0
            
            async for chunk in self.llm.generate_response_stream(
                enhanced_prompt,
                current_persona,
                context,
                constraints={"max_tokens": token_budget}
            ):
                # Check if stream was cancelled
                if self.active_streams.get(stream_id, {}).get("cancelled"):
                    break
                
                chunk_count += 1
                full_response += chunk
                
                # Send chunk event
                chunk_response = self.create_streaming_response(
                    request_id,
                    StreamingEventTypes.CHUNK,
                    data={
                        "chunk": chunk,
                        "chunk_number": chunk_count,
                        "total_length": len(full_response)
                    },
                    stream_id=stream_id
                )
                await websocket_sender(json.dumps(chunk_response))
                
                # Small delay to prevent overwhelming the client
                await asyncio.sleep(0.01)
            
            # Send completion event if not cancelled
            if not self.active_streams.get(stream_id, {}).get("cancelled"):
                processing_time = time.time() - self.active_streams[stream_id]["start_time"]
                
                complete_response = self.create_streaming_response(
                    request_id,
                    StreamingEventTypes.COMPLETE,
                    data={
                        "full_response": full_response,
                        "chunk_count": chunk_count,
                        "processing_time": round(processing_time, 3),
                        "response_length": len(full_response),
                        "persona_name": current_persona.name
                    },
                    stream_id=stream_id
                )
                await websocket_sender(json.dumps(complete_response))
                
                # Store conversation turn in memory (async)
                asyncio.create_task(self._store_streaming_conversation(
                    current_persona, message, full_response, context
                ))
            else:
                # Send cancelled event
                cancelled_response = self.create_streaming_response(
                    request_id,
                    StreamingEventTypes.CANCELLED,
                    data={"reason": "Client cancelled"},
                    stream_id=stream_id
                )
                await websocket_sender(json.dumps(cancelled_response))
        
        except Exception as e:
            logging.error(f"Streaming chat error: {e}")
            import traceback
            traceback.print_exc()
            
            # Send error event
            error_response = self.create_streaming_response(
                request_id,
                StreamingEventTypes.ERROR,
                error={
                    "code": -32603,
                    "message": "Chat streaming failed", 
                    "data": f"{type(e).__name__}: {str(e)}"
                },
                stream_id=stream_id
            )
            await websocket_sender(json.dumps(error_response))
        
        finally:
            # Clean up streaming session
            if stream_id in self.active_streams:
                del self.active_streams[stream_id]
    
    async def _store_streaming_conversation(
        self,
        persona: Persona,
        user_message: str,
        response: str,
        context: ConversationContext
    ):
        """Store streaming conversation in memory (background task)"""
        
        try:
            # Store conversation turn
            turn = await self.conversation.create_conversation_turn(
                persona_id=persona.id,
                user_message=user_message,
                persona_response=response,
                context=context
            )
            
            # Store memory if significant
            if len(response) > 50:  # Only store substantial responses
                await self.memory.store_memory(
                    persona_id=persona.id,
                    content=f"Conversation with user: '{user_message}' -> '{response[:100]}...'",
                    memory_type="conversation",
                    importance=0.6,  # Medium importance for streaming chats
                    metadata={
                        "turn_id": turn.id,
                        "streaming": True,
                        "response_length": len(response)
                    }
                )
            
            logging.debug(f"Stored streaming conversation for {persona.name}")
            
        except Exception as e:
            logging.error(f"Error storing streaming conversation: {e}")
    
    def cancel_stream(self, stream_id: str):
        """Cancel an active streaming session"""
        
        if stream_id in self.active_streams:
            self.active_streams[stream_id]["cancelled"] = True
            logging.info(f"Cancelled streaming session: {stream_id}")
            return True
        
        return False
    
    def get_active_streams(self) -> Dict[str, Dict[str, Any]]:
        """Get information about active streaming sessions"""
        
        return {
            stream_id: {
                "persona_id": session["persona_id"],
                "message": session["message"][:50] + "..." if len(session["message"]) > 50 else session["message"],
                "duration": time.time() - session["start_time"],
                "cancelled": session["cancelled"]
            }
            for stream_id, session in self.active_streams.items()
        }