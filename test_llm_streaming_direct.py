#!/usr/bin/env python3
"""
Simple test for LLM streaming functionality
"""

import asyncio
import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

async def test_llm_streaming():
    from persona_mcp.llm import LLMManager
    from persona_mcp.models import Persona, ConversationContext, Priority
    
    print("Testing LLM streaming directly...")
    
    try:
        mgr = LLMManager()
        await mgr.initialize()
        
        persona = Persona(
            name='Test',
            description='Test persona',
            personality_traits={},
            topic_preferences={},
            charisma=10,
            intelligence=10,
            social_rank="test"
        )
        
        ctx = ConversationContext(
            id='test',
            participants=[],
            topic='test',
            context_type='test',
            turn_count=1,
            urgency=Priority.CASUAL,
            token_budget=50
        )
        
        print("Attempting to stream...")
        chunk_count = 0
        async for chunk in mgr.generate_response_stream('Hello', persona, ctx):
            chunk_count += 1
            print(f'Chunk {chunk_count}: {repr(chunk)}')
            if chunk_count > 10:  # Safety limit
                break
        
        print(f"Success! Got {chunk_count} chunks")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_llm_streaming())