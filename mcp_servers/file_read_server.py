"""
MCP File Read Server
Phase 2: Model Context Protocol server for file reading operations

This server exposes a 'read_file' tool that reads files from the local /data/ folder.
It can be started as a standalone process: python mcp_servers/file_read_server.py
"""

import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define the data folder path
DATA_FOLDER = Path(__file__).parent.parent / "data"


def read_file(filename: str) -> str:
    """
    Read the contents of a file from the data folder.
    
    Args:
        filename: Name of the file to read (without path)
    
    Returns:
        str: File contents or error message
    """
    if not filename:
        return "Error: filename parameter is required"
    
    # Construct full file path
    file_path = DATA_FOLDER / filename
    
    # Security check: ensure file is within data folder
    try:
        file_path = file_path.resolve()
        data_folder_resolved = DATA_FOLDER.resolve()
        
        if not str(file_path).startswith(str(data_folder_resolved)):
            return "Error: Access denied - file must be within the data folder"
    except Exception as e:
        return f"Error: Invalid file path - {str(e)}"
    
    # Read file contents
    if not file_path.exists():
        return f"Error: File '{filename}' not found in data folder"
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        logger.info(f"Successfully read file: {filename}")
        return content
    
    except Exception as e:
        logger.error(f"Error reading file {filename}: {str(e)}")
        return f"Error: Could not read file '{filename}' - {str(e)}"
