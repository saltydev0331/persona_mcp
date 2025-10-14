"""
Simple Persona Bot Creator - Register persona bots one at a time

This script helps create persona bot accounts with proper delays
to avoid rate limiting.
"""

import asyncio
import aiohttp
import json

async def register_persona_bot(persona_name: str, homeserver: str = "http://localhost:8008"):
    """Register a single persona bot"""
    username = persona_name.lower()
    user_id = f"@{username}:localhost"
    password = f"{username}123"
    
    registration_url = f"{homeserver}/_matrix/client/r0/register"
    registration_data = {
        "username": username,
        "password": password,
        "auth": {"type": "m.login.dummy"}
    }
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(registration_url, json=registration_data) as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ Successfully registered: {user_id}")
                    print(f"   Password: {password}")
                    return True
                else:
                    error_text = await response.text()
                    if "User ID already taken" in error_text:
                        print(f"ℹ️ User {user_id} already exists")
                        return True
                    else:
                        print(f"❌ Registration failed for {user_id}: {error_text}")
                        return False
                        
        except Exception as e:
            print(f"❌ Error registering {user_id}: {e}")
            return False

async def main():
    print("🤖 Persona Bot Registration")
    print("=" * 40)
    
    # Register personas one by one with delays
    personas = ["Alice", "Bob", "Charlie"]
    
    for persona in personas:
        print(f"\nRegistering {persona}...")
        success = await register_persona_bot(persona)
        if success:
            print(f"✅ {persona} ready!")
        else:
            print(f"❌ Failed to register {persona}")
        
        # Wait between registrations to avoid rate limits
        print("⏳ Waiting 3 seconds...")
        await asyncio.sleep(3)
    
    print("\n" + "=" * 40)
    print("✅ All persona bots registered!")
    print("\nYou can now use these credentials:")
    for persona in personas:
        username = persona.lower()
        print(f"  {persona}: @{username}:localhost / {username}123")

if __name__ == "__main__":
    asyncio.run(main())