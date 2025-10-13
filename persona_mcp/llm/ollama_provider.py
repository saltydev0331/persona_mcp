"""
Local Ollama LLM integration for persona response generation
"""

import httpx
import json
from typing import Dict, List, Optional, Any, AsyncGenerator
from abc import ABC, abstractmethod
import asyncio
from datetime import datetime
import logging

from ..models import Persona, ConversationContext


class LLMProvider(ABC):
    """Abstract base class for LLM providers"""
    
    @abstractmethod
    async def generate_response(
        self, 
        prompt: str, 
        persona: Persona,
        context: ConversationContext,
        constraints: Optional[Dict[str, Any]] = None
    ) -> str:
        """Generate a response from the LLM"""
        pass
    
    @abstractmethod
    async def generate_response_stream(
        self, 
        prompt: str, 
        persona: Persona,
        context: ConversationContext,
        constraints: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[str, None]:
        """Generate a streaming response from the LLM"""
        pass
    
    @abstractmethod
    async def is_available(self) -> bool:
        """Check if the LLM provider is available"""
        pass


class OllamaProvider(LLMProvider):
    """Ollama local LLM provider"""
    
    def __init__(self, base_url: str = "http://localhost:11434", default_model: str = "llama3.1:8b"):
        self.base_url = base_url.rstrip('/')
        self.default_model = default_model
        self.client = httpx.AsyncClient(timeout=60.0)
    
    async def is_available(self) -> bool:
        """Check if Ollama is running and accessible"""
        try:
            response = await self.client.get(f"{self.base_url}/api/tags")
            return response.status_code == 200
        except:
            return False
    
    async def generate_response(
        self, 
        prompt: str, 
        persona: Persona,
        context: ConversationContext,
        constraints: Optional[Dict[str, Any]] = None
    ) -> str:
        """Generate response using Ollama"""
        
        # Build the full prompt with persona context
        full_prompt = self._build_persona_prompt(prompt, persona, context, constraints)
        
        try:
            # Call Ollama API
            model_to_use = constraints.get("model", self.default_model) if constraints else self.default_model
            payload = {
                "model": model_to_use,
                "prompt": full_prompt,
                "stream": False,
                "options": self._get_generation_options(constraints)
            }
            
            # Log the model being used
            print(f"🤖 Requesting Ollama model: {model_to_use}")
            
            response = await self.client.post(
                f"{self.base_url}/api/generate",
                json=payload
            )
            
            if response.status_code == 200:
                result = response.json()
                # Log confirmation of successful model usage
                print(f"✅ Ollama responded successfully using model: {model_to_use}")
                return result.get("response", "").strip()
            else:
                print(f"❌ Ollama API error: {response.status_code} - {response.text}")
                return self._generate_fallback_response(persona, context)
                
        except Exception as e:
            print(f"Error calling Ollama: {e}")
            return self._generate_fallback_response(persona, context)
    
    async def generate_response_stream(
        self, 
        prompt: str, 
        persona: Persona,
        context: ConversationContext,
        constraints: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[str, None]:
        """Generate streaming response using Ollama"""
        
        logger = logging.getLogger(__name__)
        
        # Build the full prompt with persona context
        full_prompt = self._build_persona_prompt(prompt, persona, context, constraints)
        
        try:
            # Call Ollama streaming API
            model_to_use = constraints.get("model", self.default_model) if constraints else self.default_model
            payload = {
                "model": model_to_use,
                "prompt": full_prompt,
                "stream": True,  # Enable streaming
                "options": self._get_generation_options(constraints)
            }
            
            logger.info(f"🌊 Starting streaming response with model: {model_to_use}")
            
            # Use httpx streaming
            async with self.client.stream(
                'POST', 
                f"{self.base_url}/api/generate",
                json=payload
            ) as response:
                
                if response.status_code != 200:
                    logger.error(f"❌ Ollama streaming error: {response.status_code}")
                    # Fallback to single chunk
                    yield self._generate_fallback_response(persona, context)
                    return
                
                # Process streaming response
                async for line in response.aiter_lines():
                    if line.strip():
                        try:
                            chunk_data = json.loads(line)
                            
                            # Extract response chunk
                            if "response" in chunk_data:
                                chunk_text = chunk_data["response"]
                                if chunk_text:  # Only yield non-empty chunks
                                    yield chunk_text
                            
                            # Check if streaming is complete
                            if chunk_data.get("done", False):
                                logger.info("✅ Ollama streaming completed successfully")
                                break
                                
                        except json.JSONDecodeError as e:
                            logger.warning(f"Failed to parse streaming chunk: {e}")
                            continue
                            
        except Exception as e:
            logger.error(f"Error in Ollama streaming: {e}")
            # Fallback to single response chunk
            fallback = self._generate_fallback_response(persona, context)
            yield fallback
    
    def _build_persona_prompt(
        self, 
        user_input: str, 
        persona: Persona, 
        context: ConversationContext,
        constraints: Optional[Dict[str, Any]] = None
    ) -> str:
        """Build a comprehensive prompt including persona context"""
        
        # Base persona description
        prompt_parts = [
            f"You are {persona.name}. {persona.description}",
            "",
            "Your personality traits:",
        ]
        
        for trait, value in persona.personality_traits.items():
            prompt_parts.append(f"- {trait}: {value}")
        
        prompt_parts.append("")
        
        # Current state context
        state = persona.interaction_state
        prompt_parts.extend([
            "Current situation:",
            f"- Energy level: {state.social_energy}/200",
            f"- Current priority: {state.current_priority.value}",
            f"- Interest in conversation: {state.interest_level}/100",
            f"- Available time: {state.available_time} seconds",
            ""
        ])
        
        # Conversation context
        if context.topic != "general":
            prompt_parts.append(f"Current topic: {context.topic}")
        
        if context.turn_count > 0:
            prompt_parts.append(f"This is turn {context.turn_count + 1} in the conversation.")
        
        # Apply constraints if provided
        if constraints:
            prompt_parts.append("")
            prompt_parts.append("Response guidelines:")
            
            if constraints.get("max_length"):
                prompt_parts.append(f"- Keep response under {constraints['max_length']} words")
            
            if constraints.get("style"):
                prompt_parts.append(f"- Style: {constraints['style']}")
            
            if constraints.get("prepare_exit"):
                prompt_parts.append("- Prepare to end the conversation politely")
            
            if constraints.get("avoid_topics"):
                topics = ", ".join(constraints["avoid_topics"])
                prompt_parts.append(f"- Avoid discussing: {topics}")
        
        prompt_parts.extend([
            "",
            f"Respond to: {user_input}",
            "",
            f"Response as {persona.name}:"
        ])
        
        return "\n".join(prompt_parts)
    
    def _get_generation_options(self, constraints: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Get Ollama generation options based on constraints"""
        
        options = {
            "temperature": 0.7,
            "top_p": 0.9,
            "top_k": 40,
            "num_predict": 150,  # Default response length
        }
        
        if constraints:
            # Adjust creativity based on continue score or explicit setting
            if "creativity" in constraints:
                options["temperature"] = constraints["creativity"]
            
            # Adjust response length
            if constraints.get("max_length"):
                # Rough conversion: words to tokens (1 word ≈ 1.3 tokens)
                max_tokens = int(constraints["max_length"] * 1.3)
                options["num_predict"] = min(max_tokens, 300)
            
            # More focused responses for low engagement
            if constraints.get("style") == "concise":
                options["temperature"] = 0.5
                options["num_predict"] = 50
        
        return options
    
    def _generate_fallback_response(self, persona: Persona, context: ConversationContext) -> str:
        """Generate a simple fallback response when LLM fails"""
        
        fallbacks = [
            "I'm having trouble finding the right words right now.",
            "Let me think about that for a moment.",
            "That's an interesting point to consider.",
            "I appreciate you bringing that up.",
        ]
        
        # Choose based on persona priority
        if persona.interaction_state.current_priority.value == "urgent":
            return "I really need to focus on urgent matters right now."
        elif persona.interaction_state.social_energy < 30:
            return "I'm feeling a bit drained from all this conversation."
        else:
            import random
            return random.choice(fallbacks)
    
    async def list_available_models(self) -> List[str]:
        """Get list of available Ollama models"""
        try:
            response = await self.client.get(f"{self.base_url}/api/tags")
            if response.status_code == 200:
                data = response.json()
                return [model["name"] for model in data.get("models", [])]
        except:
            pass
        return []
    
    async def close(self):
        """Clean up HTTP client"""
        await self.client.aclose()


class LLMManager:
    """Manages LLM providers and routing based on conversation state"""
    
    def __init__(self, ollama_host: str = "http://localhost:11434", default_model: str = "llama3.1:8b"):
        self.ollama = OllamaProvider(ollama_host, default_model)
        self.providers = {"ollama": self.ollama}
        self.default_provider = "ollama"
    
    async def initialize(self) -> bool:
        """Initialize and verify LLM providers"""
        available = await self.ollama.is_available()
        if not available:
            print("Warning: Ollama is not available. Responses will use fallback templates.")
        return available
    
    async def generate_response_by_score(
        self, 
        continue_score: int, 
        user_input: str,
        persona: Persona,
        context: ConversationContext
    ) -> tuple[str, str]:
        """Generate response based on continue score (returns response, response_type)"""
        
        if continue_score >= 80:
            # High engagement: Full LLM with high creativity
            response = await self._generate_full_response(
                user_input, persona, context, creativity=0.8
            )
            return response, "full_llm"
        
        elif continue_score >= 60:
            # Medium engagement: Standard LLM response
            response = await self._generate_full_response(
                user_input, persona, context, creativity=0.6
            )
            return response, "full_llm"
        
        elif continue_score >= 40:
            # Low engagement: Constrained LLM with exit preparation
            response = await self._generate_constrained_response(
                user_input, persona, context, prepare_exit=True
            )
            return response, "constrained"
        
        else:
            # Very low engagement: Template-based quick responses
            response = self._generate_template_response(persona, context)
            return response, "template"
    
    async def _generate_full_response(
        self, 
        user_input: str, 
        persona: Persona, 
        context: ConversationContext,
        creativity: float = 0.7
    ) -> str:
        """Generate full LLM response"""
        constraints = {
            "creativity": creativity,
            "max_length": 100
        }
        
        return await self.ollama.generate_response(user_input, persona, context, constraints)
    
    async def _generate_constrained_response(
        self, 
        user_input: str, 
        persona: Persona, 
        context: ConversationContext,
        prepare_exit: bool = False
    ) -> str:
        """Generate shorter, more focused responses"""
        constraints = {
            "max_length": 50,
            "style": "concise",
            "creativity": 0.5,
            "prepare_exit": prepare_exit
        }
        
        return await self.ollama.generate_response(user_input, persona, context, constraints)
    
    def _generate_template_response(self, persona: Persona, context: ConversationContext) -> str:
        """Fast template-based responses for very low continue scores"""
        
        state = persona.interaction_state
        
        # Choose template category based on persona state
        if state.current_priority.value == "urgent":
            templates = [
                "I really must go.",
                "I have urgent matters to attend to.", 
                "Perhaps we can continue this later."
            ]
        elif state.social_energy < 30:
            templates = [
                "I'm feeling a bit drained.",
                "I think I need a break from talking.",
                "It's been a long day for me."
            ]
        elif state.interaction_fatigue > 50:
            templates = [
                "Interesting... I should get going though.",
                "I'll let you get back to what you were doing.",
                "Nice chatting with you."
            ]
        else:
            templates = [
                "I see.",
                "That's good to know.",
                "Hmm, interesting."
            ]
        
        import random
        return random.choice(templates)
    
    def estimate_token_usage(self, response: str, response_type: str) -> int:
        """Estimate token consumption for different response types"""
        base_tokens = len(response.split()) * 1.3  # Rough word-to-token conversion
        
        multipliers = {
            "full_llm": 1.5,      # Full LLM calls use more tokens for processing
            "constrained": 1.0,   # Constrained responses use normal tokens
            "template": 0.1       # Template responses use minimal tokens
        }
        
        return int(base_tokens * multipliers.get(response_type, 1.0))
    
    async def generate_response_stream(
        self, 
        user_input: str,
        persona: Persona,
        context: ConversationContext,
        constraints: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[str, None]:
        """Generate streaming response using the default provider"""
        async for chunk in self.ollama.generate_response_stream(user_input, persona, context, constraints):
            yield chunk
    
    async def generate_response_stream_by_score(
        self, 
        continue_score: int, 
        user_input: str,
        persona: Persona,
        context: ConversationContext
    ) -> AsyncGenerator[tuple[str, str], None]:
        """Generate streaming response based on continue score (yields chunk, response_type)"""
        
        if continue_score >= 80:
            # High engagement: Full streaming LLM with high creativity
            constraints = {"creativity": 0.8, "max_length": 100}
            async for chunk in self.ollama.generate_response_stream(user_input, persona, context, constraints):
                yield chunk, "full_llm"
        
        elif continue_score >= 60:
            # Medium engagement: Standard streaming LLM response
            constraints = {"creativity": 0.6, "max_length": 100}
            async for chunk in self.ollama.generate_response_stream(user_input, persona, context, constraints):
                yield chunk, "full_llm"
        
        elif continue_score >= 40:
            # Low engagement: Constrained streaming response
            constraints = {
                "max_length": 50,
                "style": "concise", 
                "creativity": 0.5,
                "prepare_exit": True
            }
            async for chunk in self.ollama.generate_response_stream(user_input, persona, context, constraints):
                yield chunk, "constrained"
        
        else:
            # Very low engagement: Template response (single chunk)
            template_response = self._generate_template_response(persona, context)
            yield template_response, "template"
    
    async def close(self):
        """Clean up all providers"""
        await self.ollama.close()