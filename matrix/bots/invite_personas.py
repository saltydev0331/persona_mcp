"""
Simple Room Inviter - Invite personas to an existing room

This script invites all personas to a room you've already created in Element.
Much simpler and avoids rate limiting issues.
"""

import asyncio
from nio import AsyncClient

async def invite_personas_to_room(room_id: str):
    """Invite all personas to a specific room"""
    
    # Your credentials
    homeserver = "http://localhost:8008"
    user_id = "@saltydev0331:localhost"
    password = "Fz1BF0m7#"
    
    # Persona user IDs
    personas = [
        "@alice:localhost",
        "@bob:localhost", 
        "@charlie:localhost"
    ]
    
    print(f"🔑 Logging in as {user_id}...")
    client = AsyncClient(homeserver, user_id)
    
    try:
        response = await client.login(password)
        if not hasattr(response, 'access_token'):
            print(f"❌ Login failed: {response}")
            return
        
        print("✅ Logged in successfully")
        print(f"📤 Inviting personas to room: {room_id}")
        
        # Invite each persona
        for persona_id in personas:
            try:
                await client.room_invite(room_id, persona_id)
                print(f"✅ Invited {persona_id}")
                await asyncio.sleep(1)  # Small delay between invites
            except Exception as e:
                print(f"❌ Failed to invite {persona_id}: {e}")
        
        print("✅ All invitations sent!")
        print("\nNext steps:")
        print("1. Run individual persona bots to auto-accept invites")
        print("2. Or manually accept invites through Element Web")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await client.close()

async def main():
    print("🏠 Matrix Room Persona Inviter")
    print("=" * 40)
    
    # Get room ID from user
    print("To get the room ID:")
    print("1. Go to Element Web (localhost:8080)")
    print("2. Create a new room")
    print("3. Click room settings → Advanced → Internal room ID")
    print()
    
    room_id = input("Enter the room ID (starts with !): ").strip()
    
    if not room_id.startswith("!"):
        print("❌ Invalid room ID. Must start with '!'")
        return
    
    print(f"\n📤 Inviting personas to room: {room_id}")
    await invite_personas_to_room(room_id)

if __name__ == "__main__":
    asyncio.run(main())