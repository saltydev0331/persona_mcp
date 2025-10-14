# Matrix Persona Bots

This directory contains the Matrix bot implementations for the persona-mcp system.

## Core Bot Files

### **conversational_persona_bot.py** (RECOMMENDED)

- **Purpose**: Enhanced conversational bot with natural greeting responses
- **Features**: Responds to general greetings, smart randomization, loop prevention
- **Usage**: `python conversational_persona_bot.py <PersonaName>`
- **Status**: **RECOMMENDED** - Best user experience, ready for MCP bridge

### **persona_bot.py** (Conservative)

- **Purpose**: Conservative bot that only responds to direct mentions
- **Features**: Very limited responses, bulletproof loop prevention
- **Usage**: `python persona_bot.py <PersonaName>`
- **Status**: Stable but less engaging (won't respond to "hello everyone")

## Setup & Management Scripts

### **create_personas.py**

- **Purpose**: Creates Alice, Bob, Charlie persona accounts
- **Usage**: `python create_personas.py`
- **Note**: Run once to set up persona accounts

### **invite_personas.py**

- **Purpose**: Invites all personas to a specific room
- **Usage**: `python invite_personas.py` (prompts for room ID)

### **auto_room_setup.py**

- **Purpose**: Automated room creation and persona invitation
- **Usage**: `python auto_room_setup.py`

## Testing & Development

### **test_bot.py**

- **Purpose**: Basic bot for connectivity testing
- **Usage**: `python test_bot.py`

### **register_bot.py**

- **Purpose**: Register a test bot account
- **Usage**: `python register_bot.py`

## Framework

### **persona_bot_manager.py**

- **Purpose**: Advanced bot management framework (for future MCP integration)
- **Status**: Framework for MCP bridge implementation

## Quick Start

1. **Create persona accounts** (run once):

   ```bash
   python create_personas.py
   ```

2. **Start a persona bot** (RECOMMENDED):

   ```bash
   python conversational_persona_bot.py Alice
   ```

   Or for conservative version:

   ```bash
   python persona_bot.py Alice
   ```

3. **Create room and invite personas**:
   ```bash
   python auto_room_setup.py
   ```

## Next Steps

- **MCP Bridge**: Connect bots to persona-mcp backend for full intelligence
- **Production Deployment**: Use persona_bot.py as the main production bot
