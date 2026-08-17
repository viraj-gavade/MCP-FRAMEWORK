"""
Research Agent
Phase 2: Retrieves information using MCP tools

This agent receives a plan from the Planner Agent and retrieves information
using either the read_file or web_search MCP tool based on the search query.
"""

import logging
from typing import Dict, Any
import subprocess
import json
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_security_config(config_name: str) -> Dict[str, Any]:
    """
    Load security configuration from YAML file.
    
    Args:
        config_name: Name of the config (e.g., "config_a", "config_b", "config_c")
    
    Returns:
        Dict containing security configuration
    """
    import yaml
    from pathlib import Path
    
    config_map = {
        "config_a": "no_security.yaml",
        "config_b": "basic_security.yaml",
        "config_c": "hardened.yaml"
    }
    
    config_file = Path(__file__).parent.parent / "configs" / config_map.get(config_name, "no_security.yaml")
    
    with open(config_file, 'r') as f:
        config = yaml.safe_load(f)
    
    return config


def call_mcp_tool(tool_name: str, arguments: Dict[str, str]) -> Dict[str, Any]:
    """
    Call an MCP server tool function directly.
    
    Args:
        tool_name: Name of the tool to call
        arguments: Dictionary of tool arguments
    
    Returns:
        Dictionary with tool result or error
    """
    try:
        # Call the tool directly (simplified for Phase 2)
        # In production, use proper MCP client protocol
        if tool_name == "read_file":
            from mcp_servers.file_read_server import read_file
            filename = arguments.get("filename", "")
            result = read_file(filename)
            
            if result.startswith("Error:"):
                return {"success": False, "error": result}
            
            return {"success": True, "result": result}
        
        elif tool_name == "web_search":
            from mcp_servers.web_search_server import web_search
            query = arguments.get("query", "")
            result = web_search(query)
            
            if result.startswith("Error:") or result.startswith("No mock"):
                return {"success": False, "error": result}
            
            return {"success": True, "result": result}
        
        else:
            return {"success": False, "error": f"Unknown tool: {tool_name}"}
    
    except Exception as e:
        logger.error(f"Error calling MCP tool: {e}")
        return {"success": False, "error": str(e)}


def research_agent(plan: Dict[str, Any], security_config: str = "config_a") -> Dict[str, Any]:
    """
    Retrieve information based on the plan from the Planner Agent.
    
    Args:
        plan: Dictionary from Planner Agent with search_query and other fields
        security_config: Security configuration name (config_a, config_b, config_c)
    
    Returns:
        Dictionary containing:
        - query_used: str
        - tool_called: str ("read_file" | "web_search")
        - raw_result: str
        - retrieval_success: bool
        Or error dictionary if tool not permitted
    """
    logger.info(f"Research Agent processing plan. Search query: {plan.get('search_query', 'N/A')}")
    
    # Load security configuration
    config = load_security_config(security_config)
    
    # Determine which tool to use
    search_query = plan.get("search_query", "")
    
    if search_query.startswith("file:"):
        tool_name = "read_file"
        filename = search_query[5:].strip()  # Remove "file:" prefix
        arguments = {"filename": filename}
    else:
        tool_name = "web_search"
        arguments = {"query": search_query}
    
    # Security check for Config B and C: tool permission scoping
    if config.get("tool_permission_scoping", False):
        allowed_tools = config.get("allowed_tools", {}).get("research", [])
        
        if tool_name not in allowed_tools and "*" not in allowed_tools:
            logger.warning(f"Tool '{tool_name}' not permitted for research agent")
            return {
                "error": "Tool not permitted",
                "tool_requested": tool_name
            }
    
    # Call the MCP tool
    tool_result = call_mcp_tool(tool_name, arguments)
    
    if not tool_result.get("success", False):
        logger.error(f"Tool call failed: {tool_result.get('error', 'Unknown error')}")
        return {
            "query_used": search_query,
            "tool_called": tool_name,
            "raw_result": "",
            "retrieval_success": False,
            "error": tool_result.get("error", "Unknown error")
        }
    
    raw_result = tool_result.get("result", "")
    
    # Security check for Config C: output validation
    if config.get("output_validation", False):
        max_length = 2000
        if len(raw_result) > max_length:
            logger.warning(f"Tool output truncated: exceeds {max_length} characters")
            raw_result = raw_result[:max_length] + f"\n\n[TRUNCATED: Output exceeded {max_length} character limit]"
    
    logger.info(f"Research completed successfully using {tool_name}")
    
    return {
        "query_used": search_query,
        "tool_called": tool_name,
        "raw_result": raw_result,
        "retrieval_success": True
    }
