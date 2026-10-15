"""
Authentication Module
Phase 2: API key-based authentication for the multi-agent system

This module provides authentication checks to verify that requests
are authorized before allowing pipeline execution.

Authentication Mechanism:
- Config A: authentication disabled (no check)
- Config B/C: authentication enabled
- When enabled, presented credential (passed as auth_token or via AUTH_TOKEN env var)
  must match the expected secret (configured via expected_auth_secret, e.g. $AUTH_SECRET).
- Expected secret is specified in YAML config as either:
  - An environment variable name (recommended, prefixed with $, e.g. $AUTH_SECRET)
  - A direct value (supported for testing)
- Self-referential configuration (e.g. expected_auth_secret pointing to $AUTH_TOKEN)
  is rejected to prevent accepting arbitrary credentials.
- Credential comparison uses hmac.compare_digest to prevent timing attacks.
"""

import hmac
import logging
import os
from typing import Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)


def _get_expected_secret(expected_secret_config: Optional[str]) -> Optional[str]:
    """
    Resolve the expected secret from configuration.
    
    Args:
        expected_secret_config: Either a direct secret value or an env var name prefixed with $
    
    Returns:
        The expected secret value, or None if not found or invalid
    """
    if not expected_secret_config:
        return None
    
    # If prefixed with $, treat as environment variable name
    if expected_secret_config.startswith("$"):
        env_var_name = expected_secret_config[1:].strip()
        # Self-referential configuration with client token variable is disallowed
        if env_var_name == "AUTH_TOKEN":
            logger.error("Authentication configuration error: expected_auth_secret cannot reference '$AUTH_TOKEN'")
            return None
        return os.getenv(env_var_name)
    
    # Otherwise, treat as direct value
    return expected_secret_config


def check_authentication(
    security_config: Dict[str, Any],
    auth_token: Optional[str] = None
) -> Tuple[bool, Optional[str]]:
    """
    Check if authentication is required and verify credentials.
    
    Args:
        security_config: Security configuration dictionary
        auth_token: Optional supplied authentication credential.
                    If not provided, falls back to the AUTH_TOKEN environment variable.
    
    Returns:
        Tuple of (authenticated: bool, error_message: Optional[str])
    """
    # Check if authentication is enabled in configuration
    auth_enabled = security_config.get("authentication", False)
    
    if not auth_enabled:
        logger.info("Authentication disabled by configuration")
        return True, None
    
    # Authentication is enabled - get expected secret configuration
    expected_secret_config = security_config.get("expected_auth_secret")
    if not expected_secret_config:
        logger.warning("Authentication enabled but expected secret not configured")
        return False, "Authentication failed: expected secret not configured"
    
    if expected_secret_config == "$AUTH_TOKEN":
        logger.warning("Authentication configuration error: expected_auth_secret cannot be '$AUTH_TOKEN'")
        return False, "Authentication failed: invalid expected secret configuration"
    
    expected_secret = _get_expected_secret(expected_secret_config)
    if not expected_secret or not expected_secret.strip():
        logger.warning("Authentication enabled but expected secret not configured")
        return False, "Authentication failed: expected secret not configured"
    
    # Get the supplied credential (parameter takes precedence over environment variable)
    supplied_token = auth_token if auth_token is not None else os.getenv("AUTH_TOKEN")
    
    if supplied_token is None:
        logger.warning("Authentication required: missing credential")
        return False, "Authentication required: missing credential (AUTH_TOKEN not set)"
    
    # Validate token format: credential must not be empty or whitespace only
    if not supplied_token.strip():
        logger.warning("Authentication failed: empty credential")
        return False, "Authentication failed: empty credential"
    
    # Compare supplied credential against expected secret using constant-time comparison
    if not hmac.compare_digest(supplied_token, expected_secret):
        logger.warning("Authentication failed: invalid credential")
        return False, "Authentication failed: invalid credential"
    
    logger.info("Authentication successful")
    return True, None


def get_authentication_status(
    security_config: Dict[str, Any],
    auth_token: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get the current authentication status for logging/metrics.
    
    Args:
        security_config: Security configuration dictionary
        auth_token: Optional supplied authentication token
    
    Returns:
        Dictionary with authentication status information
    """
    auth_enabled = security_config.get("authentication", False)
    token = auth_token if auth_token is not None else os.getenv("AUTH_TOKEN")
    auth_token_present = bool(token and token.strip())
    
    return {
        "authentication_enabled": auth_enabled,
        "authentication_token_present": auth_token_present,
        "authentication_enforced": auth_enabled and auth_token_present
    }
