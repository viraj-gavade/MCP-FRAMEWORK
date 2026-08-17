"""
File Read MCP Server
Phase 2 — MCP Security Research Project

Runs as a standalone MCP server process using stdio transport.
Exposes one tool: read_file

Start with:
    python mcp_servers/file_read_server.py
"""

from pathlib import Path

from mcp.server.fastmcp import FastMCP


DATA_DIR = Path(__file__).parent.parent / "data"

mcp = FastMCP("file-read-server")


@mcp.tool()
def read_file(filename: str) -> str:
    """
    Reads a file from the data directory and returns its contents.
    """

    # Security: prevent directory traversal
    safe_filename = Path(filename).name
    file_path = DATA_DIR / safe_filename

    # Create data directory if it doesn't exist
    if not DATA_DIR.exists():
        DATA_DIR.mkdir(parents=True)

        return "Error: data directory was empty, now created"

    # Check whether requested file exists
    if not file_path.exists():
        available = [
            file.name
            for file in DATA_DIR.iterdir()
            if file.is_file()
        ]

        return (
            f"Error: file '{safe_filename}' not found. "
            f"Available: {available}"
        )

    # Read file
    try:
        return file_path.read_text(encoding="utf-8")

    except Exception as e:
        return f"Error reading file: {str(e)}"


if __name__ == "__main__":
    mcp.run()