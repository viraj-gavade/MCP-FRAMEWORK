"""
Research Agent
Phase 2: Retrieves information using MCP tools

This agent receives a plan from the Planner Agent and retrieves information
using either the read_file or web_search MCP tool based on the search query.

MCP PROTOCOL NOTE: This agent communicates with MCP servers via stdio transport
using the official MCP Python SDK client. Each tool call spawns the MCP server
as a subprocess and communicates via stdin/stdout as per MCP specification.
This is verifiable using MCP Inspector: npx @modelcontextprotocol/inspector
"""

import asyncio
import logging
import sys
from typing import Dict, Any
from pathlib import Path
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

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


async def call_mcp_tool(server_script: str, tool_name: str, tool_args: dict) -> str:
    """
    Calls a tool on an MCP server via stdio transport.
    Spawns the server as a subprocess, connects, calls the tool, disconnects.
    
    Args:
        server_script: Path to the MCP server Python file
        tool_name: Name of the tool to call
        tool_args: Arguments to pass to the tool
    
    Returns:
        Tool result as string
    """
    server_params = StdioServerParameters(
        command=sys.executable,
        args=[server_script],
        env=None
    )
    
    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, tool_args)
                if result.content:
                    return result.content[0].text
                return "No result returned from tool"
    except Exception as e:
        return f"MCP tool call failed: {str(e)}"


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
    else:
        tool_name = "web_search"
    
    # Security check for Config B and C: tool permission scoping
    if config.get("tool_permission_scoping", False):
        allowed_tools = config.get("allowed_tools", {}).get("research", [])
        
        if tool_name not in allowed_tools and "*" not in allowed_tools:
            logger.warning(f"Tool '{tool_name}' not permitted for research agent")
            return {
                "error": "Tool not permitted",
                "tool_requested": tool_name
            }
    
    # Determine which server to use
    if search_query.startswith("file:"):
        filename = search_query[5:].strip()
        server_script = str(Path(__file__).parent.parent / "mcp_servers" / "file_read_server.py")
        result = asyncio.run(call_mcp_tool(server_script, "read_file", {"filename": filename}))
        tool_called = "read_file"
    else:
        server_script = str(Path(__file__).parent.parent / "mcp_servers" / "web_search_server.py")
        result = asyncio.run(call_mcp_tool(server_script, "web_search", {"query": search_query}))
        tool_called = "web_search"
    
    # Check if tool call failed
    if result.startswith("Error:") or result.startswith("MCP tool call failed"):
        logger.error(f"Tool call failed: {result}")
        return {
            "query_used": search_query,
            "tool_called": tool_called,
            "raw_result": "",
            "retrieval_success": False,
            "error": result
        }
    
    raw_result = result
    
    # Security check for Config C: output validation
    if config.get("output_validation", False):
        max_length = 2000
        if len(raw_result) > max_length:
            logger.warning(f"Tool output truncated: exceeds {max_length} characters")
            raw_result = raw_result[:max_length] + f"\n\n[TRUNCATED: Output exceeded {max_length} character limit]"
    
    logger.info(f"Research completed successfully using {tool_called}")
    
    return {
        "query_used": search_query,
        "tool_called": tool_called,
        "raw_result": raw_result,
        "retrieval_success": True
    }
