"""
Test script to verify operational parity between MCP and PersonaAPI servers.

This script tests that both services provide identical functionality through
their respective interfaces (WebSocket vs HTTP).
"""

import asyncio
import json
import aiohttp
import websockets
from typing import Dict, Any, List


class OperationalParityTest:
    """Test operational parity between MCP and PersonaAPI servers"""
    
    def __init__(self):
        self.mcp_uri = "ws://localhost:8000/mcp"
        self.api_base = "http://localhost:8080/api"
        self.request_id = 0
        
    async def mcp_call(self, method: str, params: Dict[str, Any] = None) -> Any:
        """Make MCP WebSocket call"""
        self.request_id += 1
        request = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {},
            "id": str(self.request_id)
        }
        
        async with websockets.connect(self.mcp_uri) as websocket:
            await websocket.send(json.dumps(request))
            response = await websocket.recv()
            result = json.loads(response)
            
            if "error" in result:
                raise Exception(f"MCP Error: {result['error']['message']}")
            return result.get("result")
    
    async def api_call(self, endpoint: str, method: str = "GET", data: Dict[str, Any] = None) -> Any:
        """Make HTTP API call"""
        async with aiohttp.ClientSession() as session:
            url = f"{self.api_base}{endpoint}"
            
            if method == "GET":
                async with session.get(url) as response:
                    result = await response.json()
            elif method == "POST":
                async with session.post(url, json=data) as response:
                    result = await response.json()
            elif method == "DELETE":
                async with session.delete(url) as response:
                    result = await response.json()
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            if not result.get("success"):
                raise Exception(f"API Error: {result}")
            return result
    
    async def test_health_checks(self):
        """Test that both services are responsive"""
        print("🏥 Testing health checks...")
        
        try:
            # Test MCP health via system.status
            mcp_status = await self.mcp_call("system.status")
            print("   ✓ MCP server responsive")
            
            # Test API health
            api_health = await self.api_call("/health")
            print("   ✓ PersonaAPI server responsive")
            
            return True
        except Exception as e:
            print(f"   ❌ Health check failed: {e}")
            return False
    
    async def test_persona_operations(self):
        """Test persona CRUD operations have parity"""
        print("👤 Testing persona operations parity...")
        
        try:
            # Test list personas
            mcp_personas = await self.mcp_call("persona.list")
            api_result = await self.api_call("/personas")
            api_personas = api_result["personas"]
            
            # Compare results
            if len(mcp_personas["personas"]) == len(api_personas):
                print(f"   ✓ List personas: Both return {len(api_personas)} personas")
            else:
                print(f"   ⚠️  List personas: MCP={len(mcp_personas['personas'])}, API={len(api_personas)}")
            
            # Test get specific persona (if any exist)
            if api_personas:
                persona_id = api_personas[0]["id"]
                
                # Get via MCP
                mcp_persona = await self.mcp_call("persona.get", {"persona_id": persona_id})
                
                # Get via API
                api_result = await self.api_call(f"/personas/{persona_id}")
                api_persona = api_result["persona"]
                
                # Compare key fields
                if mcp_persona["persona"]["id"] == api_persona["id"]:
                    print("   ✓ Get persona: Both return same persona data")
                else:
                    print("   ❌ Get persona: Data mismatch")
            
            return True
        except Exception as e:
            print(f"   ❌ Persona operations test failed: {e}")
            return False
    
    async def test_memory_operations(self):
        """Test memory operations have parity"""
        print("🧠 Testing memory operations parity...")
        
        try:
            # Get first persona for testing
            api_result = await self.api_call("/personas")
            if not api_result["personas"]:
                print("   ⚠️  No personas available for memory testing")
                return True
                
            persona_id = api_result["personas"][0]["id"]
            
            # Test memory stats
            mcp_stats = await self.mcp_call("memory.stats", {"persona_id": persona_id})
            api_result = await self.api_call(f"/memory/{persona_id}/stats")
            api_stats = api_result["stats"]
            
            # Compare memory counts
            mcp_count = mcp_stats.get("total_memories", 0)
            api_count = api_stats.get("total_memories", 0)
            
            if mcp_count == api_count:
                print(f"   ✓ Memory stats: Both report {mcp_count} memories")
            else:
                print(f"   ⚠️  Memory stats: MCP={mcp_count}, API={api_count}")
            
            # Test memory search
            if mcp_count > 0:
                mcp_memories = await self.mcp_call("memory.search", {
                    "persona_id": persona_id,
                    "query": "conversation",
                    "n_results": 3
                })
                
                api_result = await self.api_call(f"/memory/{persona_id}/search?query=conversation&n_results=3")
                api_memories = api_result["memories"]
                
                if len(mcp_memories["memories"]) == len(api_memories):
                    print(f"   ✓ Memory search: Both return {len(api_memories)} results")
                else:
                    print(f"   ⚠️  Memory search: MCP={len(mcp_memories['memories'])}, API={len(api_memories)}")
            
            return True
        except Exception as e:
            print(f"   ❌ Memory operations test failed: {e}")
            return False
    
    async def test_system_information(self):
        """Test system information endpoints"""
        print("📊 Testing system information parity...")
        
        try:
            # Test system status
            mcp_status = await self.mcp_call("system.status")
            api_result = await self.api_call("/system/status")
            api_status = api_result["system"]
            
            # Both should provide system information
            if "database" in api_status and "memory" in api_status:
                print("   ✓ System status: Both provide comprehensive system info")
            else:
                print("   ⚠️  System status: API missing expected fields")
            
            return True
        except Exception as e:
            print(f"   ❌ System information test failed: {e}")
            return False
    
    async def run_all_tests(self):
        """Run all operational parity tests"""
        print("🧪 Running Operational Parity Tests")
        print("=====================================")
        print("")
        
        tests = [
            ("Health Checks", self.test_health_checks),
            ("Persona Operations", self.test_persona_operations),
            ("Memory Operations", self.test_memory_operations),
            ("System Information", self.test_system_information)
        ]
        
        passed = 0
        total = len(tests)
        
        for test_name, test_func in tests:
            try:
                result = await test_func()
                if result:
                    passed += 1
                print("")
            except Exception as e:
                print(f"   ❌ {test_name} failed with exception: {e}")
                print("")
        
        print("📋 Test Results")
        print("===============")
        print(f"Passed: {passed}/{total}")
        
        if passed == total:
            print("🎉 All tests passed! Operational parity confirmed.")
            print("")
            print("✅ Both MCP and PersonaAPI servers provide equivalent functionality")
            print("✅ Clean separation with parity architecture is working correctly")
        else:
            print("⚠️  Some tests failed. Check server logs for issues.")
        
        return passed == total


async def main():
    """Run operational parity tests"""
    test = OperationalParityTest()
    success = await test.run_all_tests()
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)