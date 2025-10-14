"""
Relationship Management System

Handles CRUD operations for relationships, emotional states, and compatibility scoring.
Integrates with both SQLite (structured data) and ChromaDB (vector embeddings).
"""

from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
import json
import asyncio

from ..models import Relationship, EmotionalState, RelationshipType
from ..persistence import SQLiteManager, VectorMemoryManager
from ..logging import get_logger


class RelationshipManager:
    """Manages relationships and emotional states between personas"""
    
    def __init__(self, db_session, sqlite_manager: Optional[SQLiteManager] = None, 
                 vector_manager: Optional[VectorMemoryManager] = None):
        self.db_session = db_session
        self.sqlite = sqlite_manager
        self.vector = vector_manager
        self.logger = get_logger(__name__)
    
    # === Relationship CRUD Operations ===
    
    async def get_relationship(self, persona1_id: str, persona2_id: str) -> Optional[Relationship]:
        """Get relationship between two personas (order independent)"""
        try:
            # Check both directions since relationships are bidirectional
            query = """
                SELECT * FROM relationships 
                WHERE (persona1_id = ? AND persona2_id = ?) 
                   OR (persona1_id = ? AND persona2_id = ?)
            """
            
            row = await self.db_session.fetchone(query, [persona1_id, persona2_id, persona2_id, persona1_id])
            
            if row:
                return self._row_to_relationship(row)
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting relationship: {e}")
            return None
    
    async def save_relationship(self, relationship: Relationship) -> bool:
        """Save or update a relationship"""
        try:
            # Check if relationship exists
            existing = await self.get_relationship(relationship.persona1_id, relationship.persona2_id)
            
            if existing:
                # Update existing relationship
                query = """
                    UPDATE relationships SET 
                        affinity = ?, trust = ?, respect = ?, intimacy = ?,
                        relationship_type = ?, interaction_count = ?, 
                        total_interaction_time = ?, last_interaction = ?, updated_at = ?
                    WHERE (persona1_id = ? AND persona2_id = ?) 
                       OR (persona1_id = ? AND persona2_id = ?)
                """
                params = [
                    relationship.affinity, relationship.trust, relationship.respect, 
                    relationship.intimacy, relationship.relationship_type.value,
                    relationship.interaction_count, relationship.total_interaction_time,
                    relationship.last_interaction.isoformat() if relationship.last_interaction else None,
                    datetime.now().isoformat(),
                    relationship.persona1_id, relationship.persona2_id,
                    relationship.persona2_id, relationship.persona1_id
                ]
            else:
                # Create new relationship
                query = """
                    INSERT INTO relationships 
                    (id, persona1_id, persona2_id, affinity, trust, respect, intimacy,
                     relationship_type, interaction_count, total_interaction_time, 
                     first_meeting, last_interaction, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """
                params = [
                    relationship.id,  # Include the relationship ID
                    relationship.persona1_id, relationship.persona2_id,
                    relationship.affinity, relationship.trust, relationship.respect,
                    relationship.intimacy, relationship.relationship_type.value,
                    relationship.interaction_count, relationship.total_interaction_time,
                    relationship.first_meeting.isoformat(),
                    relationship.last_interaction.isoformat() if relationship.last_interaction else None,
                    datetime.now().isoformat(), datetime.now().isoformat()
                ]
            
            await self.db_session.execute(query, params)
            await self.db_session.commit()
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving relationship: {e}")
            return False
    
    async def get_persona_relationships(self, persona_id: str) -> List[Relationship]:
        """Get all relationships for a specific persona"""
        try:
            query = """
                SELECT * FROM relationships 
                WHERE persona1_id = ? OR persona2_id = ?
            """
            
            rows = await self.db_session.fetchall(query, [persona_id, persona_id])
            
            relationships = []
            for row in rows:
                rel = self._row_to_relationship(row)
                if rel:
                    relationships.append(rel)
            
            return relationships
            
        except Exception as e:
            self.logger.error(f"Error getting persona relationships: {e}")
            return []
    
    # === Emotional State Management ===
    
    async def get_emotional_state(self, persona_id: str) -> EmotionalState:
        """Get emotional state for a persona (creates default if not exists)"""
        try:
            query = "SELECT * FROM emotional_states WHERE persona_id = ?"
            row = await self.db_session.fetchone(query, [persona_id])
            
            if row:
                return self._row_to_emotional_state(row)
            else:
                # Create default emotional state
                default_state = EmotionalState(
                    persona_id=persona_id,
                    mood=0.5,
                    energy_level=0.7,
                    stress_level=0.3,
                    curiosity=0.6,
                    social_battery=0.8,
                    last_updated=datetime.now()
                )
                
                # Save to database
                await self._save_emotional_state(default_state)
                return default_state
                
        except Exception as e:
            self.logger.error(f"Error getting emotional state: {e}")
            # Return default state on error
            return EmotionalState(
                persona_id=persona_id,
                mood=0.5,
                energy_level=0.7,
                stress_level=0.3,
                curiosity=0.6,
                social_battery=0.8,
                last_updated=datetime.now()
            )
    
    async def update_emotional_state(self, emotional_state: EmotionalState) -> bool:
        """Update emotional state in database"""
        try:
            return await self._save_emotional_state(emotional_state)
        except Exception as e:
            self.logger.error(f"Error updating emotional state: {e}")
            return False
    
    async def _save_emotional_state(self, state: EmotionalState) -> bool:
        """Internal method to save emotional state"""
        try:
            # Check if exists (using persona_id as primary key)
            query = "SELECT persona_id FROM emotional_states WHERE persona_id = ?"
            existing = await self.db_session.fetchone(query, [state.persona_id])
            
            if existing:
                # Update
                query = """
                    UPDATE emotional_states SET 
                        mood = ?, energy_level = ?, stress_level = ?, 
                        curiosity = ?, social_battery = ?, last_updated = ?
                    WHERE persona_id = ?
                """
                params = [
                    state.mood, state.energy_level, state.stress_level,
                    state.curiosity, state.social_battery, 
                    state.last_updated.isoformat(), state.persona_id
                ]
            else:
                # Insert
                query = """
                    INSERT INTO emotional_states 
                    (persona_id, mood, energy_level, stress_level, curiosity, 
                     social_battery, last_updated, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """
                params = [
                    state.persona_id, state.mood, state.energy_level, 
                    state.stress_level, state.curiosity, state.social_battery,
                    state.last_updated.isoformat(), datetime.now().isoformat()
                ]
            
            await self.db_session.execute(query, params)
            await self.db_session.commit()
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving emotional state: {e}")
            return False
    
    # === Interaction Processing ===
    
    async def process_interaction(self, persona1_id: str, persona2_id: str, 
                                interaction_quality: float, duration_minutes: float = 5.0,
                                context: str = "conversation") -> bool:
        """Process an interaction between two personas and update their relationship"""
        try:
            # Clamp interaction quality to valid range
            interaction_quality = max(-1.0, min(1.0, interaction_quality))
            
            # Validate that both personas exist
            persona1_exists = await self._persona_exists(persona1_id)
            persona2_exists = await self._persona_exists(persona2_id)
            
            if not persona1_exists or not persona2_exists:
                self.logger.warning(f"Attempted to process interaction between nonexistent personas: {persona1_id}, {persona2_id}")
                return False
            
            # Get or create relationship
            relationship = await self.get_relationship(persona1_id, persona2_id)
            
            if not relationship:
                # Create new relationship
                relationship = Relationship(
                    persona1_id=persona1_id,
                    persona2_id=persona2_id,
                    affinity=0.5,
                    trust=0.5, 
                    respect=0.5,
                    intimacy=0.5,
                    relationship_type=RelationshipType.STRANGER,
                    interaction_count=0,
                    total_interaction_time=0.0,
                    first_meeting=datetime.now(),
                    last_interaction=None
                )
            
            # Update relationship based on interaction
            self._update_relationship_scores(relationship, interaction_quality, duration_minutes, context)
            
            # Update interaction metadata
            relationship.interaction_count += 1
            relationship.total_interaction_time += duration_minutes
            relationship.last_interaction = datetime.now()
            
            # Update relationship type based on scores
            relationship.relationship_type = self._determine_relationship_type(relationship)
            
            # Save updated relationship
            success = await self.save_relationship(relationship)
            
            if success:
                # Log interaction for future analysis
                await self._log_interaction(persona1_id, persona2_id, interaction_quality, 
                                          duration_minutes, context)
                
                # Store interaction embedding in ChromaDB if available
                if self.vector:
                    await self._store_interaction_embedding(persona1_id, persona2_id, 
                                                          interaction_quality, context)
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error processing interaction: {e}")
            return False
    
    def _update_relationship_scores(self, relationship: Relationship, 
                                  interaction_quality: float, duration: float, context: str):
        """Update relationship scores based on interaction"""
        
        # Base impact from interaction quality
        base_impact = interaction_quality * 0.1
        
        # Duration factor (longer interactions have more impact)
        duration_factor = min(1.0, duration / 30.0)  # Cap at 30 minutes
        
        # Context-specific modifiers
        context_modifiers = {
            "conflict": {"trust": -0.2, "affinity": -0.1},
            "collaboration": {"trust": 0.1, "respect": 0.1},
            "casual": {"affinity": 0.1},
            "deep_conversation": {"intimacy": 0.1, "trust": 0.05},
            "professional": {"respect": 0.1}
        }
        
        modifier = context_modifiers.get(context, {})
        
        # Update scores
        relationship.affinity += base_impact * duration_factor + modifier.get("affinity", 0)
        relationship.trust += (base_impact * 0.8) * duration_factor + modifier.get("trust", 0)
        relationship.respect += (base_impact * 0.9) * duration_factor + modifier.get("respect", 0)
        relationship.intimacy += (base_impact * 0.7) * duration_factor + modifier.get("intimacy", 0)
        
        # Clamp values to [0, 1] range
        relationship.affinity = max(0.0, min(1.0, relationship.affinity))
        relationship.trust = max(0.0, min(1.0, relationship.trust))
        relationship.respect = max(0.0, min(1.0, relationship.respect))
        relationship.intimacy = max(0.0, min(1.0, relationship.intimacy))
    
    def _determine_relationship_type(self, relationship: Relationship) -> RelationshipType:
        """Determine relationship type based on scores and interaction count"""
        
        avg_score = (relationship.affinity + relationship.trust + 
                    relationship.respect + relationship.intimacy) / 4
        
        if relationship.interaction_count < 3:
            return RelationshipType.STRANGER
        elif avg_score < 0.3:
            return RelationshipType.ENEMY if relationship.affinity < 0.2 else RelationshipType.RIVAL
        elif avg_score < 0.5:
            return RelationshipType.ACQUAINTANCE
        elif avg_score < 0.7:
            return RelationshipType.FRIEND
        else:
            if relationship.intimacy > 0.8:
                return RelationshipType.ROMANTIC
            elif relationship.respect > 0.8 and relationship.interaction_count > 10:
                return RelationshipType.MENTOR
            else:
                return RelationshipType.CLOSE_FRIEND
    
    async def _log_interaction(self, persona1_id: str, persona2_id: str, 
                             quality: float, duration: float, context: str):
        """Log interaction to history table"""
        try:
            query = """
                INSERT INTO interaction_history 
                (persona1_id, persona2_id, interaction_quality, duration_minutes, 
                 context, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            """
            params = [persona1_id, persona2_id, quality, duration, context, 
                     datetime.now().isoformat()]
            
            await self.db_session.execute(query, params)
            await self.db_session.commit()
            
        except Exception as e:
            self.logger.error(f"Error logging interaction: {e}")
    
    async def _store_interaction_embedding(self, persona1_id: str, persona2_id: str,
                                         quality: float, context: str):
        """Store interaction embedding in ChromaDB for semantic search"""
        try:
            if not self.vector:
                return
            
            # Create interaction document
            interaction_text = f"Interaction between {persona1_id} and {persona2_id}: {context} (quality: {quality:.2f})"
            
            # Store in ChromaDB (this would need to be implemented based on your vector manager)
            # await self.vector.store_interaction(interaction_text, {
            #     "persona1_id": persona1_id,
            #     "persona2_id": persona2_id,
            #     "quality": quality,
            #     "context": context,
            #     "timestamp": datetime.now().isoformat()
            # })
            
        except Exception as e:
            self.logger.error(f"Error storing interaction embedding: {e}")
    
    # === Statistics and Analytics ===
    
    async def get_relationship_stats(self) -> Dict[str, Any]:
        """Get comprehensive relationship statistics"""
        try:
            stats = {}
            
            # Total relationships
            query = "SELECT COUNT(*) as count FROM relationships"
            row = await self.db_session.fetchone(query)
            stats["total_relationships"] = row[0] if row else 0
            
            # Relationship type distribution
            query = "SELECT relationship_type, COUNT(*) as count FROM relationships GROUP BY relationship_type"
            rows = await self.db_session.fetchall(query)
            stats["relationship_types"] = {row[0]: row[1] for row in rows}
            
            # Average compatibility (based on scores)
            query = """
                SELECT AVG((affinity + trust + respect + intimacy) / 4.0) as avg_compat 
                FROM relationships
            """
            row = await self.db_session.fetchone(query)
            stats["average_compatibility"] = round(row[0], 3) if row and row[0] else 0.0
            
            # Total interactions
            query = "SELECT COUNT(*) as count FROM interaction_history"
            row = await self.db_session.fetchone(query)
            stats["total_interactions"] = row[0] if row else 0
            
            # Most active personas
            query = """
                SELECT persona1_id as persona_id, COUNT(*) as count 
                FROM interaction_history 
                GROUP BY persona1_id 
                ORDER BY count DESC 
                LIMIT 5
            """
            rows = await self.db_session.fetchall(query)
            stats["most_active_personas"] = [{"persona_id": row[0], "interactions": row[1]} for row in rows]
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Error getting relationship stats: {e}")
            return {
                "total_relationships": 0,
                "relationship_types": {},
                "average_compatibility": 0.0,
                "total_interactions": 0,
                "most_active_personas": []
            }
    
    # === Helper Methods ===
    
    def _row_to_relationship(self, row) -> Optional[Relationship]:
        """Convert database row to Relationship model"""
        try:
            # Actual database column order:
            # 0: persona1_id, 1: persona2_id, 2: affinity, 3: trust, 4: respect, 
            # 5: interaction_count, 6: last_interaction, 7: shared_experiences, 8: relationship_type,
            # 9: intimacy, 10: total_interaction_time, 11: first_meeting, 12: created_at, 13: updated_at, 14: id
            return Relationship(
                id=row[14],          # id from database (column 14)
                persona1_id=row[0],  # persona1_id
                persona2_id=row[1],  # persona2_id  
                affinity=row[2],     # affinity
                trust=row[3],        # trust
                respect=row[4],      # respect
                intimacy=row[9],     # intimacy (column 9)
                relationship_type=RelationshipType(row[8]),  # relationship_type (column 8)
                interaction_count=row[5],    # interaction_count (column 5)
                total_interaction_time=row[10] if row[10] is not None else 0.0,  # total_interaction_time (column 10)
                first_meeting=datetime.fromisoformat(row[11]) if row[11] else datetime.now(),    # first_meeting (column 11)
                last_interaction=datetime.fromisoformat(row[6]) if row[6] else None  # last_interaction (column 6)
            )
        except Exception as e:
            self.logger.error(f"Error converting row to relationship: {e}")
            return None
    
    def _row_to_emotional_state(self, row) -> Optional[EmotionalState]:
        """Convert database row to EmotionalState model"""
        try:
            return EmotionalState(
                persona_id=row[0],  # persona_id is column 0
                mood=row[1],        # mood is column 1
                energy_level=row[2], # energy_level is column 2
                stress_level=row[3], # stress_level is column 3
                curiosity=row[4],    # curiosity is column 4
                social_battery=row[5], # social_battery is column 5
                last_updated=datetime.fromisoformat(row[6]) if row[6] else datetime.now()  # last_updated is column 6
            )
        except Exception as e:
            self.logger.error(f"Error converting row to emotional state: {e}")
            return None
    
    async def _persona_exists(self, persona_id: str) -> bool:
        """Check if a persona exists in the database"""
        try:
            query = "SELECT COUNT(*) FROM personas WHERE id = ?"
            row = await self.db_session.fetchone(query, (persona_id,))
            return row[0] > 0 if row else False
        except Exception as e:
            self.logger.error(f"Error checking persona existence: {e}")
            return False