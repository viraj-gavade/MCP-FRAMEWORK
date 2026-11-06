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
from typing import Dict, Any, Optional
from pathlib import Path
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


from configs import load_security_config

# Global tracker for MCP tool call counts per run
_tool_call_counts: Dict[str, int] = {}


def reset_tool_call_counter(run_id: Optional[str] = None) -> None:
    """Reset the tool call counter for a specific run or all runs."""
    global _tool_call_counts
    if run_id:
        _tool_call_counts.pop(run_id, None)
    else:
        _tool_call_counts.clear()


def get_tool_call_count(run_id: Optional[str] = None) -> int:
    """Get the current tool call count for a specific run or the default run."""
    key = run_id or "_default_"
    return _tool_call_counts.get(key, 0)


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


def research_agent(
    plan: Dict[str, Any],
    security_config: str = "config_a",
    run_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Retrieve information based on the plan from the Planner Agent.
    
    Args:
        plan: Dictionary from Planner Agent with search_query and other fields
        security_config: Security configuration name (config_a, config_b, config_c)
        run_id: Optional unique identifier for tracking per-run tool call budgets
    
    Returns:
        Dictionary containing:
        - query_used: str
        - tool_called: str ("read_file" | "web_search")
        - raw_result: str
        - retrieval_success: bool
        - security_events: Dict[str, Any] (optional)
        Or error dictionary if tool not permitted or limit exceeded
    """
    logger.info(f"Research Agent processing plan. Search query: {plan.get('search_query', 'N/A')}")
    
    # Load security configuration
    config = load_security_config(security_config)
    
    # Determine run tracking key
    effective_run_id = run_id or (plan.get("run_id") if isinstance(plan, dict) else None)
    run_key = effective_run_id or "_default_"
    
    sec_events: Dict[str, Any] = {}
    
    # Determine which tool to use
    search_query = plan.get("search_query", "")
    
    # Input validation for tool parameters
    if not search_query or not search_query.strip():
        logger.warning("Empty search query provided")
        return {
            "error": "Invalid tool parameters",
            "reason": "search query is empty"
        }
    
    if search_query.startswith("file:"):
        tool_name = "read_file"
        filename = search_query[5:].strip()  # Remove "file:" prefix
        
        # Validate filename parameter
        if not filename:
            logger.warning("Empty filename provided")
            return {
                "error": "Invalid tool parameters",
                "reason": "filename is empty"
            }
        
        # Basic filename validation - prevent path traversal
        if ".." in filename or "/" in filename or "\\" in filename:
            logger.warning(f"Invalid filename with path traversal attempt: {filename}")
            return {
                "error": "Invalid tool parameters",
                "reason": "filename contains invalid characters"
            }
    else:
        tool_name = "web_search"
        
        # Validate query parameter
        if len(search_query) > 1000:
            logger.warning(f"Search query too long: {len(search_query)} characters")
            return {
                "error": "Invalid tool parameters",
                "reason": "search query exceeds maximum length of 1000 characters"
            }
    
    # Security check for Config B and C: tool permission scoping
    if config.get("tool_permission_scoping", False):
        allowed_tools = config.get("allowed_tools", {}).get("research", [])
        
        if tool_name not in allowed_tools and "*" not in allowed_tools:
            logger.warning(f"Tool '{tool_name}' not permitted for research agent")
            return {
                "error": "Tool not permitted",
                "tool_requested": tool_name,
                "retrieval_success": False,
                "security_events": {"permission_denied": True}
            }
        
        # Tool call limit enforcement (e.g. max_tool_calls_per_run: 3 in Config C)
        max_tool_calls = config.get("max_tool_calls_per_run")
        if max_tool_calls is not None:
            current_calls = _tool_call_counts.get(run_key, 0)
            if current_calls >= max_tool_calls:
                logger.warning(
                    f"Tool call limit reached for run '{run_key}': call {current_calls + 1} denied (max allowed: {max_tool_calls})"
                )
                return {
                    "error": "Tool call limit exceeded",
                    "reason": f"Maximum tool calls per run ({max_tool_calls}) exceeded",
                    "tool_requested": tool_name,
                    "retrieval_success": False,
                    "security_events": {"permission_denied": True}
                }
        
        # Tool scoping checked and permitted
        sec_events["permission_denied"] = False
    
    # Record actual attempted tool invocation in run counter
    _tool_call_counts[run_key] = _tool_call_counts.get(run_key, 0) + 1
    
    # Determine which server to use and invoke tool
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
        err_res = {
            "query_used": search_query,
            "tool_called": tool_called,
            "raw_result": "",
            "retrieval_success": False,
            "error": result
        }
        if sec_events:
            err_res["security_events"] = sec_events
        return err_res
    
    raw_result = result
    
    # Security check for Config B and C: output validation (length truncation)
    output_truncated = False
    if config.get("output_validation", False):
        max_length = config.get("max_output_length", 2000)
        if len(raw_result) > max_length:
            logger.warning(f"Tool output truncated: exceeds {max_length} characters")
            raw_result = raw_result[:max_length] + f"\n\n[TRUNCATED: Output exceeded {max_length} character limit]"
            output_truncated = True
        sec_events["output_validation_failed"] = output_truncated
    
    logger.info(f"Research completed successfully using {tool_called}")
    
    result_dict = {
        "query_used": search_query,
        "tool_called": tool_called,
        "raw_result": raw_result,
        "retrieval_success": True
    }
    
    if sec_events:
        result_dict["security_events"] = sec_events
    
    return result_dict
