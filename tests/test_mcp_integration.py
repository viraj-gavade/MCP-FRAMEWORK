"""
Test MCP Integration
Phase 2: Integration tests for actual MCP client-server communication

This test module verifies:
- MCP servers start successfully
- Client can connect to servers via stdio transport
- MCP protocol initialization works
- Tool discovery works
- Tool invocation works through MCP protocol
- Results are returned correctly
"""

import sys
import asyncio
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def test_file_read_server_mcp_connection():
    """
    Test that the file-read MCP server can be started and connected to via stdio.
    """
    server_script = str(project_root / "mcp_servers" / "file_read_server.py")
    
    server_params = StdioServerParameters(
        command=sys.executable,
        args=[server_script],
        env=None
    )
    
    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                # Initialize MCP session
                await session.initialize()
                
                # List available tools
                tools = await session.list_tools()
                
                print(f"✓ File-read server connected successfully")
                print(f"  Available tools: {[tool.name for tool in tools.tools]}")
                
                # Verify read_file tool is available
                tool_names = [tool.name for tool in tools.tools]
                assert "read_file" in tool_names, "read_file tool not found"
                
                print(f"✓ read_file tool is available")
                
                # Call the tool
                result = await session.call_tool("read_file", {"filename": "mcp_overview.txt"})
                
                assert result.content is not None, "Tool result content is None"
                assert len(result.content) > 0, "Tool result content is empty"
                
                result_text = result.content[0].text
                print(f"✓ Tool call succeeded, result length: {len(result_text)} chars")
                
                # Verify result is not an error
                assert not result_text.startswith("Error:"), f"Tool returned error: {result_text}"
                
    except Exception as e:
        print(f"✗ MCP connection test failed: {e}")
        raise


async def test_web_search_server_mcp_connection():
    """
    Test that the web-search MCP server can be started and connected to via stdio.
    """
    server_script = str(project_root / "mcp_servers" / "web_search_server.py")
    
    server_params = StdioServerParameters(
        command=sys.executable,
        args=[server_script],
        env=None
    )
    
    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                # Initialize MCP session
                await session.initialize()
                
                # List available tools
                tools = await session.list_tools()
                
                print(f"✓ Web-search server connected successfully")
                print(f"  Available tools: {[tool.name for tool in tools.tools]}")
                
                # Verify web_search tool is available
                tool_names = [tool.name for tool in tools.tools]
                assert "web_search" in tool_names, "web_search tool not found"
                
                print(f"✓ web_search tool is available")
                
                # Call the tool
                result = await session.call_tool("web_search", {"query": "prompt injection"})
                
                assert result.content is not None, "Tool result content is None"
                assert len(result.content) > 0, "Tool result content is empty"
                
                result_text = result.content[0].text
                print(f"✓ Tool call succeeded, result length: {len(result_text)} chars")
                
                # Verify result is not an error
                assert not result_text.startswith("Error:"), f"Tool returned error: {result_text}"
                assert "prompt injection" in result_text.lower(), "Result doesn't contain expected content"
                
    except Exception as e:
        print(f"✗ MCP connection test failed: {e}")
        raise


def test_research_agent_uses_mcp():
    """
    Test that the research_agent actually uses MCP protocol (not direct imports).
    """
    # Check that research_agent imports MCP SDK components
    import agents.research_agent as research_module
    
    # Verify MCP SDK imports exist
    assert hasattr(research_module, 'ClientSession'), "ClientSession not imported in research_agent"
    assert hasattr(research_module, 'StdioServerParameters'), "StdioServerParameters not imported in research_agent"
    assert hasattr(research_module, 'stdio_client'), "stdio_client not imported in research_agent"
    
    # Verify call_mcp_tool function exists and uses MCP
    assert hasattr(research_module, 'call_mcp_tool'), "call_mcp_tool function not found"
    
    # Check that it does NOT directly import server modules
    import inspect
    source = inspect.getsource(research_module)
    
    # These imports should NOT exist if using MCP protocol
    assert "from mcp_servers import file_read_server" not in source, \
        "research_agent directly imports file_read_server (not using MCP)"
    assert "from mcp_servers import web_search_server" not in source, \
        "research_agent directly imports web_search_server (not using MCP)"
    assert "import file_read_server" not in source, \
        "research_agent directly imports file_read_server (not using MCP)"
    assert "import web_search_server" not in source, \
        "research_agent directly imports web_search_server (not using MCP)"
    
    print("✓ research_agent uses MCP SDK (ClientSession, StdioServerParameters, stdio_client)")
    print("✓ research_agent does NOT directly import server modules")
    print("✓ research_agent implements call_mcp_tool() for MCP communication")


if __name__ == "__main__":
    import pytest
    
    print("=" * 70)
    print("Running MCP Integration Tests")
    print("=" * 70)
    
    print("\n[Test 1] Checking research_agent implementation...")
    test_research_agent_uses_mcp()
    
    print("\n[Test 2] Testing file-read server MCP connection...")
    asyncio.run(test_file_read_server_mcp_connection())
    
    print("\n[Test 3] Testing web-search server MCP connection...")
    asyncio.run(test_web_search_server_mcp_connection())
    
    print("\n" + "=" * 70)
    print("All MCP integration tests passed!")
    print("=" * 70)
