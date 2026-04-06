"""Provides the MCP server for agentic configuration of Sun lab data workflow components.

This module exposes tools that enable AI agents to manage shared configuration assets that work across all data
acquisition systems.
"""

from typing import Literal
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from ..configuration import (
    get_working_directory,
    set_working_directory as _set_working_directory,
)

# Initializes the MCP server with JSON response mode for structured output.
mcp = FastMCP(name="sl-shared-assets", json_response=True)


@mcp.tool()
def get_working_directory_tool() -> str:
    """Returns the current Sun lab working directory path.

    Returns:
        The absolute path to the working directory, or an error message if not configured.
    """
    try:
        path = get_working_directory()
    except FileNotFoundError as e:
        return f"Error: {e}"
    else:
        return f"Working directory: {path}"


@mcp.tool()
def set_working_directory_tool(directory: str) -> str:
    """Sets the Sun lab working directory.

    Args:
        directory: The absolute path to set as the working directory.

    Returns:
        A confirmation message or error description.
    """
    try:
        path = Path(directory)
        _set_working_directory(path=path)
    except Exception as e:
        return f"Error: {e}"
    else:
        return f"Working directory set to: {path}"


def run_server(transport: Literal["stdio", "sse", "streamable-http"] = "stdio") -> None:
    """Starts the MCP server with the specified transport.

    Args:
        transport: The transport type to use ('stdio', 'sse', or 'streamable-http').
    """
    mcp.run(transport=transport)
