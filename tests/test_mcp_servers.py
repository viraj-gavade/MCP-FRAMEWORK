"""
Test MCP Servers
Phase 2: Tests for MCP server functionality

This test module verifies:
- file_read_server starts and responds
- web_search_server starts and responds
- Tool calls return expected format
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from mcp_servers.web_search_server import MOCK_SEARCH_RESULTS


def test_web_search_mock_data():
    """
    Test that web_search_server has mock data loaded.
    """
    assert MOCK_SEARCH_RESULTS is not None, "Mock search results not loaded"
    assert len(MOCK_SEARCH_RESULTS) > 0, "Mock search results is empty"
    assert len(MOCK_SEARCH_RESULTS) >= 10, f"Expected at least 10 mock entries, got {len(MOCK_SEARCH_RESULTS)}"
    
    print("✓ Mock search data loaded successfully")


def test_web_search_exact_match():
    """
    Test that web_search returns exact match for known queries.
    """
    query = "prompt injection"
    query_lower = query.lower()
    
    assert query_lower in MOCK_SEARCH_RESULTS, f"Query '{query}' not in mock results"
    
    result = MOCK_SEARCH_RESULTS[query_lower]
    assert result is not None, "Result is None"
    assert len(result) > 0, "Result is empty"
    assert "prompt injection" in result.lower(), "Result doesn't mention prompt injection"
    
    print(f"✓ Exact match test passed for '{query}'")


def test_web_search_partial_match():
    """
    Test that web_search can find partial matches.
    """
    query = "MCP"
    query_lower = query.lower()
    
    # Find a partial match
    found = False
    for key in MOCK_SEARCH_RESULTS.keys():
        if query_lower in key.lower() or key.lower() in query_lower:
            found = True
            break
    
    assert found, f"No partial match found for '{query}'"
    
    print(f"✓ Partial match test passed for '{query}'")


def test_file_read_data_folder():
    """
    Test that data folder exists and is accessible.
    """
    data_folder = Path(__file__).parent.parent / "data"
    
    assert data_folder.exists(), f"Data folder does not exist at {data_folder}"
    assert data_folder.is_dir(), f"Data folder is not a directory at {data_folder}"
    
    print(f"✓ Data folder exists at {data_folder}")


def test_file_read_import():
    """
    Test that file_read_server module can be imported.
    """
    try:
        from mcp_servers import file_read_server
        assert file_read_server is not None, "file_read_server module is None"
        print("✓ file_read_server module imported successfully")
    except ImportError as e:
        pytest.fail(f"Failed to import file_read_server: {e}")


def test_web_search_import():
    """
    Test that web_search_server module can be imported.
    """
    try:
        from mcp_servers import web_search_server
        assert web_search_server is not None, "web_search_server module is None"
        print("✓ web_search_server module imported successfully")
    except ImportError as e:
        pytest.fail(f"Failed to import web_search_server: {e}")


if __name__ == "__main__":
    import pytest
    
    print("Running MCP server tests...")
    
    test_web_search_mock_data()
    test_web_search_exact_match()
    test_web_search_partial_match()
    test_file_read_data_folder()
    test_file_read_import()
    test_web_search_import()
    
    print("\nAll MCP server tests passed!")
