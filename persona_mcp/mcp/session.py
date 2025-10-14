"""
Session state management for MCP handlers

Provides centralized session state that both regular and streaming handlers can share.
Eliminates hacky cross-references and provides proper state synchronization.
"""

import asyncio
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Set
from dataclasses import dataclass, field

from ..logging import get_logger


@dataclass 
class ConversationSession:
    """Active conversation session data"""
    id: str
    persona_id: str
    turn_count: int = 0
    last_activity: datetime = field(default_factory=datetime.utcnow)
    context: Dict[str, Any] = field(default_factory=dict)
    
    def update_activity(self):
        """Update last activity timestamp"""
        self.last_activity = datetime.utcnow()
    
    def increment_turn(self):
        """Increment turn count and update activity"""
        self.turn_count += 1
        self.update_activity()


@dataclass
class StreamingSession:
    """Active streaming session data"""
    id: str
    request_id: str
    persona_id: str
    message: str
    start_time: float
    cancelled: bool = False
    
    @property
    def duration(self) -> float:
        """Get session duration in seconds"""
        return time.time() - self.start_time


class MCPSessionManager:
    """
    Centralized session state manager for MCP protocol handlers
    
    Manages persona selection, conversation sessions, and streaming sessions
    in a way that both regular and streaming handlers can access safely.
    """
    
    def __init__(self):
        self.logger = get_logger(__name__)
        
        # Current persona selection (per WebSocket connection)
        self._current_personas: Dict[str, str] = {}  # websocket_id -> persona_id
        
        # Active conversation sessions
        self._conversations: Dict[str, ConversationSession] = {}  # persona_id -> session
        
        # Active streaming sessions  
        self._streaming_sessions: Dict[str, StreamingSession] = {}  # stream_id -> session
        
        # WebSocket connection tracking
        self._websocket_personas: Dict[str, Set[str]] = {}  # websocket_id -> {persona_ids}
        
        # Session cleanup task
        self._cleanup_task: Optional[asyncio.Task] = None
        self._cleanup_interval = 300  # 5 minutes
        
    async def start_cleanup_task(self):
        """Start background cleanup of stale sessions"""
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._periodic_cleanup())
            self.logger.info("Started session cleanup task")
    
    async def stop_cleanup_task(self):
        """Stop background cleanup task"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None
            self.logger.info("Stopped session cleanup task")
    
    def set_current_persona(self, websocket_id: str, persona_id: str) -> str:
        """
        Set current persona for a WebSocket connection
        
        Returns: conversation_id for the persona
        """
        self._current_personas[websocket_id] = persona_id
        
        # Track which personas this WebSocket has used
        if websocket_id not in self._websocket_personas:
            self._websocket_personas[websocket_id] = set()
        self._websocket_personas[websocket_id].add(persona_id)
        
        # Get or create conversation session
        conversation_id = self._get_or_create_conversation(persona_id)
        
        self.logger.info(f"Set current persona {persona_id} for WebSocket {websocket_id[:8]}...")
        return conversation_id
    
    def get_current_persona(self, websocket_id: str) -> Optional[str]:
        """Get current persona for a WebSocket connection"""
        return self._current_personas.get(websocket_id)
    
    def get_current_conversation_id(self, websocket_id: str) -> Optional[str]:
        """Get current conversation ID for a WebSocket connection"""
        persona_id = self.get_current_persona(websocket_id)
        if persona_id and persona_id in self._conversations:
            return self._conversations[persona_id].id
        return None
    
    def _get_or_create_conversation(self, persona_id: str) -> str:
        """Get existing conversation or create new one for persona"""
        if persona_id not in self._conversations:
            conversation_id = f"conv_{uuid.uuid4().hex[:12]}"
            self._conversations[persona_id] = ConversationSession(
                id=conversation_id,
                persona_id=persona_id
            )
            self.logger.debug(f"Created conversation {conversation_id} for persona {persona_id}")
        else:
            self._conversations[persona_id].update_activity()
        
        return self._conversations[persona_id].id
    
    def get_conversation_session(self, persona_id: str) -> Optional[ConversationSession]:
        """Get conversation session for persona"""
        return self._conversations.get(persona_id)
    
    def increment_conversation_turn(self, persona_id: str):
        """Increment turn count for persona conversation"""
        if persona_id in self._conversations:
            self._conversations[persona_id].increment_turn()
            self.logger.debug(f"Incremented turn count for persona {persona_id}")
    
    def get_conversation_context(self, persona_id: str) -> Dict[str, Any]:
        """Get conversation context for persona"""
        session = self._conversations.get(persona_id)
        if session:
            return {
                "id": session.id,
                "turn_count": session.turn_count,
                "last_activity": session.last_activity.isoformat(),
                **session.context
            }
        return {}
    
    def update_conversation_context(self, persona_id: str, context_updates: Dict[str, Any]):
        """Update conversation context for persona"""
        if persona_id in self._conversations:
            self._conversations[persona_id].context.update(context_updates)
            self._conversations[persona_id].update_activity()
    
    # Streaming session management
    def create_streaming_session(
        self, 
        request_id: str, 
        persona_id: str, 
        message: str
    ) -> str:
        """Create new streaming session"""
        stream_id = str(uuid.uuid4())
        session = StreamingSession(
            id=stream_id,
            request_id=request_id,
            persona_id=persona_id,
            message=message,
            start_time=time.time()
        )
        self._streaming_sessions[stream_id] = session
        
        self.logger.info(f"Created streaming session {stream_id[:8]}... for persona {persona_id}")
        return stream_id
    
    def get_streaming_session(self, stream_id: str) -> Optional[StreamingSession]:
        """Get streaming session by ID"""
        return self._streaming_sessions.get(stream_id)
    
    def cancel_streaming_session(self, stream_id: str) -> bool:
        """Cancel streaming session"""
        if stream_id in self._streaming_sessions:
            self._streaming_sessions[stream_id].cancelled = True
            self.logger.info(f"Cancelled streaming session {stream_id[:8]}...")
            return True
        return False
    
    def cleanup_streaming_session(self, stream_id: str):
        """Remove streaming session"""
        if stream_id in self._streaming_sessions:
            del self._streaming_sessions[stream_id]
            self.logger.debug(f"Cleaned up streaming session {stream_id[:8]}...")
    
    def get_active_streaming_sessions(self) -> Dict[str, Dict[str, Any]]:
        """Get summary of active streaming sessions"""
        return {
            stream_id: {
                "persona_id": session.persona_id,
                "message": session.message[:50] + "..." if len(session.message) > 50 else session.message,
                "duration": session.duration,
                "cancelled": session.cancelled
            }
            for stream_id, session in self._streaming_sessions.items()
        }
    
    # WebSocket connection management
    def cleanup_websocket_connection(self, websocket_id: str):
        """Clean up all session data for a WebSocket connection"""
        # Remove current persona
        if websocket_id in self._current_personas:
            del self._current_personas[websocket_id]
        
        # Clean up persona tracking
        if websocket_id in self._websocket_personas:
            del self._websocket_personas[websocket_id]
        
        self.logger.info(f"Cleaned up WebSocket connection {websocket_id[:8]}...")
    
    # Background cleanup
    async def _periodic_cleanup(self):
        """Periodically clean up stale sessions"""
        while True:
            try:
                await asyncio.sleep(self._cleanup_interval)
                await self._cleanup_stale_sessions()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in session cleanup: {e}")
    
    async def _cleanup_stale_sessions(self):
        """Clean up stale conversation and streaming sessions"""
        now = datetime.utcnow()
        stale_threshold = timedelta(hours=1)  # 1 hour timeout
        
        # Clean up stale conversations
        stale_conversations = []
        for persona_id, session in self._conversations.items():
            if now - session.last_activity > stale_threshold:
                stale_conversations.append(persona_id)
        
        for persona_id in stale_conversations:
            del self._conversations[persona_id]
            self.logger.debug(f"Cleaned up stale conversation for persona {persona_id}")
        
        # Clean up old streaming sessions
        stale_streams = []
        for stream_id, session in self._streaming_sessions.items():
            if session.duration > 3600:  # 1 hour timeout
                stale_streams.append(stream_id)
        
        for stream_id in stale_streams:
            del self._streaming_sessions[stream_id]
            self.logger.debug(f"Cleaned up stale streaming session {stream_id[:8]}...")
        
        if stale_conversations or stale_streams:
            self.logger.info(f"Cleaned up {len(stale_conversations)} conversations, {len(stale_streams)} streams")
    
    # Status and debugging
    def get_session_status(self) -> Dict[str, Any]:
        """Get comprehensive session status"""
        return {
            "active_websockets": len(self._current_personas),
            "active_conversations": len(self._conversations),
            "active_streams": len(self._streaming_sessions),
            "websocket_personas": {
                ws_id[:8] + "...": list(personas) 
                for ws_id, personas in self._websocket_personas.items()
            },
            "current_personas": {
                ws_id[:8] + "...": persona_id
                for ws_id, persona_id in self._current_personas.items()
            }
        }