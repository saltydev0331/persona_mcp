# Persona Interaction Management System

## Overview

A sophisticated system for managing dynamic interactions between AI personas, preventing endless conversations while maintaining realistic social dynamics and character consistency.

## Problem Statement

AI personas in narrative environments (D&D campaigns, virtual worlds, etc.) need intelligent conversation management to prevent:

- Endless loops between NPCs
- Inappropriate interaction lengths (e.g., urgent characters getting stuck in casual chat)
- Unrealistic social dynamics (kings chatting for hours about grain prices)
- Computational resource waste on low-priority interactions

## Core Components

### 1. Interest Level System

Each persona maintains dynamic interest metrics that influence interaction behavior:

```python
class PersonaInteractionState:
    interest_level: int = 50          # 0-100 base interest in conversation
    interaction_fatigue: int = 0      # Increases with conversation length
    current_priority: str = "none"    # "urgent", "important", "casual", "none"
    available_time: int = 300         # Seconds willing to spend in conversation
    topic_preferences: Dict[str, int] # Interest levels for different topics
    social_energy: int = 100          # Depletes with interactions, regenerates over time
    cooldown_until: float = 0         # Timestamp when persona can re-engage

class ConversationContext:
    duration: int = 0                 # Seconds elapsed
    topic: str = "general"            # Current conversation topic
    topic_drift_count: int = 0        # Number of topic changes
    token_budget: int = 1000          # Remaining LLM tokens for conversation
    participants: List[Persona]       # All conversation participants
    continue_score: int = 50          # Current continuation score (0-100)
```

### 2. Unified Continue Score System

All exit decisions are based on a single 0-100 continue score that combines multiple factors:

```python
def calculate_continue_score(persona: Persona, other: Persona, context: ConversationContext) -> int:
    """Single scalar decision score combining all factors"""

    # Time pressure (0-30 points)
    time_score = 30
    if persona.current_priority == "urgent":
        time_score = max(0, 30 - (context.duration / 2))  # Rapid decay
    elif persona.current_priority == "important":
        time_score = max(0, 30 - (context.duration / 10))

    # Topic alignment (0-25 points)
    topic_pull = calculate_topic_alignment(persona, other, context.topic)
    topic_score = min(25, topic_pull)

    # Social dynamics (0-20 points)
    social_score = get_social_compatibility_score(persona, other)

    # Fatigue penalty (0 to -15 points)
    fatigue_penalty = min(15, persona.interaction_fatigue // 2)

    # Relationship history bonus/penalty (-10 to +15 points)
    history_modifier = get_relationship_modifier(persona, other)

    # Resource constraints (0-10 points)
    resource_score = 10
    if persona.available_time < 60:  # Less than 1 minute left
        resource_score = max(0, persona.available_time // 6)
    if context.token_budget < 100:  # Low token budget
        resource_score = min(resource_score, context.token_budget // 10)

    total_score = time_score + topic_score + social_score - fatigue_penalty + history_modifier + resource_score
    return max(0, min(100, total_score))

def should_continue_conversation(continue_score: int) -> bool:
    return continue_score >= 40  # Threshold for continuation
```

#### Topic Alignment Calculation

```python
def calculate_topic_alignment(persona1: Persona, persona2: Persona, topic: str) -> float:
    """Calculate mutual topic interest using minmax(avg(preferences))"""
    p1_interest = persona1.topic_preferences.get(topic, 50)
    p2_interest = persona2.topic_preferences.get(topic, 50)

    avg_interest = (p1_interest + p2_interest) / 2
    min_interest = min(p1_interest, p2_interest)
    max_interest = max(p1_interest, p2_interest)

    # Topic pull favors mutual interest over one-sided enthusiasm
    topic_pull = (avg_interest * 0.7) + (min_interest * 0.3)

    # Penalty for topic drift
    if hasattr(context, 'topic_drift_count') and context.topic_drift_count > 2:
        topic_pull *= 0.6  # Reduce pull if conversation is wandering

    return topic_pull
```

### 3. Social Dynamics

#### Status-Based Interaction Rules

- **High Status → Low Status**: Limited time, formal language, quick exits
- **Peer-to-Peer**: Natural conversation flow, moderate time limits
- **Low Status → High Status**: Respectful, brief unless invited to continue

#### Relationship History

- Previous positive interactions increase interest levels
- Negative history creates natural avoidance or tension
- Neutral parties follow standard social protocols

### 4. Topic Preference Matrix

Each persona has weighted preferences for conversation topics:

```python
example_personas = {
    "king_at_war": {
        "military_strategy": 95,
        "politics": 85,
        "diplomacy": 80,
        "logistics": 70,
        "local_news": 20,
        "grain_prices": 10,
        "gossip": 5
    },
    "tavern_keeper": {
        "local_news": 90,
        "gossip": 85,
        "business": 80,
        "travelers": 75,
        "politics": 40,
        "military_strategy": 20
    }
}
```

## Implementation Architecture

### 1. Conversation Orchestration with Budget Management

```python
@router.post("/personas/{persona1_id}/interact/{persona2_id}")
async def initiate_persona_interaction(
    persona1_id: str,
    persona2_id: str,
    interaction_context: InteractionContext,
    max_duration: Optional[int] = None,
    token_budget: int = 1000
):
    # Check cooldown periods
    if not can_personas_interact(persona1_id, persona2_id):
        return {"status": "cooldown", "message": "Personas in cooldown period"}

    # Initialize conversation with budget constraints
    context = ConversationContext(
        participants=[persona1, persona2],
        token_budget=token_budget,
        max_duration=min(persona1.available_time, persona2.available_time, max_duration or 600)
    )

    # Run conversation loop with budget monitoring
    while context.token_budget > 0 and context.duration < context.max_duration:
        continue_score = calculate_continue_score(persona1, persona2, context)

        if continue_score < 40:  # Exit threshold
            break

        # Route to appropriate response generation based on score
        response = await generate_response_by_score(continue_score, context)
        context.token_budget -= estimate_token_usage(response)
        context.duration += estimate_response_time(response)

    # Set cooldown periods after conversation ends
    set_cooldown_periods(persona1, persona2, context)

def can_personas_interact(persona1_id: str, persona2_id: str) -> bool:
    """Check if personas are available (not in cooldown)"""
    now = time.time()
    persona1 = get_persona(persona1_id)
    persona2 = get_persona(persona2_id)

    return (persona1.cooldown_until <= now and
            persona2.cooldown_until <= now and
            persona1.available_time > 30 and
            persona2.available_time > 30)

def set_cooldown_periods(persona1: Persona, persona2: Persona, context: ConversationContext):
    """Set cooldown based on conversation satisfaction and duration"""
    base_cooldown = 300  # 5 minutes base

    # Shorter cooldown for satisfying conversations
    if context.continue_score > 70:
        cooldown = base_cooldown * 0.5
    # Longer cooldown for unsatisfying/forced exits
    elif context.continue_score < 30:
        cooldown = base_cooldown * 2
    else:
        cooldown = base_cooldown

    # Additional cooldown based on fatigue
    fatigue_multiplier = 1 + (persona1.interaction_fatigue / 100)
    cooldown *= fatigue_multiplier

    persona1.cooldown_until = time.time() + cooldown
    persona2.cooldown_until = time.time() + cooldown
```

### 2. LLM Routing with Guardrails

```python
async def generate_response_by_score(continue_score: int, context: ConversationContext) -> str:
    """Route response generation based on continue score"""

    if continue_score >= 80:
        # High engagement: Full LLM with creative freedom
        return await generate_full_llm_response(context, creativity=0.8)

    elif continue_score >= 60:
        # Medium engagement: Standard LLM response
        return await generate_full_llm_response(context, creativity=0.6)

    elif continue_score >= 40:
        # Low engagement: Constrained LLM with exit preparation
        return await generate_constrained_response(context, prepare_exit=True)

    else:
        # Very low engagement: Template-based quick responses
        return generate_template_exit_response(context)

async def generate_constrained_response(context: ConversationContext, prepare_exit: bool = False) -> str:
    """Generate shorter, more focused responses for low-engagement scenarios"""
    prompt_constraints = {
        "max_length": 50,  # Word limit
        "style": "concise",
        "prepare_exit": prepare_exit,
        "avoid_topics": get_low_interest_topics(context)
    }

    return await llm_generate(context, constraints=prompt_constraints)

def generate_template_exit_response(context: ConversationContext) -> str:
    """Fast template-based responses for very low continue scores"""
    speaker = context.current_speaker

    exit_templates = {
        "urgent": [
            "I really must go.",
            "I have urgent matters to attend to.",
            "Perhaps we can continue this later."
        ],
        "bored": [
            "Interesting... I should get going though.",
            "I'll let you get back to what you were doing.",
            "Nice chatting with you."
        ],
        "tired": [
            "I'm feeling a bit drained.",
            "I think I need a break from talking.",
            "It's been a long day for me."
        ]
    }

    exit_reason = determine_exit_reason(context.continue_score, speaker)
    return random.choice(exit_templates[exit_reason])
```

### 3. Budget and Resource Management

```python
class ConversationBudgetManager:
    def __init__(self, initial_token_budget: int = 1000):
        self.token_budget = initial_token_budget
        self.time_budget = 600  # 10 minutes max
        self.response_count = 0

    def can_continue(self, context: ConversationContext) -> bool:
        """Check if conversation can continue within budget constraints"""
        return (self.token_budget > 100 and
                context.duration < self.time_budget and
                all(p.available_time > 30 for p in context.participants))

    def estimate_token_usage(self, response: str, response_type: str) -> int:
        """Estimate token consumption for different response types"""
        base_tokens = len(response.split()) * 1.3  # Rough estimation

        multipliers = {
            "full_llm": 1.5,      # Full LLM calls use more tokens
            "constrained": 1.0,    # Constrained responses use normal tokens
            "template": 0.1        # Template responses use minimal tokens
        }

        return int(base_tokens * multipliers.get(response_type, 1.0))

    def update_budgets(self, response: str, response_type: str, duration: int):
        """Update remaining budgets after response"""
        self.token_budget -= self.estimate_token_usage(response, response_type)
        self.time_budget -= duration
        self.response_count += 1

        # Diminishing returns - longer conversations become more expensive
        if self.response_count > 10:
            self.token_budget -= 20  # Additional token penalty for long conversations
```

## Use Cases

### 1. D&D Campaign Management

**Scenario**: King leading army to war encounters local farmers

```python
king_state = PersonaInteractionState(
    current_priority="urgent",
    available_time=60,
    topic_preferences={"military": 90, "grain_prices": 10}
)

# After 45 seconds of grain discussion:
# System generates: "I must attend to my troops. Speak with my quartermaster about supplies."
```

### 2. Virtual World NPCs

**Scenario**: Merchant vs. Noble in marketplace

```python
merchant_preferences = {"trade": 95, "politics": 30}
noble_preferences = {"politics": 90, "trade": 40}

# Conversation naturally gravitates toward mutually interesting topics
# or terminates when interests diverge too much
```

### 3. AR/VR Social Spaces

**Scenario**: Multiple personas in shared virtual environment

```python
# System manages multiple concurrent conversations
# Prevents all NPCs from clustering around one player
# Maintains realistic social group dynamics
```

### 4. College Party Stress Test

**Scenario**: High-energy social environment with competing attention

```python
college_party_personas = {
    "topic_preferences": {
        "flirting": 95,
        "relationships": 90,
        "parties": 85,
        "gossip": 80,
        "drama": 75,
        "academics": 20,
        "serious_topics": 10
    },
    "interaction_state": {
        "social_energy": 150,     # High energy, want to talk to EVERYONE
        "interest_level": 80,     # Generally interested in others
        "available_time": 600,    # Will chat for 10+ minutes easily
        "current_priority": "social",
        "charisma": random.randint(12, 18)  # D&D style stats
    }
}

# Special interaction rules for high-social environments
def college_interaction_modifiers(persona1, persona2, context):
    if persona1.finds_attractive(persona2):
        context.available_time *= 3
        context.interest_level += 30

    # Drama multiplier - relationship drama = MUST DISCUSS
    if context.topic in ["breakups", "crushes", "relationship_drama"]:
        context.interest_level = 100

    # Turn-based management prevents everyone talking at once
    turn_manager = ConversationTurnManager([persona1, persona2])
    return turn_manager.next_speaker()
```

## Future Enhancements

### 1. Emotional Intelligence

- Mood affects interaction willingness
- Emotional contagion between personas
- Stress/happiness impacts conversation quality

### 2. Memory Integration

- Long-term relationship development
- Remembered conversation preferences
- Grudges and friendships affecting future interactions

### 3. Group Dynamics

- Multi-participant conversation management
- Social hierarchy enforcement
- Crowd behavior simulation

### 4. Turn-Based Conversation Initiative

**Charisma-Based Initiative System:**

```python
def calculate_conversation_initiative(persona: Persona) -> int:
    base_initiative = persona.charisma * 2
    social_status_bonus = get_status_modifier(persona.social_rank)
    energy_modifier = persona.social_energy // 10
    random_factor = random.randint(1, 20)  # D&D style randomness

    return base_initiative + social_status_bonus + energy_modifier + random_factor

def determine_speaking_order(participants: List[Persona]) -> List[Persona]:
    initiative_rolls = [(p, calculate_conversation_initiative(p)) for p in participants]
    return [p for p, _ in sorted(initiative_rolls, key=lambda x: x[1], reverse=True)]
```

**Turn Management:**

```python
class ConversationTurnManager:
    def __init__(self, participants: List[Persona]):
        self.speaking_order = determine_speaking_order(participants)
        self.current_speaker_index = 0
        self.turn_duration = 30  # seconds per turn

    def next_speaker(self) -> Persona:
        speaker = self.speaking_order[self.current_speaker_index]
        self.current_speaker_index = (self.current_speaker_index + 1) % len(self.speaking_order)
        return speaker

    def can_interrupt(self, interrupter: Persona, current_speaker: Persona) -> bool:
        # High charisma or urgent priority can interrupt
        return (interrupter.charisma > current_speaker.charisma + 3) or \
               (interrupter.current_priority == "urgent")
```

### 5. Interaction Denoising System

**Conversation Filtering:**

```python
class InteractionDenoiser:
    def __init__(self):
        self.noise_patterns = [
            r"um+\s+",           # Remove excessive "ums"
            r"\b(like)\b\s+",    # Filter filler words
            r"you know\s+",      # Remove "you know"
            r"\.\.\.\s*",        # Clean up trailing dots
        ]

    def denoise_response(self, text: str, persona: Persona) -> str:
        # Remove repetitive phrases
        denoised = self.remove_repetition(text)

        # Filter based on persona sophistication
        if persona.intelligence > 70:
            denoised = self.remove_filler_words(denoised)

        # Ensure response quality
        return self.ensure_coherence(denoised)

    def remove_repetition(self, text: str) -> str:
        sentences = text.split('.')
        unique_sentences = []
        for sentence in sentences:
            if sentence.strip() not in [s.strip() for s in unique_sentences]:
                unique_sentences.append(sentence)
        return '. '.join(unique_sentences)
```

**Quality Gates:**

```python
class ResponseQualityFilter:
    def validate_response(self, response: str, context: ConversationContext) -> bool:
        checks = [
            len(response.split()) >= 3,  # Minimum word count
            not self.is_repetitive(response),
            self.matches_persona_voice(response, context.speaker),
            self.is_contextually_relevant(response, context.topic)
        ]
        return all(checks)

    def regenerate_if_needed(self, response: str, context: ConversationContext) -> str:
        if not self.validate_response(response, context):
            return self.generate_fallback_response(context)
        return response
```

### 6. Voice Integration with ElevenLabs

- Tone changes based on interest level
- Natural audio cues for conversation endings
- Emotional inflection matching persona state

### 5. AR/VR Spatial Awareness

- Proximity-based interaction initiation
- Body language and gesture integration
- Spatial conversation boundaries

## Technical Considerations

### Performance Optimization

- Batch evaluation of multiple conversations
- Cached topic preference calculations
- Efficient state persistence

### Scalability

- Distributed conversation processing
- Load balancing for high NPC counts
- Resource allocation based on interaction priority

### Data Storage

```sql
-- Additional tables for interaction management
CREATE TABLE persona_interaction_states (
    persona_id TEXT PRIMARY KEY,
    interest_level INTEGER DEFAULT 50,
    interaction_fatigue INTEGER DEFAULT 0,
    current_priority TEXT DEFAULT 'none',
    available_time INTEGER DEFAULT 300,
    social_energy INTEGER DEFAULT 100,
    charisma INTEGER DEFAULT 10,
    cooldown_until REAL DEFAULT 0,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE topic_preferences (
    persona_id TEXT,
    topic TEXT,
    preference_score INTEGER,
    PRIMARY KEY (persona_id, topic)
);

CREATE TABLE interaction_history (
    id TEXT PRIMARY KEY,
    persona1_id TEXT,
    persona2_id TEXT,
    duration INTEGER,
    topics TEXT, -- JSON array
    satisfaction_score INTEGER,
    turn_order TEXT, -- JSON array of speaker sequence
    response_quality_scores TEXT, -- JSON array of quality metrics
    continue_score_history TEXT, -- JSON array of score progression
    token_usage INTEGER,
    exit_reason TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE conversation_turns (
    id TEXT PRIMARY KEY,
    conversation_id TEXT,
    speaker_id TEXT,
    turn_number INTEGER,
    initiative_roll INTEGER,
    response_text TEXT,
    quality_score REAL,
    denoised_response TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Advanced Features

### Unified Continue Score System

The conversation system uses a single 0-100 score that combines all decision factors:

```python
# Example: King at war meets merchant
king = Persona(charisma=16, current_priority="urgent", available_time=120)
merchant = Persona(charisma=14, current_priority="casual", available_time=600)

context = ConversationContext(
    topic="trade_routes",
    duration=90,  # 1.5 minutes in
    token_budget=800
)

# Calculate continue score:
# Time pressure: 15/30 (urgent priority, 90 seconds elapsed)
# Topic alignment: 12/25 (merchant loves trade, king neutral)
# Social compatibility: 15/20 (both high charisma)
# Fatigue: -3 (minimal fatigue)
# History: 0 (neutral)
# Resources: 8/10 (good time/token budget)
# Total: 47/100 → Continue (above 40 threshold)

continue_score = 47
# Routes to constrained LLM response with exit preparation
```

### Budget-Aware Conversation Management

```python
# Conversation automatically manages multiple resource constraints:
budget_manager = ConversationBudgetManager(initial_token_budget=1000)

# High-engagement conversation (score 85):
# - Uses full LLM (expensive but rich responses)
# - ~50 tokens per response
# - Can sustain ~20 high-quality exchanges

# Low-engagement conversation (score 35):
# - Uses template responses (cheap)
# - ~5 tokens per response
# - Can sustain 200+ quick exchanges before exit
```

### Cooldown and Re-engagement Prevention

```python
# After conversation ends, personas enter cooldown:
successful_conversation_cooldown = 150  # 2.5 minutes (short)
unsatisfying_conversation_cooldown = 600  # 10 minutes (long)

# Prevents immediate re-engagement loops:
# - King can't get stuck talking to same farmer repeatedly
# - College students cycle through different conversation partners
# - System maintains social flow without artificial constraints
```

### Denoising and Quality Control

Multi-layered filtering ensures conversation quality:

```python
class ConversationQualityPipeline:
    def process_response(self, raw_response: str, persona: Persona, context: ConversationContext) -> str:
        # Stage 1: Remove filler words and repetition
        denoised = self.denoiser.denoise_response(raw_response, persona)

        # Stage 2: Validate response quality
        if not self.quality_filter.validate_response(denoised, context):
            denoised = self.generate_fallback_response(context)

        # Stage 3: Ensure persona consistency
        final_response = self.persona_filter.align_with_personality(denoised, persona)

        # Stage 4: Log quality metrics
        self.log_response_quality(final_response, context)

        return final_response
```

## Conclusion

This interaction management system creates believable, dynamic social environments where AI personas behave with realistic social intelligence. By implementing interest-based conversation management, we can create rich narrative experiences without the computational overhead of endless NPC chatter.

The system scales from simple D&D encounters to complex virtual worlds, providing the foundation for truly immersive AI-driven social experiences.

---

## Chatroom Simulation System

### Overview

A controlled testing environment using themed chatrooms as narrative containers for observing emergent persona behavior. Each room defines a social contract that biases interaction logic, enabling safe observation and tuning before scaling to production environments.

### Room Archetype Framework

Each chatroom establishes environmental rules that influence persona behavior:

| Room Type      | Social Contract        | Typical Topics                  | Priority Bias               | Atmosphere       |
| -------------- | ---------------------- | ------------------------------- | --------------------------- | ---------------- |
| `#ai-tavern`   | Casual gossip hub      | rumors, travelers, local events | `casual`, `social`          | Warm, lively     |
| `#ai-market`   | Transactional space    | trade, negotiation, reputation  | `important`, `business`     | Loud, crowded    |
| `#ai-fortress` | Strategic command      | politics, security, logistics   | `urgent`, `military`        | Tense, focused   |
| `#ai-court`    | Formal diplomacy       | etiquette, alliances, culture   | `important`, `diplomatic`   | Elegant, refined |
| `#ai-library`  | Intellectual sanctuary | knowledge, research, philosophy | `academic`, `contemplative` | Quiet, peaceful  |

### Room Configuration Schema

```json
{
  "room_id": "ai_tavern",
  "name": "The Prancing Pony Tavern",
  "description": "A cozy tavern where travelers share stories",
  "default_priority": "social",
  "mood": "casual",
  "topic_bias": ["gossip", "rumors", "travelers", "local_events"],
  "max_concurrent_conversations": 5,
  "energy_regen_rate": 2,
  "modifiers": {
    "interest_level_bonus": 10,
    "social_energy_bonus": 5,
    "available_time_multiplier": 1.2,
    "fatigue_rate": 0.8
  },
  "exit_phrases": [
    "I should order another round.",
    "Let me find a quieter corner."
  ],
  "atmosphere": {
    "noise_level": "moderate",
    "lighting": "warm",
    "crowd_density": "lively"
  }
}
```

### Environmental Modifiers

Room-specific adjustments applied to persona behavior:

```python
def apply_room_modifiers(persona: Persona, room: Room) -> Persona:
    """Apply environmental effects based on room type"""

    # Tavern: Social energy boost, extended conversation time
    if room.id == "ai_tavern":
        persona.interest_level += 10
        persona.current_priority = "social"
        persona.available_time *= 1.2
        persona.social_energy += 5

    # Market: Business focus, reduced social patience
    elif room.id == "ai_market":
        persona.current_priority = "business"
        persona.available_time *= 0.8
        persona.interaction_fatigue += 2

    # Fortress: Urgent mindset, minimal social tolerance
    elif room.id == "ai_fortress":
        persona.current_priority = "urgent"
        persona.interest_level -= 10
        persona.available_time *= 0.6

    # Library: Extended focus, reduced fatigue
    elif room.id == "ai_library":
        persona.current_priority = "academic"
        persona.available_time *= 1.5
        persona.interaction_fatigue *= 0.5

    return persona
```

### Orchestration Architecture

#### 1. Room Management Loop

```python
class ChatroomOrchestrator:
    def __init__(self, rooms: List[Room]):
        self.rooms = rooms
        self.active_conversations = {}
        self.persona_locations = {}  # persona_id -> room_id

    async def simulation_tick(self):
        """Execute one simulation cycle across all rooms"""
        for room in self.rooms:
            await self.process_room(room)

    async def process_room(self, room: Room):
        """Handle conversations within a specific room"""
        # 1. Select available participants
        available_personas = self.get_available_personas(room)

        # 2. Trigger new conversations if capacity allows
        if len(self.active_conversations[room.id]) < room.max_concurrent:
            participants = self.select_conversation_participants(available_personas)
            if participants:
                topic = random.choice(room.topic_bias)
                await self.initiate_conversation(participants, room, topic)

        # 3. Process ongoing conversations
        await self.update_active_conversations(room)

        # 4. Handle persona migrations
        await self.process_room_migrations(room)
```

#### 2. Participant Selection Strategy

```python
def select_conversation_participants(self, available_personas: List[Persona]) -> List[Persona]:
    """Select 2-3 personas for conversation based on compatibility"""

    # Filter by social energy and availability
    candidates = [p for p in available_personas
                 if p.social_energy > 30 and p.available_time > 60]

    if len(candidates) < 2:
        return []

    # Prefer diverse social dynamics
    participants = []

    # Select high-charisma initiator
    initiator = max(candidates, key=lambda p: p.charisma + random.randint(1, 10))
    participants.append(initiator)
    candidates.remove(initiator)

    # Select compatible responder
    for candidate in sorted(candidates, key=lambda p: calculate_social_compatibility(initiator, p), reverse=True):
        participants.append(candidate)
        if len(participants) >= 2:
            break

    return participants
```

#### 3. Cross-Room Migration

```python
def evaluate_room_migration(self, persona: Persona, current_room: Room) -> Optional[Room]:
    """Determine if persona should move to different room"""

    # High social energy seeks more active rooms
    if persona.social_energy > 80:
        target_rooms = [r for r in self.rooms if r.energy_regen_rate > current_room.energy_regen_rate]

    # Low energy seeks quieter spaces
    elif persona.social_energy < 30:
        target_rooms = [r for r in self.rooms if r.energy_regen_rate < current_room.energy_regen_rate]

    # Bored personas seek topic variety
    elif persona.interaction_fatigue > 50:
        target_rooms = [r for r in self.rooms
                       if not any(topic in current_room.topic_bias for topic in r.topic_bias)]
    else:
        return None

    if target_rooms:
        return random.choice(target_rooms)
    return None
```

### Observation and Metrics

#### Real-Time Monitoring

```python
class SimulationMetrics:
    def __init__(self):
        self.conversation_logs = []
        self.room_activity = defaultdict(list)
        self.persona_trajectories = defaultdict(list)

    def log_conversation(self, conversation: Conversation):
        """Record conversation for analysis"""
        self.conversation_logs.append({
            "id": conversation.id,
            "room_id": conversation.room.id,
            "participants": [p.id for p in conversation.participants],
            "duration": conversation.duration,
            "topic": conversation.topic,
            "continue_score_progression": conversation.score_history,
            "exit_reason": conversation.exit_reason,
            "token_usage": conversation.token_usage,
            "timestamp": time.time()
        })

    def analyze_room_dynamics(self, room_id: str) -> Dict:
        """Generate room activity summary"""
        room_conversations = [c for c in self.conversation_logs if c["room_id"] == room_id]

        return {
            "total_conversations": len(room_conversations),
            "avg_duration": np.mean([c["duration"] for c in room_conversations]),
            "topic_distribution": Counter([c["topic"] for c in room_conversations]),
            "participant_frequency": Counter([p for c in room_conversations for p in c["participants"]]),
            "avg_continue_score": np.mean([np.mean(c["continue_score_progression"]) for c in room_conversations])
        }
```

#### Dashboard Visualization

```python
# Example metrics for monitoring
simulation_dashboard = {
    "rooms": {
        "ai_tavern": {
            "conversations_per_hour": 12,
            "avg_duration": 180,  # 3 minutes
            "dominant_topics": ["gossip", "travelers"],
            "social_energy": "high",
            "most_active_personas": ["bard", "innkeeper", "merchant"]
        },
        "ai_fortress": {
            "conversations_per_hour": 4,
            "avg_duration": 90,   # 1.5 minutes
            "dominant_topics": ["strategy", "logistics"],
            "social_energy": "low",
            "most_active_personas": ["commander", "scout", "advisor"]
        }
    },
    "personas": {
        "migration_patterns": "tavern -> market -> court -> library",
        "conversation_preferences": {"bard": "tavern", "merchant": "market"},
        "energy_cycles": "90% recover within 10 minutes"
    }
}
```

### Testing Scenarios

#### 1. Stress Testing

- **College Party Simulation**: 20 high-energy personas in tavern setting
- **Market Crash Event**: Emergency priority applied to all merchants
- **Royal Court Session**: Formal diplomatic gathering with status hierarchies

#### 2. Behavior Validation

- **Topic Drift Analysis**: Monitor conversation coherence over time
- **Social Dynamics**: Verify status-based interaction patterns
- **Resource Management**: Confirm budget constraints prevent runaway costs

#### 3. Emergent Behavior Discovery

- **Faction Formation**: Do like-minded personas naturally cluster?
- **Information Propagation**: How does gossip spread between rooms?
- **Leadership Emergence**: Which personas become conversation dominators?

### Production Integration

#### n8n Workflow Integration

```yaml
# Example n8n workflow trigger
trigger: "Schedule - Every 30 seconds"
actions:
  - HTTP Request: GET /simulation/tick
  - Condition: "conversations_started > 0"
  - Discord Webhook: Post conversation to appropriate channel
  - Database: Update persona states and room metrics
```

#### Discord Output Format

```
🍺 **#ai-tavern**
**Bard Lyralei** → **Merchant Gorin**
*"Have you heard about the strange lights seen near the old ruins?"*

**Merchant Gorin** → **Bard Lyralei**
*"Aye, travelers have been talking about it all week. Bad for business, it is."*

[Continue Score: 72 | Duration: 2:30 | Topic: rumors]
```

### Future Enhancements

#### Environmental Events

```python
# Dynamic room state changes
events = {
    "market_raid": {
        "affected_rooms": ["ai_market"],
        "duration": 300,  # 5 minutes
        "effects": {
            "all_personas_priority": "urgent",
            "topic_bias_override": ["security", "escape", "danger"]
        }
    },
    "royal_feast": {
        "affected_rooms": ["ai_court", "ai_tavern"],
        "effects": {
            "social_energy_bonus": 20,
            "available_time_multiplier": 2.0
        }
    }
}
```

#### Advanced Analytics

- **Conversation Network Analysis**: Map social relationship graphs
- **Predictive Modeling**: Forecast persona behavior patterns
- **A/B Testing Framework**: Compare different room configurations
- **Natural Language Analysis**: Analyze conversation content quality

This chatroom simulation system provides a controlled environment for observing and refining persona interaction dynamics before deployment in production scenarios.
