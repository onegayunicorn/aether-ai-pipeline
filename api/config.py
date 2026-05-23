"""
Configuration for Aether AI Pipeline API.
Loads settings from environment variables with sensible defaults.
"""

import os
from pathlib import Path
from typing import List, Dict, Any
import json
import logging

logger = logging.getLogger(__name__)


class Config:
    """Configuration class with environment variable support."""
    
    # ============================================================================
    # SOVEREIGN CONFIGURATION
    # ============================================================================
    
    SOVEREIGN_KEY: str = os.getenv(
        "SOVEREIGN_KEY", 
        "generate_new_key_with_python3_c_import_secrets_print_secrets_token_hex_32"
    )
    SOVEREIGN_ARCHITECT: str = os.getenv("SOVEREIGN_ARCHITECT", "Tyrone J Power Ω")
    FOLD_ENTRY: str = os.getenv("FOLD_ENTRY", "FE-OGUF-P1")
    
    # ============================================================================
    # PATH CONFIGURATION
    # ============================================================================
    
    # Base directories
    HOME_DIR: Path = Path.home()
    AETHER_HOME: Path = Path(os.getenv("AETHER_HOME", str(HOME_DIR / "aether-grid")))
    AUTONOMOUS_ORCHESTRATOR: Path = AETHER_HOME / "autonomous-orchestrator"
    PIPELINE_HOME: Path = AETHER_HOME / "ai-pipeline"
    
    # Log and cache directories
    LOG_DIR: Path = PIPELINE_HOME / "logs"
    CACHE_DIR: Path = PIPELINE_HOME / "cache"
    
    # ============================================================================
    # API CONFIGURATION
    # ============================================================================
    
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", 8000))
    API_DEBUG: bool = os.getenv("API_DEBUG", "false").lower() == "true"
    API_RELOAD: bool = os.getenv("API_RELOAD", "false").lower() == "true"
    
    # ============================================================================
    # CORS CONFIGURATION
    # ============================================================================
    
    ALLOWED_ORIGINS: List[str] = json.loads(
        os.getenv(
            "ALLOWED_ORIGINS",
            '["http://localhost:3000", "http://localhost:8000", "http://127.0.0.1:3000", "http://127.0.0.1:8000"]'
        )
    )
    
    # ============================================================================
    # RATE LIMITING
    # ============================================================================
    
    RATE_LIMIT: int = int(os.getenv("RATE_LIMIT", 60))  # requests per minute
    RATE_LIMIT_BURST: int = int(os.getenv("RATE_LIMIT_BURST", 10))
    
    # ============================================================================
    # SECURITY
    # ============================================================================
    
    AUTH_REQUIRED: bool = os.getenv("AUTH_REQUIRED", "true").lower() == "true"
    HTTPS_ENABLED: bool = os.getenv("HTTPS_ENABLED", "false").lower() == "true"
    SSL_CERTFILE: str = os.getenv("SSL_CERTFILE", "")
    SSL_KEYFILE: str = os.getenv("SSL_KEYFILE", "")
    
    # ============================================================================
    # WEB SOCKET
    # ============================================================================
    
    WS_PING_INTERVAL: int = int(os.getenv("WS_PING_INTERVAL", 30))
    WS_MAX_CONNECTIONS: int = int(os.getenv("WS_MAX_CONNECTIONS", 100))
    
    # ============================================================================
    # COMMAND EXECUTION
    # ============================================================================
    
    COMMAND_TIMEOUT: int = int(os.getenv("COMMAND_TIMEOUT", 30))  # seconds
    MAX_CONCURRENT_COMMANDS: int = int(os.getenv("MAX_CONCURRENT_COMMANDS", 10))
    
    # ============================================================================
    # AI INTEGRATION
    # ============================================================================
    
    AI_MAX_PROMPT_LENGTH: int = int(os.getenv("AI_MAX_PROMPT_LENGTH", 1000))
    AI_DEFAULT_MODEL: str = os.getenv("AI_DEFAULT_MODEL", "gpt-4")
    
    # ============================================================================
    # TERMUX/USERLAND DETECTION
    # ============================================================================
    
    IS_TERMUX: bool = os.path.exists("/data/data/com.termux/files")
    IS_USERLAND: bool = os.path.exists("/system/bin/sh")
    
    # ============================================================================
    # INITIALIZATION
    # ============================================================================
    
    @classmethod
    def initialize(cls) -> "Config":
        """Initialize configuration and create necessary directories."""
        # Create directories
        cls.LOG_DIR.mkdir(parents=True, exist_ok=True)
        cls.CACHE_DIR.mkdir(parents=True, exist_ok=True)
        
        # Create .env file if not exists
        env_path = cls.PIPELINE_HOME / ".env"
        if not env_path.exists():
            with open(env_path, "w") as f:
                f.write(f"# Aether AI Pipeline Configuration\n")
                f.write(f"SOVEREIGN_KEY={cls.SOVEREIGN_KEY}\n")
                f.write(f"FOLD_ENTRY={cls.FOLD_ENTRY}\n")
                f.write(f"SOVEREIGN_ARCHITECT={cls.SOVEREIGN_ARCHITECT}\n")
                f.write(f"API_PORT={cls.API_PORT}\n")
            logger.info(f"Created .env file at {env_path}")
        
        # Log configuration
        logger.info("=" * 60)
        logger.info("AETHER AI PIPELINE CONFIGURATION")
        logger.info("=" * 60)
        logger.info(f"Fold Entry: {cls.FOLD_ENTRY}")
        logger.info(f"Sovereign Architect: {cls.SOVEREIGN_ARCHITECT}")
        logger.info(f"API Host: {cls.API_HOST}:{cls.API_PORT}")
        logger.info(f"Autonomous Orchestrator: {cls.AUTONOMOUS_ORCHESTRATOR}")
        logger.info(f"Environment: {'Termux' if cls.IS_TERMUX else 'UserLand' if cls.IS_USERLAND else 'Linux'}")
        logger.info("=" * 60)
        
        return cls
    
    @classmethod
    def validate(cls) -> bool:
        """Validate configuration."""
        errors = []
        
        # Check if Autonomous Orchestrator exists
        if not cls.AUTONOMOUS_ORCHESTRATOR.exists():
            errors.append(f"Autonomous Orchestrator not found at {cls.AUTONOMOUS_ORCHESTRATOR}")
        
        # Check if sovereign key is set (not default)
        if "generate_new_key" in cls.SOVEREIGN_KEY:
            errors.append("SOVEREIGN_KEY is not set. Generate a new key with: python3 -c \"import secrets; print(secrets.token_hex(32))\"")
        
        if errors:
            for error in errors:
                logger.error(error)
            return False
        
        return True


# Initialize and export config
config = Config.initialize()

# Validate configuration
if not Config.validate():
    logger.warning("Configuration validation failed. Some features may not work.")
