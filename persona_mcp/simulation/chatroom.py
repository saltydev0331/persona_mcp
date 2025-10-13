"""
Chatroom simulation harness for testing persona interactions
"""

import asyncio
import random
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from ..config import get_config
from ..models import Persona, ConversationContext, SimulationState, Priority
from ..conversation import ConversationEngine
from ..persistence import SQLiteManager, VectorMemoryManager
from ..llm import LLMManager


class ChatroomSimulation:
    """Simulation harness for testing persona interactions in a virtual chatroom"""
    
    def __init__(
        self,
        db_manager: SQLiteManager,
        memory_manager: VectorMemoryManager,
        llm_manager: LLMManager,
        conversation_engine: ConversationEngine
    ):
        self.db = db_manager
        self.memory = memory_manager
        self.llm = llm_manager
        self.conversation = conversation_engine
        
        # Get configuration instance
        self.config = get_config()
        
        # Simulation state
        self.state = SimulationState()
        self.tick_interval = self.config.session.tick_interval_seconds
        
        # Room configuration (virtual tavern for testing)
        self.room_config = {
            "name": self.config.simulation.room_name,
            "description": self.config.simulation.room_description,
            "topics": self.config.simulation.default_topics,
            "max_concurrent_conversations": self.config.simulation.max_concurrent_conversations,
            "energy_regen_rate": self.config.simulation.energy_regen_rate
        }
        
        # Simulation topics that can spontaneously start conversations
        self.conversation_starters = [
            "I heard something interesting today...",
            "Have you noticed anything strange lately?",
            "What brings you to the tavern?",
            "I've been thinking about something...",
            "Did you hear about what happened in town?",
            "I have a story you might find amusing...",
            "What's your take on recent events?",
            "I'm curious about your experiences with...",
        ]
    
    async def initialize_simulation(self):
        """Set up the simulation environment"""
        
        logging.info("Initializing chatroom simulation...")
        
        # Ensure default personas exist
        personas = await self.db.list_personas()
        
        if len(personas) < 2:
            logging.warning("Need at least 2 personas for simulation")
            return False
        
        # Place personas in the tavern
        for persona in personas:
            self.state.persona_locations[persona.id] = "tavern"
        
        logging.info(f"Simulation initialized with {len(personas)} personas in the tavern")
        return True
    
    async def run_simulation(self, duration_minutes: int = 10):
        """Run the simulation for specified duration"""
        
        if not await self.initialize_simulation():
            return
        
        self.state.simulation_running = True
        end_time = datetime.now() + timedelta(minutes=duration_minutes)
        
        logging.info(f"Starting simulation for {duration_minutes} minutes...")
        
        tick_count = 0
        
        try:
            while datetime.now() < end_time and self.state.simulation_running:
                await self._simulation_tick(tick_count)
                tick_count += 1
                await asyncio.sleep(self.tick_interval)
                
        except KeyboardInterrupt:
            logging.info("Simulation interrupted by user")
        
        finally:
            self.state.simulation_running = False
            await self._cleanup_simulation()
        
        logging.info("Simulation completed")
        await self._print_simulation_summary()
    
    async def _simulation_tick(self, tick_count: int):
        """Execute one simulation tick"""
        
        current_time = datetime.now()
        self.state.last_tick = current_time.timestamp()
        
        logging.info(f"Simulation tick {tick_count}")
        
        # Update persona energy regeneration
        await self.conversation.regenerate_social_energy()
        
        # Process ongoing conversations
        await self._process_active_conversations()
        
        # Potentially start new conversations
        if len(self.state.active_conversations) < self.room_config["max_concurrent_conversations"]:
            await self._try_start_conversation()
        
        # Log current state
        await self._log_simulation_state()
    
    async def _process_active_conversations(self):
        """Process and potentially end active conversations"""
        
        conversations_to_end = []
        
        for conv_id, context in self.state.active_conversations.items():
            # Check if conversation should naturally end
            if not context.should_continue():
                conversations_to_end.append(conv_id)
                continue
            
            # Randomly advance conversation (simulate autonomous interaction)
            if random.random() < 0.3:  # 30% chance per tick
                await self._advance_conversation(conv_id)
        
        # End conversations that should end
        for conv_id in conversations_to_end:
            await self._end_simulation_conversation(conv_id, "natural_conclusion")
    
    async def _advance_conversation(self, conversation_id: str):
        """Advance a conversation by one turn"""
        
        if conversation_id not in self.state.active_conversations:
            return
        
        context = self.state.active_conversations[conversation_id]
        
        if len(context.participants) < 2:
            return
        
        # Choose random speaker (alternate or random)
        if context.current_speaker:
            # Switch to other participant
            other_participants = [p for p in context.participants if p != context.current_speaker]
            speaker_id = random.choice(other_participants) if other_participants else context.participants[0]
        else:
            speaker_id = random.choice(context.participants)
        
        # Generate a conversational prompt
        prompt = self._generate_conversation_prompt(context)
        
        # Process the turn
        turn = await self.conversation.process_conversation_turn(
            conversation_id, speaker_id, prompt
        )
        
        if turn:
            # Update simulation state
            self.state.active_conversations[conversation_id] = context
            
            # Load speaker persona for logging
            speaker = await self.db.load_persona(speaker_id)
            speaker_name = speaker.name if speaker else speaker_id
            
            logging.info(f"Conversation turn: {speaker_name} -> {turn.content[:60]}... (Score: {turn.continue_score})")
        
    def _generate_conversation_prompt(self, context: ConversationContext) -> str:
        """Generate a natural conversation prompt based on context"""
        
        if context.turn_count == 0:
            # Opening conversation
            return random.choice(self.conversation_starters)
        
        # Continuing conversation - respond to the topic
        topic_responses = {
            "gossip": [
                "That reminds me of something else I heard...",
                "Speaking of gossip, did you know...",
                "I have another story along those lines..."
            ],
            "travel": [
                "I've been to a place like that...",
                "That sounds like an interesting journey...",
                "Travel can be so unpredictable..."
            ],
            "magic": [
                "Magic is fascinating, isn't it?",
                "I've had some strange experiences with magic...",
                "The old ways are not forgotten..."
            ],
            "stories": [
                "That's quite a tale!",
                "Stories like that make me think...",
                "I love a good story..."
            ]
        }
        
        topic = context.topic
        if topic in topic_responses:
            return random.choice(topic_responses[topic])
        else:
            return random.choice([
                "That's interesting...",
                "Tell me more about that.",
                "I see what you mean.",
                "That makes sense to me."
            ])
    
    async def _try_start_conversation(self):
        """Attempt to start a new conversation between available personas"""
        
        # Get available personas
        personas = await self.db.list_personas()
        available_personas = [
            p for p in personas 
            if (p.interaction_state.is_available() and 
                p.id not in [pid for conv in self.state.active_conversations.values() 
                           for pid in conv.participants])
        ]
        
        if len(available_personas) < 2:
            return  # Need at least 2 personas
        
        # Select two personas with decent compatibility
        best_pair = None
        best_score = 0
        
        for i in range(len(available_personas)):
            for j in range(i + 1, len(available_personas)):
                persona1, persona2 = available_personas[i], available_personas[j]
                
                # Quick compatibility check based on charisma and energy
                compatibility = (
                    min(persona1.charisma, persona2.charisma) +
                    (persona1.interaction_state.social_energy + persona2.interaction_state.social_energy) / 20
                )
                
                if compatibility > best_score:
                    best_score = compatibility
                    best_pair = (persona1, persona2)
        
        if not best_pair or best_score < 10:
            return  # No good pairs available
        
        persona1, persona2 = best_pair
        
        # Choose random topic from room topics
        topic = random.choice(self.room_config["topics"])
        
        # Start conversation
        context = await self.conversation.initiate_conversation(
            persona1, persona2, topic, token_budget=500  # Smaller budget for simulation
        )
        
        if context:
            self.state.active_conversations[context.id] = context
            
            logging.info(f"Started conversation: {persona1.name} & {persona2.name} about {topic}")
            
            # Immediately generate first exchange
            await self._advance_conversation(context.id)
    
    async def _end_simulation_conversation(self, conversation_id: str, reason: str):
        """End a conversation in the simulation"""
        
        if conversation_id not in self.state.active_conversations:
            return
        
        context = self.state.active_conversations[conversation_id]
        
        # Load participant names for logging
        participant_names = []
        for persona_id in context.participants:
            persona = await self.db.load_persona(persona_id)
            participant_names.append(persona.name if persona else persona_id)
        
        logging.info(f"Ending conversation: {' & '.join(participant_names)} ({reason})")
        
        # End through conversation engine
        await self.conversation._end_conversation(context, reason)
        
        # Remove from simulation state
        del self.state.active_conversations[conversation_id]
    
    async def _log_simulation_state(self):
        """Log current simulation state"""
        
        active_count = len(self.state.active_conversations)
        
        if active_count > 0:
            logging.info(f"Active conversations: {active_count}")
            
            for conv_id, context in self.state.active_conversations.items():
                # Get participant names
                participant_names = []
                for persona_id in context.participants:
                    persona = await self.db.load_persona(persona_id)
                    participant_names.append(persona.name if persona else persona_id)
                
                logging.info(f"  {' & '.join(participant_names)}: {context.topic} (Score: {context.continue_score}, Turns: {context.turn_count})")
    
    async def _cleanup_simulation(self):
        """Clean up simulation state"""
        
        # End all active conversations
        for conv_id in list(self.state.active_conversations.keys()):
            await self._end_simulation_conversation(conv_id, "simulation_ended")
        
        logging.info("Simulation cleanup completed")
    
    async def _print_simulation_summary(self):
        """Print summary of simulation results"""
        
        logging.info("=== SIMULATION SUMMARY ===")
        
        # Get all personas and their current states
        personas = await self.db.list_personas()
        
        for persona in personas:
            state = persona.interaction_state
            memory_stats = await self.memory.get_memory_stats(persona.id)
            
            logging.info(f"{persona.name}:")
            logging.info(f"  Social Energy: {state.social_energy}/200")
            logging.info(f"  Interaction Fatigue: {state.interaction_fatigue}")
            logging.info(f"  Available Time: {state.available_time}s")
            logging.info(f"  Memories: {memory_stats.get('total_memories', 0)}")
        
        logging.info("========================")


async def run_chatroom_simulation(duration_minutes: int = 5):
    """Convenience function to run a standalone simulation"""
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Initialize components
    db_manager = SQLiteManager("data/simulation.db")
    memory_manager = VectorMemoryManager("data/simulation_memory")
    llm_manager = LLMManager()
    
    await db_manager.initialize()
    await llm_manager.initialize()
    
    conversation_engine = ConversationEngine(db_manager, memory_manager, llm_manager)
    
    # Create simulation
    simulation = ChatroomSimulation(
        db_manager, memory_manager, llm_manager, conversation_engine
    )
    
    try:
        await simulation.run_simulation(duration_minutes)
    finally:
        await llm_manager.close()
        await memory_manager.close()


if __name__ == "__main__":
    # Run simulation when called directly
    asyncio.run(run_chatroom_simulation(5))