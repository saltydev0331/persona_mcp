#!/usr/bin/env python3
"""
Comprehensive Relationship Dynamics Simulation

Demonstrates how personas develop complex relationships through various interactions:
- Multiple personas with different personalities
- Various interaction types and contexts
- Relationship evolution over time
- Emotional state changes
- Compatibility analysis and predictions
"""

import asyncio
import random
from datetime import datetime, timedelta
from typing import List, Dict, Tuple
from dataclasses import dataclass

from persona_mcp.models import Persona, Relationship, RelationshipType, EmotionalState
from persona_mcp.relationships.manager import RelationshipManager
from persona_mcp.relationships.compatibility import CompatibilityEngine


@dataclass
class SimulationEvent:
    """Represents an interaction event in the simulation"""
    persona1_id: str
    persona2_id: str
    interaction_type: str
    quality: float
    duration: float
    context: str
    description: str


class RelationshipSimulation:
    """Comprehensive relationship simulation system"""
    
    def __init__(self):
        # Mock database session for simulation
        self.db_session = MockDatabaseSession()
        self.relationship_manager = RelationshipManager(self.db_session)
        self.compatibility_engine = CompatibilityEngine()
        
        # Simulation state
        self.personas = {}
        self.relationships = {}
        self.emotional_states = {}
        self.interaction_history = []
        
    def create_personas(self) -> List[Persona]:
        """Create diverse personas for the simulation"""
        
        personas_data = [
            {
                "id": "alice_dev", "name": "Alice",
                "description": "Enthusiastic software developer with collaborative spirit",
                "personality_traits": {
                    "traits": ["curious", "collaborative", "patient", "detail-oriented"],
                    "interests": ["programming", "open-source", "teaching", "coffee"],
                    "background": "Alice is a passionate full-stack developer who loves pair programming and mentoring junior developers. She thrives in collaborative environments.",
                    "openness": 0.8, "conscientiousness": 0.7, "extraversion": 0.7,
                    "agreeableness": 0.9, "neuroticism": 0.3
                }
            },
            {
                "id": "bob_analyst", "name": "Bob", 
                "description": "Methodical data analyst who values precision",
                "personality_traits": {
                    "traits": ["analytical", "methodical", "perfectionist", "quiet"],
                    "interests": ["data-science", "statistics", "chess", "classical-music"],
                    "background": "Bob is a senior data analyst with a systematic approach to problem-solving. He prefers structure and evidence-based decisions.",
                    "openness": 0.6, "conscientiousness": 0.9, "extraversion": 0.4,
                    "agreeableness": 0.7, "neuroticism": 0.2
                }
            },
            {
                "id": "charlie_creative", "name": "Charlie",
                "description": "Creative designer with spontaneous energy", 
                "personality_traits": {
                    "traits": ["creative", "spontaneous", "passionate", "expressive"],
                    "interests": ["design", "art", "music", "travel", "photography"],
                    "background": "Charlie is a UX designer who brings innovative ideas and creative solutions. They think outside the box and love brainstorming sessions.",
                    "openness": 0.95, "conscientiousness": 0.4, "extraversion": 0.8,
                    "agreeableness": 0.6, "neuroticism": 0.6
                }
            },
            {
                "id": "diana_leader", "name": "Diana",
                "description": "Natural leader with strong organizational skills",
                "personality_traits": {
                    "traits": ["organized", "diplomatic", "decisive", "supportive"],
                    "interests": ["management", "psychology", "fitness", "reading"],
                    "background": "Diana is a project manager who excels at coordinating teams and managing complex projects. She's diplomatic but decisive.",
                    "openness": 0.7, "conscientiousness": 0.8, "extraversion": 0.6,
                    "agreeableness": 0.8, "neuroticism": 0.3
                }
            },
            {
                "id": "evan_competitive", "name": "Evan",
                "description": "Competitive sales professional with high energy",
                "personality_traits": {
                    "traits": ["competitive", "charismatic", "intense", "goal-oriented"],
                    "interests": ["sales", "sports", "networking", "business"],
                    "background": "Evan is a sales manager who thrives on competition and achieving targets. He's charismatic but can be intense in his approach.",
                    "openness": 0.5, "conscientiousness": 0.7, "extraversion": 0.9,
                    "agreeableness": 0.4, "neuroticism": 0.5
                }
            }
        ]
        
        personas = []
        for data in personas_data:
            persona = Persona(**data)
            personas.append(persona)
            self.personas[persona.id] = persona
            
            # Initialize emotional state
            self.emotional_states[persona.id] = EmotionalState(
                persona_id=persona.id,
                mood=0.6 + random.uniform(-0.1, 0.1),
                energy_level=0.7 + random.uniform(-0.1, 0.1),
                stress_level=0.3 + random.uniform(-0.1, 0.1),
                curiosity=0.6 + random.uniform(-0.1, 0.1),
                social_battery=0.8 + random.uniform(-0.1, 0.1),
                last_updated=datetime.now()
            )
        
        return personas
    
    def generate_interaction_scenarios(self) -> List[SimulationEvent]:
        """Generate realistic interaction scenarios between personas"""
        
        scenarios = [
            # Alice & Bob - Technical collaboration
            SimulationEvent("alice_dev", "bob_analyst", "collaboration", 0.7, 45.0, "professional",
                          "Alice and Bob work together on data visualization for the new analytics dashboard"),
            
            SimulationEvent("alice_dev", "bob_analyst", "collaboration", 0.8, 30.0, "professional", 
                          "Bob helps Alice optimize database queries for better performance"),
            
            # Alice & Charlie - Creative brainstorming  
            SimulationEvent("alice_dev", "charlie_creative", "brainstorming", 0.6, 25.0, "casual",
                          "Alice and Charlie brainstorm user interface improvements over coffee"),
            
            SimulationEvent("alice_dev", "charlie_creative", "brainstorming", 0.4, 15.0, "casual",
                          "Creative differences emerge during design review - Alice wants structure, Charlie wants freedom"),
            
            # Alice & Diana - Mentoring relationship
            SimulationEvent("alice_dev", "diana_leader", "mentoring", 0.8, 35.0, "professional",
                          "Diana seeks Alice's technical advice for project planning"),
            
            SimulationEvent("diana_leader", "alice_dev", "mentoring", 0.9, 40.0, "professional",
                          "Diana mentors Alice on career development and leadership skills"),
            
            # Bob & Charlie - Personality clash
            SimulationEvent("bob_analyst", "charlie_creative", "meeting", 0.2, 20.0, "conflict",
                          "Bob and Charlie clash over project timelines - Bob wants detailed plans, Charlie prefers flexibility"),
            
            SimulationEvent("bob_analyst", "charlie_creative", "meeting", 0.1, 10.0, "conflict",
                          "Heated disagreement about data presentation - Charlie's creative approach conflicts with Bob's precision"),
            
            # Diana & Evan - Professional rivalry
            SimulationEvent("diana_leader", "evan_competitive", "negotiation", 0.3, 30.0, "professional",
                          "Diana and Evan compete for the same promotion, tension during budget meeting"),
            
            SimulationEvent("evan_competitive", "diana_leader", "negotiation", 0.4, 25.0, "professional",
                          "Evan tries to prove his leadership worth, creates friction with Diana's established authority"),
            
            # Alice & Evan - Surprising connection
            SimulationEvent("alice_dev", "evan_competitive", "casual", 0.7, 20.0, "casual",
                          "Alice and Evan discover shared interest in technology trends during lunch"),
            
            # Bob & Diana - Mutual respect
            SimulationEvent("bob_analyst", "diana_leader", "collaboration", 0.8, 35.0, "professional",
                          "Bob's analytical skills complement Diana's project management - successful quarterly report"),
            
            SimulationEvent("diana_leader", "bob_analyst", "collaboration", 0.9, 40.0, "professional",
                          "Diana appreciates Bob's thoroughness, invites him to strategic planning sessions"),
            
            # Charlie & Evan - Unexpected friendship
            SimulationEvent("charlie_creative", "evan_competitive", "social", 0.8, 60.0, "casual",
                          "Charlie and Evan bond over shared love of extreme sports and adventure travel"),
            
            SimulationEvent("evan_competitive", "charlie_creative", "social", 0.9, 45.0, "casual",
                          "Evan and Charlie plan weekend rock climbing trip, discover mutual respect"),
            
            # Follow-up interactions showing relationship evolution
            SimulationEvent("alice_dev", "bob_analyst", "deep_conversation", 0.9, 50.0, "deep_conversation",
                          "Alice and Bob have deep conversation about career goals and work-life balance"),
            
            SimulationEvent("diana_leader", "alice_dev", "mentoring", 0.9, 45.0, "professional",
                          "Diana officially becomes Alice's mentor, discussing long-term career strategy"),
            
            SimulationEvent("charlie_creative", "bob_analyst", "collaboration", 0.6, 30.0, "professional",
                          "Charlie and Bob attempt to work together again, finding middle ground"),
        ]
        
        return scenarios
    
    async def run_simulation(self):
        """Run the comprehensive relationship simulation"""
        
        print("🎭 Starting Comprehensive Relationship Dynamics Simulation")
        print("=" * 60)
        
        # 1. Create personas and analyze initial compatibility
        print("\n📋 PHASE 1: Persona Creation & Initial Compatibility Analysis")
        personas = self.create_personas()
        
        for persona in personas:
            print(f"\n👤 {persona.name} ({persona.id})")
            print(f"   {persona.description}")
            traits = persona.personality_traits.get('traits', [])
            interests = persona.personality_traits.get('interests', [])
            print(f"   Traits: {', '.join(traits)}")
            print(f"   Interests: {', '.join(interests)}")
            
        # Calculate initial compatibility matrix
        print(f"\n🧮 Initial Compatibility Matrix:")
        compatibility_matrix = {}
        
        for i, p1 in enumerate(personas):
            for j, p2 in enumerate(personas):
                if i < j:  # Avoid duplicate pairs
                    compat = self.compatibility_engine.calculate_overall_compatibility(p1, p2, None)
                    compatibility_matrix[(p1.id, p2.id)] = compat['overall']
                    print(f"   {p1.name} ↔ {p2.name}: {compat['overall']:.2f} "
                          f"(personality: {compat['personality']:.2f}, "
                          f"interests: {compat['interests']:.2f}, "
                          f"social: {compat['social']:.2f})")
        
        # 2. Run interaction scenarios
        print(f"\n🎬 PHASE 2: Interaction Scenarios")
        scenarios = self.generate_interaction_scenarios()
        
        for i, event in enumerate(scenarios):
            print(f"\n--- Interaction {i+1}: {event.interaction_type.title()} ---")
            print(f"👥 {self.personas[event.persona1_id].name} & {self.personas[event.persona2_id].name}")
            print(f"📝 {event.description}")
            print(f"⚡ Quality: {event.quality:+.1f}, Duration: {event.duration}min, Context: {event.context}")
            
            # Process the interaction
            success = await self.relationship_manager.process_interaction(
                event.persona1_id, event.persona2_id, event.quality, event.duration, event.context
            )
            
            if success:
                # Get updated relationship
                relationship = await self.relationship_manager.get_relationship(event.persona1_id, event.persona2_id)
                if relationship:
                    avg_score = (relationship.affinity + relationship.trust + relationship.respect + relationship.intimacy) / 4
                    print(f"📊 Updated Relationship: {relationship.relationship_type.value} (avg: {avg_score:.2f})")
                    print(f"   Affinity: {relationship.affinity:.2f}, Trust: {relationship.trust:.2f}, "
                          f"Respect: {relationship.respect:.2f}, Intimacy: {relationship.intimacy:.2f}")
                    print(f"   Total interactions: {relationship.interaction_count}")
            
            # Add some delay for realism
            await asyncio.sleep(0.1)
        
        # 3. Final relationship analysis
        print(f"\n📈 PHASE 3: Final Relationship Analysis")
        
        relationship_summary = {}
        for (p1_id, p2_id) in compatibility_matrix.keys():
            relationship = await self.relationship_manager.get_relationship(p1_id, p2_id)
            if relationship:
                p1_name = self.personas[p1_id].name
                p2_name = self.personas[p2_id].name
                
                initial_compat = compatibility_matrix[(p1_id, p2_id)]
                final_score = (relationship.affinity + relationship.trust + relationship.respect + relationship.intimacy) / 4
                
                relationship_summary[f"{p1_name}-{p2_name}"] = {
                    'initial_compatibility': initial_compat,
                    'final_score': final_score,
                    'relationship_type': relationship.relationship_type.value,
                    'interactions': relationship.interaction_count,
                    'total_time': relationship.total_interaction_time
                }
                
                print(f"\n🔗 {p1_name} ↔ {p2_name}:")
                print(f"   Relationship Type: {relationship.relationship_type.value}")
                print(f"   Evolution: {initial_compat:.2f} → {final_score:.2f} "
                      f"({final_score - initial_compat:+.2f})")
                print(f"   Dimensions: A:{relationship.affinity:.2f} T:{relationship.trust:.2f} "
                      f"R:{relationship.respect:.2f} I:{relationship.intimacy:.2f}")
                print(f"   Interactions: {relationship.interaction_count} ({relationship.total_interaction_time:.0f} minutes)")
        
        # 4. Insights and patterns
        print(f"\n🔍 PHASE 4: Simulation Insights")
        
        # Find strongest relationship
        strongest = max(relationship_summary.items(), key=lambda x: x[1]['final_score'])
        print(f"\n🏆 Strongest Relationship: {strongest[0]}")
        print(f"   Type: {strongest[1]['relationship_type']}, Score: {strongest[1]['final_score']:.2f}")
        
        # Find biggest improvement
        biggest_growth = max(relationship_summary.items(), 
                           key=lambda x: x[1]['final_score'] - x[1]['initial_compatibility'])
        growth = biggest_growth[1]['final_score'] - biggest_growth[1]['initial_compatibility']
        print(f"\n📈 Biggest Growth: {biggest_growth[0]} (+{growth:.2f})")
        
        # Find relationship types achieved
        types_achieved = set(rel['relationship_type'] for rel in relationship_summary.values())
        print(f"\n🎭 Relationship Types Achieved: {', '.join(types_achieved)}")
        
        # Statistical summary
        stats = await self.relationship_manager.get_relationship_stats()
        print(f"\n📊 Overall Statistics:")
        print(f"   Total Relationships: {stats['total_relationships']}")
        print(f"   Total Interactions: {stats['total_interactions']}")
        print(f"   Average Compatibility: {stats['average_compatibility']:.2f}")
        
        print(f"\n🎉 Simulation Complete!")
        print("=" * 60)


class MockDatabaseSession:
    """Mock database session for simulation (stores data in memory)"""
    
    def __init__(self):
        self.relationships = {}
        self.emotional_states = {}
        self.interaction_history = []
        
    async def fetchone(self, query: str, params: list = None):
        # Normalize query: lowercase, replace multiple spaces/newlines with single space
        import re
        q = re.sub(r'\s+', ' ', query.lower()).strip()
        
        # Aggregate/statistics queries
        if "select count(*) as count from relationships" in q:
            return [len(self.relationships)]
        if "select relationship_type, count(*) as count from relationships group by relationship_type" in q:
            # Not used in fetchone, handled in fetchall
            return None
        if "select avg((affinity + trust + respect + intimacy) / 4.0) as avg_compat from relationships" in q:
            vals = []
            for rel in self.relationships.values():
                try:
                    a = float(rel[2])
                    t = float(rel[3])
                    r = float(rel[4])
                    i = float(rel[5])
                    vals.append((a + t + r + i) / 4.0)
                except Exception as e:
                    print(f"DEBUG: Error parsing relationship values: {e}")
                    print(f"DEBUG: Relationship data: {rel}")
                    continue
            avg = sum(vals) / len(vals) if vals else 0.0
            print(f"DEBUG: Calculated average compatibility from {len(vals)} relationships: {avg}")
            print(f"DEBUG: Individual scores: {vals}")
            return [avg]
        if "select count(*) as count from interaction_history" in q:
            return [len(self.interaction_history)]
        if "select persona1_id as persona_id, count(*) as count from interaction_history group by persona1_id" in q:
            # Not used in fetchone, handled in fetchall
            return None
        # Relationship row fetch
        if "relationships" in q:
            if params and len(params) >= 4:
                p1, p2, p2_alt, p1_alt = params[:4]
                key = tuple(sorted([p1, p2]))
                rel_data = self.relationships.get(key)
                if rel_data:
                    rel_list = list(rel_data)
                    if len(rel_list) > 7 and hasattr(rel_list[7], 'value'):
                        rel_list[7] = rel_list[7].value
                    return rel_list
                return None
        elif "emotional_states" in q:
            if params and len(params) >= 1:
                persona_id = params[0]
                return self.emotional_states.get(persona_id)
        return None
        
    async def fetchall(self, query: str, params: list = None):
        # Normalize query: lowercase, replace multiple spaces/newlines with single space
        import re
        q = re.sub(r'\s+', ' ', query.lower()).strip()
        
        # Relationship type distribution
        if "select relationship_type, count(*) as count from relationships group by relationship_type" in q:
            type_counts = {}
            for rel in self.relationships.values():
                rel_type = rel[6] if not hasattr(rel[6], 'value') else rel[6].value
                type_counts[rel_type] = type_counts.get(rel_type, 0) + 1
            return [[k, v] for k, v in type_counts.items()]
        # Most active personas
        if "select persona1_id as persona_id, count(*) as count from interaction_history group by persona1_id" in q:
            counts = {}
            for row in self.interaction_history:
                persona1_id = row[0]
                counts[persona1_id] = counts.get(persona1_id, 0) + 1
            # Sort by count desc, limit 5
            sorted_counts = sorted(counts.items(), key=lambda x: x[1], reverse=True)[:5]
            return [[k, v] for k, v in sorted_counts]
        # Relationship row fetch for persona
        if "relationships" in q and params:
            persona_id = params[0]
            results = []
            for key, rel_data in self.relationships.items():
                if persona_id in key:
                    rel_list = list(rel_data)
                    if len(rel_list) > 7 and hasattr(rel_list[7], 'value'):
                        rel_list[7] = rel_list[7].value
                    results.append(rel_list)
            return results
        return []
        
    async def execute(self, query: str, params: list = None):
        if "INSERT INTO relationships" in query:
            if params and len(params) >= 13:
                p1, p2 = params[0], params[1]
                key = tuple(sorted([p1, p2]))
                params_list = list(params)
                # Ensure indices 2,3,4,5 are floats (affinity, trust, respect, intimacy)
                for idx in [2,3,4,5]:
                    try:
                        params_list[idx] = float(params_list[idx])
                    except Exception:
                        params_list[idx] = 0.0
                if len(params_list) > 7 and hasattr(params_list[7], 'value'):
                    params_list[7] = params_list[7].value
                self.relationships[key] = params_list
        elif "UPDATE relationships" in query:
            if params and len(params) >= 13:
                p1, p2 = params[-4], params[-3]
                key = tuple(sorted([p1, p2]))
                if key in self.relationships:
                    existing = list(self.relationships[key])
                    # Ensure indices 2,3,4,5 are floats
                    for idx, param_idx in zip([2,3,4,5], range(4)):
                        try:
                            existing[idx] = float(params[param_idx])
                        except Exception:
                            existing[idx] = 0.0
                    # Convert relationship_type enum to string if needed
                    if hasattr(params[4], 'value'):
                        existing[6] = params[4].value
                    else:
                        existing[6] = params[4]
                    existing[7] = params[5]
                    existing[8] = params[6]
                    existing[10] = params[7]
                    existing[12] = params[8]
                    self.relationships[key] = existing
        elif "INSERT INTO interaction_history" in query:
            if params:
                self.interaction_history.append(params)
        
    async def commit(self):
        pass


# Main execution
async def main():
    """Run the comprehensive relationship simulation"""
    simulation = RelationshipSimulation()
    await simulation.run_simulation()


if __name__ == "__main__":
    asyncio.run(main())