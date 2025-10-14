"""
Register a new Matrix bot account programmatically

This script registers a new user account on the local Synapse homeserver
for use as a bot account.
"""

import asyncio
import aiohttp
import json

async def register_bot_account(username: str, password: str, homeserver: str = "http://localhost:8008"):
    """Register a new bot account on the Matrix homeserver"""
    
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
                    print(f"✅ Successfully registered bot: @{username}:localhost")
                    print(f"User ID: {data.get('user_id')}")
                    print(f"Access Token: {data.get('access_token')}")
                    return data
                else:
                    error_text = await response.text()
                    print(f"❌ Registration failed: {response.status}")
                    print(f"Error: {error_text}")
                    return None
                    
        except Exception as e:
            print(f"❌ Error during registration: {e}")
            return None

async def main():
    print("🤖 Matrix Bot Account Registration")
    print("=" * 40)
    
    # Register test bot
    bot_username = "testbot"
    bot_password = "test123"
    
    print(f"Registering bot account: {bot_username}")
    result = await register_bot_account(bot_username, bot_password)
    
    if result:
        print("\n✅ Bot registration successful!")
        print(f"You can now use these credentials in test_bot.py:")
        print(f"  user_id = '@{bot_username}:localhost'")
        print(f"  password = '{bot_password}'")
    else:
        print("\n❌ Bot registration failed. You may need to:")
        print("1. Register via Element Web interface instead")
        print("2. Check if registration is enabled in homeserver.yaml")

if __name__ == "__main__":
    asyncio.run(main())