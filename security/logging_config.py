"""
Logging Configuration Module
Phase 2: Configurable logging levels for security events
"""

import logging
from typing import Dict, Any

# Logging level mapping
LOGGING_LEVELS = {
    "basic": logging.INFO,
    "standard": logging.INFO,
    "verbose": logging.DEBUG
}


def configure_logging(security_config: Dict[str, Any]) -> None:
    """
    Configure logging level based on security configuration.
    
    Args:
        security_config: Security configuration dictionary
    """
    logging_level_name = security_config.get("logging", "basic")
    logging_level = LOGGING_LEVELS.get(logging_level_name, logging.INFO)
    
    logging.basicConfig(
        level=logging_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def get_logging_level(security_config: Dict[str, Any]) -> int:
    """
    Get the logging level for the given security configuration.
    
    Args:
        security_config: Security configuration dictionary
    
    Returns:
        Logging level constant (e.g., logging.INFO, logging.DEBUG)
    """
    logging_level_name = security_config.get("logging", "basic")
    return LOGGING_LEVELS.get(logging_level_name, logging.INFO)
