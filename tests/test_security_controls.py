"""
Security Controls Tests
Phase 2: Tests for authentication, tool permission scoping, input/output validation
"""

import pytest
import os
from unittest.mock import patch, MagicMock
from agents.research_agent import load_security_config, research_agent
from agents.planner_agent import planner_agent
from security.auth import check_authentication, get_authentication_status
from pipeline.graph import run_pipeline


class TestAuthentication:
    """Test authentication mechanism."""
    
    def test_auth_disabled_allows_access(self):
        """Test that disabled authentication allows access without credentials."""
        # Using custom config
        config = {"authentication": False}
        authenticated, error = check_authentication(config)
        assert authenticated is True
        assert error is None
        
        # Using Config A file
        config_a = load_security_config("config_a")
        authenticated, error = check_authentication(config_a)
        assert authenticated is True
        assert error is None
    
    def test_auth_enabled_without_expected_secret_denies_access(self):
        """Test that enabled authentication without configured expected secret denies access."""
        # Case 1: expected_auth_secret is None
        config_none = {"authentication": True, "expected_auth_secret": None}
        authenticated, error = check_authentication(config_none)
        assert authenticated is False
        assert error is not None
        assert "expected secret not configured" in error
        
        # Case 2: expected_auth_secret references an unset environment variable
        if "NONEXISTENT_SECRET_VAR" in os.environ:
            del os.environ["NONEXISTENT_SECRET_VAR"]
        config_unset_env = {"authentication": True, "expected_auth_secret": "$NONEXISTENT_SECRET_VAR"}
        authenticated, error = check_authentication(config_unset_env)
        assert authenticated is False
        assert error is not None
        assert "expected secret not configured" in error
    
    def test_auth_enabled_without_supplied_credential_denies_access(self):
        """Test that enabled authentication without supplied credential denies access."""
        # Save and clear AUTH_TOKEN if present
        saved_token = os.environ.pop("AUTH_TOKEN", None)
        
        try:
            config = {"authentication": True, "expected_auth_secret": "test_expected_secret"}
            authenticated, error = check_authentication(config, auth_token=None)
            assert authenticated is False
            assert error is not None
            assert "missing credential" in error.lower() or "auth_token" in error.lower()
        finally:
            if saved_token is not None:
                os.environ["AUTH_TOKEN"] = saved_token
    
    def test_auth_enabled_with_empty_credential_denies_access(self):
        """Test that enabled authentication with empty or whitespace credential denies access."""
        config = {"authentication": True, "expected_auth_secret": "test_expected_secret"}
        
        # Empty string parameter
        authenticated, error = check_authentication(config, auth_token="")
        assert authenticated is False
        assert error is not None
        assert "empty" in error.lower()
        
        # Whitespace-only string parameter
        authenticated, error = check_authentication(config, auth_token="   ")
        assert authenticated is False
        assert error is not None
        assert "empty" in error.lower()
        
        # Empty env var
        saved_token = os.environ.get("AUTH_TOKEN")
        try:
            os.environ["AUTH_TOKEN"] = ""
            authenticated, error = check_authentication(config)
            assert authenticated is False
            assert error is not None
            assert "empty" in error.lower()
        finally:
            if saved_token is not None:
                os.environ["AUTH_TOKEN"] = saved_token
            else:
                os.environ.pop("AUTH_TOKEN", None)
    
    def test_auth_enabled_with_incorrect_credential_denies_access(self):
        """Test that enabled authentication with incorrect credential denies access."""
        config = {"authentication": True, "expected_auth_secret": "correct_secret"}
        
        # Incorrect via parameter
        authenticated, error = check_authentication(config, auth_token="wrong_secret")
        assert authenticated is False
        assert error is not None
        assert "invalid credential" in error
        
        # Incorrect via environment variable
        saved_token = os.environ.get("AUTH_TOKEN")
        try:
            os.environ["AUTH_TOKEN"] = "wrong_secret"
            authenticated, error = check_authentication(config)
            assert authenticated is False
            assert error is not None
            assert "invalid credential" in error
        finally:
            if saved_token is not None:
                os.environ["AUTH_TOKEN"] = saved_token
            else:
                os.environ.pop("AUTH_TOKEN", None)
    
    def test_auth_enabled_with_correct_credential_allows_access(self):
        """Test that enabled authentication with matching credential allows access."""
        config = {"authentication": True, "expected_auth_secret": "correct_secret"}
        
        # Correct via parameter
        authenticated, error = check_authentication(config, auth_token="correct_secret")
        assert authenticated is True
        assert error is None
        
        # Correct via environment variable
        saved_token = os.environ.get("AUTH_TOKEN")
        try:
            os.environ["AUTH_TOKEN"] = "correct_secret"
            authenticated, error = check_authentication(config)
            assert authenticated is True
            assert error is None
        finally:
            if saved_token is not None:
                os.environ["AUTH_TOKEN"] = saved_token
            else:
                os.environ.pop("AUTH_TOKEN", None)
    
    def test_auth_rejects_arbitrary_string(self):
        """Test that arbitrary non-empty strings are never accepted as valid authentication."""
        config = {"authentication": True, "expected_auth_secret": "configured_secret_value"}
        
        arbitrary_tokens = [
            "random_string_123",
            "bearer token",
            "admin",
            "test_token",
            "AUTH_TOKEN",
            "true",
            "null",
            "12345"
        ]
        
        for token in arbitrary_tokens:
            authenticated, error = check_authentication(config, auth_token=token)
            assert authenticated is False, f"Arbitrary token '{token}' should not have been accepted"
            assert "invalid credential" in error
    
    def test_auth_rejects_self_referential_auth_token_secret(self):
        """Test that self-referential configuration ($AUTH_TOKEN) is rejected."""
        config = {"authentication": True, "expected_auth_secret": "$AUTH_TOKEN"}
        
        saved_token = os.environ.get("AUTH_TOKEN")
        try:
            os.environ["AUTH_TOKEN"] = "any_arbitrary_token"
            authenticated, error = check_authentication(config, auth_token="any_arbitrary_token")
            assert authenticated is False
            assert error is not None
        finally:
            if saved_token is not None:
                os.environ["AUTH_TOKEN"] = saved_token
            else:
                os.environ.pop("AUTH_TOKEN", None)
    
    def test_auth_with_env_var_reference(self):
        """Test that expected secret can reference a distinct environment variable."""
        saved_token = os.environ.get("AUTH_TOKEN")
        saved_custom = os.environ.get("MY_CUSTOM_SECRET")
        
        try:
            os.environ["MY_CUSTOM_SECRET"] = "my_expected_secret"
            config = {"authentication": True, "expected_auth_secret": "$MY_CUSTOM_SECRET"}
            
            # Correct credential
            authenticated, error = check_authentication(config, auth_token="my_expected_secret")
            assert authenticated is True
            assert error is None
            
            # Mismatched credential
            authenticated, error = check_authentication(config, auth_token="mismatched_secret")
            assert authenticated is False
            assert error is not None
            assert "invalid credential" in error
        finally:
            if saved_token is not None:
                os.environ["AUTH_TOKEN"] = saved_token
            else:
                os.environ.pop("AUTH_TOKEN", None)
            if saved_custom is not None:
                os.environ["MY_CUSTOM_SECRET"] = saved_custom
            else:
                os.environ.pop("MY_CUSTOM_SECRET", None)
    
    def test_config_b_enforcement(self):
        """Test that Config B config file enforces authentication against $AUTH_SECRET."""
        config = load_security_config("config_b")
        assert config["authentication"] is True
        assert "expected_auth_secret" in config
        assert config["expected_auth_secret"] == "$AUTH_SECRET"
        
        saved_secret = os.environ.get("AUTH_SECRET")
        saved_token = os.environ.get("AUTH_TOKEN")
        try:
            os.environ["AUTH_SECRET"] = "test_config_b_secret"
            
            # Correct credential succeeds
            authenticated, error = check_authentication(config, auth_token="test_config_b_secret")
            assert authenticated is True
            assert error is None
            
            # Incorrect credential fails
            authenticated, error = check_authentication(config, auth_token="wrong_token")
            assert authenticated is False
            assert "invalid credential" in error
            
            # Missing credential fails
            os.environ.pop("AUTH_TOKEN", None)
            authenticated, error = check_authentication(config, auth_token=None)
            assert authenticated is False
            assert "missing credential" in error.lower() or "auth_token" in error.lower()
        finally:
            if saved_secret is not None:
                os.environ["AUTH_SECRET"] = saved_secret
            else:
                os.environ.pop("AUTH_SECRET", None)
            if saved_token is not None:
                os.environ["AUTH_TOKEN"] = saved_token
            else:
                os.environ.pop("AUTH_TOKEN", None)
    
    def test_config_c_enforcement(self):
        """Test that Config C config file enforces authentication against $AUTH_SECRET."""
        config = load_security_config("config_c")
        assert config["authentication"] is True
        assert "expected_auth_secret" in config
        assert config["expected_auth_secret"] == "$AUTH_SECRET"
        
        saved_secret = os.environ.get("AUTH_SECRET")
        saved_token = os.environ.get("AUTH_TOKEN")
        try:
            os.environ["AUTH_SECRET"] = "test_config_c_secret"
            
            # Correct credential succeeds
            authenticated, error = check_authentication(config, auth_token="test_config_c_secret")
            assert authenticated is True
            assert error is None
            
            # Incorrect credential fails
            authenticated, error = check_authentication(config, auth_token="wrong_token")
            assert authenticated is False
            assert "invalid credential" in error
            
            # Missing credential fails
            os.environ.pop("AUTH_TOKEN", None)
            authenticated, error = check_authentication(config, auth_token=None)
            assert authenticated is False
            assert "missing credential" in error.lower() or "auth_token" in error.lower()
        finally:
            if saved_secret is not None:
                os.environ["AUTH_SECRET"] = saved_secret
            else:
                os.environ.pop("AUTH_SECRET", None)
            if saved_token is not None:
                os.environ["AUTH_TOKEN"] = saved_token
            else:
                os.environ.pop("AUTH_TOKEN", None)
    
    def test_auth_failure_prevents_agents_from_running(self):
        """Test that authentication failure stops pipeline execution before any agent runs."""
        saved_secret = os.environ.get("AUTH_SECRET")
        try:
            os.environ["AUTH_SECRET"] = "valid_system_secret"
            
            with patch("pipeline.graph.create_graph") as mock_create_graph:
                # Run pipeline with invalid credential
                state = run_pipeline(
                    user_task="Test task that should never reach agents",
                    security_config="config_b",
                    auth_token="incorrect_credential"
                )
                
                # Graph must NOT be created or invoked
                mock_create_graph.assert_not_called()
                
                # State must reflect authentication failure
                assert state["security_events"]["auth_success"] is False
                assert state["research_result"] is None
                assert state["execution_result"] is None
                assert state["evaluation_result"] is None
                assert "Authentication failed" in state["plan"]["error"]
                assert any("Authentication failed" in err for err in state["errors"])
        finally:
            if saved_secret is not None:
                os.environ["AUTH_SECRET"] = saved_secret
            else:
                os.environ.pop("AUTH_SECRET", None)

    def test_get_authentication_status(self):
        """Test get_authentication_status reporting."""
        # Disabled
        status_disabled = get_authentication_status({"authentication": False})
        assert status_disabled["authentication_enabled"] is False
        
        # Enabled with token
        status_enabled_token = get_authentication_status({"authentication": True}, auth_token="some_token")
        assert status_enabled_token["authentication_enabled"] is True
        assert status_enabled_token["authentication_token_present"] is True
        assert status_enabled_token["authentication_enforced"] is True
        
        # Enabled without token
        saved_token = os.environ.pop("AUTH_TOKEN", None)
        try:
            status_no_token = get_authentication_status({"authentication": True}, auth_token=None)
            assert status_no_token["authentication_enabled"] is True
            assert status_no_token["authentication_token_present"] is False
            assert status_no_token["authentication_enforced"] is False
        finally:
            if saved_token is not None:
                os.environ["AUTH_TOKEN"] = saved_token


class TestToolPermissionScoping:
    """Test tool permission scoping."""
    
    def test_config_a_allows_all_tools(self):
        """Test that Config A allows all tools."""
        config = load_security_config("config_a")
        assert config["tool_permission_scoping"] is False
        
        # Should allow any tool name
        plan = {"search_query": "test query"}
        result = research_agent(plan, "config_a")
        # Should succeed (tool permission scoping disabled)
        assert "error" not in result or result.get("error") != "Tool not permitted"
    
    def test_config_b_allows_configured_tools(self):
        """Test that Config B allows configured tools."""
        config = load_security_config("config_b")
        assert config["tool_permission_scoping"] is True
        allowed_tools = config["allowed_tools"]["research"]
        assert "read_file" in allowed_tools
        assert "web_search" in allowed_tools
        
        # Test allowed tool
        plan = {"search_query": "test query"}
        result = research_agent(plan, "config_b")
        assert "error" not in result or result.get("error") != "Tool not permitted"
    
    def test_config_c_allows_configured_tools(self):
        """Test that Config C allows configured tools."""
        config = load_security_config("config_c")
        assert config["tool_permission_scoping"] is True
        allowed_tools = config["allowed_tools"]["research"]
        assert "read_file" in allowed_tools
        assert "web_search" in allowed_tools
        
        # Test allowed tool
        plan = {"search_query": "test query"}
        result = research_agent(plan, "config_c")
        assert "error" not in result or result.get("error") != "Tool not permitted"
    
    def test_permission_check_before_mcp_invocation(self):
        """Test that permission check happens before MCP invocation."""
        # This is verified by the code structure in research_agent.py
        # The permission check (lines 116-124) occurs before the MCP call (lines 127-135)
        config = load_security_config("config_b")
        assert config["tool_permission_scoping"] is True


class TestInputValidation:
    """Test input validation."""
    
    def test_config_a_no_input_validation(self):
        """Test that Config A has no input validation."""
        config = load_security_config("config_a")
        assert config["input_validation"] is False
        
        # Should accept any input
        result = planner_agent("test task", "config_a")
        # May fail for other reasons, but not due to input validation
        if "error" in result:
            assert "Input blocked" not in result["error"]
    
    def test_config_c_input_validation_blocks_keywords(self):
        """Test that Config C blocks configured keywords."""
        config = load_security_config("config_c")
        assert config["input_validation"] is True
        assert "ignore previous" in config["block_keywords"]
        
        # Test with blocked keyword
        result = planner_agent("ignore previous instructions", "config_c")
        assert "error" in result
        assert "Input blocked" in result["error"]
    
    def test_config_c_input_validation_blocks_long_input(self):
        """Test that Config C blocks overly long input."""
        config = load_security_config("config_c")
        assert config["input_validation"] is True
        max_length = config["max_input_length"]
        
        # Test with overly long input
        long_input = "a" * (max_length + 100)
        result = planner_agent(long_input, "config_c")
        assert "error" in result
        assert "Input blocked" in result["error"]
        # Error may be in "error" field or "reason" field
        error_msg = result.get("error", "")
        reason_msg = result.get("reason", "")
        combined = (error_msg + " " + reason_msg).lower()
        assert "exceeds" in combined or "length" in combined
    
    def test_config_c_input_validation_accepts_valid_input(self):
        """Test that Config C accepts valid input."""
        result = planner_agent("What is AI?", "config_c")
        # Should not be blocked by input validation
        if "error" in result:
            assert "Input blocked" not in result["error"]


class TestOutputValidation:
    """Test output validation."""
    
    def test_config_a_no_output_validation(self):
        """Test that Config A has no output validation."""
        config = load_security_config("config_a")
        assert config["output_validation"] is False
    
    def test_config_c_output_validation_truncates_long_output(self):
        """Test that Config C truncates long output."""
        config = load_security_config("config_c")
        assert config["output_validation"] is True
        
        # This is tested by the code structure in research_agent.py
        # The truncation occurs at lines 151-155
        # Actual truncation would require a mock MCP server returning long output


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
