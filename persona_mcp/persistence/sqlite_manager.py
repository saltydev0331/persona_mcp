"""
SQLite database management for persona state persistence
"""

import sqlite3
import json
from typing import List, Optional, Dict, Any
from datetime import datetime
from pathlib import Path
import aiosqlite

from ..models import Persona, PersonaInteractionState, Relationship, Memory, ConversationContext, ConversationTurn


class SQLiteManager:
    """Manages SQLite database for persona state and conversation history"""

    def __init__(self, db_path: str = "data/personas.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    async def initialize(self):
        """Initialize database with required tables"""
        async with aiosqlite.connect(self.db_path) as db:
            await self._create_tables(db)

    async def _create_tables(self, db: aiosqlite.Connection):
        """Create all required tables"""
        
        # Personas table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS personas (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                personality_traits TEXT,  -- JSON
                topic_preferences TEXT,   -- JSON
                charisma INTEGER DEFAULT 10,
                intelligence INTEGER DEFAULT 10,
                social_rank TEXT DEFAULT 'commoner',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Persona interaction states
        await db.execute("""
            CREATE TABLE IF NOT EXISTS persona_interaction_states (
                persona_id TEXT PRIMARY KEY,
                interest_level INTEGER DEFAULT 50,
                interaction_fatigue INTEGER DEFAULT 0,
                current_priority TEXT DEFAULT 'none',
                available_time INTEGER DEFAULT 300,
                social_energy INTEGER DEFAULT 100,
                cooldown_until REAL DEFAULT 0,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (persona_id) REFERENCES personas (id)
            )
        """)

        # Relationships table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS relationships (
                persona1_id TEXT,
                persona2_id TEXT,
                affinity REAL DEFAULT 0.0,
                trust REAL DEFAULT 0.0,
                respect REAL DEFAULT 0.0,
                interaction_count INTEGER DEFAULT 0,
                last_interaction TIMESTAMP,
                shared_experiences TEXT,  -- JSON array
                relationship_type TEXT DEFAULT 'stranger',
                PRIMARY KEY (persona1_id, persona2_id),
                FOREIGN KEY (persona1_id) REFERENCES personas (id),
                FOREIGN KEY (persona2_id) REFERENCES personas (id)
            )
        """)

        # Conversations table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                participants TEXT,        -- JSON array of persona IDs
                topic TEXT DEFAULT 'general',
                topic_drift_count INTEGER DEFAULT 0,
                duration INTEGER DEFAULT 0,
                token_budget INTEGER DEFAULT 1000,
                tokens_used INTEGER DEFAULT 0,
                continue_score INTEGER DEFAULT 50,
                score_history TEXT,       -- JSON array
                turn_count INTEGER DEFAULT 0,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ended_at TIMESTAMP,
                exit_reason TEXT
            )
        """)

        # Conversation turns table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS conversation_turns (
                id TEXT PRIMARY KEY,
                conversation_id TEXT,
                speaker_id TEXT,
                turn_number INTEGER,
                content TEXT,
                response_type TEXT DEFAULT 'full_llm',
                continue_score INTEGER,
                tokens_used INTEGER DEFAULT 0,
                processing_time REAL DEFAULT 0.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (conversation_id) REFERENCES conversations (id),
                FOREIGN KEY (speaker_id) REFERENCES personas (id)
            )
        """)

        # Memories metadata table (actual content stored in ChromaDB)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id TEXT PRIMARY KEY,
                persona_id TEXT,
                memory_type TEXT DEFAULT 'conversation',
                importance REAL DEFAULT 0.5,
                emotional_valence REAL DEFAULT 0.0,
                related_personas TEXT,    -- JSON array
                metadata TEXT,            -- JSON
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                accessed_count INTEGER DEFAULT 0,
                last_accessed TIMESTAMP,
                FOREIGN KEY (persona_id) REFERENCES personas (id)
            )
        """)

        await db.commit()

    # Persona CRUD operations
    async def save_persona(self, persona: Persona) -> bool:
        """Save or update a persona"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT OR REPLACE INTO personas 
                    (id, name, description, personality_traits, topic_preferences, 
                     charisma, intelligence, social_rank, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    persona.id,
                    persona.name,
                    persona.description,
                    json.dumps(persona.personality_traits),
                    json.dumps(persona.topic_preferences),
                    persona.charisma,
                    persona.intelligence,
                    persona.social_rank,
                    persona.created_at.isoformat()
                ))

                # Save interaction state
                state = persona.interaction_state
                await db.execute("""
                    INSERT OR REPLACE INTO persona_interaction_states
                    (persona_id, interest_level, interaction_fatigue, current_priority,
                     available_time, social_energy, cooldown_until, last_updated)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    state.persona_id,
                    state.interest_level,
                    state.interaction_fatigue,
                    state.current_priority.value,
                    state.available_time,
                    state.social_energy,
                    state.cooldown_until,
                    state.last_updated.isoformat()
                ))

                await db.commit()
                return True
        except Exception as e:
            print(f"Error saving persona {persona.id}: {e}")
            return False

    async def load_persona(self, persona_id: str) -> Optional[Persona]:
        """Load a persona by ID"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # Load basic persona data
                async with db.execute("""
                    SELECT id, name, description, personality_traits, topic_preferences,
                           charisma, intelligence, social_rank, created_at
                    FROM personas WHERE id = ?
                """, (persona_id,)) as cursor:
                    row = await cursor.fetchone()
                    if not row:
                        return None

                # Load interaction state
                async with db.execute("""
                    SELECT interest_level, interaction_fatigue, current_priority,
                           available_time, social_energy, cooldown_until, last_updated
                    FROM persona_interaction_states WHERE persona_id = ?
                """, (persona_id,)) as cursor:
                    state_row = await cursor.fetchone()

                # Construct persona
                persona_data = {
                    "id": row[0],
                    "name": row[1],
                    "description": row[2],
                    "personality_traits": json.loads(row[3]) if row[3] else {},
                    "topic_preferences": json.loads(row[4]) if row[4] else {},
                    "charisma": row[5],
                    "intelligence": row[6],
                    "social_rank": row[7],
                    "created_at": datetime.fromisoformat(row[8])
                }

                persona = Persona(**persona_data)

                if state_row:
                    persona.interaction_state = PersonaInteractionState(
                        persona_id=persona_id,
                        interest_level=state_row[0],
                        interaction_fatigue=state_row[1],
                        current_priority=state_row[2],
                        available_time=state_row[3],
                        social_energy=state_row[4],
                        cooldown_until=state_row[5],
                        last_updated=datetime.fromisoformat(state_row[6])
                    )

                return persona

        except Exception as e:
            print(f"Error loading persona {persona_id}: {e}")
            return None

    async def list_personas(self) -> List[Persona]:
        """Get all personas"""
        personas = []
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute("SELECT id FROM personas") as cursor:
                    rows = await cursor.fetchall()
                    for row in rows:
                        persona = await self.load_persona(row[0])
                        if persona:
                            personas.append(persona)
        except Exception as e:
            print(f"Error listing personas: {e}")
        
        return personas

    # Relationship operations
    async def save_relationship(self, relationship: Relationship) -> bool:
        """Save or update a relationship"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT OR REPLACE INTO relationships
                    (persona1_id, persona2_id, affinity, trust, respect,
                     interaction_count, last_interaction, shared_experiences, relationship_type)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    relationship.persona1_id,
                    relationship.persona2_id,
                    relationship.affinity,
                    relationship.trust,
                    relationship.respect,
                    relationship.interaction_count,
                    relationship.last_interaction.isoformat() if relationship.last_interaction else None,
                    json.dumps(relationship.shared_experiences),
                    relationship.relationship_type
                ))
                await db.commit()
                return True
        except Exception as e:
            print(f"Error saving relationship: {e}")
            return False

    async def load_relationship(self, persona1_id: str, persona2_id: str) -> Optional[Relationship]:
        """Load relationship between two personas"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute("""
                    SELECT * FROM relationships 
                    WHERE (persona1_id = ? AND persona2_id = ?)
                       OR (persona1_id = ? AND persona2_id = ?)
                """, (persona1_id, persona2_id, persona2_id, persona1_id)) as cursor:
                    row = await cursor.fetchone()
                    if row:
                        return Relationship(
                            persona1_id=row[0],
                            persona2_id=row[1],
                            affinity=row[2],
                            trust=row[3],
                            respect=row[4],
                            interaction_count=row[5],
                            last_interaction=datetime.fromisoformat(row[6]) if row[6] else None,
                            shared_experiences=json.loads(row[7]) if row[7] else [],
                            relationship_type=row[8]
                        )
        except Exception as e:
            print(f"Error loading relationship: {e}")
        
        return None

    # Conversation operations
    async def save_conversation(self, conversation: ConversationContext) -> bool:
        """Save conversation context"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT OR REPLACE INTO conversations
                    (id, participants, topic, topic_drift_count, duration,
                     token_budget, tokens_used, continue_score, score_history,
                     turn_count, started_at, ended_at, exit_reason)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    conversation.id,
                    json.dumps(conversation.participants),
                    conversation.topic,
                    conversation.topic_drift_count,
                    conversation.duration,
                    conversation.token_budget,
                    conversation.tokens_used,
                    conversation.continue_score,
                    json.dumps(conversation.score_history),
                    conversation.turn_count,
                    conversation.started_at.isoformat(),
                    conversation.ended_at.isoformat() if conversation.ended_at else None,
                    conversation.exit_reason
                ))
                await db.commit()
                return True
        except Exception as e:
            print(f"Error saving conversation: {e}")
            return False

    async def save_conversation_turn(self, turn: ConversationTurn) -> bool:
        """Save individual conversation turn"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT INTO conversation_turns
                    (id, conversation_id, speaker_id, turn_number, content,
                     response_type, continue_score, tokens_used, processing_time, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    turn.id,
                    turn.conversation_id,
                    turn.speaker_id,
                    turn.turn_number,
                    turn.content,
                    turn.response_type,
                    turn.continue_score,
                    turn.tokens_used,
                    turn.processing_time,
                    turn.created_at.isoformat()
                ))
                await db.commit()
                return True
        except Exception as e:
            print(f"Error saving conversation turn: {e}")
            return False
    
    # Additional relationship methods for MCP handlers
    async def get_persona_relationship(self, persona1_id: str, persona2_id: str):
        """Get relationship between two personas (alias for load_relationship)"""
        return await self.load_relationship(persona1_id, persona2_id)
    
    async def get_persona_relationships(self, persona_id: str):
        """Get all relationships for a persona"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute("""
                    SELECT * FROM relationships 
                    WHERE persona1_id = ? OR persona2_id = ?
                """, (persona_id, persona_id)) as cursor:
                    rows = await cursor.fetchall()
                    relationships = []
                    for row in rows:
                        relationships.append(Relationship(
                            persona1_id=row[0],
                            persona2_id=row[1],
                            affinity=row[2],
                            trust=row[3],
                            respect=row[4],
                            interaction_count=row[5],
                            last_interaction=datetime.fromisoformat(row[6]) if row[6] else None,
                            shared_experiences=json.loads(row[7]) if row[7] else [],
                            relationship_type=row[8]
                        ))
                    return relationships
        except Exception as e:
            print(f"Error loading relationships for {persona_id}: {e}")
            return []