"""
Conversation engine for managing persona interactions
"""

import time
import random
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta

from ..config import get_config
from ..models import (
    Persona, ConversationContext, ConversationTurn, Relationship, Memory, Priority
)
from ..persistence import SQLiteManager, VectorMemoryManager
from ..llm import LLMManager
from ..memory import MemoryImportanceScorer


class ConversationEngine:
    """Core conversation management and scoring system"""
    
    def __init__(
        self, 
        db_manager: SQLiteManager,
        memory_manager: VectorMemoryManager,
        llm_manager: LLMManager
    ):
        self.db = db_manager
        self.memory = memory_manager
        self.llm = llm_manager
        
        # Get configuration instance
        self.config = get_config()
        
        # Memory importance scoring
        self.importance_scorer = MemoryImportanceScorer()
        
        # Active conversations
        self.active_conversations: Dict[str, ConversationContext] = {}
        
        # Persona relationships cache
        self._relationship_cache: Dict[str, Relationship] = {}
    
    async def calculate_continue_score(
        self, 
        persona: Persona, 
        other_persona: Persona, 
        context: ConversationContext
    ) -> int:
        """Calculate the unified continue score (0-100) for conversation decisions"""
        
        # Time pressure component (0-30 points)
        time_score = await self._calculate_time_pressure_score(persona, context)
        
        # Topic alignment component (0-25 points)
        topic_score = await self._calculate_topic_alignment_score(persona, other_persona, context)
        
        # Social dynamics component (0-20 points)
        social_score = await self._calculate_social_compatibility_score(persona, other_persona)
        
        # Fatigue penalty (0 to -15 points)
        fatigue_penalty = min(self.config.conversation.max_fatigue_penalty, persona.interaction_state.interaction_fatigue // 2)
        
        # Relationship history modifier (-10 to +15 points)
        history_modifier = await self._get_relationship_modifier(persona, other_persona)
        
        # Resource constraints component (0-10 points)
        resource_score = self._calculate_resource_score(persona, context)
        
        # Calculate total score
        total_score = (
            time_score + 
            topic_score + 
            social_score - 
            fatigue_penalty + 
            history_modifier + 
            resource_score
        )
        
        return max(0, min(100, int(total_score)))
    
    async def _calculate_time_pressure_score(self, persona: Persona, context: ConversationContext) -> float:
        """Calculate time pressure component of continue score"""
        base_score = self.config.conversation.max_time_score
        
        priority = persona.interaction_state.current_priority
        duration = context.duration
        
        if priority == Priority.URGENT:
            # Rapid decay for urgent priorities
            decay_rate = duration / self.config.conversation.urgent_decay_rate
            return max(0, base_score - decay_rate)
        
        elif priority == Priority.IMPORTANT:
            # Moderate decay for important priorities
            decay_rate = duration / self.config.conversation.important_decay_rate
            return max(0, base_score - decay_rate)
        
        elif priority == Priority.CASUAL or priority == Priority.SOCIAL:
            # Slow decay for casual/social priorities
            decay_rate = duration / self.config.conversation.casual_decay_rate
            return max(0, base_score - decay_rate)
        
        else:
            # Default decay (use important decay rate as default)
            decay_rate = duration / self.config.conversation.important_decay_rate
            return max(0, base_score - decay_rate)
    
    async def _calculate_topic_alignment_score(
        self, 
        persona1: Persona, 
        persona2: Persona, 
        context: ConversationContext
    ) -> float:
        """Calculate topic alignment using minmax(avg(preferences))"""
        
        topic = context.topic
        p1_interest = persona1.topic_preferences.get(topic, 50)
        p2_interest = persona2.topic_preferences.get(topic, 50)
        
        avg_interest = (p1_interest + p2_interest) / 2
        min_interest = min(p1_interest, p2_interest)
        
        # Topic pull favors mutual interest over one-sided enthusiasm
        topic_pull = (avg_interest * 0.7) + (min_interest * 0.3)
        
        # Penalty for topic drift
        if context.topic_drift_count > 2:
            topic_pull *= 0.6
        
        # Scale to configured max topic score range
        return min(self.config.conversation.max_topic_score, topic_pull * self.config.conversation.max_topic_score / 100)
    
    async def _calculate_social_compatibility_score(
        self, 
        persona1: Persona, 
        persona2: Persona
    ) -> float:
        """Calculate social compatibility based on charisma and status"""
        
        # Base compatibility from charisma
        charisma_compatibility = min(persona1.charisma, persona2.charisma) * 0.8
        
        # Status compatibility (peers work better than extreme differences)
        status_modifier = self._get_status_compatibility(persona1, persona2)
        
        # Scale to configured max social score range
        base_score = (charisma_compatibility + status_modifier) / 2
        return min(self.config.conversation.max_social_score, base_score)
    
    def _get_status_compatibility(self, persona1: Persona, persona2: Persona) -> float:
        """Calculate status-based compatibility"""
        
        status_hierarchy = self.config.conversation.status_hierarchy
        
        default_status = status_hierarchy.get("commoner", 2)
        status1 = status_hierarchy.get(persona1.social_rank, default_status)
        status2 = status_hierarchy.get(persona2.social_rank, default_status)
        
        status_diff = abs(status1 - status2)
        
        # Peers (same status) have high compatibility
        if status_diff == 0:
            return self.config.conversation.same_status_compatibility
        # Adjacent status levels work well
        elif status_diff == 1:
            return self.config.conversation.adjacent_status_compatibility
        # Large status gaps create awkwardness
        elif status_diff >= self.config.conversation.large_status_gap_threshold:
            return self.config.conversation.distant_status_compatibility
        else:
            return self.config.conversation.default_status_compatibility
    
    async def _get_relationship_modifier(self, persona1: Persona, persona2: Persona) -> float:
        """Get relationship history modifier"""
        
        relationship = await self._get_relationship(persona1.id, persona2.id)
        
        if not relationship:
            return 0.0  # Neutral for no history
        
        # Use compatibility score from relationship
        compatibility = relationship.get_compatibility_score()
        
        # Scale to -10 to +15 range
        return compatibility * 12.5 - 2.5
    
    def _calculate_resource_score(self, persona: Persona, context: ConversationContext) -> float:
        """Calculate resource availability score"""
        
        score = self.config.conversation.max_resource_score
        
        # Time availability check
        min_time_threshold = self.config.persona.min_time_threshold
        if persona.interaction_state.available_time < min_time_threshold:
            time_factor = persona.interaction_state.available_time / min_time_threshold
            score *= time_factor
        
        # Token budget check
        low_token_budget = self.config.persona.low_token_budget
        if context.token_budget < low_token_budget:
            token_factor = context.token_budget / low_token_budget
            score *= token_factor
        
        # Social energy check
        low_energy_threshold = self.config.persona.low_social_energy
        if persona.interaction_state.social_energy < low_energy_threshold:
            energy_factor = persona.interaction_state.social_energy / low_energy_threshold
            score *= energy_factor
        
        return score
    
    async def _get_relationship(self, persona1_id: str, persona2_id: str) -> Optional[Relationship]:
        """Get or create relationship between personas"""
        
        cache_key = f"{persona1_id}_{persona2_id}"
        reverse_key = f"{persona2_id}_{persona1_id}"
        
        # Check cache first
        if cache_key in self._relationship_cache:
            return self._relationship_cache[cache_key]
        elif reverse_key in self._relationship_cache:
            return self._relationship_cache[reverse_key]
        
        # Load from database
        relationship = await self.db.load_relationship(persona1_id, persona2_id)
        
        if not relationship:
            # Create new neutral relationship
            relationship = Relationship(
                persona1_id=persona1_id,
                persona2_id=persona2_id
            )
            await self.db.save_relationship(relationship)
        
        # Cache the relationship
        self._relationship_cache[cache_key] = relationship
        
        return relationship
    
    async def initiate_conversation(
        self,
        persona1: Persona,
        persona2: Persona,
        initial_topic: str = "general",
        max_duration: Optional[int] = None,
        token_budget: int = 1000
    ) -> Optional[ConversationContext]:
        """Start a new conversation between two personas"""
        
        # Check if personas can interact
        if not self._can_personas_interact(persona1, persona2):
            return None
        
        # Create conversation context
        context = ConversationContext(
            participants=[persona1.id, persona2.id],
            topic=initial_topic,
            token_budget=token_budget
        )
        
        # Set duration limits
        max_time = min(
            persona1.interaction_state.available_time,
            persona2.interaction_state.available_time,
            max_duration or 600
        )
        
        context.duration = 0
        self.active_conversations[context.id] = context
        
        # Save to database
        await self.db.save_conversation(context)
        
        return context
    
    def _can_personas_interact(self, persona1: Persona, persona2: Persona) -> bool:
        """Check if two personas can start a conversation"""
        
        current_time = time.time()
        
        return (
            persona1.interaction_state.cooldown_until <= current_time and
            persona2.interaction_state.cooldown_until <= current_time and
            persona1.interaction_state.available_time > 30 and
            persona2.interaction_state.available_time > 30 and
            persona1.interaction_state.social_energy > 10 and
            persona2.interaction_state.social_energy > 10
        )
    
    async def process_conversation_turn(
        self,
        conversation_id: str,
        speaker_id: str,
        user_input: str
    ) -> Optional[ConversationTurn]:
        """Process a single turn in the conversation"""
        
        if conversation_id not in self.active_conversations:
            return None
        
        context = self.active_conversations[conversation_id]
        
        # Load personas
        speaker = await self.db.load_persona(speaker_id)
        other_persona_id = next(p for p in context.participants if p != speaker_id)
        other_persona = await self.db.load_persona(other_persona_id)
        
        if not speaker or not other_persona:
            return None
        
        # Calculate continue score
        continue_score = await self.calculate_continue_score(speaker, other_persona, context)
        
        # Generate response based on score
        start_time = time.time()
        response, response_type = await self.llm.generate_response_by_score(
            continue_score, user_input, speaker, context
        )
        processing_time = time.time() - start_time
        
        # Estimate token usage
        tokens_used = self.llm.estimate_token_usage(response, response_type)
        
        # Create conversation turn
        turn = ConversationTurn(
            conversation_id=conversation_id,
            speaker_id=speaker_id,
            turn_number=context.turn_count + 1,
            content=response,
            response_type=response_type,
            continue_score=continue_score,
            tokens_used=tokens_used,
            processing_time=processing_time
        )
        
        # Update conversation context
        context.add_turn(speaker_id, continue_score)
        context.tokens_used += tokens_used
        context.duration += max(30, int(processing_time))  # Minimum 30 seconds per turn
        context.token_budget -= tokens_used
        
        # Apply interaction effects
        await self._apply_interaction_effects(speaker, other_persona, context, turn)
        
        # Store memory of the interaction
        await self._store_interaction_memory(speaker, other_persona, context, turn)
        
        # Save turn and updated context
        await self.db.save_conversation_turn(turn)
        await self.db.save_conversation(context)
        
        # Check if conversation should end
        if not context.should_continue() or continue_score < 40:
            await self._end_conversation(context, "natural_conclusion")
        
        return turn
    
    async def _apply_interaction_effects(
        self,
        speaker: Persona,
        other_persona: Persona,
        context: ConversationContext,
        turn: ConversationTurn
    ):
        """Apply fatigue, energy costs, and relationship updates"""
        
        # Apply fatigue and energy costs
        turn_duration = max(30, int(turn.processing_time))
        
        speaker.interaction_state.apply_fatigue(turn_duration)
        other_persona.interaction_state.apply_fatigue(turn_duration // 2)  # Listener gets less fatigue
        
        # Update relationship based on turn quality
        relationship = await self._get_relationship(speaker.id, other_persona.id)
        
        if relationship:
            # Positive interaction if continue score is high
            positive = turn.continue_score >= 60
            significance = min(0.1, turn.continue_score / 1000)  # Small incremental changes
            
            relationship.update_from_interaction(positive, significance)
            await self.db.save_relationship(relationship)
            
            # Update cache
            cache_key = f"{speaker.id}_{other_persona.id}"
            self._relationship_cache[cache_key] = relationship
        
        # Save updated persona states
        await self.db.save_persona(speaker)
        await self.db.save_persona(other_persona)
    
    async def _store_interaction_memory(
        self,
        speaker: Persona,
        other_persona: Persona,
        context: ConversationContext,
        turn: ConversationTurn
    ):
        """Store conversation turn as memory for both personas"""
        
        # Get relationship for importance calculation
        relationship = await self._get_relationship(speaker.id, other_persona.id)
        
        # Calculate intelligent memory importance for speaker
        speaker_importance = self.importance_scorer.calculate_importance(
            content=turn.content,
            speaker=speaker,
            listener=other_persona,
            context={
                'continue_score': turn.continue_score,
                'topic': context.topic,
                'conversation_id': context.id,
                'turn_number': turn.turn_number
            },
            turn=turn,
            relationship=relationship
        )
        
        # Calculate intelligent memory importance for listener (slightly reduced)
        listener_importance = self.importance_scorer.calculate_importance(
            content=f"{speaker.name} said to me: {turn.content}",
            speaker=other_persona,  # Listener becomes the "speaker" for their memory
            listener=speaker,
            context={
                'continue_score': turn.continue_score,
                'topic': context.topic,
                'conversation_id': context.id,
                'turn_number': turn.turn_number
            },
            turn=turn,
            relationship=relationship
        ) * 0.8  # Reduce by 20% since they didn't speak
        
        # Create memory for speaker
        speaker_memory = Memory(
            persona_id=speaker.id,
            content=f"I said to {other_persona.name}: {turn.content}",
            memory_type="conversation",
            importance=speaker_importance,
            emotional_valence=self._calculate_emotional_valence(turn.continue_score),
            related_personas=[other_persona.id],
            metadata={
                "conversation_id": context.id,
                "turn_number": turn.turn_number,
                "topic": context.topic,
                "response_type": turn.response_type
            }
        )
        
        # Create memory for listener
        listener_memory = Memory(
            persona_id=other_persona.id,
            content=f"{speaker.name} said to me: {turn.content}",
            memory_type="conversation",
            importance=listener_importance,
            emotional_valence=self._calculate_emotional_valence(turn.continue_score),
            related_personas=[speaker.id],
            metadata={
                "conversation_id": context.id,
                "turn_number": turn.turn_number,
                "topic": context.topic,
                "response_type": turn.response_type
            }
        )
        
        # Store in vector memory
        await self.memory.store_memory(speaker_memory)
        await self.memory.store_memory(listener_memory)
    
    def _calculate_emotional_valence(self, continue_score: int) -> float:
        """Calculate emotional valence from continue score"""
        # Convert 0-100 continue score to -1.0 to 1.0 emotional valence
        return (continue_score - 50) / 50
    
    async def _end_conversation(self, context: ConversationContext, reason: str):
        """End a conversation and apply cooldown periods"""
        
        context.end_conversation(reason)
        
        # Load personas to apply cooldown
        personas = []
        for persona_id in context.participants:
            persona = await self.db.load_persona(persona_id)
            if persona:
                personas.append(persona)
        
        if len(personas) >= 2:
            await self._set_cooldown_periods(personas[0], personas[1], context)
        
        # Remove from active conversations
        if context.id in self.active_conversations:
            del self.active_conversations[context.id]
        
        # Save final state
        await self.db.save_conversation(context)
    
    async def _set_cooldown_periods(
        self,
        persona1: Persona,
        persona2: Persona,
        context: ConversationContext
    ):
        """Set cooldown periods based on conversation satisfaction"""
        
        base_cooldown = self.config.persona.base_cooldown_seconds
        
        # Adjust cooldown based on final continue score
        if context.continue_score > self.config.persona.high_continue_score:
            cooldown = base_cooldown * self.config.persona.satisfying_conversation_multiplier
        elif context.continue_score < self.config.persona.low_continue_score:
            cooldown = base_cooldown * self.config.persona.unsatisfying_conversation_multiplier
        else:
            cooldown = base_cooldown
        
        # Additional cooldown based on fatigue
        fatigue_multiplier = 1 + (persona1.interaction_state.interaction_fatigue / 100)
        cooldown *= fatigue_multiplier
        
        # Apply cooldown
        cooldown_until = time.time() + cooldown
        persona1.interaction_state.cooldown_until = cooldown_until
        persona2.interaction_state.cooldown_until = cooldown_until
        
        # Save updated states
        await self.db.save_persona(persona1)
        await self.db.save_persona(persona2)
    
    async def regenerate_social_energy(self):
        """Regenerate social energy for all personas over time"""
        
        personas = await self.db.list_personas()
        current_time = time.time()
        
        for persona in personas:
            last_update = persona.interaction_state.last_updated.timestamp()
            elapsed_seconds = int(current_time - last_update)
            
            if elapsed_seconds > 0:
                persona.interaction_state.regenerate_energy(elapsed_seconds)
                persona.interaction_state.last_updated = datetime.utcnow()
                await self.db.save_persona(persona)
    
    async def get_conversation_status(self, conversation_id: str) -> Optional[Dict]:
        """Get current status of a conversation"""
        
        if conversation_id not in self.active_conversations:
            return None
        
        context = self.active_conversations[conversation_id]
        
        return {
            "id": context.id,
            "participants": context.participants,
            "topic": context.topic,
            "turn_count": context.turn_count,
            "duration": context.duration,
            "continue_score": context.continue_score,
            "tokens_remaining": context.token_budget,
            "should_continue": context.should_continue()
        }