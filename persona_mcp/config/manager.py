"""
Configuration Manager for Persona MCP Server
============================================

Centralized configuration management with environment variable loading,
validation, and type safety for all hardcoded values throughout the system.
"""

import os
import logging
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from enum import Enum
from pathlib import Path

logger = logging.getLogger(__name__)


class DecayMode(Enum):
    """Memory decay modes"""
    LINEAR = "linear"
    EXPONENTIAL = "exponential"
    LOGARITHMIC = "logarithmic"
    ACCESS_BASED = "access_based"


class Priority(Enum):
    """Conversation priority levels"""
    URGENT = "urgent"
    IMPORTANT = "important" 
    CASUAL = "casual"
    SOCIAL = "social"
    ACADEMIC = "academic"
    NONE = "none"


@dataclass
class ServerConfig:
    """Server connection and runtime configuration"""
    host: str = "localhost"
    port: int = 8000
    debug_mode: bool = False
    websocket_timeout: int = 300
    max_connections: int = 100


@dataclass
class OllamaConfig:
    """Ollama LLM provider configuration"""
    host: str = "http://localhost:11434"
    default_model: str = "llama3.1:8b"
    timeout_seconds: int = 60
    max_retries: int = 3
    request_timeout: int = 120


@dataclass
class SessionConfig:
    """Session and conversation management configuration"""
    max_context_messages: int = 20
    context_summary_threshold: int = 50
    session_timeout_hours: int = 24
    tick_interval_seconds: int = 30
    max_concurrent_conversations: int = 5


@dataclass
class MemoryConfig:
    """Memory system configuration"""
    # Importance scoring thresholds
    importance_min: float = 0.51
    importance_max: float = 0.80
    importance_threshold: float = 0.6
    
    # Scoring weights (must sum to 1.0)
    content_weight: float = 0.3
    engagement_weight: float = 0.2
    persona_weight: float = 0.15
    temporal_weight: float = 0.05
    relationship_weight: float = 0.1
    recency_weight: float = 0.2  # Increased to make total = 1.0
    
    # Pruning configuration
    min_safe_count: int = 10
    max_prune_percent: float = 0.25
    prune_batch_size: int = 5
    max_memories_per_persona: int = 1000
    pruning_threshold: int = 900
    
    # Decay system configuration
    decay_mode: DecayMode = DecayMode.EXPONENTIAL
    decay_rate: float = 0.1
    decay_interval_minutes: int = 60
    decay_min_importance: float = 0.1
    decay_enabled: bool = True
    
    # Auto-pruning triggers
    enable_auto_pruning: bool = True
    auto_prune_threshold: int = 1000
    auto_prune_importance_threshold: float = 0.3
    
    # Performance settings
    batch_size: int = 50
    async_processing: bool = True
    connection_pool_size: int = 5
    max_personas_per_cycle: int = 5
    max_memories_per_batch: int = 100


@dataclass
class PersonaConfig:
    """Default persona configuration values"""
    # Default personality trait ranges
    default_charisma: int = 10
    default_intelligence: int = 10
    default_social_rank: str = "commoner"
    
    # Interaction state defaults
    default_interest_level: int = 50
    default_interaction_fatigue: int = 0
    default_available_time: int = 300  # 5 minutes
    default_social_energy: int = 100
    default_cooldown_seconds: int = 300  # 5 minutes
    
    # Scoring thresholds
    continue_threshold: int = 40
    high_continue_score: int = 70
    low_continue_score: int = 30
    
    # Resource constraints
    min_time_threshold: int = 60  # 1 minute
    low_token_budget: int = 100
    low_social_energy: int = 30
    
    # Cooldown multipliers
    satisfying_conversation_multiplier: float = 0.5
    unsatisfying_conversation_multiplier: float = 2.0
    base_cooldown_seconds: int = 300


@dataclass
class ConversationConfig:
    """Conversation scoring and dynamics configuration"""
    # Continue score components (0-100 scale)
    max_time_score: float = 30.0
    max_topic_score: float = 25.0
    max_social_score: float = 20.0
    max_resource_score: float = 10.0
    max_fatigue_penalty: float = 15.0
    max_history_modifier: float = 15.0
    
    # Time pressure decay rates (seconds)
    urgent_decay_rate: float = 2.0
    important_decay_rate: float = 10.0
    casual_decay_rate: float = 30.0
    
    # Status hierarchy values
    status_hierarchy: Dict[str, int] = field(default_factory=lambda: {
        "royalty": 5,
        "nobility": 4,
        "merchant": 3,
        "commoner": 2,
        "peasant": 1
    })
    
    # Compatibility scoring
    same_status_compatibility: float = 8.0
    adjacent_status_compatibility: float = 6.0
    distant_status_compatibility: float = 2.0
    default_status_compatibility: float = 4.0
    large_status_gap_threshold: int = 3


@dataclass
class DatabaseConfig:
    """Database and storage configuration"""
    sqlite_path: str = "data/persona_memory.db"
    chromadb_path: str = "data/chromadb"
    enable_wal_mode: bool = True
    connection_timeout: int = 30
    backup_interval_hours: int = 24


@dataclass
class SimulationConfig:
    """Chatroom simulation configuration"""
    room_name: str = "The Debug Tavern"
    room_description: str = "A cozy virtual tavern for testing persona interactions"
    default_topics: List[str] = field(default_factory=lambda: [
        "gossip", "travel", "magic", "stories", "local_news"
    ])
    energy_regen_rate: int = 2
    max_concurrent_conversations: int = 3


class ConfigManager:
    """
    Centralized configuration manager with environment variable loading
    and runtime validation for all system settings.
    """
    
    def __init__(self, env_file_path: Optional[str] = None):
        """
        Initialize configuration manager.
        
        Args:
            env_file_path: Optional path to .env file for loading environment variables
        """
        self._load_env_file(env_file_path)
        
        # Initialize all configuration sections
        self.server = self._load_server_config()
        self.ollama = self._load_ollama_config()
        self.session = self._load_session_config()
        self.memory = self._load_memory_config()
        self.persona = self._load_persona_config()
        self.conversation = self._load_conversation_config()
        self.database = self._load_database_config()
        self.simulation = self._load_simulation_config()
        
        # Validate configuration after loading
        self._validate_configuration()
        
        logger.info("Configuration loaded and validated successfully")
    
    def _load_env_file(self, env_file_path: Optional[str]) -> None:
        """Load environment variables from .env file if it exists"""
        if env_file_path:
            env_path = Path(env_file_path)
        else:
            env_path = Path(".env")
        
        if env_path.exists():
            with open(env_path) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        key, _, value = line.partition('=')
                        os.environ[key.strip()] = value.strip()
            logger.info(f"Loaded environment variables from {env_path}")
    
    def _get_env_bool(self, key: str, default: bool) -> bool:
        """Get boolean environment variable with proper conversion"""
        value = os.getenv(key, str(default)).lower()
        return value in ('true', '1', 'yes', 'on')
    
    def _get_env_int(self, key: str, default: int) -> int:
        """Get integer environment variable with validation"""
        try:
            return int(os.getenv(key, str(default)))
        except ValueError:
            logger.warning(f"Invalid integer value for {key}, using default: {default}")
            return default
    
    def _get_env_float(self, key: str, default: float) -> float:
        """Get float environment variable with validation"""
        try:
            return float(os.getenv(key, str(default)))
        except ValueError:
            logger.warning(f"Invalid float value for {key}, using default: {default}")
            return default
    
    def _load_server_config(self) -> ServerConfig:
        """Load server configuration from environment variables"""
        return ServerConfig(
            host=os.getenv("SERVER_HOST", "localhost"),
            port=self._get_env_int("SERVER_PORT", 8000),
            debug_mode=self._get_env_bool("DEBUG_MODE", False),
            websocket_timeout=self._get_env_int("WEBSOCKET_TIMEOUT", 300),
            max_connections=self._get_env_int("MAX_CONNECTIONS", 100)
        )
    
    def _load_ollama_config(self) -> OllamaConfig:
        """Load Ollama configuration from environment variables"""
        return OllamaConfig(
            host=os.getenv("OLLAMA_HOST", "http://localhost:11434"),
            default_model=os.getenv("DEFAULT_MODEL", "llama3.1:8b"),
            timeout_seconds=self._get_env_int("OLLAMA_TIMEOUT", 60),
            max_retries=self._get_env_int("OLLAMA_MAX_RETRIES", 3),
            request_timeout=self._get_env_int("OLLAMA_REQUEST_TIMEOUT", 120)
        )
    
    def _load_session_config(self) -> SessionConfig:
        """Load session configuration from environment variables"""
        return SessionConfig(
            max_context_messages=self._get_env_int("MAX_CONTEXT_MESSAGES", 20),
            context_summary_threshold=self._get_env_int("CONTEXT_SUMMARY_THRESHOLD", 50),
            session_timeout_hours=self._get_env_int("SESSION_TIMEOUT_HOURS", 24),
            tick_interval_seconds=self._get_env_int("TICK_INTERVAL_SECONDS", 30),
            max_concurrent_conversations=self._get_env_int("MAX_CONCURRENT_CONVERSATIONS", 5)
        )
    
    def _load_memory_config(self) -> MemoryConfig:
        """Load memory system configuration from environment variables"""
        decay_mode_str = os.getenv("MEMORY_DECAY_MODE", "exponential").lower()
        try:
            decay_mode = DecayMode(decay_mode_str)
        except ValueError:
            logger.warning(f"Invalid decay mode '{decay_mode_str}', using exponential")
            decay_mode = DecayMode.EXPONENTIAL
        
        return MemoryConfig(
            importance_min=self._get_env_float("MEMORY_IMPORTANCE_MIN", 0.51),
            importance_max=self._get_env_float("MEMORY_IMPORTANCE_MAX", 0.80),
            importance_threshold=self._get_env_float("MEMORY_IMPORTANCE_THRESHOLD", 0.6),
            content_weight=self._get_env_float("MEMORY_CONTENT_WEIGHT", 0.3),
            engagement_weight=self._get_env_float("MEMORY_ENGAGEMENT_WEIGHT", 0.2),
            persona_weight=self._get_env_float("MEMORY_PERSONA_WEIGHT", 0.15),
            temporal_weight=self._get_env_float("MEMORY_TEMPORAL_WEIGHT", 0.05),
            relationship_weight=self._get_env_float("MEMORY_RELATIONSHIP_WEIGHT", 0.1),
            recency_weight=self._get_env_float("MEMORY_RECENCY_WEIGHT", 0.05),
            min_safe_count=self._get_env_int("MEMORY_MIN_SAFE_COUNT", 10),
            max_prune_percent=self._get_env_float("MEMORY_MAX_PRUNE_PERCENT", 0.25),
            prune_batch_size=self._get_env_int("MEMORY_PRUNE_BATCH_SIZE", 5),
            max_memories_per_persona=self._get_env_int("MAX_MEMORIES_PER_PERSONA", 1000),
            pruning_threshold=self._get_env_int("PRUNING_THRESHOLD", 900),
            decay_mode=decay_mode,
            decay_rate=self._get_env_float("MEMORY_DECAY_RATE", 0.1),
            decay_interval_minutes=self._get_env_int("MEMORY_DECAY_INTERVAL_MINUTES", 60),
            decay_min_importance=self._get_env_float("MEMORY_DECAY_MIN_IMPORTANCE", 0.1),
            decay_enabled=self._get_env_bool("MEMORY_DECAY_ENABLED", True),
            enable_auto_pruning=self._get_env_bool("MEMORY_ENABLE_AUTO_PRUNING", True),
            auto_prune_threshold=self._get_env_int("MEMORY_AUTO_PRUNE_THRESHOLD", 1000),
            auto_prune_importance_threshold=self._get_env_float("MEMORY_AUTO_PRUNE_IMPORTANCE_THRESHOLD", 0.3),
            batch_size=self._get_env_int("MEMORY_BATCH_SIZE", 50),
            async_processing=self._get_env_bool("MEMORY_ASYNC_PROCESSING", True),
            connection_pool_size=self._get_env_int("MEMORY_CONNECTION_POOL_SIZE", 5),
            max_personas_per_cycle=self._get_env_int("MEMORY_MAX_PERSONAS_PER_CYCLE", 5),
            max_memories_per_batch=self._get_env_int("MEMORY_MAX_MEMORIES_PER_BATCH", 100)
        )
    
    def _load_persona_config(self) -> PersonaConfig:
        """Load persona configuration from environment variables"""
        return PersonaConfig(
            default_charisma=self._get_env_int("PERSONA_DEFAULT_CHARISMA", 10),
            default_intelligence=self._get_env_int("PERSONA_DEFAULT_INTELLIGENCE", 10),
            default_social_rank=os.getenv("PERSONA_DEFAULT_SOCIAL_RANK", "commoner"),
            default_interest_level=self._get_env_int("PERSONA_DEFAULT_INTEREST_LEVEL", 50),
            default_interaction_fatigue=self._get_env_int("PERSONA_DEFAULT_INTERACTION_FATIGUE", 0),
            default_available_time=self._get_env_int("PERSONA_DEFAULT_AVAILABLE_TIME", 300),
            default_social_energy=self._get_env_int("PERSONA_DEFAULT_SOCIAL_ENERGY", 100),
            default_cooldown_seconds=self._get_env_int("PERSONA_DEFAULT_COOLDOWN_SECONDS", 300),
            continue_threshold=self._get_env_int("PERSONA_CONTINUE_THRESHOLD", 40),
            high_continue_score=self._get_env_int("PERSONA_HIGH_CONTINUE_SCORE", 70),
            low_continue_score=self._get_env_int("PERSONA_LOW_CONTINUE_SCORE", 30),
            min_time_threshold=self._get_env_int("PERSONA_MIN_TIME_THRESHOLD", 60),
            low_token_budget=self._get_env_int("PERSONA_LOW_TOKEN_BUDGET", 100),
            low_social_energy=self._get_env_int("PERSONA_LOW_SOCIAL_ENERGY", 30),
            satisfying_conversation_multiplier=self._get_env_float("PERSONA_SATISFYING_MULTIPLIER", 0.5),
            unsatisfying_conversation_multiplier=self._get_env_float("PERSONA_UNSATISFYING_MULTIPLIER", 2.0),
            base_cooldown_seconds=self._get_env_int("PERSONA_BASE_COOLDOWN_SECONDS", 300)
        )
    
    def _load_conversation_config(self) -> ConversationConfig:
        """Load conversation configuration from environment variables"""
        return ConversationConfig(
            max_time_score=self._get_env_float("CONVERSATION_MAX_TIME_SCORE", 30.0),
            max_topic_score=self._get_env_float("CONVERSATION_MAX_TOPIC_SCORE", 25.0),
            max_social_score=self._get_env_float("CONVERSATION_MAX_SOCIAL_SCORE", 20.0),
            max_resource_score=self._get_env_float("CONVERSATION_MAX_RESOURCE_SCORE", 10.0),
            max_fatigue_penalty=self._get_env_float("CONVERSATION_MAX_FATIGUE_PENALTY", 15.0),
            max_history_modifier=self._get_env_float("CONVERSATION_MAX_HISTORY_MODIFIER", 15.0),
            urgent_decay_rate=self._get_env_float("CONVERSATION_URGENT_DECAY_RATE", 2.0),
            important_decay_rate=self._get_env_float("CONVERSATION_IMPORTANT_DECAY_RATE", 10.0),
            casual_decay_rate=self._get_env_float("CONVERSATION_CASUAL_DECAY_RATE", 30.0),
            same_status_compatibility=self._get_env_float("CONVERSATION_SAME_STATUS_COMPATIBILITY", 8.0),
            adjacent_status_compatibility=self._get_env_float("CONVERSATION_ADJACENT_STATUS_COMPATIBILITY", 6.0),
            distant_status_compatibility=self._get_env_float("CONVERSATION_DISTANT_STATUS_COMPATIBILITY", 2.0),
            default_status_compatibility=self._get_env_float("CONVERSATION_DEFAULT_STATUS_COMPATIBILITY", 4.0),
            large_status_gap_threshold=self._get_env_int("CONVERSATION_LARGE_STATUS_GAP_THRESHOLD", 3)
        )
    
    def _load_database_config(self) -> DatabaseConfig:
        """Load database configuration from environment variables"""
        return DatabaseConfig(
            sqlite_path=os.getenv("DATABASE_PATH", "data/persona_memory.db"),
            chromadb_path=os.getenv("CHROMADB_PATH", "data/chromadb"),
            enable_wal_mode=self._get_env_bool("DATABASE_ENABLE_WAL_MODE", True),
            connection_timeout=self._get_env_int("DATABASE_CONNECTION_TIMEOUT", 30),
            backup_interval_hours=self._get_env_int("DATABASE_BACKUP_INTERVAL_HOURS", 24)
        )
    
    def _load_simulation_config(self) -> SimulationConfig:
        """Load simulation configuration from environment variables"""
        default_topics = ["gossip", "travel", "magic", "stories", "local_news"]
        topics_str = os.getenv("SIMULATION_DEFAULT_TOPICS")
        if topics_str:
            default_topics = [topic.strip() for topic in topics_str.split(",")]
        
        return SimulationConfig(
            room_name=os.getenv("SIMULATION_ROOM_NAME", "The Debug Tavern"),
            room_description=os.getenv("SIMULATION_ROOM_DESCRIPTION", 
                                     "A cozy virtual tavern for testing persona interactions"),
            default_topics=default_topics,
            energy_regen_rate=self._get_env_int("SIMULATION_ENERGY_REGEN_RATE", 2),
            max_concurrent_conversations=self._get_env_int("SIMULATION_MAX_CONCURRENT_CONVERSATIONS", 3)
        )
    
    def _validate_configuration(self) -> None:
        """Validate configuration values for consistency and ranges"""
        errors = []
        
        # Validate memory weights sum to approximately 1.0
        total_weights = (
            self.memory.content_weight + 
            self.memory.engagement_weight + 
            self.memory.persona_weight + 
            self.memory.temporal_weight + 
            self.memory.relationship_weight + 
            self.memory.recency_weight
        )
        if abs(total_weights - 1.0) > 0.01:
            errors.append(f"Memory scoring weights sum to {total_weights:.3f}, should be 1.0")
        
        # Validate importance ranges
        if self.memory.importance_min >= self.memory.importance_max:
            errors.append("Memory importance_min must be less than importance_max")
        
        if not (0.0 <= self.memory.importance_threshold <= 1.0):
            errors.append("Memory importance_threshold must be between 0.0 and 1.0")
        
        # Validate pruning percentages
        if not (0.0 < self.memory.max_prune_percent <= 1.0):
            errors.append("Memory max_prune_percent must be between 0.0 and 1.0")
        
        # Validate persona thresholds
        if self.persona.continue_threshold < 0 or self.persona.continue_threshold > 100:
            errors.append("Persona continue_threshold must be between 0 and 100")
        
        # Validate server port range
        if not (1 <= self.server.port <= 65535):
            errors.append("Server port must be between 1 and 65535")
        
        if errors:
            error_msg = "Configuration validation failed:\n" + "\n".join(f"  - {error}" for error in errors)
            logger.error(error_msg)
            raise ValueError(error_msg)
    
    def get_summary(self) -> Dict[str, Any]:
        """Get configuration summary for logging and debugging"""
        return {
            "server": {
                "host": self.server.host,
                "port": self.server.port,
                "debug_mode": self.server.debug_mode
            },
            "ollama": {
                "host": self.ollama.host,
                "default_model": self.ollama.default_model
            },
            "memory": {
                "importance_range": f"{self.memory.importance_min}-{self.memory.importance_max}",
                "decay_mode": self.memory.decay_mode.value,
                "max_memories": self.memory.max_memories_per_persona
            },
            "session": {
                "max_context_messages": self.session.max_context_messages,
                "timeout_hours": self.session.session_timeout_hours
            }
        }


# Global configuration instance (initialized on first import)
_config_instance: Optional[ConfigManager] = None


def get_config() -> ConfigManager:
    """
    Get the global configuration instance.
    
    Returns:
        ConfigManager: The global configuration instance
    """
    global _config_instance
    if _config_instance is None:
        _config_instance = ConfigManager()
    return _config_instance


def init_config(env_file_path: Optional[str] = None) -> ConfigManager:
    """
    Initialize the global configuration instance with custom env file.
    
    Args:
        env_file_path: Optional path to .env file
        
    Returns:
        ConfigManager: The initialized configuration instance
    """
    global _config_instance
    _config_instance = ConfigManager(env_file_path)
    return _config_instance