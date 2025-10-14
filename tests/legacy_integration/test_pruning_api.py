"""
Test Memory Pruning via MCP API
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from client.mcp_client import MCPTestClient


async def test_pruning_api():
    """Test memory pruning through MCP API"""
    print("Testing Memory Pruning via MCP API")
    print("=" * 40)
    
    # Connect to server
    client = MCPTestClient("ws://localhost:8000/mcp")
    
    try:
        await client.connect()
        print("✓ Connected to MCP server")
        
        # Switch to a persona
        personas = await client.list_personas()
        if not personas:
            print("❌ No personas available")
            return
        
        persona_id = personas[0]['id']
        await client.switch_persona(persona_id)
        print(f"✓ Switched to persona: {personas[0]['name']}")
        
        # Check current memory stats
        print("\n=== Current Memory Status ===")
        stats = await client.send_request("memory.stats", {})
        print(f"Current memories: {stats.get('total_memories', 0)}")
        
        # Get pruning recommendations
        print("\n=== Pruning Recommendations ===")
        recommendations = await client.send_request("memory.prune_recommendations", {})
        print(f"Recommendations: {recommendations}")
        
        # Check if pruning is needed
        if recommendations.get('recommendations', {}).get('needs_pruning', False):
            print(f"📝 Would prune {recommendations['recommendations']['would_prune']} memories")
            print(f"📈 Average importance to prune: {recommendations['recommendations']['average_importance_to_prune']:.3f}")
            
            # Get user confirmation for actual pruning
            print("\n⚠️  Pruning would permanently delete memories.")
            response = input("Execute pruning? (y/N): ")
            
            if response.lower() == 'y':
                print("\n=== Executing Pruning ===")
                result = await client.send_request("memory.prune", {"force": True})
                print(f"✅ Pruning completed!")
                print(f"   Memories before: {result['memories_before']}")
                print(f"   Memories pruned: {result['memories_pruned']}")
                print(f"   Memories after: {result['memories_after']}")
                print(f"   Processing time: {result['processing_time']:.3f}s")
            else:
                print("❌ Pruning cancelled by user")
        else:
            print("✅ No pruning needed - memory collection is within limits")
        
        # Get pruning system statistics
        print("\n=== Pruning System Stats ===")
        pruning_stats = await client.send_request("memory.prune_stats", {})
        stats = pruning_stats.get('pruning_statistics', {})
        
        if stats.get('total_pruning_operations', 0) > 0:
            print(f"Total pruning operations: {stats['total_pruning_operations']}")
            print(f"Total memories pruned: {stats['total_memories_pruned']}")
            print(f"Average processing time: {stats['average_processing_time']:.3f}s")
        else:
            print("No pruning operations have been performed yet")
        
        print("\n✅ Memory pruning API test completed!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(test_pruning_api())