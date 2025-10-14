"""
Test the integrated importance scoring by directly testing the handlers
"""

import asyncio
import sys
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from persona_mcp.memory.importance_scorer import MemoryImportanceScorer
from persona_mcp.models import Persona, Memory


async def test_importance_integration():
    """Test importance scoring integration"""
    print("Testing Importance Scoring Integration")
    print("=" * 50)
    
    # Create test scorer
    scorer = MemoryImportanceScorer()
    
    # Create test persona with interests
    test_persona = Persona(
        id="test_wizard",
        name="Test Wizard", 
        description="A test wizard",
        topic_preferences={
            "magic": 95,
            "spells": 90,
            "books": 85,
            "library": 80
        }
    )
    
    # Test different message types that would come from user chat
    test_messages = [
        "I love reading about magical theories and ancient spells",
        "Tell me about your favorite books on enchantment", 
        "What's your opinion on defensive magic versus offensive spells?",
        "I heard there's a new library opening with rare magical texts",
        "The weather is nice today",
        "EMERGENCY! There's a dragon attacking!",
        "I'm so bored with everything"
    ]
    
    print("\nTesting User Chat Message Importance Scoring:")
    print("-" * 50)
    
    for message in test_messages:
        # Simulate the memory content format used in handlers
        memory_content = f"User said: {message}. I responded: [Generated response]"
        
        # Calculate importance as done in handlers
        importance = scorer.calculate_importance(
            content=memory_content,
            speaker=test_persona,
            listener=None,
            context={
                'continue_score': 50.0,
                'topic': 'user_conversation',
                'response_type': 'direct'
            }
        )
        
        print(f"Message: '{message}'")
        print(f"Importance: {importance:.3f}")
        
        # Add interpretation
        if importance >= 0.8:
            interpretation = "🔥 CRITICAL - High retention"
        elif importance >= 0.6:
            interpretation = "⭐ HIGH - Important memory"
        elif importance >= 0.5:
            interpretation = "📝 MEDIUM - Standard retention"
        else:
            interpretation = "📋 LOW - May be pruned"
        
        print(f"Status: {interpretation}")
        print()
    
    print("✅ Integration test completed!")
    print("\nKey Observations:")
    print("- Magic-related content should score higher (0.6-0.8+)")
    print("- Emergency content should score very high (0.8+)")
    print("- Boring content should score lower (0.4-0.5)")
    print("- All scores should be different from the old hardcoded 0.8")


if __name__ == "__main__":
    asyncio.run(test_importance_integration())