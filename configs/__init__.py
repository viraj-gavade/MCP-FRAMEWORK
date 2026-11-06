"""
Security configurations module for MCP Security Research Framework
Phase 2: Security configuration YAML files
"""

from pathlib import Path
from typing import Dict, Any
import yaml

CONFIG_MAP: Dict[str, str] = {
    "config_a": "no_security.yaml",
    "config_b": "basic_security.yaml",
    "config_c": "hardened.yaml",
}


def load_security_config(config_name: str) -> Dict[str, Any]:
    """
    Load security configuration from YAML file with strict validation.
    
    Args:
        config_name: Name of the config (must be exactly 'config_a', 'config_b', or 'config_c')
    
    Returns:
        Dict containing security configuration
        
    Raises:
        ValueError: If config_name is invalid, misspelled, not a string, or unrecognized.
    """
    if not isinstance(config_name, str) or config_name not in CONFIG_MAP:
        valid_options = list(CONFIG_MAP.keys())
        raise ValueError(
            f"Invalid security configuration: '{config_name}'. "
            f"Must be one of: {valid_options}"
        )
    
    config_file = Path(__file__).parent / CONFIG_MAP[config_name]
    with open(config_file, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    return config
