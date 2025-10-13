#!/usr/bin/env python3
"""
Quick test script to avoid PowerShell JSON escaping issues
"""

import asyncio
import sys
from mcp_client import MCPTestClient

async def main():
    client = MCPTestClient()
    
    if not await client.connect():
        print("Failed to connect")
        return
    
    try:
        print("=== Testing persona.list ===")
        result = await client.list_personas()
        print(f"Result: {result}")
        
        print("\n=== Testing persona.switch ===")
        result = await client.switch_persona("aria")
        print(f"Result: {result}")
        
        print("\n=== Testing simple chat ===")
        result = await client.chat("Hello!")
        print(f"Result: {result}")
        
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(main())