"""
Shared data models for Persona-MCP system.

These models are used by both MCP server and PersonaAPI server to ensure
operational parity and consistent data structures.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from enum import Enum
from pydantic import BaseModel, Field
import uuid
import time


class Priority(str, Enum):
    """Persona priority levels"""
    URGENT = "urgent"
    IMPORTANT = "important"
    CASUAL = "casual" 
    SOCIAL = "social"
    ACADEMIC = "academic"
    BUSINESS = "business"
    NONE = "none"


class PersonaBase(BaseModel):
    """Base persona information"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str
    personality_traits: Dict[str, Any] = Field(default_factory=dict)
    topic_preferences: Dict[str, int] = Field(default_factory=dict)  # topic -> interest score (0-100)
    charisma: int = Field(default=10, ge=1, le=20)  # D&D style charisma score
    intelligence: int = Field(default=10, ge=1, le=20)
    social_rank: str = Field(default="commoner")  # social status for interaction dynamics
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class PersonaInteractionState(BaseModel):
    """Dynamic interaction state for a persona"""
    persona_id: str
    interest_level: int = Field(default=50, ge=0, le=100)
    interaction_fatigue: int = Field(default=0, ge=0)
    current_priority: Priority = Priority.NONE
    available_time: int = Field(default=300)  # seconds willing to spend
    social_energy: int = Field(default=100, ge=0, le=200)
    cooldown_until: float = Field(default=0)  # timestamp when can re-engage
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def is_available(self) -> bool:
        """Check if persona is available for interaction"""
        return (time.time() >= self.cooldown_until and 
                self.available_time > 30 and
                self.social_energy > 10)

    def apply_fatigue(self, duration: int):
        """Apply fatigue based on conversation duration"""
        self.interaction_fatigue += duration // 30  # 1 point per 30 seconds
        self.social_energy = max(0, self.social_energy - (duration // 60))  # 1 point per minute
        self.available_time = max(0, self.available_time - duration)

    def regenerate_energy(self, seconds_elapsed: int):
        """Regenerate social energy over time"""
        energy_gain = seconds_elapsed // 60  # 1 point per minute
        self.social_energy = min(200, self.social_energy + energy_gain)
        
        # Reduce fatigue over time
        fatigue_reduction = seconds_elapsed // 300  # 1 point per 5 minutes
        self.interaction_fatigue = max(0, self.interaction_fatigue - fatigue_reduction)


class Persona(PersonaBase):
    """Complete persona model with interaction state"""
    interaction_state: PersonaInteractionState = None

    def __init__(self, **data):
        super().__init__(**data)
        if self.interaction_state is None:
            self.interaction_state = PersonaInteractionState(persona_id=self.id)


class Memory(BaseModel):
    """Individual memory record"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    persona_id: str
    content: str
    memory_type: str = "conversation"  # conversation, relationship, event, etc.
    importance: float = Field(default=0.5, ge=0.0, le=1.0)
    emotional_valence: float = Field(default=0.0, ge=-1.0, le=1.0)  # negative to positive
    related_personas: List[str] = Field(default_factory=list)
    visibility: str = Field(default="private")  # private, shared, public
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    accessed_count: int = Field(default=0)
    last_accessed: Optional[datetime] = None

    def access(self):
        """Record memory access for relevance tracking"""
        self.accessed_count += 1
        self.last_accessed = datetime.now(timezone.utc)


class RelationshipType(str, Enum):
    """Types of relationships between personas"""
    STRANGER = "stranger"
    ACQUAINTANCE = "acquaintance"
    FRIEND = "friend"
    CLOSE_FRIEND = "close_friend"
    RIVAL = "rival"
    ENEMY = "enemy"
    MENTOR = "mentor"
    STUDENT = "student"
    ROMANTIC = "romantic"
    FAMILY = "family"


class EmotionalState(BaseModel):
    """Emotional state tracking for personas"""
    persona_id: str
    mood: float = Field(default=0.0, ge=-1.0, le=1.0)  # -1 very sad, 0 neutral, 1 very happy
    energy_level: float = Field(default=0.5, ge=0.0, le=1.0)  # 0 exhausted, 1 energetic
    stress_level: float = Field(default=0.0, ge=0.0, le=1.0)  # 0 calm, 1 very stressed
    curiosity: float = Field(default=0.5, ge=0.0, le=1.0)  # openness to new experiences
    social_battery: float = Field(default=1.0, ge=0.0, le=1.0)  # willingness to socialize
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    def apply_interaction_effect(self, relationship_quality: float, duration_minutes: float):
        """Update emotional state based on social interaction"""
        # Positive interactions boost mood and drain social battery
        mood_change = relationship_quality * 0.1 * min(duration_minutes / 10, 1.0)
        self.mood = max(-1.0, min(1.0, self.mood + mood_change))
        
        # All interactions drain social battery
        battery_drain = duration_minutes / 60.0 * 0.3  # 30% per hour of interaction
        self.social_battery = max(0.0, self.social_battery - battery_drain)
        
        # Update timestamp
        self.last_updated = datetime.now(timezone.utc)
    
    def regenerate_over_time(self, hours_elapsed: float):
        """Natural regeneration of emotional state over time"""
        # Social battery regenerates during alone time
        self.social_battery = min(1.0, self.social_battery + hours_elapsed * 0.5)
        
        # Mood drifts toward neutral
        mood_drift = hours_elapsed * 0.1
        if self.mood > 0:
            self.mood = max(0.0, self.mood - mood_drift)
        elif self.mood < 0:
            self.mood = min(0.0, self.mood + mood_drift)


class Relationship(BaseModel):
    """Enhanced relationship state between two personas"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    persona1_id: str
    persona2_id: str
    
    # Core relationship dimensions
    affinity: float = Field(default=0.0, ge=-1.0, le=1.0)  # -1 hostile, 0 neutral, 1 friendly
    trust: float = Field(default=0.0, ge=-1.0, le=1.0)     # willingness to be vulnerable
    respect: float = Field(default=0.0, ge=-1.0, le=1.0)   # admiration for capabilities
    intimacy: float = Field(default=0.0, ge=0.0, le=1.0)   # closeness and shared secrets
    
    # Relationship metadata
    relationship_type: RelationshipType = RelationshipType.STRANGER
    interaction_count: int = Field(default=0)
    total_interaction_time: int = Field(default=0)  # total minutes of interaction
    last_interaction: Optional[datetime] = None
    first_meeting: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Shared history
    shared_experiences: List[str] = Field(default_factory=list)
    memorable_moments: List[Dict[str, Any]] = Field(default_factory=list)  # significant interactions
    conflict_history: List[Dict[str, Any]] = Field(default_factory=list)   # disagreements/fights
    
    # Dynamic factors
    recent_interaction_quality: float = Field(default=0.0, ge=-1.0, le=1.0)  # quality of last few interactions
    compatibility_factors: Dict[str, float] = Field(default_factory=dict)    # specific compatibility areas
    
    def get_compatibility_score(self) -> float:
        """Calculate overall social compatibility (0.0 to 1.0)"""
        base_score = (abs(self.affinity) * 0.3 + abs(self.trust) * 0.25 + 
                     abs(self.respect) * 0.25 + self.intimacy * 0.2)
        
        # Bonus for positive relationships
        if self.affinity > 0 and self.trust > 0:
            base_score *= 1.2
            
        return min(1.0, base_score)
    
    def get_relationship_strength(self) -> float:
        """Get overall relationship strength (-1.0 to 1.0)"""
        return (self.affinity * 0.4 + self.trust * 0.3 + self.respect * 0.2 + 
                (self.intimacy if self.affinity > 0 else -self.intimacy) * 0.1)
    
    def update_relationship_type(self):
        """Auto-update relationship type based on dimensions"""
        strength = self.get_relationship_strength()
        
        if strength < -0.7:
            self.relationship_type = RelationshipType.ENEMY
        elif strength < -0.3:
            self.relationship_type = RelationshipType.RIVAL
        elif strength < 0.2:
            self.relationship_type = RelationshipType.STRANGER
        elif strength < 0.5:
            self.relationship_type = RelationshipType.ACQUAINTANCE
        elif strength < 0.8:
            self.relationship_type = RelationshipType.FRIEND
        else:
            self.relationship_type = RelationshipType.CLOSE_FRIEND

    def update_from_interaction(self, interaction_quality: float, duration_minutes: float = 5.0, 
                              context: str = "conversation"):
        """Update relationship based on interaction outcome"""
        # Weight recent interactions more heavily
        weight = min(1.0, duration_minutes / 30.0)  # Max weight at 30+ minutes
        
        # Update core dimensions
        affinity_change = interaction_quality * 0.05 * weight
        self.affinity = max(-1.0, min(1.0, self.affinity + affinity_change))
        
        # Trust builds slowly with positive interactions
        if interaction_quality > 0:
            trust_change = interaction_quality * 0.03 * weight
            self.trust = max(-1.0, min(1.0, self.trust + trust_change))
        
        # Respect can change based on impressive/disappointing interactions
        if abs(interaction_quality) > 0.5:  # Significant interactions
            respect_change = interaction_quality * 0.04 * weight
            self.respect = max(-1.0, min(1.0, self.respect + respect_change))
        
        # Intimacy grows with positive, extended interactions
        if interaction_quality > 0.3 and duration_minutes > 10:
            intimacy_change = 0.02 * weight
            self.intimacy = min(1.0, self.intimacy + intimacy_change)
        
        # Update metadata
        self.interaction_count += 1
        self.total_interaction_time += int(duration_minutes)
        self.last_interaction = datetime.now(timezone.utc)
        self.recent_interaction_quality = interaction_quality
        
        # Record memorable moments
        if abs(interaction_quality) > 0.7:
            self.memorable_moments.append({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "quality": interaction_quality,
                "context": context,
                "duration": duration_minutes
            })
        
        # Update relationship type
        self.update_relationship_type()
    
    def get_interaction_modifier(self) -> float:
        """Get modifier for interaction quality based on relationship state"""
        base_modifier = self.get_relationship_strength() * 0.3
        
        # Recent negative interactions have cooling effect
        if self.recent_interaction_quality < -0.3:
            base_modifier -= 0.2
            
        return max(-0.5, min(0.5, base_modifier))


class ConversationContext(BaseModel):
    """Current conversation state and context"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    participants: List[str] = Field(default_factory=list)  # persona IDs
    current_speaker: Optional[str] = None
    topic: str = Field(default="general")
    topic_drift_count: int = Field(default=0)
    duration: int = Field(default=0)  # seconds elapsed
    token_budget: int = Field(default=1000)
    tokens_used: int = Field(default=0)
    continue_score: int = Field(default=50, ge=0, le=100)
    score_history: List[int] = Field(default_factory=list)
    turn_count: int = Field(default=0)
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    ended_at: Optional[datetime] = None
    exit_reason: Optional[str] = None

    def add_turn(self, speaker_id: str, continue_score: int):
        """Record a conversation turn"""
        self.current_speaker = speaker_id
        self.turn_count += 1
        self.continue_score = continue_score
        self.score_history.append(continue_score)

    def should_continue(self) -> bool:
        """Check if conversation should continue based on continue score"""
        return self.continue_score >= 40 and self.token_budget > 50

    def end_conversation(self, reason: str):
        """End the conversation with a reason"""
        self.ended_at = datetime.now(timezone.utc)
        self.exit_reason = reason


class ConversationTurn(BaseModel):
    """Individual turn in a conversation"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    conversation_id: str
    speaker_id: str
    turn_number: int
    content: str
    response_type: str = "full_llm"  # full_llm, constrained, template
    continue_score: int = Field(ge=0, le=100)
    tokens_used: int = Field(default=0)
    processing_time: float = Field(default=0.0)  # seconds
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class MCPRequest(BaseModel):
    """MCP JSON-RPC 2.0 request format"""
    jsonrpc: str = "2.0"
    method: str
    params: Optional[Dict[str, Any]] = None
    id: Optional[str] = None


class MCPResponse(BaseModel):
    """MCP JSON-RPC 2.0 response format"""
    jsonrpc: str = "2.0"
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None
    id: Optional[str] = None


class MCPError(BaseModel):
    """MCP JSON-RPC 2.0 error format"""
    code: int
    message: str
    data: Optional[Any] = None


class SimulationState(BaseModel):
    """State of the chatroom simulation"""
    active_conversations: Dict[str, ConversationContext] = Field(default_factory=dict)
    persona_locations: Dict[str, str] = Field(default_factory=dict)  # persona_id -> room_id
    last_tick: float = Field(default_factory=time.time)
    simulation_running: bool = Field(default=False)
    metrics: Dict[str, Any] = Field(default_factory=dict)