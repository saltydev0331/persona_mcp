"""
Conversational Persona Bot - More natural interactions

This version responds to general greetings and conversations,
not just direct mentions, while still preventing bot loops.
"""

import asyncio
import sys
import logging
import time
from nio import AsyncClient, MatrixRoom, RoomMessageText, InviteEvent, JoinError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ConversationalPersonaBot:
    def __init__(self, persona_name: str):
        self.persona_name = persona_name
        self.homeserver = "http://localhost:8008"
        self.user_id = f"@{persona_name.lower()}:localhost"
        self.password = f"{persona_name.lower()}123"
        self.client = AsyncClient(self.homeserver, self.user_id)
        
        # Track introductions and recent messages
        self.has_introduced = set()
        self.recent_messages = []  # Prevent spam responses
        self.start_time = time.time()  # Only respond to messages after this time
        
    async def start(self):
        """Start the conversational persona bot"""
        try:
            logger.info(f"🤖 Starting CONVERSATIONAL {self.persona_name}...")
            
            response = await self.client.login(self.password)
            if hasattr(response, 'access_token'):
                logger.info(f"✅ {self.persona_name} logged in successfully")
            else:
                logger.error(f"❌ {self.persona_name} login failed: {response}")
                return False
            
            # Set up callbacks
            self.client.add_event_callback(self.message_callback, RoomMessageText)
            self.client.add_event_callback(self.invite_callback, InviteEvent)
            
            logger.info(f"💬 {self.persona_name} ready for natural conversation!")
            
            # Small delay to ensure we're fully synced, then reset start time
            await asyncio.sleep(2)
            self.start_time = time.time()  # Reset to NOW - only respond to messages from this point forward
            logger.info(f"⏰ {self.persona_name} now responding to NEW messages only!")
            
            # Start syncing
            await self.client.sync_forever(timeout=30000)
            
        except Exception as e:
            logger.error(f"❌ {self.persona_name} error: {e}")
        finally:
            await self.client.close()
    
    async def invite_callback(self, room: MatrixRoom, event: InviteEvent):
        """Handle room invitations"""
        logger.info(f"📨 {self.persona_name} received invite to room")
        
        try:
            await self.client.join(room.room_id)
            logger.info(f"✅ {self.persona_name} joined room: {room.display_name or room.room_id}")
            
            # Send introduction if first time in this room
            if room.room_id not in self.has_introduced:
                await self.client.room_send(
                    room_id=room.room_id,
                    message_type="m.room.message",
                    content={
                        "msgtype": "m.text",
                        "body": f"👋 Hello everyone! I'm {self.persona_name}. Great to be here!"
                    }
                )
                self.has_introduced.add(room.room_id)
                logger.info(f"📤 {self.persona_name} sent introduction")
            
        except JoinError as e:
            logger.error(f"❌ {self.persona_name} failed to join room: {e}")
        except Exception as e:
            logger.error(f"❌ {self.persona_name} invite error: {e}")
    
    async def message_callback(self, room: MatrixRoom, event: RoomMessageText):
        """Handle messages with natural conversation logic"""
        if event.sender == self.user_id:
            return  # Don't respond to own messages
        
        # Only respond to messages sent AFTER the bot started (ignore historical messages)
        message_time = event.server_timestamp / 1000  # Convert to seconds
        if message_time < self.start_time:
            return  # Ignore historical messages
        
        sender_name = event.sender.split(':')[0][1:]
        message = event.body.lower()
        
        # **NEVER respond to other bots** - prevents infinite loops
        if sender_name in ["alice", "bob", "charlie", "testbot"]:
            logger.info(f"🤐 {self.persona_name} ignoring bot message from {sender_name}")
            return
        
        logger.info(f"💬 {room.display_name}: {sender_name}: {event.body[:100]}...")
        
        # Prevent spam by checking recent messages
        recent_key = f"{room.room_id}:{sender_name}:{message[:20]}"
        if recent_key in self.recent_messages[-5:]:  # Don't respond to same message twice
            return
        self.recent_messages.append(recent_key)
        if len(self.recent_messages) > 20:  # Keep list manageable
            self.recent_messages = self.recent_messages[-15:]
        
        # Natural conversation logic
        response = None
        persona_lower = self.persona_name.lower()
        
        # 1. Direct mentions always get a response
        if f"@{persona_lower}" in message:
            response = f"Hi {sender_name}! You mentioned me - what can I help you with? 😊"
        
        # 2. Direct address (name at start)
        elif message.startswith(f"{persona_lower}"):
            if "hello" in message or "hi" in message:
                response = f"Hello {sender_name}! How are you doing today?"
            elif "how are you" in message:
                response = f"I'm doing great, thanks for asking! What about you, {sender_name}?"
            elif "?" in message:
                response = f"That's a great question, {sender_name}! I'd love to discuss that."
            else:
                response = f"Hi {sender_name}! I'm {self.persona_name}. What's on your mind?"
        
        # 3. General greetings (respond sometimes, not always)
        elif any(greeting in message for greeting in ["hello everyone", "hi everyone", "hey everyone", "good morning", "good afternoon"]):
            # Only respond if no other bot has responded recently
            should_respond = self._should_respond_to_general_greeting()
            logger.info(f"🎲 {self.persona_name} general greeting check: should_respond={should_respond}")
            if should_respond:
                response = f"Hello there, {sender_name}! {self.persona_name} here. Hope you're having a great day! 👋"
                logger.info(f"💡 {self.persona_name} will respond to general greeting")
            else:
                logger.info(f"🤫 {self.persona_name} chose not to respond to general greeting (randomization)")
        
        # 4. Questions about personas
        elif "who are you" in message or "what are you" in message:
            response = f"I'm {self.persona_name}! I'm a conversational AI persona. Nice to meet you, {sender_name}!"
        
        # 5. Simple greetings directed at the room
        elif any(greeting in message for greeting in ["hello", "hi", "hey"]) and len(message.split()) <= 2:
            # Respond to simple greetings sometimes
            if self._should_respond_to_simple_greeting():
                response = f"Hey {sender_name}! {self.persona_name} here. How's it going?"
        
        # 6. Follow-up conversational responses
        elif any(phrase in message for phrase in ["how are you", "how's it going", "what's up", "how do you do"]):
            if self._should_respond_to_simple_greeting():  # 100% chance currently
                response = f"I'm doing great, {sender_name}! Thanks for asking. How about you?"
        
        # 7. Acknowledgment responses
        elif any(phrase in message for phrase in ["i am!", "i'm good", "i'm great", "doing well", "not bad"]):
            if self._should_respond_to_simple_greeting():  # 100% chance currently
                response = f"That's wonderful to hear, {sender_name}! Glad you're doing well. 😊"
        
        # 8. Generic conversational catchall for questions
        elif "?" in message and len(message.split()) >= 3:  # Multi-word questions
            if self._should_respond_to_simple_greeting():  # 100% chance currently
                response = f"That's an interesting question, {sender_name}! I'd love to chat about that with you."
        
        # Send response if we have one
        if response:
            try:
                await self.client.room_send(
                    room_id=room.room_id,
                    message_type="m.room.message",
                    content={"msgtype": "m.text", "body": response}
                )
                
                logger.info(f"📤 {self.persona_name} → {sender_name}: {response[:80]}...")
                
            except Exception as e:
                logger.error(f"❌ {self.persona_name} failed to respond: {e}")
        else:
            logger.info(f"🤔 {self.persona_name} no response generated for: '{message[:50]}...'")
            logger.info(f"   Reasons checked: @mention={f'@{persona_lower}' in message}, starts_with_name={message.startswith(persona_lower)}, general_greeting={any(greeting in message for greeting in ['hello everyone', 'hi everyone', 'hey everyone', 'good morning', 'good afternoon'])}")
    
    def _should_respond_to_general_greeting(self) -> bool:
        """Decide if we should respond to a general greeting"""
        # Temporarily set to 100% for testing - was 50%
        import random
        should = random.random() < 1.0  # 100% chance for testing
        return should
    
    def _should_respond_to_simple_greeting(self) -> bool:
        """Decide if we should respond to a simple greeting"""
        # Temporarily set to 100% for testing - was 30%
        import random
        should = random.random() < 1.0  # 100% chance for testing
        return should

async def main():
    if len(sys.argv) != 2:
        print("Usage: python conversational_persona_bot.py <PersonaName>")
        print("Example: python conversational_persona_bot.py Alice")
        return
    
    persona_name = sys.argv[1].capitalize()
    
    if persona_name not in ["Alice", "Bob", "Charlie"]:
        print(f"❌ Unknown persona: {persona_name}")
        print("Available personas: Alice, Bob, Charlie")
        return
    
    print(f"🤖 Starting CONVERSATIONAL {persona_name}...")
    print("💬 This version responds naturally to greetings and conversations!")
    print("🛡️ Still prevents infinite loops between bots")
    print("Press Ctrl+C to stop")
    
    bot = ConversationalPersonaBot(persona_name)
    
    try:
        await bot.start()
    except KeyboardInterrupt:
        print(f"\n🛑 Stopping {persona_name}...")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())